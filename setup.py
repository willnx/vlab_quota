#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from setuptools import setup, find_packages


setup(name="vlab-quotas",
      author="Nicholas Willhite",
      author_email='willnx84@gmail.com',
      version='2020.02.28',
      packages=find_packages(),
      include_package_data=True,
      package_files={'vlab_quotas' : ['app.ini']},
      description="A service that enforces inventory quotas for vLab",
      long_description=open('README.rst').read(),
      install_requires=['flask', 'psycopg2', 'pyjwt', 'uwsgi', 'vlab-api-common',
                        'ujson', 'cryptography', 'vlab-inf-common', 'ldap3']
      )
