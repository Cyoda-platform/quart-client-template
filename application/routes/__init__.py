"""
Routes module for the Claims Platform Application.

This module exports all available blueprints for the application.
"""

from .claim_documents import claim_documents_bp
from .claims import claims_bp
from .fraud_alerts import fraud_alerts_bp
from .policies import policies_bp
from .queues import queues_bp
from .users import users_bp

__all__ = [
    "claims_bp",
    "claim_documents_bp",
    "fraud_alerts_bp",
    "policies_bp",
    "queues_bp",
    "users_bp",
]
