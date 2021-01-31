import pickle
from tqdm import tqdm
import pandas as pd
import numpy as np
import gensim.models.keyedvectors as word2vec_for_txt
import gensim
import matplotlib.pyplot as plt

def df_concat(csv1, csv2, output_csv):
    df1 = pd.read_csv(csv1, index_col=0)
    df2 = pd.read_csv(csv2, index_col=0)
    df_concat_tweets = pd.concat([df1, df2])
    df_concat_tweets.reset_index(drop=True).to_csv(output_csv)


def RTcount(tweet_csv):
    df_tweet = pd.read_csv(tweet_csv, index_col=0)

    for i in tqdm(range(len(df_tweet))):
        if df_tweet['tweet'][i].to_numpy()[0] in df_tweet['tweet'][i+1:].to_numpy():
            print('RT', i, df_tweet['tweet'][i].to_numpy()[0])


def histVisualize(TFIDFcsv):
    df_TFIDF_count = pd.read_csv(TFIDFcsv, names=['word', 'count', 'TFIDF'])
    tfidf = df_TFIDF_count['TFIDF'].to_numpy()
    tfidf = [160 - float(s) for s in tfidf[1:] if float(s) > 2.1]
    plt.hist(tfidf, bins=int(np.max(tfidf)), cumulative=True)
    plt.savefig(TFIDFcsv[:-4] + '_hist.jpg')

def extractTFIDF(TFIDFcsv, num):
    df_TFIDF_count = pd.read_csv(TFIDFcsv, index_col=0).reset_index(drop=True)
    df_TFIDF_count[:num].to_csv(TFIDFcsv[:-4] + str(num) + '.csv')

def pickle_dump(word2vec_dic, algo='mecab'):
    if algo == 'mecab':
        model = word2vec_for_txt.Word2VecKeyedVectors.load_word2vec_format(word2vec_dic)
    elif algo == 'sudachi':
        model = gensim.models.KeyedVectors.load(word2vec_dic)
        vocab = model.keys()

    with open(word2vec_dic[:-4] + '.pickle', mode='wb') as f:
        pickle.dump(model, f)