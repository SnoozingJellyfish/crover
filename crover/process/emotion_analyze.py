import copy
from pprint import pprint

from tqdm import tqdm
import pandas as pd
import numpy as np
from mlask import MLAsk
import oseti
from asari.api import Sonar
#from transformers import pipeline,AutoTokenizer,BertTokenizer,AutoModelForSequenceClassification,BertJapaneseTokenizer, BertForMaskedLM


def all(file_name, cluster_csv, cluster_num):
    algo = 'mlask'
    tweet_collect(file_name, cluster_csv, cluster_num)
    emotion_analyze(cluster_csv, cluster_num, algo=algo)
    analyzed_csv = cluster_csv[:-4] + '-' + str(cluster_num) + '_analyzed-' + algo + '.csv'
    emotion_count(analyzed_csv)

# クラスタリングされた単語を含むツイートを取得する
def tweet_collect(file_name, cluster_csv, cluster_num):
    tweet_csv = file_name + '.csv'
    output_name = cluster_csv[:-4] + '-' + str(cluster_num) + '_tweet.csv'

    df_cluster = pd.read_csv(cluster_csv, index_col=0).reset_index(drop=True)
    words = df_cluster['cluster' + str(cluster_num)].to_numpy()
    df_tweets = pd.read_csv(tweet_csv, index_col=0).reset_index(drop=True)

    cluster_tweet_id = []
    tweet_id = list(range(len(df_tweets['tweet'])))
    tweet_id_new = copy.deepcopy(tweet_id)
    for w in tqdm(words):
        for i in tweet_id:
            try:
                if w in df_tweets['tweet'][i]:
                    cluster_tweet_id.append(i)
                    tweet_id_new.remove(i)
            except TypeError:
                continue

        tweet_id = copy.deepcopy(tweet_id_new)

    df_tweets.iloc[cluster_tweet_id]['tweet'].to_csv(output_name)


# 感情分析する
def emotion_analyze(cluster_csv, cluster_num, algo='mlask'):
    input_name = cluster_csv[:-4] + '-' + str(cluster_num) + '_tweet.csv'
    output_name = cluster_csv[:-4] + '-' + str(cluster_num) + '_analyzed-' + algo + '.csv'
    df_cluster = pd.read_csv(input_name, index_col=0).reset_index(drop=True)

    if algo == 'mlask':
        emotion_analyzer = MLAsk()
        for i in tqdm(range(len(df_cluster))):
            result_dic = emotion_analyzer.analyze(df_cluster['tweet'][i])
            if result_dic['emotion'] == None:
                df_cluster.loc[i, 'emotion'] = 'None'
            else:
                df_cluster.loc[i, 'orientation'] = result_dic['orientation']
                df_cluster.loc[i, 'activation'] = result_dic['activation']
                df_cluster.loc[i, 'intension'] = result_dic['intension']
                df_cluster.loc[i, 'emotion'] = str(list(result_dic['emotion'].keys()))

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

    df_cluster.to_csv(output_name)


# 感情分析の結果を出力する
def emotion_count(analyzed_csv):
    count_dic = {}
    df_cluster = pd.read_csv(analyzed_csv, index_col=0)

    posi = (df_cluster['orientation'] == 'POSITIVE').sum()
    m_posi = (df_cluster['orientation'] == 'mostly_POSITIVE').sum()
    m_nega = (df_cluster['orientation'] == 'mostly_NEGATIVE').sum()
    nega = (df_cluster['orientation'] == 'NEGATIVE').sum()
    neut = len(df_cluster) - posi - m_posi - m_nega - nega
    count_dic['orientation'] = {'POSITIVE': posi, 'mostly_POSITIVE': m_posi, 'NEUTRAL': neut, 'mostly_NEGATIVE': m_nega, 'NEGATIVE': nega}

    act = (df_cluster['activation'] == 'ACTIVE').sum()
    pas = (df_cluster['activation'] == 'PASSIVE').sum()
    neut = len(df_cluster) - act - pas
    count_dic['activation'] = {'ACTIVE': act, 'NEUTRAL': neut, 'PASSIVE': pas}

    pprint(count_dic)