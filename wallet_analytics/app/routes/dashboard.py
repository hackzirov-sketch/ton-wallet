from flask import Blueprint, render_template, redirect, url_for, current_app
from app.models import AppSetting
from app.services.analytics import get_dashboard_stats
from app.services.wallet_sync import sync_incremental
from app.services.price_service import PriceService
from app.services.ton_utils import truncate_address, explorer_url
from decimal import Decimal

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return redirect(url_for("wallet.setup"))

    if not setting.last_sync_at:
        return redirect(url_for("wallet.setup"))

    wallet = setting.wallet_address
    stats = get_dashboard_stats(wallet)

    price_svc = PriceService(
        base_url=current_app.config.get("PRICE_API_BASE_URL", ""),
        api_key=current_app.config.get("PRICE_API_KEY", ""),
    )

    price_data = {"available": False}
    try:
        balance_ton = _get_current_balance(wallet, current_app.config)
        price_data = price_svc.get_wallet_value(balance_ton)
    except Exception:
        pass

    truncated = truncate_address(wallet)
    explorer = explorer_url(wallet)

    return render_template(
        "dashboard.html",
        wallet=wallet,
        truncated_wallet=truncated,
        explorer_url=explorer,
        stats=stats,
        price_data=price_data,
        last_sync=setting.last_sync_at,
    )


def _get_current_balance(wallet_address, config):
    from app.services.ton_client import TONClient
    try:
        client = TONClient(
            base_url=config.get("TON_API_BASE_URL", "https://toncenter.com/api/v2"),
            timeout=config.get("TON_API_TIMEOUT", 30),
            retries=2,
        )
        info = client.get_balance(wallet_address)
        from decimal import Decimal
        return Decimal(str(info.get("balance", 0))) / Decimal("1000000000")
    except Exception:
        return Decimal("0")
