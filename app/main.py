from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import List, Optional

from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from .config import (
    AppConfig,
    AppState,
    EmailConfig,
    RouteConfig,
    ScrapeConfig,
    dates_between,
    load_config,
    load_state,
    save_config,
    save_state,
)
from .notifier import send_email
from .scraper import check_availability


class RoutePayload(BaseModel):
    id: Optional[str] = None
    origin: str
    destination: str
    start_date: str
    end_date: str
    cabin_class: str


class EmailPayload(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    use_tls: bool = True


class ScrapePayload(BaseModel):
    poll_interval_minutes: int = 5
    ba_search_url_template: str
    availability_regex: str
    availability_json_keys: List[str] = Field(default_factory=list)
    request_headers: dict = Field(default_factory=dict)
    request_cookies: dict = Field(default_factory=dict)


class SettingsPayload(BaseModel):
    email: EmailPayload
    scrape: ScrapePayload


class CheckResult(BaseModel):
    route_id: str
    date: str
    cabin_class: str
    available: bool
    url: str
    matched_text: Optional[str]


app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

config_lock = threading.Lock()
config: AppConfig = load_config()
state: AppState = load_state()

stop_event = threading.Event()


def _save_config(updated: AppConfig) -> None:
    global config
    save_config(updated)
    config = updated


def serialize_config(current: AppConfig) -> dict:
    return asdict(current)


def run_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    with config_lock:
        current_config = config
    for route in current_config.routes:
        for travel_date in dates_between(route.start_date, route.end_date):
            try:
                availability = check_availability(
                    current_config.scrape,
                    route.origin,
                    route.destination,
                    travel_date,
                    route.cabin_class,
                )
            except Exception:
                continue
            result = CheckResult(
                route_id=route.id,
                date=travel_date,
                cabin_class=route.cabin_class,
                available=availability.available,
                url=availability.url,
                matched_text=availability.matched_text,
            )
            results.append(result)
            if availability.available:
                key = f"{route.id}:{travel_date}:{route.cabin_class}"
                with config_lock:
                    last_alerted = state.last_alerts.get(key)
                if not last_alerted:
                    subject = (
                        f"BA Reward Availability: {route.origin}-{route.destination} "
                        f"{travel_date} {route.cabin_class}"
                    )
                    body = (
                        f"Availability detected for {route.origin} to {route.destination}\n"
                        f"Date: {travel_date}\n"
                        f"Cabin: {route.cabin_class}\n"
                        f"URL: {availability.url}\n"
                        f"Matched: {availability.matched_text or 'n/a'}"
                    )
                    send_email(current_config.email, subject, body)
                    with config_lock:
                        state.last_alerts[key] = datetime.utcnow().isoformat()
                        save_state(state)
    return results


def scheduler_loop() -> None:
    while not stop_event.is_set():
        run_checks()
        with config_lock:
            interval = max(config.scrape.poll_interval_minutes, 1)
        stop_event.wait(interval * 60)


@app.on_event("startup")
async def startup_event() -> None:
    threading.Thread(target=scheduler_loop, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    stop_event.set()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/config")
async def get_config() -> dict:
    with config_lock:
        return serialize_config(config)


@app.post("/api/routes")
async def add_route(payload: RoutePayload) -> dict:
    with config_lock:
        updated = load_config()
        route_id = payload.id or str(uuid.uuid4())
        new_route = RouteConfig(
            id=route_id,
            origin=payload.origin,
            destination=payload.destination,
            start_date=payload.start_date,
            end_date=payload.end_date,
            cabin_class=payload.cabin_class,
        )
        updated.routes.append(new_route)
        _save_config(updated)
        return asdict(new_route)


@app.put("/api/routes/{route_id}")
async def update_route(route_id: str, payload: RoutePayload) -> dict:
    with config_lock:
        updated = load_config()
        for index, route in enumerate(updated.routes):
            if route.id == route_id:
                updated.routes[index] = RouteConfig(
                    id=route_id,
                    origin=payload.origin,
                    destination=payload.destination,
                    start_date=payload.start_date,
                    end_date=payload.end_date,
                    cabin_class=payload.cabin_class,
                )
                _save_config(updated)
                return asdict(updated.routes[index])
    raise HTTPException(status_code=404, detail="Route not found")


@app.delete("/api/routes/{route_id}")
async def delete_route(route_id: str) -> dict:
    with config_lock:
        updated = load_config()
        updated.routes = [route for route in updated.routes if route.id != route_id]
        _save_config(updated)
    return {"status": "deleted"}


@app.post("/api/settings")
async def update_settings(payload: SettingsPayload) -> dict:
    with config_lock:
        updated = load_config()
        updated.email = EmailConfig(**payload.email.dict())
        updated.scrape = ScrapeConfig(**payload.scrape.dict())
        _save_config(updated)
        return serialize_config(updated)


@app.post("/api/run-check")
async def run_check() -> dict:
    results = run_checks()
    return {"results": [result.dict() for result in results]}
