import io
import base64
import os
import copy
import logging
from datetime import datetime

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from flask import request, redirect, url_for, render_template, flash, session, make_response, jsonify
from flask import current_app as app
from flask import Blueprint
from google.cloud import storage

from crover import LOCAL_ENV, download_from_cloud, upload_to_cloud
from crover.process.preprocess import preprocess_all, make_top_word2vec_dic, make_part_word2vec_dic, make_top_word2vec_dic_datastore
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
#from crover.models.tweet import Tweet, WordCount, ClusterTweet

view = Blueprint('view', __name__)
logger = logging.getLogger(__name__)

sess_info = {}  # global variable containing recent session information

@view.route('/')
def home():
    return render_template('index.html', sess_info_at='first')  # ナビゲーションバーなし

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    global sess_info

    # ツイートを取得しワード数をカウントする
    if request.method == 'POST':
        # ユーザーの直前のセッションの情報を削除
        if 'searched_at' in session and session['searched_at'] in sess_info:
            del sess_info[session['searched_at']]
        # セッションを区別するタイムスタンプを設定
        session['searched_at'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        logger.info(session['searched_at'])
        searched_at_list = list(sess_info.keys())
        logger.info('count of remembered session: ' + str(len(searched_at_list)))
        # 記憶する直近のセッションを10個以内にする
        if len(searched_at_list) > 10:
            del sess_info[sorted(searched_at_list)[0]]
        sess_info[session['searched_at']] = {}
        sess_info_at = sess_info[session['searched_at']]

        keyword = request.form['keyword']
        sess_info_at['keyword'] = keyword
        max_tweets = int(request.form['tweet_num'])
        sess_info_at['tweet_num'] = max_tweets
        #word_num = int(request.form['word_num'])
        word_num = 100
        split_num = request.form['keyword'].split(',')
        datastore_upload_wv(int(split_num[0]), int(split_num[1]))

        # ツイート取得、ワードカウント
        dict_word_count_rate, tweets_list, time_hist = preprocess_all(keyword, max_tweets, word_num)
        sess_info_at['tweets'] = tweets_list
        sess_info_at['word_counts'] = list(dict_word_count_rate.items())
        cluster_to_words = [{0: dict_word_count_rate}]
        sess_info_at['cluster_to_words'] = cluster_to_words
        figures = make_word_cloud(cluster_to_words[0])

        sess_info_at['figures_dictword'] = figures
        sess_info_at['figure_time_hist'] = time_hist
        sess_info_at['figure_not_dictword'], sess_info_at['chart'], sess_info_at['figure_emotion_word'] = 'None', 'None', 'None'
        sess_info_at['emotion_tweet'] = []
        sess_info_at['emotion_idx'] = -1

    else:  # ナビゲーションバーの"ワードクラスター"をクリック
        sess_info_at = sess_info[session['searched_at']]

    return render_template('word_clustering.html', keyword=sess_info_at['keyword'], tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'], figure_not_dictword=sess_info_at['figure_not_dictword'],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx'])


@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    sess_info_at = sess_info[session['searched_at']]

    if request.method == 'POST':
        figures = sess_info_at['figures_dictword']
        '''
        for i in range(len(figures)):
            if figures[i][-9:] == '_analyzed':
                figures[i] = figures[i][:-9]
        '''
        sess_info_at['emotion_idx'] = -1

        # return to previous cluster
        if request.form['submit_button'] == 'return':
            if len(sess_info_at['cluster_to_words']) == 1:
                return redirect(url_for('view.home')) # ホーム画面に戻る
            elif len(sess_info_at['cluster_to_words']) == 2:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures
                sess_info_at['figure_not_dictword'] = 'None'
            else:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures[:-1]
                #sess_info_at['figure_not_dictword'] = figures[-1]

            sess_info_at['chart'] = 'None'
            sess_info_at['figure_emotion_word'] = 'None'
            sess_info_at['emotion_tweet'] = []

        # zoom clustering
        elif request.form['submit_button'][:4] == 'zoom':
            if len(sess_info_at['cluster_to_words']) == 1:
                if LOCAL_ENV:
                    top_word2vec = make_top_word2vec_dic(sess_info_at['cluster_to_words'][0][0])
                else:
                    top_word2vec = make_top_word2vec_dic_datastore(sess_info_at['cluster_to_words'][0][0])
                sess_info_at['top_word2vec'] = top_word2vec
                sess_info_at['cluster_to_words'].append(clustering(top_word2vec))
                not_dictword_num = len(list(sess_info_at['cluster_to_words'][-1].keys()))
                sess_info_at['cluster_to_words'][-1][not_dictword_num] = top_word2vec['not_dict_word']
            else:
                cluster_idx = int(request.form['submit_button'][4:])
                clustered_words = sess_info_at['cluster_to_words'][-1][cluster_idx]
                if len(clustered_words) == 1:  # クラスターの単語が1つのとき
                    return render_template('word_clustering.html', keyword=sess_info_at['keyword'], tweet_num=sess_info_at['tweet_num'],
                                           figures=sess_info_at['figures_dictword'],
                                           figure_time_hist=sess_info_at['figure_time_hist'],
                                           figure_not_dictword=sess_info_at['figures_not_dictword'],
                                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx']
                                           )
                part_word2vec = make_part_word2vec_dic(clustered_words, sess_info_at['top_word2vec'])
                zoom_cluster_to_words = clustering(part_word2vec)
                pre_cluster_to_words = copy.deepcopy(sess_info_at['cluster_to_words'][-1])
                sess_info_at['cluster_to_words'].append(copy.deepcopy(sess_info_at['cluster_to_words'][-1]))
                sess_info_at['cluster_to_words'][-1][cluster_idx] = zoom_cluster_to_words[0]
                sess_info_at['cluster_to_words'][-1][cluster_idx+1] = zoom_cluster_to_words[1]

                for i in range(cluster_idx+1, len(list(pre_cluster_to_words.keys()))):
                    sess_info_at['cluster_to_words'][-1][i+1] = pre_cluster_to_words[i]

            figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
            sess_info_at['figures_dictword'] = figures[:-1]
            #sess_info_at['figure_not_dictword'] = figures[-1]
            sess_info_at['chart'] = 'None'
            sess_info_at['emotion_word_figure'] = 'None'
            sess_info_at['emotion_tweet'] = []

        # emotion analysis
        elif request.form['submit_button'][:4] == 'emot':
            cluster_idx = int(request.form['submit_button'][4:])
            #sess_info_at['figures_dictword'][cluster_idx] += '_analyzed'
            sess_info_at['emotion_idx'] = cluster_idx
            words = list(sess_info_at['cluster_to_words'][-1][cluster_idx].keys())
            tweets = sess_info[session['searched_at']]['tweets']
            chart, emotion_word_figure, emotion_tweet = emotion_analyze_all(words, tweets)

            sess_info_at['chart'] = chart
            sess_info_at['figure_emotion_word'] = emotion_word_figure
            sess_info_at['emotion_tweet'] = emotion_tweet

    return render_template('word_clustering.html', keyword=sess_info_at['keyword'], tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx'])


# get session info
@view.route('/info', methods=['GET', 'POST'])
def get_info():
    sess_info_at = sess_info[session['searched_at']]
    #return jsonify([sess_info_at['figures_dictword'][0]])
    return jsonify(sess_info_at['figures_dictword'])


@view.route('/tweet')
def tweet():
    tweets = sess_info[session['searched_at']]['tweets']
    return render_template('tweets.html', tweets=tweets)

@view.route('/word_count', methods=['GET'])
def word_count():
    word_counts = sess_info[session['searched_at']]['word_counts']
    return render_template('word_counts.html', word_counts=word_counts)


# datastore upload
def datastore_upload(up_vec_num=0):
    from google.cloud import datastore
    #from crover import word2vec
    client = datastore.Client()

    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')

    logger.info('start loading dict_all_count')
    dict_all_count = download_from_cloud(storage_client, bucket_name, os.environ.get('DICT_ALL_COUNT'))
    #logger.info('start loading mlask dict')
    #mlask_emotion_dictionary = download_from_cloud(storage_client, bucket_name, os.environ.get('MLASK_EMOTION_DICTIONARY'))
    logger.info('finish loading')
    upload_dict = dict_all_count
    print('num of dict_all_count:', len(upload_dict.keys()))
    upload_folder_name = "sudachi_word2vec_300d"
    #upload_folder_name = "sudachi_all_word_count"
    i = 0
    entities = []

    #for w in word2vec.keys():
    for w in upload_dict.keys():
        i += 1
        if i > up_vec_num and type(w) == str and w[0] != '_' and w != '':
            entity = datastore.Entity(client.key(upload_folder_name, w))
            #entity.update({'vec': list(upload_dict[w].astype(np.float64))})
            entity.update({'count': upload_dict[w]})
            entities.append(entity)
        if i > up_vec_num and i % 400 == 0:
            logger.info(i)
            client.put_multi(entities)
            entities = []

    client.put_multi(entities)


# datastore upload word2vec
def datastore_upload_wv(split, up_vec_num):
    from google.cloud import datastore
    # from crover import word2vec
    client = datastore.Client()

    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')

    for i in range(split, 50):
        logger.info('start loading word2vec dict')
        upload_dict = download_from_cloud(storage_client, bucket_name,
                                          'sudachi_word2vec_dict_300d_50split/sudachi_word2vec_dict_300d_50-' + str(i+1) + '.pickle')
        logger.info('finish loading')
        print('num of word2vec keys:', len(upload_dict.keys()))
        upload_folder_name = "sudachi_word2vec_300d"

        entities = []
        j = 0
        for w in upload_dict.keys():
            j += 1
            if j < up_vec_num:
                continue

            if type(w) == str and w[0] != '_' and w != '':
                entity = datastore.Entity(client.key(upload_folder_name, w))
                entity.update({'vec': list(upload_dict[w].astype(np.float64))})
                entities.append(entity)

            if (j + 1) % 400 == 0 and len(entities) > 0:
                logger.info('split:' + str(i) + ',' + str(j+1))
                client.put_multi(entities)
                entities = []

        if len(entities) > 0:
            logger.info('split:' + str(i) + ',' + str(j + 1))
            client.put_multi(entities)