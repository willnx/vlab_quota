# -*- coding: UTF-8 -*-
"""A suite of unit tests for the healthcheck API end point"""
import unittest

from flask import Flask

from vlab_quota.libs.views import healthcheck


class TestHealthView(unittest.TestCase):
    """A set of test cases for the HealthView object"""

    @classmethod
    def setUp(cls):
        """Runs before every test case"""
        app = Flask(__name__)
        healthcheck.HealthView.register(app)
        app.config['TESTING'] = True
        cls.app = app.test_client()

    def test_health_check(self):
        """A simple test to verify the /api/1/quota/healthcheck end point works"""
        resp = self.app.get('/api/1/quota/healthcheck')

        expected = 200

        self.assertEqual(expected, resp.status_code)


if __name__ == '__main__':
    unittest.main()
