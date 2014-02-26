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
    Panels related to a company
"""
import itertools
import logging

from webhelpers import paginate
from sqlalchemy import desc, or_
from sqlalchemy.orm import aliased
from autonomie.models.task import CancelInvoice, Estimation, Invoice, Task
from autonomie.models.project import Project

from autonomie import resources


_DEFAULT_DISPLAYED_TASKS = (Invoice, Estimation, CancelInvoice)

_proj_aliases = [aliased(Project) for item in _DEFAULT_DISPLAYED_TASKS]


log = logging.getLogger(__name__)


def _get_tasklist_url(page):
    """
        Return a js url for tasklist pagination
        :param page: page number
    """
    return "#tasklist/{0}".format(page)


def _get_post_int(request, key, default):
    """
        Retrieve an int from the post datas
        :param key: the key the data should be retrieved from
        :param default: a default value
    """
    val = default
    if key in request.POST:
        try:
            val = int(request.POST[key])
        except ValueError:
            val = default
    return val


def _get_tasks_per_page(request):
    """
    Infers the nb of tasks per page from a request.
    If value supplied in POST, we redefine it in a cookie.

    tasks_per_page is a string representation of a base 10 int
        expected to be 5, 15 or 50.

    """
    post_value = _get_post_int(request, 'tasks_per_page', None)
    if post_value is not None:
        request.response.set_cookie('tasks_per_page', '%d' % post_value)
        return post_value

    if 'tasks_per_page' in request.cookies:
        raw_nb_per_page = request.cookies['tasks_per_page']
        return int(raw_nb_per_page)

    # fall back to base value
    return 5




def _company_tasks_query(company_id, displayed_tasks=_DEFAULT_DISPLAYED_TASKS):
    """
    Build sqlalchemy query to all tasks of a company, in reverse statusDate
    order.
    """
    query = Task.query()
    query = query.with_polymorphic(displayed_tasks)
    query = query.order_by(desc(Task.statusDate))

    used_proj_aliases = [
        _proj_aliases[index] for index, item in
        enumerate(_DEFAULT_DISPLAYED_TASKS)
        ]

    for proj_alias, task_class in itertools.izip(used_proj_aliases, displayed_tasks):
        query = query.outerjoin(proj_alias, Invoice.project)

    return query.filter(or_(
                    *(
                        alias.company_id == company_id
                        for alias in used_proj_aliases
                    )
                ))


def _get_taskpage_number(request):
    """
        Return the page number the user is asking
    """
    return _get_post_int(request, 'tasks_page_nb', 0)


def _get_task_requested_types(request):
    """
    By default, user wants all task types.
    """
    values = []
    if request.POST.get('task_show_invoice', True):
        values.append(Invoice)
    if request.POST.get('task_show_estimation', True):
        values.append(Estimation)
    if request.POST.get('task_show_cancelinvoice', True):
        values.append(CancelInvoice)
    return values


def recent_tasks_panel(context, request):
    """
    Panel returning the company's tasklist
    Parameters to be supplied as a cookie or in request.POST

    pseudo params: tasks_per_page, see _get_tasks_per_page()
    tasks_page_nb: -only in POST- the page we display
    """
    if not request.is_xhr:
        # javascript engine for the panel
        resources.task_list_js.need()

    task_types = _get_task_requested_types(request)
    query = _company_tasks_query(context.id, displayed_tasks=task_types)
    page_nb = _get_taskpage_number(request)
    items_per_page = _get_tasks_per_page(request)

    paginated_tasks = paginate.Page(
            query,
            page_nb,
            items_per_page=items_per_page,
            url=_get_tasklist_url,
            )

    result_data = {'tasks': paginated_tasks}

    return result_data


def includeme(config):
    """
        Add all panels to our main config object
    """
    config.add_panel(recent_tasks_panel,
                    'company_tasks',
                    renderer='panels/tasklist.mako')
