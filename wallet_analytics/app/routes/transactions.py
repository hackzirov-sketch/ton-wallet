from flask import Blueprint, render_template, redirect, url_for, request, current_app
from app.models import AppSetting, Transaction
from app.services.analytics import get_dashboard_stats
from app.services.ton_utils import truncate_address, explorer_url
from app.extensions import db
import math

transactions_bp = Blueprint("transactions", __name__)

PAGE_SIZES = [25, 50, 100]


@transactions_bp.route("/transactions")
def index():
    setting = AppSetting.get_active_wallet()
    if not setting:
        return redirect(url_for("wallet.setup"))

    wallet = setting.wallet_address

    direction = request.args.get("direction", "ALL")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search", "").strip()
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    if per_page not in PAGE_SIZES:
        per_page = 50

    q = Transaction.query.filter_by(wallet_address=wallet)

    if direction in ("IN", "OUT", "SELF", "UNKNOWN"):
        q = q.filter(Transaction.direction == direction)

    if search:
        like = f"%{search}%"
        q = q.filter(
            db.or_(
                Transaction.tx_hash.ilike(like),
                Transaction.sender.ilike(like),
                Transaction.receiver.ilike(like),
                Transaction.comment.ilike(like),
            )
        )

    if min_amount is not None:
        q = q.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        q = q.filter(Transaction.amount <= max_amount)

    if date_from:
        try:
            from datetime import datetime
            dt_from = datetime.fromisoformat(date_from)
            q = q.filter(Transaction.timestamp >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            dt_to = datetime.fromisoformat(date_to)
            q = q.filter(Transaction.timestamp <= dt_to)
        except ValueError:
            pass

    total = q.count()
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    page = max(1, min(page, total_pages))

    txs = q.order_by(Transaction.timestamp.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return render_template(
        "transactions.html",
        wallet=wallet,
        truncated_wallet=truncate_address(wallet),
        explorer_url=explorer_url(wallet),
        transactions=txs,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        page_sizes=PAGE_SIZES,
        direction=direction,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
        date_from=date_from,
        date_to=date_to,
    )
