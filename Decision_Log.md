# Founder BI Agent — Decision Log

*Skylark Drones — Full-Stack Assignment*

## Key Assumptions

1. The two monday.com boards (Deal Funnel, Work Order Tracker) are configured with column titles matching the source spreadsheets exactly (e.g. "Sector/service", "Deal Stage", "Masked Deal value"). The agent maps GraphQL column titles directly to DataFrame columns rather than using a configurable schema, so an exact title match is required for calculations to run.
2. Deals and Work Orders are treated as two independently tracked funnels. No explicit deal-to-work-order mapping exists in the source data, so the agent never assumes or states that a specific deal "converted into" a specific work order — cross-board analysis compares sector-level aggregates only.
3. "Won" and "Lost" deal outcomes are represented literally in the Deal Status column (matched case-insensitively). If an account uses different phrasing for closed deals, those two specific metrics would need remapping.
4. Sector is the natural join key across boards: "Sector/service" on the Deal Funnel board and "Sector" on the Work Order board are treated as the same business dimension for cross-board comparison.
5. Read-only access to monday.com is sufficient. The agent never writes back to either board, consistent with the assignment's read-only integration requirement.
6. A single Groq-hosted model (`openai/gpt-oss-120b`) is fast and inexpensive enough to handle both query planning and answer generation within a conversational latency budget, without needing separate models for each stage.

## Trade-offs Chosen and Why

### Deterministic BI Engine vs. LLM-computed metrics

Every business number is computed in pandas (`bi_engine.py`) and only handed to the LLM for phrasing, rather than letting the LLM query or aggregate data directly. This is less flexible for open-ended novel calculations the BI Engine doesn't already support, but it eliminates hallucinated numbers — which matters more for founder-facing figures than flexibility does.

### In-memory session context vs. persisted

Conversation context (sector, intent, boards) is kept in a plain in-process dictionary keyed by session ID. This was the fastest option to build and is sufficient for a single-instance prototype, but it does not survive a backend restart and would not scale across multiple server instances.

### Direct GraphQL API vs. MCP

Implemented a direct Monday.com GraphQL client instead of integrating monday's MCP server. This means owning more integration code, but it avoids depending on MCP server setup/availability and keeps the whole system deployable as one simple hosted API — a better fit for a single hosted-prototype deliverable on a tight timeline.

### Live fetch on every query vs. caching

Every `/api/chat` call re-fetches both boards from monday.com live, rather than caching. This guarantees the founder is always looking at current data (the point of a "live BI agent"), at the cost of extra latency and API load under high query volume.

### Exact sector matching vs. fuzzy matching

Sectors are validated against the live, dynamically discovered list rather than a hardcoded one, which prevents the LLM from inventing sectors. The trade-off is that near-duplicate sector spellings (e.g. "Renewables" vs. "renewable energy") would currently be treated as two different sectors rather than merged.

## What I'd Do Differently With More Time

- Add automated tests for BI Engine edge cases: empty boards, fully-null columns, and mixed-unit quantity fields (e.g. "5360 HA") that appear in the raw data.
- Add retry/backoff and a friendlier error layer for monday.com API failures, instead of surfacing raw exception text through a 500 response.
- Introduce a configurable column-mapping layer so the agent isn't tightly coupled to exact monday.com column titles, and can survive board renames without a code change.
- Persist conversation context (e.g. Redis) so follow-up questions survive backend restarts and work across multiple deployed instances.
- Add sector name normalization (fuzzy matching or an alias table) so near-duplicate sector spellings don't fragment sector-level reporting.
- Extend the BI Engine with time-series metrics (quarter-over-quarter or month-over-month trends), which founders ask for at least as often as point-in-time snapshots.

## Interpretation of "Leadership Updates"

I interpreted this optional requirement as giving the founder a lightweight way to turn a live BI conversation into something shareable, rather than building a separate report-generation subsystem. Concretely, the Streamlit interface includes a "Download Chat as Markdown" control that exports the full question-and-answer session — including the verified metrics and any data-quality caveats surfaced along the way — as a single Markdown file.

This lets a founder ask a handful of questions ("how's pipeline looking for renewables," "what's our collection rate"), then hand the resulting document straight to their team as a leadership-ready update, without any extra formatting step. Given the six-hour timeline, I prioritized this capture-and-export approach over a dedicated "generate leadership report" feature that would auto-summarize across every sector into a formatted briefing — that's the natural next feature to build if extending this project.
