# Context Map

`answer_service` is a modular monolith. The domain is split into bounded
contexts, each an isolated package under `src/answer_service/domain/` with its
own glossary (`CONTEXT.md`), value objects, entities, events and errors. Shared
building blocks (Entity, Aggregate, ValueObject, Event) live in
`domain/common/`.

| Context | Package | Responsibility | Glossary |
|---|---|---|---|
| **Indexing** | `domain/indexing/` | Loading the source file into the QA catalog and keeping the search stores in sync (create / update / delete), tracking each synchronization run. | [CONTEXT.md](src/answer_service/domain/indexing/CONTEXT.md) |
| **Search** | `domain/search/` | Hybrid retrieval: dense (vector) + lexical (full-text) candidate generation and their fusion into a single ranking. | [CONTEXT.md](src/answer_service/domain/search/CONTEXT.md) |
| **Conversation** | `domain/conversation/` _(planned)_ | RAG dialogue: turning a question plus retrieved context into a grounded answer with cited sources. | — |
| **Analytics** | `domain/analytics/` | Recording every search / ask request, so the service can report its usage and — more usefully — the gaps in its catalog. | [CONTEXT.md](src/answer_service/domain/analytics/CONTEXT.md) |

## Relationships

- **Search** consumes the catalog produced by **Indexing** (via the search
  stores), but shares no code with it — only the `external_id` identity crosses
  the boundary.
- **Conversation** uses **Search** to retrieve context, then generates an
  answer; sources are referenced by `external_id`.
- **Analytics** observes **Search** and **Conversation** outcomes; it never
  drives them. Only primitive data crosses the boundary — Analytics imports
  nothing from either context, and holds no aggregate: statistics are derived
  from Query Logs on read rather than stored and reconciled.

## Infrastructure choices (see `docs/adr/`)

- Search stores: **Qdrant** (dense) + **PostgreSQL full-text search** (lexical).
- Sync source of truth: a **PostgreSQL catalog** of QA pairs (diffed against the
  file; deletes are the set difference).
- Fusion: **Reciprocal Rank Fusion (RRF)**.
