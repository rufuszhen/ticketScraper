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
        status_code: Optional[int] = None,
        response_snippet: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        self.available = available
        self.matched_text = matched_text
        self.url = url
        self.status_code = status_code
        self.response_snippet = response_snippet
        self.error = error


def build_search_url(
    config: ScrapeConfig,
    origin: str,
    destination: str,
    date: str,
    cabin_class: str,
) -> str:
    return config.ba_search_url_template.format(
        origin=origin,
        destination=destination,
        date=date,
        cabin=cabin_class,
    )


def check_availability(
    config: ScrapeConfig,
    origin: str,
    destination: str,
    date: str,
    cabin_class: str,
) -> AvailabilityResult:
    url = build_search_url(config, origin, destination, date, cabin_class)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if config.request_headers:
        headers.update(config.request_headers)
    cookies = config.request_cookies or {}
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        status_code = response.status_code
        response.raise_for_status()
    except requests.RequestException as exc:
        response_text = None
        status_code = None
        if exc.response is not None:
            response_text = exc.response.text
            status_code = exc.response.status_code
        return AvailabilityResult(
            available=False,
            matched_text=None,
            url=url,
            status_code=status_code,
            response_snippet=response_text[:500] if response_text else None,
            error=str(exc),
        )
    pattern = re.compile(config.availability_regex, re.IGNORECASE)
    match = pattern.search(response.text)
    return AvailabilityResult(
        bool(match),
        match.group(0) if match else None,
        url,
        status_code=response.status_code,
        response_snippet=response.text[:500],
    )
