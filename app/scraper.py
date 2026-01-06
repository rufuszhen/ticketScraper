from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple

import requests

from .config import ScrapeConfig


class AvailabilityResult:
    def __init__(self, available: bool, matched_text: Optional[str], url: str) -> None:
        self.available = available
        self.matched_text = matched_text
        self.url = url


def check_availability(
    config: ScrapeConfig,
    origin: str,
    destination: str,
    date: str,
    cabin_class: str,
) -> AvailabilityResult:
    url = config.ba_search_url_template.format(
        origin=origin,
        destination=destination,
        date=date,
        cabin=cabin_class,
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    headers.update(config.request_headers or {})
    cookies = config.request_cookies or {}
    response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    response.raise_for_status()
    match_text = _match_regex(config.availability_regex, response.text)
    if match_text:
        return AvailabilityResult(True, match_text, url)

    json_match = _match_json_availability(response, config.availability_json_keys)
    if json_match:
        return AvailabilityResult(True, json_match, url)

    return AvailabilityResult(False, None, url)


def _match_regex(pattern: str, text: str) -> Optional[str]:
    if not pattern:
        return None
    compiled = re.compile(pattern, re.IGNORECASE)
    match = compiled.search(text)
    return match.group(0) if match else None


def _match_json_availability(response: requests.Response, keys: Iterable[str]) -> Optional[str]:
    key_set = {key.strip() for key in keys if key.strip()}
    if not key_set:
        return None
    content_type = response.headers.get("Content-Type", "")
    if "json" not in content_type.lower():
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    found = _search_json(payload, key_set)
    if found:
        key, value = found
        return f"{key}={value}"
    return None


def _search_json(payload: object, keys: set[str]) -> Optional[Tuple[str, object]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and _is_truthy(value):
                return key, value
            found = _search_json(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _search_json(item, keys)
            if found:
                return found
    return None


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "available", "open"}
    return False
