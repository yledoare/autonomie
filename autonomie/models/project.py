# -*- coding: utf-8 -*-
# * Copyright (C) 2012-2013 Croissance Commune
# * Authors:
#       * Arezki Feth <f.a@majerti.fr>;
#       * Miotte Julien <j.m@majerti.fr>;
#       * Pettier Gabriel;
#       * TJEBBES Gaston <g.t@majerti.fr>
#
# This file is part of Autonomie : Progiciel de gestion de CAE.
#
#    Autonomie is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Autonomie is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Autonomie.  If not, see <http://www.gnu.org/licenses/>.
#

"""
    Project model
"""
import colander
import deform

from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.orm import (
    deferred,
    relationship,
    backref,
)

from autonomie import forms
from autonomie.models.utils import get_current_timestamp
from autonomie.models.types import (
    CustomDateType,
    PersistentACLMixin,
)
from autonomie.models.base import (
    default_table_args,
    DBBASE,
)
from autonomie.models.node import Node


ProjectCustomer = Table('project_customer', DBBASE.metadata,
        Column("project_id", Integer, ForeignKey('project.id')),
        Column("customer_id", Integer, ForeignKey('customer.id')),
        mysql_charset=default_table_args['mysql_charset'],
        mysql_engine=default_table_args['mysql_engine'])


def build_customer_value(customer=None):
    """
        return the tuple for building customer select
    """
    if customer:
        return (str(customer.id), customer.name)
    else:
        return ("0", u"Sélectionnez")


def build_customer_values(customers):
    """
        Build human understandable customer labels
        allowing efficient discrimination
    """
    options = [build_customer_value()]
    options.extend([build_customer_value(customer)
                            for customer in customers])
    return options

def get_customers_from_request(request):
    if request.context.__name__ == 'project':
        customers = request.context.company.customers
    elif request.context.__name__ == 'company':
        customers = request.context.customers
    else:
        customers = []
    return customers

@colander.deferred
def deferred_customer_select(node, kw):
    request = kw['request']
    customers = get_customers_from_request(request)
    return deform.widget.Select2Widget(
        values=build_customer_values(customers),
        placeholder=u'Sélectionner un client',
    )


@colander.deferred
def deferred_default_customer(node, kw):
    """
        Return the customer provided as request arg if there is one
    """
    request = kw['request']
    customers = get_customers_from_request(request)
    customer = request.params.get('customer')
    if customer in [str(c.id) for c in customers]:
        return int(customer)
    else:
        return colander.null


@colander.deferred
def deferred_customer_validator(node, kw):
    request = kw['request']
    customers = get_customers_from_request(request)
    customer_ids = [customer.id for customer in customers]
    def customer_oneof(value):
        if value in ("0", 0):
            return u"Veuillez choisir un client"
        elif value not in customer_ids:
            return u"Entrée invalide"
        return True
    return colander.Function(customer_oneof)


def check_begin_end_date(form, value):
    """
    Check the project beginning date preceeds the end date
    """
    ending = value.get('endingDate')
    starting = value.get('startingDate')

    if ending is not None and starting is not None:
        if not ending >= starting:
            exc = colander.Invalid(
                form,
                u"La date de début doit précéder la date de fin du projet"
            )
            exc['startingDate'] = u"Doit précéder la date de fin"
            raise exc


def get_projects_from_request(request):
    """
    Return the projects of the current company (we fetch the company from the
    request context)
    """
    if request.context.__name__ == 'project':
        # Edition (we don't want the current project)
        projects = [project for project in request.context.company.projects \
                    if project != request.context]
    elif request.context.__name__ == 'company':
        projects = request.context.projects
    else:
        raise Exception("We can't retrieve the projects from something that's \
not a a project itself or a company")

    return projects


@colander.deferred
def deferred_project_code_validator(node, kw):
    request = kw['request']
    projects = get_projects_from_request(request)

    def unique_pcode(node, code):
        if code.upper() in [project.code.upper() for project in projects]:
            raise colander.Invalid(
                node,
                u"Ce code est déjà utilisé pour identifier un autre projet"
            )

    return colander.All(colander.Length(min=4, max=4), unique_pcode)


class Project(Node):
    """
        The project model
    """
    __tablename__ = 'project'
    __table_args__ = default_table_args
    __mapper_args__ = {'polymorphic_identity': 'project'}

    __colanderalchemy_config__ = {'validator': check_begin_end_date}

    id = Column(
        ForeignKey('node.id'),
        primary_key=True,
        info={'colanderalchemy': forms.EXCLUDED}
    )

    code = Column(
        String(4),
        info={
            'colanderalchemy': {
                'title': u"Code",
                'widget': deform.widget.TextInputWidget(mask='****'),
                'validator': deferred_project_code_validator,
            },
        },
        nullable=False,
    )

    type = deferred(
        Column(
            String(150),
            info={'colanderalchemy': {'title': u"Type de projet"}},
        ),
        group='edit'
    )

    company_id = Column(
        Integer,
        ForeignKey('company.id'),
        info={
            'options':{'csv_exclude':True},
            'colanderalchemy': forms.EXCLUDED,
        }
    )

    startingDate = deferred(
        Column(
            CustomDateType,
            info={
                "colanderalchemy":{
                    "title": u"Date de début",
                    "typ": colander.Date(),
                }
            },
            default=get_current_timestamp,
        ),
        group='edit',
    )

    endingDate = deferred(
        Column(
            CustomDateType,
            info={
                "colanderalchemy":{
                    "title": u"Date de fin",
                    "typ": colander.Date(),
                }
            },
            default=get_current_timestamp,
        ),
        group='edit',
    )

    definition = deferred(
        Column(
            Text,
            info={
                'label':u"Définition",
                  'colanderalchemy':{
                      'title': u"Définition",
                      'widget': deform.widget.TextAreaWidget(
                          css_class="col-md-10"
                      ),
                  }
            },

        ),
        group='edit',
    )

    archived = Column(
        Boolean(),
        default=False,
        info={'colanderalchemy': forms.EXCLUDED},
    )

    customers = relationship(
        "Customer",
        secondary=ProjectCustomer,
        backref=backref(
            'projects',
            info={'colanderalchemy': forms.EXCLUDED},
        ),
        info={
            'colanderalchemy': {
                "title": u"Client",
                "exclude": True,
            },
            'export': {'exclude': True},
        }
    )

    @property
    def invoices(self):
        return [task for task in self.tasks if task.type_=="invoice"]

    @property
    def estimations(self):
        return [task for task in self.tasks if task.type_=="estimation"]

    @property
    def cancelinvoices(self):
        return [task for task in self.tasks if task.type_=="cancelinvoice"]

    def get_estimation(self, taskid):
        """
            Returns the estimation with id taskid
        """
        for estimation in self.estimations:
            if estimation.id == int(taskid):
                return estimation
        raise KeyError("No such task in this project")

    def get_invoice(self, taskid):
        """
            Returns the estimation with id taskid
        """
        for invoice in self.invoices:
            if invoice.id == int(taskid):
                return invoice
        raise KeyError("No such task in this project")

    def is_deletable(self):
        """
            Return True if this project could be deleted
        """
        return self.archived and not self.invoices

    def get_company_id(self):
        return self.company.id

    @staticmethod
    def get_number(task_number, root_str):
        """
            return the number of the given doc
        """
        num = task_number[len(root_str):]
        try:
            return int(num)
        except:
            return 0

    def get_next_estimation_number(self):
        all_nums = [
            self.get_number(est.number, "Devis ")
            for est in self.estimations
        ]
        all_nums.append(
            len(self.estimations)
        )
        return max(all_nums) + 1

    def get_next_invoice_number(self):
        all_nums = [
            self.get_number(inv.number, "Facture ")
            for inv in self.invoices
        ]
        all_nums.append(len(self.invoices))
        return max(all_nums) + 1

    def get_next_cancelinvoice_number(self):
        all_nums = [
            self.get_number(cinv.number, "Avoir ")
            for cinv in self.cancelinvoices
        ]
        all_nums.append(len(self.cancelinvoices))
        return max(all_nums) + 1

    def todict(self):
        """
            Return a dict view of this object
        """
        phases = [phase.todict() for phase in self.phases]
        return dict(
            id=self.id,
            name=self.name,
            code=self.code,
            definition=self.definition,
            type=self.type,
            archived=self.archived,
            phases=phases,
        )

    def __json__(self, request):
        return self.todict()


class Phase(DBBASE, PersistentACLMixin):
    """
        Phase d'un projet
    """
    __tablename__ = 'phase'
    __table_args__ = default_table_args
    id = Column(
        Integer,
        primary_key=True,
        info={'colanderalchemy': forms.EXCLUDED},
    )

    project_id = Column(
        ForeignKey('project.id'),
        info={'colanderalchemy': forms.EXCLUDED},
    )

    name = Column("name", String(150), default=u'Phase par défaut')

    project = relationship(
        "Project",
        backref=backref(
            "phases",
            cascade="all, delete-orphan",
            info={
                'colanderalchemy': forms.EXCLUDED,
                'export': {'exclude': True}
            },
        ),
        info={
            'colanderalchemy': forms.EXCLUDED,
            'export': {'exclude': True}
        },
    )

    creationDate = deferred(
        Column(
            CustomDateType,
            info={'colanderalchemy': forms.EXCLUDED},
            default=get_current_timestamp,
        )
    )

    updateDate = deferred(
        Column(
            CustomDateType,
            info={'colanderalchemy': forms.EXCLUDED},
            default=get_current_timestamp,
            onupdate=get_current_timestamp,
        )
    )

    def is_default(self):
        """
            return True if this phase is a default one
        """
        return self.name in (u'Phase par défaut', u"default", u"défaut",)

    @property
    def estimations(self):
        return self.get_tasks_by_type('estimation')

    @property
    def invoices(self):
        return self.get_tasks_by_type('invoice')

    @property
    def cancelinvoices(self):
        return self.get_tasks_by_type('cancelinvoice')

    def get_tasks_by_type(self, type_):
        """
            return the tasks of the passed type
        """
        return [doc for doc in self.tasks if doc.type_ == type_]

    def todict(self):
        """
            return a dict version of this object
        """
        return dict(id=self.id,
                    name=self.name)


FORM_GRID = (
    ((4, True, ), (2, True, ), (4, True, ), ),
    ((6, True, ), ),
    ((3, True, ), (3, True, ), ),
    ((10, True, ), ),
)
