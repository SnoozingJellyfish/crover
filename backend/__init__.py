import pickle
import logging
# フォーマットを定義
formatter = '%(levelname)s : %(asctime)s : %(message)s'
# ログレベルを INFO に変更
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

import numpy as np
from flask import Flask

#from views.views import view

LOCAL_ENV = False

if LOCAL_ENV:
    with open('backend/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)

    with open('backend/data/mecab_word2vec_dict_1d.pickle', 'rb') as f:
    #with open('backend/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
        word2vec = pickle.load(f)





def create_app():
    #app = Flask(__name__)
    app = Flask(__name__, static_folder='frontend/dist/static', template_folder='frontend/dist')

    app.config['DEBUG'] = LOCAL_ENV
    app.config['SECRET_KEY'] = 'session_key_' + str(np.random.randint(100000, 999999))

    app.register_blueprint(view)

    return app



