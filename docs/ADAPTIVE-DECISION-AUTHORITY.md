# Adaptive Decision Authority — first vertical slice

Status: **architecture for implementation** (2026-10-26), on branch `feat/adaptive-decision-authority-20261026` (from Phase B `f4febc2`).
Product direction: [memory/DECISION-AUTHORITY.md](memory/DECISION-AUTHORITY.md), PM-001 and PM-008 to PM-015 in [memory/DECISION-REGISTER.md](memory/DECISION-REGISTER.md).
All numbers in this document and in the demonstration data are **fictional POC values**, not real NTK thresholds or measured accuracy.

## 1. What changes

Until now, a credit request was decided by the Owner, or by Staff acting within limits (`actWithinAuthority`). The new mechanism is different:

- **The Owner delegates:** a versioned *delegation policy*.
- **The agent decides:** the AI assistant decides internal credit requests within that policy.
- **The backend authorises:** it checks every bound and, when they all hold, records the decision as effective at once. No Staff or Owner click is needed per case.
- **Outside the policy:** when information is missing, the agent asks Staff for it. When a request is outside the policy, the agent sends the Owner an evidence-backed recommendation.

The model **recommends and explains**. Code decides whether the recommendation may take effect. The model cannot change the policy, widen it, or bypass a check.

### Unchanged
- **Phase B:** `prepareRequest`, the confirm page, the Owner-only review of confirmed requests (`OWNER_REVIEW_REQUIRED`) and `actWithinAuthority`.
- **Financial integrity:** completeness, balance provenance, idempotency (`record_ops`), action status and recovery, and the cards.

The delegated path is a **separate, explicit capability**. It does not quietly disable an existing guard.

## 2. Three separate dimensions (never one score)

| Dimension | Question | Computed from | Never from |
|---|---|---|---|
| **Evidence sufficiency** | Do we know enough, and is it verified? | Records (completeness, receipts, due dates), and facts Staff confirmed on a Nucleon page | The model's statement that something is verified |
| **Business risk** | Is this within what the Owner delegated? | Exposure (this decision, the customer's total, the rolling autonomous total), days, overdue, late history, unusual size, restrictions | Model confidence |
| **Demonstrated reliability** | Has this scope been shown to match the Owner's decisions? | The current policy back-tested on the **held-out evaluation set** of reviewed cases (fictional in the POC), plus live Owner-reviewed cases | The LLM rating itself |

Each dimension returns a status and its own reasons. The evaluation shows all three side by side.

## 3. Owner delegation policy (versioned, Owner-only)

**Storage.** Policies are stored append-only in table `delegation_policies(version INTEGER PRIMARY KEY, created_at, data)`.
- Every change is a new version, including pause and resume.
- `data` holds the policy plus `createdBy` (the Owner's trail) and an optional `note`.
- With no row, the effective policy is **version 0**: advisory mode with everything off, so nothing executes.

```
mode: 'advisory' | 'delegated'          # advisory: the agent only recommends; delegated: it may decide within the bounds below
paused: bool                            # the Owner's pause switch; paused => nothing executes
limits:
  maxDecisionExposure: money            # exposure added or extended by one decision
  maxCustomerExposure: money            # the customer's total exposure after the decision (known, never assumed 0)
  maxAutonomousExposure30d: money|null  # all autonomous approvals of the last 30 days that are still in force, plus this one
extensions:
  enabled: bool
  maxDays: int                          # days past the invoice's current due date
  requireNothingElseOverdue: bool
  maxPriorLateShare: fraction|null      # exact fraction, as in behaviour.checks_for
newCustomers:
  trialCredit: 'off' | 'limited'        # off: a first-credit request goes to the Owner (with a recommendation)
  maxExposure: money                    # order amount minus the verified deposit
  minDepositShare: fraction             # verified deposit / order amount
  maxTermsDays: int
  tradeReferenceAbove: money|null       # proportional evidence: a trade reference is needed only above this exposure
  staffCheckedDepositUpTo: money|null   # a deposit Staff only CHECKED (bank or document, not a recorded payment) counts when the exposure is at most this; null: only a recorded payment counts (the default)
evidence:
  confirmedCoverageAbove: money|null    # proportional: confirmed record coverage is needed only above this exposure
restrictions:
  holdCustomers: [customerId]           # policy hold: never decided by the agent; the Owner may grant an exception
  unusualSizeMultiple: number|null      # an amount above N x the customer's median earlier invoice is flagged for the Owner
trackRecord:
  minReviewedCases: int|null            # evaluation cases this policy would auto-approve in the category
  minAgreement: fraction|null           # share of those cases the Owner also approved
```

**Validation and writes.**
- **Strict:** an unknown key is 400, so there is no `allowExternalMessages` or `autoDecline`.
- **Money:** amounts must be in the workspace currency.
- **Who can write:** only an **Owner person session**. The guards are the same as Phase B confirm: `person_required` (no service session, no AI-Agent identity), CSRF and Origin.
- **Version check:** a write names `expectedVersion`. A stale one is 409 `POLICY_CHANGED`.
- **No agent path:** no MCP or desk tool writes the policy.

**Not implemented, documented blockers.**
- **Autonomous decline:** the agent never declines on its own authority (open product question, DECISION-AUTHORITY Q5). A request that fails goes to the Owner, or onto a policy hold that the Owner resolves.
- **External communication:** nothing is sent outside Nucleon, and the policy has no setting to allow it.

## 4. Request kinds in this slice

1. **`extension`.**
   - **The request:** a later due date for one open invoice of a customer.
   - **Exposure:** the invoice's amount still owed, which must be known.
   - **Days:** counted from the invoice's current due date.
   - **Customers with no payment history:** a customer with no earlier receipts falls under the `newCustomers` bounds; with trial credit off, the request goes to the Owner.
2. **`trial_credit`.**
   - **The request:** first credit for a customer with little or no history, as an order amount on `termsDays` terms with a deposit.
   - **Exposure:** order amount minus the **verified** deposit.
   - **Effect:** an internal approval (a trial credit line). No order is fulfilled and no message is sent.

## 5. Evidence: what counts as verified

| Item | Verified by | Needed when |
|---|---|---|
| `records_complete` | Records: no unreadable amount, missing due date or unplaced payment for the customer | always (a data defect means insufficient, never a decline) |
| `coverage_confirmed` | Records coverage attestation | exposure > `evidence.confirmedCoverageAbove` |
| `deposit` | **By level** (below): a recorded payment in Records (an active, unallocated receipt, received at most 30 days before as-of), or a deposit Staff checked in the bank / on a document and the exposure is within `staffCheckedDepositUpTo`. Amount ≥ the required share | trial credit |
| `business_identity` | Staff confirmed it on the evidence page (registration, trading name) **with a basis**: `registry` lookup or `document` seen; kept as a customer-level confirmed fact for 365 days. A fact with no basis does not count | trial credit |
| `trade_reference` | Staff confirmed it on the evidence page | trial exposure > `tradeReferenceAbove` |

**Deposit levels.** Every deposit source carries a level, shown in words wherever the deposit is shown (evidence item, Key Facts `verifiedDeposit` + `depositSources`, the card, the Owner page, the case view), e.g. "AUD 150.00 — checked by Staff in the bank account (not a recorded payment)".
- **`recorded_payment`:** an active unallocated receipt in Records (the ledger). Always counts.
- **`staff_checked_bank`, `staff_checked_document`:** Staff saw the money arrive, or a receipt or remittance document. Staff-verified, **not a ledger payment** (confirming one never creates or changes a payment). It counts only when the decision's exposure, with it counted, is at most `staffCheckedDepositUpTo`. With a null limit, or above it, the item is `missing` with the need "record the payment in Nucleon Records", which Staff can do; recording it and asking again re-evaluates the case.
- **`staff_assertion`** (basis `customer_statement`: the customer said they paid; also any earlier fact that kept no basis): stored and shown as "reported by the customer, not verified". Never counts.
- A deposit given for an approved trial credit is not given again for the next one, and a receipt that is a deposit does not also pay down the customer's debt in the exposure total.

**What isn't verification.** The assistant may pass along context Staff gave in the chat (`context`). It is stored as *"reported in chat, relayed by the assistant"* and **never counts as verification**.

**Contradictions.** A confirmed fact that conflicts with the records makes the evidence **contradictory**, and the request goes on a policy hold. Examples:
- a deposit confirmed with an amount different from a recorded receipt with the same reference;
- "no earlier account" confirmed while invoices exist.

**No history.** A missing history is `none`, not incomplete and not negative.

**Facts Staff confirmed** are stored in `confirmed_facts(id PK, customer_id, kind, created_at, data)` with their provenance: the person session, the action id and the time.

## 6. Evaluation and handling (pure code, `prototype/delegation.py`)

`evaluate(...)` returns:
- `keyFacts`, `evidence`, `risk`, `reliability`, `comparables`;
- `handling`, `reasons`, `authority {source:'owner_delegation_policy', version, mode, paused}`;
- `recommendation` (the model's own, labelled as such).

Handling, in order:

1. Restricted customer, or contradictory evidence → **`policy_hold`**.
2. Risk outside the policy (any limit fails) → **`owner_review`**, with the missing evidence listed for the Owner.
3. Evidence Staff can provide is missing → **`request_evidence`**. An evidence action is created and the card links to the Nucleon page. This happens even in advisory mode, because it saves the Owner a round trip.
4. Evidence insufficient and not obtainable from Staff (data defects) → **`owner_review`**.
5. Risk unknown (an amount or state the records can't establish) → **`owner_review`**.
6. Most of the closest comparable reviewed cases were declined by the Owner → **`owner_review`**.
7. Track record required but not established for the category → **`owner_review`**.
8. Advisory mode, paused, or the category off (`extensions.enabled` false, `trialCredit` 'off') → **`owner_review`**. Since 31 Oct 2026 this step is checked **before** 6 and 7: an explicit Owner setting is the deciding reason whenever it applies (with live verdicts pooled into the track record, an override during a paused policy otherwise read as "track record not established").
9. The model's recommendation isn't `approve` (it may always choose to escalate) → **`owner_review`**.
10. Otherwise → **`autonomous_approve`**: the backend records the effective internal decision.

Rules that hold throughout:
- **Unknown is never zero:** a value that can't be established never passes.
- **No permanent denial by the agent:** a hold is not a decline.
- **Current policy:** the evaluation always uses the current policy at execution time. If the caller names a `policyVersion` that is no longer current, the result says `policyChangedSinceAssessment: true`, and the decision records the version actually applied.

## 7. Decision memory (`decision_cases`)

**Table.** `decision_cases(id PK, kind, subject, status, dataset, created_at, updated_at, data)`, plus a unique index for **one live case per (kind, subject)** WHERE status IN ('gathering_evidence', 'awaiting_owner', 'on_hold').
- **subject:** the invoiceId for an extension, the customerId for trial credit.
- **dataset:** `live` | `fictional_example` | `fictional_evaluation`.
- **status:** `gathering_evidence` | `awaiting_owner` | `on_hold` | `decided` | `closed`.

**What `data` holds:**
- the request parameters;
- the frozen evaluation (all three dimensions and the comparables, with their ids);
- the AI recommendation and reasoning;
- the actor provenance (role, actor id, session channel service or person, via MCP or desk);
- the policy version and its digest;
- the decision, with `by`: agent, owner, or owner exception;
- `authoritySource`: `owner_delegation_policy` vN, or `owner`;
- the evidence items with their verification;
- Owner feedback and override;
- the outcome.

**How it links to requests.**
- **Extension decided by the agent:** the decision is **also** a request record (`new_request` with intake channel `delegated_agent` and `structured`, the case built by `structured_case`, no model run). `r['decision']` carries `decisionSource: 'delegated_policy'`, `authority`, `policyVersion` and `delegationCaseId`. The existing effective-due-date code (`App.evidence`) moves the invoice's current due date with no new code.
- **Extension escalated:** the request waits for the Owner (`awaiting_owner`, Owner-only as a structured request). When the Owner decides it (`App.decide`), the linked case is updated in the same transaction.
- **Trial credit:** lives in the case only. The Owner decides an escalated or held one with `POST /api/decision-cases/<id>/decide`.

**Comparable cases.** Retrieval is deterministic and weighted over:
- kind, and whether the customer is new;
- exposure (log ratio), days or terms;
- deposit share, earlier late share, and anything else overdue.

It searches the `fictional_example` and `live` datasets **only**. The evaluation set is held out from retrieval. Every result says whether it is another customer's case: *"analogy, not this customer's history"*.

**Track record.** The current policy is back-tested on `fictional_evaluation` (plus live Owner-reviewed cases, reported separately). Among the cases the policy would approve, it reports:
- how many the Owner approved;
- how many the Owner declined (false approvals);
- the repayment outcomes.

Each figure carries its sample size and the dataset label.

**Outcome.**
- **Live cases:** read from the records (paid, open and not yet due, open and past the approved date, or unknown).
- **Fictional cases:** the stored labels.

**Owner feedback** (`POST /api/decision-cases/<id>/feedback`, Owner person session) records:
- a verdict, `agree` or `disagree`, with a reason, and the case `version` the Owner saw (another is 409 `STALE_CASE`, nothing changes);
- an optional **override**. For an agent's extension approval, the request decision is replaced by the Owner's decline, the earlier decision is kept in `decisionHistory`, the event is `decision.overridden`, and the effective due date reverts. For trial credit, the line is revoked.

**Policy suggestions** are deterministic and only ever suggestions. For example: reviewed cases just above a cap that the Owner approved and that were repaid, with no Owner decline or default in that band. Each suggestion names its evidence and the dataset. Applying one means the Owner saves a new policy version. Nothing is relaxed automatically, and restrictions are never suggested away.

## 8. Interfaces

**HTTP (Records).**
- **Policy:** `GET/PUT /api/delegation/policy`, and `POST /api/delegation/policy/pause|resume`. Writes are for an Owner person; Staff can read the current version.
- **Owner reads:** `GET /api/delegation/policy/history`, `/api/delegation/cases`, `/api/delegation/suggestions` and `/api/delegation/stats` (live cases only, with denominator and timeframe).
- **Cases:** `GET /api/decision-cases/<id>`, then `POST .../decide` and `.../feedback` for an Owner person.
- **Evidence:** `POST /api/actions/<id>/evidence` {version, items}, for a Staff person, with CSRF and Origin. The action has kind `evidence` and the existing `act_<16 hex>` id. Submitting it records the facts, executes the action and re-evaluates the case at once under the current policy.

**Tools for the Staff agent** (MCP via the Lab; off by default, enabled by the Owner under `agentTools` like Phase B):
- **`assessDecision`** (read, stores nothing): what would happen now, with Key Facts.
- **`resolveDecision`** (act): the agent's recommendation and reasoning go in, and the backend applies the handling. A duplicate (the same live case, or the same decided request) returns the stored case with `replayed: true`.
- **`decisionStatus`** (read): the **authoritative** status of a case.

The Owner agent gets `decisionStatus` only.

**Cards (MCP-UI, `lab/card.py`).**
- **Key Facts:** original due date, as-of date, requested date, extension days, days overdue now, and warnings. These are the backend's dates, laid out as rows in date order with a bar showing where each date falls, so labels never overlap. Trial credit shows order amount, verified deposit, exposure and terms.
- **Status badge:** wording from the backend's status only.
- **The three dimensions,** and comparables labelled as analogies.
- **One button,** for `request_evidence` only: "Provide information in Nucleon", which opens the evidence page. The link is accepted by LibreChat rc3's existing allowlist, so **no LibreChat change** is needed.

**Pages (Records web).**
- **`#/delegation` (Owner):** the minimal policy form (basic, plus advanced folded), version history, pause and resume, cases awaiting the Owner, recent autonomous decisions with feedback and override, suggestions, and small live counts.
- **`#/actions/<id>` for kind evidence (Staff):** "You are confirming facts, not approving credit".

The old console is not extended.

## 9. Safety properties (tested)

- Version 0 and advisory mode never execute. Paused never executes. Nothing outside every bound executes.
- Duplicate and concurrent calls create one case and one decision (the `App.lock`, the unique index, and replay).
- A policy change between assessment and execution applies the current version.
- A Staff person, a service session or the AI-Agent identity changing the policy → 403. No tool reaches it.
- Model text never sets a status. Tool results and cards carry the backend status, and the card's badge reads it.
- Internal decision ≠ external communication. A result always says `communication: not sent; Staff informs the customer`.
- Phase B workflow unchanged (existing tests, plus a regression test).

## 10. As built (2026-10-26, commit `4a33b74` and later on this branch)

**Code.**
- **Rules:** `prototype/delegation.py` holds the pure rules.
- **App integration:** in `prototype/server.py`, the App "adaptive decision authority" block, the three `DeskTools` tools and the HTTP routes.
- **Demo data:** `prototype/delegation_demo.py` is the seed and CLI; `prototype/samples/decision_memory_fictional.json` holds the fictional cases.
- **Pages:** `prototype/web/delegation.js` is the Owner page `#/delegation`; `prototype/web/actions.js` has the evidence page for kind `evidence`.
- **Lab:** `lab/card.py` has `decision_card_html` (status badge, Key Facts, the three dimensions, comparables, authority line); `lab/mcp_server.py` exposes the tools.
- **Tests:** `prototype/test_delegation.py`, `lab/tests/test_decision_card.py`, and the headless page check `deploy/delegation_page_check.py`.

**Behaviour that differs from, or adds to, sections 1–9.**
- **Reset.** `delegation_policies`, `decision_cases` and `confirmed_facts` are in `DATA_TABLES`.
  - A demo reset or start-empty deletes them with the other data, so a practice workspace returns to policy version 0 (advisory, nothing executes) with no decision memory.
  - A restore brings back whatever the backup held.
- **Policy save.** It is `PUT /api/delegation/policy` only; a `POST` there is 405.
  - A PUT that doesn't mention `paused` keeps the current pause.
  - A key left out takes its version-0 value, never a wider one: late share 0, deposit share 1, and a track record of 5 cases at 0.8 required.
  - Exception (S1b, until S2 adds the controls): a body that leaves out `feedback.tacitAgreeAfterDays` or `trackRecord.sources` keeps the CURRENT version's value for exactly these two (an explicit value, `null` included, wins). Implemented in the save path (`App.save_policy`), not in `validate_policy`.
  - The Owner form shows shares as percentages and converts them to exact decimal text; no floats are involved.
- **Back-test.** `delegation.backtest` judges the policy's bounds (restrictions, limits, deposit share, evidence), not its switches. Advisory, pause and category on/off are judged at step 8 of `evaluate`, so an advisory policy still shows the track record its bounds would have had.
- **Evidence actions** exist for trial credit only. For an extension, nothing is obtainable from Staff, because coverage confirmation is the Owner's. `confirm` and `cancel` refuse an evidence action (409 `WRONG_ACTION_KIND`).
- **Replay.**
  - **Asked in days:** an extension is replayed, not made again, when the agent approved the same days within the last 24 hours and that approval is still the invoice's current due date.
  - **Asked by date:** it is replayed whenever the agent's approval for that date still stands.
  - **Override:** an override ends the replay.
- **Assessment preview.** `assessDecision` stores nothing. Its card reads "WOULD BE … — PREVIEW, NOT DECIDED". Without a recommendation it assumes `approve` and says so (`assumedRecommendation`).
- **Owner reasons.** The Owner's reasons on comparable cases are not shown to Staff, in the card or the HTTP view.

**Fixes from the first end-to-end round.**
- **One trial credit line at a time.** While a customer has an approved trial credit in force (agent or Owner, not overridden, not past its due date), the same terms replay the stored decided case (`replayed: true`) and other terms go to the Owner (risk check `trial_in_force`, also shown by `assessDecision`). After an override or the due date, a new request is evaluated normally.
- **Provenance.** The agent's own decisions carry `decidedBy: 'nucleon_agent'`, `decidedByKind: 'agent'` and `requestedBy {actorId, role, channel}` (the session that asked). No `actorRole`: nothing reads it as a Staff approval.
- **`decisionStatus`** takes exactly one of `caseId`, `actionId`, `requestId`, `customerId` (the last with an optional `kind`; it returns the latest live case, else the latest, with up to 5 recent cases).
- **Status wording.** `evaluate` returns `why`, the deciding reason as one sentence; `statusText` and the card's "Why:" line use it. A case gathering evidence reads "Approved under Owner policy vN only if the information confirms it; otherwise the Owner decides".
- **Payments with no received date** no longer break `customerOverview` or the allocation lines.

### Safety verification (Stage 1)

Three areas were checked against the code with new tests, and the gaps closed. Splitting, repeating or parallel requests did not get past a bound, but two edge cases let a deposit be counted more than once (B), evidence was not labelled by how it was known (A), and the override lacked safeguards (C). All are fixed.

**A. Evidence provenance.**
- *Found:* a deposit Staff confirmed counted like a recorded payment and was labelled "verified"; Staff's basis was not kept, so a bare assertion counted like a check.
- *Changed:*
  - Deposits carry a **level** (`recorded_payment`, `staff_checked_bank`, `staff_checked_document`, `staff_assertion`); the evidence page requires a basis (bank, document, customer said so), and a business identity requires a basis (registry, document).
  - New policy key `newCustomers.staffCheckedDepositUpTo` (null default, strictest; the demo policy sets AUD 600.00). A Staff-checked deposit counts only when the exposure is within it; otherwise the need is "record the payment in Nucleon Records".
  - A customer's word is stored and shown but never counts.
  - Every display (evidence item, `keyFacts.verifiedDeposit` + `depositSources`, the card, the Owner page, the case view) says the source and level in words.
  - Facts with no basis (earlier rows) are treated as assertions; the fictional seed identity is basis `document`, source "fictional seed".
  - A case gathering evidence is re-evaluated when the same ask is repeated after Staff record the payment in Records.
- *Unchanged:* a contradiction (confirmed amount differs from a recorded receipt with the same reference) still puts the request on hold, at any level; a confirmation never creates or changes a payment.

**B. Aggregate exposure.**
- *Already correct (now tested):*
  - Two invoices each within the per-decision cap but together over the customer cap are not auto-approved.
  - Several invoices within the caps are each approved.
  - Existing debt counts towards a new trial credit.
  - Parallel trials for different customers cannot pass `maxAutonomousExposure30d` (cap 1,500 with four 600 requests: two approved).
  - A second slice of an order goes to the Owner.
  - An overridden line stops counting.
  - Unknown amounts and incomplete records are unknown, never zero.
- *Gaps fixed:*
  - **Double-counted deposit:** the replay lets an unallocated deposit receipt pay down an opening balance, so a trial customer's total was understated by the deposit (debt 1,000.00, deposit 200.00, order 800.00 read 1,400.00 instead of 1,600.00). Customer totals now read the debt without receipts that are, or were given as, a deposit.
  - **Deposit reuse:** the same receipt could be the deposit of a second trial credit after the first line ran out. A deposit given for an approved trial credit is not given again.
  - **Caveat:** when the customer's records are not confirmed complete, the customer-exposure sentence and a warning call the total the RECORDED exposure (a caveat, not a block, unless `evidence.confirmedCoverageAbove` applies).

**C. Owner overrides.**
- *Already correct:* history kept in `decisionHistory`, a new `owner_override` decision, event `decision.overridden`, the due date reverting, a trial line revoked.
- *Added:*
  - `version` required (409 `STALE_CASE`, nothing changes).
  - An Idempotency-Key replays the stored result (written in the same transaction as the override, so it survives a restart); the page sends one.
  - `overridesPolicyVersion` and the Owner's person/channel provenance on the override decision, the case and the event.
  - `externalEffects` (Nucleon sent nothing; anything Staff already did outside Nucleon is not undone; for trial credit, invoiced amounts remain owed) in the result, the case view, the Owner page and the card.
- *Tested:* a payment recorded between approval and override, a records change racing the override, a double override, a stale version, and a restart.

### As built (S1a, 30 Oct 2026, branch `s1/decision-loop-backend`)

Backend only, additive (a new table, a new policy key, new routes, new JSON keys on a case); `delegation.py` rules are unchanged. Tests: `prototype/test_decision_loop.py`.

**Case timeline.** Table `case_events(seq, case_id, kind, at, actor, policy_version, data)`, append-only, indexed on `case_id`, cleared by a demo reset. `case_event()` writes inside the same transaction as the state change, and never for a replay or a refused call. `policy_version` is the version the case was evaluated under (a tacit agreement: the version in force). `actor` is `agent`, `owner`, `staff` or `system`. `data` is a small JSON, never the whole case.
- **Kinds:** `created` (agent), `evaluated` (system, on every evaluation including after evidence), `decided` (agent, or owner with `by` owner or owner_exception), `evidence_requested`, `escalated` (owner_review), `held` (policy_hold), `evidence_submitted` (staff), `feedback` (owner, with the verdict), `override` (owner, written after its `feedback`), `closed` (system: the records no longer support the request, or the request was withdrawn), `outcome_observed`, `tacit_agree` (system), `viewed` (owner).
- `GET /api/decision-cases/<id>/events` returns `{caseId, events}` in seq order, for an Owner person or Staff. Staff never see `feedback`, `tacit_agree` or `viewed`, nor any `reason`.

**Outcome observations (D10).** `outcomes.py` holds the pure rules; `App.observe_outcomes(as_of=None)` runs them over every live, approved, not overridden case. Vocabulary `on_time | late_paid | partial | open_not_due | open_past_due | written_off | unknown`; the ledger has no write-off marker, so `written_off` is never produced.
- An extension is judged against its approved due date. A trial credit reads every invoice issued on or after the approval: `on_time` only if all are, a definite adverse fact outranks `unknown`.
- A `case_events` row `outcome_observed {outcome, asOf, observedAt, policyVersion, basis}` and `data.outcomeObserved` are written only when the outcome differs from the case's last observation (so repeats write nothing, and a later ledger edit appends without rewriting). It does not change the case `version`.
- `POST /api/delegation/observe-outcomes {asOf?}` (Owner person, csrf, Origin) returns `{observed, changed, unchanged, cases, asOf}`. It also runs after an import is applied (its own transaction; a failure never fails the import).
- `case_view` and the case list carry `outcomeObserved` (stored) and `outcomeNow` (`source: 'current ledger says'`); the older `outcome` field is unchanged.

**Tacit consent (D8).** Policy key `feedback: {tacitAgreeAfterDays: null | 1..365}` (default null = off; a version saved without it reads as off; it joins the policy digest only when set). `App.sweep_tacit_consent(as_of=None)` appends `{verdict: 'tacit_agree', at, reason, policyVersion}` to `feedback[]` and writes a `tacit_agree` event, in one transaction, for live agent decisions that are not overridden, have no feedback, and are at least N days old (by `decision.at`); never while the policy is paused or the setting is null.
- `POST /api/delegation/sweep-tacit-consent` (Owner person; it takes no date) returns `{agreed, skipped: {paused, off, tooRecent, hasFeedback, alreadyTacit}}`. `GET /api/delegation/cases` runs the sweep first when the setting is on and the policy is not paused.
- `dg_owner_view` counts a tacit agreement as approve (an explicit verdict given later wins); `dg_owner_kind` gives `explicit` or `tacit`. Memory rows, live comparables and `reliability.live.verdictKinds {explicit, tacit}` report the two apart. A tacit agreement has no Owner reason.

**Owner view.** `POST /api/decision-cases/<id>/viewed` (Owner person, csrf, Origin) writes a `viewed` event, at most one per case per 60 seconds; inside the window it writes nothing and returns `recorded: false` with the earlier time.

### As built (S1b, 30 Oct 2026, branch `s1/decision-loop-backend`)

Backend only, additive; the ladder in `delegation.py` is unchanged except the step-7 input. Tests: `prototype/test_s1b.py` (and one Lab test).

**Track-record sources (D7).** Policy key `trackRecord.sources: 'fictional' | 'live' | 'both'` (default `both`; strict; a policy PUT that omits it keeps the current version's value, as it does for `feedback.tacitAgreeAfterDays`, until S2 adds the controls; a version saved without it reads as `both` and keeps its digest, which joins the fingerprint only when it is not `both`). `track_record` takes the reviewed memory the server already computes (no database in `delegation.py`) and counts, per category, the reviewed cases the policy would approve: `fictional` = the held-out evaluation set (exactly the earlier behaviour); `live` = live Owner-reviewed cases, explicit and tacit verdicts counted apart; `both` = the two pooled. With no live case `both` is `fictional`. `reliability` keeps its earlier keys and adds `sources`, `gatedOn` (`fictional | live | pooled`) and `gate {fictional {cases, approved, declined, agreement}, live {cases, approved, declined, agreement, explicit, tacit}, pooled {...}, needed, shortBy}`. Step 7's reason says how many more cases are needed ("3 more live Owner-reviewed cases the policy would approve are needed (2 of 5)"), or that agreement is below the Owner's number. The pooled figure exists for the gate only; the fictional and live counts are always shown apart.

**Tightening suggestions** (`delegation.suggestions`, served by `GET /api/delegation/suggestions`; all `suggestionOnly`, each with `evidence.byDataset` so live and fictional counts never merge). The three thresholds are module constants that become Owner settings in S2.
- `lower_limit` on `newCustomers.maxExposure` / `extensions.maxDays` (fictional examples and live; never the evaluation set): at least `LOWER_MIN_DECLINES = 2` reviewed cases inside the bound that the Owner declined or disagreed with, OR at least `LOWER_MIN_ADVERSE = 1` that turned out `late_paid | partial | open_past_due | written_off` (a live case, by its stored `outcomeObserved`; none = neither good nor bad) or `late | defaulted` (a fictional label). One decline with no adverse outcome does not trigger it. It proposes a bound one minor unit or day under the lowest triggering case, never below zero. The note says it works against growing autonomy.
- `switch_mode` to `advisory`: `ADVISORY_MIN_OVERRIDES = 2` or more live agent decisions overridden that were made under the current policy version; the list is the evidence.
- A `raise_limit` now ignores cases with an adverse stored observation, reports `evidence.tacitAgreements` and `explicitAgreements`, and needs at least one explicit approval.

**Impact** (`impact.py`, pure; `GET /api/delegation/impact?from=&to=&policyVersion=`, Owner person, Staff 403, live only). Every number is `{value, numerator, denominator, source, dataset, note}`; `source` is `measured`, `derived` (rates) or `assumption`; an empty sample is `null`, never 0. A case is in the window by its created day (UTC) and the version it was decided under.
- Keys: `counts` (same as `/stats`), `cases`, `autonomousCoverage` (agent-decided, overridden or not, over cases that reached a decision or escalation), `escalationRate`, `evidenceRequests {count, answered, pending, medianTurnaroundSeconds}`, `timeToDecisionSeconds {median, p90, cases, byKind}`, `ownerInterventionSeconds {median, cases, withoutView}` (first `viewed` to the Owner's `decided`, `feedback` or `override`; null until the Owner page posts `viewed`), `overrides {count, rate}`, `disagreements {count}`, `liveAgreement {explicit, tacit, agreementRate}`, `outcomes {byLabel, pending, neverObserved}`, `perPolicyVersion`, `timeSaved` (`value: null`, `source: 'assumption'`).
- `outcomes.pending` is approved, not overridden decisions with no observation; declined and overridden decisions are never observed, so they are `neverObserved`, not pending.

**Policy save (exception).** Until S2 adds the controls, a `PUT /api/delegation/policy` body that omits `feedback.tacitAgreeAfterDays` or `trackRecord.sources` keeps the current version's value for those two (an explicit value, `null` included, wins); every bound and limit left out still takes its version-0 value. It is done in `App.save_policy`, not `validate_policy`.

**Tool results.** On a refused `assessDecision` / `resolveDecision` / `decisionStatus` the code and message are unchanged and `hint {ask: kind | invoice | customer | amount | terms | dueDate, question, options?}` is added where Staff can answer it (no hint for a wrong recommendation or a forbidden role). On success `forModel {status, handling, statusText, why, nextStep, keyFacts <= 8}` (at most 600 characters of JSON, code-written `nextStep`) sits beside the unchanged full result; the Lab card renders the same page with or without it.

### As built (S3, 31 Oct 2026, branch `s3/agent-hardening`)

Agent hardening; no change to `delegation.py`. Tests: `prototype/test_s3_tools.py`, `test_agent_instructions.py`, Lab `test_compact_result.py`, `tools/modelbench/test_bench.py`.

**What the model reads.** When a tool result holds `forModel`, the Lab's text item for the model is the JSON of `forModel` (plus the result's `hint`), 600 characters at most for the decision tools instead of the 8-10k of the full result; the card (second item) is made from the full result and is unchanged, and the full JSON never goes to the model. A refusal is `{error, message, hint}` (the Lab used to drop the hint). Every other tool's text is unchanged. `dated()` no longer adds `...Text` keys inside `forModel`.

**Five read tools** (registry rows, `defaultEnabled: False`, none stores or decides anything; the compact `forModel` of each is bounded: 600 characters for `whatIsNeeded` and `customerStatus`, 1500 for the three that carry figures). Enable each as the Owner: Setup, "Agent tools", or `POST /api/agent-tools {"tool": "<name>", "enabled": true}` (Owner person, CSRF token); then the Lab offers it by role.
- `whatIsNeeded` (Staff, Owner): same arguments as `assessDecision` without `recommendation`. `delegation.assess_evidence` through the same path as `assessDecision` (`dg_evaluation`); returns the evidence section and `forModel {status: sufficient | missing | insufficient | contradictory, statusText, staffCanProvide [{need, how}], staffCannotProvide, nextStep}`. A missing argument gives the same `hint`.
- `comparableCases` (Staff, Owner): the comparables the evaluation would use (fictional examples and live reviewed cases, never the held-out evaluation set), each labelled an analogy unless it is the customer's own; the Owner's reasons are stripped for Staff, in the full result and in `forModel`.
- `customerStatus` (Staff, Owner): live cases of one customer: latest status and `statusText`, the trial credit line in force, the evidence requests waiting for Staff (`actionId`, `evidenceLink`, needs), the last outcome observation. No cases is a result (`no_case`), not an error.
- `policyBacktest` (Owner only; `changes` is a partial policy): the current policy with the changes merged and validated by `validate_policy`, run through `delegation.track_record` against the same memory, next to the current policy: the fictional evaluation set (labelled a simulation) and live Owner-reviewed cases counted apart, plus whether the track-record gate would be established. Saves nothing (`saved: false`); only the Owner, as a person, saves a policy.
- `impactSummary` (Owner only; optional `from`, `to`): the impact endpoint's figures (`App.impact_report`, shared with the route, which still needs an Owner person), live only; `forModel` gives each headline figure as "n of d (value, source)"; an unknown figure says "not known yet", never 0.

**Agents.** `integrations/librechat/agents/instructions_staff.txt` is the one source of the Staff instructions (the agent script `update_ada_agent_hints.js` carries a synced copy; the model bench reads the file): ask `hint.question` (with `hint.options`) and stop; reply from `forModel.statusText` / `nextStep`; one `whatIsNeeded` read before `resolveDecision` only for a trial credit whose message lacks a deposit or identity detail. `seed_owner_agent_3080.js` creates "Nucleon ADA Owner (Qwen)" on the new MCP entry `nucleon-local-owner` (the Owner token): ten read tools, no write path; for any action it sends the Owner to `#/review` or `#/delegation`. Neither script was run on the live Mongo (rollout order in `integrations/librechat/README.md`).

**Model bench** (`tools/modelbench/bench.py`): see `docs/research/MODEL-BENCH-20261031.md`. **Tool timing log:** Lab config `timingLog` (see `lab/README.md`).
### As built (S2b, 31 Oct 2026, branch `s2b/owner-pages`)

The Owner's pages on the S1 backend; the ladder in `delegation.py` is unchanged. Tests: `prototype/test_s2b.py` (29); page checks `deploy/review_page_check.py`, `deploy/dashboard_page_check.py`, `deploy/delegation_page_check.py`, `deploy/home_page_check.py`.

**New routes (all additive).** `GET /api/delegation/loop` (Owner person: `impact.loop_counts`, pure; the live cases by stage now: `request | evidence | evaluation | decision | feedback | outcome`, closed ones counted apart). `POST /api/ui-events` and `GET /api/delegation/ui-summary?from&to` (below). `GET /api/actions?kind=evidence&status=open` (Staff, Owner, and a service session; read-only; any other kind or status is 400): `{actions: [{id, status, createdAt, expiresAt, caseId, customer, caseKind, asks, needs, link: '#/actions/<id>'}]}`, open meaning proposed, not expired, on a live case still gathering evidence.
**New fields.** Case rows (`/api/delegation/cases`) add `why`, `comparables {n, approved, declined, sameCustomer}`, `reliability {status, sources, gatedOn, sentence}` and `overrideEffects` (what an override does not undo, readable before confirming). `/api/delegation/stats` adds `trackRecord {extension, trial_credit}` (`sources`, `gatedOn`, `gate {fictional, live, pooled, needed, shortBy}`, computed with the current policy). A tacit feedback entry adds `afterDays`.

**Page-use events (D11).** Table `ui_events(seq, at, role, channel, page, kind, data)`, in `DATA_TABLES` (a demo reset clears it). `POST /api/ui-events` takes a list `[{page, kind, data?, at?}]` (or `{events: [...]}`), a person's Staff or Owner session only (a service or the AI Agent is 403 PERSON_REQUIRED); `kind` is `page_enter | page_leave | click | decide_start | decide_done`, `page` a route name, `data` a flat object of at most 8 short values, `at` kept only if within a day before and five minutes after the server's time. Any invalid event makes the call 400 and stores nothing; at most 50 events are read per call and 60 kept per session per minute, the rest dropped without an error (`{accepted, dropped}`). No csrf token (a closing page's `sendBeacon` cannot send one); because it cannot send the role header either, it names it in the address (`?role=owner`). `GET /api/delegation/ui-summary` (Owner person): per page `enters, leaves, clicks, medianDwellSeconds` (None until a `page_leave` carries `ms`), named clicks, and decisions (`started, done, medianSeconds`). The pages send route names, button names (`data-track`) and durations only: no case, customer or typed text. Nothing leaves the machine.

**Pages.** `#/review` (Owner; Staff get Page not found): (a) waiting (`awaiting_owner`, `on_hold`) with Approve / Decline (an exception when on hold) and a required reason, a trial credit through `POST .../decide`, an extension through its request (`POST /api/requests/<id>/decisions`, read fresh, refused if the case version changed); (b) agent decisions with no explicit feedback (a treated-as-agreed one is labelled and stays listed until the Owner answers): Agree (reason optional; an empty one is sent as "Agreed (no reason given)." because the route requires one), Disagree and Override (reasons required; an override first shows `overrideEffects`), sent with the case `version` and one Idempotency-Key per payload; a stale version is 409, the message says nothing was recorded and the row is read again; a row left open while its case changes keeps the version it was read at and asks to be read again; (c) the last ten reviewed. `viewed` is posted when a row is first opened on the page. `#/decision-cases/<id>` (Owner and Staff): the six stages marked, the three dimensions, the decision and authority, the Owner's feedback (Owner only), `outcomeObserved` apart from `outcomeNow` ("current ledger says"), "pending" when nothing is observed, and every event. `#/dashboard` (Owner): one tile per impact metric (value, numerator over denominator, `measured | derived | assumption, not measured`, dataset), `null` as "no data yet", `timeSaved` as "not measured — set from PoV interviews", date and policy-version filters, the loop strip, outcome bars (widths set through the CSSOM: the CSP allows no inline style), usage, "Observe outcomes now". The control panel now sends `feedback.tacitAgreeAfterDays` and `trackRecord.sources` explicitly, so the PUT exception in S1b no longer matters to it.
**Not done / known.** `case_view` still returns an Owner decision's `reason` to Staff (the timeline page does not show it to Staff; the events route strips it). `ui_events` has no retention limit. The thresholds of the tightening suggestions are still module constants.

## 11. End-to-end acceptance with Qwen and LibreChat (isolated, fictional, 2026-10-26)

**Where it ran:** LibreChat rc3-test on :3081, the Nucleon test stack on :18631/:18630 (`~/Developer/nucleon-ada-test`), and Qwen3.5-35B-A3B in LM Studio. The test agent was "Nucleon ADA TEST Staff (Qwen)" (`nucleon-test/seed_ada_agent.js`).

**Evidence:** `~/Developer/nucleon-ada-test/evidence/` holds `result.json` (rounds 1–4), the screenshots and the raw tool outputs. Every scenario was checked against the backend's state; Qwen's text is supporting evidence only.

**Final round** (`81c9e6e`), no retries:
- **Bayview extension:** decided by the agent, due date 18 Oct → 10 Nov.
- **Northside trial credit:** decided by the agent, exposure AUD 600.
- **Lakeside evidence flow:** Qwen recommended `approve_if_verified`, Staff confirmed the facts, and the agent's decision took effect, exposure AUD 450. A fresh-chat status question matched the backend.

**Earlier rounds:**
- **Harbourline:** went to Owner review. Asked "just tell them yes", Qwen refused, accurately.
- **Owner page:** setting the policy, override and pause all passed.
- **Financial cards:** passed, with completeness warnings.
- **Phase B:** prepareRequest → confirm → awaiting the Owner still works.

**Defects found in E2E and fixed:**
- stacked duplicate trial approvals;
- `customerOverview` failing on an undated payment;
- the pause reason not shown on the card;
- the raw-fraction ratio wording;
- missing evidence turning into an escalation (fixed with `approve_if_verified`).

**Model behaviour still seen:**
- Qwen sometimes repeats calls or wanders.
- It can state the order amount instead of the exposure.
- It mixed the two flows when it had both `prepareRequest` and the delegation tools, so keep them on separate agents.

The card shows the backend's status.
