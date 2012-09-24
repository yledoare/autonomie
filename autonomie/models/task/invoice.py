# -*- coding: utf-8 -*-
# * File Name :
#
# * Copyright (C) 2010 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 03-09-2012
# * Last Modified :
#
# * Project :
#
"""
    Invoice model
"""
import datetime
import logging

from zope.interface import implementer

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import Date
from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred
from sqlalchemy.orm import backref
from sqlalchemy.orm import validates
# Aye : ici on a du double dans la bdd, en attendant une éventuelle
# migration des données, on dépend entièrement de mysql
from sqlalchemy.dialects.mysql import DOUBLE

from autonomie.models.types import CustomDateType
from autonomie.models.utils import get_current_timestamp
from autonomie.exception import Forbidden
from autonomie.models import DBSESSION
from autonomie.models import DBBASE

from .compute import TaskCompute
from .interfaces import IMoneyTask
from .interfaces import IInvoice
from .interfaces import IPaidTask
from .task import Task
from .states import DEFAULT_STATE_MACHINES

log = logging.getLogger(__name__)


def get_next_officialNumber():
    """
        Return the next available official number
    """
    a = Invoice.get_officialNumber().first()[0]
    b = ManualInvoice.get_officialNumber().first()[0]
    c = CancelInvoice.get_officialNumber().first()[0]
    if not a:
        a = 0
    if not b:
        b = 0
    if not c:
        c = 0
    next_ = max(a, b, c) + 1
    return int(next_)


@implementer(IPaidTask, IInvoice, IMoneyTask)
class Invoice(Task, TaskCompute):
    """
        Invoice Model
    """
    __tablename__ = 'invoice'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    __mapper_args__ = {
                       'polymorphic_identity': 'invoice',
                       }
    id = Column("id", ForeignKey('task.id'), primary_key=True)
    estimation_id = Column("estimation_id", ForeignKey('estimation.id'))
    project_id = Column("project_id", ForeignKey('project.id'))
    sequenceNumber = Column("sequenceNumber", Integer, nullable=False)
    number = Column("number", String(100), nullable=False)
    #tva = Column("tva", Integer, nullable=False, default=196)
    paymentConditions = deferred(Column("paymentConditions", Text),
                                 group='edit')
    deposit = deferred(Column('deposit', Integer, nullable=False, default=0),
                       group='edit')
    course = deferred(Column('course', Integer, nullable=False, default=0),
                      group='edit')
    officialNumber = Column("officialNumber", Integer)
    paymentMode = Column("paymentMode", String(10))
    displayedUnits = deferred(
        Column('displayedUnits', Integer, nullable=False, default=0),
        group='edit')
    discountHT = Column('discountHT', Integer, default=0)
    expenses = deferred(Column('expenses', Integer, default=0), group='edit')

    project = relationship(
        "Project",
        backref=backref('invoices', order_by='Invoice.taskDate')
    )
    #phase =  relationship("Phase", backref=backref("invoices",
    #                                            order_by='Invoice.taskDate'))
    estimation = relationship(
        "Estimation",
        backref="invoices",
        primaryjoin="Invoice.estimation_id==Estimation.id")

    state_machine = DEFAULT_STATE_MACHINES['invoice']

    paid_states = ('resulted',)
    not_paid_states = ('valid', 'paid', )
    valid_states = paid_states + not_paid_states

    def is_draft(self):
        return self.CAEStatus in ('draft', 'invalid',)

    def is_editable(self, manage=False):
        if manage:
            return self.CAEStatus in ('draft', 'invalid', 'wait', None,)
        else:
            return self.CAEStatus in ('draft', 'invalid', None,)

    def is_valid(self):
        return self.CAEStatus == 'valid'

    def has_been_validated(self):
        return self.CAEStatus in self.valid_states

    def is_waiting(self):
        return self.CAEStatus == "wait"

    def is_invoice(self):
        return True

    def is_paid(self):
        return self.CAEStatus == 'paid'

    def is_resulted(self):
        return self.CAEStatus == 'resulted'

    def is_cancelled(self):
        """
            Return True is the invoice has been cancelled
        """
        return self.CAEStatus == 'aboinv'

    def is_tolate(self):
        """
            Return True if a payment is expected since more than
            45 days
        """
        today = datetime.date.today()
        elapsed = today - self.taskDate
        if elapsed > datetime.timedelta(days=45):
            tolate = True
        else:
            tolate = False
        return self.CAEStatus in ('valid', 'paid', ) and tolate

    @classmethod
    def get_name(cls, seq_number, account=False, sold=False):
        """
            return an invoice name
        """
        if account:
            taskname_tmpl = u"Facture d'acompte {0}"
        elif sold:
            taskname_tmpl = u"Facture de solde"
        else:
            taskname_tmpl = u"Facture {0}"
        return taskname_tmpl.format(seq_number)

    @classmethod
    def get_number(cls, project, seq_number, taskDate, deposit=False):
        if deposit:
            tasknumber_tmpl = u"{0}_{1}_FA{2}_{3:%m%y}"
        else:
            tasknumber_tmpl = u"{0}_{1}_F{2}_{3:%m%y}"
        pcode = project.code
        ccode = project.client.code
        return tasknumber_tmpl.format(pcode, ccode, seq_number, taskDate)

    @validates("paymentMode")
    def validate_paymentMode(self, key, paymentMode):
        """
            Validate the paymentMode
        """
        if not paymentMode in ('CHEQUE', 'VIREMENT'):
            raise Forbidden(u'Mode de paiement inconnu')
        return paymentMode

    @classmethod
    def get_officialNumber(cls):
        """
            Return the next officialNumber available in the Invoice's table
            Take the max of official Number
            when taskDate startswith the current year
            taskdate is a string (YYYYMMDD)
        """
        current_year = datetime.date.today().year
        return DBSESSION.query(func.max(Invoice.officialNumber)).filter(
                Invoice.taskDate.between(current_year * 10000,
                                         (current_year + 1) * 10000
                                    ))

    def gen_cancelinvoice(self, user_id):
        """
            Return a cancel invoice with self's informations
        """
        cancelinvoice = CancelInvoice()
        seq_number = self.project.get_next_cancelinvoice_number()
        cancelinvoice.name = CancelInvoice.get_name(seq_number)
        cancelinvoice.phase_id = self.phase_id
        cancelinvoice.CAEStatus = 'draft'
        cancelinvoice.taskDate = datetime.date.today()
        cancelinvoice.description = self.description

        cancelinvoice.invoice_id = self.id
        cancelinvoice.invoiceDate = self.taskDate
        cancelinvoice.invoiceNumber = self.officialNumber
        cancelinvoice.expenses = -1 * self.expenses
        cancelinvoice.displayedUnits = self.displayedUnits
        cancelinvoice.sequenceNumber = seq_number
        cancelinvoice.number = CancelInvoice.get_number(self.project,
                            cancelinvoice.sequenceNumber,
                            cancelinvoice.taskDate)
        cancelinvoice.statusPerson = user_id
        cancelinvoice.project_id = self.project_id
        cancelinvoice.owner_id = user_id
        for line in self.lines:
            cancelinvoice.lines.append(line.gen_cancelinvoice_line())
        rowindex = self.get_next_row_index()
        for discount in self.discounts:
            discount_line = CancelInvoiceLine(cost=discount.amount,
                                          tva=discount.tva,
                                          quantity=1,
                                          description=discount.description,
                                          rowIndex=rowindex,
                                          unity='NONE')
            rowindex += 1
            cancelinvoice.lines.append(discount_line)
        for index, payment in enumerate(self.payments):
            paid_line = CancelInvoiceLine(
                cost=payment.amount,
                tva=0,
                quantity=1,
                description=u"Paiement {0}".format(index + 1),
                rowIndex=rowindex,
                unity='NONE')
            rowindex += 1
            cancelinvoice.lines.append(paid_line)
        return cancelinvoice

    def get_next_row_index(self):
        return len(self.lines) + 1

    def valid_callback(self):
        """
            Validate an invoice
        """
        self.officialNumber = get_next_officialNumber()
        self.taskDate = datetime.date.today()

    def record_payment(self, mode, amount, resulted=False):
        """
            Validate a record payment
        """
        log.debug("Invoice payment recording")
        log.debug("  o There was to pay : %s" % self.topay())
        log.debug("    ->Is recorded : %s" % amount)
        payment = Payment(mode=mode, amount=amount)
        self.payments.append(payment)
        log.debug("     -> There still to pay : %s" % self.topay())
        if self.topay() == 0 or resulted:
            self.CAEStatus = 'resulted'
        return self

    def duplicate(self, user, project, phase):
        """
            Duplicate the current invoice
        """
        seq_number = project.get_next_invoice_number()
        date = datetime.date.today()

        invoice = Invoice()
        invoice.name = self.get_name(seq_number)
        invoice.CAEStatus = 'draft'
        invoice.taskDate = date
        invoice.description = self.description
        invoice.expenses = self.expenses

        invoice.sequenceNumber = seq_number
        invoice.number = Invoice.get_number(project, seq_number, date)
        #invoice.tva = self.tva
        invoice.paymentConditions = self.paymentConditions
        invoice.deposit = self.deposit
        invoice.course = self.course
        invoice.displayedUnits = self.displayedUnits
        invoice.discountHT = self.discountHT
        invoice.expenses = self.expenses

        invoice.statusPersonAccount = user
        invoice.project = project
        invoice.phase = phase
        invoice.owner = user
        for line in self.lines:
            invoice.lines.append(line.duplicate())
        for line in self.discounts:
            invoice.discounts.append(line.duplicate())
        return invoice

    def __repr__(self):
        return u"<Invoice id:{s.id}>".format(s=self)


class InvoiceLine(DBBASE):
    """
        Invoice lines
    """
    __tablename__ = 'invoice_line'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    id = Column("id", Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('invoice.id'))
    rowIndex = Column("rowIndex", Integer, default=1)
    description = Column("description", Text)
    cost = Column(Integer, default=0)
    tva = Column("tva", Integer, nullable=False, default=196)
    quantity = Column(DOUBLE, default=1)
    creationDate = deferred(Column("creationDate", CustomDateType,
                                            default=get_current_timestamp))
    updateDate = deferred(Column("updateDate", CustomDateType,
                                        default=get_current_timestamp,
                                        onupdate=get_current_timestamp))
    unity = Column("unity", String(10))
    task = relationship("Invoice", backref=backref("lines",
                            order_by='InvoiceLine.rowIndex'))

    def duplicate(self):
        """
            duplicate a line
        """
        newone = InvoiceLine()
        newone.rowIndex = self.rowIndex
        newone.cost = self.cost
        newone.tva = self.tva
        newone.description = self.description
        newone.quantity = self.quantity
        newone.unity = self.unity
        return newone

    def gen_cancelinvoice_line(self):
        """
            Return a cancel invoice line duplicating this one
        """
        newone = CancelInvoiceLine()
        newone.rowIndex = self.rowIndex
        newone.cost = -1 * self.cost
        newone.tva = self.tva
        newone.description = self.description
        newone.quantity = self.quantity
        newone.unity = self.unity
        return newone

    def total_ht(self):
        """
            Compute the line's total
        """
        return float(self.cost) * float(self.quantity)

    def tva_amount(self):
        """
            compute the tva amount of a line
        """
        totalht = self.total_ht()
        result = float(totalht) * (max(int(self.tva), 0) / 10000.0)
        return result

    def total(self):
        return self.tva_amount() + self.total_ht()

    def __repr__(self):
        return u"<InvoiceLine id:{s.id} task_id:{s.task_id} cost:{s.cost} \
 quantity:{s.quantity} tva:{s.tva}".format(s=self)


@implementer(IPaidTask, IInvoice, IMoneyTask)
class CancelInvoice(Task, TaskCompute):
    """
        CancelInvoice model
        Could also be called negative invoice
    """
    __tablename__ = 'cancelinvoice'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    __mapper_args__ = {'polymorphic_identity': 'cancelinvoice'}
    id = Column(Integer, ForeignKey('task.id'), primary_key=True)

    invoice_id = Column(Integer, ForeignKey('invoice.id'),
                                                        default=None)
    project_id = Column(Integer, ForeignKey('project.id'))
    sequenceNumber = deferred(Column(Integer), group='edit')
    number = Column(String(100))
    #tva = Column(Integer, default=1960)
    reimbursementConditions = deferred(Column(String(255), default=None),
            group='edit')
    officialNumber = deferred(Column(Integer, default=None), group='edit')
    paymentMode = deferred(Column(String(80), default=None), group='edit')
    displayedUnits = Column(Integer, default=0)
    expenses = deferred(Column(Integer, default=0), group='edit')

    project = relationship("Project", backref=backref('cancelinvoices',
                                            order_by='CancelInvoice.taskDate')
                            )
    invoice = relationship("Invoice",
                      backref=backref("cancelinvoice", uselist=False),
                      primaryjoin="CancelInvoice.invoice_id==Invoice.id")

    state_machine = DEFAULT_STATE_MACHINES['cancelinvoice']
    valid_states = ('valid', )

    def is_editable(self, manage=False):
        if manage:
            return self.CAEStatus in ('draft', 'invalid', 'wait', None,)
        else:
            return self.CAEStatus in ('draft', 'invalid', None,)

    def is_draft(self):
        return self.CAEStatus in ('draft', 'invalid')

    def is_valid(self):
        return self.CAEStatus == 'valid'

    def has_been_validated(self):
        return self.CAEStatus in self.valid_states

    def is_paid(self):
        return False

    def is_resulted(self):
        return self.has_been_validated()

    def is_cancelled(self):
        return False

    def is_waiting(self):
        return self.CAEStatus == 'wait'

    def is_cancelinvoice(self):
        return True

    @classmethod
    def get_name(cls, seq_number):
        """
            return an cancelinvoice name
        """
        taskname_tmpl = u"Avoir {0}"
        return taskname_tmpl.format(seq_number)

    @classmethod
    def get_officialNumber(cls):
        """
            Return the greatest officialNumber actually used in the
            ManualInvoice table
        """
        current_year = datetime.date.today().year
        return DBSESSION.query(func.max(CancelInvoice.officialNumber)).filter(
                    func.year(CancelInvoice.taskDate) == current_year)

    def is_tolate(self):
        """
            Return False
        """
        return False

    @classmethod
    def get_number(cls, project, seq_number, taskDate):
        tasknumber_tmpl = u"{0}_{1}_A{2}_{3:%m%y}"
        pcode = project.code
        ccode = project.client.code
        return tasknumber_tmpl.format(pcode, ccode, seq_number, taskDate)

    def valid_callback(self):
        """
            Validate a cancelinvoice
            Generates an official number
        """
        self.officialNumber = get_next_officialNumber()
        self.taskDate = datetime.date.today()


@implementer(IInvoice)
class ManualInvoice(DBBASE):
    """
        Modèle pour les factures manuelles (ancienne version)
    """
    __tablename__ = 'manual_invoice'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    id = Column('id', BigInteger, primary_key=True)
    officialNumber = Column('sequence_id', BigInteger)
    description = Column('libelle', String(255))
    montant_ht = Column("montant_ht", Integer)
    tva = Column("tva", Integer)
    payment_ok = Column("paiement_ok", Integer)
    statusDate = Column("paiement_date", Date())
    paymentMode = Column("paiement_comment", String(255))
    client_id = Column('client_id', String(5),
                            ForeignKey('customer.id'))
    taskDate = Column("date_emission", Date(),
                                default=datetime.datetime.now)
    company_id = Column('compagnie_id', BigInteger,
                            ForeignKey('company.id'))
    created_at = deferred(Column("created_at", DateTime,
                                      default=datetime.datetime.now))
    updated_at = deferred(Column("updated_at", DateTime,
                                      default=datetime.datetime.now,
                                      onupdate=datetime.datetime.now))
    client = relationship("Client",
                primaryjoin="Client.id==ManualInvoice.client_id",
                backref='manual_invoices')
    company = relationship("Company",
                primaryjoin="Company.id==ManualInvoice.company_id",
                  backref='manual_invoices')

    @property
    def statusComment(self):
        return None

    @property
    def discounts(self):
        return []

    @property
    def payments(self):
        """
            Return a payment object for compatibility
            with other invoices
        """
        return [Payment(mode=self.paymentMode, amount=0, date=self.statusDate)]

    @property
    def number(self):
        """
            return the invoice number
        """
        return u"FACT_MAN_{0}".format(self.officialNumber)

    def get_company(self):
        return self.company

    def get_client(self):
        return self.client

    def is_paid(self):
        return False

    def is_resulted(self):
        return self.payment_ok == 1

    def is_cancelled(self):
        return False

    def is_tolate(self):
        today = datetime.date.today()
        elapsed = today - self.taskDate
        return not self.is_resulted() and elapsed > datetime.timedelta(days=45)

    @validates("paymentMode")
    def validate_paymentMode(self, key, paymentMode):
        """
            Validate the paymentMode
        """
        if not paymentMode in (u'chèque', u'virement'):
            raise Forbidden(u'Mode de paiement inconnu')
        return paymentMode

    def is_cancelinvoice(self):
        """
            return false
        """
        return False

    def is_invoice(self):
        """
            return false
        """
        return False

    @classmethod
    def get_officialNumber(cls):
        """
            Return the greatest officialNumber actually used in the
            ManualInvoice table
        """
        current_year = datetime.date.today().year
        return DBSESSION.query(func.max(ManualInvoice.officialNumber)).filter(
                    func.year(ManualInvoice.taskDate) == current_year)

    def total_ht(self):
        return int(self.montant_ht * 100)

    def tva_amount(self):
        total_ht = self.total_ht()
        if self.tva:
            tva = int(self.tva)
        else:
            tva = 0
        tva = max(tva, 0)
        return int(float(total_ht) * (tva / 10000.0))


class CancelInvoiceLine(DBBASE):
    """
        CancelInvoice lines
    """
    __tablename__ = 'cancelinvoice_line'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('cancelinvoice.id'))
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now,
                                  onupdate=datetime.datetime.now)
    task = relationship("CancelInvoice", backref="lines",
                            order_by='CancelInvoiceLine.rowIndex'
                        )
    rowIndex = Column(Integer)
    description = Column(Text, default="")
    cost = Column(Integer, default=0)
    tva = Column("tva", Integer, nullable=False, default=196)
    quantity = Column(DOUBLE, default=1)
    unity = Column(String(10), default=None)

    def duplicate(self):
        """
            duplicate a line
        """
        newone = CancelInvoiceLine()
        newone.rowIndex = self.rowIndex
        newone.cost = self.cost
        newone.tva = self.tva
        newone.description = self.description
        newone.quantity = self.quantity
        newone.unity = self.unity
        return newone

    def total_ht(self):
        """
            Compute the line's total
        """
        return float(self.cost) * float(self.quantity)

    def tva_amount(self):
        """
            compute the tva amount of a line
        """
        totalht = self.total_ht()
        result = float(totalht) * (max(int(self.tva), 0) / 10000.0)
        return result

    def total(self):
        return self.tva_amount() + self.total_ht()

    def __repr__(self):
        return u"<CancelInvoiceLine id:{s.id} task_id:{s.task_id} \
cost:{s.cost} quantity:{s.quantity} tva:{s.tva}".format(s=self)


class Payment(DBBASE):
    """
        Payment entry
    """
    __tablename__ = 'payment'
    __table_args__ = {'mysql_engine': 'MyISAM', "mysql_charset": 'utf8'}
    id = Column(Integer, primary_key=True)
    mode = Column(String(50))
    amount = Column(Integer)
    date = Column(DateTime, default=datetime.datetime.now)
    task_id = Column(Integer, ForeignKey('task.id'))
    task = relationship("Task",
                primaryjoin="Task.id==Payment.task_id",
                backref=backref('payments', order_by='Payment.date'))

    def get_amount(self):
        return self.amount

    def get_mode_str(self):
        """
            Return a user-friendly string describing the payment Mode
        """
        if self.mode == 'CHEQUE':
            return u"par chèque"
        elif self.mode == 'VIREMENT':
            return u"par virement"
        else:
            return u"mode paiement inconnu"

    def __repr__(self):
        return u"<Payment id:{s.id} task_id:{s.task_id} amount:{s.amount}\
 mode:{s.mode} date:{s.date}".format(s=self)
