from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


CONFIG_PATH = Path("config.json")
STATE_PATH = Path("state.json")


@dataclass
class RouteConfig:
    id: str
    origin: str
    destination: str
    start_date: str
    end_date: str
    cabin_class: str


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    use_tls: bool = True


@dataclass
class ScrapeConfig:
    poll_interval_minutes: int = 5
    ba_search_url_template: str = (
        "https://www.britishairways.com/travel/redeem/execclub/_gf/en_gb"
        "?from={origin}&to={destination}&outboundDate={date}&cabin={cabin}"
    )
    availability_regex: str = "Available"
    blocked_regexes: List[str] = field(
        default_factory=lambda: [
            "sign in",
            "log in",
            "access denied",
            "robot",
            "enable javascript",
            "verify you are a human",
        ]
    )
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_cookies: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    routes: List[RouteConfig] = field(default_factory=list)
    email: EmailConfig = field(default_factory=EmailConfig)
    scrape: ScrapeConfig = field(default_factory=ScrapeConfig)


@dataclass
class AppState:
    last_alerts: Dict[str, str] = field(default_factory=dict)


def _default_config() -> AppConfig:
    return AppConfig()


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        config = _default_config()
        save_config(config)
        return config
    data = json.loads(CONFIG_PATH.read_text())
    routes = [RouteConfig(**route) for route in data.get("routes", [])]
    email = EmailConfig(**data.get("email", {}))
    scrape = ScrapeConfig(**data.get("scrape", {}))
    return AppConfig(routes=routes, email=email, scrape=scrape)


def save_config(config: AppConfig) -> None:
    payload = asdict(config)
    CONFIG_PATH.write_text(json.dumps(payload, indent=2))


def load_state() -> AppState:
    if not STATE_PATH.exists():
        state = AppState()
        save_state(state)
        return state
    data = json.loads(STATE_PATH.read_text())
    return AppState(last_alerts=data.get("last_alerts", {}))


def save_state(state: AppState) -> None:
    STATE_PATH.write_text(json.dumps(asdict(state), indent=2))


def dates_between(start: str, end: str) -> List[str]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if end_date < start_date:
        return []
    days = (end_date - start_date).days
    return [date.fromordinal(start_date.toordinal() + offset).isoformat() for offset in range(days + 1)]
