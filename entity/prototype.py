from dataclasses import dataclass
from typing import Dict, Any, List
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches
users_cache: Dict[str, Dict[str, Any]] = {}
workflows_cache: Dict[str, Dict[str, Any]] = {}
budgets_cache: Dict[str, Dict[str, Any]] = {}
requisitions_cache: Dict[str, Dict[str, Any]] = {}
payments_cache: Dict[str, Dict[str, Any]] = {}
reports_cache: Dict[str, Dict[str, Any]] = {}

AI_MODEL_API = "https://api.mockforecast.ai/forecast"  # TODO: replace with real AI forecasting API

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

@dataclass
class CreateUserRequest:
    username: str
    email: str
    role: str
    department: str
    delegateTo: str = None

@dataclass
class UpdateUserRolesRequest:
    role: str
    permissions: Dict[str, List[str]]

@dataclass
class TriggerWorkflowRequest:
    entityType: str
    entityId: str
    event: str
    payload: Dict[str, Any] = None

@dataclass
class BudgetForecastRequest:
    entityId: str
    budgetVersion: str
    period: str
    budgetData: Dict[str, float]
    forecastOptions: Dict[str, Any]

@dataclass
class SubmitRequisitionRequest:
    requestorId: str
    items: List[Dict[str, Any]]
    budgetVersion: str

@dataclass
class SubmitPaymentRequest:
    vendorId: str
    amount: float
    dueDate: str
    currency: str
    paymentMethod: str

@dataclass
class GenerateReportRequest:
    reportType: str
    filters: Dict[str, Any]
    format: str

@app.route('/api/users/create', methods=['POST'])
# workaround: validate_request must come after route for POST due to quart-schema defect
@validate_request(CreateUserRequest)
async def create_user(data: CreateUserRequest):
    user_id = str(uuid.uuid4())
    users_cache[user_id] = {
        "userId": user_id,
        "username": data.username,
        "email": data.email,
        "role": data.role,
        "department": data.department,
        "delegation": data.delegateTo,
    }
    logger.info(f"User created: {user_id}")
    return jsonify({"userId": user_id, "status": "created"}), 201

@app.route('/api/users/<user_id>', methods=['GET'])
async def get_user(user_id):
    user = users_cache.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)

@app.route('/api/users/<user_id>/updateRoles', methods=['POST'])
@validate_request(UpdateUserRolesRequest)  # workaround: POST validation last
async def update_user_roles(user_id: str, data: UpdateUserRolesRequest):
    user = users_cache.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user["role"] = data.role
    user["permissions"] = data.permissions
    logger.info(f"User roles updated: {user_id}")
    return jsonify({"status": "updated"})

@app.route('/api/workflows/trigger', methods=['POST'])
@validate_request(TriggerWorkflowRequest)
async def trigger_workflow(data: TriggerWorkflowRequest):
    workflow_id = str(uuid.uuid4())
    workflows_cache[workflow_id] = {
        "workflowId": workflow_id,
        "entityType": data.entityType,
        "entityId": data.entityId,
        "event": data.event,
        "state": "started",
        "currentTask": "initial",
        "history": [],
        "payload": data.payload or {},
        "startedAt": now_iso(),
    }
    logger.info(f"Workflow triggered: {workflow_id}")

    async def process_workflow(wf_id: str):
        try:
            await asyncio.sleep(1)
            wf = workflows_cache.get(wf_id)
            if not wf:
                return
            wf["state"] = "completed"
            wf["currentTask"] = None
            wf["history"].append({
                "task": "initial",
                "user": "system",
                "timestamp": now_iso(),
                "action": "completed"
            })
            logger.info(f"Workflow {wf_id} completed")
        except Exception as e:
            logger.exception(e)

    asyncio.create_task(process_workflow(workflow_id))
    return jsonify({"workflowId": workflow_id, "status": "started"}), 202

@app.route('/api/workflows/<workflow_id>/status', methods=['GET'])
async def get_workflow_status(workflow_id):
    wf = workflows_cache.get(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    return jsonify({
        "workflowId": wf["workflowId"],
        "state": wf["state"],
        "currentTask": wf["currentTask"],
        "history": wf["history"],
    })

@app.route('/api/budgeting/forecast', methods=['POST'])
@validate_request(BudgetForecastRequest)
async def budget_forecast(data: BudgetForecastRequest):
    forecast_id = str(uuid.uuid4())
    budgets_cache[forecast_id] = {
        "forecastId": forecast_id,
        "entityId": data.entityId,
        "budgetVersion": data.budgetVersion,
        "period": data.period,
        "status": "processing",
        "results": None,
        "requestedAt": now_iso(),
    }
    logger.info(f"Budget forecast requested: {forecast_id}")

    async def process_forecast(fid: str):
        try:
            results = {}
            if data.forecastOptions.get("useAIModel"):
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(AI_MODEL_API, json={"budget": data.budgetData})
                    if resp.status_code == 200:
                        results = resp.json().get("forecastResults", {})
                    else:
                        logger.warning(f"AI model responded with {resp.status_code}")
            else:
                results = {dep: {"forecasted": val, "variance": 0} for dep, val in data.budgetData.items()}

            budgets_cache[fid]["status"] = "completed"
            budgets_cache[fid]["results"] = results
            logger.info(f"Forecast completed: {fid}")
        except Exception as e:
            budgets_cache[fid]["status"] = "error"
            logger.exception(e)

    asyncio.create_task(process_forecast(forecast_id))
    return jsonify({"forecastId": forecast_id, "status": "processing"}), 202

@app.route('/api/budgeting/<entity_id>/versions', methods=['GET'])
async def get_budget_versions(entity_id):
    versions = [
        {"version": "v1", "createdDate": "2023-01-01T00:00:00Z", "status": "approved"},
        {"version": "v2", "createdDate": "2023-06-01T00:00:00Z", "status": "draft"},
    ]
    return jsonify(versions)

@app.route('/api/procurement/requisition', methods=['POST'])
@validate_request(SubmitRequisitionRequest)
async def submit_requisition(data: SubmitRequisitionRequest):
    req_id = str(uuid.uuid4())
    requisitions_cache[req_id] = {
        "requisitionId": req_id,
        "requestorId": data.requestorId,
        "items": data.items,
        "budgetVersion": data.budgetVersion,
        "status": "submitted",
        "approvalHistory": [],
        "submittedAt": now_iso(),
    }
    logger.info(f"Requisition submitted: {req_id}")
    return jsonify({"requisitionId": req_id, "status": "submitted"}), 201

@app.route('/api/procurement/requisition/<req_id>', methods=['GET'])
async def get_requisition_status(req_id):
    req = requisitions_cache.get(req_id)
    if not req:
        return jsonify({"error": "Requisition not found"}), 404
    return jsonify({
        "requisitionId": req["requisitionId"],
        "status": req["status"],
        "approvalHistory": req["approvalHistory"],
    })

@app.route('/api/payments/request', methods=['POST'])
@validate_request(SubmitPaymentRequest)
async def submit_payment_request(data: SubmitPaymentRequest):
    payment_id = str(uuid.uuid4())
    payments_cache[payment_id] = {
        "paymentId": payment_id,
        "vendorId": data.vendorId,
        "amount": data.amount,
        "dueDate": data.dueDate,
        "currency": data.currency,
        "paymentMethod": data.paymentMethod,
        "status": "queued",
        "requestedAt": now_iso(),
    }
    logger.info(f"Payment request queued: {payment_id}")

    async def process_payment(pid: str):
        try:
            await asyncio.sleep(2)
            payments_cache[pid]["status"] = "processed"
            payments_cache[pid]["processedDate"] = now_iso()
            logger.info(f"Payment processed: {pid}")
        except Exception as e:
            payments_cache[pid]["status"] = "error"
            logger.exception(e)

    asyncio.create_task(process_payment(payment_id))
    return jsonify({"paymentId": payment_id, "status": "queued"}), 202

@app.route('/api/payments/<payment_id>', methods=['GET'])
async def get_payment_status(payment_id):
    payment = payments_cache.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify(payment)

@app.route('/api/reports/generate', methods=['POST'])
@validate_request(GenerateReportRequest)
async def generate_report(data: GenerateReportRequest):
    report_id = str(uuid.uuid4())
    reports_cache[report_id] = {
        "reportId": report_id,
        "reportType": data.reportType,
        "filters": data.filters,
        "format": data.format,
        "status": "processing",
        "createdDate": now_iso(),
        "downloadUrl": None,
    }
    logger.info(f"Report generation started: {report_id}")

    async def process_report(rid: str):
        try:
            await asyncio.sleep(1)
            reports_cache[rid]["status"] = "ready"
            reports_cache[rid]["downloadUrl"] = f"https://mockreports.example.com/download/{rid}"
            logger.info(f"Report ready: {rid}")
        except Exception as e:
            reports_cache[rid]["status"] = "error"
            logger.exception(e)

    asyncio.create_task(process_report(report_id))
    return jsonify({"reportId": report_id, "status": "processing"}), 202

@app.route('/api/reports/<report_id>', methods=['GET'])
async def get_report_metadata(report_id):
    report = reports_cache.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)