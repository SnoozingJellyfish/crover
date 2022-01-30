import os
import copy
import logging
import datetime as dt
#from datetime import datetime, timedelta
import traceback

from flask import request, redirect, url_for, render_template, session, jsonify
from flask import current_app as app
from flask import Blueprint

from crover import LOCAL_ENV
from crover.process.preprocess import get_trend, preprocess_all, make_top_word2vec_dic, \
    make_part_word2vec_dic, make_top_word2vec_dic_datastore,\
    scrape_retweet, get_retweet_author
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
from crover.process.retweet_network import analyze_network, get_retweet_keyword, datastore_upload_retweet
from crover.process.util import datastore_upload_wv, datastore_upload_retweet_manual, test_run_collect_retweet_job

view = Blueprint('view', __name__)
logger = logging.getLogger(__name__)

ONCE_TWEET_NUM = 10  # クライアントに一度に渡すツイート数
WORD_NUM_IN_CLOUD = 100  # ワードクラウドで表示する単語数

sess_info = {}  # global variable containing recent session information


@view.route('/')
def home():
    trend = get_trend()
    logger.info(trend)
    return render_template('index.html', home_page='true', trend=trend)  # ナビゲーションバーなし


@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))


@view.route('/about')
def about():
    # develop: リツイートデータをdatastoreにアップロード
    #datastore_upload_retweet()
    test_run_collect_retweet_job()

    global sess_info
    if session.get('searched_at') and sess_info.get(session['searched_at'], {}).get('depth') != None:
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
    app.permanent_session_lifetime = dt.timedelta(minutes=5)

    # ユーザーの直前のセッションの情報を削除
    if 'searched_at' in session and session['searched_at'] in sess_info:
        del sess_info[session['searched_at']]

    # セッションを区別するタイムスタンプを設定
    session['searched_at'] = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    logger.info(session['searched_at'])
    searched_at_list = list(sess_info.keys())
    logger.info('count of remembered session: ' + str(len(searched_at_list)))

    # 記憶する直近のセッションを10個以内にする
    if len(searched_at_list) > 10:
        del sess_info[sorted(searched_at_list)[0]]
    sess_info[session['searched_at']] = {}
    sess_info_at = sess_info[session['searched_at']]

    keyword = request.form.get('keyword')
    sess_info_at['keyword'] = keyword

    max_tweets = int(request.form.get('tweet_num', 500))
    sess_info_at['tweet_num'] = max_tweets

    # ツイート取得、ワードカウント
    try:
        dict_word_count_rate, tweets_list, time_hist = preprocess_all(keyword, max_tweets, WORD_NUM_IN_CLOUD)
    except:  # 検索可能な文字がキーワードに含まれない場合
        logger.info(traceback.format_exc())
        return redirect(url_for('view.home'))

    sess_info_at['tweets'] = tweets_list
    sess_info_at['word_counts'] = list(dict_word_count_rate.items())
    cluster_to_words = [{0: dict_word_count_rate}]
    sess_info_at['cluster_to_words'] = cluster_to_words
    colormaps = ['spring', 'summer', 'autumn', 'winter', 'PuRd', 'Wistia', 'cool', 'hot', 'YlGnBu', 'YlOrBr']
    figures = make_word_cloud(cluster_to_words[0], colormaps)

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

        # クラスターが複数
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

        colormaps = ['spring', 'summer', 'autumn', 'winter', 'PuRd', 'Wistia', 'cool', 'hot', 'YlGnBu', 'YlOrBr']
        figures = make_word_cloud(sess_info_at['cluster_to_words'][depth+1], colormaps)
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
                           figure_emotion_word='none',
                           posi_tweet='none',
                           neut_tweet='none',
                           nega_tweet='none',
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

    # クライアントに渡す先頭のツイートを抽出
    tweet = {}
    for emotion in ['positive', 'neutral', 'negative']:
        tweet[emotion] = {}
        retention_tweet = sess_info_at['emotion_tweet'][emotion]

        if ONCE_TWEET_NUM < len(retention_tweet):
            tweet[emotion]['tweet'] = retention_tweet[:ONCE_TWEET_NUM]
            tweet[emotion]['load_continue'] = 'true'
        else:
            tweet[emotion]['tweet'] = retention_tweet
            tweet[emotion]['load_continue'] = 'false'

    return render_template('word_clustering.html',
                           keyword=sess_info_at['keyword'],
                           tweet_num=sess_info_at['tweet_num'],
                           figures=sess_info_at['figures_dictword'][depth],
                           figure_time_hist=sess_info_at['figure_time_hist'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           figure_emotion_word=sess_info_at['figure_emotion_word'],
                           posi_tweet=tweet['positive'],
                           neut_tweet=tweet['neutral'],
                           nega_tweet=tweet['negative'],
                           emotion_idx=sess_info_at['emotion_idx'],
                           emotion_elem=sess_info_at['emotion_elem'],
                           depth=sess_info_at['depth'],
                           about_page='false')


# get session info
@view.route('/info', methods=['GET', 'POST'])
def get_info():
    sess_info_at = sess_info[session['searched_at']]
    return jsonify(sess_info_at['figures_dictword'])

# クライアントに感情分析後の続きのツイートを渡す
@view.route('/ajax_load_tweet/<emotion>/<int:tweet_start_cnt>')
def load_tweet(emotion, tweet_start_cnt):
    add_data = {}
    sess_info_at = sess_info[session['searched_at']]
    retention_tweet = sess_info_at['emotion_tweet'][emotion]
    if tweet_start_cnt + ONCE_TWEET_NUM < len(retention_tweet):
        add_data['tweet'] = retention_tweet[tweet_start_cnt: tweet_start_cnt + ONCE_TWEET_NUM]
        add_data['load_continue'] = 'true'
    else:
        add_data['tweet'] = retention_tweet[tweet_start_cnt:]
        add_data['load_continue'] = 'false'

    return jsonify(add_data)

# 収集済みリツイートキーワードを取得
@view.route('/network_keyword', methods=['GET'])
def network_keyword():
    re_keyword = get_retweet_keyword()

    return render_template('retweet_network.html', re_keyword=re_keyword)


# 選択されたキーワード、開始日、終了日からネットワークを生成する
@view.route('/ajax_show_network', methods=['POST'])
def show_network():
    keyword = request.form['keyword']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    graph = analyze_network(keyword, start_date, end_date)
    return jsonify(graph)


# Cloud Schedulerで1日ごとにリツイートを収集しdatastoreに保存する
@view.route('/run_collect_retweet_job', methods=['POST'])
def run_collect_retweet_job():
    logger.info('running collect retweet scheduler')
    keyword = request.get_data(as_text=True).split(',')
    logger.info(f'keyword: {str(keyword)}')

    jst_delta = dt.timedelta(hours=9)
    JST = dt.timezone(jst_delta, 'JST')
    today_dt = dt.datetime.now(JST)
    today = today_dt.strftime('%Y/%m/%d')
    yesterday_dt = dt.datetime.now(JST) - dt.timedelta(days=1)
    since_date = yesterday_dt.strftime('%Y-%m-%d')

    for k in keyword:
        # リツイートを取得する
        retweet = scrape_retweet(k)
        # リツイートしたユーザーを取得する
        retweet = get_retweet_author(retweet, since_date)
        # リツイート情報をdatastoreに保存する
        datastore_upload_retweet(k, today, retweet)