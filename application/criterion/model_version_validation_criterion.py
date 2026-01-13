from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.model_version.version_1.model_version import ModelVersion


class ModelVersionValidationCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="ModelVersionValidationCriterion",
            description="Validates model version metadata and performance metrics",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            self.logger.info(f"Validating model version {getattr(entity, 'technical_id', '<unknown>')}")

            model = cast_entity(entity, ModelVersion)

            if not model.model_name or len(model.model_name.strip()) < 3:
                self.logger.warning(f"Invalid model_name: {model.model_name}")
                return False

            if not model.version or len(model.version.strip()) < 3:
                self.logger.warning(f"Invalid version: {model.version}")
                return False

            valid_types = ["ONNX", "TENSORFLOW_SERVING", "TORCHSERVE", "RULE_BASED"]
            if model.model_type not in valid_types:
                self.logger.warning(f"Invalid model_type: {model.model_type}")
                return False

            if not model.model_path:
                self.logger.warning("Missing model_path")
                return False

            if not model.training_date:
                self.logger.warning("Missing training_date")
                return False

            if model.performance_metrics:
                metrics = model.performance_metrics
                if "auc" in metrics and (metrics["auc"] < 0 or metrics["auc"] > 1):
                    self.logger.warning(f"Invalid AUC: {metrics['auc']}")
                    return False

                if "precision" in metrics and (metrics["precision"] < 0 or metrics["precision"] > 1):
                    self.logger.warning(f"Invalid precision: {metrics['precision']}")
                    return False

            if model.canary_traffic_percent and (model.canary_traffic_percent < 0 or model.canary_traffic_percent > 100):
                self.logger.warning(f"Invalid canary traffic: {model.canary_traffic_percent}")
                return False

            self.logger.info(f"Model version {model.technical_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating model version: {str(e)}")
            return False

