"""
InstrumentValidationCriterion for Real-Time Trading Platform

Validates that Instrument meets all required business rules before it can
proceed to setup stage.
"""

from typing import Any

from application.entity.instrument.version_1.instrument import Instrument
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class InstrumentValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Instrument that checks all business rules
    before the entity can proceed to setup stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InstrumentValidationCriterion",
            description="Validates Instrument business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the Instrument meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Instrument)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating Instrument {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Instrument for type-safe operations
            instrument = cast_entity(entity, Instrument)

            # Validate required fields
            if not instrument.symbol or len(instrument.symbol.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid symbol"
                )
                return False

            if instrument.instrument_type not in Instrument.ALLOWED_INSTRUMENT_TYPES:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid instrument_type: {instrument.instrument_type}"
                )
                return False

            if not instrument.name or len(instrument.name.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid name"
                )
                return False

            if not instrument.exchange or len(instrument.exchange.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid exchange"
                )
                return False

            if instrument.currency not in Instrument.ALLOWED_CURRENCIES:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid currency: {instrument.currency}"
                )
                return False

            if instrument.lot_size <= 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid lot_size: {instrument.lot_size}"
                )
                return False

            if instrument.tick_size <= 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid tick_size: {instrument.tick_size}"
                )
                return False

            # Validate derivative-specific requirements
            if instrument.is_derivative():
                if not instrument.contract_specs:
                    self.logger.warning(
                        f"Derivative Instrument {instrument.technical_id} missing contract_specs"
                    )
                    return False

            # Validate margin requirements
            if instrument.margin_requirement is not None:
                if (
                    instrument.margin_requirement < 0
                    or instrument.margin_requirement > 100
                ):
                    self.logger.warning(
                        f"Instrument {instrument.technical_id} has invalid margin_requirement: {instrument.margin_requirement}"
                    )
                    return False

            # Validate max order size
            if instrument.max_order_size is not None and instrument.max_order_size <= 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid max_order_size: {instrument.max_order_size}"
                )
                return False

            self.logger.info(
                f"Instrument {instrument.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating Instrument {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
