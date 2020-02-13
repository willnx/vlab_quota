# -*- coding: UTF-8 -*-
"""A suite of unit tests for the ``worker.py`` module"""
import time
import unittest
from unittest.mock import patch, MagicMock

from vlab_quota import worker


class TestGetViolators(unittest.TestCase):
    """A suite of test cases for the ``_get_violators`` function"""
    @classmethod
    def setUp(cls):
        """Runs once before every test case"""
        fake_user1 = MagicMock()
        fake_user1.name = 'bill'
        fake_user1.childEntity = [1,2,3,4]
        cls.fake_user1 = fake_user1
        fake_user2 = MagicMock()
        fake_user2.name = 'lisa'
        fake_user2.childEntity = [1,2,3,4]
        cls.fake_user2 = fake_user2
        fake_user3 = MagicMock()
        fake_user3.name = 'zed'
        fake_user3.childEntity = [1,2,3,4]
        cls.fake_user3 = fake_user3
        fake_users = MagicMock()
        fake_users.__iter__.return_value = [fake_user1, fake_user2, fake_user3]
        vcenter = MagicMock()
        vcenter.get_by_name.return_value = fake_users
        cls.vcenter = vcenter

    @patch.object(worker, 'const')
    def test_return_type(self, fake_const):
        """``_get_violators`` returns a dictionary of username to VM count for users exceeding the quota limit"""
        fake_const.VLAB_QUOTA_LIMIT = 2
        violators = worker._get_violators(self.vcenter)
        expected = {'bill': 4, 'lisa': 4, 'zed': 4}

        self.assertEqual(violators, expected)

    @patch.object(worker, 'const')
    def test_account_for_default_gateway(self, fake_const):
        """``_get_violators`` doesn't count the defaultGateway towards the quota limit"""
        fake_const.VLAB_QUOTA_LIMIT = 3 # The setUp creates 4 VMs per user
        violators = worker._get_violators(self.vcenter)
        expected = {}

        self.assertEqual(violators, expected)


@patch.object(worker, 'const')
class TestGracePeriodExceeded(unittest.TestCase):
    """A suite of test cases for the ``_grace_period_exceeded`` function"""

    def test_boolean(self, fake_const):
        """``_grace_period_exceeded`` returns a boolean"""
        fake_const.QUOTA_GRACE_PERIOD = 7
        answer = worker._grace_period_exceeded(violation_date=1234)

        self.assertTrue(isinstance(answer, bool))

    def test_is_true(self, fake_const):
        """``_grace_period_exceeded`` returns True when the grace period has expired"""
        fake_const.QUOTA_GRACE_PERIOD = 7
        answer = worker._grace_period_exceeded(violation_date=1234)

        self.assertTrue(answer)

    def test_is_true(self, fake_const):
        """``_grace_period_exceeded`` returns False when the grace period has not expired"""
        fake_const.QUOTA_GRACE_PERIOD = 7
        answer = worker._grace_period_exceeded(violation_date=1234123412341234)

        self.assertFalse(answer)


class TestGetUserEmail(unittest.TestCase):
    """A suite of test cases for the ``_get_user_email`` function"""
    @classmethod
    def setUp(cls):
        """Runs once before every test case"""
        cls.fake_entry = MagicMock()
        cls.ldap_conn = MagicMock()
        cls.ldap_conn.entries = [cls.fake_entry]

    def test_finds_email(self):
        """``_get_user_email`` returns the user's email from AD/LDAP"""
        self.fake_entry.__getitem__.return_value.value = 'some@email.com'
        email = worker._get_user_email('phill', self.ldap_conn)
        expected = 'some@email.com'

        self.assertEqual(email, expected)

    def test_raises_runtime_error(self):
        """``_get_user_email``raises RuntimeError if user is not found"""
        self.ldap_conn.entries = []

        with self.assertRaises(RuntimeError):
            worker._get_user_email('phill', self.ldap_conn)

    def test_searches_for_email(self):
        """``_get_user_email`` searches for the correct email attribute"""
        worker._get_user_email('phill', self.ldap_conn)

        _, the_kwargs = self.ldap_conn.search.call_args
        searched_attribute = the_kwargs['attributes']
        expected = ['mail']

        self.assertEqual(searched_attribute, expected)


class TestGetLdapPassword(unittest.TestCase):
    """A suite of test cases for the ``_get_ldap_password`` function"""

    def test_no_location(self):
        """``_get_ldap_password`` raises RuntimeError if no locaiton is provided"""
        with self.assertRaises(RuntimeError):
            worker._get_ldap_password(location=None)

    @patch.object(worker, 'open')
    def test_returns_string(self, fake_open):
        """``_get_ldap_password`` returns a string"""
        fake_open.return_value.__enter__.return_value.read.return_value.strip.return_value = 'woot'

        secret = worker._get_ldap_password()
        expected = 'woot'

        self.assertEqual(secret, expected)


@patch.object(worker.ldap3, 'Connection')
@patch.object(worker, '_get_ldap_password')
class TestGetLdapConn(unittest.TestCase):
    """A suite of test cases for the ``_get_ldap_conn`` function"""
    def test_get_ldap_conn(self, fale_get_ldap_password, fake_Connection):
        """``_get_ldap_conn`` returns a bound LDAP connection"""
        worker._get_ldap_conn()

        _, the_kwargs = fake_Connection.call_args
        auto_bind_value = the_kwargs['auto_bind']
        expected = True

        self.assertEqual(auto_bind_value, expected)


@patch.object(worker.notify, 'send_warning')
@patch.object(worker.notify, 'send_follow_up')
@patch.object(worker, '_get_violators')
@patch.object(worker, 'log')
class TestEnforceQuotas(unittest.TestCase):
    """A suite of test cases for the ``_enforce_quotas`` function"""
    @classmethod
    def setUp(cls):
        cls.vcenter = MagicMock()
        cls.db = MagicMock()
        cls.ldap_conn = MagicMock()

    @patch.object(worker, 'destroy_vms')
    def test_delets_vms(self, fake_destroy_vms, fake_log, fake_get_violators, fake_send_follow_up, fake_send_warning):
        """``_enforce_quotas`` Deletes VMs when the grace period expires"""
        self.db.user_info.return_value = (100, 100)
        fake_get_violators.return_value = {'bob': 8, 'lisa': 3}

        worker._enforce_quotas(self.vcenter, self.db, self.ldap_conn)

        self.assertTrue(fake_destroy_vms.called)

    @patch.object(worker, 'destroy_vms')
    def test_delets_vms_follow_up(self, fake_destroy_vms, fake_log, fake_get_violators, fake_send_follow_up, fake_send_warning):
        """``_enforce_quotas`` Sends a follow up email after deleting VMs"""
        self.db.user_info.return_value = (100, 100)
        fake_get_violators.return_value = {'bob': 8, 'lisa': 3}

        worker._enforce_quotas(self.vcenter, self.db, self.ldap_conn)

        self.assertTrue(fake_send_follow_up.called)

    @patch.object(worker, 'destroy_vms')
    def test_delets_vms_db_cleanup(self, fake_destroy_vms, fake_log, fake_get_violators, fake_send_follow_up, fake_send_warning):
        """``_enforce_quotas`` Removes the user from the DB after deleting VMs"""
        self.db.user_info.return_value = (100, 100)
        fake_get_violators.return_value = {'bob': 8, 'lisa': 3}

        worker._enforce_quotas(self.vcenter, self.db, self.ldap_conn)

        self.assertTrue(self.db.remove_user.called)

    def test_send_warning(self, fake_log, fake_get_violators, fake_send_follow_up, fake_send_warning):
        """``_enforce_quotas`` Sends a warning email if enough time has passed since the last notification"""
        violation_date = (int(time.time()) - worker.const.QUOTA_GRACE_PERIOD) + 100
        last_time_notified = violation_date
        self.db.user_info.return_value = (violation_date, last_time_notified)
        fake_get_violators.return_value = {'bob': 8, 'lisa': 3}

        worker._enforce_quotas(self.vcenter, self.db, self.ldap_conn)

        self.assertTrue(fake_send_warning.called)

    @patch.object(worker.time, 'time')
    def test_set_violation_date(self, fake_time, fake_log, fake_get_violators, fake_send_follow_up, fake_send_warning):
        """``_enforce_quotas`` sets the violation_date if this the first time the user has been detected"""
        fake_time.return_value = 9001
        self.db.user_info.return_value = (0, 0)
        fake_get_violators.return_value = {'bob': 8, 'lisa': 3}

        worker._enforce_quotas(self.vcenter, self.db, self.ldap_conn)

        the_args, _ = self.db.upsert_user.call_args
        violation_date = the_args[1]
        expected = 9001

        self.assertEqual(violation_date, expected)


@patch.object(worker, '_enforce_quotas')
@patch.object(worker, 'Database')
@patch.object(worker, '_get_ldap_conn')
@patch.object(worker, 'vCenter')
@patch.object(worker, 'log')
@patch.object(worker.time, 'sleep')
class TestMain(unittest.TestCase):
    """A suite of test cases for the ``main`` function"""
    # Raising RuntimeError in the test allows for the test to break the
    # while True loop of ``main``.

    def notest_enforce_quotas(self, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` calls ``_enforce_quotas``"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise

        self.assertTrue(fake_enforce_quotas.called)

    @patch.object(worker.time, 'time')
    def notest_loop_sleep_positive(self, fake_time, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` sleeps for a positive value between zero and LOOP_INTERVAL"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        loop_takes = int(worker.LOOP_INTERVAL / 2 ) + 100
        # Need 4 to mock until the sleep side_effect
        fake_time.side_effect = [100, loop_takes, loop_takes + 5, loop_takes + 10]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise
        postive_sleep = fake_sleep.call_args[0][0] >= 0

        self.assertTrue(postive_sleep)

    @patch.object(worker.time, 'time')
    def test_loop_sleep_negitive(self, fake_time, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` the sleep at the end of the loop is always positive, even if the clock moves backwards"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        loop_takes = int(worker.LOOP_INTERVAL * 2 ) + 100
        # Need 4 to mock until the sleep side_effect
        fake_time.side_effect = [100, 95, 85, 75]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise
        first_sleep = fake_sleep.call_args_list[0][0][0]
        expected = 10

        self.assertEqual(first_sleep, expected)

    @patch.object(worker.time, 'time')
    def notest_loop_sleep_zero(self, fake_time, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` doesn't pause if enforcing quotas takes longer than the loop interval"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        loop_takes = int(worker.LOOP_INTERVAL * 2 ) + 100
        # Need 4 to mock until the sleep side_effect
        fake_time.side_effect = [100, loop_takes, loop_takes + 5, loop_takes + 10]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise
        first_sleep = fake_sleep.call_args_list[0][0][0]
        expected = 0

        self.assertEqual(first_sleep, expected)

    @patch.object(worker.atexit, 'register')
    def notest_closes_vcenter(self, fake_register, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` closes vCenter connection when the script exits"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise

        all_args = fake_register.call_args_list
        closes_vcenter = fake_vCenter.return_value.close in [x[0][0] for x in all_args]

        self.assertTrue(closes_vcenter)

    @patch.object(worker.atexit, 'register')
    def notest_closes_db(self, fake_register, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` closes Database connection when the script exits"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise

        all_args = fake_register.call_args_list
        closes_db = fake_Database.return_value.close in [x[0][0] for x in all_args]

        self.assertTrue(closes_db)

    @patch.object(worker.atexit, 'register')
    def notest_closes_ldap(self, fake_register, fake_sleep, fake_log, fake_vCenter, fake_get_ldap_conn, fake_Database, fake_enforce_quotas):
        """``main`` closes LDAP connection when the script exits"""
        fake_sleep.side_effect = [None, RuntimeError('testing')]
        try:
            worker.main()
        except RuntimeError as doh:
            if '{}'.format(doh) == 'testing':
                pass
            else:
                raise

        all_args = fake_register.call_args_list
        closes_ldap = fake_get_ldap_conn.return_value.unbind in [x[0][0] for x in all_args]

        self.assertTrue(closes_ldap)



if __name__ == "__main__":
    unittest.main()
