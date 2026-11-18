# Engineering inventory — 30 October 2026

Status: verified read-only inventory of the local M3 code (commit `83b3efb`, branch lineage `feat/adaptive-decision-authority-20261026`), produced by Claude Code on 30 Oct 2026 from direct code inspection. It supersedes the code-level parts of ENGINEERING-SNAPSHOT.md and the "Current engineering evidence" column of FEATURE-REGISTER.md. Product decisions are NOT in this file; see docs/product/POV-IMPLEMENTATION-PLAN-20261030.md and docs/memory/DECISION-REGISTER.md.

Labels: **Verified** = checked in code/git by the author; **Reported** = from developer handover/docs, not re-run; **Not verified** = could not be confirmed.

Path keys used below. `M` = main checkout `~/Developer/Project-Nucleon`; `W` = worktree `~/Developer/Project-Nucleon-ada`; `L` = `~/Developer/nucleon-local`; `LC` = `~/Developer/LibreChat`. In section 4, `S` = `prototype/server.py`, `D` = `prototype/delegation.py` (paths relative to `M/prototype/`). In section 5, `lab/...` is relative to `M`.

---

## 1. Git and deployment facts (Verified)

| Item | Fact |
|---|---|
| GitHub `main` | `f19b2bc`. Documentation only: no `prototype/`, `lab/`, `deploy/`. |
| PR #4 branch | `docs/week7-feedback-pov-reorganisation-20261030` at `5221c02`. Documentation only (same: no `prototype/`, `lab/`, `deploy/`). |
| Code branch | `feat/adaptive-decision-authority-20261026` at `777fbb8`, pushed. Application code exists only here and in local checkouts. |
| Local checkout `M` | Detached at `83b3efb` = `da95220` + docs `465ad7e` + Lab tailnet origin `83b3efb`. No uncommitted changes. No unpushed commits. |
| Worktrees | `Project-Nucleon-ada` (`777fbb8`); `Project-Nucleon-memory` (`258c078`, historical); `Project-Nucleon-phaseB` (`f4febc2`, historical). |
| Local runtime | `~/Developer/nucleon-local`. Records runs from `M` under system `python3` (3.9) on port 8631. Lab runs from a venv (3.12) on 8630. |
| LibreChat | v0.8.8, custom image `librechat:nucleon-card-v0.8.8-rc4-tailnet`, bound to 127.0.0.1:3080. |
| Exposure | Tailscale Serve: `:443` -> 3080, `:8443` -> 8631. Tailnet only. |
| M6 (`nucleon.dracooz.top`) | Runs pre-ADA code `0d54e9f` with real QA data. Untouched. It is not ADA. |

Notes:
- Deployed commit is `83b3efb`, not `da95220` (see section 6, item 3).
- `M` is a detached checkout, not a branch.

---

## 2. Code size (Verified; line counts)

| Area | Total lines | Largest files |
|---|---|---|
| `prototype/` | 34,497 | server.py 6,719; importer.py 1,680; coordinator.py 1,672; agent.py 1,217; records.py 1,104; delegation.py 782 |
| `prototype/web/` (subset) | n/a | requests.js 802; customers.js 633; core.js 597; desk.js 498; actions.js 368; delegation.js 275 |
| `lab/` | 11,821 | tests/test_agent.py 1,929; guard.py 723; card.py 576; agent.py 470; web/src/cards/act.tsx 451; tools.py 445 |
| `deploy/` | 7,634 | lab_check.js 1,614; ui_check.js 741; validate_import.py 722; desk_check.js 621; lab_conversation_check.js 426 |

Tests:
- Prototype: 42 `test_*.py` files, 955 `def test_` (grep count, **not run**). **Verified** as a count only.
- Lab: 383 tests. **Reported**.
- Largest prototype tests: test_delegation.py (129 tests, 2,143 lines), test_controlled_actions.py (1,300 lines), test_import_proposal.py (1,022 lines).

---

## 3. Three agent runtimes (Verified)

| Runtime | Components | Local state |
|---|---|---|
| (a) LibreChat + Qwen via MCP | LibreChat agent "Nucleon ADA Staff (Qwen)" -> Lab `/mcp/` -> Records `/api/tools` | **The one in use.** |
| (b) Lab's own agent + page | Pydantic-AI agent (`lab/agent.py`, `lab/tools.py`, `lab/guard.py`) + React assistant-ui page (`lab/web`) | Model `mock` locally; `lab/web/dist` not built; not used. |
| (c) Records desk chat | `prototype/agent.py`, coordinator runner, `web/desk.js`, `threads`/`turns` tables | `agentMode` mock locally; not used. |

**After S2a (31 Oct 2026, branch `s2/owner-surfaces`):** only runtime (a), LibreChat + Qwen through the Lab's MCP server to Records `/api/tools`, remains. Runtime (b) went in S0; runtime (c), the Records desk chat (`web/desk.js`, `/api/desk/*`, the desk prompt and loop `desk_run`, the reply guard, the desk mock, statement confirm/retire), went in S2a (commits `c357929`, `aa2c391`; history under tag `poc-week7`). Kept on purpose: `prototype/agent.py` (case analysis), `DeskTools` (the executor behind `POST /api/tools/<name>`), `CAPABILITIES`/`DESK_TOOLS` (without the old `reply` tool), `desk_done`/`desk_remember` (used by `set_agent_tool`), and the `threads`/`turns` tables with their store methods and `DATA_TABLES`. Tests that drove the tools through the desk now call `/api/tools/<name>` (`test_helpers.py`, `test_tool_reads.py`).

Pruning warning: `prototype/coordinator.py` also holds the `CAPABILITIES` tool registry (`coordinator.py:367-431`) that the MCP server exposes. The registry must survive any removal of runtime (c).

---

## 4. Records backend (`M/prototype/`; Verified unless marked)

### 4.1 Data model
All tables are created in `S:ensure_schema`, lines 553-593. Most store a JSON `data` blob.

| Table | Purpose |
|---|---|
| `fixtures` | Records document: settings (currency, scale, time zone), as-of date. |
| `requests` (`id`, `data`) | Legacy extension request/case, one JSON record each (S:555). Holds analysis, assessment, decision, responseDraft, `delegation` link. |
| `events` (`seq`, `request_id`, `kind`, `at`, `data`) | Append-only per-request timeline (S:556). The audit log. |
| `idempotency` | Request-creation dedup (S:559). |
| `runs` | Model analysis runs, one running per request (S:561). |
| `meta`, `batches`, `profiles` | Misc state, import batches, import profiles. |
| `record_ops` (`key`, `payload_hash`, `result`, later `state`, `at`, `boot`) | Idempotency for tool calls and Owner feedback (S:568-598). |
| `customers`, `invoices`, `notes`, `payments`, `allocations`, `opening_balances`, `coverage`, `statements` | The Records ledger (S:569-581). |
| `threads`, `turns` | Desk chat. |
| `actions` (`id`, `kind`, `status`, `invoice_id`, `created_at`, `data`) | Controlled actions: Staff confirm, and the Staff evidence request (kind `evidence`). |
| `delegation_policies` (`version` PK, `created_at`, `data`) | Immutable policy versions, insert-only (S:588). |
| `decision_cases` (`id`, `kind`, `subject`, `status`, `dataset`, `created_at`, `updated_at`, `data`) | Delegation case. Unique index `one_live_case` per (kind, subject), S:591. `dataset` is `live`, `fictional_example` or `fictional_evaluation`. |
| `confirmed_facts` (`id`, `customer_id`, `kind`, `created_at`, `data`) | Staff-verified evidence with provenance (S:593). |

Concept mapping:
- Requests/cases = `decision_cases` + `requests` (type `payment_extension` only, S:1459).
- Policy = `delegation_policies`.
- Decisions = `decision_cases.data.decision` / `requests.data.decision`.
- Memory = `decision_cases` itself (`S:dg_memory`, 2031).
- Feedback/override live in `decision_cases.data` (`feedback[]`, `override`); extensions also `requests.data.decisionHistory` + `decision.overridden` event.
- Evidence = `confirmed_facts` + `actions` kind evidence + `decision_cases.data.evidenceItems`.
- Audit events exist only for `requests`; trial-credit cases only have `case['history']` JSON.
- Outcomes = `payments`/`allocations`; there is no outcome table.

### 4.2 Policy engine (`D`)
- `POLICY_KEYS` D:67. `default_policy` D:70: advisory, everything off, limits zero. `validate_policy` D:138 is strict; unknown key -> 400.
- Keys: `mode` (advisory|delegated), `paused`, `limits{maxDecisionExposure, maxCustomerExposure, maxAutonomousExposure30d}`, `extensions{enabled, maxDays 0-365, requireNothingElseOverdue, maxPriorLateShare}`, `newCustomers{trialCredit off|limited, maxExposure, minDepositShare, maxTermsDays, tradeReferenceAbove, staffCheckedDepositUpTo}`, `evidence.confirmedCoverageAbove`, `restrictions{holdCustomers[], unusualSizeMultiple}`, `trackRecord{minReviewedCases default 5, minAgreement default 0.8}`.
- Versioning: `S:save_policy` (1895) inserts version+1; Owner person only; `expectedVersion` (409 `POLICY_CHANGED`); csrf. Pause/resume are versions. `policy_digest` (D:84) is sha256; every decision records version + digest.
- `KINDS = ('extension', 'trial_credit')` (D:23). `HANDLINGS` D:26, `RECOMMENDATIONS` D:27.

`D:evaluate` (D:670), first-match ladder:

| Step | Handling | Condition |
|---|---|---|
| 1 | policy_hold | Held customer, or contradictory evidence |
| 2 | owner_review | Risk check fails |
| 3 | request_evidence | Staff-obtainable evidence missing (even in advisory mode) |
| 4 | owner_review | Evidence insufficient and not obtainable |
| 5 | owner_review | Risk unknown |
| 6 | owner_review | Close comparables mostly declined |
| 7 | owner_review | Track record not established |
| 8 | owner_review | Not delegated / paused / category off |
| 9 | owner_review | Assistant did not recommend approve |
| 10 | autonomous_approve | All of the above passed |

Three checks feed the ladder:
- `assess_evidence` (D:394) -> sufficient|missing|insufficient|contradictory. Uses `deposit_state` (D:330; 30-day recency, levels, `staffCheckedDepositUpTo`), identity 365 days, trade reference, no-prior-account contradiction, coverage.
- `risk_checks` (D:231) -> pass|fail|unknown|na per bound; `risk_summary` (D:293). Features: `features_of` (D:630) from `S:dg_ledger` (1943) + `S:dg_lines` (2071).
- `track_record` (D:538) back-tests on `fictional_evaluation` only and gates step 7. Live Owner-reviewed cases are back-tested separately and only reported. `declined_majority` (D:518) feeds step 6.

Outcomes:
- autonomous_approve is executed in `S:dg_apply` (2252).
- owner_review / policy_hold escalate; request_evidence creates an `actions` evidence row.
- There is no autonomous decline: D:9, step 9; `validate_policy` rejects `autoDecline`/`allowExternalMessages` (D:138-142); `COMMUNICATION` D:41.
- 30-day rolling exposure: `S:dg_autonomous` (2075) sums live agent decisions in force within 30 days (`dg_in_force` S:2056; overridden stops counting), compared in `risk_checks` (D:247). Customer aggregate `customerExposure` is in `features_of`.

### 4.3 Decision lifecycle
- **Agent path.** Tools `assessDecision` (read, stores nothing, S:2131) and `resolveDecision`, registered via `/api/tools/<name>` (S:6393); impl `_assessDecision`/`_resolveDecision` (S:6014/6028). `delegation_resolve` (S:2233) creates the case (`uid('case')`), evaluates, and runs `dg_apply` in one transaction. It stores frozen evaluation, handling, features, authority, policy; on approval sets decision `by: 'agent'`, `decidedBy: nucleon_agent`, `authoritySource`, `requestedBy`.
- **Evidence path.** Status `gathering_evidence` + `actions` row (`dg_evidence_action`, S:2330). Staff person submits `POST /api/actions/<id>/evidence` (route S:6546, `submit_evidence` S:2404). Facts go to `confirmed_facts`. `reapply` (S:2433) re-evaluates under the CURRENT policy.
- **Escalation.** `awaiting_owner` or `on_hold`. An extension also creates a legacy `requests` row via `dg_open_request` (channel `delegated_agent`).
- **Owner decision.** Trial credit: `POST /api/decision-cases/<id>/decide` (S:6575, `decide_case` S:2455; reason required; sets `agreement`). Extension: `POST /api/requests/<id>/decisions` (S:6618, `App.decide` S:1570 -> `dg_request_decided` S:2485, same transaction). On hold -> `owner_exception`.
- **Feedback / override.** `POST /api/decision-cases/<id>/feedback` (`case_feedback`, S:2510): verdict agree|disagree, reason, override, case `version`; Idempotency-Key via `record_ops`. Override only on an agent approval; it replaces the decision (extension -> decline; trial line revoked) and records `overridesPolicyVersion` and `externalEffects`.
- **Reads.** `GET /api/delegation/policy`, `/policy/history`, `/cases`, `/suggestions`, `/stats` (S:6557-6574); `GET /api/decision-cases/<id>` (S:6575). Owner writes (`DELEGATION_WRITE`, S:123) need Origin, csrf and `person_required`.
- **Event log.** Extensions: yes (`events`, `S:event` 769: request.received, analysis.*, decision.committed, decision.overridden). Delegation cases: NO events table; mutable `history[]` rewritten by `dg_put` (S:1999); `recommendationHistory` only while gathering evidence; evaluation frozen in `case.evaluation`.
- **Owner reasons.** `decision.reason`, `feedback[].reason`, `override.reason`, extensions `requests.data.decision.reason`. Staff views strip `ownerReason` (S:2108). An optional `remember` note is stored as a statement.

### 4.4 Decision memory and reliability
- `D:comparables` (499), `distance` (483): deterministic weighted distance over new-customer flag, log exposure ratio, days/terms relative difference, deposit or late share, nothing-else-overdue. Top 5; similarity `1/(1+d)`. Pool = `fictional_example` + `live` with Owner verdict (`RETRIEVAL` D:25); the evaluation set is held out. `sameCustomer` flag; others labelled analogy.
- Stored per decision in `decision_cases.data`: features, evaluation (frozen), params, recommendation (reasoning; chat context marked unverified), actor, policy{version,digest,mode}, decision, feedback[], override, history[], evidenceItems.
- Owner verdict for memory (`S:dg_owner_view`, 2018): Owner-decided -> the decision; agent-decided -> feedback verdict (agree -> approve, disagree -> decline); agent-decided with NO feedback -> not counted.
- Reliability: `track_record` gates on the fictional evaluation set only; the live back-test is reported, not gating; defaults 5 cases / 0.8.
- Repayment outcome: `D:derive_outcome` (558) -> repaid | open_not_due | open_past_due | unknown. `S:dg_outcome` (2049) computes it on read; **not persisted**. Shown in `case_view` (S:2118) and attached to comparables.
- Not covered by outcomes: late-then-paid, partial payment, write-off/loss, outcomes of declined cases. For extensions "repaid" = invoice no longer open; on-time is not checked.

### 4.5 Policy suggestions
- `D:suggestions` (579) is deterministic. It proposes raising `newCustomers.maxExposure` or `extensions.maxDays` when at least 3 consecutive cases just above the bound were Owner-approved AND repaid. `suggestionOnly: True`; never relaxes restrictions.
- `GET /api/delegation/suggestions` (S:2587), Owner-only.
- Older per-request, model-written suggestion: `/api/suggestions`, counters `/api/suggestions/counters` (S:2807), `requests.suggestionSeen.relation` (S:1613).

### 4.6 Metrics derivable now
- From `decision_cases`: `created_at`, `status`, `dataset`, `kind`, `data.handling`.
- Decision fields: `data.decision.by` (agent|owner|owner_exception), `.at`, `.outcome`, `.decidedByKind`; `decision.exposure`/`creditLine`; `decision.agreement`; `feedback[].verdict`; `decision.overridden`/`overriddenAt`; `override.reason`/`overridesPolicyVersion`.
- Derived: time to decision = `decision.at` - `created_at`; evidence turnaround = `actions.created_at` -> `confirmed_facts.created_at` / `provenance.at`.
- Evaluation: `data.evaluation.step/.reasons/.why`; evidence requests = `actions` kind evidence with `data.needs[]`, `data.evidenceItems[]`; `data.policy.version/.digest`.
- `GET /api/delegation/stats` (S:2595): live counts only (autonomous, gatheringEvidence, ownerReview, onHold, ownerDecided, overrides, closed).
- Extension `events` rows.
- **NOT captured:** Owner time per case, Owner viewed timestamp, baseline.

### 4.7 Auth and roles
- `ROLES = (staff, owner, operator)` (S:55); `CASE_ROLES` (S:56). `App.login` (S:1382) uses a per-role random access code; operator = demo console only. Cookie session (`signed_in`, S:1359) + csrf.
- `service_codes` -> `channel: 'service'` session (Lab/MCP identity). Service sessions cannot confirm, cancel, submit evidence, or write policy or decisions (`person_required`, S:1774).
- AI Agent: `agent_code`, `AGENT_ID='ai_agent'` (S:57), `kind:'agent'` sessions for all roles (S:1393), blocked by `person_required`. Agent decisions carry `decidedBy = nucleon_agent` (`AGENT_DECIDER`, S:70); the requester is kept in `requestedBy`.
- Browser writes need Origin in `allowed_origins`; policy/decision writes also need csrf.
- Staff cannot read Owner reasons or policy `createdBy` (`policy_view`).

### 4.8 Web UI (`web/`, no build step; `index.html` loads all scripts; hash router)
Routes: `#/requests`, `#/cases`, `#/actions/<id>`, `#/customers`, `#/imports`, `#/knowledge`, `#/setup`, `#/delegation`, `#/console`.

| File | Lines | Role |
|---|---|---|
| core.js | 597 | `api()`, dialogs, sessions/roles, router, nav |
| requests.js | 802 | OLD request queue + case page, SAMPLES |
| desk.js | 498 | Desk chat on `#/requests` |
| actions.js | 368 | Staff confirm/cancel + evidence form (POST evidence at actions.js:344) |
| delegation.js | 275 | Owner ADA page: policy form/PUT, history, pause/resume, queue, feedback/override, suggestions, stats |
| customers.js | 633 | Customers |
| imports.js | 300 | Imports |
| knowledge.js | 45 | Knowledge |
| setup.js | 98 | Setup |
| console.js | 95 | Operator console |

Old = requests.js / `#/cases`; newer = delegation.js, actions.js evidence, desk.js.

**After S2a (31 Oct 2026).** Where this differs from the table above, this wins.
- **Routes:** `#/` is the role landing page (`home.js`, `PAGES.home`); `#/cases` is the request queue (`#/requests` is an alias); `#/case/<id>`, `#/actions/<id>`, `#/customers`, `#/imports`, `#/knowledge`, `#/setup`, `#/delegation` (titled **Control panel**), `#/console` as before. New Owner-only placeholders `#/review` and `#/dashboard` ("coming in S2b"); Staff get Page not found there. `#/requests/thread/<id>` and `#/requests/new` are gone with the desk.
- **Files:** `desk.js` (498 lines) deleted; `home.js` (94 lines) new; `core.js` 645, `delegation.js` 312, `requests.js` 802.
- **Navigation (`NAV` in core.js), one list for both roles:** Home, Assistant (new tab, only when the config sets `assistantUrl`), Requests, Customers, Imports, Knowledge, Setup; Owner also Control panel, Review, Dashboard. The current page is marked `aria-current`. At phone width the tab bar holds Home, Requests, Customers, Imports and a More menu with the rest; the Owner's header navigation takes its own row below 1500 px. The practice-workspace line is unchanged.
- **Landing page:** Owner: Waiting for you (count and list, from `/api/delegation/cases`), the last five agent decisions with status, live counts, big links (assistant, Control panel, Review). Staff: the assistant first, Requests, Customers, Imports, and the requests that wait on them (`/api/requests`). There is still no read-only list of the evidence requests waiting for Staff (`#/actions/<id>` is reached from the assistant's link), so the landing page does not list them.
- **`assistantUrl`:** optional config key, an http(s) link checked at start; `GET /api/session` returns it (`null` when unset) and the pages hide the assistant links then.
- **Self-refresh:** `keepFresh`/`REFRESH` in core.js: the Owner's home and control panel (and the Staff home's waiting list) re-read every 20 s while visible and when the window or tab regains focus; the control panel keeps typed reasons, form edits, the open Advanced section and focus, and does not read during a save. A link to the page already open draws it again.
- **Lost with the desk (API unchanged):** the Owner's web UI for the advisory suggestion, the brief's open questions, and the prepared-decision Confirm button existed only on the desk. The old request page (`#/case/<id>`) still decides escalated extensions; the tools that prepare, suggest and answer remain on `POST /api/tools/<name>` and the MCP server.
- **Tests:** 1027 (Python 3.9 and 3.12; was 1089 before S2a), Lab 122, `deploy/delegation_page_check.py` 59/59, `deploy/home_page_check.py` 56/56, `layout_check.js` 204/204 and `ui_check.js` 150/150 on scratch servers. Deleted: `test_desk_agent.py` (28), `test_desk_api.py` (13), `ReplyGuardTests` (13), desk-prose tests in test_presentation (14), test_situation, test_tool_surface, test_concern_loop, test_balance_semantics; added `test_tool_reads.py` (12) and two `assistantUrl` tests.

**After S2b (31 Oct 2026).** Where this differs from the S2a note, this wins.
- **Routes:** `#/review` (Owner; `review.js`, the one place to decide, agree, disagree and override), `#/dashboard` (Owner; `dashboard.js`) and `#/decision-cases/<caseId>` (Owner and Staff; `timeline.js`, the case timeline) are real pages; the S2a placeholders are gone from `home.js`. Staff still get Page not found at `#/review` and `#/dashboard`.
- **Files:** `review.js`, `timeline.js`, `dashboard.js` new; `core.js` gains the page-use capture (`TRACK`, `trackEvent`, `flushTrack`, `data-track` clicks, `decideStart/decideDone`, `sendBeacon` on unload with `?role=` in the address); `delegation.js` loses the decide/feedback controls (its waiting and recent sections link to Review and the timeline), gains the tacit-days and track-record-sources controls with the gate's counts, and defines `feedbackText`/`gateWords`/`timelineLink` the other pages share; `home.js` lists the open evidence requests for Staff and links Owner rows to Review and the timeline. `deploy/page_check_lib.py` is the shared helper of the new page checks.
- **Navigation:** unchanged list; the case timeline marks Review (Owner) or Requests (Staff) as the current page.
- **Self-refresh:** the Review page and the Dashboard join `REFRESH` (20 s, on focus); Review keeps typed reasons, open rows, the override confirmation and focus; the Dashboard keeps the filter being typed.
- **Tests:** 1056 (Python 3.9 and 3.12; was 1027), Lab 122; `deploy/delegation_page_check.py` 67/67, `home_page_check.py` 61/61, `action_page_check.py` 42/42, `review_page_check.py` 84/84, `dashboard_page_check.py` 34/34.

### 4.9 Tests
- 42 `test_*.py`, 955 `def test_` (**not run** in this inventory).
- Run: `python3 -m unittest discover -s prototype -p 'test_*.py' -v` (README.md:402). `deploy/nucleonctl:98` runs the same with `runtime/python-3.12.14`.
- Deployment pins Python 3.12.14 (docs/DEPLOYMENT.md:77); local Records runs on system 3.9.

### 4.10 Gaps against a complete decision feedback loop
Exists:
- Request -> evidence with provenance.
- Immutable policy versions + digest on every decision.
- Agent decision with frozen evaluation.
- Owner decision / feedback / override / reasons stored.
- Comparables using live Owner verdicts.
- Derived repayment label.
- Deterministic suggestions that read outcome.

Missing:
- No stored outcome (read-time only, no `observed_at`; label changes if the ledger is edited).
- Coarse outcome vocabulary: no late-paid / partial / written-off / defaulted; on-time vs late not distinguished.
- No outcome for declined or escalated-declined cases.
- Agent-approved cases without feedback are ignored by memory.
- Reliability gate uses the fictional set only.
- No immutable per-case event log for delegation cases.
- Stats are workflow counts only (no time series, latency, per-version, dollar impact).
- Suggestions only raise two limits (no tightening).
- Memory is not partitioned by policy version.
- Old-flow extension requests do not feed memory.
- No time-to-decision / Staff-effort / baseline metrics.

### 4.11 After S1 (30/31 Oct)
Branch `s1/decision-loop-backend` (S1a `2a9c72e`..`97796f3`, S1b after it). Sections 4.1-4.10 above describe the code before S1; where they differ, this subsection wins. Detail: ADA doc section 10, "As built (S1a)" and "(S1b)".
- **New table:** `case_events` (`seq`, `case_id`, `kind`, `at`, `actor`, `policy_version`, `data`), append-only, written in the state change's transaction; delegation cases now have a timeline (the gap in 4.3 and 4.10).
- **New modules:** `prototype/outcomes.py` (pure outcome observation rules, stored as `data.outcomeObserved` plus an `outcome_observed` event), `prototype/impact.py` (pure impact report over live `decision_cases` + `case_events`).
- **New policy keys:** `feedback.tacitAgreeAfterDays` (null = off; 1-365), `trackRecord.sources` (`fictional | live | both`, default `both`). Old stored versions read as off / `both` and keep their digests.
- **Changed rule input:** ladder step 7 (`track_record`) counts the fictional evaluation set, live Owner-reviewed cases (explicit and tacit apart) or both pooled; the "fictional only" statements in 4.2 and 4.4 are now the `fictional` setting. `reliability` adds `sources`, `gatedOn`, `gate`.
- **New routes:** `GET /api/decision-cases/<id>/events`, `POST /api/decision-cases/<id>/viewed`, `POST /api/delegation/observe-outcomes`, `POST /api/delegation/sweep-tacit-consent`, `GET /api/delegation/impact?from=&to=&policyVersion=` (Owner person). `GET /api/delegation/suggestions` now also lowers bounds and proposes advisory mode after two overrides.
- **Tool surface:** `assessDecision`, `resolveDecision`, `decisionStatus` add `hint` on a refused call and `forModel` on a success (both additive).
- **Closed gaps from 4.10:** stored outcomes with a finer vocabulary, event log, tacit consent, live gate, tightening suggestions, time to decision, Owner view timestamps (needs the Owner page to post `viewed`, S2).
- **Still open:** write-off is in the vocabulary but nothing produces it; no baseline, so `timeSaved` is an assumption placeholder; memory is not partitioned by policy version; old-flow extension requests do not feed memory; the Owner policy form does not send `trackRecord.sources` or `feedback.tacitAgreeAfterDays`, so `save_policy` keeps the current values of exactly these two when a PUT omits them, until S2 adds the controls.
- **Tests:** 1081 (`python3` 3.9 and 3.12), Lab 122, page check 59/59.

**After S2b (31 Oct 2026).** Branch `s2b/owner-pages`. Detail: ADA doc section 10, "As built (S2b)".
- **New table:** `ui_events` (`seq`, `at`, `role`, `channel`, `page`, `kind`, `data`), in `DATA_TABLES`; page-use telemetry (D11), local only.
- **New routes:** `GET /api/delegation/loop`, `POST /api/ui-events`, `GET /api/delegation/ui-summary?from&to` (Owner person), `GET /api/actions?kind=evidence&status=open` (Staff, Owner, service; read-only).
- **New pure functions** in `impact.py`: `loop_stage`, `loop_counts`, `ui_summary`.
- **Additive fields:** case rows `why`, `comparables`, `reliability`, `overrideEffects`; `stats.trackRecord`; tacit feedback `afterDays`.
- **Closed from "Still open" above:** the Owner policy form now sends `trackRecord.sources` and `feedback.tacitAgreeAfterDays`; the Owner page posts `viewed`, so `ownerInterventionSeconds` can be measured; the evidence requests waiting for Staff have a read-only list.
- **Still open:** `case_view` returns an Owner decision's `reason` to Staff (only the events route strips it); `ui_events` has no retention; write-off is never produced; no baseline for `timeSaved`; memory is not partitioned by policy version.
- **Tests:** 1056 (3.9 and 3.12), Lab 122.


---

## 5. Lab, MCP, cards, LibreChat, runtime, deploy checks, M6, frontend (Verified unless marked)

### 5.1 Lab / MCP server (`lab/`)
- Starlette app (`lab/app.py:343`) with two front doors onto Records: its own chat API + assistant-ui page (`/api/threads/{id}/chat`, SSE, person cookie) and an MCP server at `/mcp/` (`lab/mcp_server.py`, service session).
- The Lab's internal Pydantic-AI agent (`lab/agent.py`, `tools.py`, `guard.py`) runs only for the Lab's own chat page; locally `model: mock`. LibreChat's Qwen reaches the backend only through MCP.
- No hard-coded tool list. MCP exposes the Records registry for the role (`GET /api/tools`) filtered by `exposed()` (`mcp_server.py:78-80`): kinds `read` and `prepare` pass; `act` only if in `ACTS = {withdrawPreparation, requestSuggestion, resolveDecision}` (`mcp_server.py:34`); `openRequest` never.
- Registry `CAPABILITIES` in `prototype/coordinator.py:367-431` (kind, roles, defaultEnabled, needsConfirmation). Read-only annotations come from `READ_ONLY` (`mcp_server.py:56`), fail closed.

| Tool | Purpose | Kind / RO | Roles | defaultEnabled |
|---|---|---|---|---|
| findCustomers | Find customers by name, code or invoice | read, RO | staff, owner | True |
| customerOverview | What a customer owes, open invoices, requests (financial card) | read, RO | both | True |
| invoices | Open, overdue or all invoices (financial card) | read, RO | both | True |
| ownerContext | What has been said that this person may see | read, RO | both | True |
| cases | Where requests stand | read, RO | both | True |
| caseDetails | One case as the person sees it | read, RO | both | True |
| whereIs | Where something is done in Nucleon | read, RO | both | True |
| compareExtension | Extension dates against the day limit | read, RO | both | True |
| workQueue | Which cases wait for whom | read, RO | both | True |
| listRequests | Requests by customer, invoice or status | read, RO | both | True |
| assessRequest | Facts vs owner's limits; stores an assessment version | read, non-RO | both | True |
| prepareCustomer | Draft a new customer | prepare | both | True |
| prepareHoldingMessage | Draft a message to copy | prepare | both | True |
| interpretStatement | Read the owner's statement for confirmation | prepare | owner | True |
| prepareDecision | Prepare the owner's decision | prepare | owner | True |
| proposeImport (Lab name prepareImport) | Propose a spreadsheet import | prepare | both | True |
| requestSuggestion | New advisory suggestion version | act (ACTS) | owner | True |
| withdrawPreparation | Withdraw a preparation | act (ACTS) | owner | True |
| raiseConcern, answerConcern | Concern / answer on a case | act, not exposed over MCP | staff / owner | True |
| openRequest | Open a case | act, never exposed | staff | True |
| prepareRequest | Controlled action: proposal for an extension (action card) | prepare | staff | False |
| actionStatus | Where a prepared action stands (action card) | read, RO | both | False |
| assessDecision | What the delegation policy would do; stores nothing (decision card) | read, RO | staff only | False |
| resolveDecision | Assistant's recommendation; backend approves within policy / asks evidence / escalates (decision card) | act (ACTS), non-RO | staff only | False |
| decisionStatus | Backend status of a decision case (decision card) | read, RO | both | False |

- `withdrawRequest`, `actWithinAuthority`, `applyImportProposal` have `roles: []` (page-only).
- Five `defaultEnabled=False` tools are switched on by the owner under Setup (`coordinator.py:366,419,424`). Which are on locally: **Not verified** (the ADA agent uses them, so they must be).
- `L/tests/mcp_check.py` lists `STAFF14` and `OWNER_EXTRA`.

**Auth to Records**
- Client sends `Authorization: Bearer <token>`. `config.mcpTokens` maps token (>=32 chars) -> owner|staff (`mcp_server.py:118-122`). Unknown token -> 401. Foreign Host -> 421 unless in `publicOrigins` (`mcp_server.py:109-112`).
- Lab signs in to Records per role with the service code (`POST /api/demo/login`; codes from `recordsLog`/`recordsCodes`), verifies `GET /api/session` says `channel == 'service'` and the right role (else logs out and raises) (`sign_in`, `mcp_server.py:135-155`); renews on 401.
- Per-call idempotency key from `_meta nucleon.lab/idempotencyKey`, else random (`operation_key`).
- Records refuse confirm/cancel to service/agent channels (`prototype/server.py:1776-1778`, PERSON_REQUIRED).

**Role enforcement**
- `lab/guard.py` holds output validators for the Lab's internal agent only (irrelevant to MCP).
- Roles are enforced by Records (registry per role + per-call checks). Lab adds bearer-token role fixing and the `OWNER_ONLY_ASK` regex (`guard.py:466`, used at `tools.py:157`). Staff results carry no owner guidance (`tools.py:33-38`).

### 5.2 MCP-UI cards (`lab/card.py`)
Server-side HTML renderer (not the React cards). `card_html` builds one self-contained, escaped HTML page per result; nothing is derived or summed (missing -> "Not recorded"/"Unavailable"). Appended as a second content item, `EmbeddedResource` mime `text/html` after the JSON (`mcp_server.py:183-187`); on render failure the JSON alone is returned. `CARD_TOOLS` at `card.py:29`.

| Card | Tools | Notes |
|---|---|---|
| Financial | customerOverview, invoices | Inert; CSP allows only a hash-pinned size script; "Confirmed records" only when `balanceEstablished`. |
| Action | prepareRequest, actionStatus | `action_card_html` card.py:325; "PROPOSED — NOT SUBMITTED" -> "SUBMITTED FOR OWNER REVIEW". |
| Decision | assessDecision, resolveDecision, decisionStatus | `decision_card_html` card.py:543. Badge from backend status/handling: APPROVED UNDER OWNER POLICY, WITH THE OWNER FOR REVIEW, INFORMATION NEEDED FROM STAFF, ON HOLD BY POLICY. Shows key facts, three dimensions, up to 3 comparables, warnings, Authority box, override box. Evidence-needed state shows one button "Provide information in Nucleon". |

**Confirmation-link flow**
- `confirm_url()` builds `<recordsPublicUrl>/#/actions/<actionId>`. It must match `CONFIRM_URL`: origin in `CONFIRM_ORIGINS` (http://127.0.0.1:8631, http://127.0.0.1:18631, https://nucleon.tail492813.ts.net:8443), path `/`, no query, `act_` + 16 lowercase hex (`card.py:253-257`). Never built from model text.
- Click posts `{type:'link', payload:{url}}` (`CLICK_SCRIPT`). LibreChat patches 0003/0004: `handleUIAction` opens only an allow-listed URL, on user activation, via `window.open(..., 'noopener,noreferrer')`.
- The origin list is duplicated in `lab/config.py` (recordsPublicUrl check) and LibreChat `ALLOWED_ORIGINS` ("must match on both sides", integrations/librechat/README.md).

### 5.3 Lab web (`lab/web`)
- Vite 8.3.4, React 19.3.1, TypeScript 6.0.3, `@assistant-ui/react` 0.15.30. Scripts: dev / build (`tsc -b && vite build`) / lint (oxlint) / preview; `base './'`.
- Source: App.tsx (sign-in, Staff/Owner switch, threads), Authority.tsx, runtime.ts, api.ts, cards/{act,assess,calc,read,since,index}.tsx, presenter/ (purpose **Not verified**).
- Served from `lab/web/dist` (`app.py:44,137-138,343-346`), placeholder if missing. `dist/` and `node_modules/` do not exist locally; `L/README` says "no web UI build". Not built or used locally.

### 5.4 LibreChat integration
- LibreChat v0.8.8, upstream `e8f3be0` (`LC/package.json`), config version 1.3.17. `LC/docker-compose.override.yml:4` sets image `librechat:nucleon-card-v0.8.8-rc4-tailnet`, binds 127.0.0.1:3080, mounts `librechat.yaml`. Live yaml equals `W`'s `librechat.yaml.example` after masking.
- `.env` holds `NUCLEON_STAFF_MCP_TOKEN`, `NUCLEON_OWNER_MCP_TOKEN`, `NUCLEON_LOCAL_STAFF_MCP_TOKEN` (variable names only).

MCP entries (streamable-http, `requiresOAuth` false, timeout 120000):

| Entry | URL | chatMenu |
|---|---|---|
| nucleon-staff | https://nucleon.dracooz.top/lab/mcp/ (line 51) | false |
| nucleon-owner | same URL, owner token (line 59) | false |
| nucleon-local-staff | http://host.docker.internal:8630/mcp/ | default |

`mcpSettings.allowedAddresses: ['host.docker.internal:8630']`. There is no owner connection to the local Lab.

Client patches (`W/integrations/librechat/patches`, on `e8f3be0`, client only):
- 0001: show MCP-UI cards by default in tool calls (ToolCallInfo card first, raw under "Output"; `MCPUIResource/supported.ts`).
- 0002: reveal card phases and remember manual disclosure (`cardDisclosure.ts`, in-memory).
- 0003: open allow-listed Nucleon confirmation links (`nucleonLinks.ts`; exact URL, user activation, loopback origins).
- 0004: allow the tailnet origin (https accepted for listed origins). This is the live image rc4-tailnet.

Agent scripts (`agents/*.js`, run via `docker exec ... mongosh`):
- `seed_ada_agent_3080.js` creates "Nucleon ADA Staff (Qwen)" on the live stack, cloning provider/model/params from an existing agent. Model **Not verified** in code; `L/README` says qwen3.5-35b-a3b via LM Studio, temperature 0.2 (**Reported**). Tools, all `_mcp_nucleon-local-staff`: findCustomers, customerOverview, invoices, assessDecision, resolveDecision, decisionStatus. Shared to role USER as `agent_viewer`.
- `seed_ada_agent.js` / `seed_phaseb_agent.js` (isolated stack on 3081); `seed_fixtures.js`; `update_ada_agent_instructions.js` (resolve once); `update_ada_agent_clarify.js` (L-001); `update_ada_agent_steps.js` (version in force).
- Other agents in live Mongo per `L/README` (e.g. "Nucleon LOCAL Staff (Qwen)", 10 read-only tools; "Nucleon CARD TEST – terse"): **Reported**, not verified.

**Superseded 31 Oct 2026:** the step list quoted below (assessDecision, once; whatIsNeeded once) is the old text. Since S7 phase B the live Staff steps are findCustomers then resolveDecision with an explicit ambiguity check (early stops with the old steps; see `docs/research/MODEL-BENCH-20261031.md`, A4/A5; decision D15). The current text is `integrations/librechat/agents/instructions_staff.txt`.

Instructions in force (`update_ada_agent_steps.js`, quoted):
1. "You help a member of staff handle customer credit requests. Use tools for every business fact; never invent numbers, dates, ids or invoice numbers."
2. "Each request is exactly one kind: a trial credit for a new customer (order amount and terms in days) or an extension of one existing invoice (its invoice number and the new due date). If the message mixes the two, or an extension names no invoice, ask Staff one short question about what they mean and stop; do not guess. If a tool returns INVALID_ARGUMENT or a schema error, ask Staff for the missing detail instead of retrying with made-up values."
3. "Steps for a request: 1) findCustomers (and the invoice for an extension). 2) assessDecision, once. 3) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. 4) Stop calling tools: the request is finished. Reply in two or three sentences that repeat the statusText of the resolveDecision result; the card shows the details."
4. "The backend applies the Owner's delegation policy: report ONLY the outcome the tool result states; never say something is approved unless the result says decided/approved. If information is needed from Staff, tell them to use the button on the card. Nothing is ever sent to the customer by Nucleon; Staff informs the customer."
5. "Use decisionStatus only when asked where a request stands, and then answer from its result."

### 5.5 Local runtime (`L`)
- `bin/nucleon-local` (zsh; start|stop|restart|status|logs|test-mcp): nohup, pid files in `run/`, logs in `logs/`, no launchd.
- Records: `cd $REPO && python3 prototype/server.py --config L/config/records.json` (system python3, 8631). Lab: `L/venv/bin/python -m lab --config L/config/lab.json` (3.12, 8630). `REPO` defaults to `~/Developer/Project-Nucleon`. `status` curls `/api/tools` and `/mcp/` expecting 401.
- `config/records.json` keys: port, db, agentMode (mock), sampleData, accessCodes{staff,owner}, serviceCodes{staff,owner}, publicOrigins (127.0.0.1:8631 + tailnet :8443).
- `config/lab.json` keys: host, port, rootPath "", recordsUrl, store, model (mock), publicOrigins (host.docker.internal:8630), mcpTokens (2), recordsCodes, recordsPublicUrl (tailnet).
- Also present: `owner-mcp-token` (mode 600), `team-members.json` (chatUrl, members name/email/username/password).

Acceptance and checks:
- `tests/ada-acceptance/accept_final.py`: Playwright browser acceptance on the real stack with real Qwen (LibreChat 3080, Records 8631, Lab). Three browser contexts (Staff chat, Owner `#/delegation`, Staff evidence page); backend via `lib.py` Api is the proof.
- Scenarios: 0 Owner saves delegated fictional policy; 1 Riverside financial card; 2 Bayview extension decided; 3 Northside trial credit; 4a-d Lakeside evidence (card button -> evidence page -> form -> decision -> fresh-chat status); 5 Harbourline -> Owner, no false approval; 6 Owner override; 7 pause/resume; 8 no outbound events, no ledger payment.
- Helpers: chat.py (LibreChat login via credentials file), pw.py, scen.py, chk.py, set_policy_page.py.
- `evidence/backend_acceptance.json` comes from a backend-only pass whose script was not found (how it was run: **Not verified**).
- `tests/mcp_check.py` (`nucleon-local test-mcp`): 401/421, role tool lists, owner-only rejected for staff, read-only calls.

Helper scripts:
- `bin/demo-reset`: stop; sqlite `.backup` to `backup/pre-reset-<ts>`; `prototype/delegation_demo.py --db ... --replace` (clean fictional ADA data, policy v0); restart; check LM Studio Qwen ctx 32768.
- `bin/demo-video-state`: restores `snapshots/after-video-20261028.sqlite3` (policy v1, Northside approved, Harbourline waiting, Lakeside approved).
- `demo-launcher` writes an HTML page with access codes (mode 600). `team-accounts` creates LibreChat USER accounts with view access to the ADA agent.

### 5.6 Deploy checks (`M/deploy`)
None drive LibreChat; all are scratch-server only (`scratch_only.js` refuses deployed ports).

| Script | Lines | What it does |
|---|---|---|
| lab_check.js | 1,614 | Playwright against the Lab's own chat page as owner/staff (needs built dist, mock model, `ui_check_server.py`). |
| ui_check.js | 741 | Playwright regression of Records web UI as staff/owner/operator. |
| desk_check.js | 621 | Records desk page `#/requests`. |
| lab_conversation_check.js | 426 | Node, no browser; scripted scenarios in `lab_conversations.json` over the Lab chat API; `--live` uses a real model. |
| validate_import.py | 722 | stdlib; checks imported Records DB vs source ledger xlsx; `--selftest`. |
| e2e_*, browser_check, delegation_page_check | n/a | Not read in detail (**Not verified**). |

### 5.7 M6 remote (config facts only)
- Host `nucleon.dracooz.top`. `nucleon.caddy`: Lab under `/lab/` (8622); its Records under `/lab/records/` (8623); MCP at https://nucleon.dracooz.top/lab/mcp/; `/preview/` -> 8621; default -> 8620. LibreChat uses two bearer tokens (staff/owner), both `chatMenu` false.
- Differences from local (`L/README`, ADA rollout plan; **Reported**): M6 has real QA data vs local 2 fictional customers / 3 invoices; M6 Lab `rootPath /lab`; M6 has Caddy, TLS, launchd; local uses Tailscale Serve; local exposes staff only in LibreChat.
- M6 code is `0d54e9f` (pre-ADA). ADA tools on M6: **Not verified**. The rollout plan says "Never run this on M6".

### 5.8 Frontend surfaces and sign-in

| Surface | URL | Who | Sign-in |
|---|---|---|---|
| LibreChat chat UI | 127.0.0.1:3080 or https://nucleon.tail492813.ts.net (Tailscale Serve); agent "Nucleon ADA Staff (Qwen)" | Admin + members (USER, view-only on the ADA agent, cannot create agents) | LibreChat email/password; members memberN@nucleon.local; tailnet needs a Tailscale share |
| MCP-UI cards in chat | iframes in tool-call panel | Staff | None; MCP uses service session |
| Records web: Requests desk | `#/requests`, `#/requests/thread/<id>`, `#/cases`, `#/case/<id>` | Staff, Owner | Records access code (role from code) |
| Records web: other pages | `#/customers[/<id>]`, `#/completeness`, `#/imports[/<id>]`, `#/knowledge`, `#/setup` | Staff, Owner | Same session |
| Confirmation / evidence page | `#/actions/<act_id>` (actions.js) | Staff person confirm/cancel; Owner cancel; agent/service neither | Same session |
| Owner delegation page | `#/delegation` (delegation.js) | Owner | Records owner code |
| Demo console | `#/console` | Operator | Operator code |
| Lab's own chat page | `/lab/` | Staff, Owner | Records code; NOT built/used locally |

Movement and sign-in:
- The only chat -> Records link is the card button (opens `<recordsPublicUrl>/#/actions/<id>` in a new tab after the allow-list check).
- Two separate logins: LibreChat account, and Records access code per role. The Owner never uses LibreChat locally; no Owner link from chat.
- The card button opened "already signed in as Staff" in the tailnet check; mechanism **Not verified** (likely a shared browser cookie).
- Records cookies are Secure when `publicOrigins` includes the HTTPS tailnet origin. LibreChat `DOMAIN_CLIENT` is left at http://localhost:3080 on purpose.
- Sign-in wording: `core.js:270-295`.

### 5.9 After S3 (31 Oct)
Branch `s3/agent-hardening`. Sections 5.1-5.8 describe the code before S3; where they differ, this subsection wins. Detail: ADA doc section 10, "As built (S3)".
- **Text for the model, full result for the card.** `lab/mcp_server.py` `model_text`: a result with a `forModel` object is given to the model as that object's JSON (plus `hint`); the card is built from the full result as before. A refusal carries `{error, message, hint}`. Other tools unchanged. The decision tools' text fell from about 8-10k characters to at most 600.
- **New read tools** (registry rows `defaultEnabled: False`, in `READ_ONLY`): `whatIsNeeded`, `comparableCases`, `customerStatus` (Staff, Owner); `policyBacktest`, `impactSummary` (Owner only). Pure views in `prototype/agent_views.py`. The tool table in 5.1 gains these five rows (kind read, RO). Enable them with `POST /api/agent-tools` or Setup.
- **Agents.** `agents/instructions_staff.txt` is the single source of the Staff instructions (synced into `update_ada_agent_hints.js`, which also adds `whatIsNeeded` and `customerStatus`; not run). New `seed_owner_agent_3080.js` (not run): "Nucleon ADA Owner (Qwen)", MCP entry `nucleon-local-owner` (same URL as `nucleon-local-staff`, env `NUCLEON_LOCAL_OWNER_MCP_TOKEN`, `chatMenu: false`), ten read tools, no write path. The "instructions in force" quoted in 5.4 stay in force until `update_ada_agent_hints.js` is run. `mcp_check.py` has role rules for the owner token and the S3 tools.
- **Model bench** `tools/modelbench/` (bench.py, test_bench.py, results/): scratch Records and Lab on free ports with per-run tokens, the Lab's real Staff tool list, five prompts, backend-state judging. Results: `docs/research/MODEL-BENCH-20261031.md`.
- **Tool timing log.** Lab config `timingLog` appends one JSON line per call (`tool, role, caseId, start, durationMs, ok, resultChars, forModelChars`); off when unset. S4/S5 read it for the processing-time metric.
- **Tests:** Records 1055 on 3.9 and 3.12 (S3 adds 28: 23 tool tests, 5 instruction and Owner-agent checks), Lab 129, bench 7.
**After S6a (31 Oct 2026, branch `s6/owner-agent`).** The five S3 read tools are `defaultEnabled: True` (decision D14; `decisionStatus` and all act/prepare tools stay off); `workQueue` adds `decisionCasesForYou` / `decisionCasesWaitingOnOthers` (Owner: `awaiting_owner` and `on_hold`, link `#/review`; Staff: `gathering_evidence` with needs and evidence link) and a compact `forModel` (`agent_views.queue_for_model`, at most 600 characters, with the request rows kept); Owner instructions updated (REPORT.md of 31 Oct, five points); re-seeded Owner agent; `deploy/m3-local/tests/accept_owner.py` is the repeatable browser acceptance (5/5 on 31 Oct, three runs, 4/5 before the tool-attribution fix only in its own bookkeeping). Tests: Records 1091, Lab 131.

**After S6b (31 Oct 2026, branch `s6b/one-entry`).** One entry point. LibreChat runs image `librechat:nucleon-card-v0.8.8-rc6-nav` (patch 0006: a "Nucleon" icon in the left rail, `target=_blank rel=noopener`, address from build-time `VITE_NUCLEON_URL`, default `https://nucleon.dracooz.top`); `librechat.yaml` hides presets, prompts, bookmarks, multi-conversation and parameters and sets `interface.customWelcome`. Two LibreChat accounts, `owner@nucleon.local` (author and ACL owner of the Owner agent; the admin stays a viewer) and `staff@nucleon.local`, both role USER: no agent builder, PATCH on any agent returns 403; the Owner account sees both agents (the Staff agent is shared to role USER), Staff sees only the Staff agent. Created by `deploy/m3-local/bin/role-accounts` (passwords only in `config/role-accounts.json`, mode 600); `bin/demo-launcher` shows both with copy buttons. Browser checks: `deploy/m3-local/tests/s6b/`.

---

## 6. Documentation discrepancies found on 30 Oct (Verified)

1. FEATURE-REGISTER early rows F06 / F07 / F11 still say "NOT implemented", though they are built, tested and deployed locally.
2. ENGINEERING-SNAPSHOT upper half and the DECISION-AUTHORITY.md header ("PROPOSAL / OPEN, not implemented") are stale.
3. README and PR docs cite `da95220`; the actually deployed commit is `83b3efb`.
4. KNOWN-LIMITATIONS.md (L-001, L-002) exists only on the code branch, not on the PR #4 branch.
5. POV-VALIDATION-PLAN says localhost is unreachable remotely, but Tailscale Serve is live (tailnet, Staff only).
6. The reliability gate (delegation step 7) is back-tested on `fictional_evaluation` only. This is correct per the design doc, but its PoV implication (real cases do not unlock autonomy) was not stated anywhere.

---

## 7. Operational gotchas (Verified from docs/KNOWN-LIMITATIONS.md and the nucleon-local README)

- **LM Studio idle-unload.** LM Studio idle-unload reloads the model at 8,192 context, which breaks the agent. The model must be loaded with 32,768. `bin/demo-reset` checks this.
- **LibreChat client ban.** LibreChat bans non-browser HTTP clients for 2 hours, including the docker gateway IP.
- **Token budget.** Decision tool results are about 2.5-3k tokens each; budget context accordingly.
- **Separate agents.** The ADA tools and the Phase B `prepareRequest` must live on separate agents; the model mixes them otherwise.
- **LM Studio provider error** (seen 30 Oct in the acceptance round, follow-up turn in a long chat): LibreChat shows "The model provider could not complete this request. Generation predecessor handoff could not be confirmed"; re-sending the message works. Backend state is unaffected. Count it in the model bench (S3).
- **Owner page does not refresh** (`#/delegation`, 30 Oct): no polling; a same-hash `goto` is not a navigation. Fixed in the acceptance script by `reload()`; product fix in S2.
- **Local config after 30 Oct:** `publicOrigins` and `recordsPublicUrl` are back to `http://127.0.0.1:8631` (Tailscale retired). Python/urllib clients cannot use Records while an HTTPS origin makes the cookies `Secure`.

**After S6b (addendum, 31 Oct 2026):** the live `librechat.yaml` also sets `modelSpecs` (one spec, the Staff agent, default for every new chat; `enforce: false`, so the admin can still pick the raw LM Studio endpoint) and `chatMenu: false` on BOTH Nucleon MCP servers, so a plain chat cannot attach the Nucleon tools; verified in the browser for owner@ and staff@ (new chat = Staff agent, no "MCP Servers" button). The Owner reaches the read-only Owner agent via the launcher link or "My Agents".

- **1 Nov 2026, title proxy:** `deploy/m3-local/bin/title-proxy` (stdlib, 127.0.0.1:1235 → LM Studio :1234) pre-fills an empty think block on LibreChat's conversation-title call (0.3 s instead of 6-8 s); `nucleon-local` starts it, `pov-check` checks it, LibreChat's LM Studio baseURL goes through it. Demo access codes fixed (1 Nov); launcher gained a team message and a data-state section; `demo-video-state` points at the public assistant address.
- **1 Nov 2026, customer list:** `findCustomers` with the query `all` or `*` returns every customer by name (up to 25) with a `nextStep` naming the Customers page; both agents can now answer "who are our customers". The Owner agent is viewable by every LibreChat user (role USER) since 1 Nov.
