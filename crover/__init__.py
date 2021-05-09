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

from google.cloud import storage

from sudachipy.config import set_default_dict_package

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

IS_SERVER = True

if IS_SERVER:
    storage_client = storage.Client()

    bucket_name = os.environ.get('BUCKET_NAME')
    dict_all_count = download_from_cloud(storage_client, bucket_name, os.environ.get('DICT_ALL_COUNT'))

    word2vec = {}
    for i in range(9):
        wv = download_from_cloud(storage_client, bucket_name, os.environ.get('WORD2VEC') + str(i+1) + '.pickle')
        word2vec.update(wv)


    mlask_emotion_dictionary = download_from_cloud(storage_client, bucket_name, os.environ.get('MLASK_EMOTION_DICTIONARY'))

    dst_path = set_default_dict_package('sudachidict_full', sys.stdout)


else: # local
    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)

    #with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/mecab_word2vec_dict_1d.pickle', 'rb') as f:
        word2vec = pickle.load(f)
        #pass

    with open('crover/data/mlask_emotion_dictionary.pickle', 'rb') as f:
        mlask_emotion_dictionary = pickle.load(f)

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


