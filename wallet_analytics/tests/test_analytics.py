import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app.models import Transaction
from app.services.analytics import (
    get_total_incoming, get_total_outgoing, get_net_cash_flow,
    get_transaction_count, get_largest_incoming, get_largest_outgoing,
    get_average_incoming, get_average_outgoing, get_monthly_flow,
    get_active_days, get_total_fees,
)


WALLET = "EQDtest123"


def _add_tx(db, direction, amount, fee="0.001", timestamp=None):
    tx = Transaction(
        tx_hash=f"hash_{direction}_{amount}",
        wallet_address=WALLET,
        timestamp=timestamp or datetime(2025, 1, 15, tzinfo=timezone.utc),
        direction=direction,
        asset_symbol="TON",
        amount=Decimal(str(amount)),
        fee=Decimal(str(fee)),
        sender="sender1" if direction in ("IN", "SELF") else "sender2",
        receiver="receiver1" if direction in ("OUT", "SELF") else "receiver2",
        status="SUCCESS",
    )
    db.session.add(tx)
    db.session.commit()


class TestAnalyticsIncoming:
    def test_incoming_only(self, db):
        _add_tx(db, "IN", 10.5)
        _add_tx(db, "IN", 5.25)
        result = get_total_incoming(WALLET)
        assert result == Decimal("15.75")

    def test_zero_incoming(self, db):
        _add_tx(db, "OUT", 5.0)
        result = get_total_incoming(WALLET)
        assert result == Decimal("0")

    def test_empty_wallet(self, db):
        result = get_total_incoming(WALLET)
        assert result == Decimal("0")


class TestAnalyticsOutgoing:
    def test_outgoing_only(self, db):
        _add_tx(db, "OUT", 3.0)
        _add_tx(db, "OUT", 2.5)
        result = get_total_outgoing(WALLET)
        assert result == Decimal("5.5")

    def test_zero_outgoing(self, db):
        _add_tx(db, "IN", 5.0)
        result = get_total_outgoing(WALLET)
        assert result == Decimal("0")


class TestNetCashFlow:
    def test_positive_net(self, db):
        _add_tx(db, "IN", 10.0)
        _add_tx(db, "OUT", 3.0)
        result = get_net_cash_flow(WALLET)
        assert result == Decimal("7")

    def test_negative_net(self, db):
        _add_tx(db, "IN", 2.0)
        _add_tx(db, "OUT", 5.0)
        result = get_net_cash_flow(WALLET)
        assert result == Decimal("-3")

    def test_zero_net(self, db):
        _add_tx(db, "IN", 5.0)
        _add_tx(db, "OUT", 5.0)
        result = get_net_cash_flow(WALLET)
        assert result == Decimal("0")

    def test_empty_wallet(self, db):
        result = get_net_cash_flow(WALLET)
        assert result == Decimal("0")


class TestTransactionCount:
    def test_count(self, db):
        _add_tx(db, "IN", 1.0)
        _add_tx(db, "OUT", 2.0)
        _add_tx(db, "SELF", 3.0)
        assert get_transaction_count(WALLET) == 3

    def test_empty(self, db):
        assert get_transaction_count(WALLET) == 0


class TestLargestTransaction:
    def test_largest_incoming(self, db):
        _add_tx(db, "IN", 5.0)
        _add_tx(db, "IN", 15.0)
        _add_tx(db, "IN", 10.0)
        result = get_largest_incoming(WALLET)
        assert result.amount == Decimal("15")

    def test_largest_outgoing(self, db):
        _add_tx(db, "OUT", 2.0)
        _add_tx(db, "OUT", 8.0)
        result = get_largest_outgoing(WALLET)
        assert result.amount == Decimal("8")

    def test_no_incoming(self, db):
        _add_tx(db, "OUT", 5.0)
        assert get_largest_incoming(WALLET) is None


class TestAverage:
    def test_average_incoming(self, db):
        _add_tx(db, "IN", 4.0)
        _add_tx(db, "IN", 6.0)
        result = get_average_incoming(WALLET)
        assert result == Decimal("5")

    def test_average_outgoing(self, db):
        _add_tx(db, "OUT", 3.0)
        _add_tx(db, "OUT", 7.0)
        result = get_average_outgoing(WALLET)
        assert result == Decimal("5")

    def test_average_zero(self, db):
        result = get_average_incoming(WALLET)
        assert result == Decimal("0")


class TestDecimalPrecision:
    def test_precise_amounts(self, db):
        _add_tx(db, "IN", "1.123456789")
        _add_tx(db, "IN", "2.876543211")
        result = get_total_incoming(WALLET)
        expected = Decimal("1.123456789") + Decimal("2.876543211")
        assert result == expected

    def test_returns_decimal_type(self, db):
        _add_tx(db, "IN", "42.5")
        result = get_total_incoming(WALLET)
        assert isinstance(result, Decimal)
        assert result == Decimal("42.5")

    def test_zero_precision(self, db):
        _add_tx(db, "IN", "0.000001")
        _add_tx(db, "IN", "0.000002")
        result = get_total_incoming(WALLET)
        assert isinstance(result, Decimal)


class TestMonthlyFlow:
    def test_monthly_flow(self, db):
        _add_tx(db, "IN", 10.0, timestamp=datetime(2025, 1, 10, tzinfo=timezone.utc))
        _add_tx(db, "OUT", 3.0, timestamp=datetime(2025, 1, 20, tzinfo=timezone.utc))
        _add_tx(db, "IN", 5.0, timestamp=datetime(2025, 2, 5, tzinfo=timezone.utc))

        result = get_monthly_flow(WALLET)
        assert len(result) == 2
        assert result[0]["incoming"] == 10.0
        assert result[0]["outgoing"] == 3.0
        assert result[1]["incoming"] == 5.0


class TestActiveDays:
    def test_active_days(self, db):
        _add_tx(db, "IN", 1.0, timestamp=datetime(2025, 1, 10, tzinfo=timezone.utc))
        _add_tx(db, "IN", 2.0, timestamp=datetime(2025, 1, 10, 12, tzinfo=timezone.utc))
        _add_tx(db, "IN", 3.0, timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc))
        assert get_active_days(WALLET) == 2


class TestFees:
    def test_total_fees(self, db):
        _add_tx(db, "IN", 10.0, fee="0.005")
        _add_tx(db, "OUT", 5.0, fee="0.003")
        result = get_total_fees(WALLET)
        assert result == Decimal("0.008")
