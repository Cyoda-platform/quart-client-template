import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class Signup:
    email: str

entity_name = "subscriber"  # underscore lowercase entity name

async def process_subscriber(entity: Dict) -> None:
    """
    Workflow applied to 'subscriber' entity before persistence.
    Validates email, checks duplicates, adds timestamps.
    """
    email = entity.get("email", "")
    if not isinstance(email, str):
        raise ValueError("Email must be a string")
    email = email.strip().lower()
    if "@" not in email or not email:
        raise ValueError("Invalid email format")
    entity["email"] = email

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.email",
                    "operatorType": "EQUALS",
                    "value": email,
                    "type": "simple"
                }
            ]
        }
    }
    existing = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if existing:
        # Mark duplicate to inform controller and skip persistence by raising Exception
        raise ValueError("Subscriber already exists")

    entity["createdAt"] = datetime.utcnow().isoformat()

async def process_weekly_task(entity: Dict) -> None:
    """
    Workflow function for weekly cat fact sending task.
    - Fetches cat fact.
    - Updates last_fact entity.
    - Sends emails to all subscribers.
    - Updates emails_sent metrics.
    """
    CAT_FACT_API = "https://catfact.ninja/fact"
    fact = "Cats are mysterious creatures!"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_FACT_API, timeout=10)
            response.raise_for_status()
            fact_resp = response.json()
            if isinstance(fact_resp, dict) and "fact" in fact_resp:
                fact = fact_resp["fact"]
    except Exception as e:
        logger.warning(f"Failed to fetch cat fact: {e}")

    # Update last_fact entity
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="last_fact",
            entity_version=ENTITY_VERSION,
            entity={"fact": fact},
            technical_id="last",
            meta={}
        )
    except Exception:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="last_fact",
                entity_version=ENTITY_VERSION,
                entity={"fact": fact}
            )
        except Exception as ex:
            logger.warning(f"Failed to add last_fact entity: {ex}")

    # Get all subscribers
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch subscribers for weekly task: {e}")
        subscribers = []

    emails = [sub.get("email") for sub in subscribers if sub.get("email")]
    emails = list(set(emails))  # Deduplicate emails

    async def send_email(to_email: str):
        logger.info(f"Sending email to {to_email} with subject 'Your Weekly Cat Fact 🐱'")
        await asyncio.sleep(0.1)  # simulate send delay
        # TODO: integrate real email sending here
        return True

    send_results = await asyncio.gather(*(send_email(email) for email in emails), return_exceptions=True)
    sent_count = sum(1 for r in send_results if r is True)

    # Update emails_sent metric
    try:
        metrics_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="metrics",
            entity_version=ENTITY_VERSION,
            technical_id="emails_sent"
        )
        prev_count = metrics_entity.get("emails_sent", 0) if metrics_entity else 0
        new_count = prev_count + sent_count
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="metrics",
            entity_version=ENTITY_VERSION,
            entity={"emails_sent": new_count},
            technical_id="emails_sent",
            meta={}
        )
    except Exception:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="metrics",
                entity_version=ENTITY_VERSION,
                entity={"emails_sent": sent_count}
            )
        except Exception as ex:
            logger.warning(f"Failed to add metrics entity: {ex}")

    entity["cat_fact"] = fact
    entity["emails_sent"] = sent_count
    entity["taskCompletedAt"] = datetime.utcnow().isoformat()


@routes_bp.route("/api/signup", methods=["POST"])
@validate_request(Signup)
async def signup(data: Signup):
    entity = {"email": data.email}
    try:
        _id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"success": True, "message": "User subscribed successfully"})
    except Exception as e:
        msg = str(e)
        if "already exists" in msg:
            return jsonify({"success": True, "message": "User already subscribed"})
        logger.warning(f"Signup failed: {msg}")
        return jsonify({"success": False, "message": msg}), 400


@routes_bp.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in subscribers if item.get("email")]
        emails = list(set(emails))
        return jsonify({"subscribers": emails, "count": len(emails)})
    except Exception as e:
        logger.error(f"Failed to get subscribers: {e}")
        return jsonify({"subscribers": [], "count": 0})


@routes_bp.route("/api/trigger-weekly", methods=["POST"])
async def trigger_weekly():
    entity = {"requestedAt": datetime.utcnow().isoformat()}
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weekly_task",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"success": True, "message": "Weekly cat fact sending started"}), 202
    except Exception as e:
        logger.error(f"Failed to trigger weekly task: {e}")
        return jsonify({"success": False, "message": "Failed to start weekly task"}), 500


@routes_bp.route("/api/report", methods=["GET"])
async def get_report():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        total_subscribers = len(set(sub.get("email") for sub in subscribers if sub.get("email")))
        try:
            metrics = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="metrics",
                entity_version=ENTITY_VERSION,
                technical_id="emails_sent"
            )
            emails_sent = metrics.get("emails_sent", 0) if metrics else 0
        except Exception:
            emails_sent = 0

        return jsonify({
            "total_subscribers": total_subscribers,
            "emails_sent": emails_sent,
            "interactions": {
                "email_opens": 0,
                "clicks": 0,
            }
        })
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        return jsonify({
            "total_subscribers": 0,
            "emails_sent": 0,
            "interactions": {
                "email_opens": 0,
                "clicks": 0,
            }
        })