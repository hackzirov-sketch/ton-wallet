import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app.models import Transaction, AppSetting


WALLET = "EQDtest456"


class TestTransactionModel:
    def test_create_transaction(self, db):
        tx = Transaction(
            tx_hash="abc123",
            wallet_address=WALLET,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            direction="IN",
            amount=Decimal("10.5"),
            fee=Decimal("0.001"),
            sender="sender_addr",
            receiver="receiver_addr",
            status="SUCCESS",
        )
        db.session.add(tx)
        db.session.commit()

        loaded = Transaction.query.filter_by(tx_hash="abc123").first()
        assert loaded is not None
        assert loaded.amount == Decimal("10.5")
        assert loaded.direction == "IN"

    def test_unique_constraint(self, db):
        tx1 = Transaction(
            tx_hash="dup_hash",
            wallet_address=WALLET,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            direction="IN",
            amount=Decimal("1"),
            status="SUCCESS",
        )
        db.session.add(tx1)
        db.session.commit()

        tx2 = Transaction(
            tx_hash="dup_hash",
            wallet_address=WALLET,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            direction="OUT",
            amount=Decimal("2"),
            status="SUCCESS",
        )
        db.session.add(tx2)
        with pytest.raises(Exception):
            db.session.commit()

    def test_explorer_url(self, db):
        tx = Transaction(
            tx_hash="test_hash_789",
            wallet_address=WALLET,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            direction="IN",
            amount=Decimal("1"),
            status="SUCCESS",
        )
        assert "test_hash_789" in tx.explorer_url


class TestAppSetting:
    def test_set_wallet(self, db):
        setting = AppSetting.set_wallet("EQDnewwallet")
        assert setting.wallet_address == "EQDnewwallet"

    def test_get_active_wallet(self, db):
        AppSetting.set_wallet("EQDactive")
        active = AppSetting.get_active_wallet()
        assert active.wallet_address == "EQDactive"

    def test_replace_wallet(self, db):
        AppSetting.set_wallet("EQDfirst")
        AppSetting.set_wallet("EQDsecond")
        active = AppSetting.get_active_wallet()
        assert active.wallet_address == "EQDsecond"
        assert AppSetting.query.count() == 1


class TestTransactionDirection:
    def _make_tx(self, in_source, in_dest, in_value, out_dest, out_value):
        tx = {
            "in_msg": {
                "source": in_source,
                "destination": in_dest,
                "value": in_value,
                "message": {"text": ""},
            },
            "out_msgs": [
                {"destination": out_dest, "value": out_value}
            ] if out_dest else [],
            "fee": 1000,
            "now": 1700000000,
            "hash": "tx_hash_test",
            "lt": 12345,
            "type": "internal",
        }
        return tx

    def test_incoming(self):
        from app.services.wallet_sync import _classify_direction
        tx = self._make_tx("EQsender", "EQwallet", 1000000000, "", 0)
        result = _classify_direction(tx, "EQwallet")
        assert result == "IN"

    def test_outgoing(self):
        from app.services.wallet_sync import _classify_direction
        tx = self._make_tx("EQwallet", "EQwallet", 0, "EQreceiver", 500000000)
        result = _classify_direction(tx, "EQwallet")
        assert result == "OUT"

    def test_self(self):
        from app.services.wallet_sync import _classify_direction
        tx = self._make_tx("EQwallet", "EQwallet", 1000000000, "", 0)
        result = _classify_direction(tx, "EQwallet")
        assert result == "SELF"

    def test_unknown(self):
        from app.services.wallet_sync import _classify_direction
        tx = self._make_tx("EQother", "EQother2", 0, "", 0)
        result = _classify_direction(tx, "EQwallet")
        assert result == "UNKNOWN"
