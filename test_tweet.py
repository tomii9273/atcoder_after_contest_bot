# ツイートのテスト用。
# 「python test_tweet.py (API Key) (API Key Secret) (Access Token) (Access Token Secret)」で実行できる。

import sys

import tweepy


def make_test_tweet():
    consumer_key = sys.argv[1]  # API Key
    consumer_secret = sys.argv[2]  # API Key Secret
    access_token = sys.argv[3]
    access_token_secret = sys.argv[4]

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    res = client.create_tweet(text="test0")
    print(res.errors)


if __name__ == "__main__":
    make_test_tweet()
