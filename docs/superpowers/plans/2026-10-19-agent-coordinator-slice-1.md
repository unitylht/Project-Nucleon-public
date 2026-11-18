# Agent coordinator, first slice — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On fictional data, the agent coordinates the extension workflow using the owner's unstructured context, asks only what it needs and says why, gives an advisory suggestion the owner can take or leave, answers staff questions in their own words, and the owner and staff measurably do less than on the current interface.

**Architecture:** Additive. A new `coordinator.py` holds the five model tasks (route a turn, interpret a statement, plan needs, suggest, nothing else) with JSON schemas, code-side validation and deterministic mock behaviour; `server.py` gains three stores (statements, threads, turns), a desk API, owner questions and the suggestion step; `web/desk.js` is a new Requests area over the same request records. Money, state and authority stay in code: the model proposes, code classifies and verifies, people confirm.

**Tech Stack:** Python 3.10+ standard library, SQLite, vanilla JS; Playwright for browser checks (`NODE_PATH=/Users/jason/Documents/aiRP/tests/ui/node_modules`); runtime `~/srv/nucleon/runtime/python-3.12.14/bin/python3`; unit tests `cd prototype && python3 -m unittest discover -q`.

**Spec:** `docs/AGENT-COORDINATOR-PROPOSAL.md` (P003 revision 2) plus the team's decisions of 19 October recorded in `docs/DECISIONS.md` (P003 entry, E017) and in §0 below.

## §0 Decisions since revision 2 (team, 19 October, second message)

- Newly captured owner context is **owner-only by default**; migrated/existing notes keep their current (staff) visibility. Visibility is set **per statement**, not per line; staff-visible content must not expose private source text through citations, explanations or answers.
- A decision or clarification answer is **case-scoped by default**; the owner may explicitly keep guidance for that customer; business-wide is only in the Knowledge area. **Retaining an outcome ≠ retaining reusable guidance**; a remembered approval never implies permission for future cases.
- **No hosted endpoint or key.** Keep the endpoint configurable; describe hosted compatibility as untested.
- Staff questions: the four categories are the **capability scope, not fixed utterances**; natural phrasing and follow-ups within scope; clear explanation when unsupported.
- "Needed to act" stays empty in this slice; the owner decides. Keep advisory suggestion, owner decision and external action distinct.
- Evaluation: same scenarios on both interfaces; owner effort primary; also whether work shifted to staff, whether the result is correct, and whether users understand what the system did.

## Global Constraints

- Fictional data only; never commit credentials, codes, the private ledger, or private transcripts. Access codes never in screenshots or docs.
- The model never writes a number, date, amount, term, coverage or authority that reaches a person unverified; every quote must `appears_in` its source; `prose_problems` applies to every model sentence shown to a person (`agent.py:597`).
- Server-controlled fields (`businessId, actorId, runId, requestId, requestVersion`) are never model-supplied.
- Existing routes, payloads, `brief-v2` reading, tests (`test_*.py`) and release checks keep passing; `#/case/<id>` and the queue stay reachable.
- Arial; CSP `style-src 'self'`: no inline styles or scripts; dynamic positions through CSSOM only.
- Dates: `YYYY-MM-DD`; money `{minorUnits, currency, scale}`; unknown is `null` plus a reason, never 0 or an invented date.
- Statement and line dates use the workspace business date (`App.today(doc)`); `now()` is the audit timestamp.
- Prompt and schema changes are recorded in `PROMPTS.md` with a version (`coordinator-v0.1`; extraction stays `extension-v0.3`).
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (implementers: the harness tells you the current attribution line; use that).
- Branch: `explore/agent-coordinator-20261019`. Never force-push. Do not touch the shared practice site.

## Review Focus

1. A staff member asks "what has the owner said about Bayside?" when every statement is owner-only: the answer must say nothing is shared, and must not quote, paraphrase or count the private lines. (Task 6 test `test_staff_cannot_learn_owner_only_context_from_any_answer`.)
2. The owner's answer "up to 14 days this time" on case A must not change the suggestion or questions on case B for the same customer. (Task 4 test `test_a_case_scoped_answer_is_not_reused_on_another_case`.)
3. A remembered approval ("remember for Bayside: approved 14 Nov") must show up as a prior decision, never as guidance that the suggestion cites as permission. (Task 5 test `test_a_remembered_outcome_is_history_not_guidance`.)
4. A records change after the suggestion was given (a payment added) must withdraw the suggestion before the owner can accept it: the decision endpoint must reject `suggestionShown` with a stale version. (Task 5 test `test_a_stale_suggestion_cannot_be_accepted`.)
5. An owner statement naming no customer, confirmed with no customer chosen, must not become business-wide: it stays `scope.kind = 'unassigned'` and is never retrieved. (Task 3 test `test_an_unassigned_statement_is_never_retrieved`.)

---

### Task 1: Stores, business date, context retrieval

**Files:**
- Modify: `prototype/server.py` (`ensure_schema` ~386-408; `App.today` 537; demo routes ~1910-1925; `fixture`/`save_doc` untouched)
- Modify: `prototype/records.py:66-70` (`today_for`)
- Create: `prototype/test_desk_store.py`

**Interfaces:**
- Produces, on `App`:
  - `new_statement(actor, text, *, thread_id, scope, visibility, status, lines, source, checks=()) -> dict` where `scope` is `{'kind': 'business'|'customer'|'case'|'unassigned', 'customerId'?: str, 'requestId'?: str}`, `visibility` is `'owner'|'staff'`, `status` is `'proposed'|'confirmed'|'retired'`, each line is `{'kind': 'observation'|'relationship'|'expectation'|'guidance'|'constraint', 'quote': str, 'until': 'YYYY-MM-DD'|None, 'certainty': str|None}`. Returns the stored statement: `{id ('stmt_…'), text, saidBy, role, saidOn (business date), recordedAt, threadId, scope, visibility, status, lines: [{id ('line_…'), kind, quote, until, certainty, status: 'active'|'removed'|'superseded', supersededBy: None}], checks, source, version: 1, history: []}`.
  - `statement(statement_id) -> dict` (404 `NOT_FOUND`), `save_statement(s)`, `statements() -> list`.
  - `update_statement(actor, s, *, lines=None, scope=None, visibility=None, status=None) -> dict`: owner only for `confirmed`/`visibility`/`retired`; appends `history` and bumps `version`; `lines` edits are `[{'id', 'kind'?, 'until'?, 'remove'?: True}]`.
  - `thread(thread_id) -> dict`, `threads() -> list`, `general_thread() -> dict` (created on first use, id `thread_general`), `case_thread(request_id) -> dict` (created on first use, id `thread_<request_id>`), `add_turn(thread_id, *, by, role, kind, text=None, card=None, visibility='all') -> dict` returning `{id, threadId, at, by, role, kind, text, card, visibility}`, `turns(thread_id, viewer_role) -> list` filtered by visibility (`'all'`, or equal to the role; `'owner'` turns hidden from staff).
  - `context_for(customer_id, viewer_role, request_id=None) -> {'lines': [...], 'decisions': [...]}`: lines from confirmed statements whose scope is business, this customer, or this case (`request_id`), with `status == 'active'`, plus confirmed notes rendered as lines `{id: 'note:<id>', kind: 'observation' if note kind context else 'guidance', quote: text, scope: {...}, saidOn: createdAt[:10], visibility: 'staff', expired: False, source: 'note'}`; statements with `visibility == 'owner'` excluded for staff; each line carries `statementId, scope, saidOn, saidBy, role, visibility, expired` (`until` before the business date). `decisions`: every decided or completed case for the customer: `{requestId, decidedAt, outcome, approvedDueDate, approvedExtensionDays, reason, invoiceReference}`.
  - `advance_business_date(actor, days) -> date`: operator only, practice workspaces only; stores meta `businessDateOffset` (int days); `App.today(doc)` adds it.
- API: `POST /api/demo/advance {days: int}` (operator; 409 `NOT_PRACTICE` otherwise) → `{today: 'YYYY-MM-DD'}`.

- [ ] **Step 1: Write the failing tests** in `prototype/test_desk_store.py` (base on `RecordsCase` from `test_records.py`; `self.start(); self.practice_ready(); c = self.add_customer()`):
  - `test_a_statement_is_stored_with_its_provenance_and_business_date`: `new_statement` by the owner with one line; assert `saidOn == '2026-10-18'` (TODAY in tests), `status`, `visibility == 'owner'`, line ids start with `line_`.
  - `test_only_the_owner_confirms_or_changes_visibility`: staff `update_statement(status='confirmed')` raises `RecordsError` 403.
  - `test_context_for_merges_notes_and_statements_and_filters_staff`: one confirmed note (scope customer), one confirmed owner-only statement (scope customer), one staff-visible statement; `context_for(c, 'staff')` has the note and the staff-visible line only; `context_for(c, 'owner')` has all three.
  - `test_case_scoped_lines_appear_only_for_that_case`: statement scope `{'kind':'case','requestId':'req_x'}`; present for `request_id='req_x'`, absent otherwise.
  - `test_expired_lines_are_kept_and_marked`: line `until='2026-10-01'`; `expired is True`.
  - `test_turns_are_filtered_by_visibility`: `add_turn(..., visibility='owner')` hidden from staff.
  - `test_advance_business_date_moves_today_in_a_practice_workspace`: operator advances 7 days; `app.today(app.fixture())` is 2026-10-25; a real workspace gets 409 (use `setup_workspace(mode='real')` from `RecordsCase`).
- [ ] **Step 2: Run** `python3 -m unittest test_desk_store -q` → FAIL (`AttributeError: new_statement`).
- [ ] **Step 3: Implement** the three tables (`statements(id PK, seq, data)`, `threads(id PK, data)`, `turns(seq INTEGER PRIMARY KEY AUTOINCREMENT, thread_id, data)`), the methods above, `advance_business_date`, the meta offset in `App.today`, and the demo route. Statements are JSON documents like the other record tables; keep the same `uid`/`now` helpers.
- [ ] **Step 4: Run** the new tests and the whole suite → all pass (`Ran 255+`; the existing 248 unchanged).
- [ ] **Step 5: Commit** `Stores for statements, threads and turns; context retrieval; business-date advance`.

### Task 2: `coordinator.py` — schemas, validation, mock behaviour

**Files:**
- Create: `prototype/coordinator.py`
- Modify: `prototype/agent.py:1100` (`MockAdapter.respond`: first line `if task in coordinator.MOCK_TASKS: return coordinator.mock_respond(task, messages, schema)` with a local import)
- Create: `prototype/test_coordinator.py`

**Interfaces (produces):**
- `COORDINATOR_PROMPT_VERSION = 'coordinator-v0.1'`; `MOCK_TASKS = ('route_turn', 'interpret_statement', 'plan_needs', 'suggest')`.
- `route_messages(text, role, customers, recent_turns, business_date) -> list[messages]` and `ROUTE_SCHEMA`: `{intent: 'request'|'context'|'question'|'unsupported', customerQuery: str|null, requestRef: str|null, questionType: 'owes'|'open_invoices'|'request_status'|'owner_said'|null, explanation: str|null}`. `validate_route(value, text, role) -> dict`: `customerQuery`/`requestRef` must `appears_in` text or a recent turn else nulled; staff cannot get `intent == 'context'` (becomes `unsupported` with explanation "Only the owner adds context; staff notes go in the records"); `explanation` through `prose_problems` else replaced by a fixed sentence.
- `interpret_messages(text, customers, business_date) -> list` and `INTERPRET_SCHEMA`: `{customerQuery: str|null, lines: [{kind: enum, quote: str, until: 'YYYY-MM-DD'|null, certainty: str|null}]}`. `validate_interpretation(value, text, business_date) -> {customerQuery, lines, checks}`: drop a line whose `quote` is not in `text` (check recorded); `until` must be a valid date on or after `business_date` else `None` with a check; `certainty` must be in `text` else `None`; at most 6 lines; `customerQuery` must be in `text`.
- `needs_messages(facts_text, lines, prior_decisions, answers) -> list` and `NEEDS_SCHEMA`: `{needs: [{need: str, why: str, from: 'staff'|'owner', kind: 'calculate'|'recommend', answeredBy: str|null, question: str}]}`. `classify_needs(value, *, code_missing: list[str], line_ids: set[str]) -> list`: a `calculate` need is kept only when `code_missing` is non-empty (code's own list of blocking conditions: `['records_conflict']` when the invoice position status is `conflict`); otherwise it is downgraded to `recommend` with a check; `answeredBy` must be in `line_ids` else `None`; `why` and `question` through `prose_problems` (a failing need is dropped); at most 4; output items `{id ('q_…'), need, why, from, kind, question, answeredBy, status: 'answered' if answeredBy else 'open', checks}`. `from` is forced to `'staff'` for `calculate` and `'owner'` for `recommend`.
- `suggest_messages(facts_text, lines, prior_decisions, answers, open_questions) -> list` and `SUGGEST_SCHEMA`: `{outcome: 'approve'|'decline', approvedDueDate: str|null, cites: [str], sentence: str}`. `validate_suggestion(value, *, as_of, current_due, requested, loaded_ids: set[str]) -> dict|None`: `approve` needs a valid date later than both `as_of` and `current_due` (when known), else `None`; `decline` needs `approvedDueDate is None`; every cite must be in `loaded_ids` else `None`; `sentence` through `prose_problems` else `None`; returns `{outcome, approvedDueDate, cites, sentence, status: 'advisory', label: 'Suggestion, not evaluated in real use', promptVersion}`.
- `mock_respond(task, messages, schema) -> AdapterResult` with these deterministic rules (parse the user message's `<text>`, `<customers>` and `<business_date>` sections your own message builders emit):
  - `route_turn`: text containing an invoice reference (`[A-Z]{2,}-\d+`) or an ISO date → `request`; text matching `^(what|which|how much|is|has|status|when)\b` or ending `?` → `question` with `questionType` by keyword (`owe`→`owes`, `open|overdue|unpaid`→`open_invoices`, `status|request`→`request_status`, `said|told`→`owner_said`, else `null`); otherwise `context` for the owner and `unsupported` for staff; `customerQuery` = the first listed customer name found in the text.
  - `interpret_statement`: split on `.`, `;`, ` but `; each non-empty clause is a line; kind: `known|years|relationship`→`relationship`; `event|next month|should|expect`→`expectation` with `until` = business date + 30 days when "next month" appears; `consider|would|might`→`guidance`; `don't|do not|no more|not want`→`constraint`; else `observation`; `certainty` = `'should'` when present; `customerQuery` as above.
  - `plan_needs`: one `recommend` need from the owner when a `guidance` line exists and no line of scope `case` exists: `question = 'You said "<guidance quote>". Is <N> days acceptable here?'` with `N` from the facts text; `answeredBy` = the case line id when one exists; otherwise `needs: []`.
  - `suggest`: `decline` when any line contains `no extension` or `do not extend`; otherwise `approve` with the requested date, or current due + N days when a case line says `up to N days`; `cites` = all line ids; `sentence = 'Based on what you said and the records.'`.

- [ ] **Step 1: Write the failing tests** in `prototype/test_coordinator.py` (pure unit tests, no server): one per validator rule above, named `test_<rule>` (e.g. `test_a_quote_not_in_the_text_is_dropped_with_a_check`, `test_a_calculate_need_without_a_code_reason_is_downgraded`, `test_an_approve_suggestion_needs_a_date_after_the_current_due_date`, `test_cites_must_be_loaded_evidence`, `test_staff_cannot_add_context_through_routing`), plus `test_mock_interpretation_of_the_example_paragraph_gives_five_lines` asserting kinds `['observation','relationship','expectation','guidance','constraint']` and `until == '2026-11-17'` for business date 2026-10-18.
- [ ] **Step 2: Run** `python3 -m unittest test_coordinator -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** `coordinator.py`: message builders (system text states the boundaries from PROMPTS.md "Human boundaries"; the user message wraps untrusted text in `<text>` delimiters escaped like `_quote_message`), schemas with `additionalProperties: false` and every key required, validators, `mock_respond`. Import `appears_in`, `prose_problems`, `calendar_date`, `AdapterResult` from `agent`/`model_adapter`.
- [ ] **Step 4: Run** the tests and the full suite → pass.
- [ ] **Step 5: Commit** `coordinator.py: route, interpret, plan-needs and suggest tasks with code-side guards and mock behaviour`.

### Task 3: Desk API — threads, turns, owner context, one-confirmation

**Files:**
- Modify: `prototype/server.py` (routes near 1953; new `App` methods)
- Create: `prototype/test_desk_api.py`

**Interfaces:**
- Consumes Task 1 stores and Task 2 `route_*`, `interpret_*`, `validate_*`.
- Produces API (all under the existing session rules; `Idempotency-Key` on writes as other endpoints):
  - `GET /api/desk/threads` → `[{id, kind, requestId, customerId, title, status, lastTurnAt, lastTurnText}]` for the viewer (case threads carry the case `summary(r)` fields `status`, `customerName`, `invoiceReference`).
  - `GET /api/desk/threads/<id>` → `{thread, turns: [...], case: app.view(r) | null, context: context_for(customerId, role, requestId) | null}`.
  - `POST /api/desk/threads/<id>/turns {text}` → `202 {turns: [the person's turn, the agent's turns...], threadId}`; routing by `route_turn` (model call outside the lock):
    - `request` (staff or owner): calls `app.create(actor, {'messageText': text}, key)`; the case thread is created; the person's turn is copied into it; returns `threadId` of the case thread.
    - `context` (owner): calls `interpret_statement`; stores a `proposed` statement (`scope.kind = 'customer'` when exactly one customer matches `customerQuery` via `Evidence.find_customers`, else `'unassigned'`; `visibility 'owner'`; `source {kind:'turn', id}`), and a card turn `{type: 'understood', statementId, lines, customerName|null, checks}` with `visibility 'owner'`.
    - `question`: Task 6 (until then: `unsupported`).
    - `unsupported`: a text turn with the explanation and the sentence "You can ask what a customer owes, which invoices are open, a request's status, or what the owner has shared."
  - `POST /api/desk/statements/<id>/confirm {customerId?: str, visibility?: 'owner'|'staff', lines?: [{id, kind?, until?, remove?}]}` (owner) → the confirmed statement; a statement left `unassigned` is confirmed but never retrieved (Review Focus 5); `visibility 'staff'` requires `scope.kind in ('customer','business')`.
  - `POST /api/desk/statements/<id>/retire {reason}` (owner).
  - Staff text that is `context`-like gets the routing's `unsupported` explanation (Task 2) and nothing is stored.
- Turn visibility: the person's own turn and the `understood` card are `'owner'` when the author is the owner and the intent is `context`; `request` turns are `'all'`.

- [ ] **Step 1: Write the failing tests** in `prototype/test_desk_api.py` (HTTP, mock mode, `self.call(path, body, role, key)`):
  - `test_the_owner_paragraph_becomes_one_proposed_statement_and_one_understood_card` (the example paragraph with "Bayside Café" named; 5 lines; `scope.kind == 'customer'`).
  - `test_confirming_once_with_a_correction_keeps_the_rest` (remove one line, change one `until`; status confirmed; `version == 2`).
  - `test_an_unassigned_statement_is_never_retrieved` (paragraph with no customer name; confirm without `customerId`; `context_for(customer, 'owner')` empty).
  - `test_owner_context_turns_are_invisible_to_staff` (staff `GET` the general thread: no `understood` card, no owner text).
  - `test_staff_context_is_refused_with_an_explanation` (staff type the paragraph: one `unsupported` turn; `statements()` empty).
  - `test_a_request_typed_in_the_general_thread_creates_a_case_and_its_thread` (status reaches `awaiting_owner`; `GET /api/desk/threads` lists the case thread).
- [ ] **Step 2: Run** → FAIL (404 unknown route).
- [ ] **Step 3: Implement** the routes and methods; model calls (`route_turn`, `interpret_statement`) run outside the lock like `execute`, with the adapter from `adapter_for(self.agent_mode)`; adapter failure → an `unsupported` turn saying the agent could not read the message, nothing stored. Record `model.call` events on a new `events.request_id = thread id`? No: `events.request_id` is NOT NULL and per request; add a `desk_events` note? Keep it simple: store `{modelCalls, latencyMs, promptVersion}` on the agent's turn (`turn.meta`).
- [ ] **Step 4: Run** the tests and the suite → pass.
- [ ] **Step 5: Commit** `Desk API: threads and turns; owner context interpreted and confirmed once`.

### Task 4: The coordinator in the case flow — needs, questions, brief-v3

**Files:**
- Modify: `prototype/server.py` (`execute` 1515-1544, `commit_outcome` 1546-1610, `view`/`present`, routes), `prototype/agent.py:23` (`BRIEF_FORMAT = 'brief-v3'`; `render_brief` gains `context_shown`, `questions`, `suggestion`, `suggestionStatus` keys, defaulting to `[]`/`None`/`'off'`), `prototype/web/requests.js` only where `brief-v2` is tested (accept v3 too).
- Create: `prototype/test_case_coordinator.py`

**Interfaces:**
- `coordinator.prepare_needs(adapter, caller, *, facts, lines, decisions, answers, code_missing) -> {'questions': [...], 'stats': {...}}` (one model call; mock in tests) called from `execute` after the runner returns an `approval` terminal and before `commit_outcome`, outside the lock; result passed as `extras` to `commit_outcome(run_id, outcome, identity, caller, extras=None)`.
- `facts` text for the model = the code-rendered summary and typed facts from `fact_set` (already code-written); `lines` from `context_for(customer_id, 'owner', request_id)`; `code_missing = ['records_conflict']` when `snapshot['invoice']['position']['status'] == 'conflict'`.
- Brief-v3 additions: `contextShown: [line ids and decision ids]`, `questions: [{id, need, why, from, kind, question, status: 'open'|'answered'|'skipped', answeredBy}]`, `suggestion: None`, `suggestionStatus: 'off'` (Task 5 fills these).
- `app.view(r)` attaches live `context = context_for(customerId, role, r['id'])` for cases with an invoice.
- API: `POST /api/requests/<id>/questions/<qid>/answer {text, keepForCustomer: bool}` (owner; 409 unless `awaiting_owner`) → stores a confirmed statement with one `guidance` line, `scope {'kind':'case','requestId'}` or `{'kind':'customer','customerId'}` when `keepForCustomer`, `source {kind:'answer', questionId}`, `visibility 'owner'`; marks the question `answered` with `answeredBy = line id`; returns `app.view(r)`. `POST .../questions/<qid>/skip` → `skipped`. Neither bumps `r['version']` or re-runs preparation (Task 5 re-runs only the suggestion).
- Reuse: when `prepare_needs` returns a need with `answeredBy` set, it is stored as `status 'answered'` and shown as "Already known".

- [ ] **Step 1: Write the failing tests** (HTTP, mock; set up a customer with an invoice as in `test_evidence_keys.EvidenceCase.decided`, and an owner statement with a `guidance` line via Task 3's endpoints):
  - `test_a_case_with_undefined_guidance_gets_one_owner_question_with_its_reason` (`brief.format == 'brief-v3'`, one question, `kind 'recommend'`, `from 'owner'`, `why` non-empty, status `awaiting_owner`, `panel` controls still present in the view).
  - `test_answering_stores_a_case_scoped_line_and_marks_the_question_answered`.
  - `test_a_case_scoped_answer_is_not_reused_on_another_case` (second request for the same customer: its question is `open`).
  - `test_keep_for_customer_makes_the_answer_reusable` (`keepForCustomer: True`; second request's need comes back `answered`, shown as already known).
  - `test_a_calculate_need_the_code_does_not_recognise_cannot_block` (mock returns a `calculate` need; the case still reaches `awaiting_owner` with the need as `recommend`).
  - `test_staff_cannot_answer_owner_questions` (403).
  - `test_old_v2_briefs_still_read` (load a stored request with `brief.format 'brief-v2'`; `app.view` returns it unchanged apart from the live `context`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `prepare_needs`, the `execute`/`commit_outcome` plumbing, brief-v3 fields, the two endpoints, `view` context attachment.
- [ ] **Step 4: Run** the tests and the suite (including `test_agent`, `test_full_flow`, `test_workflow`, which assert on brief fields: adjust only `format` expectations from v2 to v3 where a test pins it) → pass.
- [ ] **Step 5: Commit** `Case coordinator: needs classified by code, owner questions with reasons, brief-v3`.

### Task 5: Advisory suggestion, owner setting, remember, counters

**Files:**
- Modify: `prototype/server.py` (`decide` 740-780, `execute`, routes, a `suggest` run kind in `schedule`/`work`), `prototype/coordinator.py` (`prepare_suggestion`)
- Create: `prototype/test_suggestion.py`

**Interfaces:**
- Setting: `GET /api/suggestions` → `{on: bool}` (owner, staff see `{on: false}`); `POST /api/suggestions {on}` (owner) stores meta `showSuggestions`.
- `coordinator.prepare_suggestion(adapter, caller, *, facts, lines, decisions, answers, open_questions, as_of, current_due, requested, loaded_ids) -> dict|None` (one model call; `None` when any question is `open` → `suggestionStatus 'withheld'`, `withheldBecause: [question ids]`).
- In `execute`, after `prepare_needs`, when the setting is on: run `prepare_suggestion`; brief gets `suggestion` with `version: 1` and `suggestionStatus 'given'|'withheld'`; when off, `'off'`.
- Suggest-only run: `app.schedule_suggest(r)` queues a run `{kind: 'suggest'}`; the worker runs `prepare_suggestion` outside the lock and, under the lock, if `r['status'] == 'awaiting_owner'` and the analysis is unchanged, sets `brief.suggestion` (version +1) and `suggestionStatus`, and records event `suggestion.updated {version, status}`. Triggered by `answer`, `skip`, and turning the setting on for cases already waiting.
- `decide` accepts `suggestionShown: {version, outcome, approvedDueDate} | null`; 409 `STALE_SUGGESTION` when the version differs from the current one or when `suggestionStatus != 'given'` but a version is sent; stores `decision.suggestionShown`; outcome relation computed by code: `accepted` (same outcome and date), `changed` (approve, other date), `declined_against` (different outcome), `none`.
- `decide` accepts `remember: {text, keepForCustomer: bool} | null`: when present, a confirmed statement with one `guidance` line, scope case or customer, `source {kind:'decision', id}`, `visibility 'owner'`. The decision's `reason` stays on the decision and is never copied into a line (Review Focus 3).
- `GET /api/suggestions/counters` (owner) → `{given, withheld, accepted, changed, declinedAgainst, byScenarioLabel: {...}}` computed from decisions and analyses (fictional workflow counters, labelled so in the payload: `note: 'Workflow counters on fictional data; not a measure of real-world decision quality.'`).

- [ ] **Step 1: Write the failing tests**:
  - `test_suggestions_are_off_by_default_and_owner_only`.
  - `test_a_suggestion_is_withheld_while_an_owner_question_is_open_and_given_after_the_answer` (status `withheld` with `withheldBecause`; after `answer`, a suggest-only run gives version 2 with `outcome 'approve'`, cites include the answer line; the request version is unchanged).
  - `test_context_arguing_against_approval_never_suggests_approve` (a `no extension` constraint line → `decline` with `approvedDueDate None`).
  - `test_the_decision_stores_the_suggestion_shown_apart_from_the_outcome` (decline against a suggestion: `relation 'declined_against'`; `decision.outcome 'decline'`).
  - `test_a_stale_suggestion_cannot_be_accepted` (add a payment after the suggestion → the case is re-prepared; sending the old `suggestionShown.version` → 409 `STALE_SUGGESTION`).
  - `test_a_remembered_outcome_is_history_not_guidance` (`remember` text "approved 14 Nov, fine this time", `keepForCustomer` True: the line's kind is `guidance` and the next case's `decisions` list holds the decision; assert the next suggestion's `cites` may include the line but the decision record never appears as a line).
  - `test_counters_count_the_workflow_not_quality` (note text present; counts match the scenario).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** all → pass.
- [ ] **Step 5: Commit** `Advisory suggestion: owner setting, withheld while questions are open, stored apart from the decision; remember; counters`.

### Task 6: Read-only questions for staff and the owner

**Files:**
- Modify: `prototype/server.py` (desk turn routing for `question`), `prototype/coordinator.py` (`route_messages` already carries recent turns)
- Create: `prototype/test_desk_questions.py`

**Interfaces:**
- `App.answer_question(actor, thread, route) -> card` where `route` is the validated routing; executes in code:
  - `owes`: customer resolved from `customerQuery`, else from the thread's last answered customer (follow-up), else a text turn asking which customer (listing up to 5 name matches); card `{type:'answer', questionType:'owes', customer:{id,name,code}, amount: <customer position as /api/records gives it: recordedNet, unallocated, completeness, and per open invoice the position with its mark>, asOf, why: position['notExact'] for not-exact invoices}` — all numbers from `customer_position`/`invoice_position`, none from the model.
  - `open_invoices`: the customer's active invoices with `status`, `atMost`/`exact`, due date and overdue days from `extension_facts`-style arithmetic (reuse `records` positions; no new arithmetic).
  - `request_status`: cases for the customer or the `requestRef`, with `statusOf`-like labels and links `#/case/<id>`.
  - `owner_said`: `context_for(customer, viewer_role)` lines; for staff, only `visibility 'staff'` lines, and when none: "The owner has not shared anything about <customer> with staff." with no counts (Review Focus 1).
  - `unsupported` or a question type the capability does not cover: a text turn explaining what can be asked.
- The thread stores `lastCustomerId` on the thread after an answered question, for follow-ups; `route_messages` receives the last three turns' text.

- [ ] **Step 1: Write the failing tests** (HTTP, mock; staff and owner):
  - `test_staff_ask_what_a_customer_owes_and_get_code_written_amounts_with_marks`.
  - `test_a_follow_up_without_a_name_uses_the_last_customer` ("and which are overdue?").
  - `test_staff_cannot_learn_owner_only_context_from_any_answer` (owner-only statement; staff ask "what has the owner said about Bayside?": answer has no quote, no count, the fixed sentence).
  - `test_an_unsupported_question_gets_the_capability_explanation`.
  - `test_a_question_about_an_unknown_customer_asks_which_one`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** all → pass.
- [ ] **Step 5: Commit** `Read-only questions on the desk: what a customer owes, open invoices, request status, what the owner shared`.

### Task 7: The desk interface

**Files:**
- Create: `prototype/web/desk.js`
- Modify: `prototype/web/core.js` (`readRoute` 376-391: `#/requests` → `{name:'desk'}`, `#/requests/thread/<id>` → `{name:'desk', threadId}`, `#/cases` → the old queue (`name:'requests'`), `#/case/<id>` unchanged, `#/requests/new` → desk with the composer open; `NAV` label unchanged; `index.html` adds `desk.js` before `requests.js`'s dependants if any), `prototype/web/app.css` (desk styles within the existing tokens), `prototype/web/index.html`
- Create: `deploy/desk_check.js` (mock servers, like `ui_check.js`; signs in with codes from the log)

**Interfaces (consumes Tasks 3–6 APIs; reuses `factsHtml(f, c)`, `flagsHtml(c)`, `panelHtml(c, f)`, `bindPanel(c, f, seq)`, `pageHead`, `openDialog`, `api`, `toast`, `stamp`, `dateText`, `money`, `esc` from the existing scripts).**
- Layout: desktop two panes (thread list left: general thread first, then case threads with status chips; the thread right); phone: list, then thread, with the input fixed above the tab bar.
- Cards by `turn.card.type` and from the case view: `facts` (`factsHtml`), `context` ("What you have said", lines grouped by scope with `saidOn`, expired marked "expired"; for staff the shared ones under "What the owner shared"), `questions` ("What I need": each with `why`, an answer field, "Keep this for <customer>" tick, "Answer", "Decide without this"), `decision` (`panelHtml` + a labelled suggestion block "Suggestion, not evaluated in real use" with "Use this date" that prefills the panel and sets `suggestionShown`; a "Remember for next time" field with "only this case / for <customer>" choice; the constraint note "No operational restriction has been applied" when a `constraint` line is in context), `draft`, `understood` (lines as a short list; Confirm; Correct opens a dialog with per-line kind/until/remove, customer picker when unassigned, "Share with staff" checkbox per statement), `answer` (owes/open invoices/status/owner said as tables with the certainty marks), `text`.
- Input: one textarea with "Send"; after a `request` intent the view moves to the case thread; after `context` the understood card appears; progress shown as today's `progressHtml`.
- Every card has "Sources" (expand) and, for cases, "Open the full case" → `#/case/<id>`; "Customer records" → `#/customers/<id>`.
- Polling: reuse the 8 s refresh pattern; pause while typing.

- [ ] **Step 1: Write `deploy/desk_check.js`** against a mock server (`ui_check_server.py`), checks named D1–D9: sign in; the owner types the example paragraph → one understood card with 5 lines → Confirm; staff type the request → case thread with facts, context (owner sees 5 lines; staff see none) and one question with its reason; suggestion block absent (setting off) → owner turns it on → "withheld" shown → owner answers "up to 14 days this time" → suggestion appears labelled → owner uses the date and approves → draft card, constraint note; staff ask "what does Bayside owe now?" → answer card with the exact amount; 375 and 390 px: no horizontal overflow, input reachable, cards fit; `#/cases` and `#/case/<id>` still render; no console errors.
- [ ] **Step 2: Run** it → FAIL (no desk).
- [ ] **Step 3: Implement** `desk.js`, routes, CSS, `index.html`.
- [ ] **Step 4: Run** `desk_check.js` (all pass), `layout_check.js` (156/156 or updated counts with the desk pages added), and the unit suite.
- [ ] **Step 5: Commit** `The desk: conversation and cards over the same request records; old queue at #/cases`.

### Task 8: Requests that are not extensions (`other`)

**Files:**
- Modify: `prototype/agent.py` (extraction: no schema change; `other` is decided by code: no `invoiceReference` and no `requestedDueDate` and a non-empty `otherRequests`, or `route_turn` intent `request` with `requestRef null` and no date), `prototype/server.py` (`create` → `type 'other'`: no agent run; status `awaiting_owner` with `brief {format:'brief-v3', summary: code sentence, facts: [], context…, questions: []}`; `decide` for `other`: `outcome 'noted'`, `reason` required, no draft; `finish` skips the draft), `web/desk.js` (decision card for `other`: reason only)
- Test: `prototype/test_other_requests.py`

- [ ] **Step 1: Tests**: `test_a_message_asking_for_more_credit_becomes_an_other_case_with_no_calculation` (facts empty, context present, no suggestion ever), `test_the_owner_notes_an_other_case_in_words` (`outcome 'noted'`, no `responseDraft`), `test_an_extension_message_is_still_an_extension`.
- [ ] **Step 2–5:** fail, implement, pass, commit `Other requests: triaged and recorded, never calculated`. **Cut this task if Tasks 1–7 and 9–10 are at risk for Week 7.**

### Task 9: Checks and the effort comparison

**Files:**
- Modify: `deploy/ui_check.js` (Requests steps use `go(page, '#/cases')`; sections unchanged otherwise), `deploy/layout_check.js` (add the desk at each width), `deploy/guide_check.js` (T3/T6/T7 open `#/cases` and `#/case/<id>`; the guide is unchanged in this slice)
- Create: `deploy/effort_compare.js`, `docs/qa/EFFORT-COMPARISON.md`

**Interfaces:** `effort_compare.js <mock base url> <log> <out dir>` runs three scenarios on both interfaces (the old queue/case pages and the desk) with the same fictional data, counting per role: messages typed, taps/clicks, fields filled, pages opened, people involved, elapsed ms; and records: correctness (the decision stored is the intended one, the amounts shown equal the API's), work shifted (staff actions old vs new), understanding (the final agent turn of each thread states what was done and what was not: assert the sentence exists; the human reading is recorded in the markdown by hand). Scenarios: S1 complete request, no owner judgement; S2 request needing one owner judgement with context already given; S3 staff ask what a customer owes.

- [ ] **Step 1: Write** `effort_compare.js` and run it → the table in `docs/qa/EFFORT-COMPARISON.md` with a "Reading" section for the human judgement, empty until someone fills it.
- [ ] **Step 2: Update** the three checks; run `ui_check.js` (148/148 or the new count with D-section references), `layout_check.js`, `guide_check.js` (on a live-model preview, 58/58), `desk_check.js`.
- [ ] **Step 3: Commit** `Checks follow the desk; effort comparison on three scenarios`.

### Task 10: Records

**Files:** `PROMPTS.md` (coordinator-v0.1: every prompt, schema, guard, mock rule; model access: local tested, hosted untested), `docs/DEPLOYMENT.md` (model-access options and status), `prototype/README.md`, `docs/UX-REDESIGN.md` (the desk; `#/cases`), `docs/AGENT-COORDINATOR-PROPOSAL.md` (an "Implementation notes" section: what was built, the assumptions recorded while building), `docs/DECISIONS.md` (E018: first slice built on the exploration branch; not deployed; what it establishes and does not), `docs/project-state.json` + `python3 tools/build_brief.py`.

- [ ] **Step 1:** Write them; `python3 agent.py --print-prompts` and a new `python3 coordinator.py --print-prompts` must print what PROMPTS.md shows.
- [ ] **Step 2:** Commit `Record the coordinator's first slice: prompts, model access, desk, decisions`.

---

## Self-review notes

- Spec coverage: §4 statements/interpretation (T1–T3), §5 needs and partial results (T4), §6 desk and staff questions (T6–T7), §7 suggestion tiers and E017 safeguards (T5), §8 model access (T10; no hosted test by decision), §9 assumptions (T1 dates, T4 no re-run), §10 scope items 1–8 (T1–T10), `other` (T8, cuttable), measurement (T5 counters, T9 comparison). Tier 2: none, by design. QA pack revision 4: out of this plan; noted in T10.
- Names used across tasks: `context_for`, `new_statement`, `update_statement`, `add_turn`, `turns`, `prepare_needs`, `prepare_suggestion`, `validate_*`, `mock_respond`, `suggestionShown`, `suggestionStatus`, `keepForCustomer`, `remember`.
- Review Focus 1–5 each has its test in T6, T4, T5, T5, T3.
