from flask import Blueprint, jsonify, request, current_app
from app.models import AppSetting, Transaction, SyncLog
from app.services.analytics import (
    get_dashboard_stats, get_monthly_flow, get_activity_history,
    get_total_incoming, get_total_outgoing, get_net_cash_flow, get_transaction_count,
)
from app.services.wallet_sync import sync_wallet, sync_incremental
from app.services.price_service import PriceService
from app.extensions import db
from decimal import Decimal

api_bp = Blueprint("api", __name__, url_prefix="/api")


class DecimalEncoder:
    @staticmethod
    def default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _json_response(data, status=200):
    import json

    class DEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Decimal):
                return float(o)
            if hasattr(o, "isoformat"):
                return o.isoformat()
            return super().default(o)

    return current_app.response_class(
        json.dumps(data, cls=DEncoder, default=str),
        mimetype="application/json",
        status=status,
    )


@api_bp.route("/dashboard")
def dashboard_data():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    wallet = setting.wallet_address
    stats = get_dashboard_stats(wallet)

    price_svc = PriceService(
        base_url=current_app.config.get("PRICE_API_BASE_URL", ""),
        api_key=current_app.config.get("PRICE_API_KEY", ""),
    )

    price_data = {"available": False}
    try:
        from app.routes.dashboard import _get_current_balance
        balance = _get_current_balance(wallet, current_app.config)
        price_data = price_svc.get_wallet_value(balance)
    except Exception:
        pass

    return _json_response({
        "wallet": wallet,
        "stats": {k: float(v) if isinstance(v, Decimal) else v for k, v in stats.items()},
        "price": price_data,
        "last_sync": setting.last_sync_at.isoformat() if setting.last_sync_at else None,
    })


@api_bp.route("/transactions")
def transactions_data():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    wallet = setting.wallet_address
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    direction = request.args.get("direction", "ALL")
    search = request.args.get("search", "")

    q = Transaction.query.filter_by(wallet_address=wallet)

    if direction in ("IN", "OUT", "SELF"):
        q = q.filter(Transaction.direction == direction)

    if search:
        like = f"%{search}%"
        q = q.filter(
            db.or_(
                Transaction.tx_hash.ilike(like),
                Transaction.sender.ilike(like),
                Transaction.receiver.ilike(like),
            )
        )

    total = q.count()
    txs = q.order_by(Transaction.timestamp.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return _json_response({
        "transactions": [_serialize_tx(tx) for tx in txs],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_bp.route("/analytics/monthly")
def monthly_flow():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    data = get_monthly_flow(setting.wallet_address)
    return _json_response({"monthly_flow": data})


@api_bp.route("/analytics/activity")
def activity_data():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    days = request.args.get("days", 30, type=int)
    data = get_activity_history(setting.wallet_address, days=days)
    return _json_response({"activity": data})


@api_bp.route("/sync", methods=["POST"])
def trigger_sync():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    try:
        result = sync_incremental(setting.wallet_address, current_app.config)
        return _json_response({"status": "success", "result": result})
    except Exception as e:
        return _json_response({"status": "error", "message": str(e)}, 500)


@api_bp.route("/analytics/summary")
def analytics_summary():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return _json_response({"error": "No wallet configured"}, 404)

    wallet = setting.wallet_address
    stats = get_dashboard_stats(wallet)
    monthly = get_monthly_flow(wallet)

    return _json_response({
        "stats": {k: float(v) if isinstance(v, Decimal) else v for k, v in stats.items()},
        "monthly_flow": monthly,
    })


def _serialize_tx(tx):
    return {
        "id": tx.id,
        "tx_hash": tx.tx_hash,
        "lt": tx.lt,
        "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
        "direction": tx.direction,
        "asset_symbol": tx.asset_symbol,
        "amount": float(tx.amount) if tx.amount else 0,
        "fee": float(tx.fee) if tx.fee else 0,
        "sender": tx.sender,
        "receiver": tx.receiver,
        "comment": tx.comment,
        "status": tx.status,
        "explorer_url": tx.explorer_url,
    }
