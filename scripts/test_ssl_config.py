#!/usr/bin/env python3
"""
ABOUTME: Test script to verify SSL configuration for Cyoda connections.
ABOUTME: This script tests both HTTP and OAuth client SSL settings.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config.config import CYODA_VERIFY_SSL, CYODA_HOST, CYODA_TOKEN_URL
from common.utils.utils import create_http_client
from common.auth.cyoda_auth import CyodaAuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_http_client_ssl():
    """Test HTTP client SSL configuration."""
    logger.info("Testing HTTP client SSL configuration...")
    logger.info(f"CYODA_VERIFY_SSL: {CYODA_VERIFY_SSL}")
    logger.info(f"CYODA_HOST: {CYODA_HOST}")
    
    try:
        async with create_http_client(timeout=10.0) as client:
            # Test a simple connection to the Cyoda host
            test_url = f"https://{CYODA_HOST}"
            logger.info(f"Testing connection to: {test_url}")
            
            response = await client.get(test_url)
            logger.info(f"Connection successful! Status: {response.status_code}")
            return True
            
    except Exception as e:
        logger.error(f"HTTP client test failed: {e}")
        return False


async def test_oauth_client_ssl():
    """Test OAuth client SSL configuration."""
    logger.info("Testing OAuth client SSL configuration...")
    
    # Check if credentials are available
    client_id = os.getenv("CYODA_CLIENT_ID")
    client_secret = os.getenv("CYODA_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.warning("OAuth credentials not available, skipping OAuth test")
        return True
    
    try:
        auth_service = CyodaAuthService(
            client_id=client_id,
            client_secret=client_secret,
            token_url=CYODA_TOKEN_URL,
            scope="read write"
        )
        
        logger.info(f"Testing OAuth token fetch from: {CYODA_TOKEN_URL}")
        token = await auth_service.get_access_token()
        
        if token:
            logger.info("OAuth token fetch successful!")
            return True
        else:
            logger.error("OAuth token fetch returned empty token")
            return False
            
    except Exception as e:
        logger.error(f"OAuth client test failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("Starting SSL configuration tests...")
    logger.info("=" * 50)
    
    # Test HTTP client
    http_success = await test_http_client_ssl()
    logger.info("=" * 50)
    
    # Test OAuth client
    oauth_success = await test_oauth_client_ssl()
    logger.info("=" * 50)
    
    # Summary
    logger.info("Test Results:")
    logger.info(f"  HTTP Client: {'✓ PASS' if http_success else '✗ FAIL'}")
    logger.info(f"  OAuth Client: {'✓ PASS' if oauth_success else '✗ FAIL'}")
    
    if http_success and oauth_success:
        logger.info("All SSL configuration tests passed!")
        return 0
    else:
        logger.error("Some SSL configuration tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
