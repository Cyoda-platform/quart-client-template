#!/usr/bin/env python3
"""
Test script to create entities for E2E testing
"""

import asyncio
import json
from typing import Optional, Tuple

import httpx


async def create_example_entity() -> Tuple[bool, Optional[str]]:
    """Create an ExampleEntity via the API"""
    url = "http://127.0.0.1:8000/api/example-entities"

    # Entity data that should pass validation criteria
    entity_data = {
        "name": "End-to-End Test Entity",
        "description": "Testing complete workflow execution with processor and criteria",
        "category": "ELECTRONICS",  # Valid category from criteria
        "isActive": True,
    }

    print(f"\n{'='*80}")
    print("Creating ExampleEntity via API")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(entity_data, indent=2)}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=entity_data)

            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}\n")

            if response.status_code in [200, 201]:
                result = response.json()
                entity_id = result.get("entityId") or result.get("entity_id")
                print("✅ Successfully created ExampleEntity")
                print(f"   Entity ID: {entity_id}")
                print(f"   State: {result.get('state', 'unknown')}")
                return True, entity_id
            else:
                print(f"❌ Failed to create entity: {response.status_code}")
                return False, None

        except Exception as e:
            print(f"❌ Error creating entity: {str(e)}")
            return False, None


async def main() -> bool:
    """Main function"""
    print("\n" + "=" * 80)
    print("E2E Test: Creating ExampleEntity")
    print("=" * 80)

    success, entity_id = await create_example_entity()

    if success:
        print(f"\n{'='*80}")
        print("✅ Entity creation successful!")
        print(f"{'='*80}")
        print("\nNext steps:")
        print("1. Check application logs for criteria validation")
        print("2. Check application logs for processor execution")
        print("3. Verify 3 OtherEntity instances were created")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print("❌ Entity creation failed!")
        print(f"{'='*80}\n")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
