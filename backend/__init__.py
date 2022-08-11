import os
import datetime as dt

# import numpy as np
from flask import Flask, render_template
from flask_restful import Api

from backend import view


def create_app():
    app = Flask(__name__)

    app = Flask(__name__, static_folder='../frontend/dist/static', template_folder='../frontend/dist')
    api = Api(app)
    api.add_resource(view.SearchTrend, '/trend')
    api.add_resource(view.SearchAnalyze, '/search_analyze')
    api.add_resource(view.SplitWc, '/split_wc')
    api.add_resource(view.LoadTweet, '/load_tweet')
    api.add_resource(view.BackCluster, '/back_cluster')

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
    @app.route('/<path:path>')
    def index(path):
        return render_template('index.html')

    app.permanent_session_lifetime = dt.timedelta(minutes=5)
    secret_key = os.urandom(24)
    # app.config['SECRET_KEY'] = str(np.random.randint(1000000, 9999999))
    app.secret_key = secret_key

    return app
    