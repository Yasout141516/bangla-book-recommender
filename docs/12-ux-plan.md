# 12 UX plan (demo)

The user-facing plan for the Phase 4 demo. Decided in a design review on 2026-09-26 (D-017);
each item below was approved individually. The report is at the bottom.

## Platform
- **Mobile-first web page** first, which can be opened from a link on a resume or in an interview. A Messenger bot comes later, if at all.
- One page, one column on phones; on desktop the same column is centred (no separate desktop layout).

## First screen (the first 5 seconds)
1. One large input with a Bangla placeholder, e.g. `কেমন বই খুঁজছেন? যেমন: "ফেলুদার মতো গোয়েন্দা গল্প"`.
2. Under it, **4 tappable example queries** that show what the search understands: Bangla, English, Banglish and "like X":
   - `ফেলুদার মতো গোয়েন্দা গল্প`
   - `a slow, sad village novel`
   - `himu type boi`
   - `Liberation War, hopeful ending`
3. Nothing else: no hero section, no feature grid.

## Result card (the order of prominence)
| Priority | Content | Notes |
|---|---|---|
| 1st | **Title + author** in Bangla; romanised title/author smaller beneath | From `title_bn`, `title_en`, author table |
| 2nd | **Why it matches**: one sentence from the reranker, in the user's language | The feature that sets the project apart |
| 3rd | **3–4 matching taste tags** as chips (mood, genre, setting, era) | Tappable (see *Refine*) |
| 4th | **Premise**: 2 lines, expandable | Spoiler-free (D-003) |
| 5th | **Source line**: `Premise based on: Rokomari / Wikipedia (CC BY-SA)` with a link, plus a store link if available | Attribution close to the text; shows the premise isn't invented |
| — | 👍 / 👎 | See *Feedback* |

Five cards per search.

## States
| State | Behaviour |
|---|---|
| **Loading** | Retrieval results (title + tags) appear immediately. Each card shows a small "writing reasons…" placeholder, filled as the reranker streams. The page is never blank. |
| **Weak or no match** (retrieval scores below a threshold) | Say it plainly: "No strong match for *X* in our 9.5k books". Then show the 2–3 closest results labelled **"loosely related"**, and 3 clickable rephrasings. Never invent a book. |
| **Out of scope** (not about books) | A friendly one-line redirect back to book search, plus the example queries. |
| **"Similar to X", with X misspelled or ambiguous** | A **"Did you mean"** picker: up to 3 candidates (title, author, year) from fuzzy matching over Bangla titles, romanised aliases and authors. |
| **"Similar to X", with X not in the catalogue** | Say so, and fall back to treating the text as a taste description. |
| **LLM error or timeout** | An error message with a **retry** button. |

## Refining (the first 5 minutes)
- **Tapping a tag chip** on a card adds that tag as a filter; tapping it again in the filter bar removes it.
- **"More like this"** on each card runs a similar-to-X search for that book.
- **Quick toggles** above the results: audience (teen / adult) and origin (Bangladesh / West Bengal / translated).
- These all use the fixed tag vocabulary ([04](04-tag-vocabulary.md)); there is no free-form chat refinement in the first version.

## Feedback (the ongoing relationship)
- 👍 / 👎 on each card. After 👎, an optional one-tap reason: `already read` · `wrong mood` · `wrong genre` · `not interested`.
- Logged with the query and the card's rank, which grows the evaluation set (Phase 2).

## Typography and layout
- **Font:** Noto Sans Bengali, with a Latin fallback for mixed text.
- **Mobile first:** a single column. The desktop view is the same column, centred.
- Accessibility (contrast, keyboard focus, touch sizes, `lang="bn"`, page weight) is **deferred** and listed below as unresolved.

---

## DESIGN REVIEW REPORT
Reviewed 2026-09-26 with the `plan-design-review` method. The plan had one line of UI ("Simple web UI or Messenger bot").

| Pass | Before | After | What changed |
|---|---|---|---|
| 1. Information architecture | 2 | **7** | First screen and result-card hierarchy defined |
| 2. Interaction states | 1 | **7** | Loading, weak/no match, out of scope, did-you-mean, not in catalogue, LLM error |
| 3. User journey | 2 | **7** | Example queries (first 5 s), chip refinement and more-like-this (first 5 min), feedback (ongoing) |
| 4. AI-slop risk | 4 | **6** | Explained matches and taste-tag chips give it a point of view; no hero or feature grid |
| 5. Design system | 3 | **4** | Font chosen; no spacing or type scale yet |
| 6. Responsive and accessibility | 1 | **3** | Mobile-first single column; accessibility deferred |
| 7. Unresolved decisions | 2 | **6** | Platform, card content, attribution and feedback decided |

**Decisions (11):** mobile-first web · card order title → reason → tags → premise → source · honest fallback for weak matches ·
input + 4 example queries · progressive loading · tag chips + more-like-this + toggles · did-you-mean picker ·
font + mobile only · LLM error → message + retry · source line per card · 👍/👎 + optional reason.

**Still unresolved:**
1. **Accessibility**: contrast (WCAG AA), keyboard focus, 44px touch targets, `lang="bn"`, first-load weight. Deferred by choice; needs deciding before the demo is shared publicly.
2. **Loading vs error:** with progressive loading, the matches are already on screen when the LLM fails. It's undecided whether the error message replaces the matches or sits above them. A reasonable default is to keep the matches and show the message with retry where the reasons would go, but that needs your call.
3. **Type scale and spacing**: body size, line height for Bangla conjuncts, spacing. Only the font is fixed.
4. **The weak-match threshold** needs a value, which can only be set from real scores once retrieval exists (Phase 3).
5. **English UI text:** whether interface labels are Bangla-only or switch with the query language.

**Verdict:** ready to build the Phase 4 demo against for layout, content and states; accessibility and the loading/error interplay need deciding first.
