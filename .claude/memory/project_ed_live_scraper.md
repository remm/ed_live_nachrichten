---
name: ed-live scraper project
description: Technical details of the ed-live.de/nachrichten scraper built in this project
type: project
---

Site: ed-live.de/nachrichten — German local news for Landkreis Erding. No RSS, no public API.

**Why:** Content loads via jQuery AJAX, so plain requests on the main page returns no articles.

## Discovered API

Endpoint: `https://ed-live.de/ajax/nachrichten_ajax.php`

- First page: `GET` (no params)
- Next pages: `POST` with `lastId=<id>&lastDate=<YYYY-MM-DD>`
- Returns JSON: `{ html, lastId, lastDate, count }`
- `html` field contains article list as raw HTML
- Articles ordered newest-first; ~7388 total
- Pagination stops when `lastId` stops changing

Required headers:
```
X-Requested-With: XMLHttpRequest
Referer: https://ed-live.de/nachrichten
```

## Article detail pages

- Internal: `https://www.ed-live.de/nachrichten_details?id=<id>` — **must use www** subdomain (non-www returns 301)
- Content selector: `#nachrichten_details_container`
- Remove before extracting text: `.nachrichtenbild_1, .nachrichtenbilder, #nachrichten_details_zug_gemeinde, .google_ad_responsive`
- External articles (mostly merkur.de): paywalled — trafilatura extracts available lead text

## Stack

`requests` + `BeautifulSoup` + `trafilatura`, managed with `uv`
Concurrent article fetching via `ThreadPoolExecutor(max_workers=8)`

## Output

- `articles.json` — structured data
- `articles.md` — human-readable markdown with title, date, location, link, summary, full text

## How to apply

When working on this scraper, the API is stable and fully open. No auth, no tokens. The main fragility point is HTML structure of article detail pages (internal) or paywall changes (external).
