import os
import datetime as dt

from flask import request, redirect, url_for, render_template, flash, session
from flask import current_app as app
#from crover import app
from functools import wraps
from flask import Blueprint

from crover import db
from crover.process.preprocess import preprocess_all
from crover.process.clustering import clustering
#from crover.process.emotion_analyze import emotion_analyze
#from crover.process.util import *
from crover.models.tweet import Tweet

view = Blueprint('view', __name__)



@view.route('/')
def home():
    return render_template('index.html')

@view.app_errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('view.home'))

@view.route('/word_cluster', methods=['GET', 'POST'])
def word_cluster():
    figure_dir = './crover/figure'
    if request.method == 'POST':
        if os.path.exists('./crover/crover.db'):
            db.drop_all()
        db.create_all()
        keyword = request.form['keyword']
        max_tweets = 10

        timedelta = dt.timedelta(days=100)
        dt_until = dt.datetime.now()
        dt_since = dt_until - timedelta
        top_word2vec = preprocess_all(keyword, max_tweets, dt_since.strftime('%Y-%m-%d'), dt_until.strftime('%Y-%m-%d'))
        clustering(top_word2vec, word_num=100)

    return render_template('word_clustering.html', figures=os.listdir(figure_dir))


@view.route('/tweet', methods=['GET'])
def tweet():
    tweets = Tweet.query.order_by(Tweet.id.desc()).all()
    return render_template('tweets.html', tweets=tweets)

