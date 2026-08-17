import logging
from decimal import Decimal
from datetime import datetime, timezone
import requests

from app.extensions import db
from app.models import PriceSnapshot

logger = logging.getLogger(__name__)


class PriceService:
    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def get_ton_price(self) -> dict:
        if not self.base_url:
            return {"price_usd": None, "available": False}

        try:
            resp = requests.get(
                f"{self.base_url}/simple/price",
                params={
                    "ids": "the-open-network",
                    "vs_currencies": "usd",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            price = data.get("the-open-network", {}).get("usd")

            if price is not None:
                snapshot = PriceSnapshot(
                    symbol="TON",
                    price_usd=Decimal(str(price)),
                )
                db.session.add(snapshot)
                db.session.commit()

            return {"price_usd": price, "available": True}
        except Exception as e:
            logger.error("Failed to fetch TON price: %s", e)
            return {"price_usd": None, "available": False}

    def get_wallet_value(self, balance_ton: Decimal) -> dict:
        price_data = self.get_ton_price()
        if price_data["available"] and price_data["price_usd"] is not None:
            price = Decimal(str(price_data["price_usd"]))
            value = balance_ton * price
            return {
                "price_usd": float(price),
                "value_usd": float(value),
                "available": True,
            }
        return {"price_usd": None, "value_usd": None, "available": False}
