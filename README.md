# ED-live Nachrichten Scraper

Scraper for [ed-live.de/nachrichten](https://ed-live.de/nachrichten) — a German local news site covering Landkreis Erding, Bavaria. Fetches articles by date range, extracts full text, and optionally translates them to English via a local Ollama model.

## Features

- Fetch articles by date or date range
- Extracts full article text (internal articles via CSS selector, external via [trafilatura](https://trafilatura.readthedocs.io))
- Optional English translation and summary via [Ollama](https://ollama.com) (no API key required)
- Outputs structured `articles.json` and human-readable `articles.md`
- Concurrent article fetching for speed

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd ed_live_nachrichten
uv sync
```

## Usage

```bash
# Articles from a single date
uv run python scraper.py 2026-04-17

# Articles from a date range
uv run python scraper.py 2026-04-10 2026-04-17

# With English translation and summary
uv run python scraper.py 2026-04-17 --translate

# With a custom Ollama model
uv run python scraper.py 2026-04-17 --translate --model qwen2.5:7b
```

### All-in-one translation script

`translate.sh` handles the full Ollama lifecycle: pulls the model if needed, runs the scraper with translation enabled, then unloads the model to free memory.

```bash
./translate.sh 2026-04-17
./translate.sh 2026-04-10 2026-04-17
./translate.sh 2026-04-17 --model qwen2.5:7b
```

## Output

Both output files are written to the current directory.

**`articles.json`** — structured data:
```json
{
  "scraped_at": "2026-04-17T10:00:00",
  "from_date": "2026-04-17",
  "to_date": "2026-04-17",
  "count": 12,
  "articles": [
    {
      "title": "A94: Schwerer Auffahrunfall",
      "url": "https://www.ed-live.de/nachrichten_details?id=204189",
      "date": "17.04.2026",
      "location": "Landkreis Erding",
      "summary": "Nach der Bergung musste ein Autofahrer schwerstverletzt...",
      "image": "https://ed-live.de/img/...",
      "external": false,
      "full_text": "Am 16.04.2026...",
      "translation": "TRANSLATION:\n...\n\nSUMMARY:\n..."
    }
  ]
}
```

**`articles.md`** — readable Markdown with title, date, location, link, original text, and translation (when enabled).

## Viewing the Markdown output

Use [grip](https://github.com/joeyespo/grip) to render `articles.md` in the browser with GitHub styling:

```bash
pip install grip
# or
uv tool install grip

grip articles.md
# Opens at http://localhost:6419
```

Or view it directly in the terminal with syntax highlighting:

```bash
brew install bat
bat articles.md
```

## Translation via Ollama

Translation runs locally — no API key, no internet access required beyond the initial model download.

### Setup

```bash
brew install ollama
ollama pull qwen2.5:3b   # ~2 GB, fast, strong German support
```

### How it works

The `--translate` flag sends each article's `full_text` to the Ollama API and asks the model to produce a full English translation followed by a 2–3 sentence summary. The result is stored in the `translation` field of each article.

### Models

| Model | Size | Notes |
|---|---|---|
| `qwen2.5:3b` | ~2 GB | Default. Fast, good German support |
| `qwen2.5:7b` | ~5 GB | Better quality, slower |
| `llama3.2:3b` | ~2 GB | Alternative option |

## How it works

The site loads articles dynamically via a jQuery AJAX call. The underlying endpoint is openly accessible:

- **List endpoint:** `GET https://ed-live.de/ajax/nachrichten_ajax.php`
- **Pagination:** `POST` with `lastId` and `lastDate` cursor fields
- Articles are returned newest-first; the scraper stops paginating once the cursor date goes before `from_date`
- Internal article pages require the `www` subdomain (`https://www.ed-live.de/...`)
