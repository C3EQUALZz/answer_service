# Analytics — Glossary

The Analytics context records what users asked and what came back, so the
service can report on its own usage and — more usefully — on its own gaps.

It **observes**: it never influences a search or an answer. A failure to record
must never fail the request that was already served.

## Terms

- **Query Log** — one recorded request: its text, kind, outcome, latency and
  optional category. The only entity in this context.

- **Query Text** — what the user asked, as stored for reporting. Its own value
  object rather than the search context's *Search Query*: the log outlives the
  search, and must not break when the search context changes what it accepts.

- **Query Kind** — which entry point served the request: `search` or `ask`.

- **Query Outcome** — how many results came back and the best score among them.
  A `top_score` is absent exactly when nothing was found.

- **Unanswered** — a query whose outcome had zero results. The central concept
  of this context: an unanswered query is a **gap in the catalog**, not a system
  failure, and the list of frequent unanswered queries is the content backlog.

- **Latency** — how long the request took, in milliseconds. Never negative.

- **Period** — the half-open window `[start, end)` a report covers. Half-open so
  consecutive periods tile without counting a boundary query twice.

## Why there is no Statistics aggregate

Statistics are **derived**, not owned. Totals, rates and rankings are computed
from Query Logs at read time by the query gateways, which push the aggregation
into the database.

Modelling them as a stored aggregate would mean keeping the same fact in two
places — the log entries and the running totals — and reconciling them forever.
The cost of computing on read is bounded by an index; the cost of a wrong
counter is silent, permanent, and only discovered when someone checks by hand.

## Relationships

- **Search** and **Conversation** produce the outcomes recorded here. The only
  thing crossing the boundary is primitive data (text, counts, durations) —
  Analytics imports nothing from either context.
- The **catalog half** of the statistics report comes from Indexing, counted
  live. A QA pair has no history in this model, so the catalog is always
  reported as of *now*, never as of a past period.
