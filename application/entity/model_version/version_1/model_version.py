from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class ModelVersion(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "ModelVersion"
    ENTITY_VERSION: ClassVar[int] = 1

    model_name: str = Field(..., description="Name of the model (e.g., 'credit_scorer_v1')")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    
    model_type: str = Field(
        ...,
        description="Model runtime type: ONNX, TENSORFLOW_SERVING, TORCHSERVE, RULE_BASED",
    )
    
    model_path: str = Field(..., description="Path or URI to model artifact")
    model_hash: Optional[str] = Field(
        default=None,
        description="SHA256 hash of model artifact for integrity verification",
    )
    
    training_date: str = Field(..., description="Date model was trained (ISO 8601)")
    training_dataset_version: Optional[str] = Field(
        default=None,
        description="Version of training dataset used",
    )
    
    performance_metrics: Optional[Dict[str, float]] = Field(
        default=None,
        alias="performanceMetrics",
        description="Model performance metrics (AUC, precision, recall, etc.)",
    )
    
    feature_list: Optional[List[str]] = Field(
        default=None,
        alias="featureList",
        description="List of features expected by model",
    )
    
    deployment_status: str = Field(
        default="registered",
        description="REGISTERED, CANARY, PRODUCTION, DEPRECATED",
    )
    
    canary_traffic_percent: Optional[int] = Field(
        default=None,
        alias="canaryTrafficPercent",
        description="Percentage of traffic for canary deployment (0-100)",
    )
    
    fallback_model_id: Optional[str] = Field(
        default=None,
        alias="fallbackModelId",
        description="Reference to fallback model if this one fails",
    )
    
    inference_latency_p95_ms: Optional[int] = Field(
        default=None,
        alias="inferenceLatencyP95Ms",
        description="95th percentile inference latency in milliseconds",
    )
    
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (author, description, tags, etc.)",
    )
    
    model_config = ConfigDict(populate_by_name=True)

