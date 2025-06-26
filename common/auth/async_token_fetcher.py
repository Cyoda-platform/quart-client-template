import asyncio
from authlib.integrations.httpx_client import AsyncOAuth2Client

from common.auth.base_token_fetcher import BaseTokenFetcher


class AsyncTokenFetcher(BaseTokenFetcher):
    def __init__(self, client_id, client_secret, token_url, scope=None):
        super().__init__()
        self._client = AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope
        )
        self._token_url = token_url
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        async with self._lock:
            if self.is_token_stale():
                token = await self._client.fetch_token(url=self._token_url)
                self._update_token(token)
            return self._access_token
