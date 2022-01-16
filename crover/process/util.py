import os
import pickle
from io import BytesIO
import logging
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


# datastore upload retweet_info
def datastore_upload_retweet():
    from google.cloud import datastore
    # from crover import word2vec
    client = datastore.Client()
    logger.info('start upload retweet info')

    retweet_info = {'テスト-コロナ':
                           {'2022/1/1':
                                {'テスト-コロナ1': [1, 2, 3],
                                 'テスト-コロナ2': [2, 3, 4]},
                            '2022/1/2':
                                {'テスト-コロナ2': [5, 6],
                                 'テスト-コロナ3': [1, 2, 3, 4]}},
                       'テスト-地震':
                           {'2022/1/3':
                                {'テスト-地震1': [1, 2, 3],
                                 'テスト-地震2': [2, 3, 4]},
                            '2022/1/4':
                                {'テスト-地震2': [5, 6],
                                 'テスト-地震3': [1, 2, 3, 4]}}}

    keyword_kind = "retweet_keyword"
    '''
    keyword_entities = []
    # リツイートのキーワードをアップロード
    for k in retweet_info.keys():
        logger.info(f'retweet keyword: {k}')
        keyword_entity = datastore.Entity(client.key(keyword_kind))
        keyword_entity.update({'keyword': k})
        keyword_entities.append(keyword_entity)

    client.put_multi(keyword_entities)
    '''

    tweet_kind = 'retweeted_tweet'

    # リツイートした日付をアップロード
    date_kind = 'retweeted_date'
    query = client.query(kind=keyword_kind)
    keyword_entities = list(query.fetch())
    for keyword_entity in keyword_entities:
        keyword = keyword_entity["keyword"]
        logger.info(f'date of retweet keyword- {keyword}')
        '''
        date_entities = []
        for d in retweet_info[keyword].keys():
            logger.info(f'date: {d}')
            #date_entity = datastore.Entity(client.key(date_kind, parent=keyword_entity.key.id))
            date_entity = datastore.Entity(client.key(date_kind, parent=keyword_entity.key))
            date_entity.update({'date': d})
            date_entities.append(date_entity)

        client.put_multi(date_entities)
        '''
        
        # リツイートされたツイートとリツイートした人をアップロード
        query = client.query(kind=date_kind, ancestor=keyword_entity.key)
        date_entities = list(query.fetch())
        for date_entity in date_entities:
            date = date_entity['date']
            logger.info(f'tweet of retweeted date- {date}')
            tweet_entities = []
            for t in retweet_info[keyword][date].keys():
                logger.info(f'tweet: {t}')
                #tweet_entity = datastore.Entity(client.key(tweet_kind, parent=date_entity.key.id))
                tweet_entity = datastore.Entity(client.key(tweet_kind, parent=date_entity.key))
                tweet_entity.update({'tweet': t, 're_author': retweet_info[keyword][date][t]})
                tweet_entities.append(tweet_entity)

            client.put_multi(tweet_entities)

