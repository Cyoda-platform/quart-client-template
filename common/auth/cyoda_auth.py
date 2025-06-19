import asyncio
import threading
import time
import logging
from typing import Optional

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.requests_client import OAuth2Session

logger = logging.getLogger(__name__)

class CyodaAuthService:
    """
    OAuth2-based auth service for Cyoda API using client_credentials flow.
    Handles token acquisition, caching, and re-authentication on expiration.
    Supports both async and sync contexts.
    """

    def __init__(self, client_id: str, client_secret: str, token_url: str, scope: Optional[str] = None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._scope = scope

        self._access_token: Optional[str] = None
        self._access_token_expiry: Optional[float] = None

        self._client: Optional[AsyncOAuth2Client] = None
        self._sync_client: Optional[OAuth2Session] = None
        self._thread_lock = threading.Lock()
        self._async_lock = asyncio.Lock()


    def invalidate_tokens(self):
        """
        Wipe any cached tokens so the next request does a full re-authentication.
        """
        with self._thread_lock:
            logger.info("Invalidating cached OAuth2 tokens")
            self._access_token = None
            self._access_token_expiry = None

    # -----------------------
    # ASYNC VERSION
    # -----------------------

    async def get_access_token(self) -> str:
        """
        Returns a valid access token, fetching a new one if missing or expired (async).
        """
        async with self._async_lock:
            if self._is_token_stale():
                await self._fetch_access_token()
            return self._access_token

    async def _fetch_access_token(self):
        """
        Perform client_credentials token request using Authlib (async).
        """
        if not self._client:
            self._client = AsyncOAuth2Client(
                client_id=self._client_id,
                client_secret=self._client_secret,
                scope=self._scope
            )

        logger.info(f"[async] Requesting new access token from {self._token_url}")
        token = await self._client.fetch_token(token_url=self._token_url)

        self._access_token = token.get("access_token")
        expires_in = token.get("expires_in", 300)
        self._access_token_expiry = time.time() + float(expires_in)

        logger.info("[async] Successfully obtained new OAuth2 access token")

    # -----------------------
    # SYNC VERSION
    # -----------------------

    def get_access_token_sync(self) -> str:
        """
        Synchronous version of get_access_token for use in sync contexts.
        """
        with self._thread_lock:
            if self._is_token_stale():
                self._fetch_access_token_sync()
            return self._access_token

    def _fetch_access_token_sync(self):
        """
        Perform client_credentials token request using Authlib (sync).
        """
        if not self._sync_client:
            self._sync_client = OAuth2Session(
                client_id=self._client_id,
                client_secret=self._client_secret,
                scope=self._scope,
            )

        logger.info(f"[sync] Requesting new access token from {self._token_url}")

        try:
            token = self._sync_client.fetch_token(
                url=self._token_url,
                grant_type="client_credentials"
            )
        except Exception as e:
            logger.error("Failed to fetch token synchronously", exc_info=e)
            raise

        self._access_token = token.get("access_token")
        expires_in = token.get("expires_in", 300)
        self._access_token_expiry = time.time() + float(expires_in)

        logger.info("[sync] Successfully obtained new OAuth2 access token")

    # -----------------------
    # Shared Logic
    # -----------------------

    def _is_token_stale(self) -> bool:
        """
        Determine whether the access token is missing or expiring within 60 seconds.
        """
        now = time.time()
        return (
            not self._access_token
            or not self._access_token_expiry
            or now >= self._access_token_expiry - 60
        )
