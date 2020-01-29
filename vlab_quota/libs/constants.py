# -*- coding: UTF-8 -*-
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
          ])

Constants = namedtuple('Constants', list(DEFINED.keys()))

# The '*' expands the list, just liked passing a function *args
const = Constants(*list(DEFINED.values()))
