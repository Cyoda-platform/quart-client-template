{
  "name": "pet_entity_workflow",
  "description": "Finite state machine for pet entity lifecycle workflow",
  "transitions": [
    {
      "name": "start_processing",
      "description": "Start processing pet entity",
      "start_state": "None",
      "start_state_description": "Initial state",
      "end_state": "Status_set",
      "end_state_description": "Pet status set if missing",
      "automated": true,
      "processes": {
        "schedule_transition_processors": [],
        "externalized_processors": [
          {
            "name": "processSetDefaultStatus",
            "description": "Sets default status if missing or empty"
          }
        ]
      }
    },
    {
      "name": "log_pet_name_async",
      "description": "Asynchronously log pet name",
      "start_state": "Status_set",
      "start_state_description": "Pet status set if missing",
      "end_state": "Name_logged",
      "end_state_description": "Pet name logged asynchronously",
      "automated": true,
      "processes": {
        "schedule_transition_processors": [],
        "externalized_processors": [
          {
            "name": "processAsyncLogName",
            "description": "Logs pet name asynchronously"
          }
        ]
      }
    },
    {
      "name": "additional_async_tasks",
      "description": "Perform additional asynchronous tasks",
      "start_state": "Name_logged",
      "start_state_description": "Pet name logged asynchronously",
      "end_state": "Workflow_completed",
      "end_state_description": "Workflow completed after additional tasks",
      "automated": true,
      "processes": {
        "schedule_transition_processors": [],
        "externalized_processors": [
          {
            "name": "processAdditionalTasks",
            "description": "Placeholder for additional async tasks"
          }
        ]
      }
    }
  ]
}