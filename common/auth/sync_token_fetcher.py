import threading
from typing import Optional

from authlib.integrations.requests_client import OAuth2Session

from common.auth.base_token_fetcher import BaseTokenFetcher
from common.config.config import CYODA_VERIFY_SSL


class SyncTokenFetcher(BaseTokenFetcher):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        skip_ssl: bool,
        scope: Optional[str] = None,
    ) -> None:
        super().__init__()

        # Configure SSL verification for OAuth client
        verify_ssl = CYODA_VERIFY_SSL

        self._client = OAuth2Session(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            verify=not skip_ssl,
        )

        # Configure SSL verification for the underlying session
        if not verify_ssl:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "SSL verification is disabled for OAuth client (CYODA_VERIFY_SSL=false). "
                "This should only be used in development environments with self-signed certificates."
            )
            # Disable SSL verification for the requests session
            self._client.verify = False
        self._token_url = token_url
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            if self.is_token_stale():
                token = self._client.fetch_token(
                    url=self._token_url, grant_type="client_credentials"
                )
                self._update_token(token)
            return self._access_token or ""
