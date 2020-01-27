# -*- coding: UTF-8 -*-
from flask import Flask

from vlab_quota.libs import const
from vlab_quota.libs.views import HealthView

app = Flask(__name__)

HealthView.register(app)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
