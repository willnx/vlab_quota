# -*- coding: UTF-8 -*-
"""For sending email notifications to users about quota violations"""
import ssl
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

import jinja2
from vlab_api_common.std_logger import get_logger

from vlab_quota.libs import const

log = get_logger(name=__name__, loglevel=const.QUOTA_LOG_LEVEL)


class NotifyError(Exception):
    def __init__(self, message, send_errors):
        super(NotifyError, self).__init__(message)
        self.send_errors = send_errors


def _get_ssl_context():
    """Defines what versions & ciphers to use when sending an email to the server

    :Returns: ssl.SSLContext
    """
    if const.QUOTA_EMAIL_SSL_VERIFY is False:
        log.debug('Not verifying SSL cert of SMTP server')
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.verify_mode = ssl.CERT_NONE
    else:
        context = ssl.create_default_context()
    return context


def _generate_warning(vm_count, exp_date, template='violation_warning.html'):
    """Create the HTML email body to warn users about a quota violation.

    :Returns: String

    :param vm_count: The number of VMs a user has.
    :type vm_count: Integer

    :param exp_date: When the soft quota grace period will expire (EPOCH).
    :type exp_date: Integer
    """
    with open(template) as the_file:
        template_data = the_file.read()
    vm_delta = vm_count - const.VLAB_QUOTA_LIMIT
    message = jinja2.Template(template_data).render(vm_quota=const.VLAB_QUOTA_LIMIT,
                                                    vm_count=vm_count,
                                                    vm_delta=vm_delta,
                                                    exp_date=datetime.fromtimestamp(exp_date, timezone.utc))
    return message


def _generate_follow_up(the_date, vms, template='delete_followup.html'):
    """Create the HTML email body stating what VMs were randomly deleted.

    :Returns: String

    :param the_date: The specific time when vLab randomly deleted a user's VM(s).
    :type the_date: Integer

    :param vms: The names of the VM(s) deleted.
    :type vms: List
    """
    with open(template) as the_file:
        template_data = the_file.read()
    message = jinja2.Template(template_data).render(the_date=datetime.fromtimestamp(the_date, timezone.utc),
                                                    vms=vms)
    return message


def _make_email(to, body):
    """Construct the email

    Returns: String

    :param to: The email address of the recipient.
    :type to: String

    :param body: The HTML content of the email.
    :type body: String
    """
    mail = MIMEMultipart('alternative')
    mail['Subject'] = 'vLab Quota Violation'
    mail['To'] = to
    mail['From'] = const.QUOTA_EMAIL_FROM_DOMAIN
    mail.attach(MIMEText(body, 'html'))
    return mail.as_string()


def _send_email(to, mail):
    """Connect to the SMTP server and send an email.

    :Returns: None

    :Raises: NotifyError

    :param to: The email address of the recipient.
    :type to: String

    :param mail: The constructed email to send
    :type mail: String
    """
    if const.QUOTA_EMAIL_SSL:
        log.debug('Sending email with SSL connection to server')
        mailer = smtplib.SMTP_SSL(const.QUOTA_EMAIL_SERVER, context=_get_ssl_context())
    else:
        log.debug("Sending email via clear text")
        mailer = smtplib.SMTP(const.QUOTA_EMAIL_SERVER)

    if const.QUOTA_EMAIL_USERNAME and const.QUOTA_EMAIL_PASSWORD:
        log.debug('Authenticating to SMTP server with user %s', const.QUOTA_EMAIL_USERNAME)
        mailer.login(const.QUOTA_EMAIL_USERNAME, const.QUOTA_EMAIL_PASSWORD)
    else:
        log.debug('Username & Password not provided, assuming no auth needed')

    if const.QUOTA_EMAIL_BCC:
        log.debug("BCCing %s", const.QUOTA_EMAIL_BCC)
        recipients = [to, const.QUOTA_EMAIL_BCC]
    else:
        recipients = [to]

    errors = None
    try:
        errors = mailer.sendmail(const.QUOTA_EMAIL_FROM_DOMAIN, recipients, mail)
    finally:
        mailer.close()

    if errors:
        raise NotifyError('Failure sending all emails', errors)


def send_warning(to, vm_count, exp_date):
    """Email the user letting them know when their soft-quota grace period will
    expire, and as a result, vLab will randomly delete VMs from their lab.

    :Returns: None

    :param to: The email address of the recipient.
    :type to: String

    :param vm_count: The number of VMs the user owns
    :type vm_count: Integer

    :param exp_date: The EPOCH timestamp when the grace period expires.
    :type exp_date: Integer
    """
    body = _generate_warning(vm_count, exp_date)
    mail = _make_email(to, body)
    _send_email(to, mail)


def send_follow_up(to, the_date, vms):
    """Email the user about the VMs that were deleted due to the grace period
    of their soft-quota expiring.

    :Returns: None

    :param to: The email address of the recipient.
    :type to: String

    :param the_date: The EPOCH timestamp when the VMs were deleted
    :type the_date: Integer

    :param vms: The VMs deleted
    :type vms: List
    """
    body = _generate_follow_up(the_date, vms)
    mail = _make_email(to, body)
    _send_email(to, mail)


def should_send_warning(violation_date, last_time_notified, grace_period=const.QUOTA_GRACE_PERIOD):
    """Determine if vLab should send a quota violation warning email.

    To [try and] avoid SPAMMing a user with emails, but send enough to remind them,
    the approach taken here is to send weekly emails until there's only 3 days
    left. When the grace period expires within 3 days, send daily emails.

    :Returns: Boolean

    :param violation_date: The EPOCH time when we first noticed the soft-quota had been exceeded.
    :type violation_date: Integer

    :param last_time_notified: The EPOCH time we last send a user a notification.
    :type last_time_notified: Integer

    :param grace_period: How long a soft-quota can be exceeded.
    :type grace_period: Intger
    """
    one_week = 604800
    one_day = 86400
    three_days = one_day * 3
    now = int(time.time())
    notify_delta = now - last_time_notified
    violation_delta = now - violation_date
    daily_spam = max(1, grace_period - violation_delta) <= three_days

    send_notification = False
    if last_time_notified == 0:
        send_notification = True
    elif violation_delta >= one_week and notify_delta >= one_week:
        send_notification = True
    elif daily_spam and notify_delta >= one_day:
        send_notification = True

    return send_notification
