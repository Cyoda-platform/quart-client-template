"""
InstrumentSetupProcessor for Real-Time Trading Platform

Handles instrument setup with trading parameters configuration and
market data feed initialization.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.instrument.version_1.instrument import Instrument
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class InstrumentSetupProcessor(CyodaProcessor):
    """
    Processor for Instrument that handles setup and configuration.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InstrumentSetupProcessor",
            description="Sets up instruments with trading parameters and market data feeds",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Setup the Instrument with trading parameters and market data configuration.

        Args:
            entity: The Instrument to setup (must be in 'validated' state)
            **kwargs: Additional processing parameters

        Returns:
            The instrument with setup data
        """
        try:
            self.logger.info(
                f"Setting up Instrument {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Instrument for type-safe operations
            instrument = cast_entity(entity, Instrument)

            # Create setup data
            setup_data = self._create_setup_data(instrument)
            instrument.set_setup_data(setup_data)

            # Log setup completion
            self.logger.info(
                f"Instrument {instrument.technical_id} setup completed successfully"
            )

            return instrument

        except Exception as e:
            self.logger.error(
                f"Error setting up Instrument {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _create_setup_data(self, instrument: Instrument) -> Dict[str, Any]:
        """
        Create setup data for the instrument.

        Args:
            instrument: The Instrument entity

        Returns:
            Dictionary containing setup data
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        setup_data: Dict[str, Any] = {
            "setup_at": current_timestamp,
            "trading_enabled": instrument.is_tradable,
            "market_data_feed": self._configure_market_data_feed(instrument),
            "trading_parameters": self._configure_trading_parameters(instrument),
            "setup_version": "1.0",
        }

        return setup_data

    def _configure_market_data_feed(self, instrument: Instrument) -> Dict[str, Any]:
        """Configure market data feed for the instrument"""
        return {
            "feed_enabled": True,
            "feed_source": f"{instrument.exchange}_FEED",
            "update_frequency": "REAL_TIME",
            "data_fields": ["price", "volume", "bid", "ask"],
        }

    def _configure_trading_parameters(self, instrument: Instrument) -> Dict[str, Any]:
        """Configure trading parameters for the instrument"""
        return {
            "min_order_size": instrument.lot_size,
            "max_order_size": instrument.max_order_size or 1000000,
            "price_precision": self._calculate_price_precision(instrument.tick_size),
            "margin_enabled": instrument.requires_margin(),
            "trading_hours": instrument.trading_hours or self._default_trading_hours(),
        }

    def _calculate_price_precision(self, tick_size: float) -> int:
        """Calculate price precision based on tick size"""
        if tick_size >= 1.0:
            return 0
        elif tick_size >= 0.1:
            return 1
        elif tick_size >= 0.01:
            return 2
        elif tick_size >= 0.001:
            return 3
        else:
            return 4

    def _default_trading_hours(self) -> Dict[str, str]:
        """Get default trading hours"""
        return {
            "market_open": "09:30",
            "market_close": "16:00",
            "timezone": "US/Eastern",
        }
