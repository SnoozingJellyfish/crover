import os
import re
import logging

from crover.process.preprocess import scrape_retweet, get_retweet_user

logger = logging.getLogger(__name__)


def analyze_network(keyword, max_tweets):
    #TODO: リツイートを取得する
    retweet_id, retweet_text = scrape_retweet(keyword, max_tweets)

    #TODO: リツイートしたユーザーを取得する
    user = get_retweet_user(retweet_id, retweet_text)

    #TODO: リツイート間のユーザー類似度を算出する

    #TODO: 閾値以上の類似度のユーザー間を繋いだグラフを作る

    #TODO: ネットワーク図を描画する

    return -1