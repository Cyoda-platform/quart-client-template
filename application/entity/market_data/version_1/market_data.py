# entity/market_data/version_1/market_data.py

"""
MarketData Entity for Trading Platform

Represents real-time market data feeds and pricing information.
Manages market data validation, quality checks, and distribution.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data feeds and pricing information
    with data quality validation and distribution capabilities.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core identification
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument technical ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange code")
    data_source: str = Field(..., alias="dataSource", description="Market data source")

    # Price data
    last_price: Optional[Decimal] = Field(default=None, alias="lastPrice", description="Last traded price")
    bid_price: Optional[Decimal] = Field(default=None, alias="bidPrice", description="Best bid price")
    ask_price: Optional[Decimal] = Field(default=None, alias="askPrice", description="Best ask price")
    bid_size: Optional[Decimal] = Field(default=None, alias="bidSize", description="Bid size")
    ask_size: Optional[Decimal] = Field(default=None, alias="askSize", description="Ask size")

    # Trading data
    volume: Optional[Decimal] = Field(default=None, description="Trading volume")
    turnover: Optional[Decimal] = Field(default=None, description="Trading turnover")
    vwap: Optional[Decimal] = Field(default=None, description="Volume weighted average price")

    # Daily statistics
    open_price: Optional[Decimal] = Field(default=None, alias="openPrice", description="Opening price")
    high_price: Optional[Decimal] = Field(default=None, alias="highPrice", description="High price")
    low_price: Optional[Decimal] = Field(default=None, alias="lowPrice", description="Low price")
    close_price: Optional[Decimal] = Field(default=None, alias="closePrice", description="Previous close price")
    
    # Price changes
    price_change: Optional[Decimal] = Field(default=None, alias="priceChange", description="Price change from previous close")
    price_change_percent: Optional[Decimal] = Field(default=None, alias="priceChangePercent", description="Price change percentage")

    # Market status
    market_status: str = Field(default="UNKNOWN", alias="marketStatus", description="Market status")
    trading_session: Optional[str] = Field(default=None, alias="tradingSession", description="Trading session")

    # Data quality
    data_quality: str = Field(default="GOOD", alias="dataQuality", description="Data quality indicator")
    stale_threshold_seconds: int = Field(default=60, alias="staleThresholdSeconds", description="Stale data threshold in seconds")
    
    # Timestamps
    market_timestamp: str = Field(..., alias="marketTimestamp", description="Market data timestamp from exchange")
    received_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="receivedTimestamp",
        description="Timestamp when data was received"
    )
    processed_timestamp: Optional[str] = Field(default=None, alias="processedTimestamp", description="Timestamp when data was processed")

    # Validation constants
    VALID_MARKET_STATUSES: ClassVar[List[str]] = ["OPEN", "CLOSED", "PRE_OPEN", "POST_CLOSE", "HALTED", "SUSPENDED", "UNKNOWN"]
    VALID_DATA_QUALITIES: ClassVar[List[str]] = ["GOOD", "STALE", "SUSPECT", "BAD"]
    VALID_TRADING_SESSIONS: ClassVar[List[str]] = ["REGULAR", "PRE_MARKET", "POST_MARKET", "EXTENDED"]

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        return v.strip().upper()

    @field_validator("market_status")
    @classmethod
    def validate_market_status(cls, v: str) -> str:
        """Validate market status"""
        if v not in cls.VALID_MARKET_STATUSES:
            raise ValueError(f"Market status must be one of: {cls.VALID_MARKET_STATUSES}")
        return v

    @field_validator("data_quality")
    @classmethod
    def validate_data_quality(cls, v: str) -> str:
        """Validate data quality"""
        if v not in cls.VALID_DATA_QUALITIES:
            raise ValueError(f"Data quality must be one of: {cls.VALID_DATA_QUALITIES}")
        return v

    def update_price_data(self, last_price: Optional[Decimal] = None,
                         bid_price: Optional[Decimal] = None,
                         ask_price: Optional[Decimal] = None,
                         bid_size: Optional[Decimal] = None,
                         ask_size: Optional[Decimal] = None) -> None:
        """Update price data"""
        if last_price is not None:
            self.last_price = last_price
        if bid_price is not None:
            self.bid_price = bid_price
        if ask_price is not None:
            self.ask_price = ask_price
        if bid_size is not None:
            self.bid_size = bid_size
        if ask_size is not None:
            self.ask_size = ask_size
        
        self.update_processed_timestamp()

    def update_trading_data(self, volume: Optional[Decimal] = None,
                           turnover: Optional[Decimal] = None,
                           vwap: Optional[Decimal] = None) -> None:
        """Update trading data"""
        if volume is not None:
            self.volume = volume
        if turnover is not None:
            self.turnover = turnover
        if vwap is not None:
            self.vwap = vwap
        
        self.update_processed_timestamp()

    def update_daily_stats(self, open_price: Optional[Decimal] = None,
                          high_price: Optional[Decimal] = None,
                          low_price: Optional[Decimal] = None,
                          close_price: Optional[Decimal] = None) -> None:
        """Update daily statistics"""
        if open_price is not None:
            self.open_price = open_price
        if high_price is not None:
            self.high_price = high_price
        if low_price is not None:
            self.low_price = low_price
        if close_price is not None:
            self.close_price = close_price
        
        # Calculate price changes if we have both last price and close price
        if self.last_price is not None and self.close_price is not None:
            self.price_change = self.last_price - self.close_price
            if self.close_price != 0:
                self.price_change_percent = (self.price_change / self.close_price) * 100
        
        self.update_processed_timestamp()

    def update_market_status(self, market_status: str, trading_session: Optional[str] = None) -> None:
        """Update market status"""
        self.market_status = market_status
        if trading_session is not None:
            self.trading_session = trading_session
        self.update_processed_timestamp()

    def update_data_quality(self, data_quality: str) -> None:
        """Update data quality indicator"""
        self.data_quality = data_quality
        self.update_processed_timestamp()

    def update_processed_timestamp(self) -> None:
        """Update the processed timestamp"""
        self.processed_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def is_stale(self) -> bool:
        """Check if market data is stale"""
        if not self.market_timestamp:
            return True
        
        try:
            market_time = datetime.fromisoformat(self.market_timestamp.replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)
            age_seconds = (current_time - market_time).total_seconds()
            return age_seconds > self.stale_threshold_seconds
        except (ValueError, TypeError):
            return True

    def get_spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread"""
        if self.bid_price is not None and self.ask_price is not None:
            return self.ask_price - self.bid_price
        return None

    def get_mid_price(self) -> Optional[Decimal]:
        """Calculate mid price"""
        if self.bid_price is not None and self.ask_price is not None:
            return (self.bid_price + self.ask_price) / 2
        return None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["isStale"] = self.is_stale()
        data["spread"] = self.get_spread()
        data["midPrice"] = self.get_mid_price()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
