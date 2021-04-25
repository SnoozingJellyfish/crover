import os
import re
import datetime as dt
import pickle
import csv
import requests
import json
import subprocess
import site
import sys
from io import BytesIO
import time
import logging

from flask import current_app as app
#import snscrape.modules.twitter as sntwitter
#from tqdm import tqdm
#import MeCab
#import pandas as pd
import numpy as np
from sudachipy import tokenizer
from sudachipy import dictionary as suda_dict

#import gensim
import boto3

from crover import db
#from crover import dict_all_count
from crover import dict_all_count, word2vec
from crover.models.tweet import Tweet, WordCount
#from crover.models.tweet import AllWordCount

logger = logging.getLogger(__name__)

def preprocess_all(keyword, max_tweets, word_num):
    print('all preprocesses will be done. \n(scrape and cleaning tweets, counting words, making word2vec dictionary)\n')
    #print(site.getsitepackages())
    #subprocess.Popen(os.path.join(site.getsitepackages()[0], "Scripts", "sudachipy.exe") + " link -t full")

    '''
    s3_client = boto3.resource(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=app.config['AWS_REGION']
    )
    bucket = s3_client.Bucket(app.config['AWS_BUCKET_NAME'])
    
    for i in [1, 10, 100, 1000]:
        start = time.time()
        obj = bucket.Object('temp/word2vec_' + str(i) + '.pickle')
        dict_all_count = pickle.load(BytesIO(obj.get()['Body'].read()))
        print(str(i), ' data load time: ', time.time() - start)
    return None
    '''
    '''
    ### heroku ###
    dst_path = set_default_dict_package(dict_package, output)
    start = time.time()
    obj = bucket.Object(app.config['ALL_WORD_COUNT'])
    dict_all_count = pickle.load(BytesIO(obj.get()['Body'].read()))
    all_word_count_load_point = time.time()
    print('ALL WORD COUNT load time: ', all_word_count_load_point - start)
    
    obj = bucket.Object(app.config['WORD_ID'])
    word_id = pickle.load(BytesIO(obj.get()['Body'].read()))
    print('WORD ID load time: ', time.time() - all_word_count_load_point)
    '''
    '''
    with open('crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)
    
    with open('crover/data/word_id.pickle', 'rb') as f:
        word_id = pickle.load(f)
    '''

    #dict_word_count = scrape(keyword, max_tweets, since, until)
    dict_word_count = scrape_token(keyword, max_tweets)
    dict_word_count_rate = word_count_rate(dict_word_count, dict_all_count)
    return make_top_word2vec_dic(dict_word_count_rate, word2vec, top_word_num=word_num)

    #return make_top_word2vec_dic(dict_word_count, word2vec_model='crover/data/chive-1.2-mc30.kv')
    #return make_top_word2vec_dic(dict_word_count_rate, word2vec_model='crover/data/jawiki.all_vectors.100d.pickle')


# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
def auth():
    return os.environ.get("TWITTER_BEARER_TOKEN")
    #return app.config['TWITTER_BEARER_TOKEN']

def create_url(keyword, next_token_id=None, max_results=10):
    #query = "from:twitterdev -is:retweet"
    query = keyword + " -is:retweet lang:ja"
    # Tweet fields are adjustable.
    # Options include:
    # attachments, author_id, context_annotations,
    # conversation_id, created_at, entities, geo, id,
    # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    # source, text, and withheld
    tweet_fields = "tweet.fields=author_id,created_at"
    mrf = "max_results={}".format(max_results)
    if next_token_id:
        next_token = 'next_token=' + next_token_id
        url = "https://api.twitter.com/2/tweets/search/recent?query={}&{}&{}&{}".format(
            query, tweet_fields, mrf, next_token
        )
    else:
        url = "https://api.twitter.com/2/tweets/search/recent?query={}&{}&{}".format(
            query, tweet_fields, mrf
        )
    return url


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def requestAPI():
    bearer_token = auth()
    url = create_url()
    headers = create_headers(bearer_token)
    json_response = connect_to_endpoint(url, headers)
    print(json.dumps(json_response, indent=4, sort_keys=True))

def scrape_token(keyword, max_tweets, algo='sudachi'):
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
        tokenizer_obj = suda_dict.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C

    tweets = []
    dict_word_count = {}
    word_count_list = []
    next_token_id = None
    max_results = 100

    for i in range(max_tweets // max_results + 1):
        if i == max_tweets // max_results:
            max_results = max_tweets % max_results
            if max_results < 10:
                break

        print('start scraping %d tweets', max_results)
        url = create_url(keyword, next_token_id, max_results)
        result = connect_to_endpoint(url, headers)
        print('finish scraping %d tweets', max_results)
        next_token_id = result['meta']['next_token']

        print('start word count tweet')
        for j in range(max_results):
            created_at_UTC = dt.datetime.strptime(result['data'][j]['created_at'][:-1] + "+0000", '%Y-%m-%dT%H:%M:%S.%f%z')
            created_at = created_at_UTC.astimezone(dt.timezone(dt.timedelta(hours=+9)))

            tweets.append(Tweet(tweeted_at=created_at, text=result['data'][j]['text']))

            tweet_text = result['data'][j]['text']
            # clean tweet
            tweet_text = clean(tweet_text, regexes, sign_regex)

            # update noun count dictionary
            dict_word_count = noun_count(tweet_text, dict_word_count, tokenizer_obj, mode, keyword)
        print('finish word count tweet')
    db.session().add_all(tweets)

    '''
    for k in dict_word_count.keys():
        word_count_list.append(WordCount(word=k, count=dict_word_count[k]))
    db.session().add_all(word_count_list)
    '''
    db.session().commit()

    print('-------------- scrape finish -----------------\n')

    return dict_word_count

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
            db.session().add_all(tweets)
            db.session().commit()
            break

        i += 1

    for k in dict_word_count.keys():
        word_count_list.append(WordCount(word=k, count=dict_word_count[k]))

    print('-------------- scrape finish -----------------\n')

    return dict_word_count


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
            noun = words[j].normalized_form()
            if (noun == keyword):
                continue
            part = words[j].part_of_speech()[0]

        if (part == "名詞"):
            if (noun in dict_word_count.keys()):
                dict_word_count[noun] += 1
            else:
                dict_word_count[noun] = 1

    return dict_word_count


# 特定キーワードと同時にツイートされる名詞のカウント数を、全てのツイートにおける名詞のカウント数で割る
# （相対頻出度を計算する）
def word_count_rate(dict_word_count, dict_all_count, ignore_word_count=0):
    print('------------ word count rate start --------------')
    dict_word_count = dict(sorted(dict_word_count.items(), key=lambda x: x[1], reverse=True))
    dict_word_count_rate = {}
    for word in dict_word_count.keys():
        # 出現頻度の低い単語は無視
        if dict_word_count[word] < ignore_word_count:
            break

        if (word in dict_all_count.keys()):
            all_count = dict_all_count[word]
        else:
            all_count = 0

        try:
            dict_word_count_rate[word] = float(dict_word_count[word]) / (float(all_count)/2 + 1)
        except TypeError:
            continue

    dict_word_count_rate = dict(sorted(dict_word_count_rate.items(), key=lambda x: x[1], reverse=True))

    print('------------ word count rate finish --------------')
    return dict_word_count_rate


# word_count_rate（相対頻出度）の大きい単語にword2vecを当てはめる
def make_top_word2vec_dic(dict_word_count_rate, word2vec, top_word_num=20, algo='mecab'):
    print('-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [], 'word_count_rate': [], 'not_dict_word': []}
    word_keys = list(dict_word_count_rate.keys())
    top_words = list(dict_word_count_rate.keys())[:min(top_word_num, len(word_keys))]
    all_word_list = list(word2vec.keys())

    word_rate_list = []

    for word in top_words:
        print(word)
        word_rate_list.append(WordCount(word=word, relative_frequent_rate=dict_word_count_rate[word]))

        if algo == 'mecab':
            if word in all_word_list:
                if OKword(word):
                    print('OK')
                    dict_top_word2vec['word'].append(word)
                    #id = word_id[word]
                    #source_path = os.path.join('mecab_word2vec_100d_per100-100', str(id//10000), 'word2vec_' + str((id%10000)//100) + '.pickle')
                    #source_path = 'mecab_word2vec_100d_per100-100/' + str(id//10000*10000) + '/word2vec_' + str((id%10000)//100*100) + '.pickle'
                    #obj = bucket.Object(source_path)
                    #vec_dict = pickle.load(BytesIO(obj.get()['Body'].read()))
                    #dict_top_word2vec['vec'].append(vec_dict[id])
                    dict_top_word2vec['vec'].append(word2vec[word])
                    dict_top_word2vec['word_count_rate'].append(dict_word_count_rate[word])
            else:
                dict_top_word2vec['not_dict_word'].append(word)

        elif algo == 'sudachi':
            if word in model:
                if OKword(word):
                    dict_top_word2vec['word'].append(word)
                    dict_top_word2vec['vec'].append(model[word])
                    dict_top_word2vec['word_count_rate'].append(dict_word_count_rate[word])
            else:
                dict_top_word2vec['not_dict_word'].append(word)

    db.session().add_all(word_rate_list)
    db.session().commit()

    print('-------------- making dict_top_word2vec finish -----------------\n')

    return dict_top_word2vec


# 汎用性の高い単語を除外する
def OKword(word):
    excluded_word = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '百', '千', '万', '億', '独紙', 'RT', 'フォロー', 'いいね', 'お気に入り', 'まとめ', '日本', 'NHK', 'ジオグラフィック', 'ロイター', '大手小町', 'スポニチアネックス', 'Bloomberg', 'ナショナルジオグラフィック', 'Reuters', 'reuters', 'カナロコ', 'アットエス', '西日本スポーツ', 'Annex', 'Sponichi', '沖縄タイムス', 'Infoseek', 'マイナビ', 'AFP']
    excluded_char = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '０', '１', '２', '３', '４', '５', '６', '７', '８', '９', 'AERA', 'NEWS', 'news', '県', '府', '市', '町', '放送', '新聞', 'ニュース', '時事', '日刊', '新報', 'DIGITAL', '日報', 'TOKYOweb', 'ABEMA', 'MEDIANTALKS']
    
    if word in excluded_word:
        return False

    for c in excluded_char:
        if c in word:
            return False

    return True




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
