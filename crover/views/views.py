import os
import datetime as dt
import logging
import pickle
import copy

from flask import request, redirect, url_for, render_template, flash, session
from flask import current_app as app
#from crover import app
from functools import wraps
from flask import Blueprint
from google.cloud import storage

from crover import db, IS_SERVER, download_from_cloud, upload_to_cloud
from crover.process.preprocess import preprocess_all, make_part_word2vec_dic
from crover.process.clustering import clustering, make_word_cloud
from crover.process.emotion_analyze import emotion_analyze_all
#from crover.process.emotion_analyze import emotion_analyze
#from crover.process.util import *
from crover.models.tweet import Tweet, ClusterTweet, WordCount

view = Blueprint('view', __name__)


b64_figures = []
b64_chart = 'None'
cluster_to_words = [None]
top_word2vec = {}

@view.route('/')
def home():
    return render_template('index.html')

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    global b64_figures, cluster_to_words, top_word2vec
    figure_dir = './crover/figure'
    if request.method == 'POST':
        #if os.path.exists('./crover/crover.db'):
        try:
            db.drop_all()
        except:
            pass
        db.create_all()
        keyword = request.form['keyword']
        max_tweets = int(request.form['tweet_num'])
        word_num = int(request.form['word_num'])

        #timedelta = dt.timedelta(days=100)
        #dt_until = dt.datetime.now()
        #dt_since = dt_until - timedelta
        top_word2vec = preprocess_all(keyword, max_tweets, word_num)
        print(top_word2vec['word'])
        #return redirect(url_for('view.word_count'))
        #return redirect(url_for('view.tweet'))
        #b64_figures = clustering(top_word2vec, word_num=word_num)
        cluster_to_words = [clustering(top_word2vec, word_num=word_num)]
        not_dictword_num = len(list(cluster_to_words[0].keys()))
        cluster_to_words[0][not_dictword_num] = top_word2vec['not_dict_word']
        b64_figures = make_word_cloud(cluster_to_words[0])

    return render_template('word_clustering.html', b64_figures=b64_figures[:-1], b64_figure_not_dictword=b64_figures[-1], b64_chart=b64_chart)

@view.route('/analysis', methods=['GET', 'POST'])
def analysis():
    global b64_figures, b64_chart, cluster_to_words, top_word2vec
    posi = []
    neutral = []
    nega = []
    if request.method == 'POST':
        if request.form['submit_button'] == 'return': # return to previous cluster
            del cluster_to_words[-1]
            b64_figures = make_word_cloud(cluster_to_words[-1])

        elif request.form['submit_button'][:4] == 'zoom': # zoom clustering
            cluster_idx = int(request.form['submit_button'][4:])
            clustered_words = cluster_to_words[-1][cluster_idx]
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
            b64_chart = emotion_analyze_all(words)
            posi = ClusterTweet.query.filter(ClusterTweet.emotion == 'POSITIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_POSITIVE').all()
            neutral = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEUTRAL').all()
            nega = ClusterTweet.query.filter(ClusterTweet.emotion == 'NEGATIVE').all() + \
                   ClusterTweet.query.filter(ClusterTweet.emotion == 'mostly_NEGATIVE').all()


    return render_template('word_clustering.html', b64_figures=b64_figures[:-1], b64_figure_not_dictword=b64_figures[-1],
                           b64_chart=b64_chart, posi_tweets=posi, neutral_tweets=neutral, nega_tweets=nega)

@view.route('/tweet', methods=['GET'])
def tweet():
    tweets = Tweet.query.order_by(Tweet.id.desc()).all()
    return render_template('tweets.html', tweets=tweets)

@view.route('/word_count', methods=['GET'])
def word_count():
    word_counts = WordCount.query.order_by(WordCount.relative_frequent_rate.desc()).all()
    return render_template('word_counts.html', word_counts=word_counts)

