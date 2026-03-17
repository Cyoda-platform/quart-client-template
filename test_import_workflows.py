#!/usr/bin/env python3
"""
Test script to import workflows for E2E testing
"""

import asyncio
import json
from pathlib import Path

from services.config import get_service_config
from services.services import get_workflow_management_service, initialize_services


async def import_workflow(entity_name: str, model_version: str, file_path: str) -> bool:
    """Import a workflow from file"""
    print(f"\n{'='*80}")
    print(f"Importing workflow for {entity_name} version {model_version}")
    print(f"File: {file_path}")
    print(f"{'='*80}")

    # Read workflow file
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"❌ Error: File not found: {full_path}")
        return False

    with open(full_path, "r") as f:
        workflow_data = json.load(f)
        workflows = (
            [workflow_data] if isinstance(workflow_data, dict) else workflow_data
        )

    print(f"✓ Loaded {len(workflows)} workflow(s) from file")

    # Import to Cyoda
    workflow_service = get_workflow_management_service()
    result = await workflow_service.import_entity_workflows(
        entity_name=entity_name,
        model_version=model_version,
        workflows=workflows,
        import_mode="REPLACE",
    )

    if result.get("success"):
        print(f"✅ Successfully imported workflow for {entity_name}")
        return True
    else:
        print(f"❌ Failed to import workflow: {result.get('error', 'Unknown error')}")
        return False


async def main() -> bool:
    """Main function"""
    print("Initializing services...")
    config = get_service_config()
    initialize_services(config)
    print("✓ Services initialized\n")

    # Import ExampleEntity workflow
    success1 = await import_workflow(
        entity_name="ExampleEntity",
        model_version="1",
        file_path="example_application/resources/workflow/example_entity/version_1/ExampleEntity.json",
    )

    # Import OtherEntity workflow
    success2 = await import_workflow(
        entity_name="OtherEntity",
        model_version="1",
        file_path="example_application/resources/workflow/other_entity/version_1/OtherEntity.json",
    )

    print(f"\n{'='*80}")
    print("Import Summary:")
    print(f"  ExampleEntity: {'✅ Success' if success1 else '❌ Failed'}")
    print(f"  OtherEntity: {'✅ Success' if success2 else '❌ Failed'}")
    print(f"{'='*80}\n")

    return success1 and success2


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
