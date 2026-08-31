# Decision Log — monday-bi-agent

*Skylark Drones Full-Stack Assignment*

> This log is written to fit ~2 printed pages in its main body. Deeper detail (full debugging trace, complete verification numbers) is folded into collapsible sections and the appendix so the core reasoning stays scannable.

---

## 1. Assumptions

- **Two boards, no explicit link field.** The Deals and Work Orders data were provided as separate spreadsheets with no shared key beyond a loosely matching sector taxonomy. I assumed they are *related but not joinable at the row level*, and designed cross-board answers (e.g. "sectors with deals but no work orders") around sector-level set comparison rather than inferring a deal → work-order mapping the data doesn't support.
- **"Live" means query-time, not pre-synced.** I interpreted the requirement literally: every question triggers a fresh GraphQL fetch from monday.com. I did not build a background sync/cache layer, trading some latency for a simpler, more obviously-correct "no stale data" guarantee.
- **Founder questions are underspecified by default.** I assumed the target user asks things like *"how's Mining doing"* rather than well-formed analytical queries, so the query planner treats ambiguity as the default case to check for, not the exception.
- **Sector list is ground truth from the data, not hardcoded.** Given the brief's warning about messy/changing data, I assumed sector names could differ from what I'd expect from reading the spreadsheet once, so the agent always validates against the live, dynamically-fetched sector list.

---

## 2. Architecture Decisions & Trade-offs

| Decision | Alternative considered | Why chosen | Trade-off accepted |
|---|---|---|---|
| Compute metrics in Python (`bi_engine.py`), use LLM only to narrate | Let the LLM compute directly from raw data in-context | Removes the single biggest hallucination risk — the LLM never invents a number | More code to write per new metric type; less "flexible" for truly novel ad-hoc questions |
| Two-stage LLM pipeline (planner → narrator) | Single LLM call doing everything | Clean separation between "what is being asked" and "how to explain the answer"; makes clarification-detection reliable | Two API calls per question → higher latency and cost |
| Fetch live from monday.com on every query | Sync to a local DB / cache on an interval | Guarantees freshness, matches the brief's explicit requirement | Slower responses on large boards; API rate-limit exposure under heavy use |
| In-memory `conversation_contexts` dict | Redis / persistent session store | Fastest to build within the 6-hour window | Context lost on restart; doesn't scale past one server instance |
| Column matching by title string | Match by monday.com's stable column `id` | Titles are human-readable and matched the original CSV headers I was given | **This decision caused a real bug** — see §3 below |

---

## 3. Data Resilience: What Actually Broke, and Why

This section is the most concrete evidence of how the agent handles messy data, because it's a real debugging trace, not a hypothetical.

<details open>
<summary><strong>Bug 1 — Sector hallucination on invalid input</strong></summary>

Asking about a nonexistent sector ("Aerospace") originally returned a confident-sounding zero instead of flagging the sector didn't exist. **Fix:** validate the requested sector against the live sector list before computing anything; return a clarifying response listing the real sectors on a miss.
</details>

<details open>
<summary><strong>Bug 2 — Sticky sector context</strong></summary>

A company-wide question asked immediately after a sector-specific one (e.g. "what's our collection %" right after a Mining question) incorrectly inherited the Mining filter. **Fix:** the query planner now re-evaluates scope per question rather than defaulting to "same as last time" unless the user gives an explicit follow-up cue ("what about them", "and for that sector").
</details>

<details>
<summary><strong>Bug 3 — Cross-board context leak</strong></summary>

A follow-up company-wide question asked after a *cross-board* comparison question also leaked sector scope, in `main.py`'s session-context merge logic specifically (separate code path from Bug 2). Fixed the same way, applied to the cross-board branch.
</details>

<details>
<summary><strong>Bug 4 — Ranking query misroute</strong></summary>

"Which sector has the largest outstanding billed value" was being routed to the wrong metric calculation. Fixed by tightening intent classification for ranking/superlative questions ("largest", "highest", "most") to route to a dedicated ranking function rather than a generic sector-summary function.
</details>

<details open>
<summary><strong>Bug 5 — Column title mismatch (the big one)</strong></summary>

The agent's `Monday_client.py` maps monday.com column data into a DataFrame using each column's live **title**. When the boards were created from the provided Excel files, monday.com's import step silently gave the status/date columns **generic default titles** (`Status`, `Date`) instead of preserving the original names (`Deal Status`, `Execution Status`, `Data Delivery Date`).

Downstream, `cleaner.py` and `bi_engine.py` looked for the literal expected names, found nothing, and — correctly, per the "don't guess" requirement — reported the field as unavailable rather than fabricating an answer. That's the *system* working as designed even while the *root cause* was upstream, in the board setup, not the code.

**Fix applied:** renamed the columns directly on the monday.com boards to match expected names — fast, but brittle (anyone renaming a column again silently reintroduces the bug).

**Robustness fix identified but not yet shipped:** match columns by monday.com's stable column `id`, or normalize titles (lowercase, strip whitespace, alias table) instead of requiring an exact string match. This is the correct long-term fix and is called out in the Roadmap.
</details>

<details>
<summary><strong>Bug 6 — Embedded duplicate header rows</strong></summary>

Two rows in the raw Deals data contained the literal text `"Deal Status"` in the status column — a spreadsheet artifact, not a real deal. Left unhandled, these either miscount as a 12th "sector" or as a deal with a nonsense status. **Fix:** `cleaner.py` filters rows where a status column's value equals that column's own name.
</details>

<details>
<summary><strong>Bug 7 — Stray placeholder items on freshly-created boards</strong></summary>

New monday.com boards can auto-seed with placeholder items not present in the source file, inflating item counts (347 live vs. 346 in the raw file). Caught by cross-referencing the live item count against the raw file's row count directly rather than trusting either number in isolation. **Process fix, not a code fix:** manually audit and delete stray items after board creation — flagged in the README setup instructions so it isn't repeated on a fresh deploy.

⚠️ **Lesson learned the hard way:** during cleanup, 2 extra items were accidentally deleted along with the genuine strays, silently dropping the "Won" count by 2. This is exactly the kind of silent, hard-to-notice data corruption the assignment is testing awareness of — caught only by cross-checking totals against the original file's ground-truth status distribution, not by trusting the live count.
</details>

**Net effect:** every one of these was caught by **cross-referencing the agent's output against the raw source file**, not by trusting either side alone. That cross-referencing habit is the actual deliverable here, more than any single bug fix.

---

## 4. "Leadership Update" Feature — Interpretation

`[TODO: confirm final interpretation and implementation status before submitting]`

The brief leaves this open-ended. My interpretation: **`[e.g. "a leadership update is a founder-facing digest that surfaces the 3–5 things a leadership team would want to know without asking" — describe what was actually built: a summarization endpoint? a specific query pattern? Fill in based on what's implemented.]`**

If not implemented in the current prototype, state that explicitly here rather than leaving it ambiguous — a documented decision not to build something is still a decision.

---

## 5. What I'd Do Differently With More Time

- **Match monday.com columns by ID, not title**, from the start — would have prevented Bug 5 entirely rather than requiring a live debugging session to catch it.
- **Persist conversation context** outside process memory so it survives restarts and scales past a single instance.
- **Automate the verification checklist** (Appendix A) as a real regression test suite that runs against the live boards, instead of manually re-asking questions after every board edit.
- **Add a lightweight cache with a short TTL** on board fetches — the "live" requirement doesn't strictly require *zero* caching, just no staleness a user would notice, and this would meaningfully cut latency.
- **Surface data-quality caveats more structurally** — right now caveats are generated by the narrator LLM from instructions; a more robust version would compute a "data completeness score" per answer as a first-class field in the BI engine's output, not just prose.

---

## Appendix A: Verification Checklist (ground-truth values)

Computed directly from the source Excel files, used to regression-test the live agent after every board change.

| Query | Expected |
|---|---|
| Total deals in pipeline | 344 (165 Won, 127 Dead, 49 Open, 2 On Hold, 1 unknown) |
| Deals won | 165 |
| Deals lost | 127 |
| Company-wide collection % | 71.36% (₹126,719,936.37 billed, ₹90,428,187.50 collected) |
| Sector with largest outstanding billed value | Renewables, ≈ ₹20,823,562 |
| Sector with highest billing % | Construction, 100% |
| Sector with most work orders | Mining, 100 |
| Powerline billing % | 17.42% |
| Powerline execution status breakdown | Ongoing ×3, Completed ×2, Not Started ×1 |
| Sectors with work orders but no pipeline deals | None (full overlap) |
| Sectors with pipeline deals but no work orders | Aviation, DSP, Manufacturing, Security and Surveillance, Tender |
| Sticky-context regression check | Asking a company-wide question right after a sector-specific one must not inherit that sector's filter |

*(Full raw computation available on request — derived directly from `Deal_funnel_Data.xlsx` and `Work_Order_Tracker_Data.xlsx`.)*
