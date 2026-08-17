import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TON_ADDRESS_RE = re.compile(
    r"^(EQ|UQ)[A-Za-z0-9_-]{46}$"
)


def validate_ton_address(address: str) -> bool:
    if not address or not isinstance(address, str):
        return False
    address = address.strip()
    return bool(TON_ADDRESS_RE.match(address))


def normalize_address(address: str) -> str:
    return address.strip() if address else ""


def truncate_address(address: str, chars: int = 6) -> str:
    if not address or len(address) <= chars * 2 + 3:
        return address
    return f"{address[:chars]}...{address[-chars:]}"


def explorer_url(address: str) -> str:
    return f"https://tonviewer.com/{address}"


def tx_explorer_url(tx_hash: str) -> str:
    return f"https://tonviewer.com/transaction/{tx_hash}"
