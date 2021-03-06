# -*- coding: utf-8 -*-
# * Copyright (C) 2012-2014 Croissance Commune
# * Authors:
#       * Arezki Feth <f.a@majerti.fr>;
#       * Miotte Julien <j.m@majerti.fr>;
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
import logging

from sqlalchemy import (
    Integer,
    Column,
    ForeignKey,
    String,
    DateTime,
    )
from sqlalchemy.orm import (
    relationship,
    backref,
    )

from autonomie.models.base import default_table_args
from autonomie.models.types import JsonEncodedList
from autonomie.models.activity import Event


log = logging.getLogger(__name__)


class Workshop(Event):
    """
    A workshop model

    It's a meta event grouping a bunch of timeslots with each their own
    attendance sheet
    """
    __tablename__ = 'workshop'
    __table_args__ = default_table_args
    __mapper_args__ = {'polymorphic_identity': 'workshop'}
    id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    # Libellé pour la sortie pdf
    info1 = Column(String(125), default="")
    info2 = Column(String(125), default="")
    info3 = Column(String(125), default="")
    leaders = Column(JsonEncodedList)

    @property
    def title(self):
        """
        Return a title for this given workshop
        """
        return u"Atelier '{0}' animé par {1}".format(
            self.name, ', '.join(self.leaders))


class Timeslot(Event):
    """
    A time slot for a given workshop
    """
    __tablename__ = 'timeslot'
    __table_args__ = default_table_args
    __mapper_args__ = {'polymorphic_identity': 'timeslot'}
    id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    start_time = Column(DateTime())
    end_time = Column(DateTime())
    workshop_id = Column(ForeignKey('workshop.id'))

    workshop = relationship(
        'Workshop',
        primaryjoin="Timeslot.workshop_id==Workshop.id",
        backref=backref(
            'timeslots',
            order_by='Timeslot.start_time',
            cascade='all, delete-orphan'
            ),
        )

    @property
    def duration(self):
        time_delta = self.end_time - self.start_time
        hours, rest = divmod(time_delta.seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        hours = 24 * time_delta.days + hours
        return hours, minutes
