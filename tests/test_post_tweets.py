import unittest
from unittest.mock import Mock, patch

import requests

from check_cases_and_make_tweet import MaxRetriesExceededError, post_tweets


class PostTweetsTest(unittest.TestCase):
    def test_HTTPエラーのあとに同じ投稿を再試行する(self):
        client = Mock()
        client.create_tweet.side_effect = [requests.HTTPError(), {"data": {"id": "1"}}]
        with patch("check_cases_and_make_tweet.XClient", return_value=client):
            with patch("check_cases_and_make_tweet.time.sleep"):
                post_tweets(["投稿"], "consumer", "secret", "token", "token-secret")
        self.assertEqual(client.create_tweet.call_count, 2)
        client.create_tweet.assert_called_with(text="投稿")

    def test_タイムアウトが続く場合は失敗を通知する(self):
        client = Mock()
        client.create_tweet.side_effect = requests.Timeout
        with patch("check_cases_and_make_tweet.XClient", return_value=client):
            with patch("check_cases_and_make_tweet.time.sleep"):
                with self.assertRaises(MaxRetriesExceededError):
                    post_tweets(["投稿"], "consumer", "secret", "token", "token-secret")
        self.assertEqual(client.create_tweet.call_count, 10)
