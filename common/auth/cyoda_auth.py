import json
import logging
import time
from typing import Optional

import requests

from common.config import config
from common.config.config import CYODA_API_URL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CyodaAuthService:
    """
    Auth service for interacting with the Cyoda API.
    Handles obtaining and caching a refresh token, fetching access tokens,
    and transparently re-authenticating if tokens are revoked.
    """

    def __init__(self):
        self._refresh_token: Optional[str] = None
        self._access_token: Optional[str] = None
        self._access_token_expiry: Optional[float] = None

    def invalidate_tokens(self):
        """
        Wipe any cached tokens so the next request does a full login.
        """
        logger.info("Invalidating cached tokens")
        self._refresh_token = None
        self._access_token = None
        self._access_token_expiry = None

    def _login(self) -> str:
        """
        Perform login to obtain a new refresh token.
        """
        login_url = f"{CYODA_API_URL}/auth/login"
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
        credentials = {"username": config.API_KEY, "password": config.API_SECRET}
        payload = json.dumps(credentials)

        logger.info(f"Authenticating with Cyoda API at {login_url}")
        resp = requests.post(login_url, headers=headers, data=payload)

        if resp.status_code != 200:
            logger.error(f"Login failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")

        data = resp.json()
        token = data.get('refreshToken') or data.get('refresh_token')
        if not token:
            logger.error("No refresh token found in login response")
            raise RuntimeError("Refresh token missing in login response")

        logger.info("Successfully obtained refresh token")
        return token

    def _refresh_access_token(self) -> None:
        """
        Use the refresh token to get a new access token.
        If the refresh token itself is revoked (HTTP 401/403), wipe tokens and retry login.
        """
        if not self._refresh_token:
            self._refresh_token = self._login()

        token_url = f"{CYODA_API_URL}/auth/token"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._refresh_token}'
        }

        logger.info(f"Refreshing access token at {token_url}")
        resp = requests.get(token_url, headers=headers)

        # If the refresh token has been revoked or is invalid:
        if resp.status_code in (401, 403):
            logger.warning(f"Refresh token invalid ({resp.status_code}); re-authenticating")
            self.invalidate_tokens()
            # retry from scratch
            self._refresh_token = self._login()
            return self._refresh_access_token()

        if resp.status_code != 200:
            logger.error(f"Token refresh failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Token refresh failed: {resp.status_code} {resp.text}")

        data = resp.json()
        token = data.get('token') or data.get('access_token')
        expiry = data.get('expires_in')  # seconds from now

        if not token:
            logger.error("No access token found in token response")
            raise RuntimeError("Access token missing in token response")

        self._access_token = token
        self._access_token_expiry = (
            time.time() + float(expiry)
            if expiry is not None else time.time() + 300
        )

        logger.info("Successfully obtained access token")
        return None

    def get_access_token(self) -> str:
        """
        Returns a valid access token, refreshing it if it's missing,
        expired, or about to expire within 60 seconds.
        """
        now = time.time()
        if (not self._access_token) or (self._access_token_expiry is not None and now >= self._access_token_expiry - 60):
            self._refresh_access_token()
        return self._access_token