from common.auth.async_token_fetcher import AsyncTokenFetcher
from common.auth.sync_token_fetcher import SyncTokenFetcher


class CyodaAuthService:
    def __init__(self, client_id: str, client_secret: str, token_url: str, scope: str = None):
        self._sync = SyncTokenFetcher(client_id, client_secret, token_url, scope)
        self._async = AsyncTokenFetcher(client_id, client_secret, token_url, scope)


    def get_access_token_sync(self) -> str:
        return self._sync.get_token()

    async def get_access_token(self) -> str:
        return await self._async.get_token()

    def invalidate_tokens(self):
        self._sync.invalidate_tokens()
        self._async.invalidate_tokens()