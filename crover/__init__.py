from flask import Flask
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

import os
import sys
import pickle
from io import BytesIO

import logging
# フォーマットを定義
formatter = '%(levelname)s : %(asctime)s : %(message)s'
# ログレベルを DEBUG に変更
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

from google.cloud import storage

#from sudachipy.config import set_default_dict_package

#import cloudstorage
#retryparams_instance = cloudstorage.RetryParams(initial_delay=0.2, max_delay=5.0, backoff_factor=2, max_retry_period=15)
#cloudstorage.set_default_retry_params(retryparams_instance)
#dict_all_count_obj = cloudstorage.open(filename='/word2vec_id/all_1-200-000_word_count_sudachi.pickle', mode='rb', retry_params=retryparams_instance)

def download_from_cloud(storage_client, bucket_name, filename):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    bytedata = blob.download_as_bytes()
    return pickle.load(BytesIO(bytedata))

def upload_to_cloud(storage_client, bucket_name, filename, bytedata):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(bytedata)

LOCAL_ENV = False

if LOCAL_ENV:
    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)

    #with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/mecab_word2vec_dict_1d.pickle', 'rb') as f:
        word2vec = pickle.load(f)
        #pass

def create_app(test_config=None):
    app = Flask(__name__, static_folder='figure')
    app.config.from_object('crover.config')

    app.config['SECRET_KEY'] = 'secret_key' # add

    if test_config:
        app.config.from_mapping(test_config)

    db.init_app(app)

    from crover.views.views import view
    app.register_blueprint(view)

    from crover.views import views

    return app


