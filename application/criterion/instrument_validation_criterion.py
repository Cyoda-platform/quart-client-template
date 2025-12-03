"""
InstrumentValidationCriterion for Trading Platform

Validates that an Instrument meets all required business rules before it can
proceed to activation and trading.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.instrument.version_1.instrument import Instrument


class InstrumentValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Instrument that checks all business rules
    before the instrument can be activated for trading.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InstrumentValidationCriterion",
            description="Validates Instrument business rules and trading eligibility",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the instrument meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Instrument)
            **kwargs: Additional criteria parameters

        Returns:
            True if the instrument meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating instrument {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Instrument for type-safe operations
            instrument = cast_entity(entity, Instrument)

            # Validate required fields
            if not instrument.symbol or len(instrument.symbol.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid symbol"
                )
                return False

            if not instrument.instrument_name or len(instrument.instrument_name.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid instrument_name"
                )
                return False

            # Validate instrument type
            if instrument.instrument_type not in instrument.VALID_INSTRUMENT_TYPES:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid instrument_type: {instrument.instrument_type}"
                )
                return False

            # Validate asset class
            if instrument.asset_class not in instrument.VALID_ASSET_CLASSES:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid asset_class: {instrument.asset_class}"
                )
                return False

            # Validate currency
            if instrument.currency not in instrument.VALID_CURRENCIES:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid currency: {instrument.currency}"
                )
                return False

            # Validate exchange
            if not instrument.exchange or len(instrument.exchange.strip()) == 0:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid exchange"
                )
                return False

            # Validate symbol format
            if not self._validate_symbol_format(instrument.symbol, instrument.instrument_type):
                self.logger.warning(
                    f"Instrument {instrument.technical_id} has invalid symbol format: {instrument.symbol}"
                )
                return False

            # Validate business rules
            if instrument.instrument_type == "OPTION":
                if not self._validate_option_fields(instrument):
                    return False

            if instrument.instrument_type == "FUTURE":
                if not self._validate_future_fields(instrument):
                    return False

            # Validate market data requirements
            if not instrument.market_data_source:
                self.logger.warning(
                    f"Instrument {instrument.technical_id} missing market_data_source"
                )
                return False

            # Check if instrument is eligible for trading
            if not instrument.is_tradeable():
                self.logger.warning(
                    f"Instrument {instrument.technical_id} is not tradeable"
                )
                return False

            self.logger.info(
                f"Instrument {instrument.technical_id} ({instrument.symbol}) passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating instrument {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    def _validate_symbol_format(self, symbol: str, instrument_type: str) -> bool:
        """Validate symbol format based on instrument type."""
        if instrument_type == "EQUITY":
            # Equity symbols should be 1-5 characters, alphanumeric
            return len(symbol) <= 5 and symbol.isalnum()
        
        elif instrument_type == "OPTION":
            # Option symbols should follow standard format (simplified check)
            return len(symbol) >= 6 and len(symbol) <= 21
        
        elif instrument_type == "FUTURE":
            # Future symbols should have month/year codes
            return len(symbol) >= 3 and len(symbol) <= 10
        
        elif instrument_type == "BOND":
            # Bond symbols can be longer
            return len(symbol) <= 12
        
        elif instrument_type == "ETF":
            # ETF symbols similar to equities
            return len(symbol) <= 5 and symbol.isalnum()
        
        return True  # Default validation

    def _validate_option_fields(self, instrument: Instrument) -> bool:
        """Validate option-specific fields."""
        if not instrument.underlying_symbol:
            self.logger.warning(
                f"Option instrument {instrument.technical_id} missing underlying_symbol"
            )
            return False

        if not instrument.strike_price or instrument.strike_price <= 0:
            self.logger.warning(
                f"Option instrument {instrument.technical_id} has invalid strike_price"
            )
            return False

        if not instrument.expiry_date:
            self.logger.warning(
                f"Option instrument {instrument.technical_id} missing expiry_date"
            )
            return False

        if instrument.option_type not in ["CALL", "PUT"]:
            self.logger.warning(
                f"Option instrument {instrument.technical_id} has invalid option_type: {instrument.option_type}"
            )
            return False

        return True

    def _validate_future_fields(self, instrument: Instrument) -> bool:
        """Validate future-specific fields."""
        if not instrument.underlying_symbol:
            self.logger.warning(
                f"Future instrument {instrument.technical_id} missing underlying_symbol"
            )
            return False

        if not instrument.expiry_date:
            self.logger.warning(
                f"Future instrument {instrument.technical_id} missing expiry_date"
            )
            return False

        if not instrument.contract_size or instrument.contract_size <= 0:
            self.logger.warning(
                f"Future instrument {instrument.technical_id} has invalid contract_size"
            )
            return False

        return True
