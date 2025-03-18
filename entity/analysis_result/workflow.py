import os
import asyncio
import logging
import random
import string
from datetime import datetime
from dataclasses import dataclass
from typing import List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)

# Validate that the entity contains valid comments data.
async def process_validate_comments(entity: dict):
    comments = entity.get("comments", [])
    if not isinstance(comments, list):
        entity["error"] = "Invalid comments data"

# Calculate sentiment counts based on comments.
async def process_calculate_sentiment(entity: dict):
    positive_words = ['great', 'good', 'excellent', 'positive', 'stylish', 'comfortable']
    negative_words = ['bad', 'poor', 'terrible', 'negative']
    positive_count = 0
    negative_count = 0
    for comment in entity.get("comments", []):
        lc = comment.lower()
        for word in positive_words:
            if word in lc:
                positive_count += 1
        for word in negative_words:
            if word in lc:
                negative_count += 1
    entity["positive_count"] = positive_count
    entity["negative_count"] = negative_count

# Set the analysis summary and attach the sentiment result to the entity.
async def process_set_summary(entity: dict):
    positive_count = entity.get("positive_count", 0)
    negative_count = entity.get("negative_count", 0)
    summary = "Mixed feedback"
    if positive_count > negative_count:
        summary = "Overall positive feedback"
    elif negative_count > positive_count:
        summary = "Overall negative feedback"
    entity["analysis_result"] = {
        "status": "success",
        "summary": summary,
        "sentiment": {
            "positive": positive_count,
            "negative": negative_count
        },
        "processed_at": datetime.utcnow().isoformat()
    }