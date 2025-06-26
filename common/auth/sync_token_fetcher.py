import threading
from authlib.integrations.requests_client import OAuth2Session

from common.auth.base_token_fetcher import BaseTokenFetcher


class SyncTokenFetcher(BaseTokenFetcher):
    def __init__(self, client_id, client_secret, token_url, scope=None):
        super().__init__()
        self._client = OAuth2Session(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope
        )
        self._token_url = token_url
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            if self.is_token_stale():
                token = self._client.fetch_token(url=self._token_url, grant_type="client_credentials")
                self._update_token(token)
            return self._access_token
