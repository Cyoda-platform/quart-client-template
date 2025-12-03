"""
Trading Platform Routes Module

Registers all trading platform API blueprints with the Quart application.
"""

from quart import Quart

from .orders import orders_bp
from .portfolios import portfolios_bp
from .positions import positions_bp
from .instruments import instruments_bp
from .market_data import market_data_bp
from .risk_controls import risk_controls_bp


def register_trading_routes(app: Quart) -> None:
    """Register all trading platform route blueprints with the application."""
    app.register_blueprint(orders_bp)
    app.register_blueprint(portfolios_bp)
    app.register_blueprint(positions_bp)
    app.register_blueprint(instruments_bp)
    app.register_blueprint(market_data_bp)
    app.register_blueprint(risk_controls_bp)