from dataclasses import dataclass
from typing import Dict, Any, List
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

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


# Workflow functions for each entity_model

async def process_user(entity: Dict[str, Any]) -> Dict[str, Any]:
    if "createdAt" not in entity:
        entity["createdAt"] = now_iso()
    return entity


async def process_workflow(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("state", "initialized")
    entity.setdefault("currentTask", None)
    entity.setdefault("history", [])
    entity.setdefault("startedAt", now_iso())

    # We need the persisted entity's technicalId to run background tasks
    workflow_id = entity.get("technicalId") or entity.get("workflowId")
    if not workflow_id:
        # Sometimes the ID might not be present yet; in that case, do not schedule tasks
        return entity

    async def workflow_task(workflow_id: str):
        try:
            await asyncio.sleep(1)
            wf = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="workflow",
                entity_version=ENTITY_VERSION,
                technical_id=workflow_id
            )
            if not wf:
                return
            wf["state"] = "completed"
            wf["currentTask"] = None
            wf.setdefault("history", []).append({
                "task": "initial",
                "user": "system",
                "timestamp": now_iso(),
                "action": "completed"
            })
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="workflow",
                entity_version=ENTITY_VERSION,
                entity=wf,
                technical_id=workflow_id,
                meta={}
            )
            logger.info(f"Workflow {workflow_id} completed")
        except Exception as e:
            logger.exception(e)

    asyncio.create_task(workflow_task(workflow_id))
    return entity


async def process_budget(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("status", "queued")
    entity.setdefault("requestedAt", now_iso())

    forecast_id = entity.get("technicalId") or entity.get("forecastId")
    if not forecast_id:
        return entity

    async def forecast_task(forecast_id: str):
        try:
            results = {}
            forecast_options = entity.get("forecastOptions", {})
            budget_data = entity.get("budgetData", {})

            if forecast_options.get("useAIModel"):
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(AI_MODEL_API, json={"budget": budget_data})
                    if resp.status_code == 200:
                        results = resp.json().get("forecastResults", {})
                    else:
                        logger.warning(f"AI model responded with status {resp.status_code}")
            else:
                results = {dep: {"forecasted": val, "variance": 0} for dep, val in budget_data.items()}

            forecast = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="budget",
                entity_version=ENTITY_VERSION,
                technical_id=forecast_id
            )
            if not forecast:
                return
            forecast["status"] = "completed"
            forecast["results"] = results
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="budget",
                entity_version=ENTITY_VERSION,
                entity=forecast,
                technical_id=forecast_id,
                meta={}
            )
            logger.info(f"Forecast completed: {forecast_id}")
        except Exception as e:
            try:
                forecast = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="budget",
                    entity_version=ENTITY_VERSION,
                    technical_id=forecast_id
                )
                if forecast:
                    forecast["status"] = "error"
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="budget",
                        entity_version=ENTITY_VERSION,
                        entity=forecast,
                        technical_id=forecast_id,
                        meta={}
                    )
            except Exception:
                pass
            logger.exception(e)

    asyncio.create_task(forecast_task(forecast_id))
    return entity


async def process_requisition(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("status", "pending")
    entity.setdefault("approvalHistory", [])
    entity.setdefault("submittedAt", now_iso())
    return entity


async def process_payment(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("status", "queued")
    entity.setdefault("requestedAt", now_iso())

    payment_id = entity.get("technicalId") or entity.get("paymentId")
    if not payment_id:
        return entity

    async def payment_task(payment_id: str):
        try:
            await asyncio.sleep(2)
            payment = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="payment",
                entity_version=ENTITY_VERSION,
                technical_id=payment_id
            )
            if not payment:
                return
            payment["status"] = "processed"
            payment["processedDate"] = now_iso()
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="payment",
                entity_version=ENTITY_VERSION,
                entity=payment,
                technical_id=payment_id,
                meta={}
            )
            logger.info(f"Payment processed: {payment_id}")
        except Exception as e:
            try:
                payment = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="payment",
                    entity_version=ENTITY_VERSION,
                    technical_id=payment_id
                )
                if payment:
                    payment["status"] = "error"
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="payment",
                        entity_version=ENTITY_VERSION,
                        entity=payment,
                        technical_id=payment_id,
                        meta={}
                    )
            except Exception:
                pass
            logger.exception(e)

    asyncio.create_task(payment_task(payment_id))
    return entity


async def process_report(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("status", "queued")
    entity.setdefault("createdDate", now_iso())
    entity.setdefault("downloadUrl", None)

    report_id = entity.get("technicalId") or entity.get("reportId")
    if not report_id:
        return entity

    async def report_task(report_id: str):
        try:
            await asyncio.sleep(1)
            report = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="report",
                entity_version=ENTITY_VERSION,
                technical_id=report_id
            )
            if not report:
                return
            report["status"] = "ready"
            report["downloadUrl"] = f"https://mockreports.example.com/download/{report_id}"
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="report",
                entity_version=ENTITY_VERSION,
                entity=report,
                technical_id=report_id,
                meta={}
            )
            logger.info(f"Report ready: {report_id}")
        except Exception as e:
            try:
                report = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="report",
                    entity_version=ENTITY_VERSION,
                    technical_id=report_id
                )
                if report:
                    report["status"] = "error"
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="report",
                        entity_version=ENTITY_VERSION,
                        entity=report,
                        technical_id=report_id,
                        meta={}
                    )
            except Exception:
                pass
            logger.exception(e)

    asyncio.create_task(report_task(report_id))
    return entity


@app.route('/api/users/create', methods=['POST'])
@validate_request(CreateUserRequest)
async def create_user(data: CreateUserRequest):
    data_dict = {
        "username": data.username,
        "email": data.email,
        "role": data.role,
        "department": data.department,
        "delegation": data.delegateTo,
    }
    try:
        user_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_user
        )
        logger.info(f"User created: {user_id}")
        return jsonify({"userId": user_id, "status": "created"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create user"}), 500


@app.route('/api/users/<user_id>', methods=['GET'])
async def get_user(user_id):
    try:
        user = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            technical_id=user_id
        )
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve user"}), 500


@app.route('/api/users/<user_id>/updateRoles', methods=['POST'])
@validate_request(UpdateUserRolesRequest)
async def update_user_roles(user_id: str, data: UpdateUserRolesRequest):
    try:
        existing_user = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            technical_id=user_id
        )
        if not existing_user:
            return jsonify({"error": "User not found"}), 404
        existing_user["role"] = data.role
        existing_user["permissions"] = data.permissions
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=existing_user,
            technical_id=user_id,
            meta={}
        )
        logger.info(f"User roles updated: {user_id}")
        return jsonify({"status": "updated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update user roles"}), 500


@app.route('/api/workflows/trigger', methods=['POST'])
@validate_request(TriggerWorkflowRequest)
async def trigger_workflow(data: TriggerWorkflowRequest):
    workflow_data = {
        "entityType": data.entityType,
        "entityId": data.entityId,
        "event": data.event,
        "state": "started",
        "currentTask": "initial",
        "history": [],
        "payload": data.payload or {},
        "startedAt": now_iso(),
    }
    try:
        workflow_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="workflow",
            entity_version=ENTITY_VERSION,
            entity=workflow_data,
            workflow=process_workflow
        )
        logger.info(f"Workflow triggered: {workflow_id}")
        return jsonify({"workflowId": workflow_id, "status": "started"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to trigger workflow"}), 500


@app.route('/api/workflows/<workflow_id>/status', methods=['GET'])
async def get_workflow_status(workflow_id):
    try:
        wf = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="workflow",
            entity_version=ENTITY_VERSION,
            technical_id=workflow_id
        )
        if not wf:
            return jsonify({"error": "Workflow not found"}), 404
        return jsonify({
            "workflowId": wf.get("workflowId", workflow_id),
            "state": wf["state"],
            "currentTask": wf["currentTask"],
            "history": wf["history"],
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve workflow status"}), 500


@app.route('/api/budgeting/forecast', methods=['POST'])
@validate_request(BudgetForecastRequest)
async def budget_forecast(data: BudgetForecastRequest):
    forecast_data = {
        "entityId": data.entityId,
        "budgetVersion": data.budgetVersion,
        "period": data.period,
        "status": "processing",
        "results": None,
        "requestedAt": now_iso(),
        "budgetData": data.budgetData,
        "forecastOptions": data.forecastOptions,
    }
    try:
        forecast_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="budget",
            entity_version=ENTITY_VERSION,
            entity=forecast_data,
            workflow=process_budget
        )
        logger.info(f"Budget forecast requested: {forecast_id}")
        return jsonify({"forecastId": forecast_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to request budget forecast"}), 500


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
    requisition_data = {
        "requestorId": data.requestorId,
        "items": data.items,
        "budgetVersion": data.budgetVersion,
        "status": "submitted",
        "approvalHistory": [],
        "submittedAt": now_iso(),
    }
    try:
        req_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="requisition",
            entity_version=ENTITY_VERSION,
            entity=requisition_data,
            workflow=process_requisition
        )
        logger.info(f"Requisition submitted: {req_id}")
        return jsonify({"requisitionId": req_id, "status": "submitted"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to submit requisition"}), 500


@app.route('/api/procurement/requisition/<req_id>', methods=['GET'])
async def get_requisition_status(req_id):
    try:
        req = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="requisition",
            entity_version=ENTITY_VERSION,
            technical_id=req_id
        )
        if not req:
            return jsonify({"error": "Requisition not found"}), 404
        return jsonify({
            "requisitionId": req.get("requisitionId", req_id),
            "status": req.get("status"),
            "approvalHistory": req.get("approvalHistory", []),
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve requisition"}), 500


@app.route('/api/payments/request', methods=['POST'])
@validate_request(SubmitPaymentRequest)
async def submit_payment_request(data: SubmitPaymentRequest):
    payment_data = {
        "vendorId": data.vendorId,
        "amount": data.amount,
        "dueDate": data.dueDate,
        "currency": data.currency,
        "paymentMethod": data.paymentMethod,
        "status": "queued",
        "requestedAt": now_iso(),
    }
    try:
        payment_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="payment",
            entity_version=ENTITY_VERSION,
            entity=payment_data,
            workflow=process_payment
        )
        logger.info(f"Payment request queued: {payment_id}")
        return jsonify({"paymentId": payment_id, "status": "queued"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to queue payment request"}), 500


@app.route('/api/payments/<payment_id>', methods=['GET'])
async def get_payment_status(payment_id):
    try:
        payment = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="payment",
            entity_version=ENTITY_VERSION,
            technical_id=payment_id
        )
        if not payment:
            return jsonify({"error": "Payment not found"}), 404
        return jsonify(payment)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve payment status"}), 500


@app.route('/api/reports/generate', methods=['POST'])
@validate_request(GenerateReportRequest)
async def generate_report(data: GenerateReportRequest):
    report_data = {
        "reportType": data.reportType,
        "filters": data.filters,
        "format": data.format,
        "status": "processing",
        "createdDate": now_iso(),
        "downloadUrl": None,
    }
    try:
        report_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=report_data,
            workflow=process_report
        )
        logger.info(f"Report generation started: {report_id}")
        return jsonify({"reportId": report_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start report generation"}), 500


@app.route('/api/reports/<report_id>', methods=['GET'])
async def get_report_metadata(report_id):
    try:
        report = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            technical_id=report_id
        )
        if not report:
            return jsonify({"error": "Report not found"}), 404
        return jsonify(report)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve report metadata"}), 500


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)