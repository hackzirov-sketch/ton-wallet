import logging
import base64
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.models import Transaction, SyncLog, AppSetting
from .ton_client import TONClient, TONClientError

logger = logging.getLogger(__name__)

NANO_TON = Decimal("1000000000")


def _nano_to_ton(nano_value) -> Decimal:
    if nano_value is None:
        return Decimal("0")
    return Decimal(str(nano_value)) / NANO_TON


def _parse_timestamp(ts) -> datetime:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return datetime.now(timezone.utc)


def _normalize_address(address: str) -> str:
    if not address:
        return ""
    clean = address.strip().replace("-", "+").replace("_", "/")
    try:
        raw = base64.b64decode(clean)
        return raw.hex().lower()
    except Exception:
        return address.lower().strip()


def _classify_direction(tx: dict, wallet_address: str) -> str:
    in_msg = tx.get("in_msg", {})
    out_msgs = tx.get("out_msgs", [])

    wallet_norm = _normalize_address(wallet_address)

    in_source = in_msg.get("source", "")
    in_dest = in_msg.get("destination", "")
    in_source_norm = _normalize_address(in_source)
    in_dest_norm = _normalize_address(in_dest)

    has_outgoing = False
    for m in out_msgs:
        dest = m.get("destination", "")
        dest_norm = _normalize_address(dest)
        if dest_norm and dest_norm != wallet_norm and m.get("value", 0) > 0:
            has_outgoing = True
            break

    if has_outgoing:
        return "OUT"

    if in_source_norm and in_source_norm == wallet_norm:
        if in_dest_norm and in_dest_norm == wallet_norm:
            return "SELF"
        return "SELF"

    if in_msg and in_msg.get("value", 0) > 0:
        if in_dest_norm and in_dest_norm == wallet_norm:
            return "IN"

    if in_msg and in_msg.get("value", 0) > 0:
        return "IN"

    return "UNKNOWN"


def _extract_amount(tx: dict, direction: str, wallet_address: str) -> Decimal:
    in_msg = tx.get("in_msg", {})
    out_msgs = tx.get("out_msgs", [])
    wallet_norm = _normalize_address(wallet_address)

    if direction == "IN":
        return _nano_to_ton(in_msg.get("value", 0))
    elif direction == "OUT":
        total = Decimal("0")
        for m in out_msgs:
            dest = m.get("destination", "")
            dest_norm = _normalize_address(dest)
            if dest_norm and dest_norm != wallet_norm:
                total += _nano_to_ton(m.get("value", 0))
        return total
    elif direction == "SELF":
        return _nano_to_ton(in_msg.get("value", 0))
    return Decimal("0")


def _extract_fee(tx: dict) -> Decimal:
    fee = tx.get("fee", 0)
    return _nano_to_ton(fee)


def _extract_comment(tx: dict) -> Optional[str]:
    in_msg = tx.get("in_msg", {})
    msg = in_msg.get("message", {})
    if isinstance(msg, dict):
        text = msg.get("text", "")
    elif isinstance(msg, str):
        text = msg
    else:
        text = ""
    return text if text else None


def _store_transactions(wallet_address: str, raw_transactions: list) -> int:
    added = 0
    wallet_norm = _normalize_address(wallet_address)
    logger.info("Storing %d raw transactions for %s", len(raw_transactions), wallet_address[:20])

    for tx in raw_transactions:
        tx_hash = tx.get("hash", "")
        lt = tx.get("lt")
        if not tx_hash:
            continue

        direction = _classify_direction(tx, wallet_address)
        amount = _extract_amount(tx, direction, wallet_address)
        fee = _extract_fee(tx)
        comment = _extract_comment(tx)
        timestamp = _parse_timestamp(tx.get("now", 0))

        in_msg = tx.get("in_msg", {})
        out_msgs = tx.get("out_msgs", [])
        sender = in_msg.get("source", "")
        receiver = ""
        for m in out_msgs:
            dest = m.get("destination", "")
            dest_norm = _normalize_address(dest)
            if dest_norm and dest_norm != wallet_norm:
                receiver = dest
                break

        existing = Transaction.query.filter_by(
            tx_hash=tx_hash, wallet_address=wallet_address
        ).first()
        if existing:
            continue

        record = Transaction(
            tx_hash=tx_hash,
            lt=lt,
            wallet_address=wallet_address,
            timestamp=timestamp,
            direction=direction,
            asset_symbol="TON",
            amount=amount,
            fee=fee,
            sender=sender,
            receiver=receiver,
            comment=comment,
            status="SUCCESS",
            raw_type=tx.get("type", ""),
        )
        db.session.add(record)
        added += 1

    if added > 0:
        db.session.commit()

    return added


def sync_wallet(wallet_address: str, config) -> dict:
    setting = AppSetting.get_active_wallet()
    if not setting:
        setting = AppSetting.set_wallet(wallet_address)

    sync_log = SyncLog(
        wallet_address=wallet_address,
        status="RUNNING",
    )
    db.session.add(sync_log)
    db.session.commit()

    try:
        client = TONClient(
            base_url=config.get("TON_API_BASE_URL", "https://toncenter.com/api/v2"),
            timeout=config.get("TON_API_TIMEOUT", 30),
            retries=config.get("TON_API_RETRIES", 3),
        )

        account_info = client.get_account_info(wallet_address)
        balance_nano = account_info.get("balance", 0)

        raw_txs = client.get_all_transactions(wallet_address)
        added = _store_transactions(wallet_address, raw_txs)

        setting.last_sync_at = datetime.now(timezone.utc)
        sync_log.status = "SUCCESS"
        sync_log.transactions_added = added
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()

        return {
            "status": "success",
            "transactions_added": added,
            "total_fetched": len(raw_txs),
            "balance_nano": balance_nano,
        }

    except TONClientError as e:
        logger.error("TON API error during sync: %s", e)
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise
    except Exception as e:
        logger.exception("Unexpected error during sync: %s", e)
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise


def sync_incremental(wallet_address: str, config) -> dict:
    setting = AppSetting.get_active_wallet()
    if not setting:
        return sync_wallet(wallet_address, config)

    latest_tx = Transaction.query.filter_by(
        wallet_address=wallet_address
    ).order_by(Transaction.lt.desc()).first()

    sync_log = SyncLog(
        wallet_address=wallet_address,
        status="RUNNING",
    )
    db.session.add(sync_log)
    db.session.commit()

    try:
        client = TONClient(
            base_url=config.get("TON_API_BASE_URL", "https://toncenter.com/api/v2"),
            timeout=config.get("TON_API_TIMEOUT", 30),
            retries=config.get("TON_API_RETRIES", 3),
        )

        params = {"limit": 100}
        if latest_tx and latest_tx.lt:
            params["before_lt"] = latest_tx.lt

        raw_txs = client.get_transactions(wallet_address, **params)
        added = _store_transactions(wallet_address, raw_txs)

        setting.last_sync_at = datetime.now(timezone.utc)
        sync_log.status = "SUCCESS" if added > 0 else "PARTIAL"
        sync_log.transactions_added = added
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()

        return {
            "status": "success",
            "transactions_added": added,
            "total_fetched": len(raw_txs),
        }

    except TONClientError as e:
        logger.error("Incremental sync error: %s", e)
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise
    except Exception as e:
        logger.exception("Unexpected error during incremental sync: %s", e)
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise
