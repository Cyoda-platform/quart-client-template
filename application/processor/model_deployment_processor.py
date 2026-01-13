from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.model_version.version_1.model_version import ModelVersion


class ModelDeploymentProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="ModelDeploymentProcessor",
            description="Manages model deployment to canary and production environments",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(f"Processing ModelVersion {getattr(entity, 'technical_id', '<unknown>')}")

            model_version = cast_entity(entity, ModelVersion)

            model_version.deployment_status = "canary"
            model_version.canary_traffic_percent = 10

            self.logger.info(f"ModelVersion {model_version.technical_id} deployed to canary")
            return model_version

        except Exception as e:
            self.logger.error(f"Error deploying model: {str(e)}")
            raise

