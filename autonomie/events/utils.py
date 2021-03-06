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
    Tools used to manage events
"""
import logging
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

log = logging.getLogger(__file__)

UNSUBSCRIBE_MSG = u"<mailto:{0}?subject=Unsubscribe-{1}>"

UNSUBSCRIBE_LINK = u"""


Vous avez reçu ce mail car vous êtes utilisateurs de l'application Autonomie. \
Si vous avez reçu ce mail par erreur, nous vous prions de nous \
en excuser. Vous pouvez vous désincrire en écrivant à \
{0}?subject=Unsubscribe-{1}."""


def format_mail(mail):
    """
        Format the mail address to fit gmail's rfc interpretation
    """
    return u"<{0}>".format(mail)


def format_link(settings, link):
    """
    Format a link to fit the sender's domain name if a bounce url has been
    configured
    """
    bounce_url = settings.get("mail.bounce_url")
    if bounce_url:
        url = u"http://{0}/?url={1}".format(bounce_url, link)
    else:
        url = link
    return url


def _handle_optout(settings, mail_body):
    """
    Add additionnal datas for optout declaration
    Allows to fit a bit more the mailing conformity
    """
    headers = {}
    optout_addr = settings.get("mail.optout_address")
    instance_name = settings.get('autonomie.instance_name')
    if optout_addr and instance_name:
        headers['Precedence'] = 'bulk'
        headers['List-Unsubscribe'] = UNSUBSCRIBE_MSG.format(
                optout_addr,
                instance_name,
                )
        mail_body += UNSUBSCRIBE_LINK.format(optout_addr, instance_name)
    return headers, mail_body


def send_mail(event):
    """
        send a mail to dests with subject and body beeing set

        :param @event: an event object providing :
            The following methods :
                is_key_event : return True or False
                get_attachment : return an attachment object or None

            The following attributes:
                request : access to the current request object
                sendermail: the mail's sender
                recipients : list of recipients (a string)
                subject : the mail's subject
                body : the body of the mail
                settings : the app settings

    """
    if event.is_key_event():
        recipients = event.recipients
        if recipients:
            log.info(u"Sending an email to '{0}'".format(recipients))
            headers, mail_body = _handle_optout(event.settings, event.body)
            try:
                mailer = get_mailer(event.request)
                message = Message(subject=event.subject,
                      sender=event.sendermail,
                      recipients=recipients,
                      body=mail_body,
                      extra_headers=headers)
                attachment = event.get_attachment()
                if attachment:
                    message.attach(attachment)
                mailer.send_immediately(message)
            except:
                log.exception(u" - An error has occured while sending the \
email(s)")
