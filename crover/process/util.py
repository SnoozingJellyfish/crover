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
    #from crover import word2vec
    client = datastore.Client()

    storage_client = storage.Client()
    bucket_name = os.environ.get('BUCKET_NAME')

    logger.info('start loading dict_all_count')
    dict_all_count = download_from_cloud(storage_client, bucket_name, os.environ.get('DICT_ALL_COUNT'))
    #logger.info('start loading mlask dict')
    #mlask_emotion_dictionary = download_from_cloud(storage_client, bucket_name, os.environ.get('MLASK_EMOTION_DICTIONARY'))
    logger.info('finish loading')
    upload_dict = dict_all_count
    print('num of dict_all_count:', len(upload_dict.keys()))
    upload_folder_name = "sudachi_word2vec_300d"
    #upload_folder_name = "sudachi_all_word_count"
    i = 0
    entities = []

    #for w in word2vec.keys():
    for w in upload_dict.keys():
        i += 1
        if i > up_vec_num and type(w) == str and w[0] != '_' and w != '':
            entity = datastore.Entity(client.key(upload_folder_name, w))
            #entity.update({'vec': list(upload_dict[w].astype(np.float64))})
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

    for i in range(split, 50):
        logger.info('start loading word2vec dict')
        upload_dict = download_from_cloud(storage_client, bucket_name,
                                          'sudachi_word2vec_dict_300d_50split/sudachi_word2vec_dict_300d_50-' + str(i+1) + '.pickle')
        logger.info('finish loading')
        print('num of word2vec keys:', len(upload_dict.keys()))
        upload_folder_name = "sudachi_word2vec_300d"

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

            if (j + 1) % 500 == 0 and len(entities) > 0:
                logger.info('split:' + str(i) + ',' + str(j+1))
                client.put_multi(entities)
                entities = []

        if len(entities) > 0:
            logger.info('split:' + str(i) + ',' + str(j + 1))
            client.put_multi(entities)