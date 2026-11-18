# Lab Revisions and Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Lab keeps a coherent proposal lifecycle (revise without losing information, unambiguous superseded/withdrawn/confirmed states, server-refused stale confirmations), answers in concise prose with records behind a disclosure and one current action card, and makes case state and navigation understandable; Tony's applicable ideas are built in and the rest recorded.

**Architecture:** The records server owns the lifecycle (`preparations` history on the request, `dueNow`/`originalDue`, duplicate flag, code-generated "still holds?" question, `raiseConcern`), exposed through the existing tool surface. The Lab service passes the richer case state to the model and the UI. The UI renders prepared cards from live state and folds retrievals.

**Tech Stack:** as the first Lab plan (Python 3.12 stdlib records; Lab venv with pydantic-ai-slim 2.58.0; assistant-ui 0.15.30 + Vite; Playwright checks).

**Spec:** `docs/superpowers/specs/2026-10-21-lab-revisions-and-presentation-design.md` (§3 decisions 1–5, §4, §5).

## Global Constraints

- Fictional data; no secrets; relative URLs; Arial; no inline styles; 375/390 px fit; the records server stays stdlib-only; pinned Lab dependencies.
- Existing tests and checks keep passing: records suite 443 → grows; Lab tests 87 → grows; `desk_check` 74/74; `lab_check` 58/58 → grows; `lab_conversation_check` mock 188/188 → grows; `ui_check` 150/150; `layout_check --seed` 217/217.
- Boundaries: the owner alone confirms, only through `decide` with the current version; staff never receive owner-only items (preparations, their history, limits, suggestions); every figure computed by code; no phrase-specific guards for the review's sentences; no new mandatory tool calls as a presentation fix.
- Prompts recorded verbatim in PROMPTS.md (`lab-v0.3`, `coordinator-v0.5` unchanged unless a desk block changes); scratch servers only for write-capable checks.
- Commit after each task; implementers never push or deploy.

## Review Focus

1. A revision that supplies only `days` keeps outcome and reason; one that supplies a reason equal to the current one keeps it; one that supplies a new reason in the person's words replaces it; a reason in neither place → `NO_REASON` as today. (Task 1 test.)
2. After `prepareDecision` v1, v2 and `withdrawPreparation`, `decide` with `preparedVersion` 1 or 2 → 409 and no decision; the history reads v1 superseded, v2 withdrawn. (Task 1 test; Task 4 browser check after refresh and navigation.)
3. Staff `caseDetails` never carries `preparations`, `dueNow` from an owner-only limit (it is from the decision, which staff may see), or the concern text of another staff member? Concerns are staff-visible by design; preparations are owner-only. (Task 1 test.)
4. The folded "Records" disclosure never hides the one current action card; a superseded card never shows a button even when it is the latest card on screen. (Task 3 test.)
5. The duplicate flag never blocks or merges intake; two requests on one invoice both open and both appear in the queue with distinct titles. (Task 1 test; Task 3 sidebar test.)

---

### Task 1: Lifecycle, state and the records-side ideas

**Files:**
- Modify: `prototype/server.py` (`_prepareDecision` revision semantics and reason grounding; `preparations` history with statuses and events `decision.prepared`, `decision.superseded`, `decision.withdrawn`, `decision.confirmed`; `decide` marks `confirmed`; `case_situation`/`caseDetails` return `preparations` (owner only) and `active` version; `summary(r)` gains `originalDue`, `dueNow`, text forms, `secondRequest` ordinal and `flags.duplicateIntake`; `openRequest` duplicate check; `raiseConcern` tool (staff; stores a case line `kind: 'concern'` visible to all, event `concern.raised`, owner queue reason); the needs step adds the code-generated "still holds?" question for cited lines that are expectations about the future (kind `expectation`) or older than 30 days, `from: 'code'`, deduplicated per line id; answering it records a case-scoped line), `prototype/coordinator.py` (registry entry for `raiseConcern`: staff, act, no confirmation; tool schema; mock rule "concern|worried|flag" → raiseConcern; `DESK_SYSTEM` one line for it), `prototype/web/desk.js` and `requests.js` only if the case page must show `dueNow` (it should: "Due now" line; keep the desk check green).
- Test: `prototype/test_preparations.py` (new), updates to `test_tool_surface.py`, `test_prepared_actions.py`, `test_desk_api.py`, `deploy/desk_check.js` (one check: a revised preparation keeps its reason; the page shows "Due now" after a decision).

**Interfaces:**
- Produces on the request: `preparedDecision` (current or absent), `preparations: [{version, status: 'current'|'superseded'|'withdrawn'|'confirmed', outcome, approvedDueDate, approvedDueDateText, days, reason, by, at, replacedBy?, decidedAt?}]`.
- `prepareDecision(requestId, outcome?, days?|date?, reason?)`: with a current preparation, missing fields are retained; the result carries `prepared` (the new current), `revisionOf` (the previous version or null) and `retained: ['reason', …]`.
- `caseDetails` result for the owner: `preparations`, `activePreparation` (version or null); `summary` fields `originalDue`, `originalDueText`, `dueNow`, `dueNowText`, `dueNowFrom: 'invoice'|'decision'`, `ordinal` (1 for the first open request on an invoice, 2 for the second…), `flags` incl. `{kind: 'duplicateIntake', requestId: <the other>}`.
- `raiseConcern(requestId|'current', text)` → `{requestId, invoiceReference, line: {id, quote, kind: 'concern', by: 'staff', at}, subject}`; the owner's `workQueue` lists the case with `why: 'staff raised a concern'`.
- The "still holds?" question: `{id, from: 'code', kind: 'check', lineId, question: "On <said date> you said '<quote>'. Does that still hold for this request?", status: 'open'}`; answer route unchanged.

- [ ] Tests first (Review Focus 1, 2, 3, 5; the question appears for an expectation line and not for a plain observation of today; `raiseConcern` staff-only and in the owner queue; `dueNow` after a decision; `ordinal` and `duplicateIntake` for a second open request on DEMO-101).
- [ ] Implement; run the named tests, the full records suite, `desk_check` on a scratch mock server; commit.

### Task 2: Lab service: state to the model, tools, progress vocabulary

**Files:** `lab/tools.py` (`raiseConcern` for staff; `prepareDecision` passes `reason` through unchanged, including "the same reason" resolved by the model from the prelude's active preparation), `lab/prompts.py` (`LAB_VERSION = 'lab-v0.3'`; the prelude renders the active preparation and the history with statuses, `dueNow`/`originalDue`; rules: when a card carries the figures, one or two sentences; explain the history from the prelude; never explain the screen beyond what the state says; revisions keep what was not asked to change; a staff concern is raised with `raiseConcern`), `lab/agent.py`/`lab/app.py` (the `reply` event carries `cards: [{kind, primary: bool}]` chosen by code per §3.3, and `activity: [{tool, label}]` with the human labels; the `tool` event carries `label`), `lab/guard.py` (no new guards; the figure rule already counts the prelude), tests.
- [ ] Tests first (FunctionModel: a revision call keeps the reason; the prelude text contains the history; staff cannot see `preparations`; the reply event's `cards` marks the prepared card primary and folds the reads; the progress labels map every tool).
- [ ] Implement; run Lab tests and the records suite; commit.

### Task 3: UI: prose first, live-state proposal cards, understandable navigation

**Files:** `lab/web/src/*` (message layout: prose, then the primary/action card if any, then a closed `<details>` "Records (N)" with the folded cards, then a closed "Activity" with the tool list; progress lines during a run; prepared card rendered from the live case state (`GET records/api/requests/{id}` or the `caseDetails` result of the latest turn) by version with the four statuses and the button only for `current`; after a Confirm or a withdraw, every prepared card in the thread re-renders; thread sidebar titles from the server's richer title; a case header at the top of a case thread (reference, customer, status label, due now, asked date, amount with mark); the "About" chip for the customer switch), `lab/store.py`/`lab/app.py` (thread titles with status and asked date and the ordinal), `lab/web/src/styles.css`, `deploy/lab_check.js` (checks: after v1 → v2 → withdraw the thread shows "Superseded by version 2" on the first card and "Withdrawn" on the second with no buttons, after navigation away and back, and after a page reload; a stale Confirm forced through the API gets 409 and the UI shows the message; a folded "Records (N)" by default for a question; the primary card open for a list request; the case header; two DEMO-101 threads with distinct titles; 390 px).
- [ ] Tests (the check) first; implement; build; run `lab_check`; commit.

### Task 4: Scenarios, live run, screenshots

**Files:** `deploy/lab_conversations.json` (+ the reviewer's DEMO-201 sequence verbatim; a revision that changes only the date; "keep the same reason"; withdraw then re-prepare; the "still holds?" question answered; staff raising a concern and the owner seeing it in the queue; brief answers asserting one card at most open; a comparison that is the answer; a short script), `deploy/lab_conversation_check.js` (assertions: `cardsOpen` (count of primary/action cards), `preparationStatuses`, `retained`, `concernInQueue`, `questionFromCode`), `docs/qa/LAB-CONVERSATIONS.md` (new section with mock and live results and the transcripts).
- [ ] Run mock (all pass) and live; take screenshots of the four presentation cases with Playwright at 1366 and 390 px into a scratch folder for the controller; commit.

### Task 5: Records

**Files:** `PROMPTS.md` (`lab-v0.3`), `docs/DECISIONS.md` (E023: this iteration, causes, decisions, Tony's ideas adopted/clarify/future), `docs/reviews/2026-10-21-tony-questionnaire-response.md` (new: what we adopted, what needs the team, what is future; concise, for the team's notes), `docs/AGENT-COORDINATOR-PROPOSAL.md` (revision 6, short), `lab/README.md`, `prototype/README.md`, `docs/DEPLOYMENT.md` (Lab section: Deployed/Verification placeholders for the controller), `docs/project-state.json` + build.
- [ ] Write; commit.
