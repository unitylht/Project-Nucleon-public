# Conversational desk — design and implementation plan (second slice)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working conversation: people say what they need in their own words, follow up, change customer and give context; the agent gathers from the records with tools, answers the question first, says what matters, offers the next step, and prepares actions, within the same permission and calculation boundaries as before.

**Architecture:** The four-category router is replaced by a **desk agent loop** (`coordinator.desk_run`): one bounded tool-calling run per turn, with read tools over records, context and cases, three action tools (open a request, interpret a statement, prepare a customer), a navigation tool over a fixed map of the application, and a terminal `reply` tool whose prose is guarded: every number and date in it must appear in the tool results of that run. Threads keep a **focus customer** per role. The case thread is reorganised decision-first for the owner and status-first for staff. The supporting areas stay as they are.

**Tech stack:** as the first slice (Python stdlib + SQLite; vanilla JS; Playwright checks; local Gemma through the OpenAI-compatible adapter; hosted endpoints by configuration, untested).

**Spec:** this document, §0, which revises P003 (`docs/AGENT-COORDINATOR-PROPOSAL.md`) for this slice; the team's direction of 20 October is recorded in `docs/DECISIONS.md` E020 (added by Task 6). Branch `explore/agent-coordinator-20261019`; preview at https://nucleon.dracooz.top/preview/.

## §0 Design decisions for this slice

1. **The agent composes the answer.** The model writes the reply prose. Code guards it: `prose_problems` applies; any digit run or spelled month-day in the reply must occur in the concatenated tool results of the same run (`known_text`), else the reply is replaced by the structured results with the fixed sentence "The agent's wording was withheld because it stated something the records do not show." Amounts and dates shown in cards always come from code.
2. **Tools, not intents.** Read tools: `findCustomers(query)`, `customerOverview(customerId)` (position, open and overdue invoices with marks and days overdue, payments complete to, last activity, open cases), `invoices(customerId, which: open|overdue|all)`, `ownerContext(customerId)` (role-filtered), `cases(customerId?, reference?)`, `whereIs(topic)` (fixed map: add customer, add invoice, record payment, import, knowledge, setup, completeness, opening balance, reverts; each with the hash route and the button's label). Action tools: `openRequest(text)` (staff; the existing intake), `interpretStatement(text)` (owner; the existing one-confirmation flow), `prepareCustomer(name)` (a draft card with "Create" that opens the existing Add customer dialog prefilled; nothing is created by the agent). Terminal: `reply(text, show, nextStep)`.
3. **Focus.** Each thread keeps `focus[role] = customerId`; `findCustomers` results and explicit names update it; pronouns resolve to it; the reply card names the customer it is about. A question naming a customer the records do not hold gets "which customer?" with up to five names.
4. **One answer card.** `reply` renders: the prose first; then only the `show` blocks requested by the model (`overview`, `invoices`, `context`, `cases`, `navigation`, `draft`), each compact and expandable; then one next-step control when `nextStep` is set (`open` a route, `draft` a prepared action, `ask` the owner, `decide`). Supporting links (full case, customer records, sources) appear once per thread footer, not per card.
5. **Case thread hierarchy.** Owner: the request sentence and amount with its mark; the suggestion (when given) and the decision controls; then collapsed sections "What the agent needs", "What you have said", "Facts and sources", "Reply draft after deciding". Staff: one status line ("With the owner since …; nothing for you to do" or the staff question), the request, collapsed facts. Nothing repeated.
6. **Shorter alternative.** When a day limit the owner stated applies and the request exceeds it, the suggestion step must propose the latest date within the limit (`approve` with that date) rather than decline or withhold; the guard already rejects dates beyond the limit.
7. **Permissions unchanged.** Staff never see owner-only context or any trace of it; owner-only turns stay owner-only; the agent creates nothing except a request (staff) and a proposed statement (owner); decisions stay with the owner.
8. **Models.** Same adapter; the loop is the same shape as `handle_request`; at most 8 tool calls and 6 model turns per desk turn; the mock scripts a deterministic loop so checks run without a model. Hosted endpoints remain configuration, untested.
9. **Validation is conversational.** A scenario set with varied wording, follow-ups, customer switches and multi-part asks runs on the mock (deterministic assertions) and on the live model (structural assertions plus a transcript review by a reader who judges whether the answer is understandable and the task completable without splitting the request). Counts alone do not pass a scenario.

## Global Constraints

- As the first slice: fictional data; no codes, keys or private data in files or screenshots; prose guard on every model sentence shown to a person; numbers and dates in prose only when present in that run's tool results; server-side permissions; relative URLs (works at `/` and `/preview/`); Arial; no inline styles; 375/390 px fit; existing tests and checks keep passing (suite 346; `desk_check` 49/49; `ui_check` 150/150; `layout_check` 174/174).
- Prompt text and schemas recorded in PROMPTS.md as `coordinator-v0.3`; `python3 prototype/coordinator.py --print-prompts` matches.
- Commits end with the attribution line the harness gives; never force-push; the preview is updated only with pushed commits through `NUCLEON_BASE=~/srv/nucleon-preview NUCLEON_LABEL=local.nucleon.preview NUCLEON_LOGDIR=~/Library/Logs/nucleon-preview ~/srv/nucleon-preview/bin/nucleonctl deploy <sha>`; production (`~/srv/nucleon`, `f95f50f`) is never touched.

## Review Focus

1. A reply that states an amount or date not in the run's tool results (model arithmetic, a summed total, a reworded date) must be withheld, including spelled dates ("10 November"). (Task 1 test `test_a_reply_stating_a_figure_not_in_the_tool_results_is_withheld`.)
2. After "What do they owe?" about Logistics, "and their invoices?" must stay on Logistics; "and Supplies?" must switch. (Task 3 tests.)
3. Staff asking for "everything about X including what the owner said" must get the overview and only staff-shared context, with no sentence implying more exists. (Task 1 test.)
4. A multi-part ask ("overview, overdue invoices and anything the owner shared") must be answered in one reply, not one part. (Task 1 mock test + Task 5 live scenario.)
5. `prepareCustomer` must create nothing until the person presses Create in the existing dialog; a duplicate name must surface the existing customer instead. (Task 2 tests.)

---

### Task 1: The desk agent loop, reply guard and answer card (server + coordinator + desk.js rendering of `answer`)

**Files:** modify `prototype/coordinator.py` (new: `DESK_SYSTEM`, `DESK_TOOLS`, `desk_messages(...)`, `desk_run(adapter, caller, dispatcher, *, text, role, recent_turns, business_date, focus) -> {'reply', 'show', 'nextStep', 'calls', 'stats', 'withheld'}`, `guard_reply(text, known_text) -> (text|None, reason)`, mock scripting), `prototype/server.py` (`DeskTools` dispatcher class with the read tools above built on existing position/context/case code; `desk_turn` calls `desk_run` outside the lock, stores the person's turn and one `answer` card turn `{type:'answer', text, about: {customerId, name}|null, show: {...blocks...}, nextStep, withheld}`; keeps intake and interpretation as tools; removes the four-category path and `DESK_SCOPE`), `prototype/web/desk.js` (render the new `answer` card: prose, blocks collapsed except the first, one next-step control), tests `prototype/test_desk_agent.py` (replaces the question tests that assumed categories; keep every permission assertion).

**Interfaces produced:** tool result shapes are JSON the model sees, minimised (no internal ids beyond `customerId`, `invoiceId`, `requestId`); `known_text` = the concatenation of all tool results' values as strings plus their display forms (amounts as `AUD 1,200.00`, dates as both ISO and `Tue 10 Nov 2026`); `reply` schema `{text: str, show: [enum], nextStep: {kind: 'open'|'draft'|'ask'|'decide'|'none', target: str|null, label: str|null}}`; mock rules: name → `findCustomers`; "owe|balance|overview" → `customerOverview`; "overdue|invoice" → `invoices`; "owner|said|shared|context" → `ownerContext`; "status|request|case" → `cases`; "where|how do i|add a customer|add customer" → `whereIs`; "add <Name> as a customer" → `prepareCustomer`; a request sentence (reference + date) → `openRequest`; owner statement with no question → `interpretStatement`; then `reply` with a template sentence built from the tool results (so the guard passes) and `show` for what was fetched.

- [ ] Tests first (mock): multi-part ask answered in one card with overview + invoices + context blocks; staff get only shared context and a reply with no "the owner has not said more"-type sentence; owner-only data never in staff payloads; a figure not in tool results is withheld (patch the mock reply); "where do I add a customer?" → navigation block with route `#/customers` and label "Add customer" and a next-step `open`; unknown customer → "which customer?" list; the intake and interpretation flows still work through the loop (`test_desk_api` stays green); tool-call cap respected; adapter failure → the fixed unreadable sentence, nothing stored.
- [ ] Implement; run `test_desk_agent`, `test_desk_api`, `test_desk_questions` (rewrite the latter onto the loop), the suite; `desk_check.js` (update the D-checks that typed questions; keep names). Commit.

### Task 2: Actions: prepared customer, navigation, shorter alternative

**Files:** `prototype/server.py` (`prepareCustomer` tool: checks `find_customers` for an existing or similar name and returns `{existing: [...]}` or `{draft: {name}}`; `whereIs` map as a constant `WHERE_IS` with topic → `{route, label, steps}`), `prototype/web/desk.js` (draft card "Create customer" button opens the existing `customers.js` add-customer dialog prefilled; after creation the thread gets a text turn "Customer <name> added" and focus moves to it), `prototype/coordinator.py` (`SUGGEST_SYSTEM`: within a day limit, suggest the latest allowed date; `validate_suggestion` unchanged), tests in `test_desk_agent.py` and `test_suggestion.py` (`test_a_request_beyond_the_limit_gets_the_latest_date_within_it` via the mock).

- [ ] Tests first; implement; `desk_check.js` gains D-checks for "add Riverside Bakery as a customer" → draft → Create → customer exists; commit.

### Task 3: Focus and continuity

**Files:** `prototype/server.py` (thread `focus` per role; set by `findCustomers`' single match and by explicit `about` of a reply; passed to the model as "current customer: <name>" with the last 6 turns; cleared on "another customer" phrasing is the model's job, the code only follows tool results), `prototype/coordinator.py` (DESK prompt: pronouns refer to the current customer; a new name switches), tests: Logistics → "and their invoices?" stays; "and Supplies?" switches; a question after a request keeps the case's customer in a case thread; the owner and staff have separate focus.

- [ ] Tests first; implement; commit.

### Task 4: Case thread hierarchy and staff status

**Files:** `prototype/web/desk.js`, `prototype/web/app.css`, `deploy/desk_check.js`, `deploy/layout_check.js` (measure that the decision controls are within the first 900 px of the owner's case thread at 1366 px and that nothing is duplicated: each of "Open the full case", "Customer records", "Sources" appears once per thread).

- [ ] Checks first (fail on the current layout), implement §0.5, run `desk_check`, `layout_check`, 375/390 px; commit.

### Task 5: Conversational validation

**Files:** `deploy/conversation_check.js <base> <log> <outDir> [--live]` with a scenario file `deploy/conversations.json`: ≥ 12 scenarios, each a sequence of turns per role with assertions (customer the answer is about; which blocks appear; numbers equal `/api/records`; staff/owner visibility; next step present when the scenario says so), including: varied wording for "what does X owe" (5 phrasings), follow-ups with pronouns, switching customers mid-thread, a three-part ask, navigation questions, adding a customer by conversation, an owner context paragraph followed by a request, a request beyond the stated limit (expect a shorter alternative), a staff attempt to get owner context. Mock run: all assertions deterministic. Live run: structural assertions plus the transcripts written to `docs/qa/CONVERSATION-REVIEW.md` with a rubric table (understandable? task completable without splitting? next step clear?) filled by a reader (an Opus reviewer in this run, labelled as such; a human column left empty).

- [ ] Write the scenarios and the runner; run on the mock (all pass) and on the live model (record); commit the review document.

### Task 6: Records and preview

**Files:** PROMPTS.md (`coordinator-v0.3`: desk loop prompt, tools, reply schema, guards, mock rules; observed live behaviour), `docs/AGENT-COORDINATOR-PROPOSAL.md` (revision 3 notes), `docs/DECISIONS.md` (E020: the team's direction of 20 October and this slice), `docs/UX-REDESIGN.md`, `prototype/README.md`, `docs/DEPLOYMENT.md` (preview section updated), `docs/project-state.json` + `python3 tools/build_brief.py`.

- [ ] Write; deploy to the preview (push first); verify through the public URL as both roles with the live model (a short scripted pass: a three-part ask, a follow-up, a switch, "where do I add a customer", add a customer, a request beyond a limit); record results; commit and push.
