# ED-live Nachrichten Scraper

Scraper for ed-live.de/nachrichten — German local news site for Landkreis Erding.

## How to run

```bash
uv run python scraper.py 2026-04-17                        # single date
uv run python scraper.py 2026-04-10 2026-04-17             # date range
uv run python scraper.py 2026-04-17 --translate            # with EN translation
uv run python scraper.py 2026-04-17 --translate --model qwen2.5:7b  # custom model
```

Or use the all-in-one script (starts Ollama, scrapes, translates, stops Ollama):

```bash
./translate.sh 2026-04-17
./translate.sh 2026-04-10 2026-04-17
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

## Translation via Ollama

Translation uses a local Ollama model — no API key or internet access required.

```bash
brew install ollama
ollama pull qwen2.5:3b   # recommended: fast, good German support
ollama serve             # starts the local server at http://localhost:11434
```

The `--translate` flag sends each article's `full_text` to Ollama and adds a
`translation` field (English translation + summary) to both JSON and Markdown output.

## User preferences

- Package manager: `uv`
- Prefer plain `requests` over Playwright — check page source for hidden APIs first
