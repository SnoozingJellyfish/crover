import os
import copy
import logging
from datetime import timedelta, datetime

from flask import request, redirect, url_for, render_template, flash, session, make_response
from flask import current_app as app
#from crover import app
#from functools import wraps
from flask import Blueprint
from google.cloud import storage
from sqlalchemy import desc

#from crover import db_session, LOCAL_ENV, download_from_cloud, upload_to_cloud, Base, engine
from crover import LOCAL_ENV
from crover.process.preprocess import preprocess_all, make_top_word2vec_dic, make_part_word2vec_dic, make_top_word2vec_dic_datastore
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
#from crover.models.tweet import Tweet, WordCount, ClusterTweet

view = Blueprint('view', __name__)
logger = logging.getLogger(__name__)

'''
b64_figures = []
b64_chart = 'None'
cluster_to_words = [None]
top_word2vec = {}
posi = []
neutral = []
nega = []
'''
sess_info = {}

@view.route('/')
def home():
    #session.permanent = False
    #app.permanent_session_lifetime = timedelta(minutes=5)
    #if 'time' not in session:
    #session['time2'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    #logger.info(session['time2'])

    #Base.metadata.create_all(bind=engine)
    return render_template('index.html', sess_info_at='first')

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    #global b64_figures, b64_chart, cluster_to_words, top_word2vec, posi, neutral, nega
    global sess_info

    if request.method == 'POST':
        #db_session.query(Tweet).delete()
        #db_session.query(WordCount).delete()


        #if 'time' not in session:
        #response = make_response('tmpsessi')
        #response.set_cookie('time3', value=datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        session['searched_at'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        logger.info(session['searched_at'])
        searched_at_list = list(sess_info.keys())
        logger.info('count of remembered session: ' + str(len(searched_at_list)))
        if len(searched_at_list) > 10:
            del sess_info[sorted(searched_at_list)[0]]
        sess_info[session['searched_at']] = {}
        sess_info_at = sess_info[session['searched_at']]
        '''
        try:
            db.drop_all()
        except:
            pass
        db.create_all()
        '''
        keyword = request.form['keyword']
        max_tweets = int(request.form['tweet_num'])
        word_num = int(request.form['word_num'])
        #datastore_upload(int(request.form['up_vec_num']))
        dict_word_count_rate, tweets_list = preprocess_all(keyword, max_tweets, word_num)
        sess_info_at['tweets'] = tweets_list
        sess_info_at['word_counts'] = list(dict_word_count_rate.items())
        cluster_to_words = [{0: dict_word_count_rate}]
        sess_info_at['cluster_to_words'] = cluster_to_words
        figures = make_word_cloud(cluster_to_words[0])
        sess_info_at['figures_dictword'] = figures
        sess_info_at['figure_not_dictword'], sess_info_at['chart'] = 'None', 'None'
        sess_info_at['posi'], sess_info_at['neutral'], sess_info_at['nega'] = [], [], []

    else: # ナビゲーションバーの"ワードクラスター"をクリック
        sess_info_at = sess_info[session['searched_at']]

    return render_template('word_clustering.html', figures=sess_info_at['figures_dictword'], figure_not_dictword=sess_info_at['figure_not_dictword'],
                           chart=sess_info_at['chart'], posi_tweets=sess_info_at['posi'], neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])
    #return render_template('word_clustering.html', sess_info_at=sess_info[session['searched_at']])

@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    #global b64_figures, b64_chart, cluster_to_words, top_word2vec, posi, neutral, nega
    sess_info_at = sess_info[session['searched_at']]
    posi = []
    neutral = []
    nega = []
    b64_chart = 'None'
    if request.method == 'POST':
        # return to previous cluster
        if request.form['submit_button'] == 'return':
            if len(sess_info_at['cluster_to_words']) == 1:
                return redirect(url_for('view.home'))
            elif len(sess_info_at['cluster_to_words']) == 2:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures
                sess_info_at['figure_not_dictword'] = 'None'
                #return render_template('word_clustering.html', figures=b64_figures, b64_figure_not_dictword='None',
                 #                      b64_chart='None')
            else:
                del sess_info_at['cluster_to_words'][-1]
                figures = make_word_cloud(sess_info_at['cluster_to_words'][-1])
                sess_info_at['figures_dictword'] = figures[:-1]
                sess_info_at['figure_not_dictword'] = figures[-1]

            sess_info_at['chart'] = 'None'
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
                                           chart=sess_info_at['chart'], posi_tweets=sess_info_at['posi'], neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])
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
            sess_info_at['posi'], sess_info_at['neutral'], sess_info_at['nega'] = [], [], []

        # emotion analysis
        elif request.form['submit_button'][:4] == 'emot':
            cluster_idx = int(request.form['submit_button'][4:])
            words = list(sess_info_at['cluster_to_words'][-1][cluster_idx].keys())
            tweets = sess_info[session['searched_at']]['tweets']
            chart, emotion_tweet = emotion_analyze_all(words, tweets)
            sess_info_at['chart'] = chart
            '''
            posi = ClusterTweet.query.filter(ClusterTweet.emotion == 'POSITIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_POSITIVE').all()
            neutral = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEUTRAL').all()
            nega = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEGATIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_NEGATIVE').all()
            '''
            sess_info_at['posi'] = emotion_tweet['POSITIVE'] + emotion_tweet['mostly_POSITIVE']
            sess_info_at['neutral'] = emotion_tweet['NEUTRAL']
            sess_info_at['nega'] = emotion_tweet['NEGATIVE'] + emotion_tweet['mostly_NEGATIVE']

            #if len(sess_info_at['cluster_to_words']) == 1:
             #   return render_template('word_clustering.html', b64_figures=b64_figures, b64_figure_not_dictword='None',
              #                         b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)

    return render_template('word_clustering.html', figures=sess_info_at['figures_dictword'],
                           figure_not_dictword=sess_info_at['figure_not_dictword'],
                           chart=sess_info_at['chart'], posi_tweets=sess_info_at['posi'],
                           neutral_tweets=sess_info_at['neutral'], nega_tweets=sess_info_at['nega'])


#@view.route('/tweet', methods=['GET'])
@view.route('/tweet')
def tweet():
    #tweets = Tweet.query.order_by(Tweet.id.desc()).all()
    #logger.info('start getting tweets from DB')
    #tweets = db_session.query(Tweet).all()
    tweets = sess_info[session['searched_at']]['tweets']
    #logger.info(session['time4'] + ' tweet')
    #time3 = request.cookies.get('time3', None)
    #logger.info(time3 + ' tweet')
    return render_template('tweets.html', tweets=tweets)

@view.route('/word_count', methods=['GET'])
def word_count():
    #word_counts = WordCount.query.order_by(WordCount.relative_frequent_rate.desc()).all()
    #word_counts = db_session.query(WordCount).order_by(desc(WordCount.relative_frequent_rate)).all()
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