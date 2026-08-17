import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone
from app.models import Transaction, AppSetting, SyncLog
from app.services.wallet_sync import sync_wallet, _classify_direction, _nano_to_ton, _store_transactions


WALLET = "EQDsync_test_wallet"


class TestNanoToTon:
    def test_conversion(self):
        assert _nano_to_ton(1000000000) == Decimal("1")

    def test_zero(self):
        assert _nano_to_ton(0) == Decimal("0")

    def test_none(self):
        assert _nano_to_ton(None) == Decimal("0")

    def test_large_value(self):
        assert _nano_to_ton(150000000000) == Decimal("150")


class TestDuplicatePrevention:
    def test_duplicates_ignored(self, db):
        raw_txs = [
            {
                "hash": "dup1",
                "lt": 100,
                "now": 1700000000,
                "fee": 1000,
                "type": "internal",
                "in_msg": {"source": "EQsender", "destination": WALLET, "value": 500000000, "message": {"text": ""}},
                "out_msgs": [],
            },
        ]
        added1 = _store_transactions(WALLET, raw_txs)
        assert added1 == 1

        added2 = _store_transactions(WALLET, raw_txs)
        assert added2 == 0

        total = Transaction.query.filter_by(wallet_address=WALLET).count()
        assert total == 1


class TestSyncWithMock:
    @patch("app.services.wallet_sync.TONClient")
    def test_sync_stores_transactions(self, MockClient, db, app):
        mock_client = MockClient.return_value
        mock_client.get_account_info.return_value = {"balance": 5000000000}
        mock_client.get_all_transactions.return_value = [
            {
                "hash": "sync_tx1",
                "lt": 200,
                "now": 1700000000,
                "fee": 5000,
                "type": "internal",
                "in_msg": {"source": "EQsender", "destination": WALLET, "value": 2000000000, "message": {"text": "hello"}},
                "out_msgs": [],
            },
            {
                "hash": "sync_tx2",
                "lt": 201,
                "now": 1700000100,
                "fee": 3000,
                "type": "internal",
                "in_msg": {"source": WALLET, "destination": WALLET, "value": 1000000000, "message": {"text": ""}},
                "out_msgs": [{"destination": "EQreceiver", "value": 800000000}],
            },
        ]

        AppSetting.set_wallet(WALLET)
        result = sync_wallet(WALLET, app.config)

        assert result["status"] == "success"
        assert result["total_fetched"] == 2

        txs = Transaction.query.filter_by(wallet_address=WALLET).all()
        assert len(txs) == 2

        sync_logs = SyncLog.query.filter_by(wallet_address=WALLET).all()
        assert len(sync_logs) == 1
        assert sync_logs[0].status == "SUCCESS"

    @patch("app.services.wallet_sync.TONClient")
    def test_sync_api_failure(self, MockClient, db, app):
        from app.services.ton_client import TONClientError
        mock_client = MockClient.return_value
        mock_client.get_account_info.side_effect = TONClientError("API down")

        AppSetting.set_wallet(WALLET)

        with pytest.raises(TONClientError):
            sync_wallet(WALLET, app.config)

        sync_logs = SyncLog.query.filter_by(wallet_address=WALLET).all()
        assert len(sync_logs) == 1
        assert sync_logs[0].status == "FAILED"

    @patch("app.services.wallet_sync.TONClient")
    def test_sync_partial_failure(self, MockClient, db, app):
        from app.services.ton_client import TONClientError
        mock_client = MockClient.return_value
        mock_client.get_account_info.side_effect = TONClientError("Timeout")

        AppSetting.set_wallet(WALLET)

        with pytest.raises(TONClientError):
            sync_wallet(WALLET, app.config)

        logs = SyncLog.query.filter_by(wallet_address=WALLET, status="FAILED").all()
        assert len(logs) == 1


class TestTransactionPagination:
    def test_pagination(self, db, client):
        AppSetting.set_wallet(WALLET)

        for i in range(60):
            tx = Transaction(
                tx_hash=f"page_tx_{i}",
                wallet_address=WALLET,
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                direction="IN" if i % 2 == 0 else "OUT",
                amount=Decimal(str(i + 1)),
                fee=Decimal("0.001"),
                status="SUCCESS",
            )
            db.session.add(tx)
        db.session.commit()

        resp = client.get("/transactions?per_page=25&page=1")
        assert resp.status_code == 200

        resp = client.get("/api/transactions?per_page=25&page=2")
        assert resp.status_code == 200
        import json
        data = json.loads(resp.data)
        assert data["total"] == 60


class TestApiSyncEndpoint:
    @patch("app.services.wallet_sync.TONClient")
    def test_api_sync(self, MockClient, db, client, app):
        mock_client = MockClient.return_value
        mock_client.get_account_info.return_value = {"balance": 1000000000}
        mock_client.get_transactions.return_value = []

        AppSetting.set_wallet(WALLET)

        resp = client.post("/api/sync")
        assert resp.status_code == 200
        import json
        data = json.loads(resp.data)
        assert data["status"] == "success"
