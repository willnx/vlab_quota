# -*- coding: UTF-8 -*-
"""A suite of unit tests for the constants.py module"""
import unittest

from vlab_quota.libs import const


class TestConsts(unittest.TestCase):
    """A suite of test cases for the ``const`` object"""
    def test_has_expected_attributes(self):
        """``const`` has all expected attributes"""
        found = [x for x in dir(const) if x.isupper() and not x.startswith('_')]
        expected = ['DB_DATABASE_NAME',
                    'DB_HOST',
                    'DB_PASSWORD',
                    'DB_USER',
                    'INF_VCENTER_PASSWORD',
                    'INF_VCENTER_PORT',
                    'INF_VCENTER_SERVER',
                    'INF_VCENTER_USER',
                    'QUOTA_LOG_LEVEL',
                    'VLAB_URL',
                    'VLAB_VERIFY_TOKEN']

        # set() avoids false positives due to ordering
        self.assertEqual(set(found), set(expected))


if __name__ == '__main__':
    unittest.main()
