# Week 7 core flow: hand-over (22-23 October 2026)

## Update, 24 October (evening): replay, balance and stale-instruction round, deployed `0d54e9f`

This section takes precedence over the ones below where they differ. Opus 5.5 primary session with Sonnet implementers in worktrees; every change inspected and integration-tested here. Started from `ac87e27` / `65ccd83`. Deployed `0d54e9f` to both Lab halves at 22:34 AEDT after backups; e2e 6/6; `/` (`f95f50f`) and `/preview/` (`df10ab6`) untouched; branch pushed; nothing merged into main.

1. **Replay association and visibility (fixed, `732165f`).** Cause: `sent_turn` took the first later agent row in the thread, whatever it answered and whoever could see it. Now every agent turn stores the person turn it answers (`turns.reply_to`), a replay returns only that answer and only to a role that may see it, an interrupted turn stays unanswered, a reused turnId with other words, another file or another role is refused (409 `TURN_CONFLICT`), and a store failure after a write says what was done instead of "Try again". Older rows count only when the answer is the very next row with the same visibility. Old build: 10 of 13 `test_replay` and 4 of 5 `test_crash` fail or error on `ac87e27` (the staff resend streamed the owner's tool arguments carrying a synthetic marker); all pass now. Real-process coverage: SIGKILL during a model request and after a records write, restart, the client gone mid-stream, two real connections with one turnId, an AI Agent role switch. Live with the real model: staff reuse of an owner turnId refused with no content, staff history clean, a staff resend replays its own answer with no new rows.
2. **Customer balance (fixed, `4e120d0`, `df2abb8`, `06d559c`, `b28410d`, `da6f501`).** The overview gave the recorded net (VND 222,473,520 for Customer 0012) as the customer balance. Now "owed now" from the same replay as the assessment, with its parts, the credit held, and the recorded net only under its own label where it differs; counts, the invoice table and the case invoice use the same figures; overdue is judged by the original due date (`calc-v1`) and says so where the owner approved a later date. Reconciled on the isolated acceptance copy as of 23 and 24 Oct (validator hand replay and implemented replay agree): Customer 0012 owes VND 272,687,040, all overdue (00000077 VND 172,260,000, 00000081 VND 100,427,040); the opening balance of VND 50,213,520 was paid by the unallocated payment of 26 Sep 2025. Round G's split ("222,473,520 + 50,213,520 opening") and Sequence 7's E-3 answer are corrected in `docs/qa/LAB-CONVERSATIONS.md`.
3. **Stale instructions (fixed, `e0267fa`, `8df738c`).** Each action card reports from the records whether its ask is current, done, ended or another role's; the reply's words then fold under "What the Lab said at the time" behind a "Since this answer: …" line. Covers confirmed decisions, superseded and withdrawn preparations, withdrawn requests, assessments superseded or no longer holding after a records or limits change (new: the case marks a stale assessment and the card drops Act before anyone presses it), and another role's action. Verified live in place, after a reload and in a second tab, with header, sidebar and queue; `lab_check` SN1–SN7 and SN5s.
4. **Demonstration readiness.** The script is seven messages, one Act, one Confirm, one look at the saved basis (`docs/DEMO-SCRIPT.md`). Timed attempts on fresh isolated workspaces: **3:22 and 3:29** (both within the 3:45 target); three attempts failed (stopped, 6:50, 5:57). Keep warm now runs on the server (one warm-up at a time, 30 s after the last ended, none during a chat, a 10-minute lease renewed by the panel), and its line is truthful: ready only after a success within a minute, "slow, not ready" while a warm-up waits more than 5 s, failed with the reason, recovery on the next success; it survives reload, role switch and a closed tab.
5. **Latency cause corrected.** Every slow request on 24 October (afternoon and evening) coincided to the second with a generation by another application on this network that uses the same LM Studio model (a chat front-end; 30–220 s generations every one to four minutes). The earlier "paged out after about 90 s idle" explanation is withdrawn. For the demonstration, nothing else may use the model; that application has to be stopped or pointed elsewhere first (not done here: it is not part of this project).
6. **Remaining notes, not fixed:** the records case page still shows the intake snapshot's "not recorded" for an imported invoice's amount still owed (the Lab case header shows the worked-out amount); a status sentence in an older answer ("Nothing is decided.") stays open when its card had no action; a warm-up already sent when a chat starts is not cancelled; Chrome's background-tab throttling was not reproduced (the warming no longer depends on the tab); same-day invoices are matched oldest-first by id (`calc-v1`); the reply guards do not mark-check VND amounts under 1,000; the earlier notes (repeated facts lines, earlier datasets' import cards re-fetching proposals) stand.
7. **Backups and state.** Before the deploy: `~/srv/nucleon-lab/backups/lab-conversations-20261024-223431-before-replay-round-deploy.sqlite3` (128 turns) and `lab-20261024-223434.sqlite3` (records, 9 requests). Shared Lab: workspace, threads, decisions, the three retained mis-allocations, test history and sessions unchanged except one staff smoke turn (turns 129–130); Keep warm left off. Isolated pair live3 (ports 8955–8958) holds rehearsal 5's workspace; every earlier attempt's stores are kept in the session scratchpad (`round3/backups/`). The old live2 pair was stopped; its databases are kept.
8. **Counts at `0d54e9f`:** records 687, Lab 279, `lab_check` 414/414, `desk_check` 97/97, `ui_check` 150/150, conversations on the mock 540/540; prompts `coordinator-v0.13`, `lab-v0.18`; `calc-v1`. Evidence: `docs/qa/LAB-CONVERSATIONS.md` Sequence 8, `docs/DEPLOYMENT.md` sixth deploy, `docs/DECISIONS.md` E025; ledger `.superpowers/sdd/2026-10-24-replay-round/` (`progress.md`, `evidence.md`, `balance-expectations.md`, the briefs).

## Update, 24 October (afternoon): final repair and acceptance round, deployed `ac87e27`

This section takes precedence over the ones below where they differ. Code: `3abff6b` (interface states follow the records), `8ea5ee2` (truthful recovery, writes keyed by the turn), `a4faa3a` (latency instrumentation, owner-only staff asks without the model), `5f385ae`/`5318e61`/`16d3ac9` (presenter panel: opt-in, fictional only, right-hand column, Keep warm 30 s kept per tab; never presses Send, Act or Confirm), `c167509`, `2b6018c`, `ac87e27` (three guards: owner note read with interpretStatement, ambiguous customer asks which, staff never pointed to a missing Act). Deployed to both Lab halves 17:22 AEDT after backups (`lab-20261024-172218.sqlite3` by the deploy, `lab-conversations-20261024-172217-before-final-round-deploy.sqlite3`); e2e 6/6; root site and preview untouched; branch pushed, nothing merged into main.

- **Latency, measured (explanation withdrawn on 24 October evening: the slow requests were contention with another application using the same model; see the update above):** the 90–200 s turns were the first model request after an idle gap of about 90 s or more; the model (Gemma 4 26B-A4B, about 17 GB, LM Studio) is paged out under memory pressure (swap nearly full) and read back on the next request. A 6.3k-token prompt costs about 6 s on an active model; the 17 tool schemas add nothing measurable. Within 60 s of the previous request a first request costs under half a second. Hence **Keep warm** in the presenter panel (one tiny fictional-only request every 30 s, nothing written) and the rule to quit memory-heavy applications before the demo. No response caching anywhere: every answer is a fresh model result.
- **Acceptance:** about 75 rows on an isolated fresh workspace with the real model, all PASS after the fixes; the defects found and fixed in the round: P-1 panel covered Send, KW-2 Keep warm lost on a role switch, P-2 owner note answered with staff sentences, P-3 ambiguous "customer 001" resolved silently, P-4 staff told to press a missing Act. Evidence: ledger `evidence-final-round.md`; summary in `docs/qa/LAB-CONVERSATIONS.md` Sequence 7.
- **Rehearsals:** two operator-paced runs on fresh workspaces, 4:23 and 4:29 with 10–15 s narration per card; the 3:30–3:45 target needs about a minute less narration or one fewer turn (`docs/DEMO-SCRIPT.md`, Observed timings). No backup recording exists.
- **Shared Lab state after this round:** workspace, threads, decisions and test history retained; three Round G mis-allocations untouched; one new staff turn in the 00000079 thread (the smoke check); sessions kept. Not done, by instruction: no clearing, no allocation repair, no history deletion, no final demonstration state.
- **Counts at `ac87e27`:** records 670, Lab 244, `lab_check` 275/275, `desk_check` 97/97, conversations on the mock 540/540; prompts `coordinator-v0.12`, `lab-v0.17`; `calc-v1`.

## Update, 24 October: finishing phase (calculation details, demo script, briefing, behaviour test)

This section takes precedence over the sections below where they differ. Deliverables: the Calculation details view (application), the executable demo script `docs/DEMO-SCRIPT.md`, the team briefing `docs/reviews/2026-10-24-team-briefing.md`. Evidence: `docs/qa/LAB-CONVERSATIONS.md`, "Overnight finishing phase"; the ledger folder holds `evidence-overnight-finishing.md`, `demo-timing-overnight.md`, `validate-overnight-after-import.md` and `calc-details-report.md`.

### 1. Commits and deployed versions

| Commit | Deployed (AEDT, 24 October) | What it carries |
|---|---|---|
| `0709426` | with 076d324 | Calculation details: `CALCULATION_VERSION = 'calc-v1'`; the replay records its own trail (per invoice issued, per payment: recorded allocations, oldest-first applications, to the opening balance, to customer credit, late marks; remainders, remaining opening balance, credit held; the stated-only, undated, no-due-date, unplaced and unreadable lists with their effects); the assessment stores a `basis` (records included with links, current exposure against strictly-prior history, missing information and assumptions, every policy check with actual value and threshold, the recommendation); a decision freezes the assessment it rested on in `decision.basis`; `GET /api/requests/<id>/basis`; the Lab's closed "Calculation details" section on assessment and decided cards; the records Evidence tab section; prompt lab-v0.15 |
| `8c9724c` | with 076d324 | O1 decided-case questions answered from the decision (outcome, decider, date, "not sent"); first attempt at the ambiguous-case rule; O2 "owed by the customer" wording; the Setup page no longer says imports are not in this version; prompt lab-v0.16 |
| `076d324` | 11:08 | The ambiguous-case check applies to every write outside a case thread whatever requestId the model found (the message must name the case or the customer, or there must be one open case); a date-dependent test fixed. The final code commit |

Documentation commit: the one that carries this file. **Counts at `076d324`:** records 663, Lab 218, `lab_check` 236/236, `desk_check` 96/96, conversations on the mock 540/540. Prompt versions `coordinator-v0.12` (records, unchanged), `lab-v0.16` (Lab); calculation version `calc-v1`.

### 2. Deliverables and locations

- Calculation details: `prototype/behaviour.py` (trail, `calc-v1`), `prototype/server.py` (basis, frozen decision basis, `GET /api/requests/<id>/basis`), `lab/web/src/cards/calc.tsx` (the Lab section), `prototype/web/requests.js` (the Evidence tab section). Staff and the model cannot change the limits: `PUT /api/setup/authority` refuses staff, no tool touches the limits (tests), and a staff request in words is refused live (rows 5-9, and Round G J40).
- Demo script: `docs/DEMO-SCRIPT.md` (exact messages, starting conditions, expected results, the details expansion, recovery path, backup-recording checklist, observed timings).
- Briefing and slide outline: `docs/reviews/2026-10-24-team-briefing.md`.

### 3. Browser-tested scenarios

**What the browser tests covered with the live model (isolated pair, rows 1-1 to 6-2; 61 rows: 57 pass, 3 fail (2-5, 4-13 and 5-6, each fixed and re-tested as 5-1 and 5-10), 1 inconclusive (4-17a, environment)).** Clean start and import (setup, proposal with 57 matches and 3 issued-after references, one Import, duplicate refused, corrected validator 0 discrepancies with the source-data notes separated); the routine Staff journey (open-then-assess in one message with the card filling in place, assessment against the validator's figures, Act within authority, saved decision with actor, role, date, reason and basis, reload, retrieval); the exception and Owner journey (escalation with no Act, concern, role switch keeping the case, two-date compare without preparing, guidance kept with the owner then changed to require staff action with no invented reply, staff reply stored as a reply, approval and a separate decline through Confirm, the two-part reason question, owner-private context confirmed owner-only on the records desk and never surfaced to staff); boundaries (same-day invoices within and above the limit with inclusive exposure and strictly-prior history, a missing due date reported as unknown, changed evidence re-checked at execution, an authority change applied to new assessments only with the decision basis frozen byte for byte, date filters with three, one, no and approved-date matches, ambiguous customer and case references, stale role, role persistence, the switch disabled during an answer, staff and the model unable to change the limits); and the Calculation details compared with hand expectations on Customer 0005 and Customer 0018, in the Lab and on the records Evidence tab.

### 4. Rehearsal timings and recovery path

Observed on the isolated pair (conversation store latencyMs): open request 10–16 s; assessment 14 s, 43 s when the model is cold; concern 11 s; compare 19 s; guidance 3–18 s; staff reply 14 s; prepare decision 16 s; median 13.6 s over 24 turns, longest 44.9 s. The automated run with 30–60 s reading pauses spanned 2.6 min (Journey 1) and 9.8 min (Journey 2). Projection, not a measurement: a presenter typing the scripted messages runs Journey 1 with the details expansion in about 1 min 15 s to 1 min 40 s and Journey 2 without the optional steps in about 2 min 25 s, about four minutes in all; a human-paced timing is still owed before the recording. Recovery path and backup-recording checklist: `docs/DEMO-SCRIPT.md`.

### 5. Remaining defects, limitations, uncompleted checks

- O1, fixed (`8c9724c`; live 5-1 and the deployed smoke test): a staff question about a decided case ("what was decided, who decided it, has anything gone to the customer") was answered with invoice facts; it now answers from the decision and says the reply is a draft, not sent.
- O4, fixed for the action (`8c9724c`, `076d324`; live 5-10): "Decline the QA request" with three QA customers' cases prepared a decline on the thread's focus customer silently; now nothing is prepared and the open cases are listed. Open nit O7: the fallback wording names the focus customer rather than asking "Which case do you mean?".
- O2, fixed (`8c9724c`): "owed to the customer" wording is sent back to the model.
- Open cosmetic: O3 the stale Act card keeps its old Pass lines and buttons under the refusal alert; O5 the "Nothing else overdue" check row shows words instead of "VND 0 overdue besides this invoice" in the Actual cell when nothing else is overdue; O6 a refusal alert shown twice in a decided thread; O8 three retained Round H threads on the shared Lab still read "New request · Preparing" in the sidebar; the Setup page's "Not in this version" sentence (fixed); the duplicate-import card's references line and the two dates it shows (business date and real clock) for one import.
- Environment, not product: the isolated scratch Lab was stopped once by a concurrent scratch run's cleanup (4-17a) and restarted under a different process name; the stale-tab refusal path was therefore re-verified only through its tests and the Round H live check (H18), while the tab's re-read of the shared role on focus was observed live (4-17b).

Limitations unchanged: raw export not importable as exported; netting and adjustment rows left out (customers 0008 and 0017 do not reconcile); no approval predictor and no confidence figure; replies are drafts; no measured time savings. Uncompleted or inconclusive: the stale-tab 409 path was not re-exercised live on the isolated pair (environment stop; verified by tests and Round H H18); the within-authority Act on the demo's routine case was performed on the old build and its basis check on another case (Customer 0005) on the new build; a human-paced timing of the demo; the lab_check E-C check is intermittent (a wait was added).

### 6. Workspace state and restore references

Shared Lab workspace: unchanged in content (Round G/H data, the three historical mis-allocations, the test history); the deploy created records backups and a conversation-store copy named above; the AI Agent login session is signed in. Isolated pair: database and conversation store in the session scratchpad (`live/`), the import copy `overnight-after-import.sqlite3`, the fixtures QA Boundary Iso, QA Small Iso and QA NoDue Iso and the cases of the night. Paused. The later clearing, clean import and the independent acceptance test need a separate instruction.


## Update, 24 October (addendum): the validator's hand replay

Code commit `61ab06b` (validator and its test only; the deployed application stays `a19f3d6`): `deploy/validate_import.py` `hand_replay()` matched payment references without the payment date, so the validator's independent replay could not detect the three allocations that link a payment to a later invoice and agreed with the old importer for the wrong reason. Fixed; self-test regressions with hand-computed expectations (the reproduction, an ordinary match, an unmatched advance kept as credit); the records suite runs the self-test (646 tests). Documentation commits: `a6a46fe` (qa table) and the one that carries this file.

Expected against actual on a fresh isolated database (the cleaned workbook imported through the normal importer at this commit): 21 customers, 137 invoices, 113 payments, 4 opening balances, 57 allocations (the three issued-after references unmatched) as expected; the corrected validator reports 0 discrepancies; Customer 0018: VND 2,538,005,400 owed, VND 2,538,005,400 overdue, opening balance remaining VND 0 (as expected once the mis-allocation is gone); Customer 0019: nothing owed. Remaining: the retained deployed workspace still holds the three allocations (left unchanged on instruction); two pre-existing validator notes (customers 0008 and 0017 do not reconcile by the netting and adjustment rows the importer leaves out). Corrected claims: the Round G "0 discrepancies" reconciliation (J6) and the Round H H5 "replay and hand agree" relied on the old hand replay for the allocation and replay checks; they are qualified in `docs/qa/LAB-CONVERSATIONS.md` and `docs/DEPLOYMENT.md`. Evidence: ledger folder `validate-fresh-a19f3d6.md` and rows I1 to I3.


## Update, 24 October: Round H, one focused repair-and-verification round

Continued from `5282b3d` on the retained Round G workspace. This section takes precedence over the sections below where they differ. Evidence: `docs/qa/LAB-CONVERSATIONS.md`, "Round H" (rows H1 to H18, J37-R). Causes: `docs/DECISIONS.md` E025, "Round H". Breakdown: ledger folder `j37-breakdown-round-h.md`. The workspace and the login session are kept; nothing was cleared, restored or removed.

### Commits

| Commit | AEDT, 24 October | What it carries |
|---|---|---|
| `dc8893f` | 00:24 / 00:25 | G11 `invoices` takes `dueOn`/`issuedOn`, rows say whether the original or the approved due date matched, a filter card and a guard; G9 the selected case survives a role switch; "current" outside a case thread resolves only with exactly one open case and otherwise asks which; G10 first guidance on a case reads "the owner gave guidance", case guidance before any concern is routed to answerConcern with a guard; H1 a payment reference matches only an invoice issued on or before the payment date, `validate_import.py` reports payment-before-invoice allocations; H2 the debt sentence names the remaining part of the opening balance; H3 Lab requests carry the tab's role and a stale tab gets 409 ROLE_CHANGED, a notice and a refreshed header |
| `a19f3d6` | 00:38 | G11 the prose names every date-selected invoice (the one-presentation rule had cut it to two sentences); H5 a saved guidance is never contradicted by a "no guidance saved" fallback; prompt `lab-v0.14`. The final code commit of the round |

Documentation commit: the one that carries this file. Counts at `a19f3d6`: records 645, Lab 209, `lab_check` 224/224, `desk_check` 93/93, conversations on the mock 540/540. Prompt versions `coordinator-v0.12`, `lab-v0.14`.

### Expected against actual

**Remaining live checks (all on the retained workspace, fictional fixtures):** a staff payment BANK-TEST-20261023-STAFF (VND 7,000,000, Customer 0014) recorded and allocated to 00000066 by the AI Agent as staff, the Lab then reporting VND 41,060,000 still owed and the provenance (H1a–c); two fictional customers with invoices issued on the business date 23 Oct 2026: "QA Sameday 20261023" (QS-A VND 1,000,000 and QS-B VND 600,000,000) gave exposure VND 601,000,000 inclusive of today, 0 invoices and VND 0 before today, escalate with no Act (H2); "QA Sameday Small 20261023" (QS-C VND 1,000,000 and QS-D VND 2,000,000) gave VND 3,000,000, every check passing, and staff acted within authority (H3, H3b: decision by the AI Agent as staff, decisionSource staff_within_authority, followed the recommendation); the role switch is disabled while an answer runs (H4a); the historical same-day due dates (Customer 0018, 16 Aug 2026) are a separate retrieval test (H6, H15).

### Findings and their state

- G11, fixed (`dc8893f`, `a19f3d6`; live H6, H7, H8, H15): a question by due date is answered by a deterministic filter on the original and the approved due date; three matches, one match, no match and an approved-date match verified live.
- G9, fixed (`dc8893f`; live H9, H10): the selected case stays after a Staff/Owner switch and the next message is stored in that case thread.
- "current" fallback, verified (`dc8893f`; live H12, H13, H14): with three open cases the owner is asked which (nothing prepared); with one and with none the model resolved the case itself through the case list, so the records-side rule for those two is covered by tests only.
- G10, fixed (`dc8893f`, `a19f3d6`; live H11, H16): an owner's case guidance before any staff concern is stored on the case with the next person set, shown as "Guidance on the case", and the prose agrees with the stored state.
- H1, fixed in the importer and the validator (`dc8893f`; live H5): a 2025 payment of Customer 0018 naming "54" was allocated VND 85,779,000 to invoice 00000054 issued 293 days later; two more allocations link a payment to an invoice issued 1–2 days later. The retained workspace keeps these three allocations until a re-import; the corrected replay for Customer 0018 would show the same total owed (VND 2,538,005,400) with all of it overdue.
- H2, fixed (`dc8893f`; live H17): the debt sentence named the full opening balance as included in the debt; it now names the remaining part.
- H3, fixed (`dc8893f`; live H18): a second tab executed a Lab turn under the role chosen in another tab while still showing the old role; it is now refused with a notice and the header refreshes.
- J37 corrected (H19 / J37-R): the hand expectation was wrong, not the replay; the "all figures matched exactly" claim is withdrawn for the overdue amount.
- Open, cosmetic: the refused stale-tab message is dropped rather than kept for re-sending; the opening-balance sentence repeats the figure; the one-open-case and no-open-case "current" paths were not exercised live by the model.

### Remaining failures and evidence

- Data: the three import allocations that link a payment to a later invoice (Customer 0018 BCV2509028 → 00000054; Customer 0019 BCV2509022 → 84 and BC26000006 → 7) remain in the retained workspace; the fixed importer will not create them on the next import, and `validate_import.py` now reports them (14 discrepancies on the copy, 11 of them the known hand-entered test records).
- Cosmetic: the stale-tab notice drops the typed message; the opening-balance sentence repeats the figure; the duplicate-import references line and the other Round G nits still stand.
- Evidence locations: `docs/qa/LAB-CONVERSATIONS.md` (Round G and Round H tables), the ledger folder `.superpowers/sdd/2026-10-21-week7-core-flow/` (`evidence-journey-round-g.md`, `j37-breakdown-round-h.md`, the live-turn JSON files), Playwright snapshots under `.playwright-mcp/` (not committed), records backups under the Lab's `backups/` folder.

### Pause

Deployed application commit `a19f3d6` (both halves). The workspace, the login session and the evidence are retained. The demonstration state and any clearing for an independent end-to-end test wait for a separate instruction.


## Update, 23 October late evening: cleared workspace and full journey test

The last attribution error was fixed, the fictional data was backed up and cleared through the console, and the whole journey was tested in the deployed browser with the AI Agent login. Faults found on the way were repaired and deployed. This section takes precedence over the sections below where they differ. Evidence: `docs/qa/LAB-CONVERSATIONS.md`, "Round G, 23 October" (rows J1 to J53). Causes: `docs/DECISIONS.md` E025, "Round G". The test state is kept for review; nothing was restored or cleared again.

### 1. Commits

| Commit | AEDT, 23 October | What it carries |
|---|---|---|
| `0a7f612` | 22:21 | Due-date provenance names the actual decider: the owner, staff within the owner's authority, or the AI Agent under its role (the last attribution error from Round F; regression in `test_assessment.py`, `test_agent_account.py`, desk check D16) |
| `7bb2e09` | with 4b1b901 | One selected role shared by the Lab and the records UI for the AI Agent account (cookie `nucleonl_lab_role`, `POST /api/session/role`, a 409 `ROLE_CHANGED` for a marked request); fixes J12, where the records stayed Owner while the Lab showed Staff |
| `4b1b901` | 23:09 / 23:10 | G1 a staff message after any owner answer is a reply, not a concern round; G2 recorded payment terms in the overview; G3 who entered a payment or allocation; G4 `assessRequest` on a case still being prepared answers `CASE_PREPARING` and is not sent in the same turn as `openRequest`; G5 "current" resolves to the customer's one open case outside a case thread, clearer message, recovered tool errors show no alert; G6 the "understood" card with "nothing is recorded until you confirm it"; G8 staff cannot change the limits and the Lab says so. Prompt `lab-v0.12` (verbatim in PROMPTS.md) |
| `5282b3d` | 23:21 / 23:22 | G7 the recorded-reason guard runs after the private-context rewrite, so a quoted reason is kept (regression from the live turn); G4 follow-up: a same-turn assess ends with the request-opened card and one sentence, never a step-limit error. The final code commit of the round |

Documentation commit: the one that carries this file. **Counts at `5282b3d`:** records 638, Lab 198, `lab_check` 218/218, `desk_check` 93/93, conversations on the mock 531/531. Prompt versions `coordinator-v0.12` (records, unchanged) and `lab-v0.12` (Lab).

### 2. Backup, restore and workspace state

**Backups and restore.** Before the clearing: `~/srv/nucleon-lab/backups/lab-20261023-221041.sqlite3` and `lab-20261023-221041-before-journey-test.sqlite3` (records), `lab-conversations-20261023-221041-before-journey-test.sqlite3` (Lab conversations), and the console's own `lab-20261023-221125-before-reset.sqlite3`; the conversation store was retired as `lab-conversations-20261023-221147-retired-before-journey-test.sqlite3`. Each deploy added a records backup (`lab-20261023-222054`, `-230938`, `-232137`). To restore the pre-test state: records through the demo console's Restore from `lab-20261023-221041-before-journey-test.sqlite3`; conversations by stopping the Lab service, copying the retired file back to `data/lab-conversations.sqlite3` and `launchctl kickstart -k gui/$(id -u)/local.nucleon.lab`. No restore was performed; the test state is kept for review.

**Workspace state at the end of the round (kept, not cleared).** "NTK Co (team ledger, journey test)", VND, 0 decimals, Asia/Ho_Chi_Minh; authority 14 days, nothing else overdue, VND 500,000,000, 2 concern rounds. 21 customers, 137 imported invoices plus 00000099 (Customer 0014, VND 12,000,000, no due date, entered by hand), 113 imported payments plus one test payment (BANK-TEST-20261020, Customer 0014, VND 43,200,000, allocated to 00000053), 4 opening balances. Seven requests: 00000087 (Customer 0011) approved by staff within authority to 6 Nov; 00000079 (Customer 0001) approved by the owner to 13 Nov after a concern, an information-only question, two guidance answers and a staff reply; 00000081 (Customer 0012) declined by the owner; 00000099 (Customer 0014), 00000084, 00000082 and 00000073 (Customer 0018) with the owner, 00000084 carrying a concern, a guidance answer and a staff reply. The AI Agent login session and the Playwright evidence are retained.

### 3. Files imported, raw against cleaned, reconciliation

**Files imported.** Raw export `1021/NTK Co 12mon (1).xlsx` (sha256 2f7fc6b7…, sheet "Báo cáo", 537 rows, Vietnamese headings on row 3, grouped by a "Tên KH : <name>" header row per customer) was tried first through the normal card: the first proposal mapped Customer to the group-header column (0 rows); after choosing CUSTOMER NAME in the card's own dropdown and Update proposal it read 21 customers, 137 invoices and 116 payments, but the file carries no credit-term or due-date column and no transaction-type column, so no due dates could be set and three netting rows counted as payments. It was not imported. Supported input: a sheet with one row per transaction, a customer name or code on every row, an invoice number, a document date, debit and credit columns, and either a credit term or a due date; a transaction-type column separates netting and adjustment rows. Hoang's cleaned workbook `NTK Co 12mon - Python cleaned.xlsx` (sha256 1969e373…, sheet "Cleaned Data", 511 rows) was then imported once with one press: 21 customers, 137 invoices, 113 payments, 60 allocations, 4 opening balances as at 2 Sep 2025. `deploy/validate_import.py` on a read-only copy reported 0 discrepancies against the workbook (customers, invoice totals including VAT, dates, payments, allocations, opening balances; corrected 24 Oct: the validator's hand replay then matched references without the payment date, so it could not see the three payment-before-invoice allocations, H1; the corrected validator on a fresh import gives 0 discrepancies with those references unmatched, see the Round H addendum). A repeat import of the same file was recognised as a duplicate (no Import button, no new records).

### 4. Expected against actual

The table in `docs/qa/LAB-CONVERSATIONS.md` ("Round G") has one row per step with the hand-computed expectation, the visible result and the stored state. In short: setup, import, reconciliation and duplicate handling pass; the routine case is approved by staff within authority and recorded as such; the escalation case escalates with no Act button, the concern loop runs through an information-only question (two dates compared, nothing prepared), guidance that keeps the decision with the owner, updated guidance that sends it to staff without inventing a staff reply, the staff follow-up, and the owner's approval through Confirm with the exact reason stored; the decline on a separate case is stored with its reason; staff retrieve both reasons verbatim; nothing of the owner's private words reached staff; one login serves both roles, a refresh keeps the role, no second code is asked, the audit trail names "AI Agent (as staff)" and "AI Agent (as owner)"; the boundary cases (no due date → unknown, escalate, no Act; above the amount limit → escalate; others overdue → escalate) match the hand calculations for the totals and the outcomes (the J37 overdue figure was reconciled in Round H). Reply drafts are shown as "Not sent"; no reply was represented as sent.

### 5. Issues found, with steps

- G1, fixed (`4b1b901`, live J47 and J51): a staff report-back after an owner's guidance was stored as a second concern and counted toward the escalation rounds; it is now a reply.
- G2 and G3, fixed (`4b1b901`, live J50): the overview carries the recorded payment terms and who entered each payment or allocation, so "what terms are recorded" and "who recorded that payment" are answered from the records.
- G4, fixed (`4b1b901` and `5282b3d`, live J49): "open a request … then assess it" in one message produced a raw "Invalid JSON or field format." alert (an internal ValueError on a case still being prepared); the records now answer `CASE_PREPARING`, the Lab does not assess in the same turn, and the turn ends with the request-opened card and one sentence.
- G5, cause found and mitigated (`4b1b901`, live J48): the "current" refusals happened because a role switch returns the view to General (G9), so the message had no case thread; in a case thread "current" works, outside one it now resolves to the customer's one open case, and a refused call followed by a successful retry shows no alert.
- G6, fixed (`4b1b901`, live J43): an owner's "record a private note" produced a bare "I have understood…" with nothing stored and no card; the "understood" card now states that nothing is recorded until the owner confirms it on the records page, with the link, and a guard withholds a reply that omits this.
- G7, fixed (`5282b3d`, live J48): the two-part staff question (exact decline reason + what the owner shared) lost the reason because the private-context rewrite ran after the reason check and merged the sentences; the reason check now runs last and the fallback quotes the recorded reason.
- G8, fixed (`4b1b901`, live J40): staff asking to change the limits were told "I've noted the new limits"; the Lab now answers "Only the owner can change the limits (the Authority panel). Nothing was changed." with no tool call.
- G9, open (UX): switching Acting as returns the Lab view to General without saying so; the composer then posts to General. Work-around: re-open the case thread after a switch.
- G10, open (wording): owner guidance written on a case that has no staff concern is read as a statement to confirm on the records page, not as case guidance; the Lab does not say that case guidance answers a concern. Work-around: answer the staff concern.
- G11, open (model retrieval): a question by due date ("which invoices were due on 16 August 2026") was answered about an unrelated invoice; the all-invoices card on the same turn is right. Work-around: ask by invoice number.
- Cosmetic, open: the duplicate-import card reads "0 of them match … 73 name an invoice not in this file" for a file already imported; the staff answer about an approval names "the owner" rather than the AI Agent account; the first guidance card on a case says "The owner changed the guidance"; the stored intake text of a request typed by staff includes the staff instruction ("Then assess it") around the customer's words, although the case page underlines only the request.

Steps and snapshots for each are in the table rows named above; Playwright snapshots are under `.playwright-mcp/` (not committed).

### 6. Limitations

Demonstration blockers: none, provided the presenter re-opens the case thread after switching Acting as (G9), gives guidance by answering a staff concern (G10) and asks about invoices by number (G11). Proof-of-concept limitations: the model can still answer the wrong record for a question phrased by date; undated invoices cannot be entered by hand (only imports create them), so that rule is covered by tests and the Round F controlled case rather than a live case on this workspace; the "earlier payments arrived while something was overdue" statistic was not hand-verified; the raw accounting export is not importable as exported (no credit terms, grouped layout); earlier limits (no approval predictor, Act and Withdraw as buttons, private-context trimming on the prompt, local-model cold start, hosted APIs untested) still stand.

### 7. Checks not completed

A live re-run of the "current" fallback from General after the fix; a new payment entered after the shared-role fix (only the role indicator was re-checked, J38 and J39); the Lab's behaviour when the role is switched while an answer is running (the switch is disabled then); the same-day boundary through a request (the same-day invoices on this ledger are all covered by credit, so it was checked by a retrieval question that failed for another reason, G11).

### 8. Pause

Deployed application commit `5282b3d` (both halves). The workspace, the login session and the evidence are retained. A second clearing and the final demonstration preparation wait for a separate instruction.


## Update, 23 October evening: retest findings and the AI Agent account

A second retest of `2c30d9f` found five faults, which were repaired, and a testing account for AI agents was added. This section takes precedence over the sections below where they differ. Evidence: `docs/qa/LAB-CONVERSATIONS.md`, "Round F, 23 October". Decision record: `docs/DECISIONS.md` E025, "Round F".

### Deployed commits

- `991cf31`, 20:43 AEDT, 23 October: repair E (findings A to E).
- `196c3ee`, 21:12 AEDT, 23 October: the AI Agent testing account. This is the deployed application commit.
- Both halves each time, records first, `deploy/e2e_lab_check.py` 6/6 each. Root `f95f50f` and preview `df10ab6` untouched.
- Counts at `196c3ee`: records 628, Lab 187, `lab_check` 213/213, `desk_check` 89/89, conversations on the mock 530/530. Prompt versions `coordinator-v0.12`, `lab-v0.11`.

### Scenario results

All twelve live rows pass (none partial).

- Row 14 (B), pass: the case page and Activity name "Staff, within the owner's authority" for a staff decision.
- Row 15 (C), pass: two owner guidance cards read "Followed by a later answer" and "Decided: declined"; no invented staff reply.
- Row 16 (E), pass: the "Request opened" card and the sidebar update by themselves while the request is prepared.
- Row 17 (A), pass: an undated open invoice gives "Overdue not known", an unknown check, escalate and no Act button. The prose still added that staff could press Act within authority, which the card contradicts (see limitations).
- Row 18 (D), pass: a manual amount reads "Entered by staff on Fri 23 Oct 2026 · Not verified".
- Row 19, pass: one login with the agent code gives the AI Agent in the Staff role, a Staff/Owner switch and a Demo console link, with no further codes.
- Row 20, pass: a staff concern on QU-TARGET is stored with actor name "AI Agent" and role staff.
- Row 21, pass: after switching to Owner without a code, the answer asking staff for more information is stored as AI Agent (as owner) and the case goes back to staff.
- Row 22, pass: the Demo console opens without a sign-in and shows the AI Agent identity.
- Row 23, pass: after a refresh the Lab keeps the Owner role.
- Row 24, pass: back in Staff, the sidebar and header show "Waiting on staff" with the owner's question.
- Row 25, pass: the records Activity says "AI Agent (as staff) raised a concern" and "AI Agent (as owner) answered the concern".

### What changed

- An unknown overdue state (an open invoice with no due date) is reported as unknown in the facts and the checks and cannot let staff act; the same for the late-history and amount checks.
- Who decided is read from the decision source, so a staff decision within authority is no longer shown as the owner's.
- An older owner guidance card is described from the records' order of answers, not an invented staff reply.
- A manually entered amount names who entered it and when; imports name the file.
- The "Request opened" card refreshes by itself while the case is prepared.
- The AI Agent account: one code (`accessCodes.agent`, demo instances only, value not recorded), three sessions, the effective role being the role the request names, `actorName` and `actorRole` in the audit trail, a Lab role cookie and switch, and a Demo console link. Role permissions are unchanged.

### Remaining limitations

- The model's prose may still hedge about Act within authority when the card says escalate (seen in row 17); the card and the stored recommendation are right.
- The model may class an owner's reply as guidance or as an information request; the records set the next person either way.
- Analyses stored before `991cf31` keep the older provenance wording.
- The Lab role switcher applies only to the agent identity; ordinary staff and owner codes are unchanged.
- Import batches record "AI Agent" without a role.
- Earlier limits below still stand (dirty-data compatibility, no approval predictor, Act and Withdraw as buttons, private-context trimming on the prompt, cold start, hosted APIs untested).

### Deployed application commit

`196c3ee` (21:12 AEDT, 23 October; both halves, e2e 6/6), the final code commit. The documentation commit is separate and follows this file.

## Update, 23 October: repair round

An independent browser review of the `db86293` build found failures that the first live run had passed. They were repaired and re-checked live as both roles. The product on the Lab is now `eb8eef0`; the main body below describes the build before the repairs, and this section takes precedence where they differ. Evidence table: `docs/qa/LAB-CONVERSATIONS.md`, "Repair round, 23 October". Decision record: `docs/DECISIONS.md` E025.

### Actual causes (evidence vs hypothesis)

- **F1, same-day entries missing from the assessment.** Evidence: on a read-only copy, two QA invoices issued 2026-10-23 were stored, and both assessments (as of the same day) showed no prior invoices, no debt, and the outstanding-amount check passing on VND 0. The replay selected records strictly before the as-of date, so same-day records never reached the facts, and the "incomplete" rule did not fire because the invoices were filtered out before it looked. Hypothesis ruled out: identity resolution (the request carried the right invoice id).
- **F2, invoice facts confused.** Evidence: the model's invoice rows carried only a still-owed text. Invoice 59 read "VND 0 (at most)" and "no matched payment was found", an invention from an absence; invoice 00000087 had no total in the rows. Role filtering was not a cause.
- **F3, every answer kind moved the case to staff.** Evidence: the code set the staff hold for all kinds, so guidance that kept the decision sent the case to staff while the prose said it waited for the owner.
- **F4, the recorded decision reason hidden from staff.** Evidence: the reply fell back to a generic line because the model's quotation of the reason was withheld as a judgement claim. Hypothesis not borne out: the case details already carried the reason for both roles on a decided case.
- **F5, smaller faults.** An internal instruction shown as the error text of a failed customer switch; a static "Request opened" card taken before the case settled; one date compared where two were asked. A later live check added a sixth: a withheld due-date answer hid facts the tool had returned.

### Why the previous verification missed them

- Fixtures predated the as-of date, and the live routine case (0011) was an imported invoice issued on 30 September, so the same-day boundary was never exercised.
- Live checks looked at status words and card presence, not every requested fact in the prose; "settled" was accepted for invoice 59 without the original amount and the matched payment.
- Guidance was covered only by a mock scenario written from the implementation, and the live concern-loop test used `needs_info` only.
- Nothing compared the prose with the records for the same question across layers.

### What changed in the product and in verification

- Product: current facts read up to and including the as-of date while history stays before it; every invoice row carries original amount, still owed with its basis, and allocations with payment references; the caller sets who acts next after an owner's answer; one decision view with the recorded reason, quoted verbatim; customers resolved by name or code; a live "Request opened" card; two-date comparison; original against moved due date; withheld replies fall back to facts built from the records. Prompt versions `coordinator-v0.12`, `lab-v0.10`.
- Verification: independent fixtures with hand-computed facts including same-day entries; a fail-then-pass regression for each cause; scenario assertions on every requested fact; responsibility checks in both roles; and an evidence table with expected, visible, stored and pass columns.

### Deployed workflows checked as both roles

Invoice 59 (original amount, payment BCV2509033, still owed 0) and 00000087 (original amount, no payments, still owed not recorded); a switch to customer 0004 by name (invoice 70); two same-day invoices for a fictional QA customer assessed on current facts and escalated over the VND 500,000,000 limit; a staff concern leaving the case with the owner; two dates compared with nothing prepared; owner guidance that keeps the decision (with the owner) and guidance that needs a staff action (back with staff), with staff seeing both owner answers and no owner-only text; the live "Request opened" card; the recorded decision reason quoted to staff; the original and moved due dates of 00000087. 13 checks pass at `eb8eef0`; none fails.

### Remaining failures and limitations

- The same-day boundary is handled. Broad dirty-data compatibility (other files, odd dates, unusual references) remains a documented limitation.
- No approval predictor; it would need validated decision records.
- Act and Withdraw are buttons a person presses; that is the current execution mode, not the aim.
- Private-context trimming of an owner's answer to staff rests on the prompt.
- The model sometimes labels an information request as guidance, or the reverse; the next person is set by the records' rule, so the state is right either way.
- Hosted APIs are untested. Local-model cold start can exceed the run limit on the first call after idle.

### Deployed application commit

Repair D (`2c30d9f`, both halves, 17:59 AEDT 23 October) closes the second false-authorisation path: active records without an issue date now count for exposure and overdue; records the replay cannot place make the assessment incomplete and escalate. Verified live: the reviewer's controlled case gives VND 601,000,000 owed, VND 600,000,000 overdue 22 days, both checks failing, escalate, no Act button. The deployed application was `2c30d9f` at that point; it is now `196c3ee` (see the evening update above); the documentation commit follows this file.


After the repair round a boundary review of its commits found one important guard weakness (an unquoted restatement of a recorded line passed the claim check); `0711955` fixes it and is the deployed Lab half (records half `eb8eef0`, unchanged). The documentation commit follows this file.

### Earlier line

`eb8eef0` (23 October: `1720b0d` 15:09, `08b0a07` 15:27, `eb8eef0` 15:36 AEDT; both halves, e2e 6/6 each; root `f95f50f` and preview `df10ab6` untouched). Counts: records 606, Lab 177, `lab_check` 185/185, `desk_check` 78/78, conversations on the mock 522/522 (51 live-only skipped). Documentation commits are separate and follow it.

---

For the Nucleon team. Branch `explore/agent-coordinator-20261019`, not merged into main. The root records site (`f95f50f`) and the comparison preview (`df10ab6`) are unchanged. Prompt versions: records `coordinator-v0.10`, Lab `lab-v0.7` (both verbatim in `PROMPTS.md`). Decisions and evidence: `docs/DECISIONS.md` E025, `docs/DEPLOYMENT.md` "Fourth deploy", `docs/qa/LAB-CONVERSATIONS.md`.

## What works end to end

Checked in the deployed Lab with the local Gemma model, as owner and as staff, against the records.

1. **Import.** Staff attach the ledger in the Lab chat, read the card (money unit, payment references, rows left out) and press Import once. A file in a different currency from the workspace is refused.
2. **Retrieval.** A customer by its original code, an invoice's customer and status, an honest "no customer by that name", and a correction of the customer mid-conversation.
3. **A new request is understood and assessed.** Staff quote the customer; the case opens on the right invoice; the assessment card shows facts, each of the owner's limits as pass or fail, and a recommendation derived from those checks.
4. **Routine case.** Within the owner's limits, staff press Act within authority (two steps); the decision records `staff_within_authority` and that it followed the recommendation.
5. **Escalation case.** Outside the limits, the case goes to the owner. Staff can raise a concern; the owner can ask staff for more information; both roles then see "Waiting on staff"; staff reply; the owner approves with a reason, revises, withdraws without declining, and confirms. The decision records the owner as the source and the reason.
6. **Everything survives a reload**, and the Lab's header says who decided and whether the recommendation was followed.

## The numerical/model capability delivered

Numbers come from a fixed, tested replay of the ledger by code (what is overdue and for how long, earlier receipts made while something was overdue, relationship length, in Hoang's feature names) checked against limits the owner sets. The product shows the capability line "Numerical analysis of the ledger and the owner's policy checks; no approval predictor." No probability, confidence or percentage appears anywhere. Where no amount still owed is recorded, it says "overdue not known", never "none overdue". The language model only reads and explains; it cannot change a number or a limit. Validated on the real ledger: `deploy/validate_import.py` passes customers, invoices (including VAT sums and dates), payments, allocations, openings and positions, and the replay agrees with an independent hand computation.

## Material features changed or removed

Added: the owner's answer to a staff concern (`needs_info`, `explain`, `guidance`) which sets the status and the next person; staff replies, stored apart from concern rounds; `withdrawRequest`, pressed by a person only; an opening-balance batch in the importer; normalised invoice references with reasons for unmatched payments; replay fixes (recorded allocations reserved first, prepayments and opening credits carried forward, same-day lateness judged once); credits shown as customer credit; a still-owed header for requests analysed after the deploy; the capability line; the **New workspace** button in the demo console; the Authority panel and the decision fields from earlier in the week.
Removed: the model's ability to record a staff decision (Act within authority is a button only); the model's ability to open a request inside a case; "0 overdue" where the figure is unknown; the old "No approval model runs here." heading.

## Data reset/import outcome

On 22 October, 23:42-23:46 AEDT, after backups, a person pressed **New workspace**; the owner set VND, 0 decimals, time zone Asia/Ho_Chi_Minh (the team should confirm the zone) and the business name "NTK Co (team ledger, demo)", and the authority limits (staff up to 14 days, only when nothing else is overdue, up to VND 500,000,000 outstanding, 2 concern rounds). The Lab's old conversations were retired to a backup (restore steps in `docs/DEPLOYMENT.md`). At 00:27 on 23 October staff pressed Import once: 21 customers, 137 invoices, 113 payments, 60 allocations, 4 opening balances as at 2 September 2025 (the file states no date). 60 of 113 payments matched by their references; 13 name an invoice that is not in the file; 40 have no reference. Three netting or adjustment rows and two negative reversals were left out and flagged. Two customers reconcile only up to an unapplied credit (a payment with no invoice; an overpayment), reported as notes.

## What I personally tested on the deployed site

On 23 October between 00:28 and 01:22 AEDT, in both roles, cross-checked against the records: retrieval (customer 0014, invoice 59, an unknown name, a correction to 0004); a routine case (0011, invoice 00000087, asked for 10 November) acted on by staff within authority; an escalation case (0001, invoice 00000079, asked for 15 November, 34 days against a 14 day limit) through concern, question, reply, approval, revision, withdrawal and a confirmed version 3. A stray request opened by the model was found and withdrawn through the new header button. On 22 October I also tested the first live night (thirteen findings, fixed). Screenshots `live-01` to `live-08` are under `.playwright-mcp/week7/` (local, not committed).

## Remaining failures or dependencies

- Trimming the owner's private context out of an answer to staff rests on the prompt; the tool checks only that the text appears in the owner's message.
- Minor, not fixed: a past `until` date is accepted; the opening as-at date changes if a longer ledger is re-imported; invoice reference "1.05" can match "1.5"; recorded allocations above a payment are not capped.
- A bare day of the month ("the 15th") is not resolved; the assistant asks for the full date. A reason must be in the current message or an earlier preparation.
- The local model's first call after idle can time out; the retry works. Hosted APIs are untested.
- No approval predictor. It depends on validated decision records; collecting decisions alone does not validate one.
- Act and Withdraw are buttons a person presses. That is the current execution mode; automatic action within the owner's authority is the intended product. Tool availability to the model, preparation and execution are kept as separate things.

## Deployed application commit

Superseded: the deployed application is now `196c3ee` (see "Update, 23 October evening" at the top). The text below records the commit at the time of the repair round.

`eb8eef0` (15:36 AEDT, 23 October; both halves, records first; `deploy/e2e_lab_check.py` 6/6), the final code commit of the repair round. Earlier deploys of the round: `1720b0d` 15:09 and `08b0a07` 15:27. Before the round the Lab ran `db86293` (01:21 AEDT, 23 October). Counts at `eb8eef0`: records 606, Lab 177, `lab_check` 185/185, `desk_check` 78/78, conversations on the mock 522/522 (51 live-only skipped). Prompt versions `coordinator-v0.12`, `lab-v0.10`. Documentation commits are separate and made later: the documentation commit that follows this file.

## One short realistic workflow for the team to try

1. Staff, in the Lab: quote a customer's call about an open invoice that is not yet due, asking for a date within two weeks (the demo night already decided 0011's invoice 00000087, so pick another from the Customers page). The case opens.
2. Staff: "Check the numbers." Read the assessment card, then press Act within authority and confirm.
3. Staff: open a second request that asks for a much later date (for example 34 days). The assessment says escalate. Raise a concern in words.
4. Owner: ask staff whether the customer can pay part now. Both roles see "Waiting on staff". Staff reply.
5. Owner: "Approve the 15th because ..." and press Confirm. Reload and read the header: who decided, the reason, and whether the recommendation was followed.
