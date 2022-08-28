<img src="frontend/src/assets/crover_logo_3_leaf_rgb_no_trans.png" width=50%>

Twitterのつぶやきの感情分析とネットワーク分析を行うwebアプリケーションです。

# Environment
- Google Cloud Platform AppEngine
- Python 3.9
- Flask 2.0.1
- Vue 3.2

# App URL
https://crover-word-ocean.uc.r.appspot.com/

# Function
## 感情分析
1. Twitter API により、入力されたキーワードを含む直近のツイートを取得します。
1. 得られたツイートを[Sudachipy](https://github.com/WorksApplications/SudachiPy)
   を用いて分かち書き（単語・品詞分類）します。それらの単語は頻出順に大きく Word Cloudとして表示されます。
1. Word Cloud上の「感情分析」ボタンを押すと、[pymlask](https://github.com/ikegami-yukino/pymlask)
   によって、ルールベースでそれらの単語を含むツイートをポジティブ・ニュートラル・ネガティブの３つに分類します。
1. Word Cloudの上の「意味で分ける」ボタンを押すと、単語に割り当てられたベクトル（word2vec: <a href="http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/">WikiEntVec（鈴木正敏、2019 年/CC-BY-SA</a>）に基づいて階層的クラスタリングが行われ、Word Cloudが分割されます。

## ネットワーク分析
1. 選択肢の単語を含む指定された期間につぶやかれたツイートのうち、リツイートされた回数の多いツイートを取得します。
1. 取得したツイートを円（ノード）で表したネットワークグラフを表示します。リツイートされた回数が多いツイートほど大きな円になります。同じユーザーによってリツイートされることの多い2つのツイートは線（リンク）で結ばれます。
1. 取得したツイートに頻出する単語を全体頻出ワードとしてWord Cloudで表示します。全体のネットワークを結合度によってグループに分け、それぞれのグループで頻出する単語をグループ頻出ワードとしてWord Cloudで表示します。


# License
GPL v3

# Author
https://twitter.com/snooze_jelly
