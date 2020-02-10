# -*- coding: UTF-8 -*-
"""A suite of unit tests for the ``notify.py`` module"""
import unittest
from unittest.mock import patch, MagicMock

from vlab_quota.libs import notify


@patch.object(notify, 'log') # cuts down on SPAM output
class TestGetSslContext(unittest.TestCase):
    """A suite of test cases for the ``_get_ssl_context`` function"""
    def test_ssl_context_type(self, fake_log):
        """``_get_ssl_context`` returns the expected object type"""
        context = notify._get_ssl_context()

        self.assertTrue(isinstance(context, notify.ssl.SSLContext))

    @patch.object(notify, 'const')
    def test_no_verify(self, fake_const, fake_log):
        """``_get_ssl_context`` does not verify the host cert when ``const.QUOTA_EMAIL_SSL_VERIFY`` is False"""
        fake_const.QUOTA_EMAIL_SSL_VERIFY = False

        context = notify._get_ssl_context()

        self.assertEqual(context.verify_mode, notify.ssl.CERT_NONE)

    @patch.object(notify, 'const')
    def test_verify_cert(self, fake_const, fake_log):
        """``_get_ssl_context`` will verify the host cert when ``const.QUOTA_EMAIL_SSL_VERIFY`` is not False"""
        fake_const.QUOTA_EMAIL_SSL_VERIFY = 'anything'

        context = notify._get_ssl_context()

        self.assertEqual(context.verify_mode, notify.ssl.CERT_REQUIRED)


class TestGenerateWarning(unittest.TestCase):
    """A suite of test cases for the ``_generate_warning`` function"""
    TEMPLATE = """
        <html>
          <body style="font-family:Helvetica;">
           <div style="background:blue">
             <h1 style="color:white;margin-left:5px">vLab</h1>
           </div>
           <h2 style="color:red;font-weight:bold">Quota Violation</h2>
           <p>You currently have {{ vm_quota }} VMs.<br>
              You are allowed to have {{ vm_count }} VMs.<br><br>

              If you do not <b>delete {{ vm_delta }} VMs by {{ exp_date }}</b>, vLab will randomly choose which VMs <br>
              to delete on that date.<br><br>

              You have been warned.
           </p>
          </body>
        </html>
    """

    @patch.object(notify, 'open')
    def test_generate_warning(self, fake_open):
        """``_generate_warning`` returns a string"""
        fake_open.return_value.__enter__.return_value.read.return_value = self.TEMPLATE
        message = notify._generate_warning(9001, 1234)

        self.assertTrue(isinstance(message, str))


class TestGenerateFollowUp(unittest.TestCase):
    """A suite of test cases for the ``_generate_follow_up`` function"""
    TEMPLATE = """
        <html>
          <body style="font-family:Helvetica;">
           <div style="background:blue">
             <h1 style="color:white;margin-left:5px">vLab</h1>
           </div>
           <h2 style="color:red;font-weight:bold">Quota Violation</h2>
           <p>On {{ date }} vLab deleted the following VMs:</p>
           <ul>
            {% for vm in vms %}
            <li>{{ vm }}</li>
            {% endfor %}
           </ul>
           <p>These VMs were randomly choosen, and were deleted due to the soft-quota
            grace period expiring.
           </p>
          </body>
        </html>
    """
    @patch.object(notify, 'open')
    def test_generate_follow_up_html(self, fake_open):
        """``_generate_follow_up`` returns a string"""
        fake_open.return_value.__enter__.return_value.read.return_value = self.TEMPLATE
        message = notify._generate_follow_up(1234, ['vmFoo', 'vmBar'])

        self.assertTrue(isinstance(message, str))


class TestMakeEmail(unittest.TestCase):
    """A suite of test cases for the ``_make_email`` function"""

    def test_return_type(self):
        """``_make_email`` Returns a string that is the full email to send"""
        mail = notify._make_email('bob@vlab.local', 'some email body')

        self.assertTrue(isinstance(mail, str))


@patch.object(notify, 'const')
@patch.object(notify, 'log')
class TestSendEmail(unittest.TestCase):
    """A suite of test cases for the ``_send_email`` function"""

    @patch.object(notify.smtplib, 'SMTP_SSL')
    def test_ssl(self, fake_SMTP_SSL, fake_log, fake_const):
        """``_send_email`` can send emails via SSL"""
        fake_const.QUOTA_EMAIL_SSL = True
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP_SSL.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')

        self.assertTrue(fake_mailer.sendmail.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_cleartext(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` can send emails via clear text"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')

        self.assertTrue(fake_mailer.sendmail.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_login(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` Attempts to login when username and password are defined"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')
        # const.QUOTA_EMAIL_USERNAME and const.QUOTA_EMAIL_PASSWORD are implictly
        # true because of the mock/patch
        self.assertTrue(fake_mailer.login.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_login_no_user(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` does not attempt to login when no username is defined"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_const.QUOTA_EMAIL_USERNAME = ''
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')

        self.assertFalse(fake_mailer.login.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_login_no_password(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` does not attempt to login when no password is defined"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_const.QUOTA_EMAIL_PASSWORD = ''
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')

        self.assertFalse(fake_mailer.login.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_bcc(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` will BCC an email if it's defined"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_const.QUOTA_EMAIL_BCC = 'jill@vlab.local'
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')
        the_args, _ = fake_mailer.sendmail.call_args
        sent_to = the_args[1]
        expected = ['jill@vlab.local', 'sally@vlab.local']
        # set() avoids false positive due to ordering
        self.assertEqual(set(sent_to), set(expected))

    @patch.object(notify.smtplib, 'SMTP')
    def test_no_bcc(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` will not BCC an email if it is not defined"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_const.QUOTA_EMAIL_BCC = ''
        fake_mailer = MagicMock()
        fake_mailer.sendmail.return_value = None
        fake_SMTP.return_value = fake_mailer

        notify._send_email('sally@vlab.local', 'some email')
        the_args, _ = fake_mailer.sendmail.call_args
        sent_to = the_args[1]
        expected = ['sally@vlab.local']

        self.assertEqual(sent_to, expected)

    @patch.object(notify.smtplib, 'SMTP')
    def test_always_closes(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` closes the server connection, even upon error"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_mailer = MagicMock()
        fake_SMTP.return_value = fake_mailer
        fake_mailer.sendmail.side_effect = [RuntimeError('testing')]

        try:
            notify._send_email('sally@vlab.local', 'some email')
        except RuntimeError:
            pass

        self.assertTrue(fake_mailer.close.called)

    @patch.object(notify.smtplib, 'SMTP')
    def test_raises_erorrs(self, fake_SMTP, fake_log, fake_const):
        """``_send_email`` Raises NotifyError if sending email fails"""
        fake_const.QUOTA_EMAIL_SSL = False
        fake_mailer = MagicMock()
        fake_SMTP.return_value = fake_mailer
        fake_mailer.sendmail.return_value = {'salldy@vlab.local', (500, "no such user")}

        with self.assertRaises(notify.NotifyError):
            notify._send_email('salldy@vlab.local', 'asdfwed')


class TestSendWarning(unittest.TestCase):
    """A suite of test cases for the ``send_warning`` function"""
    @patch.object(notify, '_generate_warning')
    @patch.object(notify, '_make_email')
    @patch.object(notify, '_send_email')
    def test_send_warning(self, fake_generate_warning, fake_make_email, fake_send_email):
        """``send_warning`` constructs the correct email, and sends it"""
        notify.send_warning('bob@vlab.local', 45, 123456789)

        self.assertTrue(fake_generate_warning.called)
        self.assertTrue(fake_make_email.called)
        self.assertTrue(fake_send_email.called)


class TestSendFollowUp(unittest.TestCase):
    """A suite of test cases for the ``send_warning`` function"""
    @patch.object(notify, '_generate_follow_up')
    @patch.object(notify, '_make_email')
    @patch.object(notify, '_send_email')
    def test_send_follow_up(self, fake_generate_follow_up, fake_make_email, fake_send_email):
        """``send_follow_up`` constructs the correct email, and sends it"""
        notify.send_follow_up('bob@vlab.local', 45, 123456789)

        self.assertTrue(fake_generate_follow_up.called)
        self.assertTrue(fake_make_email.called)
        self.assertTrue(fake_send_email.called)


if __name__ == '__main__':
    unittest.main()
