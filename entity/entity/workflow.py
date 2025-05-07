import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

EXTERNAL_API_URL = "https://api.agify.io"  # Mock external data source

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def process_add_created_at(entity: dict):
    entity_data = entity.get("data", {})
    entity_data["created_at"] = now_iso()
    entity["data"] = entity_data

async def process_initialize_workflow(entity: dict):
    if "workflow_status" not in entity:
        entity["workflow_status"] = "created"
    if "current_state" not in entity and "workflow" in entity:
        states = entity["workflow"].get("states", [])
        if states:
            entity["current_state"] = states[0]

async def process_handle_event(entity: dict, event_name: str, event_data: dict):
    workflow = entity.get("workflow", {})
    current_state = entity.get("current_state")
    transitions = workflow.get("transitions", [])
    transition = next(
        (
            t
            for t in transitions
            if t["from"] == current_state and t["event"] == event_name
        ),
        None,
    )
    if not transition:
        new_state = current_state
    else:
        new_state = transition["to"]
    results = await query_external_data(event_data)
    entity["current_state"] = new_state
    entity["data"].update(event_data)
    entity["data"].update(results)
    entity["workflow_status"] = "updated"
    history_entry = {
        "timestamp": now_iso(),
        "event": event_name,
        "from_state": current_state,
        "to_state": new_state,
        "metadata": {"event_data": event_data, "external_results": results},
    }
    entity_histories.setdefault(entity["entity_id"], []).append(history_entry)

async def query_external_data(event_data: dict) -> dict:
    name = event_data.get("name")
    if not name:
        return {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, params={"name": name})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logging.getLogger(__name__).exception(f"External API request failed: {e}")
            return {}