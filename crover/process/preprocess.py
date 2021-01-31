import os
import re
import datetime as dt
import pickle
import csv

import snscrape.modules.twitter as sntwitter
#from tqdm import tqdm
#import MeCab
#import pandas as pd
import numpy as np
from sudachipy import tokenizer
from sudachipy import dictionary as suda_dict
import gensim

from crover import db
from crover.models.tweet import Tweet
#from crover.models.tweet import AllWordCount

def preprocess_all(keyword, max_tweets, since, until):
    print('all preprocesses will be done. \n(scrape and cleaning tweets, counting words, making word2vec dictionary)\n')
    dict_word_count = scrape(keyword, max_tweets, since, until)
    if dict_word_count == {}:
        return False
    #all_word_count = AllWordCount.query().all()
    with open('crover/data/all_1-200-000_word_count_sudachi.pickle', 'rb') as f:
        dict_all_count = pickle.load(f)
    dict_word_count_rate = word_count_rate(dict_word_count, dict_all_count)
    return make_top_word2vec_dic(dict_word_count_rate, word2vec_model='crover/data/jawiki.all_vectors.100d.pickle')


def scrape(keyword, max_tweets, since, until, checkpoint_cnt=10000):
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

    i = 0
    already_tweets = []
    tweets = []
    dict_word_count = {}

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
        #dict_word_count = noun_count(tweet_text, dict_word_count, keyword)

        if (i+1) == max_tweets:
            db.session().add_all(tweets)
            db.session().commit()
            break

        i += 1

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
def noun_count(text, dict_word_count, keyword=None, algo='sudachi'):
    if algo == 'mecab':
        m = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        tokenizer_obj = suda_dict.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C

    try:
        if algo == 'mecab':
            words = m.parse(text).split("\n")
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

    return dict_word_count_rate


# word_count_rate（相対頻出度）の大きい単語にword2vecを当てはめる
def make_top_word2vec_dic(dict_word_count_rate, word2vec_model, top_word_num=1000, algo='mecab'):
    print('-------------- making dict_top_word2vec start -----------------\n')

    dict_top_word2vec = {'word': [], 'vec': [], 'word_count_rate': [], 'not_dict_word': []}
    word_keys = list(dict_word_count_rate.keys())
    top_words = list(dict_word_count_rate.keys())[:min(top_word_num, len(word_keys))]

    print('word2vec loading...\n')
    # 学習済み分散表現の読み込み
    if algo == 'mecab':
        with open(word2vec_model, mode='rb') as f:
            model = pickle.load(f)
    elif algo == 'sudachi':
        model = gensim.models.KeyedVectors.load(word2vec_model)

    for word in top_words:
        if algo == 'mecab':
            if word in model.wv.index2word:
                if OKword(word):
                    dict_top_word2vec['word'].append(word)
                    dict_top_word2vec['vec'].append(model.wv[word])
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
