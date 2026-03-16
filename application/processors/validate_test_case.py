"""
Processor: validate_test_case
Purpose: Validate TestCase entities in DRAFT state. Ensures mandatory fields are present:
- title (non-empty)
- at least one step with action and expected

Interface: handle(event, context)
- event: {"test_case_id": "..."} or {"test_case": {...}}

Behavior:
- If validation passes, return {status: 'ok'}
- If validation fails, return {status: 'error', errors: [...]}
- Uses application.clients.data_client.data_client for reads/updates
"""
from typing import Dict, Any, List

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def _validate_steps(steps: List[Dict[str, Any]]) -> List[str]:
    errors = []
    if not steps:
        errors.append("At least one step is required")
        return errors
    for idx, s in enumerate(steps):
        if not s.get("action"):
            errors.append(f"Step {idx+1}: action is required")
        if not s.get("expected"):
            errors.append(f"Step {idx+1}: expected is required")
    return errors


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    tc = event.get("test_case")
    tc_id = event.get("test_case_id")

    if not tc and not tc_id:
        return {"status": "error", "errors": ["test_case or test_case_id is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available"]}

    if not tc:
        tc = data_client.get_test_case(tc_id)
        if not tc:
            return {"status": "error", "errors": [f"TestCase not found: {tc_id}"]}

    errors = []
    title = tc.get("title")
    if not title or not str(title).strip():
        errors.append("Title is required")

    steps = tc.get("steps") or []
    errors.extend(_validate_steps(steps))

    if errors:
        # Optionally persist validation errors on the TestCase entity
        try:
            if tc.get("id"):
                data_client.update_test_case(tc.get("id"), {"validation_errors": errors})
        except Exception:
            pass
        return {"status": "error", "errors": errors}

    # Validation passed; clear any previous validation errors
    try:
        if tc.get("id"):
            data_client.update_test_case(tc.get("id"), {"validation_errors": []})
    except Exception:
        pass

    return {"status": "ok"}
