import pytest
from app.services.ton_utils import validate_ton_address, normalize_address, truncate_address


class TestWalletValidation:
    def test_valid_eq_address(self):
        addr = "EQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn"
        assert validate_ton_address(addr) is True

    def test_valid_uq_address(self):
        addr = "UQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn"
        assert validate_ton_address(addr) is True

    def test_empty_address(self):
        assert validate_ton_address("") is False

    def test_none_address(self):
        assert validate_ton_address(None) is False

    def test_short_address(self):
        assert validate_ton_address("EQshort") is False

    def test_invalid_prefix(self):
        addr = "XQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn"
        assert validate_ton_address(addr) is False

    def test_invalid_chars(self):
        addr = "EQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1d!"
        assert validate_ton_address(addr) is False

    def test_too_long(self):
        addr = "EQD" + "a" * 100
        assert validate_ton_address(addr) is False

    def test_whitespace_stripped(self):
        addr = "  EQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn  "
        assert validate_ton_address(addr) is True

    def test_invalid_with_spaces(self):
        addr = "EQD 4aW BQb"
        assert validate_ton_address(addr) is False


class TestNormalizeAddress:
    def test_strips_whitespace(self):
        assert normalize_address("  EQabc  ") == "EQabc"

    def test_empty_string(self):
        assert normalize_address("") == ""

    def test_none(self):
        assert normalize_address(None) == ""


class TestTruncateAddress:
    def test_normal_truncation(self):
        addr = "EQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn"
        result = truncate_address(addr)
        assert "..." in result
        assert result.startswith("EQD4aW")
        assert result.endswith("YP1dn")

    def test_short_address(self):
        addr = "EQabc"
        result = truncate_address(addr)
        assert result == addr


class TestWalletSetupRoute:
    def test_setup_page_loads(self, client, db):
        resp = client.get("/setup")
        assert resp.status_code == 200
        assert b"Hamyorni ulash" in resp.data

    def test_setup_redirects_if_wallet_set(self, client, db):
        from app.models import AppSetting
        from datetime import datetime, timezone
        setting = AppSetting.set_wallet("EQD4aWBQbA8rZDf0rOBfPk4WKjiMUBi3pSa7a1fiv8qYP1dn")
        setting.last_sync_at = datetime.now(timezone.utc)
        from app.extensions import db as _db
        _db.session.commit()
        resp = client.get("/setup", follow_redirects=False)
        assert resp.status_code == 302

    def test_setup_rejects_invalid_address(self, client, db):
        resp = client.post("/setup", data={"wallet_address": "invalid"}, follow_redirects=True)
        assert b"TON hamyor manzili" in resp.data

    def test_dashboard_redirects_without_wallet(self, client, db):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
