from __future__ import annotations

import re
from typing import Optional

import requests

from .config import ScrapeConfig


class AvailabilityResult:
    def __init__(
        self,
        available: bool,
        matched_text: Optional[str],
        url: str,
        status_code: Optional[int],
        blocked_reason: Optional[str],
        title: Optional[str],
        text_sample: Optional[str],
    ) -> None:
        self.available = available
        self.matched_text = matched_text
        self.url = url
        self.status_code = status_code
        self.blocked_reason = blocked_reason
        self.title = title
        self.text_sample = text_sample


def _extract_title(html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title or None


def _detect_blocked(html: str, blocked_regexes: list[str]) -> Optional[str]:
    for pattern in blocked_regexes:
        if re.search(pattern, html, re.IGNORECASE):
            return pattern
    return None


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
    title = _extract_title(response.text)
    blocked_reason = _detect_blocked(response.text, config.blocked_regexes)
    text_sample = response.text[:5000] if not match else None
    return AvailabilityResult(
        bool(match),
        match.group(0) if match else None,
        url,
        response.status_code,
        blocked_reason,
        title,
        text_sample,
    )
