import os
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

'''
@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))
'''

@view.route('/about')
def about():
    global sess_info
    if 'searched_at' in session and session['searched_at'] in sess_info:
        already_sess = 'true'
        depth = sess_info[session['searched_at']]['depth']
    else:
        already_sess = 'false'
        depth = 0
    return render_template('about.html', about_page='true', already_sess=already_sess, depth=depth)

@view.route('/collect_tweets', methods=['POST'])
def collect_tweets():
    global sess_info

    # ツイートを取得しワード数をカウントする
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

    sess_info_at['figures_dictword'] = [figures]
    sess_info_at['figure_time_hist'] = time_hist
    sess_info_at['figure_not_dictword'], sess_info_at['chart'], sess_info_at['figure_emotion_word'] = 'none', 'none', 'none'
    sess_info_at['emotion_tweet'] = 'none'
    sess_info_at['emotion_idx'] = -1
    sess_info_at['depth'] = 0
    sess_info_at['emotion_elem'] = [1, 1, 1]

    return redirect(url_for('view.word_clustring', depth=0))


@view.route('/analysis/', methods=['POST'])
def analysis():
    sess_info_at = sess_info[session['searched_at']]
    depth = sess_info_at['depth']
    sess_info_at['emotion_idx'] = -1

    # split cluster
    if request.form['submit_button'][:5] == 'split':
        # クラスターが1つだけ
        if depth == 0:
            # 既にベクトルが取得されている場合（戻って再び分割する場合）
            if len(sess_info_at['cluster_to_words']) > 1:
                return redirect(url_for('view.word_clustring', depth=1))

            # 初回
            if LOCAL_ENV:
                top_word2vec = make_top_word2vec_dic(sess_info_at['cluster_to_words'][depth][0])
            else:
                top_word2vec = make_top_word2vec_dic_datastore(sess_info_at['cluster_to_words'][depth][0])
            sess_info_at['top_word2vec'] = top_word2vec
            sess_info_at['cluster_to_words'].append(clustering(top_word2vec))
            # sess_info_at['figure_not_dictword'] = make_word_cloud([top_word2vec['not_dict_word']])[0]  # debug
        else:
            cluster_idx = int(request.form['submit_button'][5:])
            clustered_words = sess_info_at['cluster_to_words'][depth][cluster_idx]
            if len(clustered_words) == 1:  # クラスターの単語が1つのときそのまま返す
                return redirect(url_for('view.word_clustring', depth=sess_info_at['depth']))

            part_word2vec = make_part_word2vec_dic(clustered_words, sess_info_at['top_word2vec'])
            split_cluster_to_words = clustering(part_word2vec)
            pre_cluster_to_words = copy.deepcopy(sess_info_at['cluster_to_words'][depth])
            if len(sess_info_at['cluster_to_words']) == depth + 1:
                sess_info_at['cluster_to_words'].append(copy.deepcopy(sess_info_at['cluster_to_words'][depth]))
            else:
                sess_info_at['cluster_to_words'][depth+1] = copy.deepcopy(sess_info_at['cluster_to_words'][depth])
            sess_info_at['cluster_to_words'][depth+1][cluster_idx] = split_cluster_to_words[0]
            sess_info_at['cluster_to_words'][depth+1][cluster_idx+1] = split_cluster_to_words[1]

            for i in range(cluster_idx+1, len(list(pre_cluster_to_words.keys()))):
                sess_info_at['cluster_to_words'][depth+1][i+1] = pre_cluster_to_words[i]

        figures = make_word_cloud(sess_info_at['cluster_to_words'][depth+1])
        if len(sess_info_at['figures_dictword']) == depth + 1:
            sess_info_at['figures_dictword'].append(figures)
        else:
            sess_info_at['figures_dictword'][depth+1] = figures
        sess_info_at['chart'] = 'none'
        sess_info_at['figure_emotion_word'] = 'none'
        sess_info_at['emotion_tweet'] = []
        sess_info_at['depth'] += 1

        return redirect(url_for('view.word_clustring', depth=sess_info_at['depth']))

    # emotion analysis
    elif request.form['submit_button'][:5] == 'emoti':
        cluster_idx = int(request.form['submit_button'][5:])
        sess_info_at['emotion_idx'] = cluster_idx
        words = list(sess_info_at['cluster_to_words'][depth][cluster_idx].keys())
        tweets = sess_info[session['searched_at']]['tweets']
        emotion_elem, emotion_word_figure, emotion_tweet = emotion_analyze_all(words, tweets)

        #sess_info_at['chart'] = chart
        sess_info_at['figure_emotion_word'] = emotion_word_figure
        sess_info_at['emotion_tweet'] = emotion_tweet
        sess_info_at['emotion_elem'] = emotion_elem

        return redirect(url_for('view.emotion', depth=sess_info_at['depth']))



@view.route('/word_clustring/<int:depth>')
def word_clustring(depth):
    sess_info_at = sess_info[session['searched_at']]
    sess_info_at['depth'] = depth

    # クラスタリングしてからナビバーから検索した後、「戻る」ボタンで戻った時
    if depth >= len(sess_info_at['figures_dictword']):
        return render_template('index.html', home_page='true')  # ナビゲーションバーなし

    return render_template('word_clustering.html',
                           keyword=sess_info_at['keyword'],
                           tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'][depth],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           #chart='none',
                           figure_emotion_word='none',
                           emotion_tweet='none',
                           emotion_idx=-1,
                           emotion_elem=[1, 1, 1],
                           depth=sess_info_at['depth'],
                           about_page='false')


@view.route('/emotion/<int:depth>')
def emotion(depth):
    sess_info_at = sess_info[session['searched_at']]
    sess_info_at['depth'] = depth

    # クラスタリングしてからナビバーから検索した後、「戻る」ボタンで戻った時
    if depth >= len(sess_info_at['figures_dictword']):
        return render_template('index.html', home_page='true')  # ナビゲーションバーなし

    return render_template('word_clustering.html',
                           keyword=sess_info_at['keyword'],
                           tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'][depth],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           #chart=sess_info_at['chart'],
                           figure_emotion_word=sess_info_at['figure_emotion_word'],
                           emotion_tweet=sess_info_at['emotion_tweet'],
                           emotion_idx=sess_info_at['emotion_idx'],
                           emotion_elem=sess_info_at['emotion_elem'],
                           depth=sess_info_at['depth'],
                           about_page='false')


# get session info
@view.route('/info', methods=['GET', 'POST'])
def get_info():
    sess_info_at = sess_info[session['searched_at']]
    return jsonify(sess_info_at['figures_dictword'])
