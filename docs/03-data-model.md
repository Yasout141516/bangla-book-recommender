# 03 Data model

Five entities: **work**, **author**, **series**, **edition** and **source**.
Tag fields use IDs from [04 Tag vocabulary](04-tag-vocabulary.md).

```
author ─┬─< work_author >─ work ─< edition
        │                  │
        │                  ├── series (optional)
        │                  └─< source
        └── (translator role via work_author.role)
```

---

## work (one record per book)

### Identity
| Field | Type | Req | Notes |
|---|---|---|---|
| `work_id` | string | ✅ | `bk_000123` |
| `title_bn` | string | ✅ | Title in Bangla script |
| `title_en` | string | | Romanised or English title |
| `title_aliases` | string[] | | Other spellings users may type ("Shonar Kella") |
| `authors` | {author_id, role}[] | ✅ | role: `author` / `translator` / `adapter` / `editor` |
| `original_work` | {title, author, language} | | For translations and adaptations |
| `series_id` / `series_order` | string / number | | e.g. Feluda, 4 |
| `recurring_characters` | string[] | | Feluda, Himu, Misir Ali… |

### Bibliographic facts
| Field | Type | Req | Notes |
|---|---|---|---|
| `first_published` | int (year) | | Year of first publication |
| `origin` | enum | ✅ | `bangladesh` / `west_bengal` / `translated` |
| `format` | enum | ✅ | See vocabulary |
| `page_count` | int | | Approximate; from an edition |
| `audience` | enum | ✅ | See vocabulary |
| `language_register` | enum | | `cholito` / `sadhu` (formal older style) |

### Content (shown to users, used for search)
| Field | Type | Req | Notes |
|---|---|---|---|
| `premise_bn` | string | ✅ | 2–4 sentences, spoiler-free, written by us from sources (D-008) |
| `premise_en` | string | | English version of the premise |
| `hook` | string | | One line |

### Taste tags (fixed lists only)
| Field | Type | Count | Notes |
|---|---|---|---|
| `genres` | id[] | 1–3 | |
| `moods` | id[] | 1–3 | |
| `pace` | id | 1 | |
| `themes` | id[] | 2–5 | |
| `setting_region` | id[] | 1–2 | Fixed list |
| `setting_places` | string[] | 0–3 | Open list, normalised (e.g. "Kolkata", "Sundarbans") |
| `setting_era` | id | 1 | |
| `tone` | id | 1 | light / moderate / literary |
| `content_notes` | id[] | 0+ | For audience filtering |

### Reader signals (filled later)
| Field | Type | Notes |
|---|---|---|
| `rating_avg`, `rating_count` | float, int | Per source; keep the source |
| `review_snippets` | string[] | Short excerpts for mood signals; internal use |
| `co_liked_work_ids` | string[] | "Readers who liked this also liked" |

### Provenance and quality
| Field | Type | Notes |
|---|---|---|
| `source_ids` | string[] | Links to `source` records |
| `llm_generated_fields` | string[] | e.g. `["premise_bn","moods","themes"]` |
| `llm_model` | string | Model and prompt version that generated the fields |
| `human_verified` | bool | |
| `confidence` | enum | high / medium / low |
| `created_at`, `updated_at` | datetime | |

### Derived (built by code, never edited by hand)
| Field | Notes |
|---|---|
| `embedding_text` | Built from genres, moods, pace, setting, themes, premise_bn and premise_en |
| `embedding_dense`, `embedding_sparse` | From the embedding model (e.g. bge-m3) |

---

## author
| Field | Type | Req | Notes |
|---|---|---|---|
| `author_id` | string | ✅ | `au_humayun_ahmed` |
| `name_bn` | string | ✅ | হুমায়ূন আহমেদ |
| `name_en` | string | ✅ | Humayun Ahmed |
| `aliases` | string[] | | Humayun Ahmad, pen names, other spellings |
| `birth_year`, `death_year` | int | | |
| `origin` | enum | | `bangladesh` / `west_bengal` / `other` |
| `roles` | enum[] | | author / translator / adapter |
| `wikidata_qid` | string | | For linking and deduplication |
| `bio_short_bn` | string | | Optional, 1–2 lines |
| `public_domain_bd` | bool (derived) | | death_year + 60 < current year (Bangladesh term: verify the current Act) |

## series
| Field | Type | Notes |
|---|---|---|
| `series_id` | string | `sr_feluda` |
| `name_bn`, `name_en`, `aliases` | | ফেলুদা / Feluda |
| `author_ids` | string[] | Some series have several writers (e.g. Masud Rana ghostwriters) |
| `main_characters` | string[] | |

## edition
| Field | Type | Notes |
|---|---|---|
| `edition_id` | string | |
| `work_id` | string | |
| `publisher` | string | |
| `year` | int | |
| `isbn` | string | |
| `page_count` | int | |
| `store_links` | {store, url}[] | |
| `cover_url` | string | Link only; don't copy images without permission |

## source
| Field | Type | Notes |
|---|---|---|
| `source_id` | string | |
| `type` | enum | `wikipedia_bn`, `wikipedia_en`, `wikidata`, `goodreads`, `rokomari`, `openlibrary`, `review_dataset`, `manual`… |
| `url` | string | |
| `license` | string | e.g. CC BY-SA 4.0, CC0, "store ToS" |
| `fetched_at` | datetime | |
| `raw_ref` | string | Path to the stored raw snapshot |

---

## Example (illustrative; facts to be checked against sources)
```json
{
  "work_id": "bk_000123",
  "title_bn": "সোনার কেল্লা",
  "title_en": "Sonar Kella",
  "title_aliases": ["Shonar Kella"],
  "authors": [{"author_id": "au_satyajit_ray", "role": "author"}],
  "series_id": "sr_feluda",
  "recurring_characters": ["Feluda", "Topshe", "Jatayu"],
  "first_published": 1971,
  "origin": "west_bengal",
  "format": "novella",
  "audience": "all_ages",
  "language_register": "cholito",
  "premise_en": "A young boy in Kolkata claims memories of a past life in a golden fort. When he becomes a target, detective Feluda follows the trail to Rajasthan.",
  "genres": ["detective", "adventure"],
  "moods": ["tense", "heartwarming"],
  "pace": "fast",
  "themes": ["childhood", "crime"],
  "setting_region": ["kolkata", "elsewhere_india"],
  "setting_places": ["Kolkata", "Rajasthan"],
  "setting_era": "post_independence",
  "tone": "light",
  "content_notes": [],
  "llm_generated_fields": ["premise_en", "moods", "themes", "pace"],
  "human_verified": false
}
```
