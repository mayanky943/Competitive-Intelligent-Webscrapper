import re
from urllib.parse import urlparse
from typing import Optional


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


def extract_domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except ValueError:
        return False


def truncate_string(s: Optional[str], max_length: int = 200) -> Optional[str]:
    if not s:
        return s
    return s[:max_length] + "…" if len(s) > max_length else s


def safe_float(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None
