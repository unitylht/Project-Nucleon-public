# Nucleon specification

Project Nucleon, INFS3605, Stream 1. Written on 11 November 2026 for branch `feat/week9-followups` and checked against its code. Numbers from tests or trials name their source file. The assistants' prompts are in [PROMPTS.md](PROMPTS.md).

## 1 Purpose and users

A small B2B business owner gets requests for more time to pay and for a first credit. Each one pulls the Owner into a phone call. Nucleon takes the routine ones off the Owner. An assistant reads the request and the records. Code checks it against rules the Owner set, then approves it, asks Staff for missing evidence, or sends it to the Owner. Every decision is recorded and the Owner can reverse it.

Users:

- **Owner.** Sets the rules, decides what is sent to them, reviews what the agent decided.
- **Staff.** Enter requests, confirm facts they have seen, tell the customer. Staff never approve credit.
- **Operator.** Demo console, practice workspaces only.

The pilot business reports about one such request a week and about five days to approve (`docs/pov/README.md`, relayed, not measured by us).

## 2 Scope

**In scope**

- Two kinds of request: a payment extension on one existing invoice, and a trial credit (a first order on credit) for a customer with no earlier invoices.
- A versioned Owner policy for what the agent may decide, evidence checks, a record of every decision, Owner feedback, and the outcome read from the records.

**Out of scope:** sending anything to a customer (every result says "Nucleon sent nothing to the customer. Staff informs the customer."); looking up a business in any register; fine-tuning a language model.

**Non-goals:** replacing the Owner's judgement on large cases; fulfilling orders or taking payments.

## 3 The decision loop

Six stages, shown on every case timeline (`web/timeline.js`).

1. **Request.** Staff enter it on Requests or through the Staff assistant.
2. **Evidence.** Nucleon works out what the records show and what Staff confirmed, and asks Staff for what they can supply.
3. **Evaluation.** Code applies the policy (section 6) and stores the result.
4. **Decision.** The agent approves (or, if the Owner allowed it, declines), or the case goes to the Owner or onto a policy hold.
5. **Owner feedback.** The Owner can agree, disagree or override. After a number of days the Owner sets, an unreviewed approval counts as agreed, and is labelled so.
6. **Outcome.** Later, the records show it repaid, open and not yet due, open and past due, or unknown (`delegation.derive_outcome`).

## 4 Roles and what each may do

**Owner** may save a policy version, pause the agent, decide waiting cases, agree with, disagree with or override agent decisions, confirm a customer's records are complete, and switch assistant tools on or off. Only the Owner sees the Control panel, Decide, Dashboard, Model, Quick setup and Doctor.

**Staff** may enter requests, keep records, run imports, write notes, and confirm facts. Staff may not approve credit and may not see the Owner's reasons.

**The agent** is the chat assistant acting through tools. It recommends. It cannot change the policy, cannot approve outside it, and cannot confirm facts: a session that belongs to the assistant or a service is refused (`web/actions.js`).

**The Staff assistant** (LibreChat agent "Nucleon ADA Staff (Qwen)", `integrations/librechat/agents/instructions_staff.txt`) finds customers, reads invoices, gives a recommendation with `resolveDecision`, and reports status. It may never guess an invoice number or other argument, handle a mixed request without asking Staff which kind it is, say a request is approved unless the tool result says so, or send anything to a customer.

**The Owner assistant** (LibreChat agent "Nucleon ADA Owner (Qwen)", `seed_owner_agent_3080.js`) is read-only: `decisionStatus`, `customerStatus`, `comparableCases`, `policyBacktest`, `impactSummary`, `doctor`, `modelStatus`, `cases`, `workQueue`, `customerOverview`, `invoices`, `findCustomers`. It may never decide, approve, decline, override, give feedback, pause the agent or save a policy. For these it points the Owner to the Decide page or the Control panel.

## 5 Functional specification

### Pages

The menu is `NAV` in `prototype/web/core.js`. The Owner sees Home, Assistant, Decide, Control panel, Dashboard and Customers, with Requests, Imports, Model, Knowledge and Setup under "More". Staff see Home, Assistant, Requests and Customers, with Imports, Knowledge and Setup under "More". Assistant shows only when a chat address is configured. Quick setup and Doctor are not in the menu: the Control panel and Owner Home link to them.

- **Home.** What waits, recent agent decisions (Owner), information Nucleon needs (Staff), live counts, and what happened since the user last looked.
- **Decide** (Owner). "Waiting for you": escalated and held cases with the reason, key facts, the assistant's recommendation and similar reviewed cases. Approve or Decline needs a reason. "Autonomous decisions to review": Agree (reason optional), Disagree and Override (reason required; Override states what it does not undo). "Recently reviewed" shows ten.
- **Control panel** (Owner). The settings below; each save is a new policy version. Also: current policy, suggestions, standing rules for one customer, scheduled changes, model settings, versions, live counts, and "Pause delegation" or "Resume delegation".
- **Dashboard** (Owner). Exposure now, live cases by loop stage, impact tiles (each with numerator, denominator and source; unknown reads "no data yet", never 0), outcomes of approved decisions, page usage. Fictional cases are not counted.
- **Customers** (records, completeness statements, notes) and **Requests** (queue, new-request form, case page with one next action).
- **Imports.** CSV invoice and payment files become drafts. The user checks every row, then applies, keeps or discards. An applied import can be reverted.
- **Model** (Owner). The team's classifier, kept as a shadow: "Model in force", "Agreement with you", "Settings", "Training table", "Saved versions", and two sections that feed it.
  - "Teach it your limits" asks what-if questions about real customers, far out first and then narrowed. Each answer is stored as an `owner_preference` case that comparables and the training table use. The track record does not.
  - "Add a decision you made yourself" records a past approve or decline for a customer and request kind, with an optional reason.
- **Knowledge.** Short notes shown in requests. Only Owner-confirmed notes are used, and none changes a calculation.
- **Setup.** Workspace type (real or practice, chosen once), currency, decimal places, time zone, a checklist, and the "Agent tools" on/off table.
- **Quick setup** (Owner). Nine plain questions: how the agent starts; the largest invoice; the most one customer may owe; the latest new payment date; the most an invoice may be late in total; whether other overdue invoices block it; how to treat customers who paid late before; customers never to decide for; whether the agent may say no by itself. A read-only preview shows what the answers would do to the Owner's open invoices if each customer asked for 7, 14 or 30 more days. Save stores an ordinary policy version.
- **Doctor** (Owner). Six questions, answered by code from the Owner's cases over 30 days, 90 days or everything: why requests still come to the Owner; why the Owner keeps correcting the agent; how much the agent helps; whether approved extensions were paid; which customers come most; which rules never matter or block everything. A suggestion opens Quick setup filled in. Nothing is saved from the Doctor.
- **Staff information page** (`#/actions/<id>`). Staff confirm facts they have seen: a deposit (amount, date, reference, how known), a business identity, a trade reference, no earlier account. The page says Staff are confirming facts, not approving credit. Business identity asks for the registration number, trading name, how it was seen, and optionally "Registered since".
  - **ABN check.** An 11-digit number is tested with the ABN arithmetic (`delegation.abn_check`), and the page says whether it is well formed. It is for information only. No rule reads it or the age of the business, and Nucleon looks nothing up.

### Control panel settings

Labels are quoted from `web/delegation.js`.

**Basic**

- Mode: Advisory or Delegated.
- Most money one request may involve (the exposure of one decision)
- Most one customer may owe you in total (the customer's total exposure)
- Longest single extension (days after the invoice's current due date)
- Latest new payment date (days after the day the request is received), optional
- Most an invoice may be late in total (days after its original due date), optional
- Trial credit for new customers: Off, or On within the limits
- Most trial credit exposure (the order less the deposit received)
- Smallest deposit (% of the order; 0 = none asked)

**Approvals the agent made that you have not looked at, and how it earns trust**

- Count an approval the agent made as agreed when you have not reviewed it for (days)
- Which reviewed cases count as the agent's track record: fictional, live, or both pooled (default).

**Exceptions the agent may decide.** Off by default. A request a little over a money limit or the longest extension, approved only when the model gives a high chance of approval and the Owner approved enough of the five most similar cases.

**A little over a money limit.** Off by default. A share and/or amount over a money limit the agent may approve with no model.

**When the agent may decline on its own.** Off by default, extensions only. Lines: days past the due date, amount unpaid on the invoice, everything the customer owes, share of earlier payments that were late.

**Advanced (extra controls; all can be left as they are).** The 30-day approval budget, late-payment share, trial terms, trade reference level, Staff-checked deposit level, records-confirmed-complete level, never-decide customers, unusual size, track record minimums.

### Tools

Tools are defined in `prototype/coordinator.py` (`CAPABILITIES`), served at `GET api/tools`, and republished by the Lab (`lab/mcp_server.py`) over MCP with a bearer token per role. The Lab exposes read and prepare tools and three acts (`withdrawPreparation`, `requestSuggestion`, `resolveDecision`), never `openRequest`.

- **Both roles, read:** `findCustomers`, `customerOverview`, `invoices`, `ownerContext`, `cases`, `caseDetails`, `listRequests`, `workQueue`, `whereIs`, `compareExtension`, `whatIsNeeded`, `comparableCases`, `customerStatus`, `decisionStatus`, `actionStatus`.
- **Staff:** `assessDecision` (stores nothing), `resolveDecision`, `openRequest`, `raiseConcern`, `prepareRequest`.
- **Owner:** `policyBacktest`, `impactSummary`, `modelStatus`, `doctor`, `prepareDecision`, `requestSuggestion`, `withdrawPreparation`, `answerConcern`, `interpretStatement`.
- **Prepare for a person to confirm:** `prepareCustomer`, `proposeImport`. `prepareHoldingMessage` writes text to copy and sends nothing.
- **Never offered to an agent:** `actWithinAuthority`, `applyImportProposal`, `withdrawRequest`.

`assessDecision`, `resolveDecision`, `decisionStatus`, `prepareRequest` and `actionStatus` are off by default in the code. The Owner switches them on under Setup. I could not check whether a deployed instance has.

## 6 Decision rules in order

`delegation.evaluate` is a pure function. The model recommends. Code decides. Unknown is never treated as zero.

**Before the steps.** A current standing rule for the customer replaces the general customer limit and longest extension. Evidence is assessed. Each risk check gets pass, fail, unknown or na. A money limit missed by the small margin the Owner allowed becomes an "exception" and no longer fails. The exception band can do the same, but only with a model score and enough approved comparables.

**Definitions**

- **Exposure of one decision.** Extension: the amount still unpaid on that invoice (unknown if not recorded). Trial credit: the order amount less the verified deposit, the deposit capped at the order.
- **The customer's total exposure.** Extension: what the customer owes now (ignoring receipts already used as an approved trial credit's deposit) plus trial credit lines in force. The request adds nothing, because the invoice is already owed. Trial credit: what the customer owes, ignoring any receipt that could be this deposit, plus lines in force, plus this decision's exposure. Unknown if the customer's records are incomplete. A trial line is in force when approved, not overridden and not past its due date.

**Steps.** The first step that applies, in the order below, decides. The others are shown as further reasons. Step 8 comes before 6 and 7.

1. **Hold:** the customer is on the Owner's hold list, or the evidence contradicts the records. `policy_hold`.
2. **Outside the policy:** a risk check fails (limits, days, nothing else overdue, late history, unusual size, trial already in force, earlier dealings, terms). `owner_review`.
3. **Evidence Staff can supply is missing** (deposit, identity, trade reference). `request_evidence`, even in advisory mode.
4. **Evidence is insufficient and Staff cannot supply it** (unreadable records, or records not confirmed complete above the Owner's level). `owner_review`.
5. **A risk check is unknown.** `owner_review`.
8. **Not delegated:** advisory mode, a pause, or the category switched off. `owner_review`.
6. **Most of the closest comparable reviewed cases were declined by the Owner.** `owner_review`.
7. **The required track record is not established.** `owner_review`.
9. **The assistant did not recommend approval,** or the promoted model puts the chance of a decline at or above the Owner's bar. `owner_review`.
10. **None of the above.** `autonomous_approve`.
11. **Autonomous decline.** Only if the Owner turned it on, the request is an extension, the assistant recommended decline, a value the records establish is over a decline line, and no step 1 or 8 applies. `autonomous_decline`. Over a line without a decline recommendation, the request goes to the Owner and the agent never approves it.

A trial credit also needs a deposit share at least the Owner's minimum (step 3 asks for it).

## 7 Data and privacy

- Records live in a local SQLite database. The model runs locally in LM Studio. No customer data goes to a cloud model.
- Money is stored in minor units. Each decision stores the policy version and a fingerprint of its rules.
- Nothing is sent to customers. No setting allows it.
- Demonstrations and tests use **fictional** data in a labelled practice workspace. Real workspaces refuse the sample. Pilot data came from a real small business's records, anonymised.
- Access codes are generated at start-up and are not committed.

## 8 Architecture and deployment in brief

- **Records** (`prototype/`): a Python standard-library server and browser front end. It holds the data, policy, rules and tools.
- **Lab** (`lab/`): an MCP server that maps a bearer token to a role and calls the Records tools. It holds no data.
- **LibreChat**: the chat front end, with a Staff and an Owner agent.
- **Local model**: Qwen3.5-35B-A3B in LM Studio on 127.0.0.1, context 32,768 tokens.
- **Public access for testers**: a Cloudflare Tunnel with Cloudflare Access (email allow-list, one-time code). The three services listen only on 127.0.0.1. Source: `docs/DEPLOYMENT.md`.

## 9 Non-functional targets that were measured

No numeric usability targets are set (`docs/research/POV-VALIDATION-PLAN-20261030.md` claims none). Measured:

- **Staff agent on a five-prompt bench** (`docs/research/MODEL-BENCH-20261031.md`; bar: 9 of 10 runs with every prompt correct in at most 4 tool calls). Reference instructions: 5 of 10 runs, 47 of 50 prompts. Resolve-only instructions: 17 of 20 runs, 97 of 100 prompts, no wrong approvals, 8 to 11 s per prompt. qwen3.8-27b: 9 of 10 runs, median 70.6 s per prompt.
- **Per request on the live agent at 32,768 context:** 1 to 3 tool calls, 21 to 32 s (`docs/KNOWN-LIMITATIONS.md`, L-001, L-002). Backend time inside tool calls: 18 to 56 ms per prompt (bench file).
- **Local model as a free-text doctor:** 19 of 24 answers right, one to three minutes each (L-004). So code writes the Doctor's answers.
- **Edge limit:** Cloudflare cuts a request silent for more than 100 s (`docs/DEPLOYMENT.md`).

## 10 Acceptance checks

- **Unit tests:** 55 files `prototype/test_*.py`, 7 in `lab/tests/`. Run `python3 -m unittest discover -s prototype -p 'test_*.py'` and `python3 -m unittest discover -s lab/tests` from the repository root.
- **Page checks (browser):** `deploy/*_page_check.py` (delegation, home, action, review, review_decline, dashboard, quick_setup, doctor) and `deploy/e2e_*_check.py`.
- **One command:** `deploy/m3-local/bin/check` runs the unit tests and the main page checks. `--quick` skips the slow ones, `--mcp` adds live services. It uses `NUCLEON_REPO` (default `~/Developer/Project-Nucleon`), so set that to test this branch.
- **Agent acceptance** (model running): `deploy/m3-local/tests/accept_final.py`, `accept_owner.py`. **Public setup:** `deploy/m3-local/bin/pov-check`.

These checks were not run when this file was written.

## 11 Known limitations

From `docs/KNOWN-LIMITATIONS.md`:
- A mixed or incomplete request can make the model guess. The backend refuses invalid arguments, but the model's wording is the weak point (L-001).
- If the model's context falls back to 8,192 tokens, the agent forgets its results and loops (L-002).
- Quick setup's preview is an estimate. It assumes the assistant recommends approval, tries at most 200 open invoices, and is English only (L-003).
- The Doctor's what-ifs ignore the assistant's recommendation, track record, advisory mode, pauses and first credits (L-004).
- LibreChat can ban a script that logs in, with the host address, for 2 hours. Test it in a browser.

Also:

- The ABN is checked arithmetically. It is not looked up, and no rule uses it.
- Approving a waiting case on the Decide page requires a reason.
- The model needs fitted data. Without enough Owner-labelled cases it gives no score, so the exception band and the model's caution do not apply.
- The Setup page says every tool is on by default, but five are off in the code until the Owner switches them on.

## 12 Change log

Git history of this repository. Product decisions are in [docs/DECISIONS.md](docs/DECISIONS.md) and, for the current phase, `docs/memory/DECISION-REGISTER.md`.
