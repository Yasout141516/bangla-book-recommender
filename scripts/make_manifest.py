"""Record every file in data/raw/ in data/raw/MANIFEST.json with its sha256 checksum.

Usage: python scripts/make_manifest.py
Existing entries keep their source_url, license and fetched_at. New files get
the defaults from SOURCES below (edit these when adding a new source).
"""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "MANIFEST.json"

# Defaults per top-level folder in data/raw/.
SOURCES = {
    "rokomaribg": {
        "source_url": "https://github.com/backlashblitz/Bangla-Book-Recommendation-Dataset",
        "license": "CC BY-NC 4.0 (HF mirror tag; GitHub repo has no license file)",
    },
    "banglabook": {
        "source_url": "https://github.com/mohsinulkabir14/BanglaBook",
        "license": "CC BY-NC-SA 4.0",
    },
    "wikipedia": {
        "source_url": "https://bn.wikipedia.org (category walk of বাংলা ভাষার উপন্যাস and related)",
        "license": "CC BY-SA 4.0",
    },
    "wikidata": {
        "source_url": "https://query.wikidata.org/sparql (scripts/collect_wikidata_authors.py)",
        "license": "CC0",
    },
    "boighor": {
        "source_url": "https://boighor.com (scripts/crawl.py)",
        "license": "No data license; store facts, use blurbs only as private input (non-commercial, D-010)",
    },
    "boitoi": {
        "source_url": "https://boitoi.com.bd (scripts/crawl.py)",
        "license": "No data license; store facts, use blurbs only as private input (non-commercial, D-010)",
    },
}

# Crawled page folders hold thousands of files; they are summarised as one entry
# (file count + bytes). Their fetch_log.jsonl is the per-page record.
BULK_DIRS = {"pages", "listings"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    old = {e["path"]: e for e in json.loads(MANIFEST.read_text(encoding="utf-8"))} if MANIFEST.exists() else {}
    today = datetime.date.today().isoformat()
    entries = []
    bulk = {}
    for f in sorted(p for p in RAW.rglob("*") if p.is_file() and p != MANIFEST):
        rel = f.relative_to(RAW).as_posix()
        if BULK_DIRS & set(rel.split("/")[:-1]):
            folder = rel.rsplit("/", 1)[0]
            n, size = bulk.get(folder, (0, 0))
            bulk[folder] = (n + 1, size + f.stat().st_size)
            continue
        digest = sha256(f)
        prev = old.get(rel, {})
        if prev and prev.get("sha256") != digest:
            print(f"WARNING: {rel} changed since it was recorded. Raw files should never change.")
        defaults = SOURCES.get(rel.split("/")[0], {"source_url": "UNKNOWN", "license": "UNKNOWN"})
        entries.append({
            "path": rel,
            "sha256": digest,
            "bytes": f.stat().st_size,
            "source_url": prev.get("source_url", defaults["source_url"]),
            "license": prev.get("license", defaults["license"]),
            "fetched_at": prev.get("fetched_at", today),
        })
    for folder, (n, size) in sorted(bulk.items()):
        defaults = SOURCES.get(folder.split("/")[0], {"source_url": "UNKNOWN", "license": "UNKNOWN"})
        prev = old.get(folder + "/", {})
        entries.append({
            "path": folder + "/", "files": n, "bytes": size,
            "source_url": prev.get("source_url", defaults["source_url"]),
            "license": prev.get("license", defaults["license"]),
            "fetched_at": prev.get("fetched_at", today),
        })
    MANIFEST.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {MANIFEST}")


if __name__ == "__main__":
    main()
