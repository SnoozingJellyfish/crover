from flask import Flask
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

import pickle
import BytesIO

import logging
# フォーマットを定義
formatter = '%(levelname)s : %(asctime)s : %(message)s'

import cloudstorage
retryparams_instance = cloudstorage.RetryParams(initial_delay=0.2, max_delay=5.0, backoff_factor=2, max_retry_period=15)
cloudstorage.set_default_retry_params(retryparams_instance)
dict_all_count_obj = cloudstorage.open(filename='/crover_word2vec/all_1-200-000_word_count_sudachi.pickle', mode='rb', retry_params=retryparams_instance)
dict_all_count = pickle.load(BytesIO(dict_all_count_obj))
dict_all_count_obj.close()
print(type(dict_all_count))

# ログレベルを DEBUG に変更
logging.basicConfig(level=logging.INFO, format=formatter)

'''
with open('crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
    dict_all_count = pickle.load(f)

with open('crover/data/word_id.pickle', 'rb') as f:
    word_id = pickle.load(f)
'''

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


