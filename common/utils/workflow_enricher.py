import json
import copy

# Default values for the missing attributes
default_workflow_criteria = {
    "externalized_criteria": [],
    "condition_criteria": [
        {
            "name": "ENTITY_MODEL_VAR:ENTITY_VERSION_VAR:CHAT_ID_VAR",
            "description": "Workflow criteria",
            "condition": {
                "group_condition_operator": "AND",
                "conditions": [
                    {
                        "field_name": "entityModelName",
                        "is_meta_field": True,
                        "operation": "equals",
                        "value": "ENTITY_MODEL_VAR",
                        "value_type": "strings"
                    },
                    {
                        "field_name": "entityModelVersion",
                        "is_meta_field": True,
                        "operation": "equals",
                        "value": "ENTITY_VERSION_VAR",
                        "value_type": "strings"
                    }
                ]
            }
        }
    ]
}

default_transition_criteria = {
    "externalized_criteria": [],
    "condition_criteria": []
}

default_processor_criteria = {
    "externalized_criteria": [],
    "condition_criteria": []
}

default_externalized_processor_defaults = {
    # Only add these keys if missing in the processor
    "calculation_nodes_tags": "CHAT_ID_VAR",
    "attach_entity": True,
    "calculation_response_timeout_ms": "120000",
    "retry_policy": "NONE",
    "sync_process": False,
    "new_transaction_for_async": True,
    "none_transactional_for_async": False,
    "processor_criteria": copy.deepcopy(default_processor_criteria)
}


def enrich_workflow(workflow):
    # Add workflow_criteria if missing
    if "workflow_criteria" not in workflow:
        workflow["workflow_criteria"] = copy.deepcopy(default_workflow_criteria)

    # Process each transition in the workflow
    for transition in workflow.get("transitions", []):
        # Add transition_criteria if missing
        if "transition_criteria" not in transition:
            transition["transition_criteria"] = copy.deepcopy(default_transition_criteria)

        # Ensure the processes key exists and add schedule_transition_processors if missing
        processes = transition.get("processes", {})
        if "schedule_transition_processors" not in processes:
            processes["schedule_transition_processors"] = []

        # For each externalized processor, add missing attributes
        if "externalized_processors" in processes:
            for processor in processes["externalized_processors"]:
                # If the processor doesn't have a "name", you might want to set it to an empty string (or leave it)
                processor.setdefault("name", "")
                # Set a default description if not provided
                processor.setdefault("description", "External processor to create a job")

                # Loop over each default attribute and add if missing
                for key, default_value in default_externalized_processor_defaults.items():
                    if key not in processor:
                        processor[key] = copy.deepcopy(default_value)
                    elif key == "processor_criteria":
                        # Ensure nested keys exist in processor_criteria
                        processor["processor_criteria"].setdefault("externalized_criteria", [])
                        processor["processor_criteria"].setdefault("condition_criteria", [])

        # Update the processes back into the transition (if modified)
        transition["processes"] = processes

    workflow['name'] = f"{workflow['name']}:ENTITY_MODEL_VAR:ENTITY_VERSION_VAR:CHAT_ID_VAR"

    return workflow


# Example "not complete" JSON
not_complete_json = {
    "name": "company_job_processing_workflow",
    "description": "A workflow that processes company data through various steps including validation, fetching data, filtering, enriching, and finalizing the job.",
    "transitions": [
        {
            "name": "validate_input",
            "description": "Validate input data",
            "start_state": "None",
            "start_state_description": "Initial state",
            "end_state": "Input_validated",
            "end_state_description": "The input data has been validated",
            "automated": True,
            "processes": {
                "externalized_processors": [
                    {
                        "name": "process_validate_input",
                        "description": "Validates the input data before processing further"
                    }
                ]
            }
        },
        {
            "name": "fetch_company_data",
            "description": "Fetch company data from the API",
            "start_state": "Input_validated",
            "start_state_description": "The input data has been validated",
            "end_state": "Company_data_fetched",
            "end_state_description": "Company data has been successfully fetched",
            "automated": True,
            "processes": {
                "externalized_processors": [
                    {
                        "name": "process_fetch_company_data",
                        "description": "Fetches company data from an external API"
                    }
                ]
            }
        },
        {
            "name": "error_handling",
            "description": "Handle errors during any step of the process",
            "start_state": "None",
            "start_state_description": "Initial state",
            "end_state": "Job_failed",
            "end_state_description": "The job has failed due to an error",
            "automated": True,
            "processes": {
                "externalized_processors": [
                    {
                        "name": "process_error_handling",
                        "description": "Handles errors and sets the job status to failed"
                    }
                ]
            }
        }
    ]
}


if __name__ == "__main__":
    # Update the not complete JSON
    updated_workflow = enrich_workflow(not_complete_json)
    updated_workflow['name'] = f"{updated_workflow['name']}:ENTITY_MODEL_VAR:ENTITY_VERSION_VAR:CHAT_ID_VAR"
    # Print the updated workflow as a pretty-formatted JSON
    print(json.dumps(updated_workflow, indent=4))