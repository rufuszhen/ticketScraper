from __future__ import annotations

import re
from typing import Dict, Optional

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
    headers = config.request_headers or {}
    cookies = config.request_cookies or {}
    response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    response.raise_for_status()
    pattern = re.compile(config.availability_regex, re.IGNORECASE)
    match = pattern.search(response.text)
    return AvailabilityResult(bool(match), match.group(0) if match else None, url)
