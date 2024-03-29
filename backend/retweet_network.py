import os
import logging
import datetime as dt
import itertools
import json

import numpy as np
import networkx as nx
from networkx.algorithms import community
# import matplotlib.pyplot as plt
from google.cloud import datastore, storage

from backend.util import make_retweet_list, upload_to_cloud, download_text_from_cloud
'''
from crover import LOCAL_ENV
from crover.process.preprocess import tokenizer, suda_dict, \
    noun_count, word_count_rate
from crover.process.clustering import make_word_cloud
from crover.process.util import download_from_cloud, make_retweet_list


if LOCAL_ENV:
    from crover import dict_all_count

    plt.rcParams['font.family'] = 'Hiragino Sans GB'
else:
    plt.rcParams['font.family'] = 'IPAPGothic'
'''

logger = logging.getLogger(__name__)

ANALYZED_KEYWORD_KIND = "retweet_analyzed_keyword"
ANALYZED_DATE_KIND = "retweeted_analyzed_date"
ANALYSIS_KIND = 'retweeted_analysis'

KEYWORD_KIND = "retweet_keyword"
DATE_KIND = "retweeted_date"
TWEET_KIND = 'retweeted_tweet'


def get_retweet_keyword(LOCAL_ENV=False, ignore_day=7):
    logger.info('get retweet keyword and date')

    # debug用
    if LOCAL_ENV:
        # 収集済みリツイートキーワード
        re_keyword = {'keywordList': ['テスト-コロナ', 'テスト-地震'],
                      "dateLists": [
                                    ["2022/01/01~2022/01/02", "2022/02/02~2022/02/03"],
                                    ["2022/03/01~2022/03/02", "2022/04/02~2022/04/03"]
                                   ]
                      }
        return re_keyword

    # release用
    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')
    bucket = storage_client.bucket(bucket_name)

    datastore_client = datastore.Client()
    keyword_query = datastore_client.query(kind=KEYWORD_KIND)
    keyword_entities = list(keyword_query.fetch())

    re_keyword = {'keywordList': [],
                  'dateLists': []}

    for keyword_entity in keyword_entities:
        '''
        # リツイートされたツイートとリツイートした人をアップロード
        date_query = client.query(kind=DATE_KIND, ancestor=keyword_entity.key)
        date_entities = list(date_query.fetch())
        date_int = []
        for date_entity in date_entities:
            date = date_entity.key.name
            date_int.append(int(date.replace('/', '')))

        start_date = date_entities[np.argmin(date_int)].key.name
        end_date = date_entities[np.argmax(date_int)].key.name
        start_date_dt = dt.datetime.strptime(start_date, '%Y/%m/%d')
        end_date_dt = dt.datetime.strptime(end_date, '%Y/%m/%d')

        # 一番最近の収集日が今日よりignore_day日前の場合スキップ
        dif_today_end = dt.datetime.now() - end_date_dt
        if dif_today_end.days > ignore_day:
            continue
            # pass  # for debug

        td = end_date_dt - start_date_dt
        # 一番最近の収集日から7日前をデフォルト開始日とする
        # 一番古い収集日がデフォルト開始日より遅い場合はデフォルト開始日を一番古い収集日とする
        if td.days > 7:
            default_start_date_dt = end_date_dt - dt.timedelta(days=7)
        else:
            default_start_date_dt = start_date_dt

        default_start_date = default_start_date_dt.strftime('%Y/%m/%d')
        '''

        keyword = keyword_entity.key.name
        re_keyword['keywordList'].append(keyword)
        logger.info(f'date of retweet keyword- {keyword}')
        '''
        re_keyword['startDateList'].append(default_start_date)
        re_keyword['minDateList'].append(start_date)
        re_keyword['maxDateList'].append(end_date)
        '''

        blobs = bucket.list_blobs(prefix=f"{os.environ.get('ANALYZED_RETWEET_DATA_DIR')}/{keyword}/")
        
        # date_path = []
        date_list = []
        for b in blobs:
            # date_path.append(b.name)
            date_list.append(os.path.basename(b.name).replace('-', '/').replace('_', '~').split('.')[0])
            
        # 日付を新しい順にする
        # re_keyword['datePath'].append(date_path[::-1])
        re_keyword['dateLists'].append(date_list[::-1])

    return re_keyword


# datastoreからリツイートを取得しネットワークを生成する
def analyze_network(keyword, start_date, end_date, sim_thre=0.03, LOCAL_ENV=False):
    logger.info('start analyze_network')
    start_date = int(start_date.replace('-', ''))
    end_date = int(end_date.replace('-', ''))

    retweet_dict = {}

    if LOCAL_ENV:
        retweet_dict = make_retweet_list(keyword, start_date, end_date)
    else:
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

                # 異なる日で重複しているリツイートの情報は統合する
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

    # リツイートされたツイートの個数が多い場合は、リツイート回数が少ないツイートを削除
    retweet = del_low_count_retweet(retweet_dict)

    # リツイート間のユーザー類似度を算出する
    edge = author_similarity(retweet, sim_thre)

    # 閾値以上の類似度のユーザー間を繋いだグラフを作る
    g, cmap_idx = sim_graph(edge, retweet)

    # d3.jsでグラフを描画するためのjson用dictを作る
    graph_dict = make_graph_dict(edge, retweet, cmap_idx)

    # 頻出単語のワードクラウドを作成する
    group_num = max(cmap_idx) + 1

    logger.info('finish analyze_network')

    return graph_dict, keyword, retweet, group_num


# リツイートされたツイートの個数が多い場合は、リツイート回数が少ないツイートを削除
def del_low_count_retweet(retweet_dict, max_len=50):
    retweet = list(retweet_dict.values())

    if len(retweet) > max_len:
        retweet = np.array(retweet)
        cnt = np.array([r['count'] for r in retweet])
        sorted_index = np.argsort(cnt)[::-1]  # 降順
        retweet = list(retweet[sorted_index[:max_len]])

    return retweet


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
    # color = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'pink', 'skyblue', 'olive']
    # cmap = []
    cmap_idx = []

    for node in G:
        for i, s in enumerate(communities[last_level]):
            if node in s:
                cmap_idx.append(i)
                # cmap.append(color[i])

    # pos = nx.spring_layout(G, k=0.9)
    # nx.draw_networkx(G, pos)
    # black_edges = list(G.edges())
    # node_size = [d["count"] // 20 for (n, d) in G.nodes(data=True)]
    # nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=cmap)
    # nx.draw_networkx_edges(G, pos, edgelist=black_edges, width=0.2)
    # nx.draw_networkx_labels(G, pos)

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


def make_word_cloud_node_old(keyword, retweet, group_num, algo='sudachi'):
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


# Cloud Scheduler: datastore upload retweet_info
def datastore_upload_retweet(keyword, date, retweet_info):
    client = datastore.Client()
    logger.info('start upload retweet info')

    # リツイートのキーワードをアップロード
    logger.info(f'retweet keyword: {keyword}')
    keyword_entity = datastore.Entity(client.key(KEYWORD_KIND, keyword))
    client.put(keyword_entity)

    # リツイートした日付をアップロード
    keyword_entity = client.get(client.key(KEYWORD_KIND, keyword))
    logger.info(f'date: {date}')
    date_entity = datastore.Entity(client.key(DATE_KIND, date, parent=keyword_entity.key))
    client.put(date_entity)

    # リツイートされたツイートとリツイートした人をアップロード
    date_entity = client.get(client.key(DATE_KIND, date, parent=keyword_entity.key))
    logger.info(f'tweet of retweeted date- {date}')
    tweet_entities = []
    tweet_query = client.query(kind=TWEET_KIND, ancestor=date_entity.key)
    tweet_entities_old = list(tweet_query.fetch())
    tweet_id_old = [t_o['tweet_id'] for t_o in tweet_entities_old]

    for t in retweet_info:
        if t['tweet_id'] not in tweet_id_old:
            logger.info(f'tweet: {t["text"]}')
            tweet_entity = datastore.Entity(client.key(TWEET_KIND, parent=date_entity.key))
            tweet_entity.update(t)
            tweet_entities.append(tweet_entity)

    if len(tweet_entities) > 0:
        client.put_multi(tweet_entities)


# ネットワーク解析済みのリツイートデータをdatastoreとcloud storageに保存する
def upload_analyzed_retweet(keyword, start_date, end_date, retweet_dict):
    logger.info('start uploading ANALYZED retweet str')

    client = datastore.Client()
    retweet_str = json.dumps(retweet_dict)

    # リツイートのキーワードをdatastoreにアップロード
    logger.info(f'retweet keyword: {keyword}')
    keyword_entity = datastore.Entity(client.key(ANALYZED_KEYWORD_KIND, keyword))
    client.put(keyword_entity)

    # リツイートした日付をdatastoreにアップロード
    dates = f'{start_date}_{end_date}'
    logger.info(f'dates: {dates}')
    keyword_entity = client.get(client.key(ANALYZED_KEYWORD_KIND, keyword))
    date_entity = datastore.Entity(client.key(ANALYZED_DATE_KIND, dates, parent=keyword_entity.key))
    client.put(date_entity)

    # リツイートされたツイートとリツイートした人をアップロード
    # (datastoreには1項目あたり1500byte以上のデータを保存できないため、cloud storageに保存する)
    logger.info('upload analyzed data')
    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')
    upload_to_cloud(storage_client,
                    bucket_name,
                    os.path.join(os.environ.get('ANALYZED_RETWEET_DATA_DIR'), keyword, f'{dates}.txt'),
                    retweet_str)

    logger.info('finish uploading ANALYZED retweet str')


# cloud storageからネットワーク解析済みリツイートデータを取得する
def get_analyzed_network(keyword, dates, LOCAL_ENV):
    logger.info('start getting ANALYZED network')

    if LOCAL_ENV:
        with open('backend/data/test_analyzed_retweet.txt', 'r') as f:
            retweet_str = f.read()
    else:
        storage_client = storage.Client()
        bucket_name = os.environ.get('BUCKET_NAME')
        dates = dates.replace('/', '-').replace('~', '_')
        # dates = f'{start_date}_{end_date}'

        retweet_str = download_text_from_cloud(storage_client,
                                               bucket_name,
                                               os.path.join(os.environ.get('ANALYZED_RETWEET_DATA_DIR'), keyword, f'{dates}.txt'),
                                               )


    '''
    client = datastore.Client()

    # リツイートしたキーワードを取得
    logger.info(f'retweet keyword: {keyword}')
    keyword_entity = client.get(client.key(ANALYZED_KEYWORD_KIND, keyword))

    # リツイートした日付を取得
    dates = f'{start_date}_{end_date}'
    logger.info(f'dates: {dates}, keyword_entity.key: {keyword_entity.key}')
    date_entity = client.get(client.key(ANALYZED_DATE_KIND, dates, parent=keyword_entity.key))
    
    # 解析済みリツイート結果を取得
    logger.info(f'date_entity.key: {date_entity.key}')
    analysis_entity = client.get(client.key(ANALYSIS_KIND, dates, parent=date_entity.key))
    retweet_str = analysis_entity['retweet_str']
    '''

    retweet_dict = json.loads(retweet_str)

    logger.info('finish getting ANALYZED network')

    return retweet_dict
    