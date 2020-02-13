# -*- coding: UTF-8 -*-
"""A suite of unit tests for the Database object"""
import unittest
from unittest.mock import MagicMock, patch

import psycopg2

from vlab_quota.libs import database


class TestDatabase(unittest.TestCase):
    """A suite of tests for the vlab_quota.lib.database module"""

    def setUp(self):
        """Runs before every test case"""
        # mock away the psycopg2 module
        self.patcher = patch('vlab_quota.libs.database.psycopg2.connect')
        self.mocked_connection = MagicMock()
        self.mocked_cursor = MagicMock()
        self.mocked_connection.cursor.return_value = self.mocked_cursor
        self.mocked_conn = self.patcher.start()
        self.mocked_conn.return_value = self.mocked_connection

    def tearDown(self):
        """Runs after every test case"""
        self.patcher.stop()

    def test_init(self):
        """Simple test that we can instantiate Database class for testing"""
        db = database.Database()
        self.assertTrue(isinstance(db, database.Database))
        self.assertTrue(db._connection is self.mocked_connection)
        self.assertTrue(db._cursor is self.mocked_cursor)

    def test_context_manager(self):
        """Database support use of `with` statement and auto-closes connection"""
        with database.Database() as db:
            pass
        self.assertTrue(self.mocked_connection.close.call_count is 1)

    def test_close(self):
        """Calling Database.close() closes the connection to the DB"""
        db = database.Database()
        db.close()
        self.assertTrue(self.mocked_connection.close.call_count is 1)

    def test_execute(self):
        """Happy path test for the Database.execute method"""
        self.mocked_cursor.fetchall.return_value = []

        db = database.Database()
        result = db.execute(sql="SELECT * from FOO WHERE bar LIKE 'baz'")
        self.assertTrue(isinstance(result, list))

    def test_database_error(self):
        """``execute`` database.DatabaseError instead of psycopg2 errors"""
        self.mocked_cursor.execute.side_effect = psycopg2.Error('testing')

        db = database.Database()

        with self.assertRaises(database.DatabaseError):
            db.execute(sql="SELECT * from FOO WHERE bar LIKE 'baz'")

    def test_auto_rollback(self):
        """``execute`` auto rollsback the db connection upon error"""
        self.mocked_cursor.execute.side_effect = psycopg2.Error('testing')

        db = database.Database()
        try:
            db.execute(sql="SELECT * from FOO WHERE bar LIKE 'baz'")
        except database.DatabaseError:
            pass

        self.assertEqual(self.mocked_connection.rollback.call_count, 1)

    def test_no_results(self):
        """``execute`` returns an empty list when no query has no results"""
        self.mocked_cursor.description = None

        db = database.Database()
        result = db.execute(sql="SELECT * from FOO WHERE bar LIKE 'baz'")
        self.assertTrue(isinstance(result, list))

    def test_user_info(self):
        """``user_info`` returns a tuple"""
        fake_fetchall = MagicMock()
        fake_fetchall.return_value = [(1234, 5678)]
        db = database.Database()
        db._cursor.fetchall = fake_fetchall

        info = db.user_info('sally')
        expected = (1234, 5678)

        self.assertEqual(info, expected)

    def test_user_info_no_violations(self):
        """``user_info`` returns zero when the user has no quota violations"""
        fake_fetchall = MagicMock()
        fake_fetchall.return_value = []
        db = database.Database()
        db._cursor.fetchall = fake_fetchall

        exceeded_quota_epoch = db.user_info('sally')
        expected = (0, 0)

        self.assertEqual(exceeded_quota_epoch, expected)

    def test_remove_user(self):
        """``remove_user`` executes the expected SQL to delete a user"""
        db = database.Database()
        db.remove_user('nick')

        the_args, _ = db._cursor.execute.call_args
        sql = the_args[0]
        expected_sql = 'DELETE FROM quota_violations WHERE username LIKE (%s)'

        self.assertEqual(sql, expected_sql)

    def test_upsert_user(self):
        """``upsert_user`` Executes SQL that will create or update a user"""
        db = database.Database()
        db.upsert_user('nick', 100, 100)

        the_args, _ = db._cursor.execute.call_args
        sql = the_args[0]
        expected_sql = 'INSERT INTO quota_violations (username, triggered, last_notified)\n                 VALUES (%s, %s, %s)\n                 ON CONFLICT (username)\n                 DO UPDATE SET\n                    (triggered, last_notified)\n                    = (EXCLUDED.triggered, EXCLUDED.last_notified);\n        '

        self.assertEqual(sql, expected_sql)


if __name__ == '__main__':
    unittest.main()
