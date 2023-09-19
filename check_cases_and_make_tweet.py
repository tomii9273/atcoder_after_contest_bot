import sys
import time

import tweepy

from get_and_update_added_cases import get_and_update_added_cases


class MaxRetriesExceededError(Exception):
    pass


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

    tweet = "以下の問題に新たなテストケースが追加されました。\n"
    for contest_name, task_name, added_cases in all_added_cases:
        assert added_cases != []
        if re.fullmatch("a[brg]c[0-9]{3}_[a-z]", task_name):  # 一般的な表記の場合は大文字の方が見やすいので変換
            task_name_in_tweet = task_name.upper()
        else:
            task_name_in_tweet = task_name
        tweet += f"{task_name_in_tweet}: "
        for ind, added_case in enumerate(added_cases):
            tweet += f"{added_case}"
            if ind != len(added_cases) - 1:
                if ind == 2:
                    tweet += " など"
                    break
                tweet += ", "
        tweet += "\n"
        tweet += f"https://atcoder.jp/contests/{contest_name}/tasks/{task_name}\n"  # 末尾の場合、この改行はツイート時に消される

    print("tweet:", tweet)

    max_retries = 5  # 5 回試す
    for t in range(max_retries):
        try:
            client.create_tweet(text=tweet)
            print(f"tweet {t} succeeded")
            return
        except tweepy.TweepyException as e:
            print(f"tweet {t} failed")
            print(f"reason: {e}")
            time.sleep(1)

    raise MaxRetriesExceededError()


if __name__ == "__main__":
    check_cases_and_make_tweet()
