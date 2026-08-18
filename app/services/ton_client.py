import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TONClientError(Exception):
    pass


class TONClient:
    def __init__(self, base_url: str, timeout: int = 30, retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        retry_strategy = Retry(
            total=retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = self.session.request(method, url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and data.get("ok") is False:
                raise TONClientError(data.get("error", "Unknown API error"))

            return data

        except requests.exceptions.Timeout:
            logger.error("TON API timeout: %s", endpoint)
            raise TONClientError("API request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("TON API connection failed: %s", endpoint)
            raise TONClientError("Cannot connect to TON API")
        except requests.exceptions.HTTPError as e:
            status = resp.status_code if resp is not None else 0
            logger.error("TON API HTTP %s: %s", status, e)
            if status == 429:
                raise TONClientError("Rate limited. Wait a moment.")
            if status == 400:
                raise TONClientError("Invalid request.")
            if status == 404:
                raise TONClientError("Wallet not found.")
            raise TONClientError(f"API error: {status}")
        except ValueError:
            raise TONClientError("Invalid API response")

    def get_balance(self, address: str) -> dict:
        data = self._request("GET", "/getAddressBalance", {"address": address})
        result = data.get("result", {})
        return {
            "balance": int(result.get("balance", 0)),
            "address": address,
        }

    def get_account_info(self, address: str) -> dict:
        data = self._request("GET", "/getAddressInformation", {"address": address})
        result = data.get("result", {})
        return {
            "address": address,
            "balance": int(result.get("balance", 0)),
            "status": result.get("status", "unknown"),
            "last_transaction_lt": result.get("last_transaction_lt"),
            "last_transaction_hash": result.get("last_transaction_hash"),
        }

    def get_transactions(self, address: str, limit: int = 50, before_lt: int = None) -> list:
        params = {
            "address": address,
            "limit": min(limit, 100),
        }
        if before_lt is not None:
            params["before_lt"] = before_lt

        data = self._request("GET", "/getTransactions", params)
        return data.get("result", [])

    def get_all_transactions(self, address: str, max_pages: int = 20) -> list:
        all_txs = []
        seen_hashes = set()
        before_lt = None
        page = 0

        while page < max_pages:
            try:
                txs = self.get_transactions(address, limit=100, before_lt=before_lt)
            except TONClientError:
                logger.warning("Failed to fetch page %d, stopping", page)
                break

            if not txs:
                break

            new_count = 0
            for tx in txs:
                tx_id = tx.get("transaction_id", {})
                tx_hash = tx_id.get("hash", "") or tx.get("hash", "")
                if tx_hash and tx_hash not in seen_hashes:
                    seen_hashes.add(tx_hash)
                    all_txs.append(tx)
                    new_count += 1

            if new_count == 0:
                break

            last_tx_id = txs[-1].get("transaction_id", {})
            last_lt = last_tx_id.get("lt") or txs[-1].get("lt")
            if last_lt == before_lt:
                break
            before_lt = last_lt

            if len(txs) < 100:
                break

            page += 1
            time.sleep(1)

        return all_txs
