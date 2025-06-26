import datetime
import asyncio
import base64
import logging
import httpx
from uuid import uuid4

logger = logging.getLogger(__name__)

async def detect_food_request_from_text(entity: dict) -> None:
    text = entity.get("inputData", "").lower()
    keywords = ["snack", "food", "hungry", "feed", "treat", "meow", "demand"]
    entity["detected"] = any(k in text for k in keywords)

async def detect_food_request_from_audio(entity: dict) -> None:
    ASSEMBLYAI_API_KEY = "YOUR_ASSEMBLYAI_API_KEY"  # TODO: Add your AssemblyAI API key here
    audio_b64 = entity.get("inputData", "")
    entity["detected"] = False
    try:
        audio_bytes = base64.b64decode(audio_b64)
        async with httpx.AsyncClient(timeout=60) as client:
            upload_resp = await client.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                content=audio_bytes,
            )
            upload_resp.raise_for_status()
            upload_url = upload_resp.json()["upload_url"]
            transcript_req = {"audio_url": upload_url, "language_code": "en", "iab_categories": False}
            tr_resp = await client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
                json=transcript_req,
            )
            tr_resp.raise_for_status()
            tid = tr_resp.json()["id"]
            while True:
                status_resp = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{tid}",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                )
                status_resp.raise_for_status()
                st = status_resp.json()
                if st["status"] == "completed":
                    transcript_text = st["text"]
                    entity["detected"] = any(k in transcript_text.lower() for k in ["snack", "food", "hungry", "feed", "treat", "meow", "demand"])
                    break
                if st["status"] == "error":
                    logger.error("AssemblyAI error: %s", st.get("error"))
                    entity["detected"] = False
                    break
                await asyncio.sleep(2)
    except Exception:
        logger.exception("Audio detection failed")
        entity["detected"] = False

async def send_notification(entity: dict) -> None:
    entity["notification"] = {
        "catId": entity.get("catId"),
        "eventType": "food_request",
        "message": "Emergency! A cat demands snacks",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "queued"
    }
    logger.info("Notification prepared: %s", entity["notification"])

async def process_event(entity: dict) -> None:
    input_type = entity.get("inputType")
    if input_type == "text":
        await detect_food_request_from_text(entity)
    elif input_type == "audio":
        await detect_food_request_from_audio(entity)
    else:
        entity["detected"] = False

async def process_notification(entity: dict) -> None:
    # Workflow orchestration only
    if "timestamp" not in entity:
        entity["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    entity.setdefault("priority", "normal")

    await process_event(entity)

    if entity.get("detected"):
        entity["eventId"] = str(uuid4())
        entity["eventType"] = "food_request"
        entity["message"] = "Emergency! A cat demands snacks"
        await send_notification(entity)
    else:
        entity["eventType"] = None
        entity["message"] = "No key event detected"