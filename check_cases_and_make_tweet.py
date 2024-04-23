import re
import sys
import time

import tweepy

from get_and_update_added_cases import get_and_update_added_cases


class MaxRetriesExceededError(Exception):
    pass


def count_half_width_chars_as_tweet(s: str) -> int:
    """ツイートに含まれる半角換算文字数を返す (URL は 23 文字換算)"""
    ind = 0
    count = 0
    while ind < len(s):
        if s[ind : ind + 8] == "https://":
            count += 23
            while ind < len(s) and s[ind] not in ("\n", " "):
                ind += 1
        elif ord(s[ind]) <= 0x7F:
            count += 1
            ind += 1
        else:
            count += 2
            ind += 1
    return count


def check_cases_and_make_tweet() -> None:
    """
    14 日以内に開始された ABC, ARC, AGC の各問題について、
    前回確認時点 (無い場合、コンテスト開始直後時点) から新たに追加されたテストケース一覧を取得し、
    存在する場合にツイートする。testcases.txt の更新も行う。
    """
    consumer_key = sys.argv[1]
    consumer_secret = sys.argv[2]
    access_token = sys.argv[3]
    access_token_secret = sys.argv[4]
    password = sys.argv[5]

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    all_added_cases = get_and_update_added_cases(password)

    if len(all_added_cases) == 0:
        return

    tweet_head = "以下の問題に新たなテストケースが追加されました。\n"

    tweet_bodies = []
    tweet_body = ""

    for contest_name, task_name, added_cases in all_added_cases:
        tweet_body = ""
        assert added_cases != []
        if re.fullmatch("a[brg]c[0-9]{3}_[a-z]", task_name):  # 一般的な表記の場合は大文字の方が見やすいので変換
            task_name_in_tweet = task_name.upper()
        else:
            task_name_in_tweet = task_name
        tweet_body += f"{task_name_in_tweet}: "
        for ind, added_case in enumerate(added_cases):
            tweet_body += f"{added_case}"
            if ind != len(added_cases) - 1:
                if ind == 1:  # テストケースが 3 個以上の場合は省略表記にする
                    tweet_body += " など"
                    break
                tweet_body += ", "
        tweet_body += "\n"
        tweet_body += f"https://atcoder.jp/contests/{contest_name}/tasks/{task_name}\n"  # 末尾の場合、この改行はツイート時に消される
        tweet_bodies.append(tweet_body)

    tweets = []
    tweet = tweet_head
    for tweet_body in tweet_bodies:
        if count_half_width_chars_as_tweet(tweet + tweet_body) > 275:  # 5 文字分安全マージン
            tweets.append(tweet)
            tweet = tweet_head + tweet_body
        else:
            tweet += tweet_body
    tweets.append(tweet)

    print("tweets:", tweets)

    max_retries = 5  # ツイートをそれぞれ最大 5 回試す

    for ind, tweet in enumerate(tweets):
        for t in range(max_retries):
            try:
                client.create_tweet(text=tweet)
                print(f"tweet {ind} succeeded (time: {t})")
                break
            except tweepy.TweepyException as e:
                print(f"tweet {ind} failed (time: {t})")
                print(f"reason: {e}")
                time.sleep(1)
        else:
            raise MaxRetriesExceededError()


if __name__ == "__main__":
    check_cases_and_make_tweet()
