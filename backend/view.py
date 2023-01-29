import os
import re
# import io
# import base64
import datetime as dt
import pickle
import csv
import copy
import requests
import json
import logging
import site
import concurrent.futures
import traceback

import numpy as np
# import pytz
from flask import session, request
from flask_restful import Resource, reqparse
from google.cloud import datastore, storage
from sudachipy import dictionary as suda_dict
from sudachipy import tokenizer
# from importlib.resources import Resource

from backend.clustering import clustering
from backend.util import download_from_cloud
from backend.emotion_analyze import emotion_analyze_all
from backend.retweet_network import analyze_network, get_retweet_keyword, datastore_upload_retweet, upload_analyzed_retweet, get_analyzed_network

#LOCAL_ENV = True
LOCAL_ENV = False
ONCE_TWEET_NUM = 15
# 除外するツイートのフレーズリストを取得
with open('backend/data/word_list/excluded_tweet.txt', 'r', encoding='utf-8') as f:
    EXCLUDED_TWEET = f.read().split('\n')

# regex to clean tweets
REGEXES = [
    re.compile(
        r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
    re.compile(" .*\.jp/.*$"),
    re.compile('@\S* '),
    re.compile('pic.twitter.*$'),
    re.compile(' .*ニュース$'),
    re.compile('[ 　]'),
    re.compile('\n')
]
URL_REGEX = re.compile(
    r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)")
SIGN_REGEX = re.compile(
    '[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF。、ー～！？!?()（）]')

ALGO = 'sudachi'
if ALGO == 'mecab':
    TOKENIZER_OBJ = MeCab.Tagger("-Ochasen")
elif ALGO == 'sudachi':
    TOKENIZER_OBJ = suda_dict.Dictionary(dict_type='full').create()
    SPLIT_MODE = tokenizer.Tokenizer.SplitMode.C  # 最も長い分割ルール

# TIMEZONE = pytz.timezone('Asia/Tokyo')
TIMEZONE = dt.timezone(dt.timedelta(hours=9), 'JST')

sess_info = {}  # global variable containing recent session information

logger = logging.getLogger(__name__)

# 全ツイートからサンプリングした単語の頻出度の辞書を読み込む
if LOCAL_ENV:
    with open('backend/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        DICT_ALL_COUNT = pickle.load(f)
    with open('backend/data/mecab_word2vec_dict_1d.pickle', 'rb') as f:
        # with open('backend/data/mecab_word2vec_dict_100d.pickle', 'rb') as f:
        word2vec = pickle.load(f)
else:
    logger.info('start loading dict_all_count')
    DICT_ALL_COUNT = download_from_cloud(storage.Client(), os.environ.get(
                'BUCKET_NAME'), os.environ.get('DICT_ALL_COUNT'))
    logger.info('finish loading dict_all_count')


class NoKeywordError(Exception):
    """検索可能な文字が含まれないキーワードの場合のエラー"""
    pass


class InvalidURLError(Exception):
    """Twitter APIにリクエストするURLが有効でない場合のエラー"""
    pass


class InvalidKeywordError(Exception):
    """Twitter APIにリクエストするキーワードが有効でない場合のエラー"""
    pass


class RunCollectRetweetJob(Resource):
    def post(self):
        logger.info('running collect retweet scheduler')
        # parser = reqparse.RequestParser()
        # parser.add_argument('keyword', type=str)
        # query_data = parser.parse_args()
        # keyword = query_data['keyword'].split(',')
        keyword = request.get_data(as_text=True).split(',')
        logger.info(f'keyword: {str(keyword)}')

        jst_delta = dt.timedelta(hours=9)
        JST = dt.timezone(jst_delta, 'JST')
        yesterday_dt = dt.datetime.now(JST) - dt.timedelta(days=1)
        since_date = yesterday_dt.strftime('%Y-%m-%d')
        yesterday = yesterday_dt.strftime('%Y/%m/%d')

        for i in range(len(keyword) // 2):
            k = keyword[i*2]
            # リツイートを取得する
            retweet = scrape_retweet(k, min_retweets=int(keyword[i*2 + 1]))
            if len(retweet) == 0:
                break
            # リツイートしたユーザーを取得する
            retweet = get_retweet_author(retweet, since_date)
            if len(retweet) == 0:
                break

            # リツイート情報をdatastoreに保存する
            datastore_upload_retweet(k, yesterday, retweet)

        return '', 200


# Twitter APIで現在のトレンドを取得する
class SearchTrend(Resource):
    def get(self):
        logger.info('get trend')
        trend_num = 5
        headers = create_headers()
        url = 'https://api.twitter.com/1.1/trends/place.json?id=23424856'
        trend_list = connect_to_endpoint(url, headers)[0]['trends']
        trend = [t['name'] for t in trend_list[:trend_num]]
        logger.info(trend)
        return trend


# Twitter APIで入力したキーワードを含むツイートを取得しツイートと感情分析結果を返す
class SearchAnalyze(Resource):
    def get(self):
        logger.info('start search analysis')
        global sess_info

        # ツイートを取得しワード数をカウントする
        session.permanent = True

        # ユーザーの直前のセッションの情報を削除
        if 'searched_at' in session and session['searched_at'] in sess_info:
            del sess_info[session['searched_at']]

        # セッションを区別するタイムスタンプを設定
        session['searched_at'] = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        logger.info(f'session timestamp: {session["searched_at"]}')
        searched_at_list = list(sess_info.keys())
        logger.info('count of remembered session: ' + str(len(searched_at_list)))

        # 記憶する直近のセッションを10個以内にする
        if len(searched_at_list) > 10:
            del sess_info[sorted(searched_at_list)[0]]
        sess_info[session['searched_at']] = {}
        sess_info_at = sess_info[session['searched_at']]

        logger.info('get tweet')
        parser = reqparse.RequestParser()
        parser.add_argument('keyword', type=str)
        parser.add_argument('tweetNum', type=int)
        query_data = parser.parse_args()
        keyword = query_data['keyword']
        tweet_num = query_data['tweetNum']
        sess_info_at['keyword'] = keyword
        sess_info_at['tweet_num'] = tweet_num
        logger.info(f'keyword: {keyword}, tweet_num: {tweet_num}')

        logger.info('scraping and cleaning tweets, counting words,  analyzing emotion\n')
        try:
            dict_word_count, tweets_list, time_hist, time_label = scrape_tweet(
                keyword, tweet_num)
        except InvalidKeywordError:
            return {"errorcode": 1}

        sess_info_at['tweets'] = tweets_list
        sess_info_at['tweet_time'] = {'hist': time_hist, 'label': time_label}
        logger.info('finish scraping tweets')

        if tweet_num > 1000:
            ignore_word_count = 10
        else:
            ignore_word_count = 5

        word_num_in_cloud = 100  # ワードクラウドで表示する単語数
        dict_word_count_rate = word_count_rate(
            dict_word_count, DICT_ALL_COUNT, word_num_in_cloud, tweet_num, ignore_word_count)
        sess_info_at['word_counts'] = list(dict_word_count_rate.items())
        sess_info_at['cluster_to_words'] = [{0: dict_word_count_rate}]

        topic_word_list = []
        for k, v in dict_word_count_rate.items():
            topic_word_list.append({"text": k, "value": v})

        emotion_ratio, emotion_tweet_dict, emotion_word = emotion_analyze_all(
            dict_word_count_rate.keys(), tweets_list)
        emotion_word_list = []
        for k, v in emotion_word.items():
            emotion_word_list.append({"text": k, "value": v})
        sess_info_at['emotion_tweet'] = [[emotion_tweet_dict]]
        sess_info_at['depth'] = 0

        # クライアントに渡す先頭のツイートを抽出
        isLoad = [{'positive': False, 'neutral': False, 'negative': False} for _ in range(4)]
        tweet = {}
        for emotion in ['positive', 'neutral', 'negative']:
            tweet[emotion] = {}
            retention_tweet = sess_info_at['emotion_tweet'][0][0][emotion]

            if ONCE_TWEET_NUM < len(retention_tweet):
                tweet[emotion] = retention_tweet[:ONCE_TWEET_NUM]
                isLoad[0][emotion] = True
            else:
                tweet[emotion] = retention_tweet
                isLoad[0][emotion] = False

        sess_info_at['isLoad'] = [isLoad]

        result = {"errorcode": 0,
                  "topicWord": [topic_word_list],
                  "emotionWord": [emotion_word_list],
                  "tweetedTime": {
                    "labels": time_label,
                    "datasets": [
                        {
                            "data": time_hist,
                            "backgroundColor": "dodgerblue",
                            "barPercentage": 1.2
                        }
                    ]
                  },
                  "emotionRatio": [
                    {
                      "labels": ["ネガティブ", "ニュートラル", "ポジティブ"],
                      "datasets": [
                        {
                          "label": "Data One",
                          "backgroundColor": ["#59a0f1", "#5bca78", "#e77181"],
                          "data": emotion_ratio[::-1]
                        }
                      ]
                    }
                  ],
                  "tweet": [tweet],
                  "isLoad": isLoad
                  }

        sess_info_at['cluster_result'] = [result]

        return result


# Twitter APIで入力したキーワードを含むツイートを取得しツイートと感情分析結果を返す
class SplitWc(Resource):
    def get(self):
        logger.info('split word cloud')
        sess_info_at = sess_info[session['searched_at']]
        depth = sess_info_at['depth']
        # 戻った状態で分割する時は以降の階層を削除
        if len(sess_info_at['cluster_result']) > depth + 1:
            del sess_info_at['cluster_result'][depth + 1:]
            del sess_info_at['emotion_tweet'][depth + 1:]
            del sess_info_at['isLoad'][depth + 1:]

        parser = reqparse.RequestParser()
        parser.add_argument('wcId', type=int)
        query_data = parser.parse_args()
        wc_id = query_data['wcId']
        clustered_words = sess_info_at['cluster_to_words'][depth]

        # クラスターが1つだけ
        if depth == 0:
            if LOCAL_ENV:
                top_word2vec = make_top_word2vec_dic(clustered_words[wc_id])
            else:
                top_word2vec = make_top_word2vec_dic_datastore(clustered_words[wc_id])
            sess_info_at['top_word2vec'] = top_word2vec
            sess_info_at['cluster_to_words'].append(clustering(top_word2vec))

        # クラスターが複数
        else:
            part_word2vec = make_part_word2vec_dic(clustered_words[wc_id], sess_info_at['top_word2vec'])
            split_cluster_to_words = clustering(part_word2vec)
            pre_cluster_to_words = copy.deepcopy(clustered_words)
            if len(sess_info_at['cluster_to_words']) == depth + 1:
                sess_info_at['cluster_to_words'].append(copy.deepcopy(clustered_words))
            else:
                sess_info_at['cluster_to_words'][depth+1] = copy.deepcopy(clustered_words)
            sess_info_at['cluster_to_words'][depth+1][wc_id] = split_cluster_to_words[0]
            sess_info_at['cluster_to_words'][depth+1][wc_id+1] = split_cluster_to_words[1]

            for i in range(wc_id+1, len(list(pre_cluster_to_words.keys()))):
                sess_info_at['cluster_to_words'][depth+1][i+1] = pre_cluster_to_words[i]

        sess_info_at['depth'] += 1
        depth = sess_info_at['depth']
        topic_word_list_list = []
        emotion_word_list_list = []
        emotion_ratio_list = []
        tweet_list = []
        cluster_to_words = sess_info_at['cluster_to_words'][sess_info_at['depth']]
        sess_info_at['emotion_tweet'].append([])
        sess_info_at['isLoad'].append([{'positive': False, 'neutral': False, 'negative': False} for _ in range(4)])

        for i in range(len(cluster_to_words)):  # cluster_to_wordsはリストではなくintをキーにした辞書のためenumerateできない
            topic_word_list_list.append([])
            for k, v in cluster_to_words[i].items():
                topic_word_list_list[-1].append({"text": k, "value": v})

            emotion_ratio, emotion_tweet_dict, emotion_word = emotion_analyze_all(
                cluster_to_words[i].keys(), sess_info_at['tweets'])
            sess_info_at['emotion_tweet'][-1].append(emotion_tweet_dict)
            emotion_ratio_list.append({
                      "labels": ["ネガティブ", "ニュートラル", "ポジティブ"],
                      "datasets": [
                        {
                          "label": "Data One",
                          "backgroundColor": ["#59a0f1", "#5bca78", "#e77181"],
                          "data": emotion_ratio[::-1]
                        }
                      ]
                    })
            emotion_word_list_list.append([])
            for k, v in emotion_word.items():
                emotion_word_list_list[-1].append({"text": k, "value": v})

            tweet = {}
            for emotion in ['positive', 'neutral', 'negative']:
                tweet[emotion] = {}
                retention_tweet = emotion_tweet_dict[emotion]

                if ONCE_TWEET_NUM < len(retention_tweet):
                    tweet[emotion] = retention_tweet[:ONCE_TWEET_NUM]
                    sess_info_at['isLoad'][depth][i][emotion] = True
                else:
                    tweet[emotion] = retention_tweet
                    sess_info_at['isLoad'][depth][i][emotion] = False

            tweet_list.append(tweet)
            
        result = {"topicWord": topic_word_list_list,
                  "emotionWord": emotion_word_list_list,
                  "emotionRatio": emotion_ratio_list,
                  "tweet": tweet_list,
                  "isLoad": sess_info_at['isLoad'][depth]
                  }

        sess_info_at['cluster_result'].append(result)

        return result


# EmotionBlock内の戻るボタンを押したときに1つ前の階層のクラスターを返す
class BackCluster(Resource):
    def get(self):
        logger.info('back cluster')
        sess_info_at = sess_info[session['searched_at']]
        sess_info_at['depth'] -= 1
        depth = sess_info_at['depth']

        # クラスターが1つだけ
        if depth == 0:
            if "tweetedTime" in sess_info_at['cluster_result'][depth]:
                del sess_info_at['cluster_result'][depth]["tweetedTime"]

        return sess_info_at['cluster_result'][depth]


# 感情分析済みのツイートを追加で返す
class LoadTweet(Resource):
    def get(self):
        logger.info('load more tweet')
        sess_info_at = sess_info[session['searched_at']]
        depth = sess_info_at['depth']

        parser = reqparse.RequestParser()
        parser.add_argument('wcId', type=int)
        parser.add_argument('emotion', type=str)
        parser.add_argument('tweetCnt', type=int)
        query_data = parser.parse_args()
        wc_id = query_data['wcId']
        emotion = query_data['emotion']
        tweet_cnt = query_data['tweetCnt']

        retention_tweet = sess_info_at['emotion_tweet'][depth][wc_id][emotion]
        if tweet_cnt + ONCE_TWEET_NUM < len(retention_tweet):
            add_tweet = retention_tweet[tweet_cnt: tweet_cnt + ONCE_TWEET_NUM]
            sess_info_at['isLoad'][depth][wc_id][emotion] = True
            isLoadOne = True
        else:
            add_tweet = retention_tweet[tweet_cnt:]
            sess_info_at['isLoad'][depth][wc_id][emotion] = False
            isLoadOne = False

        return {'addTweet': add_tweet, 'isLoadOne': isLoadOne}


# 収集済みのリツイートキーワードを取得
class InitRetweet(Resource):
    def get(self):
        return get_retweet_keyword(LOCAL_ENV)


# リツイートネットワークを作成
class AnalyzeNetwork(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('keyword', type=str)
        parser.add_argument('startDate', type=str)
        parser.add_argument('endDate', type=str)
        query_data = parser.parse_args()
        keyword = query_data['keyword']
        start_date = query_data['startDate']
        end_date = query_data['endDate']

        try:
            graph_dict, keyword, retweet, group_num = analyze_network(keyword, start_date, end_date, LOCAL_ENV=LOCAL_ENV)
            whole_word, group_word = make_word_cloud_node(keyword, retweet, group_num)
            result_dict = {"errorcode": 0, "graph": graph_dict, "wholeWord": whole_word, "groupWord": group_word}
        except:
            result_dict = {"errorcode": 1}

        # 処理時間計測のためdatastoreにUPして再取得する
        upload_analyzed_retweet(keyword, start_date, end_date, result_dict)
        result_dict = get_analyzed_network(keyword, start_date, end_date, result_dict)

        return result_dict


# 認証済みトークンのヘッダーを作成
def create_headers():
    tokens = [os.environ.get("TWITTER_BEARER_TOKEN1"),
              os.environ.get("TWITTER_BEARER_TOKEN2"),
              os.environ.get("TWITTER_BEARER_TOKEN3")]
    bearer_token = tokens[np.random.randint(0, len(tokens))]
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


# ツイートを取得するURLを作成
def create_url(keyword, next_token_id=None, max_results=10):
    # リツイート、リプライ、公式アカウント、広告を除外
    query = f'query={keyword} -is:retweet -is:reply -is:verified lang:ja'
    tweet_fields = "tweet.fields=author_id,created_at"
    mrf = "max_results={}".format(max_results)
    if next_token_id:
        next_token = 'next_token=' + next_token_id
        url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}&{}".format(
            query, tweet_fields, mrf, next_token
        )
    else:
        url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}".format(
            query, tweet_fields, mrf
        )

    return url.replace('#', '%23')  # ハッシュタグをURLエンコーディング


# リツイートを取得するURLを作成（リツイートはTwitter API v1.1でないと取得できない）
def create_url_retweet(keyword, next_results=None, max_results=10, min_retweets=3000):
    if next_results:
        url = f'https://api.twitter.com/1.1/search/tweets.json{next_results}'
    else:
        query = f'{keyword} lang:ja min_retweets:{min_retweets}'  # retweet
        url = f'https://api.twitter.com/1.1/search/tweets.json?q={query}&count={max_results}'
    return url.replace('#', '%23')  # ハッシュタグをURLエンコーディング


# リツイートを取得
def create_url_retweet_author(tweet, since_date=None, next_token_id=None, max_results=100):
    #url = f'https://api.twitter.com/1.1/statuses/retweeters/ids.json?id={tweet_id}&cursor={cursor}'
    # query = f'query="{tweet}" is:retweet -is:reply since:{since_date}_00:00:00_JST'  # retweet
    # query = f'query="{tweet}" is:retweet -is:reply'  # retweet
    #tweet_fields = "tweet.fields=author_id"
    #mrf = "max_results={}".format(max_results)
    #since = f"until={since_date}"
    if next_token_id:
        #next_token = 'next_token=' + next_token_id
        # url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}&{}".format(
        #query, tweet_fields, mrf, next_token
        # )
        # v1.1
        url = f'https://api.twitter.com/1.1/search/tweets.json{next_token_id}'
    else:
        # url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}&{}".format(
        #query, tweet_fields, mrf, since
        # )
        query = f'"{tweet}" since:{since_date}_03:00:00_JST'  # retweet
        url = f'https://api.twitter.com/1.1/search/tweets.json?q={query}&count={max_results}'

    return url.replace('#', '%23')  # ハッシュタグをURLエンコーディング


# Twitter APIで情報を取得
def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        if json.loads(response.text)['errors'][0]['code'] == 195:
            raise InvalidURLError(response.text)
        else:
            raise Exception(response.status_code, response.text)
    return response.json()


# ツイートの取得、クリーン、名詞抽出・カウント
def scrape_tweet(keyword, max_tweets, algo='sudachi'):
    print('-------------- scrape start -----------------\n')
    headers = create_headers()

    # 先頭と末尾のスペース、末尾の#を除去し、間のスペースをORに変換する
    # keyword = re.sub('^[ 　]+|[ 　]+$', '', keyword)  # フロント側で処理
    keyword = re.sub('[ 　]+', ' OR ', keyword)
    # keyword = re.sub('[#]+$', '', keyword)  # フロント側で処理
    # if keyword == '':
    #     raise NoKeywordError  # フロント側で処理

    dict_word_count = {}
    next_token_id = None
    max_results = 100  # 1度のリクエストで取得するツイート数
    exclude_flag = False
    tweets_list = []
    past_tweets = []
    # time_list = []
    time_array = np.empty(0)

    for i in range(max_tweets // max_results + 1):
        if i == max_tweets // max_results:
            max_results = max_tweets % max_results
            if max_results < 10:
                break

        logger.info('start scraping')
        url = create_url(keyword, next_token_id, max_results)
        try:
            result = connect_to_endpoint(url, headers)
        except:
            raise InvalidKeywordError

        logger.info('start word count tweet')

        for j in range(len(result['data'])):
            tweet_text = result['data'][j]['text']
            tweet_no_URL = URL_REGEX.sub('', tweet_text)
            if tweet_no_URL in past_tweets:
                continue
            else:
                past_tweets.append(tweet_no_URL)

            try:
                # created_at_UTC = dt.datetime.strptime(
                created_at = dt.datetime.strptime(
                    result['data'][j]['created_at'][:-1] + "+0000", '%Y-%m-%dT%H:%M:%S.%f%z')
            except IndexError:
                continue
            # created_at = created_at_UTC.astimezone(
            #    dt.timezone(dt.timedelta(hours=+9)))
            # time_list.append(created_at)
            time_array = np.append(time_array, created_at.timestamp())

            # 特定フレーズを含むツイートを除外
            for w in EXCLUDED_TWEET:
                if w in tweet_text:
                    exclude_flag = True
                    break
            if exclude_flag:
                exclude_flag = False
                continue

            # clean tweet
            # logger.info('clean tweet')
            tweet_text = clean(tweet_text, REGEXES, SIGN_REGEX)

            # update noun count dictionary
            # logger.info('noun count')
            dict_word_count, split_word = noun_count(
                tweet_text, dict_word_count, TOKENIZER_OBJ, SPLIT_MODE, keyword)

            tweets_list.append([created_at, tweet_no_URL, split_word])

        if 'next_token' in result['meta']:
            next_token_id = result['meta']['next_token']
        else:
            break

    # ツイート日時のヒストグラムを作る
    time_hist, time_label = make_time_hist(time_array)

    logger.info('-------------- scrape finish -----------------\n')

    return dict_word_count, tweets_list, time_hist, time_label


# 正規表現でツイート中の不要文字を除去する
def clean(text, regexes, sign_regex):
    try:
        for regex in regexes:
            text = regex.sub('', text)

        text = sign_regex.sub('。', text)
        text = re.sub('。+', "。", text)
        return text

    except (KeyError, TypeError):
        return text


# 辞書型を使って名詞をカウントする
def noun_count(text, dict_word_count, tokenizer_obj, mode=None, keyword=None, algo='sudachi'):
    split_word = []
    try:
        if algo == 'mecab':
            words = tokenizer_obj.parse(text).split("\n")
        elif algo == 'sudachi':
            words = tokenizer_obj.tokenize(text, mode)

    except (KeyError, TypeError):
        return dict_word_count

    for j in range(len(words)):
        if algo == 'mecab':
            word_info = words[j].split("\t")
            if (len(word_info) == 1 or word_info[0] == keyword):
                continue
            noun = word_info[0]
            part = word_info[3][:2]

        elif algo == 'sudachi':
            word = words[j].normalized_form()
            split_word.append(word)
            if (word == keyword):
                continue
            part = words[j].part_of_speech()[0]

        if (part == "名詞"):
            if (word in dict_word_count.keys()):
                dict_word_count[word] += 1
            else:
                dict_word_count[word] = 1

    return dict_word_count, str(split_word)


# ツイート日時のヒストグラムを作る
def make_time_hist(time_array):
    hist, bins = np.histogram(time_array)
    time_label = ['' for _ in range(10)]
    dif_bins = bins[-1] - bins[0]

    if dif_bins < 60:
        time_label_end_dt = dt.datetime.fromtimestamp(bins[-1], tz=TIMEZONE)
        time_label[-1] = time_label_end_dt.strftime('%H:%M')
        time_label_start_dt = time_label_end_dt - dt.timedelta(minutes=1)
        time_label[0] = time_label_start_dt.strftime('%H:%M')
    elif dif_bins < 60 * 10:
        time_label[0] = dt.datetime.fromtimestamp(bins[0], tz=TIMEZONE).strftime('%H:%M')
        time_label[-1] = dt.datetime.fromtimestamp(bins[-1], tz=TIMEZONE).strftime('%H:%M')
    elif dif_bins < 60 * 30:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:%M')
        round_m = 10
        round_start_m = int(
            np.round(float(time_label_start[-2:]) / round_m + 0.4) * round_m)  # 5分単位で繰り上げ
        round_start_h = int(time_label_start[-5:-3])
        if round_start_m == 60:
            round_start_h += 1
            round_start_m = 0
        round_start_dt = dt.datetime.strptime(
            f'{time_label_start[:-5]}{round_start_h}:{round_start_m}', '%Y/%m/%d %H:%M').astimezone(TIMEZONE)

        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(minutes=round_m)

    elif dif_bins < 60 * 60:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:%M')
        round_m = 20
        round_start_m = int(
            np.round(float(time_label_start[-2:]) / round_m + 0.4) * round_m)  # 10分単位で繰り上げ
        round_start_h = int(time_label_start[-5:-3])
        if round_start_m == 60:
            round_start_h += 1
            round_start_m = 0
        round_start_dt = dt.datetime.strptime(
            f'{time_label_start[:-5]}{round_start_h}:{round_start_m}', '%Y/%m/%d %H:%M').astimezone(TIMEZONE)

        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(minutes=round_m)

    elif dif_bins < 60 * 60 * 3:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:00')
        round_start_dt = dt.datetime.strptime(
            time_label_start, '%Y/%m/%d %H:%M').astimezone(TIMEZONE)
        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(hours=1)

    elif dif_bins < 60 * 60 * 6:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:00')
        round_h = 2
        round_start_h = int(np.round(
            float(time_label_start[-5:-3]) / round_h + 0.4) * round_h)  # 2h単位で繰り上げ
        round_start_dt = dt.datetime.strptime(
            f'{time_label_start[:-5]}{round_start_h}:00', '%Y/%m/%d %H:%M').astimezone(TIMEZONE)

        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(hours=round_h)

    elif dif_bins < 60 * 60 * 12:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:00')
        round_h = 4
        round_start_h = int(np.round(
            float(time_label_start[-5:-3]) / round_h + 0.4) * round_h)  # 4h単位で繰り上げ
        round_start_dt = dt.datetime.strptime(
            f'{time_label_start[:-5]}{round_start_h}:00', '%Y/%m/%d %H:%M').astimezone(TIMEZONE)

        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(hours=round_h)

    elif dif_bins < 60 * 60 * 24:
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d %H:00')
        round_h = 8
        round_start_h = int(np.round(
            float(time_label_start[-5:-3]) / round_h + 0.4) * round_h)  # 8h単位で繰り上げ
        round_start_dt = dt.datetime.strptime(
            f'{time_label_start[:-5]}{round_start_h}:00', '%Y/%m/%d %H:%M').astimezone(TIMEZONE)

        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%H:%M')
                round_dt = round_dt + dt.timedelta(hours=round_h)

    else:  # 1日以上7日未満
        time_label_start = dt.datetime.fromtimestamp(
            bins[0], tz=TIMEZONE).strftime('%Y/%m/%d 00:00')
        round_start_dt = dt.datetime.strptime(
            time_label_start, '%Y/%m/%d %H:%M').astimezone(TIMEZONE)
        round_dt = round_start_dt
        for i, bin in enumerate(bins[1:]):
            bin_dt = dt.datetime.fromtimestamp(bin, tz=TIMEZONE)
            td = bin_dt - round_dt
            if td.days >= 0:
                time_label[i] = round_dt.strftime('%m/%d')
                round_dt = round_dt + dt.timedelta(days=1)

    hist = [int(h) for h in hist]
    return hist, time_label


# 特定キーワードと同時にツイートされる名詞のカウント数を、全てのツイートにおける名詞のカウント数で割る
# （相対頻出度を計算する）
def word_count_rate(dict_word_count, dict_all_count, word_num_in_cloud=20, max_tweets=100, ignore_word_count=5, word_length=20, thre_word_count_rate=3):
    logger.info('------------ word count rate start --------------')
    dict_word_count = dict(
        sorted(dict_word_count.items(), key=lambda x: x[1], reverse=True))
    dict_word_count_rate = {}

    # 除外単語リストを取得
    with open('backend/data/word_list/excluded_word.txt', 'r', encoding='utf-8') as f:
        excluded_word = f.read().split('\n')
    with open('backend/data/word_list/excluded_char.txt', 'r', encoding='utf-8') as f:
        excluded_char = f.read().split('\n')

    for word in dict_word_count.keys():
        # 出現頻度の低い単語は無視
        if dict_word_count[word] < ignore_word_count:
            break

        if (word in dict_all_count.keys()):
            all_count = dict_all_count[word]
        else:
            all_count = 0

        try:
            # 1以下のカウントはwordcloudで認識されないため最後に1を足す
            dict_word_count_rate[word] = float(
                dict_word_count[word]) / (float(all_count)/(1000000/max_tweets) + 1) + 1
        except TypeError:
            continue

    dict_word_count_rate = dict(
        sorted(dict_word_count_rate.items(), key=lambda x: x[1], reverse=True))
    extract_dict = {}

    # 相対出現頻度が高いワードからword_num_in_cloud個抽出
    for w in dict_word_count_rate.keys():
        if OKword(w, excluded_word, excluded_char) and len(w) < word_length and dict_word_count_rate[w] > thre_word_count_rate:
            extract_dict[w] = dict_word_count_rate[w]
            if len(extract_dict) >= word_num_in_cloud:
                break

    logger.info('------------ word count rate finish --------------')
    return extract_dict


# word_count_rate（相対頻出度）の大きい単語にword2vecを当てはめる
def make_top_word2vec_dic(dict_word_count_rate):
    logger.info(
        '-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [],
                         'word_count_rate': [], 'not_dict_word': {}}
    all_word_list = list(word2vec.keys())

    for word in dict_word_count_rate.keys():
        logger.info(word)

        if word in all_word_list:
            dict_top_word2vec['word'].append(word)
            dict_top_word2vec['vec'].append(word2vec[word])
            dict_top_word2vec['word_count_rate'].append(
                dict_word_count_rate[word])
        else:
            dict_top_word2vec['not_dict_word'][word] = dict_word_count_rate[word]

    logger.info(
        '-------------- making dict_top_word2vec finish -----------------\n')
    return dict_top_word2vec


def make_top_word2vec_dic_datastore(dict_word_count_rate):
    logger.info(
        '-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [],
                         'word_count_rate': [], 'not_dict_word': {}}
    client = datastore.Client()
    keys = []

    for word in dict_word_count_rate.keys():
        logger.info(word)
        keys.append(client.key('mecab_word2vec_100d', word))

    logger.info('entities')
    entities = client.get_multi(keys)  # 複数ワードのword2vecをクラウドからダウンロード
    logger.info('get multi word2vec')

    vec_exist_words = []
    for entity in entities:
        vec_exist_words.append(entity.key.name)

    # ツイート頻出ワードのベクトルがあるかチェック
    for word in dict_word_count_rate.keys():
        if word in vec_exist_words:
            logger.info('vec exist: ' + word)
            dict_top_word2vec['word'].append(word)
            entity = entities[vec_exist_words.index(word)]
            dict_top_word2vec['vec'].append(np.array(entity['vec']))
            dict_top_word2vec['word_count_rate'].append(
                dict_word_count_rate[word])
        else:
            logger.info('vec not exist: ' + word)
            dict_top_word2vec['not_dict_word'][word] = dict_word_count_rate[word]

    logger.info(
        '-------------- making dict_top_word2vec finish -----------------\n')

    return dict_top_word2vec


# word_count_rate（相対頻出度）の大きい単語にword2vecを当てはめる
def make_part_word2vec_dic(dict_word_count_rate, top_word2vec):
    logger.info(
        '-------------- making dict_part_word2vec start -----------------\n')

    dict_part_word2vec = {'word': [], 'vec': [],
                          'word_count_rate': [], 'not_dict_word': []}

    for word in dict_word_count_rate.keys():
        logger.info(word)
        word_idx = top_word2vec['word'].index(word)
        dict_part_word2vec['word'].append(word)
        dict_part_word2vec['vec'].append(top_word2vec['vec'][word_idx])
        dict_part_word2vec['word_count_rate'].append(
            top_word2vec['word_count_rate'][word_idx])

    logger.info(
        '-------------- making dict_part_word2vec finish -----------------\n')

    return dict_part_word2vec


# 汎用性の高い単語を除外する
def OKword(word, excluded_word, excluded_char):
    if word in excluded_word:
        return False

    for c in excluded_char:
        if c in word:
            return False

    return True


# リツイートの取得
def scrape_retweet(keyword, min_retweets=1500, max_tweets=1000):
    logger.info('-------------- scrape start -----------------\n')
    headers = create_headers()

    URL_regex = re.compile(
        r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)")

    # 先頭と末尾のスペースを除去し、間のスペースをORに変換する
    keyword = re.sub('^[ 　]+|[ 　]+$', '', keyword)
    keyword = re.sub('[ 　]+', ' OR ', keyword)

    next_results = None
    max_results = 100  # 1度のリクエストで取得するツイート数
    exclude_flag = False
    past_tweets = []
    retweet = []

    for i in range(max_tweets // max_results):
        logger.info('start scraping')
        url = create_url_retweet(
            keyword, next_results, max_results=max_results, min_retweets=min_retweets)
        try:
            result = connect_to_endpoint(url, headers)
        except:
            logger.info('Unpredicted Error')
            logger.info(traceback.format_exc())
            return retweet

        logger.info(f"{len(result['statuses'])} tweet")

        # これ以上リツイートがない場合
        if 'next_results' not in result['search_metadata']:
            break

        for res in result['statuses']:
            tweet_text = res['text']

            # 特定フレーズを含むツイートを除外
            for w in EXCLUDED_TWEET:
                if w in tweet_text:
                    exclude_flag = True
                    break
            if exclude_flag:
                exclude_flag = False
                continue

            tweet_no_URL = URL_regex.sub('', tweet_text)
            if tweet_no_URL in past_tweets:
                continue
            else:
                past_tweets.append(tweet_no_URL)

            retweet.append({'tweet_id': res['id'], 'author': res['user']['name'],
                            'text': tweet_no_URL, 'count': res["retweet_count"]})
            logger.info(
                f'retweet_count: {res["retweet_count"]}, {res["created_at"]}')

        next_results = result['search_metadata']['next_results']

    return retweet


# Twitter APIでツイートで検索するため名詞まで抽出
def stop_noun(text, tokenizer_obj, mode):
    words = list(tokenizer_obj.tokenize(text, mode))
    noun_cnt = 0
    for w in reversed(words):
        if w.part_of_speech()[0] == '名詞':
            noun_cnt += 1
            if noun_cnt > 1 and not str(w).isdigit():
                text = text[:text.rfind(str(w)) + len(str(w))]
                return text
            else:
                text = text[:text.rfind(str(w))]

    return ''


def make_word_cloud_node(keyword, retweet, group_num, algo='sudachi'):
    logger.info('start make_word_cloud_node')
    whole_word_count = {}
    group_word_count = [{} for _ in range(group_num)]

    for r in retweet:
        whole_word_count, _ = noun_count(r['text'], whole_word_count,
                                         TOKENIZER_OBJ, SPLIT_MODE, keyword)
        group_word_count[r['group']], _ = noun_count(r['text'], group_word_count[r['group']],
                                                     TOKENIZER_OBJ, SPLIT_MODE, keyword)

    whole_word = word_count_rate(whole_word_count,
                                 DICT_ALL_COUNT, word_num_in_cloud=20,
                                 max_tweets=len(retweet),
                                 thre_word_count_rate=0,
                                 ignore_word_count=0)

    whole_word_list = []
    for k, v in whole_word.items():
        whole_word_list.append({"text": k, "value": v})

    group_word_list = []
    for i in range(group_num):
        group_word_list.append([])
        group_word = word_count_rate(group_word_count[i],
                                     DICT_ALL_COUNT, word_num_in_cloud=20,
                                     max_tweets=len(retweet),
                                     thre_word_count_rate=0,
                                     ignore_word_count=0)

        for k, v in group_word.items():
            group_word_list[-1].append({"text": k, "value": 2 * v})

    group_word_list.append([{"text": "", "value": 1}])

    logger.info('finish make_word_cloud_node')

    return whole_word_list, group_word_list


# リツイートしたユーザーIDを取得する
def get_retweet_author(retweet, since_date, max_scrape_retweet=2000, thre_retweet_cnt=200, max_trial=30):
    logger.info('get retweet user\n')
    sign_regex = re.compile(
        '[^\r\n0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF。、ー～！？!?()（）【】]')

    retweet_OK = []
    for i, r in enumerate(retweet):
        # debug
        # if i > 10:
        # break

        headers = create_headers()
        logger.info(f"{i+1} / {len(retweet)}, retweet count: {r['count']}")
        t = r['text']
        next_token_id = None

        if '#' in t:
            t = t[:t.find('#')]

        if t == ' ' or len(t) < 3:
            logger.info(f"extract few string '{r['text']}'")
            continue

        t = stop_noun(t, TOKENIZER_OBJ, SPLIT_MODE)

        t = sign_regex.sub(' ', t)
        t = re.sub('[ 　]+', ' ', t)
        if t == ' ' or len(t) < 3:
            logger.info(f"extract few string '{r['text']}'")
            continue

        r['re_author'] = []
        k = 0
        extract_cnt = 0

        for j in range(max_trial):
            if k > max_scrape_retweet // 100:
                break

            url = create_url_retweet_author(t, since_date, next_token_id)
            #result = connect_to_endpoint(url, headers)

            # if 'data' in result:
            try:
                result = connect_to_endpoint(url, headers)
                k += 1
            # else:
            except InvalidURLError:
                # logger.info(traceback.format_exc())
                t = stop_noun(t, TOKENIZER_OBJ, SPLIT_MODE)
                if t == ' ' or len(t) < 3:
                    logger.info(f"extract few string '{t}'")
                    break
                else:
                    extract_cnt += 1
                    continue
            except:
                logger.info('Unpredicted Error')
                logger.info(traceback.format_exc())
                break

            # for res in result['data']:
            for res in result['statuses']:
                r['re_author'].append(res['user']['id'])

            # if 'next_token' in result['meta']:
                #next_token_id = result['meta']['next_token']
            # これ以上リツイートがない場合
            if 'next_results' in result['search_metadata']:
                next_token_id = result['search_metadata']['next_results']
            else:
                break

        if len(r['re_author']) > thre_retweet_cnt:
            retweet_OK.append(r)
        else:
            logger.info(f"extract count: {extract_cnt}\n"
                        f"few retweet count: {len(r['re_author'])}\n"
                        f"cannot search '{t}'")

    return retweet_OK


##################### 以下使わない関数 ######################

def scrape(keyword, max_tweets, since, until, checkpoint_cnt=10000, algo='sudachi'):
    print('-------------- scrape start -----------------\n')

    dt_until = dt.datetime.strptime(until, '%Y-%m-%d')
    dt_since = dt.datetime.strptime(since, '%Y-%m-%d')

    # regex to clean tweets
    regexes = [
        re.compile(
            r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
        re.compile(" .*\.jp/.*$"),
        re.compile('@\S* '),
        re.compile('pic.twitter.*$'),
        re.compile(' .*ニュース$'),
        re.compile('[ 　]'),
        re.compile('\n')
    ]
    sign_regex = re.compile(
        '[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF。、ー～！？!?()（）]')

    if algo == 'mecab':
        m = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        tokenizer_obj = suda_dict.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C

    i = 0
    already_tweets = []
    tweets = []
    dict_word_count = {}
    word_count_list = []

    for _, tweet in enumerate(sntwitter.TwitterSearchScraper(keyword + 'since:' + since + ' until:' + until).get_items()):
        dt_naive = tweet.date.replace(tzinfo=None)

        # (snscrapeのバグにより)指定した期間内でない、またはキーワードを含まないツイートを除外
        if ((dt_naive < dt_since) or (dt_until < dt_naive) or (keyword not in tweet.content)):
            continue

        # RTを除外
        if tweet.content in already_tweets:
            continue
        else:
            already_tweets.append(tweet.content)

        tweets.append(Tweet(tweeted_at=tweet.date, text=tweet.content))

        tweet_text = tweet.content
        # clean tweet
        #tweet_text = clean(tweet_text, regexes, sign_regex)

        # update noun count dictionary
        dict_word_count = noun_count(tweet_text, dict_word_count, keyword)

        if (i+1) == max_tweets:
            db_session().add_all(tweets)
            db_session().commit()
            break

        i += 1

    for k in dict_word_count.keys():
        word_count_list.append(WordCount(word=k, count=dict_word_count[k]))

    print('-------------- scrape finish -----------------\n')

    return dict_word_count


def scrape_next_tweets(max_results, keyword, headers, next_token_id):
    url = create_url(keyword, next_token_id, max_results)
    tweets_result = connect_to_endpoint(url, headers)
    return tweets_result

# マルチスレッド・コアでツイートの取得、クリーン、名詞抽出・カウント
# マルチスレッドはリクエスト待ちでも速くならない
# マルチコアはsudachipyでは無理


def scrape_token_multi_thread(keyword, max_tweets, algo='sudachi'):
    print('-------------- scrape start -----------------\n')
    bearer_token = auth()
    headers = create_headers(bearer_token)

    # regex to clean tweets
    regexes = [
        re.compile(
            r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
        re.compile(" .*\.jp/.*$"),
        re.compile('@\S* '),
        re.compile('pic.twitter.*$'),
        re.compile(' .*ニュース$'),
        re.compile('[ 　]'),
        re.compile('\n')
    ]
    sign_regex = re.compile(
        '[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF。、ー～！？!?()（）]')

    if algo == 'mecab':
        tokenizer_obj = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        lib_path = site.getsitepackages()
        logger.info(lib_path)
        try:
            tokenizer_obj = suda_dict.Dictionary(
                config_path='crover/data/sudachi.json', resource_dir=os.path.join(lib_path[0], 'sudachipy/resources')).create()
        except:
            tokenizer_obj = suda_dict.Dictionary(config_path='crover/data/sudachi.json',
                                                 resource_dir=os.path.join(lib_path[-1], 'sudachipy/resources')).create()

        mode = tokenizer.Tokenizer.SplitMode.C

    dict_word_count = {}
    next_token_id = None
    max_results = 100

    tweets = []
    tweets_info_tasks = []
    tweets_info_list = []
    # with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor: # multi thread
    # multi core
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        for i in range(max_tweets // max_results + 1):
            if i == max_tweets // max_results:
                max_results = max_tweets % max_results
                if max_results < 10:
                    break

            logger.info('start scraping')
            #url = create_url(keyword, next_token_id, max_results)
            #result = connect_to_endpoint(url, headers)

            tweets.append(executor.submit(scrape_next_tweets,
                          max_results, keyword, headers, next_token_id))

            if i > 0:
                tweets_info, dict_word_count = tweets_info_tasks[-1].result()
                #tweets_info = tweets_info_tasks[-1].result()
                tweets_info_list.extend(tweets_info)

            logger.info('start word count tweet')
            tweets_info_tasks.append(executor.submit(word_count, tweets[-1].result(
            ), regexes, sign_regex, tokenizer_obj, mode, keyword, dict_word_count))

            result = tweets[-1].result()
            if 'next_token' in result['meta']:
                next_token_id = result['meta']['next_token']
            else:
                break

    tweets_info, dict_word_count = tweets_info_tasks[-1].result()
    #tweets_info = tweets_info_tasks[-1].result()
    tweets_info_list.extend(tweets_info)
    #tweets_info_list = tweets_info_tasks[0].result()
    # for i in range(1, len(tweets_info_tasks)):
    #    tweets_info_list.extend(tweets_info_tasks[i].result())
    #tweets_info_list = [x.result() for x in tweets_info_tasks]
    logger.info('-------------- scrape finish -----------------\n')

    return dict_word_count, tweets_info_list


# word_count_rateを算出するため、日本語の全ツイートをランダムサンプリングする
def scrapeAll(output_name, max_tweets, until):
    all_hiragana = "したとにのれんいうか"  # 出現頻度の高いひらがな
    dt_until = dt.datetime.strptime(until, '%Y-%m-%d')
    timedelta = dt.timedelta(days=1)
    df_tweets = pd.DataFrame(columns=['date', 'tweet', 'outlink'], dtype=str)

    if os.path.exists(output_name):
        print("already exist!")
        return
    else:
        df_tweets.to_csv(output_name)

    for i in tqdm(range(max_tweets//10000)):
        dt_since = dt_until - timedelta
        keyword = all_hiragana[i % len(keyword_all)]
        scrape(output_name, keyword, 10000, dt_since.strftime(
            '%Y-%m-%d'), dt_until.strftime('%Y-%m-%d'))
        dt_until -= timedelta


def word_count_old(result, regexes, sign_regex, tokenizer_obj, mode, keyword, dict_word_count):
    #result = tweets.result()
    tweets_info = []
    for j in range(len(result['data'])):
        try:
            created_at_UTC = dt.datetime.strptime(result['data'][j]['created_at'][:-1] + "+0000",
                                                  '%Y-%m-%dT%H:%M:%S.%f%z')
        except IndexError:
            continue
        created_at = created_at_UTC.astimezone(
            dt.timezone(dt.timedelta(hours=+9)))

        tweet_text = result['data'][j]['text']
        # clean tweet
        # logger.info('clean tweet')
        tweet_text = clean(tweet_text, regexes, sign_regex)

        # update noun count dictionary
        # logger.info('noun count')
        dict_word_count, split_word = noun_count(
            tweet_text, dict_word_count, tokenizer_obj, mode, keyword)

        tweets_info.append([created_at, result['data'][j]['text'], split_word])

    return tweets_info, dict_word_count
    # return tweets_info

# load all word count from datastore


def word_count_rate_datastore(dict_word_count, top_word_num=20, max_tweets=100, ignore_word_count=5):
    print('------------ word count rate start --------------')
    client = datastore.Client()
    keys = []

    for word in dict_word_count.keys():
        logger.info(word)
        keys.append(client.key('sudachi_all_word_count', word))

    logger.info('entities')
    entities = client.get_multi(keys)
    logger.info('get multi word2vec')

    count_exist_words = []
    for entity in entities:
        count_exist_words.append(entity.key.name)
    print(count_exist_words)

    dict_word_count = dict(
        sorted(dict_word_count.items(), key=lambda x: x[1], reverse=True))
    dict_word_count_rate = {}
    for word in dict_word_count.keys():
        # 出現頻度の低い単語は無視
        if dict_word_count[word] < ignore_word_count:
            break

        # if (word in dict_all_count.keys()):
        if word in count_exist_words:
            all_count = entities[count_exist_words.index(word)]['count']
        else:
            all_count = 0

        try:
            dict_word_count_rate[word] = float(
                dict_word_count[word]) / (float(all_count)/(1000000/max_tweets) + 1)
        except TypeError:
            continue

    dict_word_count_rate = dict(
        sorted(dict_word_count_rate.items(), key=lambda x: x[1], reverse=True))
    i = 0
    extract_dict = {}
    word_rate_list = []
    for w in dict_word_count_rate.keys():
        if OKword(w):
            extract_dict[w] = dict_word_count_rate[w]
            word_rate_list.append(
                WordCount(word=w, relative_frequent_rate=dict_word_count_rate[w]))
            i += 1
            if i >= top_word_num:
                break

    db_session().add_all(word_rate_list)
    db_session().commit()

    print('------------ word count rate finish --------------')
    return extract_dict


def sudachi_test():
    tokenizer_obj = suda_dict.Dictionary().create()
    mode = tokenizer.Tokenizer.SplitMode.C
    text = '吉岡里帆が赤いきつねを食べる。'
    for t in tokenizer_obj.tokenize(text, mode):
        print(t.surface(), t.part_of_speech(),
              t.reading_form(), t.normalized_form())


def make_sudachi_pickle(path, sudachiDataPath="sudachiData.pickle"):
    f = open(path, 'r')
    reader = csv.reader(f, delimiter=' ')
    # 最初に含有単語リストやメモリアドレスリストを作成する（かなり時間かかる）
    # 2回目以降はpickle化したものを読み込む
    if os.path.exists(sudachiDataPath):
        with open(sudachiDataPath, 'rb') as f:
            dataset = pickle.load(f)
        offset_list = dataset["offset_list"]
        emb_size = dataset["emb_size"]
        word2index = dataset["word2index"]
        ave_vec = dataset["ave_vec"]
    else:
        txt = f.readline()
        # 分散表現の次元数
        emb_size = int(txt.split()[1])
        # 未知語が来た場合平均ベクトルを返す
        ave_vec = np.zeros(emb_size, np.float)
        # メモリアドレスリスト
        offset_list = []
        word_list = []
        count = 0
        maxCount = int(txt.split()[0])
        while True:
            count += 1
            offset_list.append(f.tell())
            if count % 100000 == 0:
                print(count, "/", maxCount)
            line = f.readline()
            if line == '':
                break
            line_list = line.split()
            word_list.append(line_list[0])
            ave_vec += np.array(line_list[-300:]).astype(np.float)
        offset_list.pop()
        ave_vec = ave_vec / count
        word2index = {v: k for k, v in enumerate(word_list)}

        dataset = {}
        dataset["offset_list"] = offset_list
        dataset["emb_size"] = emb_size
        dataset["word2index"] = word2index
        dataset["ave_vec"] = ave_vec
        with open(sudachiDataPath, 'wb') as f:
            pickle.dump(dataset, f)
