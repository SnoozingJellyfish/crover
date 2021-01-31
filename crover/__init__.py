from flask import Flask
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

def create_app(test_config=None):
    app = Flask(__name__, static_folder='figure')
    app.config.from_object('crover.config')

    if test_config:
        app.config.from_mapping(test_config)

    db.init_app(app)

    from crover.views.views import view
    app.register_blueprint(view)

    from crover.views import views

    return app


