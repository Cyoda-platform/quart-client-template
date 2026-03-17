#!/usr/bin/env python3
"""
Test script to verify created entities
"""

import asyncio
from typing import Any, List, Tuple

import httpx


async def list_example_entities() -> Tuple[bool, List[Any]]:
    """List all ExampleEntities"""
    url = "http://127.0.0.1:8000/api/example-entities"

    print(f"\n{'='*80}")
    print("Listing ExampleEntities")
    print(f"URL: {url}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                entities = result.get("entities", [])
                total = result.get("total", 0)

                print(f"✅ Found {total} ExampleEntity(ies)")
                for i, entity in enumerate(entities, 1):
                    print(f"\n  Entity {i}:")
                    print(
                        f"    ID: {entity.get('entityId') or entity.get('entity_id')}"
                    )
                    print(f"    Name: {entity.get('name')}")
                    print(f"    Category: {entity.get('category')}")
                    print(f"    State: {entity.get('state')}")

                return True, entities
            else:
                print(f"❌ Failed to list entities: {response.status_code}")
                print(f"Response: {response.text}")
                return False, []

        except Exception as e:
            print(f"❌ Error listing entities: {str(e)}")
            return False, []


async def list_other_entities() -> Tuple[bool, List[Any]]:
    """List all OtherEntities"""
    url = "http://127.0.0.1:8000/api/other-entities"

    print(f"\n{'='*80}")
    print("Listing OtherEntities")
    print(f"URL: {url}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                entities = result.get("entities", [])
                total = result.get("total", 0)

                print(f"✅ Found {total} OtherEntity(ies)")
                for i, entity in enumerate(entities, 1):
                    print(f"\n  Entity {i}:")
                    print(
                        f"    ID: {entity.get('entityId') or entity.get('entity_id')}"
                    )
                    print(f"    Title: {entity.get('title')}")
                    print(f"    Priority: {entity.get('priority')}")
                    print(f"    Source Entity ID: {entity.get('sourceEntityId')}")
                    print(f"    State: {entity.get('state')}")

                return True, entities
            else:
                print(f"❌ Failed to list entities: {response.status_code}")
                print(f"Response: {response.text}")
                return False, []

        except Exception as e:
            print(f"❌ Error listing entities: {str(e)}")
            return False, []


async def main() -> bool:
    """Main function"""
    print("\n" + "=" * 80)
    print("E2E Test: Verifying Created Entities")
    print("=" * 80)

    # List ExampleEntities
    success1, example_entities = await list_example_entities()

    # List OtherEntities
    success2, other_entities = await list_other_entities()

    print(f"\n{'='*80}")
    print("Verification Summary:")
    print(
        f"  ExampleEntities: {'✅ Found' if success1 and len(example_entities) > 0 else '❌ Not found'}"
    )
    print(
        f"  OtherEntities: {'✅ Found' if success2 and len(other_entities) > 0 else '❌ Not found'}"
    )

    if success2 and len(other_entities) >= 3:
        print(f"\n  ✅ Processor created {len(other_entities)} OtherEntity instances")
        print("     Expected: 3 instances")
        print(f"     Actual: {len(other_entities)} instances")

    print(f"{'='*80}\n")

    return success1 and success2


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
