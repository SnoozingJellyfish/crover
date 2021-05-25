import copy
from pprint import pprint
import io
import base64
import logging
import pickle

import matplotlib.pyplot as plt
import numpy as np
from flask import session
#from mlask import MLAsk
from crover.process.mlask_no_mecab import MLAskNoMecab
#from transformers import pipeline,AutoTokenizer,BertTokenizer,AutoModelForSequenceClassification,BertJapaneseTokenizer, BertForMaskedLM

from crover.models.tweet import Tweet, ClusterTweet
#from crover import db, mlask_emotion_dictionary
from crover import db_session

logger = logging.getLogger(__name__)

def emotion_analyze_all(words):
    logger.info('collect tweet including cluster word')
    cluster_tweets = tweet_collect(words)
    logger.info('emotion analyze')
    emotion_count, emotion_tweet = emotion_analyze(cluster_tweets)
    logger.info('make pie chart')
    b64_chart = make_emotion_pie_chart(emotion_count)
    return b64_chart, emotion_tweet

# クラスタリングされた単語を含むツイートを取得する
def tweet_collect(words):
    #tweets = np.array(Tweet.query.all())
    tweets = np.array(db_session.query(Tweet).all())
    #tweets = np.array(session['tweets'])
    tweet_id = list(np.arange(len(tweets)))
    tweet_id_new = copy.deepcopy(tweet_id)
    cluster_tweet_id = []

    for w in words:
        for i in tweet_id:
            try:
                if w in tweets[i].text:
                #if w in tweets[i, 1]:
                    cluster_tweet_id.append(i)
                    tweet_id_new.remove(i)
            except TypeError:
                continue

        tweet_id = copy.deepcopy(tweet_id_new)

    cluster_tweets = tweets[cluster_tweet_id]
    return cluster_tweets


# 感情分析する
def emotion_analyze(cluster_tweets, algo='mlask'):
    #if engine.dialect.has_table(engine, ClusterTweet.__tablename__):
        #ClusterTweet.__table__.drop(engine)
    cluster_tweets_emotion = []
    emotion_count = {'POSITIVE': 0, 'mostly_POSITIVE': 0, 'NEUTRAL': 0, 'mostly_NEGATIVE': 0, 'NEGATIVE': 0}
    emotion_tweet = {'POSITIVE': [], 'mostly_POSITIVE': [], 'NEUTRAL': [], 'mostly_NEGATIVE': [], 'NEGATIVE': []}

    if algo == 'mlask':
        with open('crover/data/mlask_emotion_dictionary.pickle', 'rb') as f:
            mlask_emotion_dictionary = pickle.load(f)
        emotion_analyzer = MLAskNoMecab(mlask_emotion_dictionary)
        for tweet in cluster_tweets:
            result_dic = emotion_analyzer.analyze(tweet.text, tweet.word)
            #result_dic = emotion_analyzer.analyze(tweet[1], tweet[2])
            if result_dic['emotion'] == None:
                cluster_tweets_emotion.append(ClusterTweet(tweeted_at=tweet.tweeted_at, text=tweet.text, emotion='NEUTRAL'))
                #cluster_tweets_emotion.append(ClusterTweet(tweeted_at=tweet[0], text=tweet[1], emotion='NEUTRAL'))
                emotion_count['NEUTRAL'] += 1
                emotion_tweet['NEUTRAL'].append(tweet.text)
            else:
                cluster_tweets_emotion.append(ClusterTweet(tweeted_at=tweet.tweeted_at, text=tweet.text, emotion=result_dic['orientation']))
                #cluster_tweets_emotion.append(ClusterTweet(tweeted_at=tweet[0], text=tweet[1], emotion=result_dic['orientation']))
                emotion_count[result_dic['orientation']] += 1
                emotion_tweet[result_dic['orientation']].append(tweet.text)

    elif algo == 'oseti':
        emotion_analyzer = oseti.Analyzer()
        for i in tqdm(range(len(df_cluster))):
            df_cluster.loc[i, 'orientation'] = np.mean(emotion_analyzer.analyze(df_cluster['tweet'][i]))

    elif algo == 'asari':
        # エラーで実行できない

        #sonar = asari.api.Sonar()
        sonar = Sonar()
        print(type(df_cluster['tweet'][0]))
        print(sonar.ping(text="休みでうれしい"))

    '''
    # BERTでは多くがポジティブに判定される
    elif algo == 'bert':
        model = AutoModelForSequenceClassification.from_pretrained('daigo/bert-base-japanese-sentiment')
        tokenizer = BertJapaneseTokenizer.from_pretrained('cl-tohoku/bert-base-japanese-whole-word-masking')
        nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

        for i in tqdm(range(len(df_cluster))):
            result = nlp(df_cluster['tweet'][i])
            df_cluster.loc[i, 'label'] = result[0]['label']
            df_cluster.loc[i, 'score'] = result[0]['score']

            if (i+1) % 1000 == 0:
                df_cluster.to_csv(cluster_csv[:-4] + '_' + algo + '_analyzed.csv')
    '''
    db_session().add_all(cluster_tweets_emotion)
    db_session().commit()

    return emotion_count, emotion_tweet


def make_emotion_pie_chart(emotion_count):
    x = np.array([emotion_count['POSITIVE'] + emotion_count['mostly_POSITIVE'], emotion_count['NEUTRAL'], emotion_count['NEGATIVE'] + emotion_count['mostly_NEGATIVE']])
    label = ['positive', 'neutral', 'negative']
    colors = ["lightcoral", 'yellowgreen', 'cornflowerblue']
    font_color = ["firebrick", 'darkgreen', 'darkblue']
    plt.figure(figsize=(12, 8))
    patches, texts = plt.pie(x, labels=label, counterclock=True, startangle=90, colors=colors)
    for i in range(len(texts)):
        texts[i].set_size(48)
        texts[i].set_color(font_color[i])
    buf = io.BytesIO()
    plt.savefig(buf)
    qr_b64str = base64.b64encode(buf.getvalue()).decode("utf-8")
    b64_chart = "data:image/png;base64,{}".format(qr_b64str)
    return b64_chart


# 感情分析の結果を出力する
def emotion_count(cluster_tweets):
    count_dic = {}
    df_cluster = pd.read_csv(analyzed_csv, index_col=0)

    posi = (df_cluster['orientation'] == 'POSITIVE').sum()
    m_posi = (df_cluster['orientation'] == 'mostly_POSITIVE').sum()
    m_nega = (df_cluster['orientation'] == 'mostly_NEGATIVE').sum()
    nega = (df_cluster['orientation'] == 'NEGATIVE').sum()
    neut = len(df_cluster) - posi - m_posi - m_nega - nega
    count_dic['orientation'] = {'POSITIVE': posi, 'mostly_POSITIVE': m_posi, 'NEUTRAL': neut, 'mostly_NEGATIVE': m_nega, 'NEGATIVE': nega}

    pprint(count_dic)