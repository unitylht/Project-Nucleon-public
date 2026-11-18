# Nucleon: Product & Architecture Brief (Adaptive Decision Authority)

For the INFS3605 team and presenters. Updated 2026-10-26.

**Status labels**
- **Built & tested in isolation:** code committed on a local branch, tested on a separate test stack. **Not** on the normal M3 demo services and **not** on M6.
- **Simulation:** uses fictional data. Never present it as NTK results.
- **Roadmap:** not built.

## Status as of 27 Oct 2026 (verified)

**Code:** `da95220` on `feat/adaptive-decision-authority-20261026`, local and unpushed. (`2b2b786` was the first deployed commit.)

**Deployed to the normal local M3 environment, all on fictional data:**
- **Nucleon:** Records `http://127.0.0.1:8631` and Lab/MCP `:8630`.
- **LibreChat:** `http://127.0.0.1:3080` switched to the `librechat:nucleon-card-v0.8.8-rc3-test` image.
- **Agent:** a separate **"Nucleon ADA Staff (Qwen)"** agent with 6 tools. The existing agents are unchanged.
- **Policy:** version 0 (advisory, nothing executes), until the Owner saves a delegated policy.

**Verified:**
- **Automated tests:** Records 950 (Python 3.9 and 3.12), Lab 382, and the headless page checks (59/59 and 42/42).
- **Isolated browser rounds:** four rounds with real Qwen + LibreChat on a separate test stack.
- **Deployed backend:** a deterministic acceptance against the deployed backend passed every scenario.

**Browser-verified on the normal environment (27 Oct):** a real Qwen + LibreChat round on 3080 passed **17/17** checks against the backend records. It covered:
- **Decided by the agent:** the extension (+23 days), Northside's trial credit, and Lakeside after Staff evidence.
- **Owner review:** Harbourline went to the Owner, and the "just say yes" probe was answered correctly.
- **Owner controls:** override with history kept, and pause and resume.
- **Integrity:** the financial card's completeness warnings, no outbound actions, and no ledger payment created from Staff evidence.

The 4-minute demo video was recorded on this environment. **The normal system is left in advisory mode (policy version 0)** until a presenter saves the demo policy.

**Not on M6.**

## One-line pitch
A founder's second brain. It turns the Owner's judgement into **explicitly delegated, evidence-based decisions**. The AI decides routine credit requests within limits the Owner sets, asks Staff for missing facts, and sends only genuine exceptions to the Owner.

## The problem we solve
Today every credit or payment-extension request ends with the Owner.
- **Moving the queue doesn't help:** shifting the approval click to Staff just moves it, and Staff don't want personal responsibility for credit decisions.
- **What Nucleon does instead:** it removes *unnecessary* human decisions. The Owner defines what is delegated, and the agent acts inside those bounds.

## How a request is handled now (built & tested in isolation)
1. **Staff tell the assistant in chat**, for example: "Bayview asks to move DEMO-301 to 10 Nov."
2. **The agent gathers the facts** with tools: records, completeness, and comparable reviewed cases from other customers.
3. **The agent recommends** approve, decline or escalate, with its reasoning.
4. **Nucleon's backend code checks the Owner's delegation policy** and returns one of four results:

| Result | When | What happens |
|---|---|---|
| **Approved by the agent** | Inside every bound, evidence verified, agent recommends approve | Takes effect at once inside Nucleon (for example, the invoice's due date moves). No Staff or Owner click. |
| **Information needed from Staff** | A fact Staff can provide is missing (for example, a deposit or business identity) | The card shows a button. Staff confirm **facts** (not approval) on a Nucleon page, and the backend re-checks at once. |
| **With the Owner for review** | Outside the policy, unknown or incomplete records, policy paused or advisory, or the agent didn't recommend approval | The Owner decides, with the agent's recommendation and evidence |
| **On hold by policy** | A held customer, or evidence that contradicts the records | The Owner may grant an exception |

The agent **never declines on its own authority**. That's an open product question, so a request that doesn't qualify goes to the Owner, never to an automatic "no".

## Three separate questions (never one confidence score)
1. **Evidence sufficiency:** is what we know verified? This is decided by the records or by Staff confirming on a Nucleon page, never by what the model says.
   - Each deposit carries an explicit **verification level**:
     - **recorded payment** (in the ledger);
     - **checked by Staff in the bank account** or **on a document** (not a ledger payment);
     - **reported by the customer** (never counts).
   - Staff-checked deposits count only up to a limit the Owner sets.
   - Nothing Staff confirm becomes a ledger payment.
2. **Business risk:** is this within the Owner's limits?
   - limits per decision, per customer in total, and across all autonomous approvals in 30 days;
   - days, anything else overdue, late history, unusually large amounts, and held customers.
   - An unknown amount is **never** treated as zero.
3. **Demonstrated reliability:** how does the current policy compare with the Owner's decisions on a **held-out evaluation set** of reviewed cases? In the POC this set is **fictional (simulation)**.

## The Owner's controls (built)
The Owner page `#/delegation` in Nucleon:
- **Mode:** advisory (the agent only recommends) or delegated.
- **Limits:** the most one decision may add, and the most a customer may owe after it.
- **Extensions:** on or off, and the maximum days.
- **New-customer trial credit:** off, or limited (maximum exposure, minimum deposit %, maximum terms). The **Advanced** section has proportional evidence rules, held customers, the unusual-size multiple and the track-record requirement.

Rules that apply to every change:
- **Versions:** every change is a new **version**, and every decision records the version it was made under.
- **Pause:** one click.
- **Who can change it:** only the Owner, signed in as a person in the browser. The AI, Staff and service connections can't.

**Suggestions only.** Nucleon can *suggest* a policy change from the reviewed cases, for example raising the trial cap. Nothing changes until the Owner saves a new version, and limits are never relaxed automatically.

## Decision memory (built, minimal)
Every case records:
- the request, the evidence and how it was verified;
- the agent's recommendation and reasoning;
- who decided and under which authority (agent under policy vN, or the Owner);
- Owner feedback (agree or disagree), any override, and the repayment outcome where the records show it.

**Comparable cases** come from other customers' reviewed cases and are always labelled *"analogy, not this customer's history"*. The evaluation cases are kept separate from the examples.

## Architecture (what runs where)
- **LibreChat** is the chat front end: custom rc3-test image, unchanged in this round. It calls the **Nucleon Lab MCP server**, which calls **Nucleon Records**: the business records, rules and database.
- **The model** is Qwen3.5-35B-A3B in LM Studio, running locally. It reasons and recommends. **It cannot grant itself permission, change the policy, or set a status.**
- **Cards** (MCP-UI) show the backend's own status and Key Facts: original due date, as-of date, requested date, extension days and days overdue. They show the three dimensions and labelled comparables. Each card states "Nucleon sent nothing to the customer."
- **Existing safeguards are kept:**
  - financial completeness;
  - confirmed versus unconfirmed amounts;
  - durable idempotency (retries don't double-decide);
  - the Phase B human-confirmed request flow;
  - audit events.

## Deliberately not built (roadmap)
- **Agent declines:** the agent never declines on its own authority (open question).
- **Outbound actions:** no emails to customers and no order fulfilment. Staff tell the customer.
- **Owner Console:** the full redesign and "Decision Handling" analytics. Only minimal counts exist.
- **Learning:** no ML training or retraining pipeline. "Learning" is decision memory plus Owner-approved policy versions.
- **Accounts:** no personal accounts. Roles are Staff and Owner, with shared access codes.
- **Deployment:** the normal local M3 environment runs this version and is browser-verified there. There is no M6 deployment.

## Honest claims
- **Say:** "Built and tested on an isolated test stack with fictional data."
- **Don't say:** that it is validated on NTK data, that it has measured accuracy, or that it is deployed.
- **Track-record figures** (for example "Owner approved 5 of 6") are a **simulation on fictional cases**.
- **No real Owner approval history** can be derived from the NTK ledger.
