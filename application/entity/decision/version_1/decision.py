from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Decision(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Decision"
    ENTITY_VERSION: ClassVar[int] = 1

    applicant_id: str = Field(..., description="Reference to Applicant entity")
    credit_report_id: Optional[str] = Field(
        default=None,
        description="Reference to CreditReport entity",
    )
    
    decision_outcome: str = Field(
        ...,
        description="APPROVED, DECLINED, REFERRED",
    )
    
    credit_score: Optional[int] = Field(default=None, description="Credit score used in decision")
    model_score: Optional[float] = Field(
        default=None,
        description="Raw model score (0-1 range)",
    )
    
    model_version_id: Optional[str] = Field(
        default=None,
        description="Reference to ModelVersion used",
    )
    
    decision_latency_ms: Optional[int] = Field(
        default=None,
        description="End-to-end decision latency in milliseconds",
    )
    
    features_used: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Feature values used in model inference",
    )
    
    rule_overrides: Optional[List[str]] = Field(
        default=None,
        description="List of rule-based overrides applied",
    )
    
    explanation: Optional[str] = Field(
        default=None,
        description="Concise explanation of decision for compliance",
    )
    
    approved_amount: Optional[float] = Field(
        default=None,
        description="Approved loan amount (if approved)",
    )
    approved_rate: Optional[float] = Field(
        default=None,
        description="Approved interest rate (if approved)",
    )
    
    decline_reason: Optional[str] = Field(
        default=None,
        description="Reason for decline (if declined)",
    )
    
    audit_trail: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        alias="auditTrail",
        description="Immutable audit trail of decision process",
    )
    
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")
    
    model_config = ConfigDict(populate_by_name=True)

