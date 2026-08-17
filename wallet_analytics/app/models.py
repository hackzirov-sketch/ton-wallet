from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_sync_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def get_active_wallet(cls):
        return cls.query.first()

    @classmethod
    def set_wallet(cls, address):
        setting = cls.query.first()
        if setting:
            setting.wallet_address = address
            setting.updated_at = datetime.now(timezone.utc)
            setting.last_sync_at = None
        else:
            setting = cls(wallet_address=address)
            db.session.add(setting)
        db.session.commit()
        return setting


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(128), nullable=False, index=True)
    lt = db.Column(db.BigInteger, nullable=True)
    wallet_address = db.Column(db.String(128), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    direction = db.Column(db.String(10), nullable=False, index=True)
    asset_symbol = db.Column(db.String(32), default="TON")
    asset_address = db.Column(db.String(128), nullable=True, index=True)
    amount = db.Column(db.Numeric(30, 18), nullable=False, default=Decimal("0"))
    fee = db.Column(db.Numeric(30, 18), nullable=False, default=Decimal("0"))
    sender = db.Column(db.String(128), nullable=True)
    receiver = db.Column(db.String(128), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="SUCCESS")
    raw_type = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("tx_hash", "wallet_address", name="uq_tx_wallet"),
    )

    @property
    def explorer_url(self):
        return f"https://tonviewer.com/transaction/{self.tx_hash}"


class SyncLog(db.Model):
    __tablename__ = "sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(128), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="RUNNING")
    transactions_added = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)


class PriceSnapshot(db.Model):
    __tablename__ = "price_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(32), default="TON")
    price_usd = db.Column(db.Numeric(20, 8), nullable=False)
    fetched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
