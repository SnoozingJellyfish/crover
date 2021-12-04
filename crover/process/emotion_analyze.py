
import copy
from pprint import pprint
import io
import base64
import logging
import pickle

import matplotlib.pyplot as plt
plt.switch_backend('Agg')
import numpy as np
from wordcloud import WordCloud

from crover.process.mlask_no_mecab import MLAskNoMecab
#from transformers import pipeline,AutoTokenizer,BertTokenizer,AutoModelForSequenceClassification,BertJapaneseTokenizer, BertForMaskedLM
from asari.api import Sonar
sonar = Sonar()

logger = logging.getLogger(__name__)

def emotion_analyze_all(words, tweets):
    logger.info('collect tweet including cluster word')
    cluster_tweets = tweet_collect(words, tweets)
    logger.info('emotion analyze')
    emotion_elem, emotion_tweet_dict, emotion_word = emotion_analyze(cluster_tweets, algo='asari')
    logger.info('make pie chart')
    #b64_chart = make_emotion_pie_chart(emotion_count)
    if len(emotion_word) == 0:
        b64_figure = 'none'
    else:
        b64_figure = make_emotion_wordcloud(emotion_word)

    return emotion_elem, b64_figure, emotion_tweet_dict

# クラスタリングされた単語を含むツイートを取得する
def tweet_collect(words, tweets):
    tweets = np.array(tweets)
    tweet_id = list(np.arange(len(tweets)))
    tweet_id_new = copy.deepcopy(tweet_id)
    cluster_tweet_id = []

    for w in words:
        for i in tweet_id:
            try:
                if w in tweets[i, 1]:
                    cluster_tweet_id.append(i)
                    tweet_id_new.remove(i)
            except TypeError:
                continue

        tweet_id = copy.deepcopy(tweet_id_new)

    cluster_tweets = tweets[cluster_tweet_id]
    return cluster_tweets


# 感情分析する
def emotion_analyze(cluster_tweets, algo='mlask', max_word=50):
    emotion_count = {'POSITIVE': 0, 'mostly_POSITIVE': 0, 'NEUTRAL': 0, 'mostly_NEGATIVE': 0, 'NEGATIVE': 0}
    emotion_tweet = {'POSITIVE': [], 'mostly_POSITIVE': [], 'NEUTRAL': [], 'mostly_NEGATIVE': [], 'NEGATIVE': []}
    emotion_word = {}

    if algo == 'mlask':
        with open('crover/data/mlask_emotion_dictionary.pickle', 'rb') as f:
            mlask_emotion_dictionary = pickle.load(f)
        emotion_analyzer = MLAskNoMecab(mlask_emotion_dictionary)
        for tweet in cluster_tweets:
            result_dic = emotion_analyzer.analyze(tweet[1], tweet[2])
            if result_dic['emotion'] == None:
                emotion_count['NEUTRAL'] += 1
                emotion_tweet['NEUTRAL'].append(tweet[1])
            else:
                for emo in result_dic['emotion'].keys():
                    for w in result_dic['emotion'][emo]:
                        if w[-1] == 'S':  # pymlaskのバグ
                            w = w[:-4]
                        if w in emotion_word.keys():
                            emotion_word[w] += 1
                        else:
                            emotion_word[w] = 1

                emotion_count[result_dic['orientation']] += 1
                emotion_tweet[result_dic['orientation']].append(tweet[1])

        emotion_word_list = sorted(emotion_word.items(), key=lambda x: x[1], reverse=True)
        extract_emotion_word = dict(emotion_word_list[:np.min((len(emotion_word_list), max_word))])

    elif algo == 'oseti':
        emotion_analyzer = oseti.Analyzer()
        for i in tqdm(range(len(df_cluster))):
            df_cluster.loc[i, 'orientation'] = np.mean(emotion_analyzer.analyze(df_cluster['tweet'][i]))

    elif algo == 'asari':
        for tweet in cluster_tweets:
            result_dic = sonar.ping(tweet[1])
            posi_conf = result_dic.classes[1].confidence
            if posi_conf > 0.75:
                emotion_count['POSITIVE'] += 1
                emotion_tweet['POSITIVE'].append(str(posi_conf) + tweet[1])
            elif posi_conf > 0.25:
                emotion_count['NEUTRAL'] += 1
                emotion_tweet['NEUTRAL'].append(str(posi_conf) + tweet[1])
            else:
                emotion_count['NEGATIVE'] += 1
                emotion_tweet['NEGATIVE'].append(str(posi_conf) + tweet[1])

        #emotion_word_list = sorted(emotion_word.items(), key=lambda x: x[1], reverse=True)
        #extract_emotion_word = dict(emotion_word_list[:np.min((len(emotion_word_list), max_word))])
        extract_emotion_word = {'asariテスト': 1}


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
    emotion_tweet_dict = {'positive': emotion_tweet['POSITIVE'] + emotion_tweet['mostly_POSITIVE'],
                          'neutral': emotion_tweet['NEUTRAL'],
                          'negative': emotion_tweet['NEGATIVE'] + emotion_tweet['mostly_NEGATIVE']
                          }

    emotion_elem = [(emotion_count['POSITIVE'] + emotion_count['mostly_POSITIVE']) * 100 // len(cluster_tweets),
                    emotion_count['NEUTRAL'] * 100 // len(cluster_tweets),
                    100 - (emotion_count['POSITIVE'] + emotion_count['mostly_POSITIVE']) * 100 // len(cluster_tweets) - emotion_count['NEUTRAL'] * 100 // len(cluster_tweets)]

    return emotion_elem, emotion_tweet_dict, extract_emotion_word


def make_emotion_pie_chart(emotion_count):
    x = np.array([emotion_count['POSITIVE'] + emotion_count['mostly_POSITIVE'], emotion_count['NEUTRAL'], emotion_count['NEGATIVE'] + emotion_count['mostly_NEGATIVE']])
    label = ['ポジティブ', 'ニュートラル', 'ネガティブ']
    colors = ["#EE8B98", '#9CE7B0', '#75B2F7']
    font_color = ["firebrick", 'darkgreen', 'darkblue']
    plt.figure(figsize=(10, 10))
    #plt.subplots_adjust(left=0.3, right=0.7)
    #patches, texts = plt.pie(x, labels=label, counterclock=True, startangle=90, colors=colors)
    patches, texts = plt.pie(x, counterclock=True, startangle=90, colors=colors)
    for i in range(len(texts)):
        texts[i].set_size(48)
        texts[i].set_color(font_color[i])
    buf = io.BytesIO()
    plt.savefig(buf)
    qr_b64str = base64.b64encode(buf.getvalue()).decode("utf-8")
    b64_chart = "data:image/png;base64,{}".format(qr_b64str)
    return b64_chart


def make_emotion_wordcloud(emotion_word):
    font_path = "./crover/data/font/NotoSansJP-Regular_subset.otf"  # 通常使われる漢字を抽出したサブセット
    wordcloud = WordCloud(font_path=font_path, background_color="white", width=500, height=500,
                          colormap='Dark2'
                          #, mask=msk, contour_width=20, contour_color='gray'
                          )
    logger.info('fit word cloud')
    wordcloud.fit_words(emotion_word)

    logger.info('save word cloud')
    # 画像書き込み用バッファに画像を保存してhtmlに返す
    buf = io.BytesIO()
    img = wordcloud.to_image()
    img.save(buf, 'PNG')
    logger.info('b64 encode')
    qr_b64str = base64.b64encode(buf.getvalue()).decode("utf-8")
    b64_figure = "data:image/png;base64,{}".format(qr_b64str)

    return b64_figure


# 感情分析の結果を出力する
def emotion_count(cluster_tweets):
    count_dic = {}
    df_cluster = pd.read_csv(analyzed_csv, index_col=0)

    posi = (df_cluster['orientation'] == 'POSITIVE').sum()
    m_posi = (df_cluster['orientation'] == 'mostly_POSITIVE').sum()
    m_nega = (df_cluster['orientation'] == 'mostly_NEGATIVE').sum()
    nega = (df_cluster['orientation'] == 'NEGATIVE').sum()
    neut = len(df_cluster) - posi - m_posi - m_nega - nega
    count_dic['orientation'] = {'POSITIVE': posi, 'mostly_POSITIVE': m_posi, 'NEUTRAL': neut, 'mostly_NEGATIVE': m_nega, 'NEGATIVE': nega}

    pprint(count_dic)