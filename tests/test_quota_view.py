# -*- coding: UTF-8 -*-
"""A suite of unit tests for the QuotaView object"""
import unittest
from unittest.mock import patch, MagicMock

import ujson
from flask import Flask
from vlab_api_common import flask_common
from vlab_api_common.http_auth import generate_v2_test_token

from vlab_quota.libs.views import quota


class TestQuotaView(unittest.TestCase):
    """A suite of test cases for the QuotaView object"""
    @classmethod
    def setUpClass(cls):
        """Runs once for the whole test suite"""
        cls.token = generate_v2_test_token(username='sally')

    @classmethod
    def setUp(cls):
        """Run before every test case"""
        app = Flask(__name__)
        quota.QuotaView.register(app)
        cls.app = app.test_client()

    @patch.object(quota, 'Database')
    def test_foo(self, fake_Database):
        """QuotaView - GET on /api/1/quota returns the expected JSON response"""
        fake_Database.return_value.__enter__.return_value.user_info.return_value = 0
        resp = self.app.get('/api/1/quota',
                            headers={'X-Auth' : self.token})
        expected = {'error': None, 'content': { 'exceeded_on': None }, 'params': {}}



if __name__ == '__main__':
    unittest.main()
