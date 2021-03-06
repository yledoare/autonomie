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


from mock import MagicMock


def test_context_is_task(config):
    from autonomie.views.taskaction import context_is_task
    context = MagicMock()
    for i in ("invoice", "cancelinvoice", "estimation"):
        context.__name__ = i
        assert(context_is_task(context))

def test_context_is_not_task(config):
    from autonomie.views.taskaction import context_is_task
    context = MagicMock()
    for i in ("project_invoices", "project_cancelinvoices", "project_estimations"):
        context.__name__ = i
        assert not context_is_task(context)

def test_context_is_editable(config, pyramid_request):
    from autonomie.views.taskaction import context_is_editable
    context = MagicMock()
    context.__name__ = "invoice"
    context.is_editable = lambda :True
    assert(context_is_editable(None, context))
    context = MagicMock()
    context.__name__ = "notinvoice"
    assert(context_is_editable(None, context))
    context = MagicMock()
    context.__name__ = 'invoice'
    context.is_editable = lambda :False
    context.is_waiting = lambda :True
    pyramid_request.context = context
    assert(context_is_editable(pyramid_request, context))
