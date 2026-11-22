# GraphOne Intelligence Architecture

## 1. Scaling to 500,000+ records

Workers are stateless and consume Redis-coordinated Celery tasks. PostgreSQL uniqueness constraints provide the distributed deduplication boundary. Add API and worker replicas horizontally; partition timestamp-heavy tables and move archival data to object storage when a production row volume requires it. Qdrant remains optional for semantic retrieval and is never authoritative.

## 2. Distributed asynchronous ingestion

Adapters implement one source contract and are dispatched through bounded aiohttp and Playwright clients. Celery coordinates workers, Redis coordinates queues and rate limits, and source checkpoints persist cursor and freshness state. Every write is idempotent and retried transactionally.

## 3. Payload and freshness handling

LLM text is split into provider-specific token-bounded chunks with semantic boundaries and overlap. HTTP 413 payload failures stop the provider attempt and trigger smaller chunks or fallback. HTTP 429 responses respect `Retry-After`, otherwise use bounded exponential backoff.

News and jobs must have a separately verified original publication timestamp in UTC and remain within the inclusive 24-hour window. Missing or unverifiable dates enter quarantine; updated timestamps are retained separately and never replace publication timestamps.

## 4. Storage and entity decisions

PostgreSQL is authoritative for provenance and uniqueness. JSONB preserves raw source evidence. Redis supports queues and coordination. Qdrant may support similarity search only, not canonical identity. Exact normalized names and aliases are resolved before conservative RapidFuzz matching. Ambiguous matches enter human review.

## 5. Anti-bot and access policy

Official APIs, RSS feeds, and permitted public pages are preferred. Playwright is disabled unless explicitly enabled and authorized. Concurrency and per-domain pacing are bounded. CAPTCHA, access denial, 403, 429, Cloudflare, and DataDome signals stop or quarantine the task rather than bypassing controls. Circuit breakers and retry checkpoints prevent repeated blocked requests.
