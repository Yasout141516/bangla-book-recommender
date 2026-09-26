"""Download Bengali-language writers from Wikidata (CC0) for the author table.

Usage:  python scripts/collect_wikidata_authors.py
Output: data/raw/wikidata/<date>/authors.json  (raw SPARQL JSON response, unmodified)
"""
import datetime
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "wikidata" / datetime.date.today().isoformat()
ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "BanglaBookRecommender/0.1 (non-commercial research project)",
           "Accept": "application/sparql-results+json"}

# People who write in Bengali (P1412 = Q9610) with a writing occupation.
QUERY = """
SELECT ?person ?bnLabel ?enLabel
       (GROUP_CONCAT(DISTINCT ?bnAlias; separator="|") AS ?bnAliases)
       (GROUP_CONCAT(DISTINCT ?enAlias; separator="|") AS ?enAliases)
       (SAMPLE(?birth) AS ?birthDate) (SAMPLE(?death) AS ?deathDate)
       (GROUP_CONCAT(DISTINCT ?countryLabel; separator="|") AS ?countries)
       (GROUP_CONCAT(DISTINCT ?occLabel; separator="|") AS ?occupations)
       (SAMPLE(?bnwiki) AS ?bnWiki) (SAMPLE(?enwiki) AS ?enWiki)
WHERE {
  VALUES ?occ { wd:Q36180 wd:Q6625963 wd:Q49757 wd:Q482980 wd:Q4853732 wd:Q333634 wd:Q1930187 }
  ?person wdt:P31 wd:Q5 ; wdt:P1412 wd:Q9610 ; wdt:P106 ?occ .
  OPTIONAL { ?person rdfs:label ?bnLabel FILTER(LANG(?bnLabel) = "bn") }
  OPTIONAL { ?person rdfs:label ?enLabel FILTER(LANG(?enLabel) = "en") }
  OPTIONAL { ?person skos:altLabel ?bnAlias FILTER(LANG(?bnAlias) = "bn") }
  OPTIONAL { ?person skos:altLabel ?enAlias FILTER(LANG(?enAlias) = "en") }
  OPTIONAL { ?person wdt:P569 ?birth }
  OPTIONAL { ?person wdt:P570 ?death }
  OPTIONAL { ?person wdt:P27 ?country . ?country rdfs:label ?countryLabel FILTER(LANG(?countryLabel) = "en") }
  OPTIONAL { ?occ rdfs:label ?occLabel FILTER(LANG(?occLabel) = "en") }
  OPTIONAL { ?bnwiki schema:about ?person ; schema:isPartOf <https://bn.wikipedia.org/> }
  OPTIONAL { ?enwiki schema:about ?person ; schema:isPartOf <https://en.wikipedia.org/> }
}
GROUP BY ?person ?bnLabel ?enLabel
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    r = requests.post(ENDPOINT, data={"query": QUERY}, headers=HEADERS, timeout=300)
    r.raise_for_status()
    out = OUT_DIR / "authors.json"
    out.write_bytes(r.content)
    n = len(r.json()["results"]["bindings"])
    print(f"Wrote {n:,} authors to {out}")


if __name__ == "__main__":
    main()
