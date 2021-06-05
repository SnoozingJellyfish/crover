import pickle
import io
import base64
import logging

from wordcloud import WordCloud
from scipy.cluster.hierarchy import linkage,dendrogram, fcluster, cut_tree
from collections import defaultdict

logger = logging.getLogger(__name__)


# 相対頻出度が高いword_num個の単語をword2vec上でクラスタリングする
def clustering(top_word2vec, cluster_all=3, algo='ward'):
    logger.info('------------------- clustering start ---------------------')

    words = top_word2vec['word']
    vec = top_word2vec['vec']
    word_count_rates = top_word2vec['word_count_rate']
    not_dict_word = top_word2vec['not_dict_word']

    if algo == 'kmeans':
        kmeans_model = KMeans(n_clusters=cluster_all, verbose=1, random_state=42, n_jobs=-1)
        kmeans_model.fit(vec)
        labels = kmeans_model.labels_
        label2csv(output_name, labels, words, word_count_rates, not_dict_word)

    elif algo == 'ward':
        link = linkage(vec, algo)
        # 1始まりを0始まりに変更
        labels = cut_tree(link, n_clusters=2)[:, 0]
        cluster_to_words = defaultdict(dict)
        for cluster_id, word, word_count_rate in zip(labels, words, word_count_rates):
            cluster_to_words[cluster_id][word] = word_count_rate

        for i in range(len(cluster_to_words)):
            cluster_to_words[i] = dict(sorted(cluster_to_words[i].items(), key=lambda x: x[1], reverse=True))

        #dendrogram(link, labels=labels)
        #plt.title('デンドログラム')
        #plt.savefig('dendrogram.jpg')

    logger.info('------------------- clustering finish ---------------------')
    return cluster_to_words


# クラスターをさらにクラスタリングする（k-means法用）
def zoomClustering(file_name, cluster_csv, cluster_num, zoom_cluster_all):
    input_name = file_name + '_top_word2vec_dic.pickle'
    with open(input_name, mode='rb') as f:
        top_word2vec_dic = pickle.load(f)

    df_cluster = pd.read_csv(cluster_csv, index_col=0).reset_index(drop=True)
    not_dict_word = top_word2vec_dic['not_dict_word']
    words = top_word2vec_dic['word']
    vec = top_word2vec_dic['vec']
    word_count_rate = top_word2vec_dic['word_count_rate']
    cluster_words = df_cluster['cluster' + str(cluster_num)].to_numpy()
    cluster_vec = []
    cluster_word_count_rate = []

    for i in range(len(cluster_words)):
        try:
            idx = words.index(cluster_words[i])
            cluster_vec.append(vec[idx])
            cluster_word_count_rate.append(word_count_rate[idx])
        except (TypeError, ValueError):
            continue

    top_word2vec_dic_cluster = {'word': cluster_words, 'vec': cluster_vec, 'word_count_rate': cluster_word_count_rate, 'not_dict_word': not_dict_word}
    top_word2vec_dic_cluster_pkl = file_name + '_cluster' + str(cluster_num) + '.pickle'
    with open(top_word2vec_dic_cluster_pkl, mode='wb') as f:
        pickle.dump(top_word2vec_dic_cluster, f)

    clustering(file_name, cluster_csv[:-4] + '_cluster' + str(cluster_num) + '_dim300.csv', word_num=len(cluster_words), cluster_all=zoom_cluster_all, algo='kmeans')


def make_word_cloud(cluster_to_words):
    colormaps = ['spring', 'summer', 'autumn', 'winter', 'PuRd', 'Wistia', 'cool', 'hot', 'YlGnBu', 'YlOrBr']
    b64_figures = []
    font_path = "./crover/data/font/NotoSansJP-Regular_subset.otf" # 通常使われる漢字を抽出したサブセット

    for i in range(len(cluster_to_words)):
        wordcloud = WordCloud(font_path=font_path, background_color="white",
                              width=500, height=500, colormap=colormaps[i])
        logger.info('fit word cloud')
        wordcloud.fit_words(cluster_to_words[i])

        logger.info('save word cloud')
        # 画像書き込み用バッファに画像を保存してhtmlに返す
        buf = io.BytesIO()
        img = wordcloud.to_image()
        img.save(buf, 'PNG')
        logger.info('b64 encode')
        qr_b64str = base64.b64encode(buf.getvalue()).decode("utf-8")
        b64_figures.append("data:image/png;base64,{}".format(qr_b64str))

    return b64_figures