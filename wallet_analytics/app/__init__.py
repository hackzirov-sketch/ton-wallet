import os
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from flask import Flask
from .extensions import db, migrate
from config import config_by_name


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    _setup_logging(app)
    _register_routes(app)
    _register_error_handlers(app)
    _register_context_processors(app)
    _register_filters(app)

    with app.app_context():
        from . import models
        db.create_all()

    return app


def _setup_logging(app):
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _register_routes(app):
    from .routes.wallet import wallet_bp
    from .routes.dashboard import dashboard_bp
    from .routes.transactions import transactions_bp
    from .routes.api import api_bp

    app.register_blueprint(wallet_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(api_bp)


def _register_error_handlers(app):
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", error="Page not found", code=404), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", error="Internal server error", code=500), 500


def _register_context_processors(app):
    @app.context_processor
    def inject_get_active_wallet():
        from .models import AppSetting
        def get_active_wallet():
            return AppSetting.get_active_wallet()
        return dict(get_active_wallet=get_active_wallet)


def _register_filters(app):
    def serialize_tx(tx):
        return json.dumps({
            "tx_hash": tx.tx_hash,
            "lt": tx.lt,
            "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
            "direction": tx.direction,
            "asset_symbol": tx.asset_symbol,
            "amount": float(tx.amount) if tx.amount else 0,
            "fee": float(tx.fee) if tx.fee else 0,
            "sender": tx.sender or "",
            "receiver": tx.receiver or "",
            "comment": tx.comment or "",
            "status": tx.status,
            "explorer_url": tx.explorer_url,
        })

    app.jinja_env.filters["serialize_tx"] = serialize_tx
