"""
Portfolio Entity for Real-Time Trading Platform

Represents trading portfolios with position tracking, P&L calculations,
and real-time valuation updates.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Portfolio entity represents trading portfolios with position tracking and P&L calculations.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> active -> updated
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    portfolio_id: str = Field(
        ..., 
        alias="portfolioId",
        description="Business portfolio identifier"
    )
    account_id: str = Field(
        ..., 
        alias="accountId",
        description="Account identifier"
    )
    cash_balance: float = Field(
        ..., 
        alias="cashBalance",
        description="Available cash balance"
    )
    total_value: float = Field(
        ..., 
        alias="totalValue",
        description="Total portfolio value"
    )

    # P&L tracking fields
    unrealized_pnl: float = Field(
        default=0.0,
        alias="unrealizedPnl",
        description="Unrealized profit and loss"
    )
    realized_pnl: float = Field(
        default=0.0,
        alias="realizedPnl",
        description="Realized profit and loss"
    )

    # Position tracking
    positions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Current positions in the portfolio"
    )

    # Portfolio metadata
    base_currency: str = Field(
        default="USD",
        alias="baseCurrency",
        description="Base currency for portfolio valuation"
    )
    portfolio_type: str = Field(
        default="TRADING",
        alias="portfolioType",
        description="Portfolio type: TRADING, INVESTMENT, HEDGE"
    )
    risk_profile: Optional[str] = Field(
        default=None,
        alias="riskProfile",
        description="Risk profile: CONSERVATIVE, MODERATE, AGGRESSIVE"
    )

    # Calculated fields (updated during processing)
    market_value: Optional[float] = Field(
        default=None,
        alias="marketValue",
        description="Current market value of positions"
    )
    day_pnl: Optional[float] = Field(
        default=None,
        alias="dayPnl",
        description="Day profit and loss"
    )
    exposure: Optional[Dict[str, float]] = Field(
        default=None,
        description="Portfolio exposure by asset class/sector"
    )

    # Processing-related fields
    update_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="updateData",
        description="Data from portfolio updates"
    )
    pnl_calculation_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="pnlCalculationData",
        description="P&L calculation details"
    )

    # Validation constants
    ALLOWED_CURRENCIES: ClassVar[List[str]] = [
        "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"
    ]
    ALLOWED_PORTFOLIO_TYPES: ClassVar[List[str]] = ["TRADING", "INVESTMENT", "HEDGE"]
    ALLOWED_RISK_PROFILES: ClassVar[List[str]] = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]

    @field_validator("portfolio_id")
    @classmethod
    def validate_portfolio_id(cls, v: str) -> str:
        """Validate portfolio ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Portfolio ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Portfolio ID must be at most 50 characters long")
        return v.strip()

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Validate account ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Account ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Account ID must be at most 50 characters long")
        return v.strip()

    @field_validator("base_currency")
    @classmethod
    def validate_base_currency(cls, v: str) -> str:
        """Validate base currency"""
        currency_upper = v.upper()
        if currency_upper not in cls.ALLOWED_CURRENCIES:
            raise ValueError(f"Base currency must be one of: {cls.ALLOWED_CURRENCIES}")
        return currency_upper

    @field_validator("portfolio_type")
    @classmethod
    def validate_portfolio_type(cls, v: str) -> str:
        """Validate portfolio type"""
        if v not in cls.ALLOWED_PORTFOLIO_TYPES:
            raise ValueError(f"Portfolio type must be one of: {cls.ALLOWED_PORTFOLIO_TYPES}")
        return v

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validate risk profile"""
        if v is not None and v not in cls.ALLOWED_RISK_PROFILES:
            raise ValueError(f"Risk profile must be one of: {cls.ALLOWED_RISK_PROFILES}")
        return v

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol"""
        for position in self.positions:
            if position.get("symbol") == symbol:
                return position
        return None

    def add_position(self, symbol: str, quantity: int, average_price: float) -> None:
        """Add or update a position"""
        existing_position = self.get_position(symbol)
        
        if existing_position:
            # Update existing position
            old_quantity = existing_position["quantity"]
            old_avg_price = existing_position["average_price"]
            
            new_quantity = old_quantity + quantity
            if new_quantity != 0:
                new_avg_price = ((old_quantity * old_avg_price) + (quantity * average_price)) / new_quantity
                existing_position["quantity"] = new_quantity
                existing_position["average_price"] = new_avg_price
            else:
                # Remove position if quantity becomes zero
                self.positions.remove(existing_position)
        else:
            # Add new position
            if quantity != 0:
                self.positions.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "average_price": average_price,
                    "market_value": quantity * average_price,
                    "unrealized_pnl": 0.0
                })
        
        self.update_timestamp()

    def calculate_total_value(self) -> float:
        """Calculate total portfolio value"""
        position_value = sum(pos.get("market_value", 0) for pos in self.positions)
        return self.cash_balance + position_value

    def calculate_total_pnl(self) -> float:
        """Calculate total P&L"""
        return self.realized_pnl + self.unrealized_pnl

    def update_position_market_value(self, symbol: str, market_price: float) -> None:
        """Update market value for a position"""
        position = self.get_position(symbol)
        if position:
            quantity = position["quantity"]
            position["market_value"] = quantity * market_price
            position["unrealized_pnl"] = (market_price - position["average_price"]) * quantity
            self.update_timestamp()

    def set_update_data(self, update_data: Dict[str, Any]) -> None:
        """Set update data and refresh calculations"""
        self.update_data = update_data
        self.total_value = self.calculate_total_value()
        self.update_timestamp()

    def set_pnl_calculation_data(self, pnl_data: Dict[str, Any]) -> None:
        """Set P&L calculation data"""
        self.pnl_calculation_data = pnl_data
        self.update_timestamp()

    def get_net_exposure(self) -> float:
        """Calculate net exposure (long positions - short positions)"""
        long_value = sum(pos.get("market_value", 0) for pos in self.positions if pos.get("quantity", 0) > 0)
        short_value = sum(abs(pos.get("market_value", 0)) for pos in self.positions if pos.get("quantity", 0) < 0)
        return long_value - short_value

    def get_gross_exposure(self) -> float:
        """Calculate gross exposure (sum of absolute position values)"""
        return sum(abs(pos.get("market_value", 0)) for pos in self.positions)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        # Add calculated fields
        data["totalPnl"] = self.calculate_total_pnl()
        data["netExposure"] = self.get_net_exposure()
        data["grossExposure"] = self.get_gross_exposure()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
