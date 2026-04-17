"""
ed-live.de/nachrichten scraper
API: https://ed-live.de/ajax/nachrichten_ajax.php
- First page: GET (no params)
- Next pages: POST with lastId=<id>&lastDate=<YYYY-MM-DD>
- Pagination ends when lastId stops changing
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup

BASE_URL = "https://ed-live.de"
INTERNAL_BASE = "https://www.ed-live.de"
API_URL = f"{BASE_URL}/ajax/nachrichten_ajax.php"
OUTPUT_FILE = Path("articles.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/nachrichten",
}


def parse_articles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for container in soup.select(".box_news_container"):
        link_el = container.select_one(".box_news_image a")
        title_el = container.select_one("h3")
        meta_el = container.select_one("span")

        href = link_el["href"] if link_el else None
        if href and href.startswith("http"):
            url = href          # external article (e.g. Merkur)
            is_external = True
        elif href:
            url = f"{BASE_URL}/{href}"
            is_external = False
        else:
            url = None
            is_external = False

        title = title_el.get_text(strip=True) if title_el else None

        date, location = None, None
        if meta_el:
            meta = meta_el.get_text(strip=True)  # e.g. "16.04.2026 - Erding"
            parts = meta.split(" - ", 1)
            if len(parts) == 2:
                date, location = parts[0].strip(), parts[1].strip()

        # Summary is plain text inside box_news_content, after the <br> tags
        content_el = container.select_one(".box_news_content")
        summary = None
        if content_el:
            # Strip child tags, keep only direct text nodes
            for tag in content_el.find_all(["h3", "span", "a", "br"]):
                tag.decompose()
            summary = content_el.get_text(" ", strip=True) or None

        img_el = container.select_one(".box_news_image img")
        image = None
        if img_el and img_el.get("src"):
            src = img_el["src"]
            image = src if src.startswith("http") else f"{BASE_URL}/{src.lstrip('/')}"

        articles.append({
            "title": title,
            "url": url,
            "date": date,
            "location": location,
            "summary": summary,
            "image": image,
            "external": is_external,
        })

    return articles


def fetch_full_text(url: str, is_external: bool) -> str | None:
    """Fetch and return the main text body of an article URL."""
    try:
        if is_external:
            # trafilatura handles boilerplate removal and works on most news sites
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        else:
            # Internal ed-live.de: content is in #nachrichten_details_container
            # Normalise to www subdomain to avoid redirect
            url = url.replace("https://ed-live.de", INTERNAL_BASE)
            resp = requests.get(url, headers={**HEADERS, "X-Requested-With": ""}, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            container = soup.select_one("#nachrichten_details_container")
            if not container:
                return None
            # Remove image captions, "weitere Nachrichten" block, and ads
            for el in container.select(".nachrichtenbild_1, .nachrichtenbilder, #nachrichten_details_zug_gemeinde, .google_ad_responsive"):
                el.decompose()
            return container.get_text("\n", strip=True) or None
    except Exception as e:
        print(f"    [!] Failed to fetch {url}: {e}")
        return None


def fetch_all_texts(articles: list[dict], max_workers: int = 8) -> list[dict]:
    """Concurrently fetch full article text for each article."""
    print(f"[*] Fetching full text for {len(articles)} articles ({max_workers} workers)...")

    def worker(article: dict) -> dict:
        if not article.get("url"):
            return article
        text = fetch_full_text(article["url"], article["external"])
        return {**article, "full_text": text}

    results = [None] * len(articles)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, a): i for i, a in enumerate(articles)}
        done = 0
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            done += 1
            if done % 5 == 0 or done == len(articles):
                print(f"    → {done}/{len(articles)}")

    return results


def fetch_page(last_id: str | None = None, last_date: str | None = None) -> dict:
    if last_id and last_date:
        resp = requests.post(
            API_URL,
            headers=HEADERS,
            data={"lastId": last_id, "lastDate": last_date},
            timeout=15,
        )
    else:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)

    resp.raise_for_status()
    return resp.json()


def parse_date(date_str: str) -> datetime:
    """Parse DD.MM.YYYY or YYYY-MM-DD into a datetime."""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {date_str!r}")


def scrape(from_date: datetime, to_date: datetime | None = None) -> list[dict]:
    """
    Fetch all articles between from_date and to_date (inclusive).
    to_date defaults to today.
    Articles are returned newest-first from the API, so we stop
    paginating as soon as the cursor date goes before from_date.
    """
    if to_date is None:
        to_date = datetime.now().replace(hour=23, minute=59, second=59)

    all_articles = []
    last_id, last_date = None, None
    page = 0

    while True:
        print(f"[*] Page {page + 1} (cursor: {last_date or 'start'})")
        data = fetch_page(last_id, last_date)
        articles = parse_articles(data["html"])

        for article in articles:
            if not article["date"]:
                continue
            article_date = parse_date(article["date"])
            if from_date <= article_date <= to_date:
                all_articles.append(article)

        page_last_date = data.get("lastDate")
        new_last_id = data.get("lastId")

        print(f"    → kept {len(all_articles)} so far, cursor date: {page_last_date}")

        # Stop when the page cursor goes before our from_date
        if not page_last_date or parse_date(page_last_date) < from_date:
            break

        # Stop if pagination didn't advance (end of data)
        if new_last_id == last_id:
            break

        last_id, last_date = new_last_id, page_last_date
        page += 1

    return all_articles


def export_markdown(articles: list[dict], from_date: datetime, to_date: datetime | None = None):
    md_file = Path("articles.md")
    lines = [
        f"# ED-live Nachrichten",
        f"**{from_date.strftime('%d.%m.%Y')} – {(to_date or datetime.now()).strftime('%d.%m.%Y')}**",
        f"*{len(articles)} articles*",
        "",
    ]
    for a in articles:
        lines.append(f"## {a['title']}")
        lines.append(f"📅 {a['date']} · 📍 {a['location']}")
        if a.get("url"):
            lines.append(f"🔗 {a['url']}")
        if a.get("summary"):
            lines.append(f"\n> {a['summary']}")
        if a.get("full_text"):
            lines.append(f"\n{a['full_text']}")
        lines.append("\n---\n")

    md_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Markdown saved to {md_file}")


def run(from_date: datetime, to_date: datetime | None = None):
    articles = scrape(from_date=from_date, to_date=to_date)
    articles = fetch_all_texts(articles)

    output = {
        "scraped_at": datetime.now().isoformat(),
        "source": API_URL,
        "from_date": from_date.strftime("%Y-%m-%d"),
        "to_date": (to_date or datetime.now()).strftime("%Y-%m-%d"),
        "count": len(articles),
        "articles": articles,
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"[+] Saved {len(articles)} articles to {OUTPUT_FILE}")
    export_markdown(articles, from_date, to_date)


if __name__ == "__main__":
    import sys

    # Usage:
    #   python scraper.py 2026-04-10              # from date until today
    #   python scraper.py 2026-04-10 2026-04-15   # date range
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <from_date> [to_date]")
        print("       Dates in YYYY-MM-DD format")
        sys.exit(1)

    _from = parse_date(sys.argv[1])
    _to = parse_date(sys.argv[2]) if len(sys.argv) > 2 else None
    run(from_date=_from, to_date=_to)
