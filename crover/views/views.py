import os
import copy
import logging
from datetime import datetime

from flask import request, redirect, url_for, render_template, flash, session, make_response
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

sess_info = {} # global variable containing recent session information

@view.route('/')
def home():
    return render_template('index.html', sess_info_at='first') # ナビゲーションバーなし

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
        max_tweets = int(request.form['tweet_num'])
        word_num = int(request.form['word_num'])
        #datastore_upload(int(request.form['up_vec_num']))

        # ツイート取得、ワードカウント
        dict_word_count_rate, tweets_list = preprocess_all(keyword, max_tweets, word_num)
        sess_info_at['tweets'] = tweets_list
        sess_info_at['word_counts'] = list(dict_word_count_rate.items())
        cluster_to_words = [{0: dict_word_count_rate}]
        sess_info_at['cluster_to_words'] = cluster_to_words
        figures = make_word_cloud(cluster_to_words[0])
        sess_info_at['figures_dictword'] = figures
        sess_info_at['figure_not_dictword'], sess_info_at['chart'], sess_info_at['figure_emotion_word'] = 'None', 'None', 'None'
        sess_info_at['posi'], sess_info_at['neutral'], sess_info_at['nega'] = [], [], []

    else: # ナビゲーションバーの"ワードクラスター"をクリック
        sess_info_at = sess_info[session['searched_at']]

    return render_template('word_clustering.html', figures=sess_info_at['figures_dictword'], figure_not_dictword=sess_info_at['figure_not_dictword'],
                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                           posi_tweets=sess_info_at['posi'], neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])


@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    sess_info_at = sess_info[session['searched_at']]

    if request.method == 'POST':
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
                sess_info_at['figure_not_dictword'] = figures[-1]

            sess_info_at['chart'] = 'None'
            sess_info_at['figure_emotion_word'] = 'None'
            sess_info_at['posi'], sess_info_at['neutral'], sess_info_at['nega'] = [], [], []

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
                if len(clustered_words) == 1: # クラスターの単語が1つのとき
                    return render_template('word_clustering.html', figures=sess_info_at['figures_dictword'],
                                           figure_not_dictword=sess_info_at['figures_not_dictword'],
                                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                                           posi_tweets=sess_info_at['posi'], neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])
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
            sess_info_at['figure_not_dictword'] = figures[-1]
            sess_info_at['chart'] = 'None'
            sess_info_at['emotion_word_figure'] = 'None'
            sess_info_at['posi'], sess_info_at['neutral'], sess_info_at['nega'] = [], [], []

        # emotion analysis
        elif request.form['submit_button'][:4] == 'emot':
            cluster_idx = int(request.form['submit_button'][4:])
            words = list(sess_info_at['cluster_to_words'][-1][cluster_idx].keys())
            tweets = sess_info[session['searched_at']]['tweets']
            chart, emotion_word_figure, emotion_tweet = emotion_analyze_all(words, tweets)

            sess_info_at['chart'] = chart
            sess_info_at['figure_emotion_word'] = emotion_word_figure
            sess_info_at['posi'] = emotion_tweet['POSITIVE'] + emotion_tweet['mostly_POSITIVE']
            sess_info_at['neutral'] = emotion_tweet['NEUTRAL']
            sess_info_at['nega'] = emotion_tweet['NEGATIVE'] + emotion_tweet['mostly_NEGATIVE']

    return render_template('word_clustering.html', figures=sess_info_at['figures_dictword'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           chart=sess_info_at['chart'], figure_emotion_word=sess_info_at['figure_emotion_word'],
                           posi_tweets=sess_info_at['posi'],
                           neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])


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
    logger.info('start loading mlask dict')
    mlask_emotion_dictionary = download_from_cloud(storage_client, bucket_name, os.environ.get('MLASK_EMOTION_DICTIONARY'))
    logger.info('finish loading')
    upload_dict = dict_all_count
    print('num of dict_all_count:', len(upload_dict.keys()))
    #upload_folder_name = "mecab_word2vec_100d"
    upload_folder_name = "sudachi_all_word_count"
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