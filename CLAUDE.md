# ED-live Nachrichten Scraper

Scraper for ed-live.de/nachrichten — German local news site for Landkreis Erding.

## How to run

```bash
uv run python scraper.py 2026-04-17            # single date
uv run python scraper.py 2026-04-10 2026-04-17 # date range
```

Output: `articles.json` + `articles.md`

## API

Endpoint: `https://ed-live.de/ajax/nachrichten_ajax.php`
- First page: GET (no params)
- Pagination: POST with `lastId=<id>&lastDate=<YYYY-MM-DD>`
- Returns JSON: `{ html, lastId, lastDate, count }`

## Article detail pages

- Internal: `https://www.ed-live.de/nachrichten_details?id=<id>` — **www subdomain required**
- Content selector: `#nachrichten_details_container`
- External (e.g. merkur.de): paywalled — trafilatura extracts available lead text

## User preferences

- Package manager: `uv`
- Prefer plain `requests` over Playwright — check page source for hidden APIs first
