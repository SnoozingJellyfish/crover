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

from google.cloud import storage

from sudachipy.config import set_default_dict_package

#import cloudstorage
#retryparams_instance = cloudstorage.RetryParams(initial_delay=0.2, max_delay=5.0, backoff_factor=2, max_retry_period=15)
#cloudstorage.set_default_retry_params(retryparams_instance)
#dict_all_count_obj = cloudstorage.open(filename='/word2vec_id/all_1-200-000_word_count_sudachi.pickle', mode='rb', retry_params=retryparams_instance)

server = False

if server:
    storage_client = storage.Client()

    def load_from_cloud(bucket_name, filename):
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        bytedata = blob.download_as_bytes()
        return pickle.load(BytesIO(bytedata))

    bucket_name = os.environ.get('BUCKET_NAME')
    #bucket_name = os.environ.get('GOOGLE_CLOUD_PROJECT')
    dict_all_count = load_from_cloud(bucket_name, os.environ.get('DICT_ALL_COUNT'))
    word2vec = {}
    for i in range(9):
        wv = load_from_cloud(bucket_name, os.environ.get('WORD2VEC') + str(i+1) + '.pickle')
        word2vec.update(wv)
    print(type(dict_all_count))

    # ログレベルを DEBUG に変更
    logging.basicConfig(level=logging.INFO, format=formatter)

    dst_path = set_default_dict_package('sudachidict_full', sys.stdout)

else: # local
    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)

    with open('C:/Users/直也/Documents/twitter_analysis/crover_application/crover/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
        word2vec = pickle.load(f)
        #pass



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


