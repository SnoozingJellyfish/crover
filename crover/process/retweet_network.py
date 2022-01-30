import os
import re
import logging
import datetime
import itertools
import json

import numpy as np
import networkx as nx
from networkx.algorithms import community
import matplotlib.pyplot as plt
from google.cloud import datastore, storage

from crover import LOCAL_ENV
from crover.process.preprocess import scrape_retweet, get_retweet_author, tokenizer, suda_dict, \
    noun_count, word_count_rate
from crover.process.clustering import make_word_cloud
from crover.process.util import download_from_cloud

if LOCAL_ENV:
    from crover import dict_all_count

    plt.rcParams['font.family'] = 'Hiragino Sans GB'
else:
    plt.rcParams['font.family'] = 'IPAPGothic'

logger = logging.getLogger(__name__)

KEYWORD_KIND = "retweet_keyword"
DATE_KIND = "retweeted_date"
TWEET_KIND = 'retweeted_tweet'


def get_retweet_keyword():
    '''
    # debug
    # 収集済みリツイートキーワード
    re_keyword = {'keyword': ['テスト-コロナ', 'テスト-地震'],
                  'default_start_date': ['2022/01/01', '2022/01/02'],
                  'limit_start_date': ['2022/01/01', '2022/01/02'],
                  'limit_end_date': ['2022/01/02', '2022/01/03']}
    return re_keyword
    ###
    '''


    client = datastore.Client()
    logger.info('get retweet keyword and date')

    re_keyword = {'keyword': [],
                  'default_start_date': [],
                  'limit_start_date': [],
                  'limit_end_date': []}

    keyword_query = client.query(kind=KEYWORD_KIND)
    keyword_entities = list(keyword_query.fetch())

    for keyword_entity in keyword_entities:
        keyword = keyword_entity.key.name
        re_keyword['keyword'].append(keyword)
        logger.info(f'date of retweet keyword- {keyword}')

        # リツイートされたツイートとリツイートした人をアップロード
        date_query = client.query(kind=DATE_KIND, ancestor=keyword_entity.key)
        date_entities = list(date_query.fetch())
        date_int = []
        for date_entity in date_entities:
            date = date_entity.key.name
            date_int.append(int(date.replace('/', '')))

        start_date = date_entities[np.argmin(date_int)].key.name
        end_date = date_entities[np.argmax(date_int)].key.name
        start_date_dt = datetime.datetime.strptime(start_date, '%Y/%m/%d')
        end_date_dt = datetime.datetime.strptime(end_date, '%Y/%m/%d')
        td = end_date_dt - start_date_dt
        # 一番最近の収集日から7日前をデフォルト開始日とする
        # 一番古い収集日がデフォルト開始日より遅い場合はデフォルト開始日を一番古い収集日とする
        if td.days > 7:
            default_start_date_dt = end_date_dt - datetime.timedelta(days=7)
        else:
            default_start_date_dt = start_date_dt

        default_start_date = default_start_date_dt.strftime('%Y/%m/%d')

        re_keyword['default_start_date'].append(default_start_date)
        re_keyword['limit_start_date'].append(start_date)
        re_keyword['limit_end_date'].append(end_date)

    return re_keyword

# datastoreからリツイートを取得しネットワークを生成する
def analyze_network(keyword, start_date, end_date, sim_thre=0.03):
    '''
    keyword = '紅白'
    sim_thre = 0.03

    # リツイートを取得する
    # retweet = scrape_retweet(keyword)

    # リツイートしたユーザーを取得する
    # retweet = get_retweet_author(retweet)

    # debug
    import pickle
    # with open(f'crover/data/retweet_{keyword}_all2.pickle', 'wb') as f:
    # pickle.dump(retweet, f)
    with open(f'crover/data/retweet_{keyword}_all2.pickle', 'rb') as f:
        retweet = pickle.load(f)
    ###
    '''

    logger.info('analyze network')
    start_date = int(start_date.replace('/', ''))
    end_date = int(end_date.replace('/', ''))

    retweet_dict = {}

    # datastoreからリツイートを取得する
    client = datastore.Client()
    keyword_entity = client.get(client.key(KEYWORD_KIND, keyword))

    # リツイートされたツイートとリツイートした人をダウンロード
    date_query = client.query(kind=DATE_KIND, ancestor=keyword_entity.key)
    date_entities = list(date_query.fetch())
    for date_entity in date_entities:
        date = int(date_entity.key.name.replace('/', ''))

        # 範囲外の日付の場合はスキップ
        if date < start_date or date > end_date:
            continue

        tweet_query = client.query(kind=TWEET_KIND, ancestor=date_entity.key)
        tweet_entities = list(tweet_query.fetch())

        for tweet_entity in tweet_entities:
            tweet_id_str = str(tweet_entity['tweet_id'])
            if tweet_id_str in retweet_dict:
                retweet_elem = retweet_dict[tweet_id_str]
                retweet_elem['count'] = max((retweet_elem['count'], tweet_entity['count']))
                retweet_elem['re_author'] = np.hstack((retweet_elem['re_author'],
                                                       np.array(tweet_entity['re_author'])))
            else:
                retweet_dict[tweet_id_str] = {'tweet_id': tweet_entity['tweet_id'],
                                          'author': tweet_entity['author'],
                                          'text': tweet_entity['text'],
                                          'count': tweet_entity['count'],
                                          're_author': tweet_entity['re_author']}

    '''
    # debug
    with open('crover/data/test_retweet_info.json', 'r') as f:
        retweet_info = json.load(f)

    for date_str in retweet_info[keyword].keys():
        date = int(date_str.replace('/', ''))

        # 範囲外の日付の場合はスキップ
        if date < start_date or date > end_date:
            continue

        for tweet_info in retweet_info[keyword][date_str]:
            tweet_id_str = str(tweet_info['tweet_id'])
            if tweet_id_str in retweet_dict:
                retweet_elem = retweet_dict[tweet_id_str]
                retweet_elem['count'] = max((retweet_elem['count'], tweet_info['count']))
                retweet_elem['re_author'] = np.hstack((retweet_elem['re_author'],
                                                       np.array(tweet_info['re_author'])))
            else:
                retweet_dict[tweet_id_str] = {'tweet_id': tweet_info['tweet_id'],
                                              'author': tweet_info['author'],
                                              'text': tweet_info['text'],
                                              'count': tweet_info['count'],
                                              're_author': tweet_info['re_author']}
    #####
    '''
    retweet = list(retweet_dict.values())

    # リツイート間のユーザー類似度を算出する
    edge = author_similarity(retweet, sim_thre)

    # 閾値以上の類似度のユーザー間を繋いだグラフを作る
    g, cmap_idx = sim_graph(edge, retweet)

    # d3.jsでグラフを描画するためのjson用dictを作る
    graph_dict = make_graph_dict(edge, retweet, cmap_idx)

    # 頻出単語のワードクラウドを作成する
    group_num = max(cmap_idx) + 1
    word_clouds_figure = make_word_cloud_node(keyword, retweet, group_num)
    graph = {'graph_dict': graph_dict, 'word_cloud': word_clouds_figure}

    return graph


# リツイート間のユーザー類似度を算出する
def author_similarity(retweet, sim_thre=0.03):
    re_len = len(retweet)
    mat = np.zeros((re_len, re_len))

    for i in range(re_len - 1):
        author1 = retweet[i]['re_author']
        # 多すぎて収集できなかったツイート分を補正
        correct1 = np.sqrt(retweet[i]['count'] / len(author1))
        for j in range(i + 1, re_len):
            author2 = retweet[j]['re_author']
            # 多すぎて収集できなかったツイート分を補正
            correct2 = np.sqrt(retweet[j]['count'] / len(author2))
            intersect = len(np.intersect1d(author1, author2))
            geo_mean = np.sqrt(len(author1) * len(author2))
            cos_sim = intersect / geo_mean * correct1 * correct2
            mat[i, j] = cos_sim

    edge = list(zip(*np.where(mat > sim_thre)))
    return edge


# 閾値以上の類似度のユーザー間を繋いだグラフを作る
def sim_graph(edge, retweet, level=3):
    G = nx.Graph()
    G.add_nodes_from([(i, {"count": len(r['re_author'])}) for i, r in enumerate(retweet)])
    G.add_edges_from(edge)

    # クラスタリング
    communities = []
    comp = community.girvan_newman(G)
    #for _ in range(10):
        #communities.append(next(comp))
    #for i, c in enumerate(comp):
        #if i > level:
            #break
    for i, c in enumerate(itertools.islice(comp, level)):
        communities.append(c)
    last_level = i
    color = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'pink', 'skyblue', 'olive']
    cmap = []
    cmap_idx = []

    for node in G:
        for i, s in enumerate(communities[last_level]):
            if node in s:
                cmap_idx.append(i)
                # cmap.append(color[i])

    pos = nx.spring_layout(G, k=0.9)
    # nx.draw_networkx(G, pos)
    black_edges = list(G.edges())
    node_size = [d["count"] // 20 for (n, d) in G.nodes(data=True)]
    # nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=cmap)
    nx.draw_networkx_edges(G, pos, edgelist=black_edges, width=0.2)
    nx.draw_networkx_labels(G, pos)

    return G, cmap_idx


# d3.jsでグラフを描画するためのjson用dictを作る
def make_graph_dict(edge, retweet, cmap_idx):
    graph_dict = {'nodes': [], 'links': []}
    for i, r in enumerate(retweet):
        graph_dict['nodes'].append({'id': str(i), 'group': cmap_idx[i], 'author': r['author'],
                                    'tweet': r['text'], 'count': r['count']})
        r['group'] = cmap_idx[i]

    for e in edge:
        graph_dict['links'].append({'source': str(e[0]), 'target': str(e[1]), 'value': 1})
        graph_dict['links'].append({'source': str(e[1]), 'target': str(e[0]), 'value': 1})

    return graph_dict


def make_word_cloud_node(keyword, retweet, group_num, algo='sudachi'):
    if algo == 'mecab':
        tokenizer_obj = MeCab.Tagger("-Ochasen")
    elif algo == 'sudachi':
        tokenizer_obj = suda_dict.Dictionary(dict_type='full').create()
        mode = tokenizer.Tokenizer.SplitMode.C  # 最も長い分割ルール

    word_count_cluster = [{} for _ in range(group_num + 1)]

    for r in retweet:
        word_count_cluster[-1], _ = noun_count(r['text'], word_count_cluster[-1],
                                               tokenizer_obj, mode, keyword)
        word_count_cluster[r['group']], _ = noun_count(r['text'], word_count_cluster[r['group']],
                                                       tokenizer_obj, mode, keyword)

    if not LOCAL_ENV:
        logger.info('start loading dict_all_count')
        dict_all_count = download_from_cloud(storage.Client(), os.environ.get('BUCKET_NAME'),
                                             os.environ.get('DICT_ALL_COUNT'))
        logger.info('finish loading dict_all_count')
    else:
        from crover import dict_all_count

    word_count_rate_cluster = []
    for i in range(group_num + 1):
        word_count_rate_cluster.append(word_count_rate(word_count_cluster[i],
                                                       dict_all_count, word_num_in_cloud=20,
                                                       max_tweets=len(retweet),
                                                       thre_word_count_rate=0,
                                                       ignore_word_count=0))

    colormaps = ['Blues', 'Oranges', 'Greens', 'Reds', 'Purples', 'copper', 'pink', 'bone', 'YlGn', 'BuGn']
    word_clouds_figure = make_word_cloud(word_count_rate_cluster[:-1], colormaps=colormaps)
    # 全クラスターのワードクラウド
    word_clouds_figure.append(make_word_cloud([word_count_rate_cluster[-1]], colormaps=['Greys'])[0])

    return word_clouds_figure
