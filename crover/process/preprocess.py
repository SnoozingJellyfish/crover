import copy
import os
import re
import io
import base64
import datetime as dt
import pickle
import csv
import requests
import json
import logging
import site
import concurrent.futures
import traceback

import numpy as np
import matplotlib
matplotlib.rcParams['timezone'] = 'Asia/Tokyo'
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
plt.rcParams["font.size"] = 18
from sudachipy import tokenizer
from sudachipy import dictionary as suda_dict
from google.cloud import datastore, storage

from crover import LOCAL_ENV
from crover.process.util import download_from_cloud
if LOCAL_ENV:
    from crover import dict_all_count, word2vec
    plt.rcParams['font.family'] = 'Hiragino Sans GB'
else:
    plt.rcParams['font.family'] = 'IPAPGothic'

logger = logging.getLogger(__name__)


class NoKeywordError(Exception):
    """検索可能な文字が含まれないキーワードの場合のエラー"""
    pass

def get_trend(trend_num=5):
    logger.info('get trend')
    headers = create_headers()
    url = 'https://api.twitter.com/1.1/trends/place.json?id=23424856'
    trend_list = connect_to_endpoint(url, headers)[0]['trends']
    trend = [t['name'] for t in trend_list[:trend_num]]

    return trend

def preprocess_all(keyword, max_tweets, word_num_in_cloud):
    logger.info('all preprocesses will be done. \n(scrape and cleaning tweets, counting words, making word2vec dictionary)\n')

    dict_word_count, tweets_list, b64_time_hist = scrape_tweet(keyword, max_tweets)
    logger.info('finish scraping tweets')
    if not LOCAL_ENV:
        logger.info('start loading dict_all_count')
        dict_all_count = download_from_cloud(storage.Client(), os.environ.get('BUCKET_NAME'), os.environ.get('DICT_ALL_COUNT'))
        logger.info('finish loading dict_all_count')
    else:
        from crover import dict_all_count

    if max_tweets > 1000:
        ignore_word_count = 10
    else:
        ignore_word_count = 5
    dict_word_count_rate = word_count_rate(dict_word_count, dict_all_count, word_num_in_cloud, max_tweets, ignore_word_count)
    return dict_word_count_rate, tweets_list, b64_time_hist

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
def create_url_retweet(keyword, next_results=None, max_results=10, min_retweets=1000):
    if next_results:
        url = f'https://api.twitter.com/1.1/search/tweets.json{next_results}'
    else:
        query = f'{keyword} lang:ja min_retweets:{min_retweets}'  # retweet
        url = f'https://api.twitter.com/1.1/search/tweets.json?q={query}&count={max_results}'
    return url.replace('#', '%23')  # ハッシュタグをURLエンコーディング

# リツイートを取得
def create_url_retweet_author(tweet, since_date=None, next_token_id=None, max_results=100):
    #url = f'https://api.twitter.com/1.1/statuses/retweeters/ids.json?id={tweet_id}&cursor={cursor}'
    #query = f'query="{tweet}" is:retweet -is:reply since:{since_date}_00:00:00_JST'  # retweet
    #query = f'query="{tweet}" is:retweet -is:reply'  # retweet
    #tweet_fields = "tweet.fields=author_id"
    #mrf = "max_results={}".format(max_results)
    #since = f"until={since_date}"
    if next_token_id:
        #next_token = 'next_token=' + next_token_id
        #url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}&{}".format(
            #query, tweet_fields, mrf, next_token
        #)
        url = f'https://api.twitter.com/1.1/search/tweets.json{next_token_id}'  # v1.1
    else:
        #url = "https://api.twitter.com/2/tweets/search/recent?{}&{}&{}&{}".format(
            #query, tweet_fields, mrf, since
        #)
        query = f'"{tweet}" since:{since_date}_00:00:00_JST'  # retweet
        url = f'https://api.twitter.com/1.1/search/tweets.json?q={query}&count={max_results}'

    return url.replace('#', '%23')  # ハッシュタグをURLエンコーディング

# Twitter APIで情報を取得
def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()

# ツイートの取得、クリーン、名詞抽出・カウント、
def scrape_tweet(keyword, max_tweets, algo='sudachi'):
    print('-------------- scrape start -----------------\n')
    headers = create_headers()

    # 除外するツイートのフレーズリストを取得
    with open('crover/data/word_list/excluded_tweet.txt', 'r', encoding='utf-8') as f:
        excluded_tweet = f.read().split('\n')

    # regex to clean tweets
    regexes = [
        re.compile(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
        re.compile(" .*\.jp/.*$"),
        re.compile('@\S* '),
        re.compile('pic.twitter.*$'),
        re.compile(' .*ニュース$'),
        re.compile('[ 　]'),
        re.compile('\n')
    ]
    URL_regex = re.compile(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)")

    sign_regex = re.compile('[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF。、ー～！？!?()（）]')

    if algo == 'mecab':
        tokenizer_obj = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        tokenizer_obj = suda_dict.Dictionary(dict_type='full').create()
        mode = tokenizer.Tokenizer.SplitMode.C  # 最も長い分割ルール

    # 先頭と末尾のスペース、末尾の#を除去し、間のスペースをORに変換する
    keyword = re.sub('^[ 　]+|[ 　]+$', '', keyword)
    keyword = re.sub('[ 　]+', ' OR ', keyword)
    keyword = re.sub('[#]+$', '', keyword)
    if keyword == '':
        raise NoKeywordError

    dict_word_count = {}
    next_token_id = None
    max_results = 100  # 1度のリクエストで取得するツイート数
    exclude_flag = False
    tweets_list = []
    past_tweets = []
    time_list = []

    for i in range(max_tweets // max_results + 1):
        if i == max_tweets // max_results:
            max_results = max_tweets % max_results
            if max_results < 10:
                break

        logger.info('start scraping')
        url = create_url(keyword, next_token_id, max_results)
        result = connect_to_endpoint(url, headers)

        logger.info('start word count tweet')

        for j in range(len(result['data'])):
            try:
                created_at_UTC = dt.datetime.strptime(result['data'][j]['created_at'][:-1] + "+0000", '%Y-%m-%dT%H:%M:%S.%f%z')
            except IndexError:
                continue
            created_at = created_at_UTC.astimezone(dt.timezone(dt.timedelta(hours=+9)))

            tweet_text = result['data'][j]['text']

            tweet_no_URL = URL_regex.sub('', tweet_text)
            if tweet_no_URL in past_tweets:
                continue
            else:
                past_tweets.append(tweet_no_URL)

            time_list.append(created_at)

            # 特定フレーズを含むツイートを除外
            for w in excluded_tweet:
                if w in tweet_text:
                    exclude_flag = True
                    break
            if exclude_flag:
                exclude_flag = False
                continue

            # clean tweet
            #logger.info('clean tweet')
            tweet_text = clean(tweet_text, regexes, sign_regex)

            # update noun count dictionary
            #logger.info('noun count')
            dict_word_count, split_word = noun_count(tweet_text, dict_word_count, tokenizer_obj, mode, keyword)

            tweets_list.append([created_at, tweet_no_URL, split_word])

        if 'next_token' in result['meta']:
            next_token_id = result['meta']['next_token']
        else:
            break

    # ツイート日時のヒストグラムを作る
    b64_time_hist = make_time_hist(time_list)

    logger.info('-------------- scrape finish -----------------\n')

    return dict_word_count, tweets_list, b64_time_hist


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
def make_time_hist(time_list):
    mpl_date = mdates.date2num(time_list)
    fig, ax = plt.subplots(1, 1, figsize=(6.0, 6.0))
    ax.hist(mpl_date, rwidth=0.95, color='dodgerblue')
    ax.yaxis.set_label_coords(0, 1.05)
    td = time_list[0] - time_list[-1]

    if td.days > 5:  # 3day~
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    elif td.days > 2:  # 3day~5day
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    elif td.days > 0:  # 1~2 days
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:00'))
    elif td.seconds // (3600 * 12) > 0:  # 12~24 hours
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:00'))
    elif td.seconds // (3600 * 6) > 0:  # 6~12 hours
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:00'))
    elif td.seconds // (3600 * 2) > 0:  # 2~6 hours
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:00'))
    elif td.seconds // (3600 * 1) > 0:  # 1~2 hours
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif td.seconds // 1800 > 0:  # 30~60 minutes
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif td.seconds // 600 > 0:  # 10~30 minutes
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif td.seconds // 300 > 0:  # 5~10 minutes
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    else:  # ~5 minutes
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    #ax.set_ylabel("ツイート", fontsize=24, rotation=0)
    ax.grid(which="major", axis="y", alpha=1)
    ax.set_axisbelow(True)
    plt.subplots_adjust(left=0.15, right=0.9, bottom=0.1, top=0.95)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    ax.tick_params(bottom=False, left=False, right=False, top=False)
    buf = io.BytesIO()
    plt.savefig(buf)
    qr_b64str = base64.b64encode(buf.getvalue()).decode("utf-8")
    b64_time_hist = "data:image/png;base64,{}".format(qr_b64str)

    return b64_time_hist

# 特定キーワードと同時にツイートされる名詞のカウント数を、全てのツイートにおける名詞のカウント数で割る
# （相対頻出度を計算する）
def word_count_rate(dict_word_count, dict_all_count, word_num_in_cloud=20, max_tweets=100, ignore_word_count=5, word_length=20, thre_word_count_rate=3):
    logger.info('------------ word count rate start --------------')
    dict_word_count = dict(sorted(dict_word_count.items(), key=lambda x: x[1], reverse=True))
    dict_word_count_rate = {}

    # 除外単語リストを取得
    with open('crover/data/word_list/excluded_word.txt', 'r', encoding='utf-8') as f:
        excluded_word = f.read().split('\n')
    with open('crover/data/word_list/excluded_char.txt', 'r', encoding='utf-8') as f:
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
            dict_word_count_rate[word] = float(dict_word_count[word]) / (float(all_count)/(1000000/max_tweets) + 1) + 1
        except TypeError:
            continue

    dict_word_count_rate = dict(sorted(dict_word_count_rate.items(), key=lambda x: x[1], reverse=True))
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
    logger.info('-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [], 'word_count_rate': [], 'not_dict_word': {}}
    all_word_list = list(word2vec.keys())

    for word in dict_word_count_rate.keys():
        logger.info(word)

        if word in all_word_list:
            dict_top_word2vec['word'].append(word)
            dict_top_word2vec['vec'].append(word2vec[word])
            dict_top_word2vec['word_count_rate'].append(dict_word_count_rate[word])
        else:
            dict_top_word2vec['not_dict_word'][word] = dict_word_count_rate[word]

    logger.info('-------------- making dict_top_word2vec finish -----------------\n')
    return dict_top_word2vec


def make_top_word2vec_dic_datastore(dict_word_count_rate):
    logger.info('-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [], 'word_count_rate': [], 'not_dict_word': {}}
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
            dict_top_word2vec['word_count_rate'].append(dict_word_count_rate[word])
        else:
            logger.info('vec not exist: ' + word)
            dict_top_word2vec['not_dict_word'][word] = dict_word_count_rate[word]

    logger.info('-------------- making dict_top_word2vec finish -----------------\n')

    return dict_top_word2vec

# word_count_rate（相対頻出度）の大きい単語にword2vecを当てはめる
def make_part_word2vec_dic(dict_word_count_rate, top_word2vec):
    logger.info('-------------- making dict_part_word2vec start -----------------\n')

    dict_part_word2vec = {'word': [], 'vec': [], 'word_count_rate': [], 'not_dict_word': []}

    for word in dict_word_count_rate.keys():
        logger.info(word)
        word_idx = top_word2vec['word'].index(word)
        dict_part_word2vec['word'].append(word)
        dict_part_word2vec['vec'].append(top_word2vec['vec'][word_idx])
        dict_part_word2vec['word_count_rate'].append(top_word2vec['word_count_rate'][word_idx])

    logger.info('-------------- making dict_part_word2vec finish -----------------\n')

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
def scrape_retweet(keyword, max_tweets=1000):
    logger.info('-------------- scrape start -----------------\n')
    headers = create_headers()

    # 除外するツイートのフレーズリストを取得
    with open('crover/data/word_list/excluded_tweet.txt', 'r', encoding='utf-8') as f:
        excluded_tweet = f.read().split('\n')

    URL_regex = re.compile(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)")

    # 先頭と末尾のスペースを除去し、間のスペースをORに変換する
    keyword = re.sub('^[ 　]+|[ 　]+$', '', keyword)
    keyword = re.sub('[ 　]+', ' OR ', keyword)

    next_results = None
    max_results = 100  # 1度のリクエストで取得するツイート数
    exclude_flag = False
    past_tweets = []
    tweet_ids = []
    retweet = []

    for i in range(max_tweets // max_results):
        logger.info('start scraping')
        url = create_url_retweet(keyword, next_results, max_results=max_results)
        result = connect_to_endpoint(url, headers)
        logger.info(f"{len(result['statuses'])} tweet")

        # これ以上リツイートがない場合
        if 'next_results' not in result['search_metadata']:
            break

        for res in result['statuses']:
            tweet_text = res['text']

            # 特定フレーズを含むツイートを除外
            for w in excluded_tweet:
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
            logger.info(f'retweet_count: {res["retweet_count"]}, {res["created_at"]}')

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


# リツイートしたユーザーIDを取得する
def get_retweet_author(retweet, since_date, max_scrape_retweet=100, thre_retweet_cnt=50):
    logger.info('get retweet user\n')
    max_trial = 30
    tokenizer_obj = suda_dict.Dictionary(dict_type='full').create()
    mode = tokenizer.Tokenizer.SplitMode.C  # 最も長い分割ルール
    sign_regex = re.compile(
        '[^\r\n0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF。、ー～！？!?()（）【】]')

    retweet_OK = []
    for i, r in enumerate(retweet):
        # debug
        if i > 10:
            break

        headers = create_headers()
        logger.info(f"{i+1} / {len(retweet)}, retweet count: {r['count']}")
        t = r['text']
        next_token_id = None

        #if '#' in t:
            #t = t[:t.find('#')]

        t = stop_noun(t, tokenizer_obj, mode)

        t = sign_regex.sub(' ', t)
        t = re.sub('[ 　]+', ' ', t)
        if t == ' ' or len(t) < 3:
            logger.info(f"extract few string\n"
                        f"cannot search '{r['text']}'")
            continue

        r['re_author'] = np.empty(0, dtype=int)
        k = 0

        try:
            for j in range(max_trial):
                if k > max_scrape_retweet // 100:
                    break

                url = create_url_retweet_author(t, since_date, next_token_id)
                #result = connect_to_endpoint(url, headers)

                #if 'data' in result:
                try:
                    result = connect_to_endpoint(url, headers)
                    k += 1
                #else:
                except:
                    t = stop_noun(t, tokenizer_obj, mode)
                    if t == ' ' or len(t) < 3:
                        break
                    else:
                        continue

                #for res in result['data']:
                for res in result['statuses']:
                    r['re_author'] = np.append(r['re_author'], res['user']['id'])

                #if 'next_token' in result['meta']:
                    #next_token_id = result['meta']['next_token']
                # これ以上リツイートがない場合
                if 'next_results' in result['search_metadata']:
                    next_token_id = result['search_metadata']['next_results']
                else:
                    break

            if len(r['re_author']) > thre_retweet_cnt:
                retweet_OK.append(r)
            else:
                logger.info(f"few retweet count: {len(r['re_author'])}\n"
                            f"cannot search '{r['text']}'")

        except:  # twitter APIの15分間取得ツイート数を越えた場合
            logger.info(traceback.format_exc())
            pass

    return retweet_OK















##################### 以下使わない関数 ######################

def scrape(keyword, max_tweets, since, until, checkpoint_cnt=10000, algo='sudachi'):
    print('-------------- scrape start -----------------\n')

    dt_until = dt.datetime.strptime(until, '%Y-%m-%d')
    dt_since = dt.datetime.strptime(since, '%Y-%m-%d')

    # regex to clean tweets
    regexes = [
        re.compile(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
        re.compile(" .*\.jp/.*$"),
        re.compile('@\S* '),
        re.compile('pic.twitter.*$'),
        re.compile(' .*ニュース$'),
        re.compile('[ 　]'),
        re.compile('\n')
    ]
    sign_regex = re.compile('[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF。、ー～！？!?()（）]')

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
        re.compile(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)"),
        re.compile(" .*\.jp/.*$"),
        re.compile('@\S* '),
        re.compile('pic.twitter.*$'),
        re.compile(' .*ニュース$'),
        re.compile('[ 　]'),
        re.compile('\n')
    ]
    sign_regex = re.compile('[^0-9０-９a-zA-Zａ-ｚＡ-Ｚ\u3041-\u309F\u30A1-\u30FF\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF。、ー～！？!?()（）]')

    if algo == 'mecab':
        tokenizer_obj = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        lib_path = site.getsitepackages()
        logger.info(lib_path)
        try:
            tokenizer_obj = suda_dict.Dictionary(config_path='crover/data/sudachi.json', resource_dir=os.path.join(lib_path[0], 'sudachipy/resources')).create()
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
    #with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor: # multi thread
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor: # multi core
        for i in range(max_tweets // max_results + 1):
            if i == max_tweets // max_results:
                max_results = max_tweets % max_results
                if max_results < 10:
                    break

            logger.info('start scraping')
            #url = create_url(keyword, next_token_id, max_results)
            #result = connect_to_endpoint(url, headers)

            tweets.append(executor.submit(scrape_next_tweets, max_results, keyword, headers, next_token_id))

            if i > 0:
                tweets_info, dict_word_count = tweets_info_tasks[-1].result()
                #tweets_info = tweets_info_tasks[-1].result()
                tweets_info_list.extend(tweets_info)

            logger.info('start word count tweet')
            tweets_info_tasks.append(executor.submit(word_count, tweets[-1].result(), regexes, sign_regex, tokenizer_obj, mode, keyword, dict_word_count))

            result = tweets[-1].result()
            if 'next_token' in result['meta']:
                next_token_id = result['meta']['next_token']
            else:
                break

    tweets_info, dict_word_count = tweets_info_tasks[-1].result()
    #tweets_info = tweets_info_tasks[-1].result()
    tweets_info_list.extend(tweets_info)
        #tweets_info_list = tweets_info_tasks[0].result()
        #for i in range(1, len(tweets_info_tasks)):
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
        scrape(output_name, keyword, 10000, dt_since.strftime('%Y-%m-%d'), dt_until.strftime('%Y-%m-%d'))
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
        created_at = created_at_UTC.astimezone(dt.timezone(dt.timedelta(hours=+9)))

        tweet_text = result['data'][j]['text']
        # clean tweet
        # logger.info('clean tweet')
        tweet_text = clean(tweet_text, regexes, sign_regex)

        # update noun count dictionary
        # logger.info('noun count')
        dict_word_count, split_word = noun_count(tweet_text, dict_word_count, tokenizer_obj, mode, keyword)

        tweets_info.append([created_at, result['data'][j]['text'], split_word])

    return tweets_info, dict_word_count
    #return tweets_info

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

    dict_word_count = dict(sorted(dict_word_count.items(), key=lambda x: x[1], reverse=True))
    dict_word_count_rate = {}
    for word in dict_word_count.keys():
        # 出現頻度の低い単語は無視
        if dict_word_count[word] < ignore_word_count:
            break

        #if (word in dict_all_count.keys()):
        if word in count_exist_words:
            all_count = entities[count_exist_words.index(word)]['count']
        else:
            all_count = 0

        try:
            dict_word_count_rate[word] = float(dict_word_count[word]) / (float(all_count)/(1000000/max_tweets) + 1)
        except TypeError:
            continue

    dict_word_count_rate = dict(sorted(dict_word_count_rate.items(), key=lambda x: x[1], reverse=True))
    i = 0
    extract_dict = {}
    word_rate_list = []
    for w in dict_word_count_rate.keys():
        if OKword(w):
            extract_dict[w] = dict_word_count_rate[w]
            word_rate_list.append(WordCount(word=w, relative_frequent_rate=dict_word_count_rate[w]))
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
        print(t.surface(), t.part_of_speech(), t.reading_form(), t.normalized_form())


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
            if count % 100000 == 0: print(count, "/", maxCount)
            line = f.readline()
            if line == '': break
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
