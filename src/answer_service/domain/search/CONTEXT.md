# Search — Glossary

The Search context turns a user query into a ranked list of QA pairs by fusing
two independent retrievers. It is stateless: no aggregates, no persistence — the
domain owns the *ranking*, the application owns calling the stores.

## Terms

- **Search Query** — the user's free-text query. Must be non-empty.

- **Top K** — how many results to return; between 1 and 20.

- **Category Filter** — an optional category the search is restricted to.

- **Search Criteria** — a fully-validated request: Search Query + Top K +
  optional Category Filter.

- **Retriever** — a source of candidates. There are two kinds:
  - **Dense** — semantic / vector similarity.
  - **Lexical** — full-text / keyword match.

- **Scored Candidate** — one hit from a single retriever: an External Id plus
  that retriever's Score. Candidates arrive already ordered by score.

- **Score** — a single relevance number produced at some ranking stage (a
  retriever's raw score, or the fused score). Must be finite.

- **Fusion** — combining the dense and lexical candidate lists into one ranking.
  The chosen algorithm is **Reciprocal Rank Fusion (RRF)**: each candidate scores
  `1 / (k + rank)` per retriever it appears in, summed. Rank-based, so it is
  immune to the two retrievers' different score scales.

- **Scores** — the breakdown behind a ranked result: the original **dense** and
  **lexical** scores (either may be absent) and the **final** fused score.

- **Ranked Result** — a QA pair at a definite 1-based position in the final
  ranking, with its Scores. Identified by External Id; question/answer text is
  joined in by the application.

- **Search Outcome** — the query together with its Ranked Results.

## Rules

- Ordering is **deterministic**: sorted by final score descending, ties broken
  by External Id ascending — equal scores never reorder between runs.
- **No results** is a valid outcome (an empty Search Outcome), never an error.
- Request id and duration are application concerns, not part of this context.
