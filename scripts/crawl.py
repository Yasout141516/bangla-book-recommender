"""Polite crawler for book pages. Stores raw HTML only; parsing happens later.

Usage:
  python scripts/crawl.py boighor [--limit N]
  python scripts/crawl.py boitoi  [--limit N]

Output (per D-012):
  data/raw/<site>/<run-date>/pages/<page_id>.html.gz   raw HTML, gzip-compressed
  data/raw/<site>/<run-date>/fetch_log.jsonl           one line per request (url, status, bytes, time)

Behaviour:
  - robots.txt was checked by hand for both sites (2026-09-26): book pages are allowed.
  - One request per DELAY seconds; honest User-Agent.
  - Resumable: pages already on disk are skipped, so re-running continues where it stopped.
  - Stops by itself after MAX_BLOCKED consecutive 403/429 responses, or MAX_ERRORS errors in a row.
"""
import argparse
import datetime
import gzip
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "BanglaBookRecommender/0.1 (non-commercial research project; polite crawler)"}
DELAY = 1.0
MAX_BLOCKED = 5
MAX_ERRORS = 20
# Boighor book codes are not sequential, so we list them per category through the same
# endpoint the public website calls when you scroll a category page. Listing responses are
# saved raw in listings/. Book details come from the public book pages.
BOIGHOR_API = "https://api.boighor.com/api/getBooksByCategorys"
BOIGHOR_CATEGORIES = ["nov", "str", "pom", "drm", "cmx", "bio", "trv", "atc", "abi", "otr"]


def boighor_urls(session, run_dir):
    listings = run_dir / "listings"
    listings.mkdir(exist_ok=True)
    seen = set()
    for cat in BOIGHOR_CATEGORIES:
        page, pagelimit = 1, 1
        while page <= pagelimit:
            out = listings / f"{cat}_{page:03d}.json"
            if out.exists():
                body = out.read_bytes()
            else:
                r = session.post(BOIGHOR_API, headers=HEADERS, timeout=60,
                                 files={"page": (None, str(page)), "catcode": (None, cat),
                                        "msisdn": (None, ""), "fromsrc": (None, "web")})
                r.raise_for_status()
                body = r.content
                out.write_bytes(body)
                time.sleep(DELAY)
            data = json.loads(body)
            pagelimit = int((data.get("data") or {}).get("pagelimit") or pagelimit)
            codes = re.findall(r'"bookcode"\s*:\s*"(\w+)"', body.decode("utf-8"))
            if not codes:
                break
            for code in codes:
                if code not in seen:
                    seen.add(code)
                    yield code, f"https://boighor.com/book/{code}"
            page += 1
        print(f"boighor: category {cat} listed, {len(seen)} codes so far", flush=True)


def boitoi_urls(session):
    index = session.get("https://boitoi.com.bd/sitemap.xml", headers=HEADERS, timeout=60)
    index.raise_for_status()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for sm in ET.fromstring(index.content).findall("s:sitemap/s:loc", ns):
        loc = sm.text.strip()
        if "/books-" not in loc:
            continue
        time.sleep(DELAY)
        r = session.get(loc, headers=HEADERS, timeout=60)
        r.raise_for_status()
        for u in ET.fromstring(r.content).findall("s:url/s:loc", ns):
            url = u.text.strip()
            m = re.search(r"/books/(\d+)", urlparse(url).path)
            if m:
                yield m.group(1), url


def is_boighor_book(html):
    return '"bookdetails"' in html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", choices=["boighor", "boitoi"])
    ap.add_argument("--limit", type=int, default=0, help="stop after N new pages (0 = no limit)")
    ap.add_argument("--run-date", default=datetime.date.today().isoformat(),
                    help="reuse an earlier run folder to resume it")
    args = ap.parse_args()

    run_dir = ROOT / "data" / "raw" / args.site / args.run_date
    pages_dir = run_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    log = (run_dir / "fetch_log.jsonl").open("a", encoding="utf-8")

    # Pages without a book are logged so a resume doesn't re-request them.
    seen_empty = set()
    log_path = run_dir / "fetch_log.jsonl"
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("note") == "no_book":
                seen_empty.add(e["page_id"])

    session = requests.Session()
    urls = boighor_urls(session, run_dir) if args.site == "boighor" else boitoi_urls(session)
    new = blocked = errors = 0
    for page_id, url in urls:
        out = pages_dir / f"{page_id}.html.gz"
        if out.exists() or page_id in seen_empty:
            continue
        entry = {"page_id": page_id, "url": unquote(url), "fetched_at": datetime.datetime.now().isoformat(timespec="seconds")}
        try:
            r = session.get(url, headers=HEADERS, timeout=60)
            entry.update(status=r.status_code, bytes=len(r.content))
            if r.status_code in (403, 429):
                blocked += 1
                entry["note"] = "blocked"
                if blocked >= MAX_BLOCKED:
                    log.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    print(f"Stopping: {blocked} blocked responses in a row.", file=sys.stderr)
                    break
                time.sleep(DELAY * 30)
            elif r.status_code == 200:
                blocked = errors = 0
                html = r.text
                if args.site == "boighor" and not is_boighor_book(html):
                    entry["note"] = "no_book"
                else:
                    out.write_bytes(gzip.compress(r.content))
                    new += 1
            else:
                entry["note"] = "http_error"
        except requests.RequestException as ex:
            errors += 1
            entry.update(status=None, error=str(ex)[:200])
            if errors >= MAX_ERRORS:
                log.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"Stopping: {errors} errors in a row.", file=sys.stderr)
                break
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.flush()
        if new and new % 200 == 0 and entry.get("status") == 200:
            print(f"{args.site}: {new} pages saved", flush=True)
        if args.limit and new >= args.limit:
            break
        time.sleep(DELAY)
    print(f"{args.site}: done, {new} new pages saved in {pages_dir}")


if __name__ == "__main__":
    main()
