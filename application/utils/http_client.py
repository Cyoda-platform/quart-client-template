"""
HTTP Client Wrapper with Retry Support

Provides a lightweight HTTP client wrapper with configurable retry policies
for external service calls used by Order processors.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


class RetryPolicy(Enum):
    """Retry policy types."""
    FIXED = "FIXED"
    EXPONENTIAL = "EXPONENTIAL"
    LINEAR = "LINEAR"


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Any = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class HttpRetryableError(HttpClientError):
    """Exception for retryable HTTP errors."""
    pass


class HttpNonRetryableError(HttpClientError):
    """Exception for non-retryable HTTP errors."""
    pass


class HttpClient:
    """
    Lightweight HTTP client with retry support.
    
    Provides async HTTP operations with configurable retry policies,
    timeout handling, and structured error handling.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
        retry_delay: float = 1.0,
        retry_backoff_factor: float = 2.0,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_policy: Retry policy to use
            retry_delay: Initial delay between retries in seconds
            retry_backoff_factor: Backoff factor for exponential retry
            headers: Default headers to include in all requests
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_policy = retry_policy
        self.retry_delay = retry_delay
        self.retry_backoff_factor = retry_backoff_factor
        self.default_headers = headers or {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.default_headers
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path."""
        if self.base_url:
            return urljoin(self.base_url, path)
        return path

    def _is_retryable_error(self, status_code: int) -> bool:
        """Check if HTTP status code indicates a retryable error."""
        # Retry on server errors (5xx) and some client errors
        retryable_codes = {
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        }
        return status_code in retryable_codes

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt."""
        if self.retry_policy == RetryPolicy.FIXED:
            return self.retry_delay
        elif self.retry_policy == RetryPolicy.LINEAR:
            return self.retry_delay * attempt
        elif self.retry_policy == RetryPolicy.EXPONENTIAL:
            return self.retry_delay * (self.retry_backoff_factor ** (attempt - 1))
        else:
            return self.retry_delay

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            json_data: JSON data to send
            data: Raw data to send
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            HttpClientError: If request fails after all retries
        """
        await self._ensure_session()
        
        full_url = self._build_url(url)
        request_headers = {**self.default_headers, **(headers or {})}
        
        last_exception = None
        
        for attempt in range(1, self.max_retries + 2):  # +1 for initial attempt
            try:
                logger.debug(f"HTTP {method} {full_url} (attempt {attempt})")
                
                async with self._session.request(
                    method=method,
                    url=full_url,
                    headers=request_headers,
                    json=json_data,
                    data=data,
                    params=params
                ) as response:
                    
                    # Read response data
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()
                    
                    # Check if request was successful
                    if response.status < 400:
                        logger.debug(f"HTTP {method} {full_url} succeeded (status: {response.status})")
                        return {
                            "status_code": response.status,
                            "data": response_data,
                            "headers": dict(response.headers)
                        }
                    
                    # Handle error responses
                    error_msg = f"HTTP {method} {full_url} failed with status {response.status}"
                    
                    if self._is_retryable_error(response.status) and attempt <= self.max_retries:
                        logger.warning(f"{error_msg}, retrying (attempt {attempt}/{self.max_retries})")
                        last_exception = HttpRetryableError(error_msg, response.status, response_data)
                    else:
                        logger.error(f"{error_msg}, not retrying")
                        raise HttpNonRetryableError(error_msg, response.status, response_data)
                        
            except aiohttp.ClientError as e:
                error_msg = f"HTTP {method} {full_url} failed with client error: {str(e)}"
                
                if attempt <= self.max_retries:
                    logger.warning(f"{error_msg}, retrying (attempt {attempt}/{self.max_retries})")
                    last_exception = HttpRetryableError(error_msg)
                else:
                    logger.error(f"{error_msg}, not retrying")
                    raise HttpClientError(error_msg) from e
                    
            except Exception as e:
                error_msg = f"HTTP {method} {full_url} failed with unexpected error: {str(e)}"
                logger.error(error_msg)
                raise HttpClientError(error_msg) from e
            
            # Wait before retry (except on last attempt)
            if attempt <= self.max_retries:
                delay = self._calculate_retry_delay(attempt)
                logger.debug(f"Waiting {delay}s before retry")
                await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise HttpClientError(f"HTTP {method} {full_url} failed after {self.max_retries} retries")

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self._make_request("GET", url, headers=headers, params=params)

    async def post(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self._make_request("POST", url, headers=headers, json_data=json_data, data=data)

    async def put(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self._make_request("PUT", url, headers=headers, json_data=json_data, data=data)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self._make_request("DELETE", url, headers=headers)


# Convenience functions for creating pre-configured clients

def create_order_cancellation_client() -> HttpClient:
    """
    Create HTTP client configured for order cancellation service calls.
    
    Returns:
        HttpClient configured with EXPONENTIAL retry policy and 10s timeout
    """
    return HttpClient(
        timeout=10.0,
        max_retries=3,
        retry_policy=RetryPolicy.EXPONENTIAL,
        retry_delay=1.0,
        retry_backoff_factor=2.0,
        headers={"Content-Type": "application/json"}
    )


def create_fixed_retry_client(timeout: float = 5.0) -> HttpClient:
    """
    Create HTTP client configured with FIXED retry policy.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        HttpClient configured with FIXED retry policy
    """
    return HttpClient(
        timeout=timeout,
        max_retries=3,
        retry_policy=RetryPolicy.FIXED,
        retry_delay=1.0,
        headers={"Content-Type": "application/json"}
    )
