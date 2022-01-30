import os
import pickle
from io import BytesIO
import logging
import json
import datetime as dt

import numpy as np
from google.cloud import storage

logger = logging.getLogger(__name__)


def download_from_cloud(storage_client, bucket_name, filename):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    bytedata = blob.download_as_bytes()
    return pickle.load(BytesIO(bytedata))


def upload_to_cloud(storage_client, bucket_name, filename, bytedata):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(bytedata)


# datastore upload
def datastore_upload(up_vec_num=0):
    from google.cloud import datastore
    # from crover import word2vec
    client = datastore.Client()

    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')

    logger.info('start loading dict_all_count')
    dict_all_count = download_from_cloud(storage_client, bucket_name, os.environ.get('DICT_ALL_COUNT'))
    # logger.info('start loading mlask dict')
    # mlask_emotion_dictionary = download_from_cloud(storage_client, bucket_name, os.environ.get('MLASK_EMOTION_DICTIONARY'))
    logger.info('finish loading')
    upload_dict = dict_all_count
    print('num of dict_all_count:', len(upload_dict.keys()))
    upload_folder_name = "sudachi_word2vec_300d"
    # upload_folder_name = "sudachi_all_word_count"
    i = 0
    entities = []

    # for w in word2vec.keys():
    for w in upload_dict.keys():
        i += 1
        if i > up_vec_num and type(w) == str and w[0] != '_' and w != '':
            entity = datastore.Entity(client.key(upload_folder_name, w))
            # entity.update({'vec': list(upload_dict[w].astype(np.float64))})
            entity.update({'count': upload_dict[w]})
            entities.append(entity)
        if i > up_vec_num and i % 400 == 0:
            logger.info(i)
            client.put_multi(entities)
            entities = []

    client.put_multi(entities)


# datastore upload word2vec
def datastore_upload_wv(split, up_vec_num):
    from google.cloud import datastore
    # from crover import word2vec
    client = datastore.Client()

    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')
    first = True

    for i in range(split, 9):
        logger.info('start loading word2vec dict')
        upload_dict = download_from_cloud(storage_client, bucket_name,
                                          'mecab_word2vec_dict_100d_9split/mecab_word2vec_dict_100d_9-' + str(
                                              i + 1) + '.pickle')
        logger.info('finish loading')
        print('num of word2vec keys:', len(upload_dict.keys()))
        upload_folder_name = "mecab_word2vec_100d"

        entities = []
        j = 0
        for w in upload_dict.keys():
            j += 1
            if first and j < up_vec_num:
                continue
            else:
                first = False

            if type(w) == str and w[0] != '_' and w != '':
                entity = datastore.Entity(client.key(upload_folder_name, w))
                entity.update({'vec': list(upload_dict[w].astype(np.float64))})
                entities.append(entity)

            if (len(entities) + 1) % 500 == 0:
                logger.info('split:' + str(i) + ',' + str(j + 1))
                client.put_multi(entities)
                entities = []

        if len(entities) > 0:
            logger.info('split:' + str(i) + ',' + str(j + 1))
            client.put_multi(entities)


# datastore upload retweet_info by manual
def datastore_upload_retweet_manual():
    retweet_info = {'テスト-コロナ':
                           {'2022/01/01':
                                [{'tweet_id': 0,
                                  'author': 'author0',
                                  'text': 'text0',
                                  'count': 1000,
                                  're_author': [100, 200]},
                                 {'tweet_id': 1,
                                  'author': 'author1',
                                  'text': 'text1',
                                  'count': 2000,
                                  're_author': [200, 300]}],
                            '2022/01/02':
                                [{'tweet_id': 0,
                                  'author': 'author0',
                                  'text': 'text0',
                                  'count': 1000,
                                  're_author': [300, 400, 500]},
                                 {'tweet_id': 2,
                                  'author': 'author2',
                                  'text': 'text2',
                                  'count': 3000,
                                  're_author': [200, 600]}]},
                       'テスト-地震':
                           {'2022/01/02':
                                [{'tweet_id': 3,
                                  'author': 'author3',
                                  'text': 'text3',
                                  'count': 2000,
                                  're_author': [100, 200, 700, 800]},
                                 {'tweet_id': 4,
                                  'author': 'author4',
                                  'text': 'text4',
                                  'count': 500,
                                  're_author': [200, 300, 800]}],
                            '2022/01/03':
                                [{'tweet_id': 4,
                                  'author': 'author4',
                                  'text': 'text4',
                                  'count': 1000,
                                  're_author': [300, 400, 500]},
                                 {'tweet_id': 5,
                                  'author': 'author5',
                                  'text': 'text5',
                                  'count': 3000,
                                  're_author': [100, 600]}]}}

    with open('crover/data/test_retweet_info.json', 'w') as f:
        json.dump(retweet_info, f, indent=4, ensure_ascii=False)

    from google.cloud import datastore
    # from crover import word2vec
    client = datastore.Client()
    logger.info('start upload retweet info')

    keyword_kind = "retweet_keyword"

    keyword_entities = []
    # リツイートのキーワードをアップロード
    for k in retweet_info.keys():
        logger.info(f'retweet keyword: {k}')
        #keyword_entity = datastore.Entity(client.key(keyword_kind))
        keyword_entity = datastore.Entity(client.key(keyword_kind, k))
        #keyword_entity.update({'keyword': k})
        keyword_entities.append(keyword_entity)

    client.put_multi(keyword_entities)

    tweet_kind = 'retweeted_tweet'

    # リツイートした日付をアップロード
    date_kind = 'retweeted_date'
    keyword_query = client.query(kind=keyword_kind)
    keyword_entities = list(keyword_query.fetch())
    for keyword_entity in keyword_entities:
        #keyword = keyword_entity["keyword"]
        keyword = keyword_entity.key.name
        logger.info(f'date of retweet keyword- {keyword}')

        date_entities = []
        for d in retweet_info[keyword].keys():
            logger.info(f'date: {d}')
            #date_entity = datastore.Entity(client.key(date_kind, parent=keyword_entity.key.id))
            #date_entity = datastore.Entity(client.key(date_kind, parent=keyword_entity.key))
            date_entity = datastore.Entity(client.key(date_kind, d, parent=keyword_entity.key))
            #date_entity.update({'date': d})
            date_entities.append(date_entity)

        client.put_multi(date_entities)

        # リツイートされたツイートとリツイートした人をアップロード
        date_query = client.query(kind=date_kind, ancestor=keyword_entity.key)
        date_entities = list(date_query.fetch())
        for date_entity in date_entities:
            #date = date_entity['date']
            date = date_entity.key.name
            logger.info(f'tweet of retweeted date- {date}')
            tweet_entities = []

            tweet_query = client.query(kind=tweet_kind, ancestor=date_entity.key)
            tweet_entities_old = list(tweet_query.fetch())
            tweet_id_old = [t_o['tweet_id'] for t_o in tweet_entities_old]
            for t in retweet_info[keyword][date]:
                if t['tweet_id'] not in tweet_id_old:
                    logger.info(f'tweet: {t["text"]}')
                    #tweet_entity = datastore.Entity(client.key(tweet_kind, parent=date_entity.key.id))
                    tweet_entity = datastore.Entity(client.key(tweet_kind, parent=date_entity.key))
                    tweet_entity.update(t)
                    tweet_entities.append(tweet_entity)

            if len(tweet_entities) > 0:
                client.put_multi(tweet_entities)


def make_retweet_list(keyword, start_date, end_date):
    retweet_dict = {}
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

    return retweet_dict


# cloud schedulerのjobを模擬
def test_run_collect_retweet_job():
    from crover.process.preprocess import scrape_retweet, get_retweet_author

    keyword = ['コロナ']

    jst_delta = dt.timedelta(hours=9)
    JST = dt.timezone(jst_delta, 'JST')
    yesterday_dt = dt.datetime.now(JST) - dt.timedelta(days=1)
    since_date = yesterday_dt.strftime('%Y-%m-%d')
    for k in keyword:
        # リツイートを取得する
        retweet = scrape_retweet(k)
        # リツイートしたユーザーを取得する
        retweet = get_retweet_author(retweet, since_date)
        pass


