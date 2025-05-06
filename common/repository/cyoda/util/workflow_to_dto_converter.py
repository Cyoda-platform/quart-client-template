import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

TREE_NODE_ENTITY = "com.cyoda.tdb.model.treenode.TreeNodeEntity"
OPERATION_MAPPING = {
        "equals (disregard case)": {"operation": "IEQUALS", "@bean": "com.cyoda.core.conditions.nonqueryable.IEquals"},
        "not equal (disregard case)": {"operation": "INOT_EQUAL",
                                       "@bean": "com.cyoda.core.conditions.nonqueryable.INotEquals"},
        "between (inclusive)": {"operation": "BETWEEN", "@bean": "com.cyoda.core.conditions.queryable.Between"},
        "contains": {"operation": "CONTAINS", "@bean": "com.cyoda.core.conditions.nonqueryable.IContains"},
        "starts with": {"operation": "ISTARTS_WITH", "@bean": "com.cyoda.core.conditions.nonqueryable.IStartsWith"},
        "ends with": {"operation": "IENDS_WITH", "@bean": "com.cyoda.core.conditions.nonqueryable.IEndsWith"},
        "does not contain": {"operation": "INOT_CONTAINS",
                             "@bean": "com.cyoda.core.conditions.nonqueryable.INotContains"},
        "does not start with": {"operation": "INOT_STARTS_WITH",
                                "@bean": "com.cyoda.core.conditions.nonqueryable.INotStartsWith"},
        "does not end with": {"operation": "NOT_ENDS_WITH",
                              "@bean": "com.cyoda.core.conditions.nonqueryable.NotEndsWith"},
        "matches other field (case insensitive)": {"operation": "INOT_ENDS_WITH",
                                                   "@bean": "com.cyoda.core.conditions.nonqueryable.INotEndsWith"},
        "equals": {"operation": "EQUALS", "@bean": "com.cyoda.core.conditions.queryable.Equals"},
        "not equal": {"operation": "NOT_EQUAL", "@bean": "com.cyoda.core.conditions.nonqueryable.NotEquals"},
        "less than": {"operation": "LESS_THAN", "@bean": "com.cyoda.core.conditions.queryable.LessThan"},
        "greater than": {"operation": "GREATER_THAN", "@bean": "com.cyoda.core.conditions.queryable.GreaterThan"},
        "less than or equal to": {"operation": "LESS_OR_EQUAL",
                                  "@bean": "com.cyoda.core.conditions.queryable.LessThanEquals"},
        "greater than or equal to": {"operation": "GREATER_OR_EQUAL",
                                     "@bean": "com.cyoda.core.conditions.queryable.GreaterThanEquals"},
        "between (inclusive, match case)": {"operation": "BETWEEN_INCLUSIVE",
                                            "@bean": "com.cyoda.core.conditions.queryable.BetweenInclusive"},
        "is null": {"operation": "IS_NULL", "@bean": "com.cyoda.core.conditions.nonqueryable.IsNull"},
        "is not null": {"operation": "NOT_NULL", "@bean": "com.cyoda.core.conditions.nonqueryable.NotNull"}
    }

def _transform_condition(condition):
    """Transforms a condition based on the provided enums mapping."""
    if "conditions" in condition:  # Handle group conditions
        return {
            "@bean": "com.cyoda.core.conditions.GroupCondition",
            "operator": condition.get("group_condition_operator", "AND"),
            "conditions": [_transform_condition(sub_condition) for sub_condition in condition["conditions"]],
        }

    operation_label = condition.get("operation")
    mapping = OPERATION_MAPPING.get(operation_label)

    if not mapping:
        raise ValueError(f"Unsupported operation: {operation_label}")

    is_range = "BETWEEN" in mapping["operation"]
    is_meta_field = condition["is_meta_field"]

    # Determine the appropriate fieldName
    if not is_meta_field:
        field_name_prefix = "members.[*]@com#cyoda#tdb#model#treenode#NodeInfo.value@com#cyoda#tdb#model#treenode#PersistedValueMaps."
        fieldName = f"{field_name_prefix}{condition['value_type']}.[$.{condition['field_name']}]"
    else:
        fieldName = condition["field_name"]

    base_condition = {
        "@bean": mapping["@bean"],
        "fieldName": fieldName,
        "operation": mapping["operation"],
        "rangeField": str(is_range).lower(),
    }

    def _parse_value(value):
        if isinstance(value, bool):
            return value
        try:
            # Try converting to float
            return float(value)
        except (ValueError, TypeError):
            # Leave non-numeric values as-is
            return value

    # Add value if not disabled by "is null" or similar
    if "value" in condition and mapping["operation"] not in {"IS_NULL", "NOT_NULL"}:
        base_condition["value"] = _parse_value(condition["value"])

    # Special handling for "does not start with" operation
    if condition.get("operation").lower() == "does not start with":
        base_condition["iStartsWith"] = {
            "@bean": "com.cyoda.core.conditions.nonqueryable.IStartsWith",
            "fieldName": condition["field_name"],
            "operation": "ISTARTS_WITH",
            "rangeField": "false",
            "value": _parse_value(condition["value"])
        }

    return base_condition


def _transform_conditions(input_conditions):
    """Transforms the entire conditions list."""
    return [_transform_condition(cond) for cond in input_conditions]


def _get_existing_state_id(state_name, dto):
    for state in dto["states"]:
        if state["name"] == state_name:
            return state["id"]
    return None


def _generate_id():
    return str(uuid.uuid1())


def _current_timestamp():
    now = datetime.now(ZoneInfo("UTC"))
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + now.strftime("%z")[:3] + ":" + now.strftime("%z")[3:]


def _generate_ext_criteria_params(criteria):
    criteria_params = [
        {
            "persisted": True,
            "owner": criteria["owner"],
            "id": _generate_id(),
            "name": "Tags for filtering calculation nodes (separated by ',' or ';')",
            "creationDate": _current_timestamp(),
            "valueType": "STRING",
            "value": {
                "@type": "String",
                "value": criteria["calculation_nodes_tags"]
            }
        },
        {
            "persisted": True,
            "owner": criteria["owner"],
            "id": _generate_id(),
            "name": "Attach entity",
            "creationDate": _current_timestamp(),
            "valueType": "STRING",
            "value": {
                "@type": "String",
                "value": str(criteria["attach_entity"]).lower()
            }
        },
        {
            "persisted": True,
            "owner": criteria["owner"],
            "id": _generate_id(),
            "name": "Calculation response timeout (ms)",
            "creationDate": _current_timestamp(),
            "valueType": "INTEGER",
            "value": {"@type": "String", "value": criteria["calculation_response_timeout_ms"]}
        },
        {
            "persisted": True,
            "owner": criteria["owner"],
            "id": _generate_id(),
            "name": "Retry policy",
            "creationDate": _current_timestamp(),
            "valueType": "STRING",
            "value": {"@type": "String", "value": criteria["retry_policy"]}
        }
    ]
    return criteria_params


def _generate_ext_criteria(criteria, criteria_id, criteria_params, class_name):
    criteria_dto = {
        "persisted": True,
        "owner": criteria["owner"],
        "id": criteria_id,
        "name": criteria["name"],
        "entityClassName": class_name,
        "creationDate": _current_timestamp(),
        "description": criteria["description"],
        "condition": {
            "@bean": "com.cyoda.core.conditions.GroupCondition",
            "operator": "AND",
            "conditions": []
        },
        "aliasDefs": [],
        "parameters": criteria_params,
        "criteriaChecker": "ExternalizedCriteriaChecker",
        "user": "CYODA"
    }
    return criteria_dto


def parse_ai_workflow_to_dto(input_workflow, class_name=TREE_NODE_ENTITY):
    dto = {
        "@bean": "com.cyoda.core.model.stateMachine.dto.FullWorkflowContainerDto",
        "workflow": [],
        "transitions": [],
        "criterias": [],
        "processes": [],
        "states": [],
        "processParams": []
    }

    # Map workflow
    workflow_id = _generate_id()
    dto["workflow"].append({
        "persisted": True,
        "owner": "CYODA",
        "id": workflow_id,
        "name": input_workflow["name"],
        "entityClassName": class_name,
        "creationDate": _current_timestamp(),
        "description": input_workflow.get("description", ""),
        "entityShortClassName": "TreeNodeEntity",
        "transitionIds": [],
        "criteriaIds": [],
        "stateIds": ["noneState"],
        "active": False,
        "useDecisionTree": False,
        "decisionTrees": [],
        "metaData": {"documentLink": ""}
    })

    # Process workflow's externalized_criteria
    workflow_criteria_ids = []

    for criteria in input_workflow["workflow_criteria"]["externalized_criteria"]:
        criteria_id = _generate_id()
        workflow_criteria_ids.append(criteria_id)
        criteria_params = _generate_ext_criteria_params(criteria)
        dto["processParams"].extend(criteria_params)
        criteria_dto = _generate_ext_criteria(criteria, criteria_id, criteria_params, class_name)
        dto["criterias"].append(criteria_dto)

    # Process workflow's condition_criteria
    for criteria in input_workflow["workflow_criteria"]["condition_criteria"]:
        criteria_id = _generate_id()
        workflow_criteria_ids.append(criteria_id)
        dto["criterias"].append({
            "persisted": True,
            "owner": "CYODA",
            "id": criteria_id,
            "name": criteria["name"],
            "entityClassName": class_name,
            "creationDate": _current_timestamp(),
            "description": criteria["description"],
            "condition": {
                "@bean": "com.cyoda.core.conditions.GroupCondition",
                "operator": criteria["condition"]["group_condition_operator"],
                "conditions": _transform_conditions(criteria["condition"]["conditions"])
            },
            "aliasDefs": [],
            "parameters": [],
            "criteriaChecker": "ConditionCriteriaChecker",
            "user": "CYODA"
        })

    dto["workflow"][0]["criteriaIds"].extend(workflow_criteria_ids)

    # Process transitions
    for transition in input_workflow["transitions"]:
        transition_id = _generate_id()
        process_ids = []
        criteria_ids = []

        # Process transition's externalized_criteria
        for criteria in transition["transition_criteria"]["externalized_criteria"]:
            criteria_id = _generate_id()
            criteria_ids.append(criteria_id)
            criteria_params = _generate_ext_criteria_params(criteria)
            dto["processParams"].extend(criteria_params)
            criteria_dto = _generate_ext_criteria(criteria, criteria_id, criteria_params, class_name)
            dto["criterias"].append(criteria_dto)

        # Process transition's condition_criteria
        for criteria in transition["transition_criteria"]["condition_criteria"]:
            criteria_id = _generate_id()
            criteria_ids.append(criteria_id)
            dto["criterias"].append({
                "persisted": True,
                "owner": "CYODA",
                "id": criteria_id,
                "name": criteria["name"],
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": criteria["description"],
                "condition": {
                    "@bean": "com.cyoda.core.conditions.GroupCondition",
                    "operator": criteria["condition"]["group_condition_operator"],
                    "conditions": _transform_conditions(criteria["condition"]["conditions"])
                },
                "aliasDefs": [],
                "parameters": [],
                "criteriaChecker": "ConditionCriteriaChecker",
                "user": "CYODA"
            })

        # Process externalized_processor
        for process in transition.get("processes", {}).get("externalized_processors", []):
            process_id = _generate_id()
            process_ids.append(
                {
                    "persisted": True,
                    "persistedId": process_id,
                    "runtimeId": 0
                }
            )

            process_params = [
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Tags for filtering calculation nodes (separated by ',' or ';')",
                    "creationDate": _current_timestamp(),
                    "valueType": "STRING",
                    "value": {
                        "@type": "String",
                        "value": process["calculation_nodes_tags"]
                    }
                },
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Attach entity",
                    "creationDate": _current_timestamp(),
                    "valueType": "STRING",
                    "value": {
                        "@type": "String",
                        "value": str(process["attach_entity"]).lower()
                    }
                },
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Calculation response timeout (ms)",
                    "creationDate": _current_timestamp(),
                    "valueType": "INTEGER",
                    "value": {"@type": "String", "value": str(process["calculation_response_timeout_ms"])}
                },
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Retry policy",
                    "creationDate": _current_timestamp(),
                    "valueType": "STRING",
                    "value": {"@type": "String", "value": process["retry_policy"]}
                }
            ]

            dto["processParams"].extend(process_params)

            # Process externalized_processor's externalized_criteria
            process_criteria_ids = []

            for criteria in process["processor_criteria"]["externalized_criteria"]:
                criteria_id = _generate_id()
                process_criteria_ids.append(criteria_id)
                criteria_params = _generate_ext_criteria_params(criteria)
                dto["processParams"].extend(criteria_params)
                criteria_dto = _generate_ext_criteria(criteria, criteria_id, criteria_params, class_name)
                dto["criterias"].append(criteria_dto)

            # Process externalized_processor's condition_criteria
            for criteria in process["processor_criteria"]["condition_criteria"]:
                criteria_id = _generate_id()
                process_criteria_ids.append(criteria_id)
                dto["criterias"].append({
                    "persisted": True,
                    "owner": "CYODA",
                    "id": criteria_id,
                    "name": criteria["name"],
                    "entityClassName": class_name,
                    "creationDate": _current_timestamp(),
                    "description": criteria["description"],
                    "condition": {
                        "@bean": "com.cyoda.core.conditions.GroupCondition",
                        "operator": criteria["condition"]["group_condition_operator"],
                        "conditions": _transform_conditions(criteria["condition"]["conditions"])
                    },
                    "aliasDefs": [],
                    "parameters": [],
                    "criteriaChecker": "ConditionCriteriaChecker",
                    "user": "CYODA"
                })

            # Process externalized_processor's dto
            dto["processes"].append({
                "persisted": True,
                "owner": "CYODA",
                "id": {
                    "@bean": "com.cyoda.core.model.stateMachine.dto.ProcessIdDto",
                    "persisted": True,
                    "persistedId": process_id,
                    "runtimeId": 0
                },
                "name": process["name"],
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": process["description"],
                "processorClassName": "net.cyoda.saas.externalize.processor.ExternalizedProcessor",
                "parameters": process_params,
                "fields": [],
                "syncProcess": process["sync_process"],
                "newTransactionForAsync": process["new_transaction_for_async"],
                "noneTransactionalForAsync": process["none_transactional_for_async"],
                "isTemplate": False,
                "criteriaIds": process_criteria_ids,
                "user": "CYODA"
            })

        # Process schedule_transition_processor
        for process in transition["processes"]["schedule_transition_processors"]:
            process_id = _generate_id()
            process_ids.append(
                {
                    "persisted": True,
                    "persistedId": process_id,
                    "runtimeId": 0
                }
            )

            process_params = [
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Delay (ms)",
                    "creationDate": _current_timestamp(),
                    "valueType": "INTEGER",
                    "value": {
                        "@type": "String",
                        "value": str(process["delay_ms"])
                    }
                },
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Timeout (ms)",
                    "creationDate": _current_timestamp(),
                    "valueType": "INTEGER",
                    "value": {
                        "@type": "String",
                        "value": str(process["timeout_ms"])
                    }
                },
                {
                    "persisted": True,
                    "owner": "CYODA",
                    "id": _generate_id(),
                    "name": "Transition name",
                    "creationDate": _current_timestamp(),
                    "valueType": "STRING",
                    "value": {"@type": "String", "value": process["transition_name"]}
                }
            ]

            dto["processParams"].extend(process_params)

            # Process schedule_transition_processor's externalized_criteria
            process_criteria_ids = []

            for criteria in process["processor_criteria"]["externalized_criteria"]:
                criteria_id = _generate_id()
                process_criteria_ids.append(criteria_id)
                criteria_params = _generate_ext_criteria_params(criteria)
                dto["processParams"].extend(criteria_params)
                criteria_dto = _generate_ext_criteria(criteria, criteria_id, criteria_params, class_name)
                dto["criterias"].append(criteria_dto)

            # Process schedule_transition_processor's condition_criteria
            for criteria in process["processor_criteria"]["condition_criteria"]:
                criteria_id = _generate_id()
                process_criteria_ids.append(criteria_id)
                dto["criterias"].append({
                    "persisted": True,
                    "owner": "CYODA",
                    "id": criteria_id,
                    "name": criteria["name"],
                    "entityClassName": class_name,
                    "creationDate": _current_timestamp(),
                    "description": criteria["description"],
                    "condition": {
                        "@bean": "com.cyoda.core.conditions.GroupCondition",
                        "operator": criteria["condition"]["group_condition_operator"],
                        "conditions": _transform_conditions(criteria["condition"]["conditions"])
                    },
                    "aliasDefs": [],
                    "parameters": [],
                    "criteriaChecker": "ConditionCriteriaChecker",
                    "user": "CYODA"
                })

            # Process schedule_transition_processor's dto
            dto["processes"].append({
                "persisted": True,
                "owner": "CYODA",
                "id": {
                    "@bean": "com.cyoda.core.model.stateMachine.dto.ProcessIdDto",
                    "persisted": True,
                    "persistedId": process_id,
                    "runtimeId": 0
                },
                "name": process["name"],
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": process["description"],
                "processorClassName": "com.cyoda.plugins.cobi.processors.statemachine.ScheduleTransitionProcessor",
                "parameters": process_params,
                "fields": [],
                "syncProcess": process["sync_process"],
                "newTransactionForAsync": process["new_transaction_for_async"],
                "noneTransactionalForAsync": process["none_transactional_for_async"],
                "isTemplate": False,
                "criteriaIds": process_criteria_ids,
                "user": "CYODA"
            })

        # Process states
        start_state_id = "noneState"
        end_state_id = ""

        # Create a list to hold the new states
        new_states = []

        # Add start_state only if it is not "None"
        if transition["start_state"] != "None":
            start_state_id = _get_existing_state_id(transition["start_state"], dto)

            if not start_state_id:
                start_state_id = _generate_id()
                new_states.append({
                    "persisted": True,
                    "owner": "CYODA",
                    "id": start_state_id,
                    "name": transition["start_state"],
                    "entityClassName": class_name,
                    "creationDate": _current_timestamp(),
                    "description": transition["start_state_description"]
                })
        # Add "None" state
        else:
            new_states.append({
                "persisted": True,
                "owner": "CYODA",
                "id": start_state_id,
                "name": "None",
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": "Initial state of the workflow."
            })

        # Add end_state
        end_state_id = _get_existing_state_id(transition["end_state"], dto)
        if not end_state_id:
            end_state_id = _generate_id()
            new_states.append({
                "persisted": True,
                "owner": "CYODA",
                "id": end_state_id,
                "name": transition["end_state"],
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": transition["end_state_description"]
            })

        # Extend the dto["states"] with the new states
        dto["states"].extend(new_states)

        # Process transitions
        dto["transitions"].append({
            "persisted": True,
            "owner": "CYODA",
            "id": transition_id,
            "name": transition["name"],
            "entityClassName": class_name,
            "creationDate": _current_timestamp(),
            "description": transition["description"],
            "startStateId": start_state_id,
            "endStateId": end_state_id,
            "workflowId": workflow_id,
            "criteriaIds": criteria_ids,
            "endProcessesIds": process_ids,
            "active": True,
            "automated": transition["automated"],
            "logActivity": False
        })

        dto["workflow"][0]["transitionIds"].append(transition_id)

    _add_none_state_if_not_exists(dto, class_name)
    return dto


def _add_none_state_if_not_exists(dto, class_name):
    # State "None" is mandatory for the workflow. It is added, if missing in the DTO.
    none_state_exists = any(str(state["name"]).lower() == "none" for state in dto["states"])

    if not none_state_exists:
        none_state = {
            "persisted": True,
            "owner": "CYODA",
            "id": "noneState",
            "name": "None",
            "entityClassName": class_name,
            "creationDate": _current_timestamp(),
            "description": "Initial state of the workflow."
        }
        dto["states"].append(none_state)

        # Find the current first state
        end_state_ids = {transition["endStateId"] for transition in dto["transitions"]}
        first_state_id = None
        for transition in dto["transitions"]:
            if transition["startStateId"] not in end_state_ids:
                first_state_id = transition["startStateId"]
                break
        if first_state_id:
            # Add new transition connecting noneState with current first state
            new_transition = {
                "persisted": True,
                "owner": "CYODA",
                "id": _generate_id(),
                "name": "initial_transition",
                "entityClassName": class_name,
                "creationDate": _current_timestamp(),
                "description": "Initial transition from None state.",
                "startStateId": "noneState",
                "endStateId": first_state_id,
                "workflowId": dto["workflow"][0]["id"],
                "criteriaIds": [],
                "endProcessesIds": [],
                "active": True,
                "automated": True,
                "logActivity": False
            }
            dto["transitions"].append(new_transition)
            dto["workflow"][0]["transitionIds"].append(new_transition["id"])
