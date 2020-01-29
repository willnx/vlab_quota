# -*- coding: UTF-8 -*-
"""A suite of unit tests for the RESTful API schemas"""
import unittest

from jsonschema import Draft4Validator, validate, ValidationError
from vlab_quota.libs.views import quota


class TestQuotaViewSchema(unittest.TestCase):
    """A set of test cases of /api/1/quota"""

    def test_get_schema(self):
        """The schema defined for GET is valid"""
        try:
            Draft4Validator.check_schema(quota.QuotaView.GET_SCHEMA)
            schema_valid = True
        except RuntimeError:
            schema_valid = False

        self.assertTrue(schema_valid)


if __name__ == '__main__':
    unittest.main()
