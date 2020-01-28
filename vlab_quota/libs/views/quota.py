# -*- coding: UTF-8 -*-
"""Defines the API for checking if a user has exceeded their inventory quota"""
import ujson
from flask_classy import request, Response
from vlab_api_common import BaseView, get_logger, describe, requires

from vlab_quota.libs import const, Database

logger = get_logger(__name__, loglevel=const.QUOTA_LOG_LEVEL)


class QuotaView(BaseView):
    """API end point for checking on quota violations"""
    route_base = '/api/1/inf/quota'
    GET_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                  "description": "Return quota information"
                 }

    @requires(verify=const.VLAB_VERIFY_TOKEN, verison=2)
    @describe(get=GET_SCHEMA)
    def get(self, *args, **kwargs):
        """Obtain quota information"""
        username = kwargs['token']['username']
        with Database() as db:
            exceeded_on = db.user_info(username)
        resp_data = {'exceeded_on': exceeded_on}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 200
        resp.headers.add('Link', '<{0}/api/1/inf/inventory>; rel=inventory'.format(const.VLAB_URL))
        return resp
