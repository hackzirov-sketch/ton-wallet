from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, extract

from app.extensions import db
from app.models import Transaction


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def get_total_incoming(wallet_address: str, asset: str = None) -> Decimal:
    txs = Transaction.query.filter_by(
        wallet_address=wallet_address,
        direction="IN",
    )
    if asset:
        txs = txs.filter_by(asset_symbol=asset)
    total = Decimal("0")
    for tx in txs.all():
        total += tx.amount or Decimal("0")
    return total


def get_total_outgoing(wallet_address: str, asset: str = None) -> Decimal:
    txs = Transaction.query.filter_by(
        wallet_address=wallet_address,
        direction="OUT",
    )
    if asset:
        txs = txs.filter_by(asset_symbol=asset)
    total = Decimal("0")
    for tx in txs.all():
        total += tx.amount or Decimal("0")
    return total


def get_total_fees(wallet_address: str) -> Decimal:
    txs = Transaction.query.filter_by(wallet_address=wallet_address)
    total = Decimal("0")
    for tx in txs.all():
        total += tx.fee or Decimal("0")
    return total


def get_net_cash_flow(wallet_address: str) -> Decimal:
    incoming = get_total_incoming(wallet_address)
    outgoing = get_total_outgoing(wallet_address)
    return incoming - outgoing


def get_transaction_count(wallet_address: str) -> int:
    return db.session.query(func.count(Transaction.id)).filter(
        Transaction.wallet_address == wallet_address,
    ).scalar() or 0


def get_largest_incoming(wallet_address: str) -> Optional[Transaction]:
    return Transaction.query.filter_by(
        wallet_address=wallet_address, direction="IN"
    ).order_by(Transaction.amount.desc()).first()


def get_largest_outgoing(wallet_address: str) -> Optional[Transaction]:
    return Transaction.query.filter_by(
        wallet_address=wallet_address, direction="OUT"
    ).order_by(Transaction.amount.desc()).first()


def get_average_incoming(wallet_address: str) -> Decimal:
    count = db.session.query(func.count(Transaction.id)).filter(
        Transaction.wallet_address == wallet_address,
        Transaction.direction == "IN",
    ).scalar() or 0
    if count == 0:
        return Decimal("0")
    total = get_total_incoming(wallet_address)
    return total / Decimal(str(count))


def get_average_outgoing(wallet_address: str) -> Decimal:
    count = db.session.query(func.count(Transaction.id)).filter(
        Transaction.wallet_address == wallet_address,
        Transaction.direction == "OUT",
    ).scalar() or 0
    if count == 0:
        return Decimal("0")
    total = get_total_outgoing(wallet_address)
    return total / Decimal(str(count))


def get_first_transaction_date(wallet_address: str) -> Optional[datetime]:
    tx = Transaction.query.filter_by(wallet_address=wallet_address).order_by(
        Transaction.timestamp.asc()
    ).first()
    return tx.timestamp if tx else None


def get_latest_transaction_date(wallet_address: str) -> Optional[datetime]:
    tx = Transaction.query.filter_by(wallet_address=wallet_address).order_by(
        Transaction.timestamp.desc()
    ).first()
    return tx.timestamp if tx else None


def get_active_days(wallet_address: str) -> int:
    result = db.session.query(
        func.count(func.distinct(func.date(Transaction.timestamp)))
    ).filter(
        Transaction.wallet_address == wallet_address,
    ).scalar()
    return result or 0


def get_monthly_flow(wallet_address: str) -> list:
    rows = db.session.query(
        extract("year", Transaction.timestamp).label("year"),
        extract("month", Transaction.timestamp).label("month"),
        func.sum(Transaction.amount).label("total_amount"),
        Transaction.direction,
    ).filter(
        Transaction.wallet_address == wallet_address,
        Transaction.direction.in_(["IN", "OUT"]),
    ).group_by(
        extract("year", Transaction.timestamp),
        extract("month", Transaction.timestamp),
        Transaction.direction,
    ).all()

    monthly = {}
    for row in rows:
        key = (int(row.year), int(row.month))
        if key not in monthly:
            monthly[key] = {"incoming": Decimal("0"), "outgoing": Decimal("0")}
        amt = Decimal(str(row.total_amount))
        if row.direction == "IN":
            monthly[key]["incoming"] += amt
        else:
            monthly[key]["outgoing"] += amt

    result = []
    for (y, m) in sorted(monthly.keys()):
        data = monthly[(y, m)]
        result.append({
            "year": y,
            "month": m,
            "label": f"{y}-{m:02d}",
            "incoming": float(data["incoming"]),
            "outgoing": float(data["outgoing"]),
            "net": float(data["incoming"] - data["outgoing"]),
        })

    return result


def get_activity_history(wallet_address: str, days: int = 30) -> list:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.session.query(
        func.date(Transaction.timestamp).label("date"),
        func.count(Transaction.id).label("count"),
        Transaction.direction,
    ).filter(
        Transaction.wallet_address == wallet_address,
        Transaction.timestamp >= since,
    ).group_by(
        func.date(Transaction.timestamp),
        Transaction.direction,
    ).all()

    daily = {}
    for row in rows:
        date_str = str(row.date)
        if date_str not in daily:
            daily[date_str] = {"date": date_str, "incoming": 0, "outgoing": 0, "total": 0}
        if row.direction == "IN":
            daily[date_str]["incoming"] = row.count
        elif row.direction == "OUT":
            daily[date_str]["outgoing"] = row.count
        daily[date_str]["total"] += row.count

    result = []
    current = since.date()
    end = datetime.now(timezone.utc).date()
    while current <= end:
        ds = current.isoformat()
        if ds not in daily:
            daily[ds] = {"date": ds, "incoming": 0, "outgoing": 0, "total": 0}
        result.append(daily[ds])
        current += timedelta(days=1)

    return result


def get_dashboard_stats(wallet_address: str) -> dict:
    incoming = get_total_incoming(wallet_address)
    outgoing = get_total_outgoing(wallet_address)
    fees = get_total_fees(wallet_address)
    net = incoming - outgoing
    count = get_transaction_count(wallet_address)
    largest_in = get_largest_incoming(wallet_address)
    largest_out = get_largest_outgoing(wallet_address)
    avg_in = get_average_incoming(wallet_address)
    avg_out = get_average_outgoing(wallet_address)
    first_date = get_first_transaction_date(wallet_address)
    last_date = get_latest_transaction_date(wallet_address)
    active_days = get_active_days(wallet_address)

    return {
        "total_incoming": incoming,
        "total_outgoing": outgoing,
        "total_fees": fees,
        "net_cash_flow": net,
        "transaction_count": count,
        "largest_incoming": largest_in.amount if largest_in else Decimal("0"),
        "largest_outgoing": largest_out.amount if largest_out else Decimal("0"),
        "average_incoming": avg_in,
        "average_outgoing": avg_out,
        "first_transaction_date": first_date,
        "latest_transaction_date": last_date,
        "active_days": active_days,
    }
