# -*- coding: UTF-8 -*-
import socket
from os import environ
from collections import namedtuple, OrderedDict


DEFINED = OrderedDict([
            ('VLAB_URL', environ.get('VLAB_URL', 'https://localhost')),
            ('QUOTA_LOG_LEVEL', environ.get('QUOTA_LOG_LEVEL', 'INFO')),
            ('INF_VCENTER_SERVER', environ.get('INF_VCENTER_SERVER', 'localhost')),
            ('INF_VCENTER_PORT', int(environ.get('INFO_VCENTER_PORT', 443))),
            ('INF_VCENTER_USER', environ.get('INF_VCENTER_USER', 'tester')),
            ('INF_VCENTER_PASSWORD', environ.get('INF_VCENTER_PASSWORD', 'a')),
            ('DB_USER', environ.get('DB_USER', 'postgres')),
            ('DB_PASSWORD', environ.get('DB_PASSWORD', 'testing')),
            ('DB_DATABASE_NAME', environ.get('DB_DATABASE_NAME', 'quota')),
            ('DB_HOST', environ.get('DB_HOST', 'quota-db')),
            ('VLAB_VERIFY_TOKEN', environ.get('VLAB_VERIFY_TOKEN', False)),
            ('VLAB_QUOTA_LIMIT', int(environ.get('VLAB_QUOTA_LIMIT', 30))),
            ('QUOTA_GRACE_PERIOD', int(environ.get('QUOTA_GRACE_PERIOD', 1209600))), # 2 weeks, in seconds
            ('QUOTA_EMAIL_SERVER', environ.get('QUOTA_EMAIL_SERVER', 'localhost')),
            ('QUOTA_EMAIL_FROM_DOMAIN', 'noreply@{}'.format(environ.get('QUOTA_EMAIL_FROM_DOMAIN', 'vlab.local'))),
            ('QUOTA_EMAIL_BCC', environ.get('QUOTA_EMAIL_BCC', '')),
            ('QUOTA_EMAIL_SSL', environ.get('QUOTA_EMAIL_SSL', False)),
            ('QUOTA_EMAIL_SSL_VERIFY', environ.get('QUOTA_EMAIL_SSL_VERIFY', False)),
            ('QUOTA_EMAIL_USERNAME', environ.get('QUOTA_EMAIL_USERNAME', '')),
            ('QUOTA_EMAIL_PASSWORD', environ.get('QUOTA_EMAIL_PASSWORD', '')),
          ])

Constants = namedtuple('Constants', list(DEFINED.keys()))

# The '*' expands the list, just liked passing a function *args
const = Constants(*list(DEFINED.values()))
