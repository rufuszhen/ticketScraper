# BA Reward Ticket Monitor

Local web app that tracks British Airways reward availability for configurable routes and dates, persists settings on disk, and emails you when matching cabins appear.

## Features
- Add/edit/delete routes with date ranges and cabin classes.
- Persist configuration to `config.json` and alert history to `state.json`.
- Background polling every few minutes.
- SMTP email notifications.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`.

## Configuration Notes

The app uses a configurable British Airways reward search URL template and an availability regex. Configure these in the UI:

- `BA Search URL Template` should contain `{origin}`, `{destination}`, `{date}`, and `{cabin}` placeholders.
- `Availability Regex` should match text that appears when reward seats are available.
- `Blocked Page Regexes` are patterns that indicate the response is a login page, bot check, or access block.
- `Request Headers` / `Request Cookies` can include session cookies or auth tokens if required.

Example template:

```
https://www.britishairways.com/travel/redeem/execclub/_gf/en_gb?from={origin}&to={destination}&outboundDate={date}&cabin={cabin}
```

## Email

Fill in SMTP details under **Email Settings**. If SMTP is not configured, email notifications are skipped.

## Troubleshooting Availability

Some British Airways pages are rendered with JavaScript or require login/cookies. If the scraper does not detect availability:

1. Run **Manual Check** and review the JSON output. The response includes `status_code`, `title`, and `blocked_reason`.
2. If `blocked_reason` matches a login/bot pattern, add authenticated cookies/headers via the UI.
3. Update the `Availability Regex` to match the exact text shown on the reward availability page.

## Files

- `config.json` - persisted routes and settings.
- `state.json` - last alert history to avoid repeated emails.
