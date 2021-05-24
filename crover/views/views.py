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

from crover import db_session, LOCAL_ENV, download_from_cloud, upload_to_cloud, Base, engine
from crover.process.preprocess import preprocess_all, make_top_word2vec_dic, make_part_word2vec_dic, make_top_word2vec_dic_datastore
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
from crover.models.tweet import Tweet, WordCount

view = Blueprint('view', __name__)
logger = logging.getLogger(__name__)

b64_figures = []
b64_chart = 'None'
cluster_to_words = [None]
top_word2vec = {}
posi = []
neutral = []
nega = []

@view.route('/')
def home():
    #session.permanent = False
    #app.permanent_session_lifetime = timedelta(minutes=5)
    #if 'time' not in session:
    #session['time2'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    #logger.info(session['time2'])

    Base.metadata.create_all(bind=engine)
    return render_template('index.html')

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    global b64_figures, b64_chart, cluster_to_words, top_word2vec, posi, neutral, nega

    if request.method == 'POST':
        #if 'time' not in session:
        #response = make_response('tmpsessi')
        #response.set_cookie('time3', value=datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        session['time4'] = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        logger.info(session['time4'])

        b64_chart = 'None'
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
        #session['tmp2'] = 'session_tmp2'
        #session['tweets'] = tweets_list
        cluster_to_words = [{0: dict_word_count_rate}]
        b64_figures = make_word_cloud(cluster_to_words[0])

    if len(b64_figures) == 1:
        return render_template('word_clustering.html', b64_figures=b64_figures, b64_figure_not_dictword='None',
                               b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)
    else:
        return render_template('word_clustering.html', b64_figures=b64_figures[:-1], b64_figure_not_dictword=b64_figures[-1],
                               b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)

@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    global b64_figures, b64_chart, cluster_to_words, top_word2vec, posi, neutral, nega
    posi = []
    neutral = []
    nega = []
    b64_chart = 'None'
    if request.method == 'POST':
        if request.form['submit_button'] == 'return': # return to previous cluster
            if len(cluster_to_words) == 1:
                return redirect(url_for('view.home'))
            elif len(cluster_to_words) == 2:
                del cluster_to_words[-1]
                b64_figures = make_word_cloud(cluster_to_words[-1])
                return render_template('word_clustering.html', b64_figures=b64_figures, b64_figure_not_dictword='None',
                                       b64_chart='None')
            else:
                del cluster_to_words[-1]
                b64_figures = make_word_cloud(cluster_to_words[-1])

        elif request.form['submit_button'][:4] == 'zoom': # zoom clustering
            if len(cluster_to_words) == 1:
                if LOCAL_ENV:
                    top_word2vec = make_top_word2vec_dic(cluster_to_words[0][0])
                else:
                    top_word2vec = make_top_word2vec_dic_datastore(cluster_to_words[0][0])
                cluster_to_words.append(clustering(top_word2vec))
                not_dictword_num = len(list(cluster_to_words[-1].keys()))
                cluster_to_words[-1][not_dictword_num] = top_word2vec['not_dict_word']
            else:
                cluster_idx = int(request.form['submit_button'][4:])
                clustered_words = cluster_to_words[-1][cluster_idx]
                if len(clustered_words) == 1:
                    return render_template('word_clustering.html', b64_figures=b64_figures[:-1],
                                           b64_figure_not_dictword=b64_figures[-1],
                                           b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)
                part_word2vec = make_part_word2vec_dic(clustered_words, top_word2vec)
                zoom_cluster_to_words = clustering(part_word2vec)
                pre_cluster_to_words = copy.deepcopy(cluster_to_words[-1])
                cluster_to_words.append(copy.deepcopy(cluster_to_words[-1]))
                cluster_to_words[-1][cluster_idx] = zoom_cluster_to_words[0]
                cluster_to_words[-1][cluster_idx+1] = zoom_cluster_to_words[1]

                for i in range(cluster_idx+1, len(list(pre_cluster_to_words.keys()))):
                    cluster_to_words[-1][i+1] = pre_cluster_to_words[i]

            b64_figures = make_word_cloud(cluster_to_words[-1])

        elif request.form['submit_button'][:4] == 'emot': # emotion analysis
            cluster_idx = int(request.form['submit_button'][4:])
            words = list(cluster_to_words[-1][cluster_idx].keys())
            b64_chart, emotion_tweet = emotion_analyze_all(words)
            '''
            posi = ClusterTweet.query.filter(ClusterTweet.emotion == 'POSITIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_POSITIVE').all()
            neutral = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEUTRAL').all()
            nega = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEGATIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_NEGATIVE').all()
            '''
            posi = emotion_tweet['POSITIVE'] + emotion_tweet['mostly_POSITIVE']
            neutral = emotion_tweet['NEUTRAL']
            nega = emotion_tweet['NEGATIVE'] + emotion_tweet['mostly_NEGATIVE']

            if len(cluster_to_words) == 1:
                return render_template('word_clustering.html', b64_figures=b64_figures, b64_figure_not_dictword='None',
                                       b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)


    return render_template('word_clustering.html', b64_figures=b64_figures[:-1], b64_figure_not_dictword=b64_figures[-1],
                           b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)

#@view.route('/tweet', methods=['GET'])
@view.route('/tweet')
def tweet():
    tweets = Tweet.query.order_by(Tweet.id.desc()).all()
    logger.info(session['time4'] + ' tweet')
    #time3 = request.cookies.get('time3', None)
    #logger.info(time3 + ' tweet')
    return render_template('tweets.html', tweets=tweets)

@view.route('/word_count', methods=['GET'])
def word_count():
    word_counts = WordCount.query.order_by(WordCount.relative_frequent_rate.desc()).all()
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