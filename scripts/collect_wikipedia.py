"""Download Bangla Wikipedia articles (wikitext + Wikidata ID) for the book pages list.

Usage:  python scripts/collect_wikipedia.py
Input:  data/raw/wikipedia/bn_novel_pages.json   (list of page titles)
Output: data/raw/wikipedia/<date>/pages.jsonl     (one raw API page object per line)
License of content: CC BY-SA 4.0. Keep the attribution (page URL) with anything derived from it.
"""
import datetime
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TITLES = ROOT / "data" / "raw" / "wikipedia" / "bn_novel_pages.json"
OUT_DIR = ROOT / "data" / "raw" / "wikipedia" / datetime.date.today().isoformat()
API = "https://bn.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "BanglaBookRecommender/0.1 (non-commercial research project)"}
BATCH = 50  # API maximum for content queries


def main():
    titles = json.loads(TITLES.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "pages.jsonl"
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for i in range(0, len(titles), BATCH):
            batch = titles[i:i + BATCH]
            params = {"action": "query", "format": "json", "formatversion": "2", "redirects": "1",
                      "prop": "revisions|pageprops|info", "rvprop": "content|timestamp|ids",
                      "rvslots": "main", "ppprop": "wikibase_item", "inprop": "url",
                      "titles": "|".join(batch)}
            r = requests.get(API, params=params, headers=HEADERS, timeout=60)
            r.raise_for_status()
            for page in r.json()["query"]["pages"]:
                fh.write(json.dumps(page, ensure_ascii=False) + "\n")
                n += 1
            time.sleep(1)
    print(f"Wrote {n} pages to {out}")


if __name__ == "__main__":
    main()
