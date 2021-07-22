"""
Copyright (c) 2021 Naoya Furuhashi
This software is released under the MIT License, see LICENSE.
"""

import copy
import logging
from datetime import datetime, timedelta

from flask import request, redirect, url_for, render_template, session, jsonify
from flask import current_app as app
from flask import Blueprint

from crover import LOCAL_ENV
from crover.process.preprocess import preprocess_all, make_top_word2vec_dic, make_part_word2vec_dic, make_top_word2vec_dic_datastore
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
from crover.process.util import datastore_upload_wv

view = Blueprint('view', __name__)
logger = logging.getLogger(__name__)

sess_info = {}  # global variable containing recent session information

@view.route('/')
def home():
    return render_template('index.html', home_page='true')  # ナビゲーションバーなし

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/about')
def about():
    global sess_info
    if 'searched_at' in session and session['searched_at'] in sess_info:
        already_sess = 'true'
    else:
        already_sess = 'false'
    return render_template('about.html', about_page='true', already_sess=already_sess)

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    global sess_info

    # ツイートを取得しワード数をカウントする
    if request.method == 'POST':
        session.permanent = True
        app.permanent_session_lifetime = timedelta(minutes=5)

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
        word_num = 100

        # ツイート取得、ワードカウント
        dict_word_count_rate, tweets_list, time_hist = preprocess_all(keyword, max_tweets, word_num)
        sess_info_at['tweets'] = tweets_list
        sess_info_at['word_counts'] = list(dict_word_count_rate.items())
        cluster_to_words = [{0: dict_word_count_rate}]
        sess_info_at['cluster_to_words'] = cluster_to_words
        figures = make_word_cloud(cluster_to_words[0])

        sess_info_at['figures_dictword'] = figures
        sess_info_at['figure_time_hist'] = time_hist
        sess_info_at['figure_not_dictword'], sess_info_at['chart'], sess_info_at['figure_emotion_word'] = 'none', 'none', 'none'
        sess_info_at['emotion_tweet'] = []
        sess_info_at['emotion_idx'] = -1

    else:  # ナビゲーションバーの"Analysis"をクリック
        sess_info_at = sess_info[session['searched_at']]

    return render_template('word_clustering.html', keyword=sess_info_at['keyword'], tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'], figure_not_dictword=sess_info_at['figure_not_dictword'],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx'],
                           about_page='False')


@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    sess_info_at = sess_info[session['searched_at']]

    if request.method == 'POST':
        sess_info_at['emotion_idx'] = -1

        # return to previous cluster
        if request.form['submit_button'] == 'return':
            if len(sess_info_at['cluster_to_words']) == 1:
                return redirect(url_for('view.home')) # ホーム画面に戻る
            elif len(sess_info_at['cluster_to_words']) == 2:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures
                sess_info_at['figure_not_dictword'] = 'none'
            else:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures[:-1]

            sess_info_at['chart'] = 'none'
            sess_info_at['figure_emotion_word'] = 'none'
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
                                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx'],
                                           about_page='False')
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
            #sess_info_at['figure_not_dictword'] = figures[-1]  # debug
            sess_info_at['chart'] = 'none'
            sess_info_at['emotion_word_figure'] = 'none'
            sess_info_at['emotion_tweet'] = []

        # emotion analysis
        elif request.form['submit_button'][:4] == 'emot':
            cluster_idx = int(request.form['submit_button'][4:])
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
                           emotion_tweet=sess_info_at['emotion_tweet'], emotion_idx=sess_info_at['emotion_idx'],
                           about_page='False')


# get session info
@view.route('/info', methods=['GET', 'POST'])
def get_info():
    sess_info_at = sess_info[session['searched_at']]
    return jsonify(sess_info_at['figures_dictword'])


@view.route('/tweet')
def tweet():
    tweets = sess_info[session['searched_at']]['tweets']
    return render_template('tweets.html', tweets=tweets)

@view.route('/word_count', methods=['GET'])
def word_count():
    word_counts = sess_info[session['searched_at']]['word_counts']
    return render_template('word_counts.html', word_counts=word_counts)