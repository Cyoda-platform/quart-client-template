from abc import ABC, abstractmethod
import time

class BaseTokenFetcher(ABC):
    def __init__(self):
        self._access_token = None
        self._access_token_expiry = None

    def is_token_stale(self) -> bool:
        return (
            not self._access_token or
            not self._access_token_expiry or
            time.time() >= self._access_token_expiry - 60
        )

    def invalidate_tokens(self):
        self._access_token = None
        self._access_token_expiry = None

    def _update_token(self, token: dict):
        self._access_token = token.get("access_token")
        self._access_token_expiry = time.time() + float(token.get("expires_in", 300))

    @abstractmethod
    def get_token(self) -> str:
        pass
