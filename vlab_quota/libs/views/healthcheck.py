# -*- coding: UTF-8 -*-
"""
Enables Health checks for the Quota API
"""
import pkg_resources

import ujson
from flask_classy import FlaskView, Response

from vlab_quota.libs import const


class HealthView(FlaskView):
    """
    Simple end point to test if the service is alive
    """
    route_base = '/api/1/quota/healthcheck'
    trailing_slash = False

    def get(self):
        """End point for health checks"""
        resp = {}
        status = 200
        resp['version'] = pkg_resources.get_distribution('vlab-quotas').version
        response = Response(ujson.dumps(resp))
        response.status_code = status
        response.headers['Content-Type'] = 'application/json'
        return response
