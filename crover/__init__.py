
import pickle
from io import BytesIO
import logging
# フォーマットを定義
formatter = '%(levelname)s : %(asctime)s : %(message)s'
# ログレベルを INFO に変更
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

import numpy as np

from flask import Flask

LOCAL_ENV = False


if LOCAL_ENV:
    with open('crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)

    with open('crover/data/mecab_word2vec_dict_1d.pickle', 'rb') as f:
    #with open('crover/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
        word2vec = pickle.load(f)


def create_app():
    app = Flask(__name__)
    app.config['DEBUG'] = LOCAL_ENV
    app.config['SECRET_KEY'] = 'session_key_' + str(np.random.randint(100000, 999999))

    from crover.views.views import view
    app.register_blueprint(view)
    from crover.views import views

    return app



