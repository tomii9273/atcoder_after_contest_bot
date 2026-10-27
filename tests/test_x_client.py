import json
import unittest
from unittest.mock import patch

import requests

from x_client import XClient


class XClientTest(unittest.TestCase):
    def setUp(self):
        self.client = XClient("consumer", "secret", "token", "token-secret", timeout=17)
        self.addCleanup(self.client.session.close)

    def test_投稿に署名とタイムアウトを設定する(self):
        response = requests.Response()
        response.status_code = 201
        response._content = b'{"data": {"id": "123"}}'
        with patch.object(self.client.session, "send", return_value=response) as send:
            result = self.client.create_tweet(text="投稿テスト")
        request = send.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, "https://api.x.com/2/tweets")
        self.assertEqual(json.loads(request.body), {"text": "投稿テスト"})
        authorization = request.headers["Authorization"].decode()
        self.assertIn('oauth_token="token"', authorization)
        self.assertIn('oauth_signature_method="HMAC-SHA1"', authorization)
        self.assertIn("oauth_signature=", authorization)
        self.assertEqual(send.call_args.kwargs["timeout"], 17)
        self.assertEqual(result["data"]["id"], "123")

    def test_HTTPエラーを成功として扱わない(self):
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                with patch.object(self.client.session, "send", return_value=response):
                    with self.assertRaises(requests.HTTPError):
                        self.client.create_tweet(text="投稿テスト")

    def test_通信タイムアウトを呼び出し元に伝える(self):
        with patch.object(self.client.session, "send", side_effect=requests.Timeout):
            with self.assertRaises(requests.Timeout):
                self.client.create_tweet(text="投稿テスト")
