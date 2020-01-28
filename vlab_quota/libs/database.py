# -*- coding: UTF-8 -*-
"""Abstracts the database and SQL"""
import psycopg2
from vlab_api_common import get_logger

from vlab_quota.libs import const


class Database:
    """TODO"""
    def __init__(self, user=const.DB_USER, password=const.DB_PASSWORD,
                 database=const.DB_DATABASE_NAME, host=const.DB_HOST):
        self.logger = get_logger(__name__, loglevel=const.QUOTA_LOG_LEVEL)
        self._connection = psycopg2.connect(database=database,
                                     host=host,
                                     user=user,
                                     password=password)
        self._cursor = self._connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._connection.close()

    def execute(self, sql, params=None):
        """Run a single SQL command

        :Returns: List

        :param sql: **Required** The SQL syntax to execute
        :type sql: String

        :param params: The values to use in a parameterized SQL query
        :type params: Iterable
        """
        try:
            self._cursor.execute(sql, params)
            self._connection.commit()
        except psycopg2.Error as doh:
            # All psycopg2 Exceptions are subclassed from psycopg2.Error
            self._connection.rollback()
            raise DatabaseError(message=doh.pgerror, pgcode=doh.pgcode)
        else:
            if self._cursor.description is None:
                return []
            else:
                return self._cursor.fetchall()

    def close(self):
        """Disconnect from the database"""
        self._connection.close()

    def user_info(self, username):
        """Obtain the EPOCH timestamp when a user exceeded their quota. A value
        of zero means there is no exceeded quota.

        :Returns: Integer

        :param username: The name of the user
        :type username: String
        """
        sql = """SELECT triggered FROM quota_violations WHERE username LIKE (%s);"""
        exceeded_on = self.execute(sql, (username,))
        self.logger.info(exceeded_on)
        if exceeded_on:
            return exceeded_on[0][0] # because it's a list of tuples, i.e. [(12345,)]
        return 0
