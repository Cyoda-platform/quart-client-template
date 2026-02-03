import json
from pathlib import Path
from typing import List


def validate_workflow(workflow_path: str) -> List[str]:
    """Basic validation of workflow against schema requirements"""
    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    errors = []

    # Check required fields
    required_fields = ["version", "name", "initialState", "states"]
    for field in required_fields:
        if field not in workflow:
            errors.append(f"Missing required field: {field}")

    # Check initialState value
    if workflow.get("initialState") != "initial_state":
        errors.append(
            f"initialState must be 'initial_state', got '{workflow.get('initialState')}'"
        )

    # Check states structure
    if "states" in workflow:
        states = workflow["states"]
        if "initial_state" not in states:
            errors.append("Missing 'initial_state' in states")

        for state_name, state_config in states.items():
            if "transitions" not in state_config:
                errors.append(f"State '{state_name}' missing 'transitions' field")
            else:
                for transition in state_config["transitions"]:
                    if "name" not in transition:
                        errors.append(
                            f"Transition in state '{state_name}' missing 'name'"
                        )
                    if "next" not in transition:
                        errors.append(
                            f"Transition in state '{state_name}' missing 'next'"
                        )
                    if "manual" not in transition:
                        errors.append(
                            f"Transition in state '{state_name}' missing 'manual'"
                        )

                    # Check processors if present
                    if "processors" in transition:
                        for processor in transition["processors"]:
                            if "name" not in processor:
                                errors.append("Processor missing 'name'")
                            if "executionMode" not in processor:
                                errors.append("Processor missing 'executionMode'")
                            mode = processor.get("executionMode")
                            if mode not in ["SYNC", "ASYNC_NEW_TX", "ASYNC_SAME_TX"]:
                                errors.append(f"Invalid executionMode: {mode}")
                            if "config" not in processor:
                                errors.append("Processor missing 'config'")
                            elif "calculationNodesTags" not in processor["config"]:
                                errors.append(
                                    "Processor config missing 'calculationNodesTags'"
                                )

    return errors


workflow_dir = Path(
    "/tmp/cyoda_builds/0b194e7b-dae1-48df-be6c-f1b2379dadf5/application/resources/workflow"
)

workflows = [
    workflow_dir / "orderlifecycle/version_1/OrderLifecycle.json",
    workflow_dir / "pretraderiskcheck/version_1/PreTradeRiskCheck.json",
    workflow_dir / "tradesettlement/version_1/TradeSettlement.json",
]

all_valid = True
for workflow_path in workflows:
    if not workflow_path.exists():
        print(f"❌ {workflow_path.name}: File not found")
        all_valid = False
        continue

    errors = validate_workflow(str(workflow_path))
    if errors:
        print(f"❌ {workflow_path.name}:")
        for error in errors:
            print(f"   - {error}")
        all_valid = False
    else:
        print(f"✅ {workflow_path.name}: Valid")

if all_valid:
    print("\n✅ All workflows are valid!")
else:
    print("\n❌ Some workflows have validation errors")
