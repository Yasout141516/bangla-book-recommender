# 01 Project overview

## Problem
Bangla readers find books through word of mouth, Facebook groups ("suggest me a book like…")
and bookstore categories. Existing "similar books" features (Rokomari, Goodreads) rely on
category and purchase data, not on what a book is actually like. No known tool lets a reader
search Bangla books by the taste they want.

## Goal
A search and recommendation tool for Bangla books that supports:
1. **Search by description:** the user describes plot, mood, setting or theme in Bangla, English or
   romanised Bangla, and gets matching books.
2. **Search by example:** the user names a book, author or series, and gets books similar in taste.
3. **Explained results:** each suggestion comes with a short reason ("Like X because…").

## Scope

### In scope
- Bangladeshi books
- West Bengal (Indian Bengali) books
- Books translated into Bangla, and adaptations (e.g. Sheba Prokashoni)
- Fiction first; non-fiction may come later
- Metadata only: title, author, genre, premise, tags, reader signals

### Out of scope
- Full book text, or question answering over book contents
- Spoiler plot summaries (see decision D-003)
- Selling books. We may link to stores later.

## Users
- General Bangla readers looking for their next book
- Teen readers (needs audience and content-note filters)
- Members of book communities who answer "suggest me a book" posts

## Core pipeline
```
query (bn / en / romanised)
  → LLM query understanding: search text + filters (genre, audience, era…)
  → hybrid search (dense + sparse) over the embedded premise + tags, with filters
  → top ~30 candidates
  → LLM rerank → top 5 with a reason for each, in the user's language
```

## User experience
The demo's screens, result card, states and feedback are specified in [12 UX plan](12-ux-plan.md).

## Success criteria (first version)
- Recall@10 on a test set of 100–200 real "suggest a book like…" queries
- In a blind comparison, readers prefer our top 5 over a bookstore's "similar books"
