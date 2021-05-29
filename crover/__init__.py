from flask import Flask, session
#from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
#db = SQLAlchemy()

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

import numpy as np

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
else:
    pass
    '''
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]
    db_socket_dir = os.environ.get("DB_SOCKET_DIR", "/cloudsql")
    cloud_sql_connection_name = os.environ["CLOUD_SQL_CONNECTION_NAME"]

    # Extract host and port from db_host
    host_args = db_host.split(":")
    db_hostname, db_port = host_args[0], int(host_args[1])

    engine = sqlalchemy.create_engine(
        # Equivalent URL:
        # mysql+pymysql://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL(
            drivername="mysql+pymysql",
            username=db_user,  # e.g. "my-database-user"
            password=db_pass,  # e.g. "my-database-password"
            host=db_hostname,  # e.g. "127.0.0.1" # internal IP
            port=db_port,  # e.g. 3306 # internal IP
            database=db_name,  # e.g. "my-database-name"
            query={
                #"unix_socket": "{}/{}".format(
                #    db_socket_dir,  # e.g. "/cloudsql"
                #    cloud_sql_connection_name), # i.e "<PROJECT-NAME>:<INSTANCE-REGION>:<INSTANCE-NAME>"
                "charset": "utf8mb4"
            }
        )
    )

    db_session = scoped_session(sessionmaker(bind=engine))
    Base = declarative_base()
    Base.query = db_session.query_property()
    import crover.models
    #Base.metadata.create_all(bind=engine)
    '''
    
def create_app(test_config=None):
    app = Flask(__name__, static_folder='figure')
    app.config.from_object('crover.config')

    app.config['SECRET_KEY'] = 'session_key_' + str(np.random.randint(100000, 999999))


    if test_config:
        app.config.from_mapping(test_config)

    #db.init_app(app)


    from crover.views.views import view
    app.register_blueprint(view)

    from crover.views import views

    return app
