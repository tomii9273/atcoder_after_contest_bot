from requests_oauthlib import OAuth1Session


class XClient:
    """OAuth 1.0a で X API に投稿するためのクライアント。"""

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        timeout: int = 60,
    ) -> None:
        self.session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        self.timeout = timeout

    def create_tweet(self, *, text: str) -> dict:
        """投稿結果を返し、HTTP エラーと通信エラーを呼び出し元に伝える。"""
        response = self.session.post(
            "https://api.x.com/2/tweets",
            json={"text": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
