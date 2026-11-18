# Decision log

Updated on 16 October 2026 with Sandeep’s agentic AI/Week 7 requirements and Hanting’s HTML-maintenance instruction. Owner statements in the 15 October meeting remain reports by Hoang, not independently confirmed here.

## D001 — Local-first development

- Status: confirmed by Hanting; not a claim of a team vote.
- Date: 15 October 2026, 18:46 Sydney, conversation instruction.
- Decision: build and experiment with the MVP on Hanting’s computer or home Linux server. Defer cloud hosting decisions.
- Reason: prioritise development and product validation rather than long-term operating infrastructure.
- Supersedes: the immediate hosted-stack recommendation in Claude’s architecture proposal; it does not invalidate the proposal’s reusable data/workflow ideas.

## D002 — Use this repository as the shared project record

- Status: established at Hanting’s request on 15 October 2026; team adoption to confirm.
- Decision: version current state, sources, decisions and meeting notes alongside future code. A portable meeting view was initially generated from the same state file; its maintenance stopped on 16 October (D005). Current memory remains in Markdown.
- Reason: reduce dependence on individual memory and separate assistant chat histories.
- Boundary: AI sessions and offline page notes do not synchronise themselves. Reviewed file updates must be committed.

## D003 — Draft evidence-based, measurable success criteria

- Status: meeting agreement to do this work; no numeric target adopted.
- Date/source: 15 October meeting, 33:48–41:46.
- Agreement: Chris drafts criteria for review. Examine owner adoption and time saved while counting new interaction/maintenance work; actual baseline and target need evidence.
- The three questions discussed: work removed/faster, new work introduced, information reused.
- Boundary: 10 minutes, half an hour and an hour were examples, not requirements. No complete comparison protocol was adopted.

## D004 — Prepare realistic fictional scenarios for onboarding/PoC

- Status: agreed next-step direction; detailed ownership and review plan incomplete.
- Date/source: 15 October meeting, 23:24–26:16.
- Agreement: use research and owner decisions/reasons to prepare plausible fictional cases for onboarding and demonstration.
- Boundary: synthetic demonstration does not establish real-world accuracy. No model-training method or guaranteed learning period was selected.

## D005 — Stop maintaining the HTML brief

- Status: explicit Hanting instruction, 16 October 2026.
- Decision: save current requirements and decisions in project records. Do not spend further time updating the HTML because the team does not use it.
- Implementation: default generator writes Markdown only; existing HTML and template remain unchanged as archived snapshots.
- Supersedes: instructions to regenerate both Markdown and HTML. It does not discontinue shared project memory.

## New external course constraint — agentic AI and Week 7 demo

- Source: two Sandeep announcements and the supplied PoC template, recorded 16 October in `COURSE-REQUIREMENTS.md`.
- Agentic AI must provide substantial value, ideally as the core feature. Specify trigger, perception, decisions, tool actions, outcome and human approval points; a generic chatbot/dashboard alone is insufficient.
- Week 7: seven minutes total, five-minute Q&A, four content slides plus title, roughly three minutes slides and at least four minutes demo, backup recording, clear live/mocked disclosure and accessible PROMPTS.md.
- This constrains next decisions; it is not a claim that the team has selected or implemented a specific agent workflow.

## Still open — do not represent these as decisions

- Pilot business and source of the reported credit-approval bottleneck.
- First request type and substantial agentic work-saving mechanism, including trigger, tools/actions, final output and existing user channel.
- Whether the first pilot’s dominant bottleneck is information, judgement or authority. Hoang’s new report supports an authority/responsibility issue for some experienced staff; it remains a report to verify.
- AI autonomy and employee/owner approval boundaries.
- Whether the agent may ever recommend approve/decline. That needs an owner-confirmed approval policy and an evaluation method that includes refusals; recommendations are disabled in the prototype until then (E003).
- Application stack, database and model.
- Verified decision labels, including approved extensions versus unapproved late payments.
- Complete due dates and scenario-review ownership. Concrete action commitments are now in the meeting minutes; old backlog dates are not automatically reaffirmed.
- Whether any implementation is reused for INFS3701.

## Record future decisions

For each: ID; status; date; participants/decision-maker; decision; reason/evidence; consequences; superseded decision if any. Keep rejected or superseded decisions with their status instead of erasing history.

## 16 October — first-build evidence reconciliation

- Hanting asked to start by organising project facts and open questions after checking the latest announcements.
- Added `FACTS-AND-OPEN-QUESTIONS.md` with source/status boundaries, evidence needed, existing contacts and build dependencies.
- Updated current state with Hoang's later request for Saturday 17 October data delivery; acceptance and completion are unverified (S13).
- No pilot, MVP request type, stack, model, autonomous authority or numeric success target was adopted. Existing meeting commitments were not reassigned.

## P001 — Minimum extension workflow and interfaces v0.1

- Status: development proposal prepared at Hanting's request on 16 October; not a confirmed team/owner scope or implemented system.
- Candidate: one existing invoice payment-extension request, received through disclosed prototype intake.
- Agent work: extract/resolve inputs, retrieve facts and confirmed notes, create focused clarification and owner-approval tasks, then save a reply draft after the owner's decision.
- Prototype boundary: owner commits all financial outcomes; no customer sending, accounting writeback or automatic rule publication.
- Contracts: language/framework-neutral JSON records, six backend modules, tool allowlist, state/version/idempotency rules and error fallback in MODULE-INTERFACES.md.
- Rationale: narrow a date-based candidate from S9 while business attribution, clean data, terms and delegation remain unconfirmed. MINIMUM-FLOW.md defines four fictional acceptance scenarios.
- Replaces: the broader three-demo-path proposal in current-state MVP notes for this draft only. Does not supersede D001–D005 or resolve Q01–Q08 as business facts.

## E001 — Local fictional workflow skeleton

- Status: implemented engineering scaffold at Hanting's request on 16 October; not team approval of a production stack or owner delegation.
- Choice: Python standard-library HTTP server, SQLite and plain browser JavaScript so the first end-to-end flow runs without package installation.
- Implemented: one fictional invoice, request/event persistence, internal clarification, code-calculated dates/balance, server-assigned demo sessions, owner-only decisions, stale-evidence/idempotency guards and saved template replies.
- Mocked: deterministic extraction and step sequence; no LLM/model prompts, training or financial predictions. Tool-action records describe mock-runner/code steps, not model-selected calls.
- Limits: one business/customer/invoice, synchronous local processing, no actual customer sends or accounting writes. prototype/README.md records differences from the wider interface proposal.
- Validation: 13 HTTP workflow checks pass; UI JavaScript syntax checked. No browser binary was available for actual browser or visual QA.
- Pending: real model adapter, realistic language handling and business/owner validation, without turning the fictional fixture into evidence about NTK or Art of Gelato.

## E002 — Local Gemma agent for case preparation and home-server test deployment

- **Status:** implemented engineering change in the repository owner's (unitylht) development session on 16 October. It is not team approval of a production stack or model, and not owner delegation.
- **Choice:**
  - Use the model already served on the home server through its existing loopback gateway: `gemma-4-26b-a4b-it-heretic-zh-rp`, a community Gemma 4 26B-A4B fine-tune (GGUF Q4_K_M) in LM Studio.
  - Call it through a small OpenAI-compatible adapter configured outside business logic.
  - Use native tool calling plus strict JSON-schema extraction, with no agent framework, multi-agent design or retraining.
  - This choice was one of convenience. Whether this model suits the team remains open.
- **Implemented:**
  - In live mode, the model extracts the request, identifies missing or ambiguous information, selects and invokes the six permitted tools, writes a source-linked owner brief and creates the clarification or approval task through validated application functions.
  - Code keeps lookups, money/date calculation, permissions, state, persistence and the reply template.
  - Inference runs outside the application lock, with durable run records, one running run per request, version and evidence re-checks before commit, and restart recovery.
  - Mock and unavailable modes remain. A model failure produces a disclosed manual fallback (`aiStatus=failed`).
  - Fixture v2 adds a second fictional customer and two invoices so ambiguous matches occur; DEMO-101 is unchanged.
  - Writes are restricted to an explicit origin allowlist; behind HTTPS the session cookie is Secure.
- **Deployment:**
  - https://nucleon.dracooz.top, behind the server's existing Caddy HTTPS ingress, running as LaunchAgent `local.nucleon.prototype` with a loopback-only backend on port 8620.
  - SQLite database and log outside Git, owner-only permissions. Details in DEPLOYMENT.md.
- **Validation, 16 October (fictional data):**
  - Unit suite: 39/39 deterministic tests (the original 13 plus 26 new).
  - Real-model integration: 8/8 scenarios in two full runs, covering natural/relative/ambiguous dates, an ambiguous customer, multiple open invoices, an overdue invoice and prompt injection.
  - Deployed HTTPS checks:
    - approve 23/23, restart 7/7, stale evidence 11/11;
    - change-date 12/12, decline 11/11, clarify 15/15;
    - unavailable-model fallback 9/9, invalid-output fallback 9/9;
    - crash recovery 11/11.
  - Headless Chromium browser checks: live 17/17, fallback 15/15.
- **Not established:** business accuracy, quality of the model's suggestions, owner agreement or time savings. The model suggested "approve" in every complete fictional case, and that suggestion carries no authority.
- **Pending:**
  - owner/team scope validation;
  - model-written reply drafts (template retained);
  - real data import;
  - value measurement;
  - a decision on the team's model and stack.

## E003 — Code-rendered brief facts and disabled recommendations

- **Status:** engineering change in the repository owner's (unitylht) development session on 16 October 2026, made in response to an independent review. It is not an owner policy decision.
- **Problem:** in extension-v0.2 the model wrote the owner brief's facts as prose. Checks only recognised whether values and reference IDs existed, not what a sentence meant or whether its citation supported it. Three incorrect briefs were reproduced and accepted:
  1. "10 days overdue and 0 days extension", when the real facts were a 10-day extension and 0 days overdue;
  2. current and requested dates swapped;
  3. "never missed a payment and is a low-risk borrower", citing `invoice:DEMO-101`.
- **Decision (format `brief-v2`, prompt extension-v0.3):**
  - Application code builds the material facts as typed fields from trusted tool results: outstanding amount, original due date, current due date, requested date, as-of date, extension days and overdue days.
  - Each fact records its exact source field, the owner decision that set it, or its calculation inputs. Code also renders the summary sentence.
  - The model's brief contribution is limited to verbatim customer quotes. Each quote is checked against the message and kept as an attributed, unverified customer statement.
  - A small guard rejects or removes the remaining model prose (clarifications, extraction notes) if it states amounts, credit judgements, decisions or confidence.
  - All three counterexamples have regression tests.
- **Recommendation boundary:**
  - `suggestedOption` is always `null`, enforced by the backend. Suggestion fields a model still sends are stripped and recorded as `suggestion.suppressed`; decisions no longer copy a suggestion; the UI says "No recommendation".
  - Reason: there is no confirmed owner approval policy or validated recommendation method, and v0.2 suggested "approve" in every complete fictional case.
  - Historical v0.2 suggestions are kept, labelled historical and unvalidated.
- **Compatibility:**
  - The stored format is versioned. Older v1 briefs are labelled `brief-v1-legacy` at read time and never rewritten.
  - Production held 0 requests before the deploy and was backed up anyway.
  - Rollback was tested: the previous release reads and decides `brief-v2` records.
- **Other fixes:**
  - field-specific validation errors that keep what was typed, with clarification answers checked immediately;
  - a model-status endpoint and a 30 s request socket timeout;
  - clearer state labels, Sydney-time timestamps, stable idempotency keys on retries, and backup/clone-db commands.
- **Validation, 16 October (fictional data, deployed commit `e4556a7`):**
  - Unit suite: 51/51.
  - Real model: 9/9 scenarios in each of three v0.3 runs, including a customer credit claim and prompt injection, with 0 blocked calls and 0 attempted recommendations.
  - HTTPS (each scenario on an isolated database):
    - approve 28/28, restart 7/7, stale evidence 11/11;
    - change-date 15/15, decline 14/14, clarify 20/20;
    - unavailable fallback 10/10, invalid-output fallback 10/10;
    - legacy database 11/11, crash recovery 11/11.
  - Browser (headless Chromium): live 24/24, fallback 19/19, legacy 7/7.
  - Latency: a complete case took 7–13 s, down from 11–17 s.
- **Not established:** business accuracy, owner agreement or time savings.
- **Pending (team/owner):** whether recommendations are wanted at all, and under what owner policy and evaluation. Also still pending: the questions recorded under "Still open".

## E004 — Redesigned case desk and demo console

- **Status:** engineering and design change in the repository owner's (unitylht) development session on 17 October 2026. It is not an owner policy decision.
- **Problem:** the interface read like a development report.
  - There were four bands of notices before any case content.
  - Every saved case was listed as "DEMO-101 · date".
  - The owner's decision form was the seventh of eight sections on a page about 2,500 px tall.
  - Model and tool diagnostics sat between business facts.
- **Design decisions:**
  - **Layout:** one list beside one case. Each role sees its own work first ("For you"). A one-line headline says what happens next, written for the person reading it. A single raised panel holds the only action: decide, answer the agent, copy the reply, or watch progress.
  - **Due-date timeline:** every prepared case opens with one, drawn from the code-calculated facts (today, current due date, requested date, outcome, days late). It is the single bold element. Everything else stays quiet.
  - **Customer words:** set in a serif, with the agent's verbatim quotes underlined in place. The rest of the interface uses one sans family (IBM Plex, self-hosted, SIL Open Font License).
  - **Collapsed details:** evidence with sources, a plain-language activity history and technical run details are folded below. A case prepared without AI, by the test agent or by an earlier version still says so under its title.
  - **Wording:** sentence case, plain verbs, contractions. The environment note appears once, in the footer, instead of on every case.
- **Demo console:**
  - **Access:** an operator code exists only when `demo.enabled` is set and the data are fictional. Production is explicitly enabled.
  - **Reset** takes a backup, then clears cases, events, runs and retry keys and puts back the original invoices and due dates. Sign-ins, codes, model settings and configuration stay. A reset epoch stops a model run that started earlier from writing back.
  - **Undo and Restore** save the replaced data first and resume any pending work.
  - **Deliberately minimal:** no confirmation step, because every reset is recoverable.
- **Sessions:** one cookie per role, with the role named on each request, so a presenter can switch between staff and owner without re-entering codes. The operator code cannot do case work.
- **Decision record:** it now stores `approvedExtensionDays`, calculated by the server. When the owner approves a different date, the page shows that number instead of working out a day count itself.
- **Kept unchanged:**
  - the agent contract and prompts (extension-v0.3, brief-v2);
  - code-rendered facts and the disabled recommendations;
  - owner-only decisions;
  - stale-evidence, duplicate-write, persistence and legacy-record protections.
- **Validation, 17 October (fictional data, deployed runtime `c966a23`):**
  - Unit suite: 66/66 (15 new).
  - Real model: 9/9 scenarios on `2b4b58d`. The agent code has not changed since; every later HTTPS and browser run also used live Gemma. One call queued for about 101 s behind another client of the shared model.
  - HTTPS:
    - approve 30/30, restart 9/9, stale 13/13;
    - change-date 17/17, decline 16/16, clarify 22/22;
    - console 27/27, unavailable fallback 12/12, invalid-output fallback 12/12;
    - legacy 13/13, kill -9 recovery 8/8.
  - Browser (headless Chromium 156, including 390 px phone width and console errors): live 27/27, fallback 9/9, legacy 8/8.
  - Rollback to `23e6bdb` was checked on new-release data.
  - The production case created on 16 October (waiting for the owner) was kept, and a backup was taken before each deploy.
- **Not established:** usability with real staff or owners, accessibility beyond keyboard focus, labels and contrast checks, business accuracy, time savings.

## P002 — Setup and records: onboarding, imports and owner knowledge

- **Status:** proposal, v0.3 (18 October 2026). Prepared in the repository owner's (unitylht) development session. **Not a team decision or owner policy.**
  - On 18 October Hanting selected the Slice 2 engineering approach: D1 and D2 as proposed, D8 and D12 adjusted, the sample-loading rules, and the retained Slice 2 items. Slice 2 was then built (E006).
  - Slice 2 was deployed to the shared practice instance (E007). Stage 3 steps were then built on a separate branch, which is not merged or deployed: payments and payment import (E008), then opening balances, completeness statements and exact amounts (E009).
  - The rest of the Stage 3 design (D3–D6), the business questions (B1–B11) and the final additional-credit scope remain open.
  - This establishes no business policy.
- **Document:** [SETUP-AND-RECORDS-PROPOSAL.md](SETUP-AND-RECORDS-PROPOSAL.md).
- **Kept from v0.1 at the reviewer's request:**
  - one Records area serving both onboarding and maintenance;
  - explicit loading of practice data;
  - unknown-state handling;
  - comparing imports document by document.
- **v0.2 adds:**
  - whether an invoice is already included in an opening balance;
  - coverage statements with a scope (customers and record types), separate from last activity;
  - revert rules: restoring versions, blocked and needs-review cases, and decisions never undone;
  - prerequisites before any "exact outstanding" claim;
  - three distinct payment-term actions, each stating which invoices it covers;
  - an optional up-front entry point for existing owner knowledge;
  - the boundary between extensions and additional-credit requests;
  - staged implementation (slice 1 done, slice 2 proposed, stage 3 later).
- **Scope boundary:** the built workflow covers extensions of existing invoices only. It must not be described as handling requests for additional trade credit (section 1.1 of the document).
- **Reopens:** partial payments and ledger imports, which MINIMUM-FLOW v0.1 deferred. This is a proposal only.

## E005 — Unknown due dates and explicit sample data

- **Status:** engineering fixes made in the repository owner's (unitylht) development session on 17 October 2026, at Hanting's instruction to fix these first in small, verified changes. They are not owner policy decisions.
- **Branch:** `feat/setup-records-20261017`. **Not deployed.**
- **`62a0cd6` — invoices with no due date.**
  - **Before:** such an invoice crashed `calculateExtension`. The no-AI fallback crashed the same way, so the case stayed in "Preparing" indefinitely (verified by running it). Approving such an invoice also broke later evidence reads, and the date checks returned a generic 400.
  - **Now:** the due date, extension length and days overdue are explicit unknowns (fact kind `unknown`, value `null`, with a reason). The owner's earliest allowed date is today, and `approvedExtensionDays` is `null`. The page says "Not on record", "Not calculated" or "Unknown".
  - The prompt text is unchanged (extension-v0.3); PROMPTS.md describes the new tool result.
- **`0465394` — explicit sample data.**
  - The fictional sample loads only with `--sample-data`, `"sampleData": true`, or the operator's console reset.
  - A newer sample replaces stored records only when they are the sample (`dataMode: "fictional"`).
  - An empty database reports `hasRecords: false`, refuses new requests (`409 NO_RECORDS`) and explains why on the page.
- **`7d95e33`:** a targeted ignore rule for the private NTK (Nutek) workbook. It was never committed.
- **Validation (17 October):**
  - Unit suite: 76/76 (10 new; each watched failing first, except one guard for kept behaviour).
  - Live Gemma on scratch databases:
    - 3/3 unknown-due-date cases: two reached the owner with the unknowns stated, one asked staff for the date. 0 rejected calls; 6–9 s each.
    - One message that also asked for more credit: only the date was handled. The credit request reached the owner as a quoted "other request"; the amount guard removed the limit part of the model's note.
  - Headless browser: the owner case with an unknown due date, and the empty state. No console errors while the server ran.
- **Before deploying:** add `"sampleData": true` to the server's `production.json` (DEPLOYMENT.md). It was not changed in this session.
- **Remaining risk:** a fallback failing for a reason other than a missing due date can still leave a case in "Preparing". Slice 2 of P002 adds a last-resort state.
- **Not established:** usability, business accuracy and time savings.

## E006 — Slice 2: setup, records, CSV import and revert

- **Status:** engineering change in the repository owner's (unitylht) development session on 18 October 2026, following Hanting's selection of the Slice 2 approach (P002 v0.3).
  - It is not owner policy.
  - It covers payment extensions on existing invoices, not requests for additional trade credit.
- **Branch:** `feat/setup-records-20261017`, commits `f4fff2f` to `19bfafb`. **Not pushed, not deployed.**
- **Built:**
  - **First-run setup.** Real, practice empty, or practice with the sample. The explicit workspace always beats `sampleData`.
  - **Settings.** Currency, decimal places and time zone; real-clock "today" outside the sample.
  - **Setup checklist** in tiers, with Skip.
  - **Manual customers and invoices.** Identity is (customer, number), and numbers may repeat across customers. An optional amount still owed always carries its as-of date.
  - **Corrections** as versions with a reason. **Removal** with blocking and review rules.
  - **Owner notes** scoped to the business or a customer: the owner's are confirmed, staff's are drafts. Business-wide notes reach the brief.
  - **Invoice-list CSV import:** preview categories, saved column mappings, as-of dates, conflicts and resolutions, revert with blocking and review.
  - **Agent and cases.**
    - "Stated as of" and "not recorded" amounts. Days overdue only from the sample or a statement dated today.
    - Code-written explanation for a stated zero.
    - Explicit staff choice when an invoice number belongs to several customers.
    - `preparation_failed` with **Prepare again** when even the fallback fails.
- **Fixed on the way:** after a server restart ended the sessions, the case desk polled `GET /api/requests` in a tight loop (an existing bug). It now shows the sign-in screen.
- **Validation, 18 October (fictional data):**
  - Unit suite: 113/113, 37 new. New behaviour was watched failing first, except 4 parser unit tests written after the parser.
  - Real model (Gemma): the existing 9 scenarios, 9/9. Seven new checks on scratch databases, 7/7:
    - a shared number asks staff to choose, then resolves;
    - a stated amount, with no overdue claim;
    - a stated zero, explained by code;
    - unknowns stay unknown;
    - the fallback with a realistic invoice number. Its basic parser reads only `DEMO-###`, so it asks staff for the number.
  - Headless browser, on a scratch database: setup, entry, import, choice, decision and revert. No overflow at 390 px.
  - **Migration**, on a copy of the deployed database: recorded as practice; sample and cases unchanged; both cases waiting for the owner still current.
- **Before deploying:** add `"sampleData": true` to the practice instance's `production.json` only (DEPLOYMENT.md). A database used for real records must not carry it.
- **Limitations:**
  - **Coarse re-preparation.** After any records change, every case waiting for the owner is prepared again, because evidence versions cover the whole document. This costs model time when there are many pending cases.
  - **Fallback parser.** The no-AI fallback reads only `DEMO-###` invoice numbers.
  - **Not built yet:** payments, opening balances, coverage statements, structured terms, ledger or XLSX import, decision-time capture, user accounts.
  - **Not established:** usability with real staff or owners, business accuracy, time savings.

## E007 — Slice 2 deployed to the shared practice instance

- **Status:** deployment on 18 October 2026, about 01:16 Sydney, at Hanting's instruction. It is not owner policy.
- **Release:** `89b92d8` (branch `feat/setup-records-20261017`, pushed; the remote commit matched before the deploy). Previous release: `d59af7a`.
- **Before deploying:**
  - **Outgoing changes:** 24 files, no binaries, no credentials or access codes. None of the 44 customer names or 256 accounting document numbers from the private NTK workbook appear in them.
  - **Backups:** database and both config files backed up.
  - **Rollback:** tested by running `d59af7a` against a migrated copy of the database.
  - **Config:** `"sampleData": true` set only in this practice instance's `production.json`.
- **Result:**
  - The production database was recorded as a practice workspace, with the sample and all 3 cases unchanged.
  - Checks through the public URL (DEPLOYMENT.md): production read-only 14/14, practice 24/24, empty workspace 16/16, real workspace 23/23, existing HTTPS scenarios 79/79, existing browser check 27/27.
  - Live Gemma prepared every case in these checks.
- **Rollback procedure:** DEPLOYMENT.md, "Earlier release: Slice 2".
- **Seen, not changed in the deployed release:** the sample's invoices have no stored invoice date or amount. An import that supplies them therefore shows a *conflict*, where an *update* would be the better result. This is safe (a person chooses) and is noted for the next branch.
- **Not established:** usability with real staff or owners, business accuracy, time savings.

## E008 — Stage 3 foundation: records in tables, payments and payment-list import

- **Status:** engineering change made overnight on 18 October 2026, in the repository owner's (unitylht) development session, at Hanting's instruction. It is not owner policy, and covers extensions of existing invoices only.
- **Branch:** `feat/records-payments-20261018`, from `d32dd49`, commits `1104a63` to `5c42ea4`, plus this record. **Pushed. Not merged, not deployed:** the shared instance still runs `89b92d8` (E007).
- **Built:**
  - **Records in tables** (`1104a63`, `27897ba`).
    - Customers, invoices, notes, payments and allocations are table rows, each keeping its id, version, provenance and history.
    - At first start, the records document is copied into the tables once, checked to be lossless, and then frozen. The tables are the only writable source. The document shape is now only a read view, for the agent and for imports.
    - Saving never deletes a record.
    - Evidence versions are per customer, so a change re-prepares only that customer's waiting cases.
    - A case whose stored version differs only in format is re-stamped (logged), not run again.
    - A backup from before the tables is migrated when restored.
    - Startup stops, with an explanation, if the frozen document changed after the move (an earlier release ran on the database).
  - **Import fix** (`d6aa017`): a date or amount the records lacked is an *update*, not a *conflict*. This was seen during the Slice 2 deploy (E007).
  - **Payments and explicit allocations** (`33c77b2`, `d0b00cc`).
    - **Recording.** Customer, date received, amount and an optional reference. A possible duplicate needs a person to confirm it is a different payment: the same reference, or, with no reference, the same date and amount.
    - **Allocating.** Only to the same customer's invoices, and only up to what is left on both the payment and the invoice.
    - **Corrections** keep versions. A payment cannot be corrected below what is allocated from it, nor an invoice total below what is allocated to it.
    - **Removal** is blocked while allocations depend on the record. Removing an allocation that cases use needs confirmation; decided cases are flagged, never changed.
  - **What the records support** (code, never the model):
    - **Per invoice:** "settled by allocated payments", or "at most X". X is the total, or a stated amount minus the payments allocated after its date.
    - **Per customer:** recorded payments, unallocated money, and a recorded net labelled "a difference of records, not what is owed".
    - **Absent payments** are "not recorded", never "unpaid". Days overdue are not calculated when payments exist but are not confirmed complete.
    - Nothing is called exact. No FIFO, payment terms, credit limits or authority are inferred.
  - **In cases:**
    - The owner sees "At most AUD 400.00", with code-written open points: payments allocated, unallocated money, recorded net.
    - An invoice that allocations fully settle goes back to staff, with the reason written by code.
  - **Payment-list CSV import** (`41aaadc`). The file is declared an invoice list or a list of payments received. Payment rows use the same preview, saved mappings, provenance and revert as invoice lists.
    - **Identity:** (customer, reference). With no reference, (source, customer, date, amount, occurrence in the file). Re-imports and overlapping exports therefore add only what is new.
    - **Ambiguity goes to a person.** Two cases: a reference repeated within a file with different values, and an unreferenced row that looks like a payment already recorded from elsewhere. The choices are: same payment, a different one, or leave the row out.
    - **An invoice column is an explicit allocation**, to that customer's invoice only and within what is left. The rest stays unallocated, with a note. A reference to another customer's invoice is never allocated.
    - **A person's correction wins** over a later import unless they choose to replace it.
    - **Revert** is blocked while money from the import has been allocated later.
  - **Fictional sample files** in `prototype/samples/`, and a demo script ([DEMO-SCRIPT.md](DEMO-SCRIPT.md)).
- **Validation, 18 October (fictional data):**
  - **Unit suite:** 140/140, 27 of them new. New behaviour was watched failing first, except one test that characterises the existing stale-preview refusal for payment imports. Fixtures cover partial payments, unreferenced payments, overpayments, duplicate references, corrections, overlapping exports, stale previews and revert dependencies.
  - **Migration**, on fresh copies of the deployed database (never the live file): lossless, and all 3 cases kept with their status. The cases waiting for the owner were re-stamped, not run again, and could still be decided. A second start passed the new guard.
  - **Real model** (Gemma, prompt extension-v0.3 unchanged): 12/12 scenarios, 0 rejected tool calls, 5–11 s each.
    - The 9 existing scenarios behaved as before.
    - Three new payment scenarios: a partly paid invoice reached the owner with "at most" only; a settled invoice went back to staff with the code's reason; unallocated money left the amount unknown and was shown as an open point.
    - The demo sequence also ran end to end with live Gemma: the three sample imports, then a request on the shared INV-1001, a staff choice, and "At most AUD 400.00".
  - **Headless browser**, on local scratch servers: payment entry, duplicate confirmation, allocation and the positions on the Records page; the payment-import preview with allocation notes, and the overlapping export; the owner's "At most" brief (screenshots 12 and 13).
- **Not built:**
  - opening balances and inclusion (P002 8.1), and coverage statements (8.2). So the system can never claim an exact outstanding amount;
  - structured payment terms (9.3);
  - ledger-account shapes and XLSX; OCR and integrations;
  - decision-time capture (6.4);
  - user accounts.
- **Known limits:**
  - **Allocation form.** It allocates to one invoice at a time; the API accepts several.
  - **Review choices.** In an import preview, a review choice (same, different, leave out) can't be changed once it has been resolved; to change it, upload the file again.
  - **Payment-import revert.** It waits until a person removes the allocations made after the import.
  - **Whole-records loading.** Each operation loads all records. That is fine at fictional sizes; it has not been measured on a real business's volume.
  - **Fallback parser.** The no-AI fallback still reads only `DEMO-###` numbers.
- **Before deploying Stage 3** (a team decision; not done):
  - The first start moves the database into tables.
  - From then on, a code-only rollback to `89b92d8` would show the records as they were at the move. If that release then saved a records change, Stage 3 would refuse to start.
  - Back up the database first. A rollback restores that backup, and loses any changes made since.
  - Rehearse on a fresh copy, and keep `sampleData` on the practice instance only.
- **Not established:** usability with real staff or owners, business accuracy, time savings. A passing suite does not establish any of these.

## E009 — Stage 3 records foundation: statements and payments, opening balances, completeness, exact amounts

- **Status:** engineering change on 18 October 2026, in the repository owner's (unitylht) development session, at Hanting's instruction to continue the records foundation. It is not owner policy, and covers extensions of existing invoices only.
- **Branch:** `feat/records-payments-20261018`, commits `fbc952f` to `74c6a6b`, plus this record (`e7f5f52`). **Pushed. Not merged, not deployed:** the shared instance still runs `89b92d8` (E007).
- **Checked first: where stated balances meet payments.** A Slice 2 statement "X still owed as of D" may already reflect payments made on or before D. Three defects were found:
  - the sample's figure has no as-of date, so every payment allocated to it was subtracted again;
  - dated statements silently assumed that earlier payments were included;
  - a later statement showing *more* owed was imported as an update.

  Now:
  - payments after D come off X;
  - for payments on or before D, the inclusion is *reconciled* (the invoice amount less them is exactly X), a person's answer, or unresolved. An unresolved payment is not taken off, so "at most" stays an upper bound;
  - answers belong to the statement they were given about;
  - contradicting evidence is a conflict, never settled;
  - a payment after D can only be allocated within what the statement leaves;
  - a later, higher statement is an import conflict;
  - reverts list the answers that will stop applying.
- **Built** (P002 §8.1–8.3). Engineering choices are listed below.
  - **Opening balances.**
    - Each is per customer: owed or held in credit as at a date, with its source, who entered it, and an optional "stated to have no credits". Corrections are versioned.
    - Invoices and payments dated on or before the as-at date are *included*, *missed* or *unresolved*; unresolved is the default. Later records are new activity.
    - Manual entry asks the question; answers keep their own history.
    - Invoices whose amounts at the as-at date add up exactly to the balance are reconciled.
    - Included invoices adding up to more than a net balance imply credits. That is only a conflict if the balance was stated to have no credits.
    - The customer balance is the opening balance + new activity + missed records, with unresolved records shown as "plus up to" or "minus up to". It is always presented as the whole account, never as one invoice's settlement.
  - **Completeness statements.**
    - Each names customers (or all), record types and a period, with how the confirmer knows, who confirmed it and when. Only the owner confirms, by hand or with an import.
    - Completeness is never derived from entries, file dates or last activity; last activity is shown separately.
    - "Complete to" is the unbroken run from the customer's base. Gaps stop it; overlaps extend it.
    - A record that enters or leaves a confirmed period afterwards (added, removed, reverted, or corrected in or out) makes the statement stop holding for that customer only.
    - Reverting an import removes its statement after review.
  - **Exact amounts.** An exact amount still owed, as of the payments-complete date, appears only when all of P002 §8.3's prerequisites hold (adapted, see the choices):
    - the invoice amount is known and consistent with any statement;
    - its starting amount is known: it is dated after the base, or it is part of the opening balance with what was owed on it then;
    - payments are confirmed complete from the base;
    - every payment in the period is allocated or marked "not for an open invoice";
    - nothing about the customer is unresolved.

    Otherwise the reasons are given in plain words. The owner sees the calculation steps, the as-of date and the statement relied on. Days overdue are stated only when records are complete to today.
  - **Decided cases.** A decided case is flagged whenever what its invoice shows changes, by any route, with the amount before and after. The decision and its stored snapshot never change. Decisions made before this release get a baseline at the first start.
  - **Records page.** Opening balances, a "Needs attention" list, completeness statements and the owner's form, the exact / at most / stated amount with its reasons, and the "not for an open invoice" marking.
  - **Upgrade guard and rehearsal.** `deploy/rehearse_stage3_upgrade.py` (see Validation).
- **Engineering choices: for review, not business policy.**
  1. One active opening balance per customer. A later one is a correction, after which answers given about the earlier as-at date stop applying.
  2. Reconciliation by exact equality of amounts counts as evidence of inclusion, for opening balances (P002 §7, step 9, extended to manual records) and for invoice statements (new).
  3. Only the owner confirms completeness. Staff and owner may answer inclusion questions and mark payments "not for an open invoice", attributed, like allocations. This is interim until B7 and B4 are settled.
  4. Credit notes are not recorded in this version. The owner's statement that payments are complete explicitly includes "no credit notes or other adjustments in the period", and the exact amount says so.
  5. The contradiction rule for completeness (enter or leave a confirmed period) is new; P002 did not define it.
  6. For an invoice dated after the base, a statement on it must agree with the complete records before an amount is called exact.
- **Validation, 18 October (fictional data):**
  - **Unit suite:** 196/196 (56 new). Most new behaviour was watched failing first. Where a test was written after its code, it was checked against a build without the behaviour; the commit messages say which.
  - **Whole-workflow test** (`test_full_flow.py`): empty workspace → records → opening balance → historical inclusion → imported payments with allocations → completeness → request → owner decision → revert. It caught one defect before release: cases did not see records that had left a confirmed period, so a revert could leave an exact amount standing.
  - **Real model** (Gemma, prompt extension-v0.3 unchanged): 14/14, 0 rejected tool calls, 5–9 s each.
    - The 9 original scenarios and the 3 payment scenarios behaved as before.
    - New: an exact amount from complete records (with days overdue); an amount that stays unknown, with the reasons.
    - The extended demo also ran end to end with the sample files: the owner saw "AUD 150.00 (exact, as of Sun 18 Oct 2026)".
  - **Headless browser,** on local scratch databases (one in live mode): every new form, question and review; the import's completeness option and its revert; the owner's exact amount; decided-case flags; no horizontal overflow at 390 px; no console errors other than expected 400/409 replies. Screenshots 14–19.
  - **Upgrade rehearsal,** on fresh copies of the deployed database (never the live file): 14/14. See DEPLOYMENT.md, "Next release".
- **Known limits and unresolved defects:**
  - **Not built:** credit notes and adjustments; an opening-balance CSV shape (opening balances are entered by hand); ledger-account and XLSX imports; structured terms (§9.3); decision-time capture.
  - **No prompt for missing still-owed amounts.** An included invoice without a still-owed amount at the as-at date gets no question in Needs attention. Correct the invoice instead.
  - **Interface limits:** the allocation form allocates to one invoice at a time, and an import review choice can't be changed once resolved.
  - **Unmeasured cost:** every records view and case preparation recomputes positions over all records (cost roughly invoices × records). That is fine at fictional sizes and not measured at real volume.
  - **Timeline labels (existing, not fixed):** on the case timeline, a short "N days late" label can overlap the "Today" label.
  - **Fallback parser:** the no-AI fallback still reads only `DEMO-###` numbers.
- **Business questions still open:**
  - B4: how payments are allocated in practice;
  - B6: opening balances, and who may state them;
  - B7: who may confirm completeness, answer inclusion questions, import, apply and revert;
  - B8: how old records may be;
  - B9: which instance, if any, holds real records;
  - credit notes and adjustments.
- **Not established:** usability with real staff or owners, business accuracy, time savings. A passing suite does not establish any of these.

## E010 — Correctness and release-readiness pass: credits, suggestions, cost, timeline

- **Status:** engineering change on 18 October 2026, in the repository owner's (unitylht) development session, at Hanting's instruction after an independent check. Not owner policy.
- **Branch:** `feat/records-payments-20261018`, commits `46b2a0a` to `09e6d35`, plus this update. **Pushed. Not merged, not deployed:** the shared instance still runs `89b92d8`.
- **Reported defect, reproduced on `7a79798`.**
  - **The case:** an unallocated opening credit of AUD 50 (30 Sep), a new AUD 100 invoice (5 Oct), and payments confirmed complete from 1 to 18 Oct gave "AUD 100 exact", with no reasons.
  - **Same class, also found:**
    - credits inside a positive net opening balance;
    - a customer with no opening balance, where the position before completeness started was silently taken as zero;
    - unallocated money received on or before the opening balance date.
- **Fixed:**
  - **Credits.**
    - An opening balance records what a person said about credits in it: *none*, *every credit recorded here*, or not stated (the default). A balance held in credit cannot be *none*.
    - A payment record can be a **credit** held for the customer (a credit note, or a prepayment carried in the balance). It is allocated or marked "not for an open invoice" like any payment.
    - **An exact amount now also needs:**
      - an opening balance with its credits stated;
      - every payment or credit up to the complete-to date, however early, allocated or marked;
      - the credits implied by included invoices to fit what was said.
    - Without an opening balance there is no exact amount.
  - **Equal amounts.**
    - Invoices that add up to an opening balance, and earlier payments that make a stated amount reconcile, are now **suggestions**, not answers. Offsetting omissions (a missing invoice plus a missing credit, or an unrecorded credit note) reconcile just as well.
    - Only all the unanswered records together are suggested, never a choice between combinations.
    - A person confirms; the Records page does it in one step for a whole suggestion.
    - Bounds are unchanged. Exact amounts wait for the confirmation.
    - Automatic inclusion would need the balance and its make-up from one source document as at one date, with stable line identities (P002 8.1). This version has none, so nothing is included automatically.
  - **Timeline:** a day-count label no longer overlaps "Today" when the late span is short.
- **Regression tests:**
  - 15 in `test_credits.py`. 14 failed on the previous revision; the 15th (a credit applied to the invoice) passed there for the wrong reason.
  - 9 existing tests were updated to the new rules.
  - Briefs, decided-case flags and reverts were checked by 3 further tests.
- **Validation (fictional data):**
  - **Unit tests:** 215/215.
  - **Real model** (Gemma): 15/15, including the reported case, 0 rejected tool calls.
  - **Demo Part C,** with the sample files and live Gemma: the opening balance suggests INV-1001 and INV-1002; once a person confirms them, the owner sees "AUD 150.00 (exact, as of Sun 18 Oct 2026)".
  - **Browser:** the credits statement, confirming a suggestion in one step, recording a credit, and an opening credit becoming exact only once it is accounted for. The timeline was checked at 1280 and 390 px with no overlapping label boxes.
  - **Upgrade rehearsal:** 14/14 again.
- **Measured cost:**
  - **Datasets:** `prototype/perf_records.py` builds fixed-seed fictional datasets of about 500, 5,000 and 20,000 records.
  - **The problem:** each invoice's calculation rescanned every record. Before the change (on the same dataset), at 5,150 records: Records page 1.96 s, evidence 1.50 s, one case 4.66 s, one records change 3.06 s. At 20,600 records: 45.5 s, 26.2 s, 84.9 s and 58.2 s.
  - **The fix:** per-customer calculations now get only that customer's records. A test checks the results are identical, invoice by invoice.
  - **After:** 0.16 s, 0.10 s, 0.23 s and 0.26 s; at 20,600 records 0.81 s, 0.54 s, 1.33 s and 1.37 s.
  - **Smaller fixes:** the setup checklist stops computing positions (0.67 → 0.18 s at 20,600), and the page indexes records once per render.
  - **Browser page load at 20,600 records:** 2.6–3.2 s (was 4.3–5.0 s). It is now dominated by the server's 0.9 s and the layout of about 17,000 rows. No further optimisation: the pilot business's records run to hundreds.
- **Remaining release blockers:** DEPLOYMENT.md, "Next release". For the practice demo:
  - the team's decision;
  - the deployed-URL checks on an isolate;
  - a fresh backup and rehearsal at deploy time.

  For real records:
  - the open business questions (B4, B6–B9);
  - usability with real staff;
  - no opening-balance file import;
  - no credit-note documents.
- **Not established:** usability with real staff or owners, business accuracy, time savings.

## E011 — Stage 3 deployed to the shared practice instance

- **Status:** deployment on 18 October 2026, 14:33 Sydney time, at Hanting's instruction, after an approval through Claude Code's permission prompt. It is not owner policy.
- **Revisions:**
  - **Application:** `4f45ca7`, the server's checkout. It replaced `89b92d8`.
  - **Release-check tools and instructions:** `efff0fd`. Their application code is identical to `4f45ca7`.
  - **This record:** the commit that adds it.
  - The branch `feat/records-payments-20261018` is not merged into main.
- **Before:**
  - the outgoing changes were reviewed: no private data, credentials or unexpected files;
  - the full release suite ran against the candidate on copies (DEPLOYMENT.md, "Release validation");
  - the isolated checks through the public URL passed, with the service on disposable copies: production comparison 14/14, smoke 26/26, full Stage 3 flow 53/53, after a restart 10/10, no-AI path 19/19, browser Records 11/11, browser live 27/27.
- **Backups:**
  - database: `backups/nucleon-20261018-143302.sqlite3`, taken with the service stopped;
  - configs and revision note: `backups/predeploy-stage3-20261018-143302/`.
- **Result:**
  - The production database moved into tables; all 3 cases were kept, and the pending briefs were re-stamped.
  - **Live checks:** production comparison 14/14 and smoke 26/26. The smoke flow's owner case was prepared by live Gemma and showed an exact amount.
  - **Read-only browser check:** passed.
  - `sampleData` remains on this practice instance only.
- **Left on the instance:** one labelled fictional customer, "Release check café (fictional)", and one completed case, both from the smoke check.
- **Known issue, existing before this release:** on a 390 px phone with the demo console enabled, the top bar overflows by about 50 px. The phone check missed it. Fixed by `a9ce30d` (E012).
- **Rollback:** restore the backup above and deploy `89b92d8` (DEPLOYMENT.md, "Previous release: Stage 3"). It was rehearsed, and not needed.
- **Not established:** usability with real staff or owners, business accuracy, time savings.

## E012 — Phone top-bar fix deployed to the shared practice instance

- **Status:** deployment on 18 October 2026, 14:45 Sydney time, at Hanting's instruction, through Claude Code's permission prompt. Layout only; not owner policy.
- **Problem:** at 375 and 390 px with the demo console enabled, the top bar was 430–441 px wide. Sign out sat off-screen and the page scrolled sideways. The defect predates Stage 3 (E011).
  - The phone check missed it because it compared with `innerWidth`, which mobile emulation widens to fit wide content.
- **Change:** at 820 px and below, the top bar wraps its controls onto a second row; every control stays visible. There is no page-wide overflow clipping and no behaviour change.
- **Revisions:**
  - **Application:** `a9ce30d`, the server's checkout. It replaced `4f45ca7`.
  - **Check tools:** `deploy/layout_check.js` (new, read-only) and `browser_check.js`'s phone checks, now against the configured width, are in `a9ce30d`. The production comparison's sample check was corrected in `0854b86`.
  - **This record:** the commit that adds it. The branch is not merged into main.
- **Before:**
  - `layout_check.js` reproduced the defect on the previous release (64/100) and passed against the fix on a copy of production (100/100).
  - A width sweep from 320 to 1366 px found no overflow.
  - `browser_check.js` passed on scratch databases: live 27/27, Records 11/11.
- **Backups:**
  - database: `backups/nucleon-20261018-144453.sqlite3`, taken with the service stopped;
  - configs and revision note: `backups/predeploy-topbar-20261018-144453/`.
- **Result:**
  - The unit suite passed in the deploy: 215 tests OK.
  - The production comparison passed 14/14, read-only. Its first run was 13/14 because the check assumed sample-only records; the check was corrected, not the application.
  - `layout_check.js` passed 100/100 on the public URL.
  - Data was untouched: no reset, all 4 cases, the sample, and the labelled release-check customer and case. The test databases were kept.
- **Rollback:** `nucleonctl deploy 4f45ca7`; only the stylesheet differs.
- **Not established:** usability with real staff or owners on their own phones.

## E013 — Interface redesign and the PC QA findings (branch only)

- **Status:** implementation on branch `feat/ux-redesign-20261018`, 18 October 2026, at Hanting's instruction.
  - Not merged into main. **Not deployed:** the shared practice instance still runs `a9ce30d`, and nothing on it was reset or changed.
  - These are engineering and interface decisions, not owner policy.
- **Why:** a guided test on a Windows PC (tester tag `CL1018T`; [qa/2026-10-18-pc-handover](qa/2026-10-18-pc-handover/README.md)) reported 26 findings. The interface had also outgrown its structure: one Records page about 7,000 px long on a desktop and 10,000 px on a phone.
- **Decisions:**
  - **Navigation:** task areas (Requests, Customers, Imports, Knowledge, Setup) instead of a single Records area with tabs. The customer page holds invoices, payments, opening balance and completeness, notes and requests; changes happen in dialogs that state their impact. The comparison and the reasons are in [UX-REDESIGN.md](UX-REDESIGN.md).
  - **Sign out** ends every role this browser holds; other browsers keep theirs (QA B1). A code for a different role is refused at a role prompt, with a message (U2).
  - **Opening balances:** the permission is unchanged; staff and the owner can both enter them. Who may is open question B6 (P002 §13.2). The brief and the customer page now say who entered each one (B2). Completeness stays owner-only (B7 open).
  - **Import drafts** can be kept, resumed or discarded (B4). A revert shows what it would do before anyone confirms, through a read-only impact view; the server's checks are unchanged (B3).
  - **Money and dates:** every amount carries its certainty (exact, at most, stated, not recorded, as recorded). "Not recorded" and "at most" stay distinct, because only allocated payments bound what is owed on an invoice (U6). Recorded times are labelled as real time, next to the fixed business date (U5). The customer reply writes the date out (U4).
  - **The agent:** a quote about the invoice, in a message without date wording, is labelled the request when the extraction found no other request (B6). A separate request the extraction lists keeps its label. The prompt is unchanged; the rule is recorded in PROMPTS.md.
  - **Design system:** Arial; one accent for actions; colour only for status. Text contrast is at least 4.95:1 and control borders 3.4:1 or more.
- **Commits:**
  - `cfda0e7`: sessions;
  - `17a7806`: server corrections;
  - `a4cd2ab`: interface;
  - `c03e552`: browser checks;
  - `4fa5726`: agent status shown at once, and check updates;
  - `7be43c9`: border contrast;
  - this record: the documentation commit.
- **Disposition of all 26 findings:** [qa/FINDINGS-DISPOSITION.md](qa/FINDINGS-DISPOSITION.md).
  - Fixed: B1, B3 (interface), B4–B9, U1–U4, U7–U12, G2 and G3.
  - Clarified: B2 (with provenance added), U5, U6 and G1.
  - Corrected in the guide: G4 and G5.
  - Deferred: one defect found during this work. A revert that removes only an import's bookkeeping still flags decided cases, because the evidence key covers it; changing the key needs a re-baselining migration.
- **Checks on the final code** (local scratch servers only; fictional data):
  - **Unit tests:** 225 OK.
  - **Interface:** `ui_check.js` 112/112 (sessions, roles, records, imports, allocation, exactness, flags, reverts, loading, keyboard, 375 and 390 px, a failed preparation and its retry). `layout_check.js` 156/156 (375 and 390 px, with and without mobile emulation; 820 and 1366 px).
  - **Guide revision 3:** `guide_check.js` 56/56 with the live model.
  - **Live model and fallbacks:** `browser_check.js` live 28/28, fallback 9/9, legacy 7/7, records 12/12.
  - **Records:** `e2e_records_check` practice 24/24, empty 16/16, real 23/23.
  - **Requests and the console:** `e2e_https_check` approve 30/30, restart 9/9, stale 13/13, change-date 17/17, decline 16/16, clarify 22/22, console 27/27, both fallbacks 12/12, legacy 12/12.
  - **Stage 3:** full 53/53, after a restart 10/10, fallback 19/19, smoke 26/26 on a copy of production.
- **Not established:**
  - a real phone, other browsers, a screen reader;
  - use by a teammate;
  - business accuracy, time savings.
- **Next:** a team review of the branch and of B6/B7. Then, if accepted, a deploy through the established backup process, with the corresponding browser checks.

## E014 — After the review of `810a4cc`: sign-out, the phone customer page, evidence keys (branch only)

- **Status:** branch `feat/ux-redesign-20261018`, 18 October 2026, at Hanting's instruction after an independent review of `810a4cc`.
  - Not merged into main and **not deployed**: the shared practice instance still runs `a9ce30d`, unchanged.
  - Engineering and interface decisions, not owner policy.
- **Decisions:**
  - **Sign-out ends work in this view at once.**
    - Unsent drafts, kept filters and searches, and loaded records are removed from this browser; other tabs follow.
    - Success is shown only when the server, asked afterwards, holds no session for this browser. Otherwise the page says "Sign-out not confirmed", says what is known, and offers a retry.
    - Every role in the browser still ends together; other browsers keep their sessions.
    - While signed in, drafts still survive navigation and reloads.
  - **The phone customer page puts the records and routine actions first.**
    - A short summary of open issues names their records, blocking ones first, with "Review all". The explanations and questions are on a Needs attention tab.
    - Uncertain figures keep their marks. Nothing is clipped or hidden.
  - **Evidence keys, format 2** ([EVIDENCE-KEYS.md](EVIDENCE-KEYS.md); the assessment was committed before the code).
    - Decided-case flags and pending-case re-preparation react to what an invoice shows, not to import bookkeeping or to the wording of an explanation.
    - A kept conflict counts as evidence: the amount is unchanged, but the evidence is not.
    - **Migration:** a stored key is carried over only when it equals `a9ce30d`'s key for the records now. Otherwise a decided case is flagged when this version starts, and a pending case is prepared again. Existing flags are never changed.
    - **Rollback** is by restoring the pre-deploy backup.
  - **Then open, now settled for the prototype in E015:** what a revert should do when a later import disagreed with the record and a person kept the recorded value.
- **Commits:**
  - `44fc0f8`: sign-out;
  - `2b1fea0`: the customer page;
  - `31f0dd6`: guide revision 3;
  - `1d799ac`: the evidence-key assessment;
  - `83c602e`: format 2 and the migration;
  - this record.
- **Checks on the final code** (local scratch servers and scratch or read-only copied databases; fictional data):
  - **Unit tests:** 237 OK, including `test_evidence_keys.py` (12) on a database written by `a9ce30d`'s own code.
  - **Interface:** `ui_check.js` 148/148 on fresh servers. It covers the sign-out lifecycle (E1–E6) and the customer page at 375 and 390 px, routine and with three open issues. `layout_check.js` 156/156.
  - **Guide revision 3:** `guide_check.js` 58/58 with the live model.
  - **Evidence keys:**
    - the frozen `a9ce30d` keys equal that release's own on 26 cases in 9 databases;
    - on a production copy: 3 re-baselined, 3 re-stamped, nothing flagged; an unrelated change then flags nothing, and a real one does.
  - **Release batch, on local servers of the final code:**
    - `e2e_records_check`: practice 24/24, empty 16/16, real 23/23.
    - `e2e_https_check`: approve 30/30, restart 9/9, stale 13/13, change-date 17/17, decline 16/16, clarify 22/22, console 27/27, both fallbacks 12/12, legacy 12/12.
    - Stage 3: full 53/53, after a restart 10/10, fallback 19/19, and smoke 26/26 on a fresh read-only copy of production. Its startup logged 3 decided cases re-baselined, 3 pending re-stamped and 0 flagged.
    - `browser_check.js`: live 28/28, fallback 9/9, legacy 7/7, records 12/12. `--records` first failed 1/2: it still looked for the attention explanations on the customer page. It now follows the summary to the Needs attention tab.
- **Next:** a team review of the branch. Then, if accepted, a deploy through the established backup process. Watch the startup log line `evidence keys: format 2 {…}`; production should show 3 re-baselined, 3 re-stamped and 0 flagged if nothing changes before then.

## E015 — Revert provenance after a kept conflict; sign-out wording (branch only)

- **Status:** branch `feat/ux-redesign-20261018`, 18 October 2026, at Hanting's instruction, given as a conservative rule for the prototype.
  - Not merged into main and **not deployed**: the shared practice instance still runs `a9ce30d`.
- **Rule (Hanting, for the prototype):** "Keep what's recorded" rejects the conflicting file's values.
  - It does not make that file a source for the values kept.
  - It does not create a manual record, and it does not credit the person who chose Keep.
  - Example: import A creates an invoice for 1,000; import B proposes 1,200; a person keeps 1,000. Reverting A must never credit the 1,000 to B.
- **Decisions that follow from it:**
  - **Support:** a later import supports a record only when it listed the record in a row accepted as it stood, and that row states every value the record has now. An equal amount is not enough.
  - **Blocking:**
    - Without a supporter, reverting the record's import is blocked.
    - The reason names the record, each later import involved, and the way out: revert those imports first, or leave this one in place.
    - Nothing is deleted, converted or re-credited.
  - **Scope:** the same rule covers invoices and payments, records created by an import, restored earlier versions, and records credited to an import when an earlier one was reverted.
  - **Unchanged:** allocation, dependency, case-review and evidence-change safeguards.
- **Sign-out wording:** when no response arrives, the page says "The app did not receive confirmation", not that the request could not reach the server.
- **Existing data:** read-only copies of all 105 databases on the home server were searched. Nothing was credited by the old rule, and nothing was rewritten ([qa/FINDINGS-DISPOSITION.md](qa/FINDINGS-DISPOSITION.md), R5).
- **Commits:**
  - `7ccdd63`: sign-out wording;
  - `f95bbc0`: revert provenance;
  - the scan for attribution made by the old rule (`deploy/provenance_scan.py`), with this record.
- **Checks** (local scratch servers and copied databases; fictional data):
  - unit tests 247 OK, including `test_revert_provenance.py` (10, one for the scan of existing data);
  - `ui_check.js` 148/148;
  - `guide_check.js` 58/58 with the live model;
  - `e2e_records_check` practice 24/24;
  - Stage 3 full 53/53, after a restart 10/10, and smoke 26/26 on a fresh production copy;
  - `browser_check.js --records` 12/12.
- **Open for real use, not decided here:** in a real workspace, whether a value kept against a conflicting file may stand on a person's confirmation when its import is reverted. That is part of P002 B7 (who may import, apply, revert and correct).


## E016 — The redesign deployed to the shared practice instance

- **Status:** deployed on 18 October 2026 at Hanting's explicit instruction. Branch `feat/ux-redesign-20261018`, not merged into main.
- **Revisions:**
  - `33272b7`, the reviewed candidate, went live at 23:14 Sydney.
  - `f95f50f` went live at 23:24, on Hanting's approval. It adds one fix found after the first deploy: the server's listen queue was 5, so most first page loads lost a file to a 502. It is now 128.
- **Data:** kept. Nothing was reset or removed.
  - The evidence-key migration re-baselined 3 decided cases and re-stamped 3 pending ones. It flagged nothing and prepared nothing again, exactly as rehearsed on a fresh copy.
  - The provenance scan found nothing to correct.
- **Checks on the live site:**
  - production comparison 15/15 and layout 156/156 (both read-only);
  - smoke 26/26, which adds one labelled fictional customer and case;
  - a read-only browser check of navigation, case to customer and back, imports, the phone layout and sign-out: 15/15;
  - 0 of 30 fresh page loads lost a file.
- **Record:** [DEPLOYMENT.md](DEPLOYMENT.md), "Current release". It holds the backups, what the checks left behind, and the rollback: restore the backup, never run earlier code on this database.
- **Testers:** use guide revision 3 ([qa/test-pack-v3/](qa/test-pack-v3/)) on the shared site.

## P003 — Nucleon as a coordinating agent (proposal, 19 October; revision 2 the same day)

- **Status:** proposal written by Hanting's development session at the team's request after the first-time-user interview and the application walkthrough; revised the same day against the team's written decisions. Not owner authority; nothing implemented. [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md).
- **Baseline preserved:** tag `baseline-records-ui-20261019` on `f95f50f`, the records interface as deployed (E016). Exploration branch `explore/agent-coordinator-20261019`.
- **Team decisions of 19 October, recorded in the proposal:** additive coordinator over the retained records and controls; the current local model's speed does not set the interaction model, and hosted model APIs are an intended deployment option (none connected or tested yet); conversation stays a primary way to work, with cards and asynchronous processing where useful, judged by how much work the user does; owner knowledge structured internally but confirmed as one interpretation, with guidance never becoming permission and case answers never becoming universal definitions; essential clarification covers what is needed to calculate, to recommend and to act, with reasons and partial results; an advisory suggestion in the first slice (E017); a small read-only conversational capability for staff; an unresolved ordering constraint kept and shown as not applied, never automatically in a reply.
- **Questions to the team** (P003 §12): staff visibility of owner context; the scope of "remember" at the decision moment; a hosted endpoint to test against.
- **Open business questions** stay as recorded (Q01–Q08, P002 B1–B11); none blocks the first slice.

## E017 — Advisory suggestions in the prototype (team instruction, 19 October)

- **Status:** the team's written instruction of 19 October, relayed by Hanting, for the first slice of P003. Not implemented yet. It changes the prototype's recommendation boundary (E003) **for the prototype only**.
- **Decision:** the first slice includes a clearly labelled advisory suggestion (outcome, date, the context lines and facts it cites, one sentence). It is off by default, turned on by the owner only, shown to the owner only, stored apart from the decision and never copied into it. The owner retains every decision.
- **What it does not establish:** real-world decision quality. E003's conditions for recommendations in real use, an owner-confirmed approval policy (Q03) and an evaluation that includes refusals (Q05), are **not met**; fictional scenarios demonstrate and test the workflow only. The "Still open" item on whether the agent may ever recommend stays open for real use.
- **Safeguards carried over from E003:** every number and date in a suggestion is checked by code; citations must be loaded evidence; the prose guard applies; a test scenario in which the context argues against approval guards against "approve in every complete case".

## E018 — The coordinator's first slice, built on the exploration branch (not deployed)

- **Status:**
  - Engineering change in the repository owner's (unitylht) development session, 19–20 October 2026, implementing P003 revision 2 and the team's decisions of 19 October (P003 §12a; E017).
  - Branch `explore/agent-coordinator-20261019`, commits `191038b`…`9e7f52c` and this record (`51b48d8`), then the final review's fix wave: `1f26b36`, `dc1768c`, `bba6529` and its record.
  - **Not merged and not deployed:** the shared practice site still runs `f95f50f` (E016).
  - Not owner policy, and not a team decision to adopt the desk.
- **Decision:** build the first slice additively over the retained records, controls and case pages:
  - the coordinator's four model tasks (`coordinator-v0.1`);
  - statements confirmed once;
  - owner questions classified by code;
  - the advisory suggestion of E017;
  - read-only questions;
  - the desk as the Requests area.

  The old list view and form stay at `#/cases` and `#/cases/new`.
- **Reason:** the team's decisions of 19 October: P003 §12a says "The slice proceeds on the exploration branch". The slice tests whether coordination reduces the work people do (P003 §6 and §10).
- **Detail:**
  - what was built, by section: [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Implementation notes (first slice)";
  - prompts, schemas, guards, mock rules, staff visibility and model access: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.1";
  - the desk: [UX-REDESIGN.md](UX-REDESIGN.md) and [prototype/README.md](../prototype/README.md).
- **What it establishes** (fictional data; local scratch servers):
  - The workflow runs end to end on fictional data:
    - the owner's words are confirmed once and used with their scope and date;
    - a case asks the owner only what code lets through, with the reason;
    - a suggestion is withheld, then given, then taken or declined, and stored apart from the decision;
    - staff get code-written answers and none of the owner-only context.
  - **Where the suggestion shown is stored:** beside the decision, as the case's `suggestionSeen {version, outcome, approvedDueDate, relation}`, owner-only; the decision record and its `decision.committed` event hold none of it (fix wave, `1f26b36`).
  - **Checks at `51b48d8`:** `layout_check.js` 174/174, `ui_check.js` 149/149 and `guide_check.js` 58/58 ran at Task 9. The unit suite (330 OK), `desk_check.js` (47/47) and `effort_compare.js` (17/17) were re-run after the last fixes.
  - **Checks after the fix wave** (20 October; each browser check on a fresh `deploy/ui_check_server.py` scratch server, mock agent):
    - unit suite at `bba6529`: `Ran 333 tests` `OK`. One earlier full run had one error in `test_evidence_keys` (startup flagging), which the fix wave does not touch. It did not recur in three more full runs or 15 runs of that test alone;
    - `desk_check.js` at `dc1768c`: `RESULT desk: 48/48 checks passed`;
    - `layout_check.js` at `dc1768c`: `RESULT layout: 174/174 checks passed`;
    - `ui_check.js` at `dc1768c`, normal and `--fault-fallback` servers: `RESULT ui: 150/150 checks passed`;
    - `effort_compare.js` at `dc1768c`: `RESULT effort: 17/17 checks passed`. The counts were the same as at `2b628ab`, so [qa/EFFORT-COMPARISON.md](qa/EFFORT-COMPARISON.md) keeps the `2b628ab` run;
    - `guide_check.js` at `bba6529`, with the live model through the old pages: `RESULT guide: 58/58 checks passed`;
    - `deploy/live_coordinator_check.py` at `bba6529`, with the live model through the desk API, twice: `RESULT live coordinator: 18/18 checks passed` and `RESULT live coordinator: 20/20 checks passed`.
  - **The live model in the coordinator's tasks** (two runs of one scenario; wording in [PROMPTS.md](../PROMPTS.md), "Observed behaviour: coordinator-v0.1"):
    - every turn was routed as intended, and the paragraph gave the same six quoted lines both times;
    - the questions were about the owner's own words ("small extension"; "I don't want their debt to increase"). In run 2 the guard dropped one that stated an amount;
    - run 1's suggestion was withheld by code: it cited the answer line's id without its `line_` prefix. Run 2 gave decline, citing the owner's answer "Up to 14 days this time".
  - **Effort comparison** ([qa/EFFORT-COMPARISON.md](qa/EFFORT-COMPARISON.md); mock agent, fictional):
    - the owner's actions did not fall: S1 4 → 4, S2 5 → 6;
    - staff actions were unchanged;
    - pages opened for the staff question fell from 2 to 0;
    - all six runs were correct.

    By P003 §6's own test, the desk did not win on owner actions in this comparison.
- **What it does not establish:**
  - real-world value or time savings;
  - decision quality: E003's and E017's conditions, Q03 and Q05, are not met, and the counters say so of themselves;
  - any hosted model: none was connected or tested;
  - the live model's quality in the coordinator's tasks: two functional runs of one scenario, through the API, not the browser;
  - use by a teammate, the Reading section of the effort comparison, a real phone, or a screen reader.
- **Rulings recorded while building** (one line each; the reasons are in P003's implementation notes):
  1. Owner context does not survive a demo reset. Reset and start-empty clear statements, threads, turns and the moved business date.
  2. Malformed model output raises an adapter error, as in extraction, and the existing failure paths handle it.
  3. A need is answered only by an answer line, never by the guidance that raised it.
  4. Requests stay staff-submitted. An owner's "request" on the desk creates nothing and gets an owner-only explanation.
  5. Every owner turn, and the agent's reply to it, is owner-only.
  6. Staff see no case questions and no `contextShown`.
  7. "Remember" keeps reusable guidance only, and the decision keeps the outcome. A later question raised by unclear guidance is intended.
  8. `byScenarioLabel` was dropped from the counters.
  9. Task 8, the `other` request type, is cut. The existing behaviour stands.
  10. The desk lists every case, including those entered through the form. A case's thread is created on first use.
  11. `suggestionShown` is sent whenever a suggestion is on screen.
  12. `#/cases/new` is the old form, linked as "New request (form)" in the list view.
  13. Process: the work was done in place on the exploration branch, with no worktree, and commits use the attribution line the harness gives.
  14. Fix wave: staff see no trace of the owner's questions. That covers the `question.*` events and the needs step's check items (`step: 'needs'`). Staff see only the event kinds in an allowlist (`STAFF_EVENTS`). The brief stays a key-by-key scrub: an allowlist of brief keys would also have to carry the `brief-v1` keys.
  15. Fix wave: a line whose source is `decision` is never cited by a suggestion. Code leaves it out of the citable ids, and the prompts say those are words kept at another case's decision, never an approval of this one. The line is still shown to the owner.
  16. Fix wave: the suggestion shown is stored beside the decision (`suggestionSeen`), not inside the decision or its event, as E017 words it.
  17. Fix wave: staff reading a statement get its id, status, visibility, scope, date and active lines only. On the desk, a shared `guidance` or `constraint` line is marked "not enforced by the system".
  18. Fix wave: a case prepared without the agent says "No suggestion: the case was prepared without the agent." and does not offer to turn suggestions on.
  19. Fix wave: two §10 scenarios stay unbuilt in this slice and the demo must not claim them: re-asking an expired expectation, and a staff fact that conflicts with an owner line. There is no code rule for either; they are left to the model.
  20. 20 October, replacing ruling 6 for questions: staff see and answer questions addressed to them; owner questions stay owner-only; a staff question that repeats private context (12 or more characters of an owner-only quote) is moved to the owner. A staff answer is a proposed, staff-visible, case-scoped statement. Staff still see no `contextShown`.
- **Consequences:**
  - The guide's Requests steps describe the old pages, which are at `#/cases` on this branch. Test pack revision 4 is pending.
  - `PROMPTS.md` records `coordinator-v0.1` and `brief-v3`.
  - `DEPLOYMENT.md` records model access: local tested, hosted untested.
- **Next:**
  1. A team review of the branch on a local preview. `deploy/live_coordinator_check.py` can be run there before the review.
  2. A decision on whether to deploy it to the shared practice site. Any deploy would go through the established backup process, and testers there would need guide revision 4.

## E019 — Preview of the agent-coordinator branch deployed under /preview/

- **Status:** deployed on 20 October 2026 at 10:33 Sydney, on the team's instruction of 20 October, for a browser review of E018.
  - Branch `explore/agent-coordinator-20261019`, commit `8084bee`. Not merged into main.
  - It builds on `124a343` (the page served under a path prefix, with its own cookies and storage).
- **What it is:**
  - a second instance at https://nucleon.dracooz.top/preview/: its own launch agent (`local.nucleon.preview`), port 8621, clone, config and database (`~/srv/nucleon-preview/`, a practice workspace with the fictional sample, and the demo console);
  - its own codes and log, and cookies `nucleonp_*` with `Path=/preview`;
  - the same local Gemma gateway as production, in live mode;
  - Caddy routes `/preview/*` to it with the prefix stripped.

  Full record: [DEPLOYMENT.md](DEPLOYMENT.md), "Preview instance (agent-coordinator branch)".
- **What it is not:**
  - not a release and not a decision to adopt the desk: the shared practice site at `/` still runs `f95f50f` (E016), with its data and configuration untouched;
  - not real data;
  - not a hosted model;
  - not a test-pack revision: guide revision 3 still describes the old pages, which are at `#/cases` on the preview.
- **Results** (one run, live model, through the public URL; scratch Playwright script, not committed): 25 of 26 checks passed.
  - **Workflow:** the owner's paragraph → 6 quoted lines, confirmed. The staff request → a case thread, `awaiting_owner` in 15 s. Then: the owner's view and cards; suggestions turned on and withheld while a question was open; the answer; the decision and draft; staff "what does … owe?" → an answer card matching the records.
  - **Other checks:** 390 px fit; production unchanged (`static/desk.js` 404 at `/`); a preview cookie is not a sign-in at `/`; the counters.
  - **The one FAIL was the script's expectation.** Staff do get a "What the owner shared" card, holding the sample's shared note. A read-only probe found none of the owner's words, questions or suggestion in the staff payload.
  - **Live-model findings:**
    - the owner's question asked for the decision itself: "Do you want to grant the requested extension for invoice DEMO-101 until Tue 10 Nov 2026?". Its reason was the prompt's example sentence, word for word;
    - the suggestion **failed** after one call, and the reason is not recorded (the server keeps only the status);
    - every agent step took 2–15 s.
- **Remaining limitations:**
  - the effort comparison did not show fewer owner actions;
  - guide revision 4 is pending;
  - a hosted model is untested;
  - staff questions are rare with the live model;
  - the two unbuilt §10 scenarios (E018 ruling 19) must not be claimed.
- **Left on the preview:** the check's statement, case and turns (fictional). Suggestions are left on. The demo console's reset on the preview clears them.
- **Fix and re-check (20 October, 10:53–10:56 Sydney):** `f3dd129` is deployed to the preview. Production is unchanged.
  - **The fix:**
    - `plan_needs` has a rewritten prompt. A code guard drops any question that asks for the decision, or that repeats a prompt example.
    - A failed suggestion gives the owner a fixed reason and keeps the raw reason (`suggestReason`, owner-only).
    - A cite without its id's prefix now names the loaded id.
    - The decision form drops "The agent doesn't recommend an outcome." while suggestions are on, and a failed suggestion is shown once.
    - Unit suite 344 OK. `desk_check.js` 49/49.
  - **Re-check** (one run, live model, public URL, Harbour Demo Logistics DEMO-201 asked 21 days late):
    - The question was "Regarding the 'newer customer since August 2026', what is the maximum number of days you would typically allow for an extension?". It does not ask for the decision, and its reason is in the model's own words.
    - After the answer "Up to 14 days this time", the suggestion was **given** (1 call, 2.5 s): approve Fri 30 Oct 2026, citing that answer. Its sentence: "The suggestion is based on the provided guidance regarding the duration of the extension."
    - It approves 21 days while citing "up to 14 days": code checks citations, not agreement. This is advisory and not evaluated (E017).
    - The failure reason and the bare-cite rule were not exercised live.
  - Record: [DEPLOYMENT.md](DEPLOYMENT.md), "Fix and re-check".
  - Left on the preview: case `req_b1819e749212286d`, undecided.
- **Day-limit guard and prompt version (20 October):** `9cc6d75`, on the team's instruction after the re-check above.
  - **Guard, in code:** the server reads a limit from each loaded answer or guidance line of this case, or of this customer, whose quote says "up to N days" (not one that has ended). The model never computes it. `validate_suggestion` withholds an `approve` dated later than the current due date plus the smallest limit. The raw reason is `exceeds_day_limit`, and the owner sees "The suggested date goes beyond the days you allowed." The `suggest` prompt now says never to suggest a date beyond a limit the owner stated.
  - **Scope:** it binds the suggestion only. The owner's decision form is unchanged. Other wordings ("two weeks at most") are not read.
  - **Prompt version:** `coordinator-v0.2`, because the `plan_needs` and `suggest` texts changed after the first live runs. PROMPTS.md lists the changes from v0.1. Earlier suggestions and desk turns still say `coordinator-v0.1`.
  - Unit suite 346 OK. `desk_check.js` 49/49 on a fresh mock server.

## E020 — The conversational desk: second slice on the team's direction of 20 October (preview only)

- **Status:**
  - Engineering change in the repository owner's (unitylht) development session, 20 October 2026, on the team's direction of that day.
  - Branch `explore/agent-coordinator-20261019`, commits `c3af0db` (plan) to `b888db8`, and these records. Prompt version `coordinator-v0.3`.
  - **Deployed to the preview only** (`/preview/`, E019). The shared practice site at `/` still runs `f95f50f` (E016). Not merged.
  - Not owner policy, and not a team decision to adopt the desk.
- **The team's direction (20 October), as given:**
  1. a natural working conversation;
  2. combine tools;
  3. permissions and calculations in code;
  4. answer first;
  5. simplify;
  6. prepare actions;
  7. both hosted and local models;
  8. validate with varied wording.
- **Decision:** replace the desk's four-category router (`route_turn`, E018) with a bounded tool-calling agent loop, as the plan's §0 sets out (`docs/superpowers/plans/2026-10-20-conversational-desk.md`; [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 3"):
  - the model gathers with read tools (records, context, cases), a navigation tool and action tools, then writes the reply;
  - code guards every sentence of it and writes every figure in the cards;
  - each thread keeps a current customer per role;
  - one answer card, words first;
  - the case thread decision-first for the owner and one status line for staff;
  - a shorter alternative within a day limit the owner stated.
- **What this slice built:**
  - `desk_run` and `DeskTools` (at most 8 tool calls and 6 model turns per desk turn), the `answer` card and the reply guard;
  - `prepareCustomer` and the draft card, whose Create button opens the existing Add customer dialog prefilled, so nothing is created by the agent;
  - `whereIs` over a fixed map of the application with each button's label and steps;
  - the current customer, with follow-ups, switches and "which customer?";
  - the reorganised case thread;
  - `deploy/conversation_check.js` with 13 scenarios, and [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md);
  - Task 6: `customerOverview`'s `balanceLine`, written by code for the model to quote, and the prompt rule never to total amounts.

  Details: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.3" (prompts, tools, reply schema, guards, mock rules, observed behaviour); [UX-REDESIGN.md](UX-REDESIGN.md); [prototype/README.md](../prototype/README.md).
- **Checks** (fictional data):
  - unit suite 372 OK at `b888db8`; `desk_check.js` 60/60; `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 at the fix waves, on fresh scratch servers with the mock agent;
  - `conversation_check.js`: mock 169/169 (4 live-only assertions skipped);
  - live, local Gemma at temperature 0: Task 5 159/161 twice (2 FAIL: the wrong customer after a name the records do not hold); after two fix waves 172/172, 170/170, 172/172 and 167/167; with `coordinator-v0.3` 170/170, 3 INFO, no reply withheld;
  - the preview: deployed as `65982b8` at 19:46 on 20 October and checked through the public URL with the live model: the three-part ask, the follow-up, the switch, "where do I add a customer", adding Riverside Bakery and the owner's context passed; of two requests beyond the owner's "up to 14 days", the first got a suggestion of the current due date, which code withheld, and the second, after the owner's answer, approve Mon 30 Nov 2026 within the limit. Production still runs `f95f50f` ([DEPLOYMENT.md](DEPLOYMENT.md), "Conversational desk and verification").
- **Rulings recorded while building** (reasons in P003, "Revision 3"):
  1. Task 1 shipped without a current customer; Task 3 added it, with the continuity assertions Task 1 had deleted.
  2. Counts the model may state are explicit fields in the tool results (`openCount`, `overdueCount`, `caseCount`, `invoiceCount`), keyed by noun; ids and links are not known figures.
  3. After a search that matched nobody, `"current"` is refused for the rest of the run, and the model must ask which customer.
  4. For staff, a sentence about the absence of owner context is replaced in code by "The owner has not shared anything about <customer> with staff.".
  5. An amount may appear in the reply only with the certainty mark the tool returned for it; otherwise the sentence is withheld.
- **What it establishes:**
  - On 13 scripted conversations with fictional data, the desk answers in one card, follows a current customer, asks which customer for an unknown name, prepares a customer without creating one, points to where things are done, and keeps the owner's private context from staff.
  - The guard withheld what it was built to withhold: the model's own totals, a wrong mark, invented counts and dates, claims of action.
- **What it does not establish:**
  - that people understand the desk or finish tasks with less work: the rubric's reader is a model, the human column is empty, and the effort comparison was not re-run on this slice (the first slice's did not show fewer owner actions);
  - any hosted model: the direction asks for both, but none was connected or tested;
  - the model's quality beyond one local model at temperature 0 on scripted wording; `coordinator-v0.3` had one full live run;
  - decision quality: E003's and E017's conditions, Q03 and Q05, are still not met;
  - use on a real phone or with a screen reader.
- **Consequences:**
  - The four read-only question types of P003 §6 are superseded by the tools. `route_turn` is gone from the code and from PROMPTS.md.
  - Guide revision 4 is still pending.
  - The open items are listed in P003, "Revision 3": the staff completeness steps, the Create button after use, ø and ł, the browser check for three open blocks, final review items 7–11, counts by noun only, and the unguarded `browser_check.js` and `e2e_*` scripts.
- **Next:** a team review on the preview, then a decision on whether to deploy to the shared practice site, through the established backup process and with guide revision 4.

## E021 — Situation, capabilities and prepared actions: third slice on the team's direction of 21 October (preview only)

- **Status:**
  - Engineering change in the repository owner's (unitylht) development session, 21 October 2026, on the team's direction of that day.
  - Branch `explore/agent-coordinator-20261019`, commits `e7a45be` (plan) to `50233e5`, and the records (`25e3e59` and this pass). Prompt version `coordinator-v0.4`.
  - **For the preview only** (`/preview/`, E019); deployed as `df10ab6` at 02:26 on 21 October and checked through the public URL as both roles ([DEPLOYMENT.md](DEPLOYMENT.md), "Third slice (21 October)"). The shared practice site at `/` still runs `f95f50f` (E016). Not merged.
  - Not owner policy, and not a team decision to adopt the desk.
- **The team's direction (21 October), as given:**
  1. Nucleon serves people and AI agents: the agent shares the role-appropriate context of a case, with a case-details capability;
  2. availability, permission and confirmation are distinct concerns; the preview's defaults enable every implemented tool for its roles, with no silent outbound effects;
  3. prepared decisions with one confirmation, and calculable questions answered from code;
  4. suggestions the owner asks for go through the guarded mechanism;
  5. workflow actions derived by code;
  6. fix the stale focus, repeated details and failed responses, and avoid phrase-specific fixes.
- **Decision:** build the plan's §0 (`docs/superpowers/plans/2026-10-21-situation-and-capabilities.md`; [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 4"):
  - one role-filtered situation that the desk page draws and the agent reads, and `caseDetails`;
  - a capability registry (`coordinator.CAPABILITIES`) with availability, permission and confirmation kept apart, and the owner's switches under Setup → Agent tools;
  - `prepareDecision` with one **Confirm decision**, `requestSuggestion` through the existing guarded step, and next steps from `actions_for`;
  - the reply's `detail`, blocks merged by code, three focus kinds, and one retry of a withheld reply before "Here is what the records show about <subject>.".
- **What this slice built** (`git log 65982b8..HEAD --oneline`, oldest first):
  - `3d0ae0d` Preview: the conversational desk deployed (65982b8) and checked through the public URL (E020's preview record, before this slice);
  - `e7a45be` Plan: situation, capabilities and prepared actions (third slice);
  - `506e51a` Situation: one role-filtered picture of the case for the page and the agent; caseDetails; case lines in context;
  - `aaa17b4` Situation fix round 1: the desk opens on a fresh workspace; a claim in a label's words is withheld;
  - `ae3dfd8` Capabilities: a registry of the desk tools, owner overrides under Setup, only enabled tools offered and run;
  - `f791731` Prepared actions: the owner prepares a decision and confirms it with one button; a new suggestion on demand; next steps from the workflow;
  - `99c9b63` Prepared actions fix round 1: days and dates only as the owner said them; a new suggestion withdraws a preparation; steps follow the tool settings;
  - `d5d165a` Presentation, focus and recovery: the reply says how its blocks are shown; each invoice once; the focus is a customer, a draft or a name not found; a withheld reply is asked again once;
  - `3351fd2` Presentation fix round 1: the withheld card names no customer the turn did not show; every call in the batch is answered before the retry; the retry's reply is counted;
  - `ccb8b50` Validation of slice 3: ten case and desk conversations on the mock and the live model;
  - `f83ddfc`, `6ca8d69`, `80d164f` Slice 3 fix wave, rounds 1–3: short answers as a summary; the card's subject after caseDetails; codes and references as ids; a repeated call answered from above; "current" with a draft or a name not found; reference digits are no count, a range still is; the owner's quoted line is no judgement; a suggestion sentence that contradicts the day-limit comparison is withheld and asked again once; one context block; the draft kept on a search for its own name; the page's date words in results;
  - `25e3e59` Records: coordinator-v0.4 (E021, P003 revision 4), and the fix-wave re-run;
  - `50233e5` Slice 3 fix wave round 4: a list's step numbers are no figures; a lead-in ending a short answer does not keep it open; the detail rule names no lead-in; the runner keeps the owner's limit when no question was asked and prints why a suggestion failed;
  - this final records pass.

  Details: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.4"; [UX-REDESIGN.md](UX-REDESIGN.md), "Third slice (21 October)"; [prototype/README.md](../prototype/README.md); [DEPLOYMENT.md](DEPLOYMENT.md), "Third slice (21 October)".
- **Decision taken while building, a deviation from §0.6:** code folds a reply the model sends as `full` to `summary` when the reply has at most two sentences and carries a figure, whatever its blocks. A last sentence ending in ":" is not counted (round 4), so a lead-in the model adds to a short answer ("Here are their invoices:") does not keep it open; a lead-in alone, or a short reply without a figure ("Here are the open invoices for Bayside Café."), stays `full`. §0.6 lets the reply's `detail` decide, and says "list their invoices" renders `full`. Reason: on the live model the prompt line alone was not followed (31 of 51 answer cards `full` in run 7). Cost if wrong: one click on Details. Since round 4 the `detail` prompt line and the reply tool's description no longer mention a lead-in.
- **Checks** (fictional data):
  - unit suite 428 OK at `50233e5` (372 before the slice); `desk_check.js` 73/73 (60 before); `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 at `d5d165a`, with no page code changed after; all on fresh scratch servers with the mock agent;
  - `conversation_check.js`, 23 scenarios and 108 turns: mock 310/310 (18 live-only assertions skipped) at `50233e5`;
  - live, local Gemma at temperature 0: after round 4, at `50233e5`, **325/325, 3 INFO, no reply withheld, no retry, no model failure, no failed suggestion**, 601 s. History: run 7 (`3351fd2`) 307/317, 10 INFO, 3 replies withheld plus 1 recovered on the retry, 2 model failures; round 1 (`f83ddfc`) 314/320, 7 INFO; round 2 (`6ca8d69`) 323/323, 4 INFO; round 3 (`80d164f`, the controller's re-run) 312/318, 10 INFO, 621 s, failing on numbered steps read as figures, a lead-in appended to keep short answers open, a runner gap when no question was asked, and a cite id the model truncated. The runs up to `80d164f` reported `coordinator-v0.3`;
  - `coordinator.py --print-prompts` equals PROMPTS.md's 12 `coordinator-v0.4` blocks (21 October);
  - the preview through its public URL: pending.
- **Rulings recorded while building** (reasons and costs in P003, "Revision 4"):
  1. the situation keeps the customer overview when `customerOverview` is off; the registry governs tools, not the picture;
  2. a tool's days and date must be grounded in the owner's text, a provenance check and not a phrase rule;
  3. a new suggestion version withdraws a preparation;
  4. a name a search found nobody for becomes the "not found" focus, and a following "their" asks which customer;
  5. `caseDetails` makes the card about the case's customer; display codes and invoice references are ids; a repeated identical call is refused as already answered;
  6. digits after a letter and a hyphen start no count; a word-for-word quote of a known line is exempt from the payment-judgement check only;
  7. a suggestion's within/beyond claim is withheld only when it is wrong for both the suggested and the asked date, and asked again once;
  8. scenario expectations that were wrong about correct behaviour were changed, not the product;
  9. a last sentence ending in a colon does not count toward the two-sentence rule, and the `detail` prompt no longer describes a lead-in (round 4);
  10. when the needs step asks no question, the runner records the owner's limit itself (checks only).
- **What it establishes:**
  - On 23 scripted conversations with fictional data, the owner's decisions said in words were prepared with code's date and committed only by Confirm decision; a tool turned off was neither offered nor run; a new suggestion on request went through the same checks; staff's next steps came from the workflow.
  - The page and the agent read the same role-filtered situation: tests check that the staff situation holds no owner-only line, question, suggestion or preparation.
- **What it does not establish:**
  - that people understand the desk or finish tasks with less work: the rubric's reader is a model, the human column is empty, and the effort comparison was not re-run;
  - any hosted model: none was connected or tested;
  - the model's quality beyond one local model at temperature 0 on scripted wording; wording differs between runs of the same code;
  - decision quality: E003's and E017's conditions, Q03 and Q05, are still not met;
  - use on a real phone or with a screen reader.
- **Limits:**
  - the situation's JSON widens the guard's known numbers;
  - spelled numbers beyond twelve do not ground days, and another number in the owner's message can (the prepared block shows the date before Confirm);
  - on the search path the model is not told that a name is a draft;
  - `customerOverview` and `invoices` give dates in ISO form only;
  - not exercised live: the suggestion's claim retry, the step-number rule and the runner's no-question path;
  - a cite id the model truncates fails the whole suggestion (owner-case #4 at `80d164f`); no code change;
  - live wording is not stable between runs of the same code;
  - the actions are not drawn on the page.

  The full list is in P003, "Revision 4", "What remains open".
- **The shared site** still runs `f95f50f`, with none of the three slices.
- **Next:** deploy to the preview, verify it through the public URL as both roles, then a team review and a decision on the shared practice site, through the established backup process and with guide revision 4.

## E022 — Nucleon Lab: a reuse experiment on the conversation layer (21 October; preview and root site untouched)

- **Status:**
  - This is an engineering experiment, built in the repository owner's (unitylht) development session on 21 October 2026 on the team's direction of that day.
  - Branch `explore/agent-coordinator-20261019`, from `6d1ee1b` (design and plan) to `3e52328`, plus this records commit. Prompt versions: `lab-v0.2` for the Lab's agent and `coordinator-v0.5` for the records' desk tools.
  - It is deployed as a third, separate instance at `/lab/`, with its own records instance at `/lab/records/`. `lab-v0.1` went out first, at `c454d9d`; the Lab now runs `3e52328`. The deploy and its verification are recorded in [DEPLOYMENT.md](DEPLOYMENT.md), "Lab instance (reuse experiment)".
  - Nothing else was touched. The preview at `/preview/` still runs `df10ab6` (`coordinator-v0.4`, E021) and is the comparison baseline. The shared practice site at `/` still runs `f95f50f` (E016). Not merged.
  - Not owner policy. Not a team decision to adopt a framework, a front end or the Lab.
- **The team's direction (21 October), as given:** investigate how far existing projects and frameworks can make Nucleon more natural and easier to maintain; deploy a working experiment; test it in a real browser as both roles, with full conversations and unfamiliar wording; compare it with the current preview on the same model and equivalent data. Further points from the brief:
  - reuse where it cuts maintenance;
  - treat the business API and tool layer as the reusable asset;
  - make capabilities configurable, with every implemented tool on per role in the experiment;
  - keep role privacy, and keep consequential commitments explicit;
  - fix general causes, not sentences;
  - keep cancelling a proposal distinct from declining a request;
  - disclose any preloading;
  - stay local-model first, with hosted APIs as a later comparison.

  Source: the design, `docs/superpowers/specs/2026-10-21-nucleon-lab-design.md`, §1 and §6.
- **What the investigation found** (design §2; research notes of 21 October, read from official sources that day):
  - **The causes of the seven review findings** were read from the preview's database and code. They were missing business operations, plus a guard that works around them ("digits must appear in results"):
    - no operation compared an extension without preparing one;
    - none withdrew a preparation, so "cancel" became a prepared decline;
    - none listed the work queue across customers;
    - the requests tool had no status filter;
    - nothing wrote a holding message.

    Neither the vanilla front end nor the lack of a framework caused them. Three spikes on the same local model confirmed it: a date tool answered the ten-day question; a withdraw tool made "cancel" a withdrawal; and a role filter stopped staff preparing anything, while the model still claimed it had, so a claim check remains a real requirement.
  - **LibreChat** (MIT, v0.8.8) has admin-enforced tool approval and per-user MCP headers. Against it:
    - it needs MongoDB, and this machine has no Docker; the install would be native, with Homebrew;
    - its config schema moved from 1.3.14 to 1.3.17 in five weeks;
    - it has no MCP elicitation;
    - it shows the model's reply unchecked;
    - the course brief warns that a generic chatbot does not meet the value proposition.
  - **Open WebUI** has MCP elicitation, but its tool approval is per user and experimental. Its licence is BSD-3 with a branding clause above 50 users.
  - **Dify** needs Docker Compose, even for a source install. It is a workflow builder, and its modified Apache 2.0 licence keeps the logo and forbids multi-tenant use.
  - **Pydantic AI** (MIT, 2.58.0, Python ≥ 3.11):
    - it has tools from functions, per-role `prepare` hooks, output validators with `ModelRetry`, usage limits and `FunctionModel` for tests;
    - it replaces the loop mechanics, and the prompts, role-scoped views and guard logic stay Nucleon's;
    - it moves fast: V2 in June, V3 already allowed, seven minors in three weeks, and four security advisories in those weeks;
    - its approval flow is "not an authorization boundary against an untrusted client".
  - **LangGraph** (MIT) adds graphs, checkpoints and interrupts that Nucleon does not need. Its Agent Server is Elastic-2.0, and self-hosting it for production needs an enterprise licence.
  - **assistant-ui** (MIT, 0.15.x) is React chat components built to static files with Vite. There is no Node server at runtime. Its 0.x minors removed APIs every two to four months.
  - **CopilotKit** (MIT) needs its own TypeScript runtime server, or an Enterprise-labelled direct mode. Its telemetry is on by default (Segment, Scarf).
  - **MCP** (spec 2026-07-28; Python SDK `mcp` 2.3.0): an MCP server over Nucleon's operations lets other agents use them, with the role taken from a bearer token.
- **Decision** (design §3): build **Nucleon Lab**, a third deployment at `/lab/`, with one reusable asset and three reused parts:
  1. **The business tool layer is the asset.** Framework-neutral operations live in the records server behind one HTTP surface: `GET /api/tools` and `POST /api/tools/<name>`, with the role from the session. Code computes every figure, date and comparison, and every result carries display text and its subject. Five new operations close the review's causes: `compareExtension`, `withdrawPreparation`, `workQueue`, `listRequests` with a status filter, and `prepareHoldingMessage`. Human-only operations are never offered to an agent.
  2. **Pydantic AI** runs the Lab's conversation loop. Its tools are those operations, called over HTTP with the person's own cookie; per-role availability comes from the registry; the guard becomes output validators with one retry.
  3. **assistant-ui** provides the chat: tool-call cards, a thread list and links into the records pages, with history rebuilt per role on the server.
  4. **MCP** gives the same operations to an external agent.

  Not built: LibreChat, Open WebUI, LangGraph, CopilotKit, and hosted model APIs. Hosted APIs can be configured but are untested.
- **The builder's calls** (design §7, stated so they can be overturned):
  - Confirm is a button that calls the records API, not a framework approval; the model is never in the commit path;
  - the Lab reaches the records over HTTP with the person's cookie, not in-process;
  - assistant-ui's local runtime uses a custom adapter over plain server-sent events, not AG-UI;
  - the Lab has its own SQLite conversation store, with a general thread and case threads, as the preview has;
  - the figure rule: a number or date must come from this run's results or from the person's own message;
  - MCP tokens map to a role in the Lab's config, with no OAuth.
- **Rulings while building** (the build ledger, `.superpowers/sdd/2026-10-21-nucleon-lab/`, kept on the development machine and not in Git):
  - the desk's registry gets the five tools too, on by default, so a gain is attributed by commit;
  - compare rules precede prepare rules in the mock;
  - staff's `forYou` leaves out reply drafts;
  - openRequest over the surface opens a case only from the person's message;
  - 401, not 403, without a session;
  - the amount mark "stated" is accepted;
  - `delta` carries the checked text once, with no token streaming before validation.

  After the browser comparison and the scripted run:
  - the reply became an output tool, so every model turn is a tool call;
  - the claim check covers any assertion that an action happened;
  - a retry with no tool called asks for the tools;
  - history stays text-only, and a case thread is shown its case each turn;
  - staff are told "The owner's guidance, limits and preparations are never shown to staff." instead of an untrue absence. The sentence replacement that enforces it is a phrase rule, accepted as a privacy guard on wording.
- **What was built** (`git log 31ac60d..HEAD --oneline`, oldest first):
  - `6d1ee1b` Nucleon Lab: design and plan for the reuse experiment;
  - `73e95d4`, `98e2448` the business tool surface: `GET`/`POST api/tools` and the five operations; one result per key, openRequest only from the person's message, model unavailable as a refusal;
  - `922f62c`, `32b1ccf` the Pydantic AI agent over the tool surface, with validators, store and SSE API; one run at a time per thread, approval claims always refused, amounts whole with their own mark;
  - `0305cfc`, `2aa4acc` the deployment: labctl, launch agent, Caddy route and e2e check, then a fix round;
  - `c454d9d` the assistant-ui front end, with tool cards and Confirm and Create through the records API (`lab-v0.1`, first deployed);
  - `4b05f5d` an MCP server over the tool surface, with bearer tokens per role;
  - `b2b890e` the scripted conversation check, with the mock and live runs recorded;
  - `7b23cd8`, `b90ea4d`, `f4e4c99`, `b31fe2a`, `8bea1c5`, `f3f75f9`, `781c1b5`, `52d8cb1`, `f10ee37`, `409d95f`, `14225ea`, `5165050` the fix wave (`lab-v0.2` from `b90ea4d`), covering:
    - claims in any voice, and references that are no figures;
    - the reply as an output tool, the case shown each turn, turned-off tools named, and notes on results;
    - withdrawPreparation's `invoiceReference`;
    - the MCP allow-list;
    - the access codes read from the records log;
    - the closed composer and exact pins;
    - the repeat rule, and the request limit ending as the fixed sentence;
  - `b44c31b` fix-wave round 2: past-passive and bare-participle claims, states the results show, reads after a change, made-up references;
  - `3e52328` the runner counts a prepareDecision claim only in a sentence about a decision;
  - this records commit: `coordinator-v0.5`, and these records.

  Details: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.5" and "lab-v0.2"; [lab/README.md](../lab/README.md); [prototype/README.md](../prototype/README.md), "The business tool surface"; [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 5".
- **Evidence** (fictional data; scratch servers unless stated):
  - **The records:** the unit suite is 443 OK (428 before; 15 tool-surface tests). `desk_check.js` is 74/74 with D12 added. At `73e95d4`, `ui_check.js` was 150/150, `layout_check.js --seed` 217/217, and the desk's `conversation_check.js` 310/310 on the mock.
  - **The Lab:** 87 unit tests at `b44c31b` (26 at Task 2, 34 after its fix round, 47 with MCP, 79 after the fix wave), and `lab_check.js` 58/58 in a browser on the mock.
  - **The Lab's scripted conversations** (11 scenarios, 40 turns; [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md)): the mock is 188/188 (184/184 before). Live, on the local Gemma at temperature 0:
    - `lab-v0.1` at `4b05f5d`: 187/205, 18 FAIL, 5 withheld, 1 error;
    - after the fix wave, `5165050`: 218/218;
    - round 2, `b44c31b`: 214/216 as the runner scored it. Its two FAILs were the runner's own detector, fixed in `3e52328`, so the run is 216/216 re-scored.
  - **The browser comparison** ([qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md); the builder's own sessions through the public URLs, both roles, the same model, equivalent preloaded data, disclosed):
    - the Lab answered what the preview could not: the cross-customer queue, "would ten days fit?" and three weeks, compared without preparing, and holding messages written by code;
    - the preview turned "cancel" into a prepared decline;
    - the Lab at `lab-v0.1` claimed a withdrawal and a new preparation with no tool call, so its Confirm would have committed the preparation the owner thought cancelled. That is the most serious finding, and the fix wave's reason;
    - no owner-only line reached staff on either site.
  - **The comparison's reading** (LAB-COMPARISON.md, "Reading"):
    - the tool surface closed review findings 2, 3, 5 (partly), 6 and 7 on its own, a gain that does not depend on the framework;
    - the framework made the loop small, but its defaults let the model skip tools and its first claim check let passive fabrications through; both are fixed;
    - the UI gave streaming, cards and a thread list for about a dozen files;
    - the preview would gain the same operations without any framework.
- **Recommendation** (the controller's reading in LAB-COMPARISON.md; a recommendation, not a team decision):
  - reuse the business tool surface, the asset that carried the gains;
  - reuse the UI components;
  - keep the conversation loop small;
  - the agent framework is optional: the loop mechanics it replaced are about 270 lines of the desk's own (design §2), and its default of plain-text replies had to be overridden.
- **Maintenance implications:**
  - **Python.** The Lab has its own venv (`~/srv/nucleon-lab/runtime-lab/venv`, 106 MB). It holds 42 packages, pinned exactly in `lab/requirements.txt`; the design estimated 45. Pydantic AI 2.58.0, `mcp` 2.3.0, Starlette and uvicorn are among them. A test pins pydantic-ai-slim 2.58.0 and the framework's own retry message, because the Lab reads that message.
  - **The page.** It needs Node 24 and the Vite toolchain at build time only (`npm ci && npm run build`; exact pins equal the lock; 121 packages, 125 MB of `node_modules`). The built page is about 770 KB of static files, served by the Lab.
  - **The records server stays stdlib-only.** The Lab imports `prototype/` for the coordinator's guard patterns, so both must come from one checkout.
  - **Operations.** A third instance means two launch agents, two ports, a Caddy route and `labctl`. The MCP tokens live only in the deployed config.
  - **Wording rules.** The Lab's guard is regex over wording, as the desk's is, so new wordings will need new tests.
- **What it establishes:**
  - On scripted conversations and in the builder's browser sessions with fictional data, the five operations let the same local model answer the review's questions: compare without preparing, withdraw without declining, show the queue across customers, and give a holding message.
  - A framework loop with output validators, a reply that is a tool, and Confirm as a records button committed nothing the owner did not confirm after the fix wave.
  - The same operations serve an external agent over MCP, by role.
- **What it does not establish:**
  - that people find the Lab more natural or do less work: the rubric's reader is a model, the human column is empty, and no person other than the builder has used it;
  - any hosted model: none was connected or tested;
  - the model's quality beyond one local model at temperature 0 on scripted wording; one full live run per code version, and the model varies between runs;
  - that a framework is needed: the gains came from the operations;
  - decision quality: E003's and E017's conditions, Q03 and Q05, are still not met;
  - a session from a real external agent: no Claude Code connection was made; the `mcp` client was tested on scratch servers.
- **What remains open:**
  - from fix-wave round 2:
    - with prepareDecision off, the owner is no longer told it is turned off; the reply misleads but makes no claim;
    - the state rule accepts "has been decided" or "approved" whenever any decision appears in the results;
    - staff asking to approve get the fixed sentence, not "only the owner decides";
  - the guard is regex;
  - the composer's lost text was never reproduced; the box is now closed during a run;
  - from LAB-COMPARISON.md:
    - the Bayside statement and "gimme the lay of the land" were not run on the Lab before the fix wave;
    - the public re-run after the fix wave is the controller's ("After the fix wave");
  - a prepared card does not know it was replaced, or decided before a reload; the records refuse a stale Confirm;
  - the thread list loads once;
  - one browser holds one role;
  - the bundle is one chunk of about 770 KB;
  - adding the five operations to the preview's desk is built (`coordinator-v0.5`) but not deployed there.
- **Next:** the controller's public re-run after the fix wave (LAB-COMPARISON.md), then a team review of the recommendation and a decision on what, if anything, goes to the preview or the shared site, through the established backup process.

## E023 — The Lab's second iteration: coherent revisions, prose first, understandable state, and Tony's ideas scoped (21 October; preview and root site untouched)

- **Status:**
  - An engineering iteration, built in the repository owner's (unitylht) development session on 21 October 2026, on the team's direction after the independent review of the Lab.
  - Branch `explore/agent-coordinator-20261019`, from `1d1840a` (design and plan) to `a0ab50d` (fix wave 2), plus the records commits.
  - **Prompt versions: `lab-v0.4` for the Lab's agent and `coordinator-v0.7` for the records' desk tools,** set in the final records commit.
    - The code carried the labels `lab-v0.3` and `coordinator-v0.6` until then.
    - The Lab ran the lab-v0.3 text as recorded at `30f35a4` at `d080fd6` and `6038696`, and earlier variants before that.
    - Fix wave 2 changed both texts without changing the labels ([PROMPTS.md](../PROMPTS.md), "coordinator-v0.7" and "lab-v0.4").
  - **Deploys.** The Lab was deployed several times during the iteration for the builder's browser checks: `a0ba992`, then `8fa7b5b`, `cf3cbaf`, `f3f616e`, `d080fd6` and `6038696` (the build ledger).
    - It was demonstrated at `6038696` from 14:22 Sydney time.
    - `a0ab50d` was deployed at about 15:20 for a team demonstration. It runs the lab-v0.4 and coordinator-v0.7 texts under the old labels until the next deploy.
    - The final deploy is recorded in [DEPLOYMENT.md](DEPLOYMENT.md), "Second deploy (21 October): revisions and presentation".
  - The preview at `/preview/` still runs `df10ab6` (`coordinator-v0.4`), and the shared practice site at `/` still runs `f95f50f`. Not merged.
  - Not owner policy. Not a team decision to adopt the Lab or any of its parts.
- **The review's findings** (design `docs/superpowers/specs/2026-10-21-lab-revisions-and-presentation-design.md`, §1). The independent review confirmed the Lab's gains: queues across customers, holding language, comparison without preparation, preparation in conversation, and a withdrawal that is not a decline. It found three things that make the Lab hard to trust through a conversation:
  1. a revision lost what the owner asked to keep, and left stale Confirm buttons;
  2. every retrieval was shown as a card and then repeated in prose;
  3. business state and navigation were unclear: an approved case still showed its old due date, and two requests had the same sidebar label.

  The team's direction: a natural assistant that stays understandable and dependable when the person changes their mind.
- **Causes** (design §2, read from the Lab's store and the records):
  - **Reason lost on revision.** The model passed the reason again, but the records accepted a reason only if it was in the current message. "Keep the same reason" contains none, so the reason became "No reason given; prepared on the desk.". A revision had no notion of keeping what was not changed.
  - **Stale Confirm buttons.** Each prepared card was drawn from the result stored with its turn, and nothing tied it to the live state. The server refused a stale version (409), so nothing wrong was committed, but the person could not see that.
  - **An invented explanation.** `caseDetails` carried only the active preparation, so the agent had no history to explain the earlier card from.
  - **"Current due date" after approval.** The case had one `currentDue`, the invoice's recorded date. Nothing named the approved date.
  - **Identical sidebar labels.** Thread titles were "reference · customer" only, and intake had no duplicate check.
  - **Cards repeated in prose.** The page showed every tool result as an open card, the model restated it, and tool names ("findCustomers: done") were shown as progress.
- **Decisions** (design §3):
  1. **A revision lifecycle in the records.** A preparation is a versioned proposal with a status: `current`, `superseded`, `withdrawn` or `confirmed`. A new `prepareDecision` while one is current is a revision: what it does not give keeps its current value. Every status change is an event, and `caseDetails` gives the owner the history.
  2. **One proposal card, drawn from live state.** Only a `current` card has Confirm. The others say "Superseded by version N", "Withdrawn" or "Confirmed", with no button. The state is read when a thread opens and after every turn.
  3. **Prose first.** A reply is its prose. Tool results fold under one closed "Records (N)", except the one card that is the answer or the action. The steps go under a closed "Activity". While a run is in progress, one human line is shown per step.
  4. **Understandable business state.**
     - The case gains `originalDue` and `dueNow`.
     - Thread titles carry the status and the asked date, and "(2nd request)" when there is an earlier one.
     - A likely duplicate is flagged, never merged or refused.
     - A case thread opens with a header: reference, customer, status, due now, asked date, and the amount with its mark.
  5. **Tony's ideas, scoped:** see the subsection below.
- **The builder's calls** (design §5): the history is stored on the request; the duplicate flag is informational; the "still holds?" question is generated by code after the model's questions, once per line; the progress lines are a fixed map from tool to phrase, not model text.
- **Rulings while building** (the build ledger, `.superpowers/sdd/2026-10-21-lab-revisions-and-presentation/`, kept on the development machine and not in Git):
  - **The "still holds?" question:**
    - it is asked about an expectation said before today, or a line more than 30 days old;
    - only lines the case cites, and not expired ones;
    - once answered it stays answered.
  - **Deciding through the form** while a preparation is current marks the preparation withdrawn.
  - **Concerns** are listed with what was said, for both roles.
  - **prepareDecision:**
    - a day count or date said implies approve;
    - a new decline must be said, and a decline word blocks the implied approve;
    - a reason said for an earlier preparation is kept;
    - an earlier preparation's figure counts only when the message states no figure of its own.
  - **workQueue** says `waitingOn: 'you'` for the caller's items and carries a summary line written by code. The live model had read the owner's own items as "not you".
  - **The claim guard:**
    - it grounds history explanations from the case;
    - a present-tense "prepared" needs a current version;
    - a refused call never grounds a claim.
  - **Which card is open:**
    - a list kind is open when every card of the turn is a list (the queue opens);
    - only the last preparation of a turn that prepared one is open;
    - settled proposal cards are compact.
  - **Titles.** The Lab's thread titles use the records' own status words (`case_label`, imported from `prototype/server.py`).
- **What was built** (`git log 47594b7..HEAD --oneline`, oldest first):
  - `1d1840a` design and plan;
  - **records** (Task 1): `9672de1` the preparation lifecycle, due dates, duplicate intake, staff concerns and the "still holds?" check. Fix rounds:
    - `5f54843` no times for the model, checks that stay answered, the outcome in the owner's words;
    - `8fa7b5b` a date said implies approve, and a new decline must be said;
    - `cf3cbaf` a reason said for an earlier preparation is kept, and an unambiguous work queue;
    - `d080fd6` figures said for an earlier preparation;
    - `6038696` any figure in the message blocks an earlier one;
  - **the Lab service** (Task 2): `bd356df` the case state to the model, `raiseConcern`, and cards and activity on the reply (`lab-v0.3`). Fix rounds:
    - `a5d6f40`, `f685eb6` and `4eb3285` history explanations grounded, with the tense rule;
    - `36c5823` a call grounds a claim only when it did its action;
    - `30775b5` a withheld reply falls back to what the records asked;
    - `f3f616e` the MCP test's queue assertion;
  - **the page** (Task 3): `2220a5c` prose first, live-state proposal cards, the case header and titles. `a0ba992`: no cached state on a reopened thread, compact settled cards, titles in the route;
  - **the builder's browser sessions:** `25ff1a2` and `65f2f9d` ([qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md), "Second iteration");
  - **scenarios** (Task 4): `a96a23b`, 7 new scenarios and their assertions ([qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Second iteration");
  - **fix wave 2:**
    - `58c7a7f` (records): a reason clause of the message is the reason, and a limit said with nothing prepared is asked about;
    - `749b313` (Lab): no card echo, the owner's reason clause passed, a limit is guidance, the app's question asked, and no holding card for a decision;
    - `a0ab50d` (Lab): the holding message's result says that its card shows the text;
  - `5b33eda`: local ledger data files ignored by Git;
  - the records commits: `30f35a4`, and the final one that sets `coordinator-v0.7` and `lab-v0.4`.

  Details: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.7" and "lab-v0.4"; [lab/README.md](../lab/README.md); [prototype/README.md](../prototype/README.md), "The second iteration"; [AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 6".
- **Evidence** (fictional data; scratch servers):
  - **The records:**
    - the unit suite is 463 OK after fix wave 2, re-run for the final records (461 at `a96a23b`; 443 before);
    - `desk_check.js` is 76/76 (74 before);
    - at `9672de1`, `ui_check.js` 150/150 and `layout_check.js --seed` 217/217.
  - **The Lab:**
    - 115 unit tests after fix wave 2, re-run for the final records (107 before it; 87 before the iteration);
    - `lab_check.js` 99/99 in a browser on the mock, re-run at `a0ab50d` (58 before). Its new checks cover live-state cards after navigation and reload, a stale Confirm (409, nothing decided), a card on a reopened thread that waits for a fresh read, titles, the header, folding and progress lines. A mutation that shows Confirm on a settled card fails it.
  - **The scripted conversations** (18 scenarios, 64 turns; [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Second iteration"):
    - the mock is 319/319, with 51 live-only assertions skipped (188/188 before). A negative probe with the new assertions flipped gave 106/150;
    - live, on the local Gemma at temperature 0, at `6038696`: 354/364, 6 INFO, 2 replies withheld (claim), and 2 runs over the 120 s limit. The new scenarios were 147/150. Their three FAILs all have one cause: the owner's reason not passed at the first preparation. A partial re-run of the two timed-out scenarios was 74/74.
  - **The builder's browser sessions** through the public URL ([qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md), "Second iteration"):
    - DEMO-201 was prepared, revised with the reason kept, withdrawn with no button left, explained from state, prepared again and confirmed. The history read v3 superseded, v4 superseded, v5 withdrawn and v6 confirmed;
    - at `d080fd6`, "put it back as it was: same date, same reason" re-prepared from the case's own history;
    - a staff concern in natural wording reached the case;
    - at 390 px there was no overflow.
  - **Fix wave 2** (`58c7a7f`, `749b313`, `a0ab50d`; [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "After fix wave 2"). It made one general change for each of the six findings of run 1:
    1. a reason clause of the owner's message is the reason;
    2. a statement of a limit is guidance, not a decision;
    3. the prose may not echo the open card (`no_card_echo`);
    4. the app's open question is asked, with where to answer it;
    5. a holding card is never open when a decision was asked for;
    6. no "today", "tomorrow" or "now" about a date (prompt only, model-limited).

    Its checks:
    - records 463, Lab tests 115, `desk_check.js` 76/76, `lab_check.js` 99/99, and the conversation mock 319/319 (51 skipped);
    - live, the 9 affected scenarios (the 7 new ones, owner-full-flow, staff-flow; 39 messages) went from 212/222 at `6038696` to **223/223** at `a0ab50d`, with 2 INFO, 0 withheld, 0 error events, in 597 s;
    - an intermediate run at `749b313` gave 221/221 with 2 replies withheld for echo, because the model quoted the holding script. `a0ab50d` changed the holding message's description and result note.
- **What it establishes:** on scripted conversations and the builder's sessions, with fictional data and one local model:
  - a revision keeps what the owner did not change;
  - a withdrawn or replaced proposal shows no Confirm, after navigation and reload too;
  - the agent explains earlier proposals from the case's history rather than inventing one;
  - a brief ask gets prose with the records folded;
  - the case shows its due date now;
  - two requests on one invoice are told apart.
- **What it does not establish:**
  - that people find it clearer: the rubric's reader is a model, the human column is empty, and only the builder has used it;
  - any hosted model;
  - stability between runs: one full live run;
  - decision quality: E003's and E017's conditions, Q03 and Q05, are still not met.
- **Still open:**
  - **after fix wave 2** ([PROMPTS.md](../PROMPTS.md), "Observed behaviour: lab-v0.3 and lab-v0.4"):
    - the reason clause wins over a kept reason: "Keep the same reason, since nothing changed" stores "nothing changed", and a time "since" ("since Monday") is taken too. The owner sees the reason on the card before Confirm;
    - `no_card_echo` checks the words the card prints from its result, not the card's composed lines (the figure limit covers those), and it does not check list cards;
    - the fix for stray "prepare" tools (finding 5) was not re-run live, because tool-off and staff-privacy were not among the 9 scenarios;
    - "today" about a date is addressed in the prompt only;
    - staff-flow #2's `textContains` "with the owner" is now INFO on the live model, since the prose no longer quotes the script;
    - the new question line leaks into a preparation reply: owner-full-flow #7 ("OK, approve 14 days.") ended "You can answer this here or on the case page.", where the next step is Confirm;
  - **the builder's notes:**
    - signing out during a run ends it with "Here is what the records show.";
    - a slow shared gateway makes two-call replies take over a minute;
  - **from the task reports:**
    - a suggestion can rest on an old line that no question cites, so no check is asked about it;
    - the NEEDS fallback reads only the last tool result;
    - "revised" is a claim verb for any subject;
    - the case header appears a moment after the messages;
    - the placeholder reason is shown as written;
  - **checks:** card repetition in prose is not asserted; the "still holds?" scenario uses lines more than 30 days old (no API backdates a line); 51 assertions are live-only;
  - **the guard is regex over wording.**
- **Next:** the final deploy and its verification (DEPLOYMENT.md), and the team's reading of the subsection below after the 1 pm meeting.

### Tony's questionnaire: what we adopted, what needs the team, what is future

Sources:
- Tony's Tally mock-up "Chatbot Questionnaire Scenario", as a teammate inspected and recorded it in [reviews/2026-10-21-tony-questionnaire.md](reviews/2026-10-21-tony-questionnaire.md) (21 October; nothing submitted). The form calls itself a mock-up of a flow, not evidence of what a chatbot can do;
- design §3.5.

The team's notes: [reviews/2026-10-21-tony-questionnaire-response.md](reviews/2026-10-21-tony-questionnaire-response.md).

- **Adopted now** (built in Task 1; fictional data):
  - **Check whether earlier knowledge still holds.** His page 4 reads: "You've last updated this relationship on the [A month ago] … Is this still the case?". Nucleon now asks the owner itself, as a question from the app (`from: 'code'`): "On <date> you said '<quote>'. Does that still hold for this request?". It asks this about an expectation said before today, or a line more than 30 days old, that the case relies on. Answering keeps a fresh line for that case; nothing is retired.
  - **Staff raise a concern.** This follows his page 17, "raising a approval concern to the owner". Staff say it in their own words (`raiseConcern`). The concern is kept on the case for both roles, and the owner's queue lists the case "because staff raised a concern". It decides nothing, and it needs no form or employee ID.
  - **Owner involvement is explicit.** It already was: the queue says what waits on the owner ("waiting on you"), and only the owner's Confirm on a prepared decision decides, with the owner's reason recorded.
- **Kept separate on purpose** (assumptions held until there is owner evidence, not owner rules):
  - **A one-off approval is a decision on one case.** Reusable guidance is a line the owner confirmed, with the scope the owner stated. His pages 5, 7 and 12 turn one answer into a standing rule ("make future decisions on your behalf"). AGENTS.md says not to do that without the owner's stated scope and authority.
  - **An extension of a due date is not a credit-limit or new-order decision**, and Nucleon infers neither from it. His pages 5 and 10 ask about approving over a credit limit. Credit limits are out of scope.
  - **"Good financial terms" or "good standing" is context the owner gives, not a recommendation.** His pages 15 and 16 tell the employee to ACCEPT or DECLINE. Nucleon gives staff no accept-or-decline advice; only the owner decides.
- **Needs the team's clarification:**
  - whether a yes on one case may apply "from now on", and for how long;
  - the reasons-skipped path: on his page 5, answering Yes to payments past the due date skips the reasons and the signature (rule R5 in the review). Is that intended?
  - the question set for A08: is the form a flow mock-up, the A08 question set, or both?
- **Future, not built:**
  - automatic decisions on standing authority;
  - periodic relationship reviews, which are not wanted as a questionnaire.
- **Assumptions awaiting evidence.** The business rules above are assumptions until owner evidence settles them (Q03, Q05). Vince's responses are pending.

## E024 — Agent-assisted import: a spreadsheet attached in the chat becomes a checked proposal, imported only by a person's press (21 October; preview and root site untouched)

- **Status:**
  - An engineering iteration, built in the repository owner's (unitylht) development session on 21 October 2026, after the second iteration (E023).
  - Branch `explore/agent-coordinator-20261019`. Design `docs/superpowers/specs/2026-10-21-agent-assisted-import-design.md`; plan `docs/superpowers/plans/2026-10-21-agent-assisted-import.md`.
  - **Prompt versions: `lab-v0.5` and `coordinator-v0.8`** ([PROMPTS.md](../PROMPTS.md)). v0.8 because the tool schemas and the classification prompt changed.
  - Not deployed (see [DEPLOYMENT.md](DEPLOYMENT.md), "Third deploy (21 October): agent-assisted import"). Not merged. Not owner policy, and not a team decision to adopt it.
- **The need.** Importing one spreadsheet through the Records page took about 28 dropdowns (the column of each field, the customer choices) and two uploads (invoices, then payments) for a single ledger. That is more work for the owner, not less, which the MVP is meant to reduce.
- **The design.**
  - A person attaches the file (.xlsx or CSV, at most 2.5 MB) in the Lab chat, or pastes rows. The agent calls `prepareImport` (the records' `proposeImport`).
  - The records read the workbook with a small stdlib reader (`prototype/xlsx.py`: shared and inline strings, numbers, serial dates by cell style or heading, a DOCTYPE refused anywhere in a part), find the header row, tell the shape (invoices, payments, or a ledger of debits and credits) and map the columns by their headings, in English or Vietnamese.
  - **The model is asked only about columns no heading names**, and sees their headings and three sample rows. Each answer is checked against the whole column before it is used.
  - A ledger is split by code: an invoice's amount is the sum of its debit lines once (VAT lines are not counted twice), and credit rows are payments. The proposal states the naming rule (a customer code becomes "Customer 0002" unless the person sets a prefix), the due-date rule, the counts, and the doubtful rows (opening balance, totals rows, a debit with no invoice number). All counts are computed by code.
  - The proposal is previewed against the records with the importer's own dry run and kept as a version. The Lab shows an import card: shape, sheet, mapping dropdowns, rules, counts, flagged rows. **Update proposal** makes the next version; **Import** (`applyImportProposal`, offered to no agent) writes two batches (invoices, then payments) through the importer's upload, mapping and apply, each revertable, only if the version matches and the records still preview the same.
- **Built** (`git log 66f9f6b..HEAD --oneline`):
  - `b97e50b` Records side: xlsx reader, ledger splitter, `proposeImport` and `applyImportProposal`;
  - `43781d6` Lab side: attachment, `prepareImport`, the import card with the Import button, `lab_check` I1-I8;
  - `7a9e2c5` ignores agent worktrees (housekeeping);
  - the commit that records this decision: retention of proposals (5 kept; the files of superseded or applied proposals dropped, their summaries and batches kept), the whole-part DOCTYPE guard, `coordinator-v0.8`, `classify_columns` in the prompt printer, and the records.
- **Evidence** (scratch servers, fictional data, no live model):
  - records suite 484 OK (463 before; `test_import_proposal.py` has 20 tests, covering dates, the ledger split, two-batch apply and revert, roles, a stale version, changed records, and what the model is sent);
  - Lab suite 119 OK (115 before); `deploy/lab_check.js` 113/113 (99 before; I1-I8 attach a fictional .xlsx, change a mapping, update to version 2, check that nothing is written before Import, import two batches and fit 390 px); `deploy/desk_check.js` 76/76 (Task 1);
  - the fixture is built in the tests from fictional rows in the shape of the team's ledger; no real file is in the repository.
- **Limits.**
  - **No live-model run of the import has been done.** The controller runs the team's file on the Lab after the demonstration; its result will be recorded in PROMPTS.md.
  - After a reload the card shows version 1 as stored. If that proposal was updated or applied meanwhile, Import returns the records' message (stale version or already imported) and no batch list is rebuilt.
  - **Update proposal bypasses the model:** it calls the records' `proposeImport` with the proposal id and the person's mapping, with no model call, on the stored file.
  - Only the newest proposal keeps its file. Updating an older one asks the person to attach the file again.
  - Model classification covers only columns no heading names; shape detection is heuristic (the person can set the shape).
  - Conflicts with recorded values, repeated payments, and "still owed" columns are not imported by a proposal: they stop it with a plain "import on the Records page to choose".
  - Amounts are shown in the workspace's currency format. A VND workspace shows them as whole dong with separators, not a separate VND style.
  - Unstyled date serials use the 1900 date system; a sheet over 20,050 rows is refused.
  - `records.name_key` folds `đ` to `d`, so "Đông" and "Dong" now match as the same name everywhere.
- **The real-data caveat.** The team imported a real ledger into the Lab's instance at `a0ab50d`, through the Records page (E023). The Lab's chat sends only the person's text and, now, the attached file to the records and the model sees only headings and three sample rows, but Q08 (data access and handling, the model's destination) is still open. Until the owner confirms it, a real file attached in the chat reaches the local model through those rows. Fictional data only is the rule for anything beyond the local Lab.
- **Not built:** automatic import without a press; editing individual rows in the card; multi-sheet imports; scheduled or repeated imports.

## E025 — Week 7 core flow: honest numbers, usable imports, explicit authority (21 October; preview and root site untouched)

- **Status:**
  - An engineering iteration, built in the repository owner's (unitylht) development session on 21 October 2026, after agent-assisted import (E024) and the team meeting of the same day.
  - Branch `explore/agent-coordinator-20261019`. Design `docs/superpowers/specs/2026-10-21-week7-core-flow-design.md`; plan `docs/superpowers/plans/2026-10-21-week7-core-flow.md`; inputs `docs/reviews/2026-10-21-team-meeting-and-model-review.md` and `docs/reviews/2026-10-21-tony-questionnaire-response.md`.
  - **Prompt versions: `coordinator-v0.10` and `lab-v0.7` at the final deploy** (`lab-v0.6` and `coordinator-v0.9` were the first, [PROMPTS.md](../PROMPTS.md) has each verbatim).
  - Deployed to the Lab only, final code commit `db86293` at 01:21 AEDT on 23 October (see [DEPLOYMENT.md](DEPLOYMENT.md), "Fourth deploy"). Not merged. Not owner policy, and not a team decision to adopt it. The root site (`f95f50f`) and the preview (`df10ab6`) are unchanged.
- **What the 21 October materials establish, and what they assume.** The meeting establishes the flow the team wants (import usable records, understand a payment-term extension request, get numbers from a fixed pipeline that humans configure and the AI cannot change, interpret them with the owner's context, recommend, act only within authority the owner set and escalate the rest, and record the decision, the reasons and any disagreement), the scope (extensions only, one currency per dataset, the AI proposes the import and a person presses once) and the evidence of what was broken (VND shown as AUD, a payment not matched to its invoice, a retrieval that failed after a reset and read as empty, "retrieving, not predicting"). It does not establish that a trained model is useful here: the labels in Hoang's data are proxies (an "approve" is a payment made while something was overdue and not refused; a "deny" is three customers the owner named), with 85 labelled payments, 8 denials from 3 customers and 2 holdout denials from one customer; the scores are class-weighted and uncalibrated; no model artefact is saved, the shipped cleaner is behind the notebook and the cleaned workbook is absent. The expectation that a confidence number would appear in the product, the owner's real limits, and whether staff would use the ask-first flow are assumptions or open (Q03, Q05, Q08 in [FACTS-AND-OPEN-QUESTIONS.md](FACTS-AND-OPEN-QUESTIONS.md)).
- **Decision: no approval model runs in the Lab.**
  - The product shows numbers that are facts computed from the records, and checks of those facts against limits the owner configured. It shows no probability, no confidence percentage and no "the model says approve". Where the meeting expected a confidence number, the product shows what it has: how many decisions are recorded, how many for this customer, and which checks pass.
  - **Evidence:** [reviews/2026-10-21-team-meeting-and-model-review.md](reviews/2026-10-21-team-meeting-and-model-review.md) sections 5 and 6: the labels are proxies; 8 denials from 3 customers in the one ledger studied (too few to measure); the scores are not probabilities ("82 percent risk" would be false precision); nothing is saved or reproducible from the supplied files. `assessRequest` returns `model: {status: 'unavailable', reason}` with the fixed reason text, and the Lab's conversation check asserts that no `%` appears in any assessment reply.
  - **What is portable:** the deterministic part of Hoang's pipeline, the ledger replay, is written with the standard library in `prototype/behaviour.py` using his feature names (`credit_term_days`, `debt_before_m`, `overdue_before_m`, `max_days_past_due_before`, `prior_invoice_documents`, `prior_billed_m`, `prior_received_m`, `prior_receipt_count`, `has_prior_receipt`, `days_since_prior_receipt`, `observed_relationship_days`, `prior_late_receipt_fraction`), so a model can be attached when there are real decisions to learn from.
- **The numerical pipeline and the recommendation.**
  - `replay` gives each figure as money in the workspace unit or a day count, and reconciles the debt against the customer's balance (`reconciles`, with the difference). Recorded allocations are used where they exist and the rest is FIFO; `allocationBasis` (`recorded`, `fifo`, `mixed`) says which, and the limitations text says FIFO is an assumption.
  - The replay runs as of the business date, not the date asked for: an extension is always asked for a date after the invoice's due date, so replaying "before the asked date" would make the invoice in question overdue and no case could ever pass "nothing overdue". The case invoice's own lateness is reported separately (`ownInvoiceText`), and "nothing overdue" tests the customer's other invoices.
  - `recommendation` is derived from the policy checks alone: all pass and a staff limit exists, `approve_within_authority`; a check the owner marked as a hard rule fails, `decline_by_policy`; otherwise `escalate`. Prediction, recommendation and authority are separate fields and are never merged into one word.
- **The authority model.**
  - The owner sets limits in Setup (`GET/PUT /api/setup/authority`, owner only, the whole object, unknown keys refused): `staffMayApproveUpToDays`, `maxOutstanding`, `requireNothingOverdue` (default true), `maxPriorLateShare`, `hardRules`, `maxConcernRounds` (default 2). With every limit unset, everything escalates. The agent reads the limits through `assessRequest` and can say a change in words; it has no way to make one.
  - `actWithinAuthority` (staff; pressedBy, offered to no agent, as Import is: the staff member presses Act within authority on the assessment card (the records tool, run as that person); the assistant never records it) works only when the current assessment says `approve_within_authority`. It records a decision with `decisionSource: 'staff_within_authority'`, the limits and the checks it rested on, and the reasons in words. Otherwise it is refused (`NOT_WITHIN_AUTHORITY`), the case is marked `escalated` with the failing check, and the owner's queue says "escalated: <check>".
  - The owner's decision records `decisionSource: 'owner'`, the recommendation at the time and `followedRecommendation` (null when the recommendation was `escalate`, since that names no outcome). Staff disagreement is `raiseConcern`; on an assessed case it records which recommendation it disagrees with, and after `maxConcernRounds` the case is marked `escalated: 'concern rounds'`.
  - **Scope of "from now on".** `remember` gains `until` (a date) and is carried on a preparation, so "for this customer until 31 December" is one confirmed guidance line with an expiry. The Lab's prompt asks "Does that apply to this request only, or to this customer from now on, and until when?" only when the owner's words imply more than one case. A standing rule is never inferred from a single approval.
- **Import rules.**
  - The unit is read from the file (a currency column or token: VND, đ, AUD, "$"; Vietnamese ledger headings mean VND). A mismatch with the workspace is refused with nothing written (`UNIT_MISMATCH`, status `refused`: "The file's amounts look like VND; these records are kept in AUD. Nothing was imported. Start a workspace in VND, or convert the file."). A file that does not say its currency imports as the workspace currency and says so. "$" is read as a dollar and fits AUD, USD, NZD, SGD, CAD and HKD workspaces.
  - A payment's invoice is read from its description or a reference column (`HĐ 73`, `hóa đơn 73`, `HD73`, `invoice 73`, `số HĐ 73`) and matched to that customer's invoice when it exists; a payment naming several invoices is flagged and left unmatched; unmatched payments count toward the customer balance, and FIFO is never applied at import. Customer codes stay as aliases so a search for the code finds the customer.
  - A proposal is read live (`GET /api/records/imports/proposals/<id>`): `proposed`, `applied`, `reverted` (every batch of an applied proposal was reverted: the card says "Reverted on <date>", and the same file proposed again is `proposed`, not `duplicate`), `refused` or `duplicate` (the same file hash was already applied and some batch of it is still applied). Pressing Import twice returns the same batches; a partly failed apply reverts its first batch.
  - "Still owed" per invoice is the stated amount, else total minus allocations with the basis in words; per customer, invoiced minus received, with the unmatched amount named.
- **The reset boundary.**
  - Records carry a `datasetId` (the time of the last reset, or the creation time). A retrieval after a reset that finds the customer gone drops that focus and says so in `notes`; the Lab never turns it into an empty answer.
  - A failed tool is never an empty result: when every call of a turn failed, the Lab's reply is "The records could not be read: <message>."; when one of several failed, a line names it; the claim guard withholds "nothing / none / no items" about a tool that failed.
  - Each Lab case thread stores the `datasetId` it was created under. Case threads from an earlier dataset open read-only, under "Before the records reset on <date>", and a new message to one is refused (`DATASET_CHANGED`). The general thread is exempt, since there is only one.
  - The operator demo reset gains `to: 'empty'`: an empty workspace with no settings, so the owner sets the currency (VND, 0 decimals) on Setup before the first import. The shared Lab's own transition is recorded in DEPLOYMENT.md.
- **Built** (`git log 60a9f59..HEAD --oneline`):
  - `3be2ad2`: the Lab's page (live import card, assessment card, authority panel, reset group, `remember` passed through);
  - `dfa5847`, `804f2eb`: `current` as a hint, `datasetId`, the empty reset;
  - `4743a1e`, `a38111e`: import correctness;
  - `b0ce594`, `c4bd9fc`, `fb0b00b`: the replay, the assessment, authority, `actWithinAuthority`, the decision fields, `remember` on preparations;
  - `5e8a2de`, `c18d3cd`: the Lab's failed-tool honesty, dataset boundaries and the two tools;
  - the commit that records this decision: seven conversation scenarios (`deploy/lab_conversations.json`), the check's new assertions, the mock model's rules, a claim-guard fix so that a staff approval within authority can be reported as approved, `coordinator-v0.9` and `lab-v0.6` in PROMPTS.md, and the documents.
- **Evidence** (scratch servers, fictional data, no live model):
  - records suite 547 OK; Lab suite 139 OK (after the final review's fixes);
  - `deploy/desk_check.js` 76/76 at `b0ce594`; `deploy/lab_check.js` 155/155 for the Lab's new cards and panel;
  - `deploy/lab_conversation_check.js` on the mock: 433/433 with 51 skipped (443 before the final review's fixes: the two staff acts became card presses with fewer lines) (319/319 before this iteration); the 7 new scenarios give 124 of those lines. They cover a new request assessed and escalated with the reasons (no `%`), staff acting within authority (`decisionSource: staff_within_authority`), staff refused outside it, `remember.until` 2026-12-31 on a preparation, two concerns escalating the case with the owner's queue saying why, a VND file refused in an AUD workspace, and a thread whose customer was removed (the note, never "no items"). A probe with the new expectations flipped failed 19 assertions (every kind of the new assertions except `noPercent`, which cannot be flipped).
  - The mock model reads "from now on, until 31 December" by keyword and the Lab's `prepareDecision` passes it as `remember`, so the scenario shows the path to `remember.until`; whether a real model asks the scope question is for the live run.
- **Limits.**
  - **Live runs were made by the controller by hand** (22 and 23 October, local model), not as the scripted live check, and the scripted check has not been run against the live model. The hosted APIs are untested.
  - **The real NTK import was run** on 23 October on `7f6f64b` and validated against the source (see the live-test paragraph below).
  - The matching of a description to an invoice reads digits after a keyword. If the real invoice numbers carry a prefix (such as HD0000073) a "HĐ 73" description will not match; that is a mapping question for the real file.
  - A payment larger than its invoice is matched up to what the invoice owes and the rest stays unallocated.
  - Overdue is judged by recorded due dates, not by extensions already granted (the original due date is kept).
  - Assessing writes a version to the case from a read tool; it does not change the request's version.
  - The numbers are one company and one year; they are not evidence about other businesses.
- **Deferred.**
  - **Hoang's classifier**, until real decisions exist to label it with (the hook is the feature set above). The owner's recorded decisions, and the disagreements, are the future training data.
  - **Credit-limit requests**, which are a different decision from an extension.
  - **Multi-currency workspaces**: one currency per dataset; conversion is the accountant's job.
  - **A rotating owner questionnaire** (Tony's idea, answered in [reviews/2026-10-21-tony-questionnaire-response.md](reviews/2026-10-21-tony-questionnaire-response.md); not adopted here).
  - Customer communications, the root site and the preview.
- **Live test, deploy and VND transition, 22-23 October.**
  - **Deploys** of the Lab (both halves, records first, local Gemma 4 26B-A4B model), AEDT: `c792a43` 00:50 22 Oct; `f1cabf9` 00:55; `3efe379` 01:27; `d74c33c` 23:41 22 Oct; `7f6f64b` 00:25 23 Oct; `7c6bec4` 00:48; `db86293` 01:21 23 Oct, the final code commit. `deploy/e2e_lab_check.py` 6/6 after each; the root site `f95f50f` and the preview `df10ab6` untouched. Counts at `db86293`: records 585, Lab 148, `lab_check` 174/174, `desk_check` 78/78, conversations on the mock 472/472 (51 live-only skipped), `deploy/validate_import.py` self-test ok and 0 discrepancies on a copy of the live records. Details in [DEPLOYMENT.md](DEPLOYMENT.md), "Fourth deploy"; the live runs in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md).
  - **First live night (22 October).** Thirteen findings (L1-L13) came out of it and were fixed. **Three honesty rules:** (1) an invoice with only a stated amount owed counts as open, and the replay never reports "nothing overdue" on an empty or unreadable picture; (2) where no amount still owed is recorded, the product says "overdue not known", never "none overdue", and the Lab guard withholds a claim of none overdue; (3) a money unit is detected from any sheet, doubtful magnitudes are refused rather than relabelled, and proposals made before the rules are re-checked or marked stale.
  - **The VND transition was done by a person pressing a button.** The controller's scripted reset had been declined by the permission classifier, so the product gained a console button, **New workspace** (`1169eef`), and the operator pressed it (22 October, 23:42-23:46 AEDT). Backups first. The Lab's conversation store was retired to a backup (restore steps in DEPLOYMENT.md). Setup: VND, 0 decimals, `Asia/Ho_Chi_Minh` (the team should confirm the zone), "NTK Co (team ledger, demo)". Authority: staff may approve up to 14 days, only when nothing else is overdue, up to VND 500,000,000 outstanding, 2 concern rounds.
  - **Import and validation.** One press by staff at 00:27 on 23 October (`7f6f64b`): 21 customers, 137 invoices, 113 payments, 60 allocations (60 of 113 payments matched by normalised references; 13 name an invoice not in the file; 40 have no reference), 4 opening balances as at 2 September 2025 (the day before the first entry; the file states no date). Three netting or adjustment rows and two negative reversals were left out and flagged. The validator checks 1-6 passed; check 7 (replay against an independent hand computation) passed after two replay fixes. Two customers reconcile only up to an unapplied credit and are reported as notes.
  - **Ruling made on the way: the owner's answer to a staff concern.** The concern loop had no owner side. `answerConcern` (owner only, an act, no confirmation) takes `needs_info`, `explain` or `guidance`, stores a case line visible to staff, sets `withStaff` ("Waiting on staff" for both roles) and restarts the concern rounds; guidance is also a confirmed statement for the customer with an optional end date. A decision stays `prepareDecision`. A staff reply to an owner's question is stored as a reply and is not a concern round. Cost if wrong: one extra tool and line kind. A negative opening balance is customer credit applied to later invoices, like a prepayment (replay ruling).
  - **Ruling: `withdrawRequest` is pressed by a person, never by the model.** And `openRequest` is refused inside a case, at both layers, after the model opened a stray request from a staff reply.
  - **Product changes of the resumed round:** capability line "Numerical analysis of the ledger and the owner's policy checks; no approval predictor." (the model status is still `unavailable`, and no probability appears); the case header shows invoice value, allocated payments and "still owed not stated" for requests analysed after the deploy; credits shown as customer credit.
  - **Live tests on the final build** (local model, both roles, cross-checked against the records): retrieval (0014 by code; invoice 59 settled for Customer 0001; "BNSO" honestly unknown; a correction to 0004 gives VND 0 owed); a routine case (0011, 00000087, asked 10 November) assessed within limits and acted on by staff (`staff_within_authority`, `followedRecommendation` true); an escalation case (0001, 00000079, asked 15 November, 34 days against 14) through staff concern, owner `needs_info`, staff reply, owner approval with a reason, revision to 8 November keeping the reason, withdrawal without declining, a request for the full date, and a confirmed version 3 (`decisionSource` owner, `followedRecommendation` null).
  - **Remaining, none blocking:** review 2, item 3: trimming private context out of an owner's answer to staff rests on the prompt (the tool checks only that the text appears in the message); minors: a past `until` is accepted, the opening as-at date changes on a longer re-import, `invoice_key` equates "1.05" with "1.5", recorded allocations above the payment are not capped; bare day-of-month dates are not resolved; a reason must be in the current message or an earlier preparation; the local model's cold start; hosted APIs untested.
  - **No approval predictor, and what it would need.** A predictor depends on validated decision records. Collecting the owner's decisions alone does not validate a predictor; the labels would still need review.
  - **Execution mode.** Staff Act and the Withdraw button are buttons a person presses. That is the current mode, not the aim: automatic action within the owner's authority is the intended product. Tool availability to the model, preparation and execution are different things and stay separate until the team decides otherwise.

- **Independent review and repair, 23 October.**
  - An independent browser review of the `db86293` build, run against the deployed Lab, found five failures. Causes, with what was shown by evidence and what was inferred:
  - **F1, same-day entries missing from the assessment.** Evidence: on a read-only copy, two QA invoices issued 2026-10-23 were stored, and both assessments (as of 2026-10-23) showed no prior invoices, no debt and the outstanding-amount check passing on VND 0; the replay read `day(date) < as_of` (`behaviour.py` lines 35-37), so same-day records never reached the facts, and the "incomplete" rule did not fire because the invoices were filtered out before it looked. The hypothesis that identity resolution picked the wrong invoice was ruled out (the request carried the right invoice id). Repair: history stays strictly before the date, current facts read up to and including it, and a target invoice absent from the current records makes the facts incomplete and escalates.
  - **F2, invoice facts confused.** Evidence: the model's invoice rows had only a still-owed text; no original total, allocations or payment references. Invoice 59 therefore read "VND 0 (at most)" and "no matched payment was found", an invention from an absence, and invoice 00000087 had its total withheld. Role filtering was not a cause. Repair: every invoice row carries the original amount, the still-owed text with its basis, the allocations with references, and a not-recorded line that keeps the original amount; a validator sends back an answer that omits a part that was asked.
  - **F3, every answer kind moved the case to staff.** Evidence: `answerConcern` set `withStaff` for all kinds, so guidance that kept the decision still sent the case to staff while the prose said it was with the owner. Repair: the caller chooses the next person, with defaults by kind; the records' rule, not the model's label, sets the next person.
  - **F4, the recorded decision reason hidden from staff.** Evidence: the reply to "what reason did the owner record" fell back to "Here is what the records show", because the model's quotation of the reason was withheld as a judgement claim and the fallback then hid it. Hypothesis not borne out: `caseDetails` already carried `decision.reason` for both roles on a decided case, so the key was not missing; it was the guard. Repair: one decision view in tools and the case summary, a prelude line, verbatim quotes of recorded text exempt from the validators (the assistant's own judgement beside the quote is still caught), and a fallback that states the recorded decision.
  - **F5, three smaller faults.** An internal instruction was shown as the error text of a failed customer switch (the model passed a name as a customer id; names and codes now resolve, and a refusal reads as a question). The "Request opened" card was a static snapshot taken before the case settled, so it stayed "Not identified yet" (it now reads the live case and says so). Compare took one date, so two dates were compared as one (it now takes two). A later live check also showed that a withheld reply about due dates hid facts the tool had returned (original and moved due date); the fallback is now built from the invoice rows (C6).
  - **Why the previous verification missed them.** (1) Replay and assessment fixtures used invoices dated before the as-of date, and the live routine case (0011) was an imported invoice issued on 30 September, so the same-day boundary was never exercised. (2) Live checks asserted status words, card presence and the recorded decision fields, not every requested fact in the prose; for invoice 59 "settled" was accepted without demanding the original amount and the matched payment. (3) The concern-loop live test exercised `needs_info` only; guidance was covered by a mock scenario whose expectation was written from the implementation, so it asserted what the code did. (4) No check compared the prose with the records for the same question across layers.
  - **What changed in verification.** Independent fixtures with hand-computed facts, including same-day entries; a fail-then-pass regression for each cause (the new tests fail with the source stashed and pass with it); scenario assertions on every requested fact (`textContains` and `textLacks`) instead of status words; responsibility checks in both roles (the next person, the queue wording and what each role can see); and an evidence table for the live run with the expectation worked out independently of the product, the visible result, the stored state and a pass or fail, kept in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md).
  - **Deployed:** `1720b0d` 15:09, `08b0a07` 15:27, `eb8eef0` 15:36 AEDT on 23 October (both halves; `deploy/e2e_lab_check.py` 6/6 each; root `f95f50f` and preview `df10ab6` untouched). Prompt versions `coordinator-v0.12` and `lab-v0.10`. Counts at `eb8eef0`: records 606, Lab 177, `lab_check` 185/185, `desk_check` 78/78, conversations on the mock 522/522 (51 live-only skipped). At `eb8eef0` all 13 live checks pass; three first failed or partly failed and were repaired (see the table). Not decided by this: the model still sometimes labels an information request as guidance or the reverse; the next person is set by the records' rule, so the state is right either way.

A boundary review of the repair commits (owner-only fields for staff, the same-day rule, the guard exemptions, `next` validation, customer resolution) found no blocker and one important weakness in the quote exemption, fixed in `0711955` (quoted text only, twelve characters or more). Minor items left open: an invoice with a total but no issue date is ignored by the replay without marking the records incomplete (only reachable by import or a hand edit); `followedRecommendation` is visible to staff (they already see the assessment's recommendation); a customer-name list in the "which customer" question stops at a full stop inside a name.

Repair D (23 October): the current-facts selection still required an issue date, so an active invoice without one silently reduced exposure and could make a request eligible (a second false-authorisation path, reproduced by the reviewer). The rule is now general: an active record with any amount counts for exposure; missing timing excludes it only from the history, with a stated basis; a record that cannot be placed (no due date on an open invoice, an undated payment without an allocation, an allocation to a missing invoice) makes the assessment incomplete and escalates. Fixed in `2c30d9f`, verified live on a fictional controlled case.

- **Round F, 23 October (a second retest of `2c30d9f`; deployed `991cf31` 20:43 and `196c3ee` 21:12 AEDT, both halves, e2e 6/6 each).** Five faults, each with a fail-then-pass regression, then a testing account for AI agents.
  - **A, an unknown overdue state shown as "no overdue".** The facts printed "Nothing is overdue" whenever the known overdue amount was 0, and the nothing-else-overdue check treated 0 as a pass; a missing due date only fed the "incomplete" flag. Now the replay reports open invoices without a due date, the facts say "Overdue not known", and the check is unknown (it cannot pass, so staff cannot act, and it never declines by policy). The same rule covers the late-history and outstanding-amount checks. The recommendation stays escalate.
  - **B, a staff decision shown as the owner's.** The case page and the Activity line had "The owner" written into them for every decision. The stored decision was right (`decidedBy`, `decisionSource`). One function now reads the decision source first.
  - **C, an older guidance card inventing a staff reply.** The Lab card fell back to "Staff have replied" for any answer that was not the one the case still waited on. It now reads the records' own order of answers, staff lines and decision.
  - **D, a manual amount labelled as the customer's words.** The evidence text had no branch for a stated amount, so it fell through to "Customer's words". The invoice's own change record (who, when, from which import) now travels with the fact and is shown.
  - **E, a stale "Request opened" card.** The card read the case once, so a case still preparing stayed so until the user left and came back. While the case is received or analysing the card re-reads every 3 seconds and stops when it settles.
  - **The AI Agent testing account.** One code (`accessCodes.agent`, demo instances only) creates three sessions at once (staff, owner, and the console where it is on) for one actor, `ai_agent`, named "AI Agent". The effective role of a request is the role its header names, which must be one of the held sessions, so staff mode meets the real staff restrictions and permissions are unchanged. The audit trail carries `actorName` and `actorRole` beside the id on events, decisions, concerns, answers and provenance; pages show "AI Agent (as staff)" or "AI Agent (as owner)". The Lab keeps the chosen role in a cookie, sends it with every request to the records, and shows a Staff/Owner switch and a Demo console link in its banner. Prompt `lab-v0.11` adds one rule so the model does not call an unknown overdue state "none overdue".
  - **Counts at `196c3ee`:** records 628, Lab 187, `lab_check` 213/213, `desk_check` 89/89, conversations on the mock 530/530. Live rows 14 to 25 all pass (`docs/qa/LAB-CONVERSATIONS.md`).
  - **Limitation.** Analyses stored before `991cf31` keep the older provenance wording ("Entered manually" or "Customer's words"); only new analyses carry who entered an amount, and an invoice corrected in another field later shows that later date. Other limits are in the hand-over.
- **Round G, 23 October late evening (deployed `0a7f612` 22:21, `4b1b901` 23:09, `5282b3d` 23:21 AEDT, both halves, e2e 6/6 each).** The last attribution error, a backed-up clearing of the fictional data, and a full journey test with the AI Agent account on the cleared workspace (table rows J1 to J53).
  - **Attribution.** The due-date provenance said "Set by an earlier owner decision" for a staff approval because the sources kept only `decidedAt` and the records page hard-coded "owner decision"; the decider is now read from the decision source (owner, staff within authority, or the AI Agent under its role).
  - **Shared role.** The records UI kept its own role while the Lab switched, so a payment entered during the journey was stored as "AI Agent (as owner)" while the Lab said Staff; the selected role is now one cookie read by both halves, and a request marked to follow the role gets a 409 when it changed.
  - **Replies.** The reply rule applied only after an information question, so a staff report-back after guidance counted as a concern round; a staff message is now a reply whenever the case is with staff because of any owner answer.
  - **Same-turn assess.** `assessRequest` on a case still analysing raised inside the handler and surfaced as "Invalid JSON or field format."; the records now answer `CASE_PREPARING`, and the Lab neither sends nor shows it in the turn that opened the case.
  - **"current".** The refusals came from messages sent in General after a role switch returned the view there (G9); "current" now also resolves to the customer's one open case outside a case thread, and a refused call that a later call answered shows no alert.
  - **Owner statements.** There was no "understood" card, so "record a private note" looked kept; the card and a guard now say that nothing is recorded until the owner confirms it on the records page.
  - **Recorded reason.** The reason check passed before the private-context rewrite merged the reason into the fixed "has not shared" sentence; the check now runs last.
  - **Staff and the limits.** No rule covered a staff request to change the limits, and the model claimed it had noted them; the Lab now answers that only the owner can, with no tool call, and a guard withholds any "noted/changed" claim.
  - **Terms and payment provenance** were added to the overview so those questions are answered from the records rather than as guidance.
  - **Open.** G9 the role switch returns the view to General silently; G10 owner guidance on a case without a concern becomes a statement; G11 a question by due date can be answered about the wrong invoice (the invoice card is right). None blocks the demonstration flow; work-arounds are in the hand-over.
  - **Counts at `5282b3d`:** records 638, Lab 198, `lab_check` 218/218, `desk_check` 93/93, conversations on the mock 531/531; prompts `coordinator-v0.12`, `lab-v0.12`.

- **Round H, 23–24 October (deployed `dc8893f` 00:24 and `a19f3d6` 00:38 AEDT 24 Oct, both halves, e2e 6/6 each).** A focused round on the retained workspace.
  - **Invoices by date (G11).** The model had no way to select invoices by a date and picked an arbitrary one; the `invoices` tool now filters by `dueOn`/`issuedOn` against the original and the approved due date, says which matched, and a guard requires the prose to name every match and no other; a one-presentation rule that cut the prose to two sentences was the second cause.
  - **Case kept across a role switch (G9).** The Lab remounted on a switch and lost the thread, so messages went to General and "current" had no case; the thread id is carried over when the new role can see it, else the view says it returned to General. The "current" fallback outside a case thread resolves only with exactly one open case; two or more ask which; none says so.
  - **Guidance before a concern (G10).** Case guidance with no concern was read as a customer statement; it now routes to answerConcern (which already accepted it), reads "the owner gave guidance" on the first guidance, and a saved guidance is never followed by a "not saved" fallback.
  - **Import mis-allocation (H1).** Reference normalisation let a payment match an invoice issued after it (293 days later in the ledger); a reference now matches only an invoice issued on or before the payment date, the proposal flags the rest, and `validate_import.py` reports payment-before-invoice allocations independently of the normalisation. The deployed workspace keeps the three affected allocations until a re-import.
  - **Opening balance in the debt sentence (H2).** The sentence used the full opening balance; the replay now returns the remaining part and the sentence names it.
  - **Stale role in another tab (H3).** A Lab turn followed the shared cookie role, not the role the tab showed; Lab requests now carry the tab's role, a mismatch is refused with 409 ROLE_CHANGED before anything runs, and the tab shows a notice and refreshes.
  - **J37 corrected.** The hand expectation was wrong, not the replay; the claim that all figures matched exactly is withdrawn for the overdue amount.
  - **Counts at `a19f3d6`:** records 645, Lab 209, `lab_check` 224/224, `desk_check` 93/93, conversations on the mock 540/540; prompts `coordinator-v0.12`, `lab-v0.14`.
- **Round H addendum, 24 October (`61ab06b`, validator only; the deployed application stays `a19f3d6`).** The validator's hand replay matched payment references without the payment date, so it was not independent of the importer on the payment-before-invoice rule and agreed with it for the wrong reason; fixed, with hand-computed self-test regressions, and re-run on a fresh isolated import of the cleaned workbook: 0 discrepancies, the three issued-after references unmatched, Customer 0018 VND 2,538,005,400 owed and overdue with no opening balance remaining. The Round G and Round H claims that the validator had independently confirmed the allocations are qualified accordingly.
- **Finishing phase, 24 October (deployed `076d324` 11:08 AEDT, both halves, e2e 6/6).** Calculation details generated from the replay itself (no model narration, no second calculator): a trail recorded inside the replay loop, a basis stored with each assessment and frozen on each decision (later record or authority edits do not rewrite it; verified byte for byte), exposed to both UIs behind a closed section and to the Lab through a records endpoint. The model never sees the full basis. Two live defects found by the behaviour test and fixed: a decided-case question answered with invoice facts (O1) and an ambiguous case reference resolved silently from the thread focus (O4; the check now applies to every write outside a case thread whatever requestId the model found). Payload note: a basis for a large customer is about 200 KB and is stored several times per case; acceptable for the local proof of concept. Open: cosmetic nits O3, O5–O8 (hand-over). **Counts at `076d324`:** records 663, Lab 218, `lab_check` 236/236, `desk_check` 96/96, conversations on the mock 540/540. Prompt versions `coordinator-v0.12` (records, unchanged), `lab-v0.16` (Lab); calculation version `calc-v1`.
- **Final repair and acceptance round, 24 October afternoon (deployed `ac87e27` 17:22 AEDT, both Lab halves, e2e 6/6; branch pushed, main untouched).** Six application commits after `076d324`: `3abff6b` interface states follow the records after a refusal, a reload or a role switch (superseded cards with no enabled control, refreshed assessment beneath, ambiguous case asks which and prepares nothing, thread titles from the records); `8ea5ee2` a failed turn says what the records did, writes keyed by the turn so a resend writes once; `a4faa3a` latency instrumentation per model request and phase, owner-only staff asks answered without the model; `5f385ae` + `5318e61` + `16d3ac9` the opt-in presenter panel (fictional workspaces only; Fill, Open case, role buttons, Warm, build and business date; a right-hand column that never covers Send; a Keep warm toggle, 30 s, kept per tab; it never presses Send, Act or Confirm); `c167509` an owner's private-note message must be read with interpretStatement or the reply says nothing was recorded; `2b6018c` several customer matches ask which customer instead of reading one; `ac87e27` staff are never pointed to an Act button the assessment does not offer. Latency: the 90–200 s first requests were the local model paged out after an idle gap of about 90 s or more (swap nearly full on the 32 GB machine), not prompt size or tool schemas (6.3k-token prompt 6 s on an active model; 17 tool schemas 3.7 s); mitigation is Keep warm plus freeing memory before the demo. No response caching: every answer is a fresh model result. Acceptance with the real model on an isolated fresh workspace: 70-odd rows, all PASS after the fixes (evidence-final-round.md); two operator-paced rehearsals 4:23 and 4:29, above the 3:30–3:45 target at a 10–15 s narration per card. **Counts at `ac87e27`:** records 670, Lab 244, `lab_check` 275/275, `desk_check` 97/97, conversations on the mock 540/540; prompts `coordinator-v0.12`, `lab-v0.17`; `calc-v1`.

- **Replay, balance and stale-instruction round, 24 October evening (deployed `0d54e9f` 22:34 AEDT, both Lab halves, e2e 6/6; branch pushed, main untouched).** Decisions recorded: (1) a resent turn (the same turnId) is answered only with the agent turn stored for that person turn (`turns.reply_to`), and only to a role that may see it; an interrupted turn stays unanswered; a turnId reused with other words, another file or under another role is refused (409 `TURN_CONFLICT`); an older answer without the link counts only when it is the very next row in the thread with the person turn's visibility (`732165f`; Codex's reproduction failed on `ac87e27`). (2) What a customer owes is "owed now" from the same replay as the assessment (`calc-v1`, unchanged), split into overdue, not yet due, no due date and the remaining opening balance, with a credit held said apart; the recorded invoices less recorded payments appears only under its own label and only where it differs from owed now; open and overdue counts and the case invoice follow the same figures; overdue stays judged by the original due date and says so where the owner approved a later one (`4e120d0`, `df2abb8`, `06d559c`, `b28410d`, `da6f501`; prompts `coordinator-v0.13`, `lab-v0.18`). Customer 0012 reconciled: owed now VND 272,687,040, all overdue on 23 and 24 Oct, the opening balance of VND 50,213,520 paid by the 26 Sep 2025 payment, recorded net VND 222,473,520. (3) An earlier answer's words fold behind a line from the records once its card's action is done, superseded, withdrawn, decided without it, no longer holding, or another role's (`e0267fa`, `8df738c`); stored history is never changed. (4) Keep warm runs on the server and its readiness line is truthful (ready only after a success within a minute; slow while a warm-up waits more than 5 s) (`171fe39`, `9d21aba`). Correction: the long turns are contention for the single local model with another application on this network, not paging after idle; the earlier explanation is withdrawn. Rehearsals of the shortened script: 3:22 and 3:29 in quiet windows; three attempts failed while that application was generating. Evidence: `docs/qa/LAB-CONVERSATIONS.md` Sequence 8; ledger `evidence.md` of the round.
- **Financial completeness contract and MCP operation-safety audit, 25 October (branch `feat/financial-completeness-contract-20261025`, from the deployed `0d54e9f`; not deployed).** Decided: (1) `customerOverview`, `invoices` (also when filtered), `caseDetails` (through its customer) and `assessRequest` carry one additive `completeness` object next to any customer-level figure, from `records.coverage_view` and `owed_position` (no second algorithm): per kind (invoices and payments judged apart) `completeTo`, `state` (`complete` only when confirmed to the business date or later; `completeToEarlierDate`; `notConfirmed`), `lastActivity`, `recordedCount`, `contradicted`; `balanceEstablished`; stable reason codes; a deterministic `caveatText` with no amount. No payments recorded is never proof of no payments unless payments are confirmed complete to the date. `balanceEstablished` says the records support a balance; it changes no mark: a figure worked out from records stays "worked out". It also needs the customer-level prerequisites `exact_outstanding` uses (opening balance, credits stated, opening records answered), factored out unchanged as `records.customer_blocks`. `invoices` adds `scopeText` (a list is not the account position). A customer that is not found stays an error. (2) MCP audit by what a call stores: pure reads (`findCustomers`, `customerOverview`, `invoices`, `ownerContext`, `cases`, `caseDetails`, `whereIs`, `compareExtension`, `workQueue`, `listRequests`) store nothing, checked by a table-hash test; `assessRequest` is a read in kind but keeps the latest assessment on a case not yet decided (version + 1), so it is not read-only (descriptions corrected); `prepareCustomer`, `prepareHoldingMessage`, `interpretStatement` keep no business record; `prepareDecision` and `proposeImport` keep a preparation and a proposal; `withdrawPreparation` and `requestSuggestion` change the case. The Lab sets MCP annotations (`readOnlyHint` only for the audited reads, fail closed; `destructiveHint: false` where nothing is removed; `openWorldHint: false`): advice for the client, role gating stays in the records. Noted, not changed: over MCP every prepare/act call gets a fresh random idempotency key, so a client retry repeats the effect. Open: whether a small model quotes the caveat is not shown by these tests.
- **MCP write idempotency, 26 October (branch `feat/mcp-write-idempotency-20261026`, from `f4a9b96`; not deployed).** Decided: (1) Identity comes from the client, never from the model's arguments: an MCP client may send `_meta` key `nucleon.lab/idempotencyKey` (8–128 characters of letters, digits, `. _ : -`); the Lab sends the records `mcpc-` + a hash of the bearer token, the role and that key, so a key is bound to the token and role that sent it and the token is never stored or logged. Without the key each call is a new operation (`mcp-` + a random id, as before); identical arguments are never taken for a retry. Non-read results carry `_meta` `nucleon.lab/operation` `{keySource, replayed}`; read-only results are unchanged. (2) In the records, an act or prepare tool, and `assessRequest` when a key is sent (it keeps a new assessment version), runs once per key. The scope is actor, role, tool and key (the AI Agent has one id for both roles, so its owner answer is never replayed to a staff session), claimed in `record_ops` after the role check. States: `pending` (this boot) -> `applied` -> `done`. The `applied` mark is written by the connection in the same SQLite transaction as the business write, so after a crash `applied` means the change committed and a still `pending` claim of another boot means nothing did (it is reclaimed). A retry gets the stored answer with top-level `replayed: true`; other input under the key is `KEY_REUSED`; a concurrent retry (also while a model-calling tool waits for the model) is `OPERATION_IN_PROGRESS`; a committed change whose answer was lost is `OPERATION_RESULT_UNAVAILABLE` and is never run again under that key. (3) A refusal that changed nothing is not kept (`MODEL_UNAVAILABLE`, `CASE_PREPARING`, a missing message...): its claim is dropped, so a retry is judged on the records as they are then; before, only `MODEL_UNAVAILABLE` was dropped and any other refusal stuck to its key. (4) Finished tool answers are kept 90 days (pruned at start and after a restore, only `done` rows of this scope); a retry later than that is treated as new. `record_ops` gains `state` (default `done`), `at` and `boot` additively, so rows and answers from before replay as they did. Records stays one process: the key's primary key and the claim commit are the guard across requests, the in-process lock only orders them. Limitation: LibreChat v0.8.8 sends no `_meta` key, so its repeated or re-issued tool calls are distinct operations; only clients that send the key get deduplication across MCP retries. Lab to records resends were already keyed.
- **Controlled agent actions, design only, 26 October (branch `docs/controlled-agent-actions-20261026`, from `c69d521`; nothing implemented or enabled).** Proposed in `docs/CONTROLLED-AGENT-ACTIONS.md`: the first controlled action is a Staff payment-extension request prepared by the assistant (`prepareRequest`, a prepare kind) as a Nucleon-minted `actionId` in a new `actions` table, confirmed by a person on a Records page (`#/actions/<id>`) opened from the card through an allow-listed MCP-UI `link` handler (LibreChat patch 0003), and executed through `App.create` with key `action:<id>` (the permanent create idempotency), so retries, reloads and restarts resume one request. A LibreChat card `tool` action is not a confirmation (LibreChat sends it to the model). Confirm re-checks the person's current staff session (service sessions refused), the customer's evidence version and one open request per invoice; Staff confirmation submits a request and approves nothing; Owner decisions stay on the existing flow (Phase E). Local M3 runtime now runs `c69d521` (reused database, additive `record_ops` migration; MCP checks 33/33).
- **Controlled agent actions, Phase A (Records backend only), 26 October (branch `feat/controlled-actions-server-20261026`, from `a12e121`; not deployed, nothing enabled).** Decided, correcting the design in `docs/CONTROLLED-AGENT-ACTIONS.md`: (1) The invariant: the business effect of a confirmed action (customer, invoice, requested date, that it is a request for the owner and never an approval) is fixed by code; no model or later answer may alter it, and any path that could fails closed. (2) The request a confirmed action opens is built by application code only: it takes customer, invoice, date and reason from the action's frozen values (`intake.structured`), is never read by a model, and is never sent to the manual fallback (which reads answers and the message); the worker, `commit_outcome`, `fallback_or_fail`, `answer` (409 `CONFIRMED_FIELDS_LOCKED`), recovery and "Prepare again" each guard this. This replaces the design's "intake template + mismatch detection". If the records stop supporting the frozen values the case needs information that nobody can give and says to withdraw it and prepare a new action. (3) Confirmation is one SQLite transaction under the lock (revalidate against the records now, create the request through the same `new_request` as `create`, build the case, record the idempotency row `action:<id>`, mark the action executed), so there is no `confirming` state: five states (`proposed`, `executed`, `invalidated`, `cancelled`/`superseded`/`expired`), a read reports expiry without writing. (4) Only a person confirms: a session that is not the AI Agent and not marked `channel: 'service'` (the Lab's `sign_in` sends it), from a browser (an `Origin` header is required: 403 `ORIGIN_REQUIRED`), with an Idempotency-Key convention; the owner cannot confirm. Stated plainly: Records has role-level identities only, and the service mark is set by the client that signs in. (5) `prepareRequest` and `actionStatus` are `defaultEnabled: False`, so they are in no registry (desk, tool surface, MCP, LibreChat) until the owner turns them on; the `actions` table is additive. Action rows and their idempotency rows are permanent business records until reset; archiving is future work. Not built: the card, the confirmation page, the LibreChat link handler (Phases B to E). Noted, not changed: staff may still act within the owner's authority on a confirmed request like any other, and a confirmed request gets no model suggestion.
- **Controlled agent actions, Phase B (Nucleon side), 26 October (branch `feat/controlled-actions-ui-20261026`, from `1324a2e`; not deployed, nothing enabled).** Decided, correcting Phase A after review: (1) A request opened from a confirmed action is decided only by the owner: `actWithinAuthority` on one is 409 `OWNER_REVIEW_REQUIRED` before anything is assessed or stored (the only two code paths that set `decided` are the owner's `decide` and that staff tool, pinned by a source test); other requests keep staff-within-authority. (2) The reason is frozen: the request's reason is the assistant's `params.reasonDraft`; the confirm body is `{version}` and a `reason` that differs is 400 `REASON_FROZEN`; a replay no longer compares reasons. (3) The server, not the client, decides service versus person: per-role **service codes** (config `serviceCodes`, else random; printed as `STAFF/OWNER service code:` lines apart from the access codes) make `channel: 'service'` sessions; access codes and the agent code always make person sessions; the login's `channel` field is ignored; `/api/session` returns `channel` and the session's `csrf` token; confirm and cancel need `X-Nucleon-CSRF` (403 `CSRF_REQUIRED`) beside Origin, JSON, key, role staff, not the AI Agent, not a service. The Lab signs in with the service codes (`recordsCodes` now means those) and fails closed if the session it gets is not a service's. The sign-in remains role-level and shared: whoever holds the person staff access code can confirm; the Lab and its configuration cannot. (4) `prepareRequest` says it stores a proposal and supersedes the invoice's previous live one, and stays not read-only and not harmless-marked. (5) The confirmation page `#/actions/<id>` (desktop; read-only reason; "Submit for owner review", "Cancel proposal"; a lost response re-reads the action and offers the same key again; the owner sees it read-only with cancel only) and the Lab's proposal card (`prepareRequest`, `actionStatus`; "PROPOSED — NOT SUBMITTED" until an executed `actionStatus`; one link button only when `recordsPublicUrl` and the result's `actionId` fit the contract with LibreChat patch 0003) were built; the confirmed request's case page says it is not AI-prepared and shows "Submitted by staff for your review". Why: Phase A let staff decide what staff had just submitted, let a page-typed reason replace the frozen one, and trusted a client-declared channel. Limits: no per-person identity; the Lab and records must deploy together; the AI Agent test account's owner session can still decide any request. Evidence: `docs/CONTROLLED-AGENT-ACTIONS.md` (Phase B), `docs/PHASE-B-TEST-ENVIRONMENT.md`.
- **Adaptive Decision Authority, first vertical slice, 26 October (branch `feat/adaptive-decision-authority-20261026`, from `f4febc2`; not deployed, everything off by default).** By the user's product direction (product memory PM-001, PM-008 to PM-015), the AI agent may make an internal credit decision that takes effect with no per-case Staff or Owner click, but only within a versioned Owner delegation policy that the backend enforces. (1) The policy (`delegation_policies`, append-only, version 0 = advisory, nothing executes) is written only by an Owner person session (`person_required`, CSRF, Origin, `expectedVersion`), validated strictly; pause/resume are new versions; no tool or service reaches it. (2) `delegation.evaluate` keeps three dimensions apart (evidence sufficiency from records or Staff confirmation on a Nucleon page, never model text; business risk against per-decision, per-customer and 30-day autonomous exposure, days, overdue, late share, unusual size, held customers, unknown never zero; track record = the current policy back-tested on a held-out fictional evaluation set, a simulation) and applies a fixed handling order: policy hold, owner review, request evidence from Staff, then approve only if every step passes and the assistant recommended `approve` or `approve_if_verified`. The agent never declines on its own authority. (3) An approved extension is an ordinary request decision (`decisionSource: delegated_policy`, `decidedBy: nucleon_agent`, policy version), so the effective due date moves through the existing code; trial credit is a credit line on the case. (4) Decision memory (`decision_cases`, `confirmed_facts`): evidence, recommendation history, authority, Owner feedback/override (an override replaces the decision and keeps the history), outcome from the records; comparables come only from examples and live cases and are labelled analogies; deterministic policy suggestions never apply themselves. (5) MCP tools `assessDecision` (stores nothing), `resolveDecision`, `decisionStatus` (off by default); decision/Key Facts card; Owner page `#/delegation`; evidence page on the existing `#/actions/<id>`, so LibreChat rc3 needed no change. Why: the product goal is to remove unnecessary Owner and Staff decisions, not to move the approval click; the existing `OWNER_REVIEW_REQUIRED` guard and Phase B flow are kept for non-delegated work. Limits: fictional thresholds and data; role-level shared logins; no outbound communication; no auto-decline. Evidence: `docs/ADAPTIVE-DECISION-AUTHORITY.md`, `docs/ADA-LOCAL-ROLLOUT-PLAN.md`, `~/Developer/nucleon-ada-test/evidence/`.
- **One list of requests, 4 November (main, deployed to the local M3 runtime the same afternoon).** The first tester to come in through the assistant (Hoang, 4 Nov) submitted two trial-credit requests in the chat and then could not find them: the Owner's Requests page listed only the form requests (`requests` table) while the assistant's decision cases (`decision_cases`) lived on Review and Home alone, and the Review lede sent people to Requests for "the full record". Decided: (1) `GET /api/decision-cases` lists every live decision case for both roles, newest first: the Owner gets the Review rows, Staff a row without the Owner's private signals (no feedback, prepared decline, override, observed outcome, comparables or reliability; the decision reduced to outcome, who and when), as the timeline already shows them neither. (2) The Requests page (`#/cases`) lists both kinds in the same groups (For you, In progress, Done) with the same chips; an assistant request carries a "Via the assistant" mark and opens its timeline (`#/decision-cases/<id>`); a form request that the agent prepared has a decision case too (`requestId`) and is listed once, as the form row, whose page carries the next action. (3) The navigation count on Requests counts both. (4) The form is demoted: Staff land on a start panel whose primary link is the assistant (when `assistantUrl` is configured) and the form is "Send a request without the assistant"; the composer renders only at `#/cases/new`. The Owner's start panel says how many came through the assistant and points to Review, where the decision is still made. Checks: records 1110 (3.12), Review 84/84, action 42/42, control panel 67/67, dashboard 34/34; home 58/61 with the same three navigation-order failures as before this change (stale since the Model page).
- **A refusal is not a state: the Staff agent asks the backend again, 4 November (main; live agent updated the same afternoon).** In one chat the tester asked for a second trial credit for a customer while the first was with the Owner (409 CASE_OPEN, correctly), then asked again after the Owner had decided; the model repeated the refusal word for word from the earlier turn without a tool call (two replies, no tool content at all), so Staff were told to wait for a review that had already happened. Decided: (1) the CASE_OPEN message says it is the state at the time of the call and that the Owner decides outside the chat, so a later request is to be resolved again, not answered from this message; the text sits in the conversation and is what the model reads next time. (2) The Staff instructions gain one line: run the steps for every request, including one refused or answered earlier; an earlier tool result is history; do not check with decisionStatus first; call resolveDecision and let the backend refuse again if a case is still open. The first wording ("call resolveDecision again") made the model check decisionStatus, report the Owner's decline and never submit the new request; the second wording submitted it. Reproduced on the live agent in one chat each time (request A opens a case, request B is refused, the Owner decides A by API, request B again): before the change the refusal was repeated with no tool call; after it, one resolveDecision and a new case. One sample each, same model (35B at 32k), not benched; add "ask again after the Owner decided" to the bench's ambiguity set before relying on it further. Seen on the way: one empty final reply after a successful resolveDecision (the card still showed), the known early stop.
- **A repeated message is answered by the backend, not by the model's memory, 4 November (main; live the same afternoon).** The instruction line above was not enough: the tester's chat held the same question four times with two copied refusals in between, and with the new rule in the system prompt the model again answered the repeat with no tool call ("the user is asking the same question again; I should repeat the same explanation"). Replayed on the live agent (the same refused message three times, the Owner decides by API, the message once more): no tool call, with the rule in place. Decided: (1) the title proxy in front of LM Studio (`bin/title-proxy`, every chat completion passes through it) appends a short Nucleon note to the last user message when its text equals an earlier user message of the same chat, whitespace and case aside: the message is new, something may have changed outside the chat, do not answer from earlier turns, call resolveDecision again or answer a question from a fresh tool call. A note beside the message is read where the model's attention is; the same words at the top of the system prompt were not. The proxy's `--selftest` pins the rewrite (string and multimodal content, a tool turn is left alone, a different wording is left alone, titles still pre-filled). (2) A decided case's `nextStep` (both the agent's and the Owner's decisions) ends with "A further request is a new resolveDecision call", so a status lookup of a decided case points the model at the right tool. (3) The Staff instruction line stays, worded for a repeated message and against looking it up with decisionStatus. Replayed again after (1)–(3): the fourth identical message called findCustomers and resolveDecision and opened the new case (one sample, 35B at 32k). The Staff agent's and the Owner's earlier replies are untouched; nothing else in LibreChat changed. Left for the bench: a "repeat after the Owner decided" prompt pair in the ambiguity set.
- **A stalled evidence case gives way, 4 November (main; deployed to the local M3 runtime).** The tester asked for a trial credit for Lakeside Kiosk; the customer had a case gathering evidence since 1 Nov whose information request had expired after 24 hours, so every other request for that customer was refused CASE_OPEN, and the assistant pointed Staff at the expired page, which said "Expired. Ask the assistant to resolve the request again" without saying that only the same request would do (any other was refused). Decided: (1) a case still gathering evidence whose information request has expired is stalled, and the backend says so: `evidenceExpired` on the case view and the list rows, no `evidenceLink`, a statusText that names the expiry, and a `nextStep` that says the same request gets a fresh page and a different one replaces the case. (2) `resolveDecision` with a different request for that customer closes the stalled case (status `closed`, a history note and a `closed` event "Superseded: the information request expired unanswered and Staff asked for a different request for this customer", an Owner notice) and resolves the new request in its place: nothing was decided or executed on the stalled case, so nothing is undone. The same request still replays and gets a fresh page (as before). (3) The expired-action page and the Requests page chips word the two ways out. Checked: records 1111 (3.12), Review 84/84, action 42/42; on the live agent the tester's message opened a new Lakeside case and closed the stalled one. Product note for the Owner's review: a case the Owner has in hand (awaiting_owner, on_hold) is NOT superseded; only one waiting on Staff who did not answer.
- **Week 8 seminar follow-ups, 4 November evening (main; deployed to the local M3 runtime).** From the seminar's testing session and the team's discussion (transcript of 4 Nov). Decided and built: (1) **Staff practice.** One switch for the workspace (`POST /api/staff/practice {on}`, Staff person; shown on the Staff Home page): with it on, `resolveDecision` from a Staff session is the preview (`delegation_assess`), marked `practice: true`, its statusText prefixed "Practice mode (nothing stored, nothing sent to the Owner)" and its nextStep saying so, so the assistant repeats it; nothing is stored, no case reaches the Owner. The team's wording was "turn the escalation to the Owner off while trying things"; the switch is that, with the consequence that a within-policy request is not approved either, since practising must not change the ledger. (2) **The Owner's what-ifs** (`GET /api/delegation/preferences/next`, `POST .../answer`, the "Teach it your limits" section of the Model page). Real cases are rare, so the Owner is asked about real customers with numbers the records do not hold: first far outside (ten times the usual invoice), then narrowed between the highest approved and the lowest declined, one dimension at a time (amount at the business's usual terms, then terms at the highest approved amount; for extensions, days after the due date of the largest open invoice), customers with a history first, the fewest answers first. Each answer is stored as a `decision_cases` row in the new `owner_preference` dataset with the features the real ledger gives the what-if that day and the research feature row, so the comparables (labelled "the Owner's own answer to a what-if … not a real case") and the training table (dataset column) see it; the track-record gate never counts it. The params are rebuilt server-side from the customer, the invoice and the numbers. (3) **Deposit.** The strict default of the policy stays (a missing key never widens), but the control panel sets the deposit to 0 when the Owner turns trial credit on from the defaults, and the field says "0 = none asked"; the team's position is that a deposit is not asked when buying on credit, and becomes a condition only when the Owner offers it (a counter-offer with a deposit is not built: see open items). (4) **"First credit"** check relabelled "Earlier dealings" with a sentence that says why a customer with invoices is not a first-credit case. (5) **Control panel:** the form warns before leaving the page or closing the tab with unsaved changes (the Owner lost a change this way in the session). (6) **Business identity:** the field says ABN or ACN and why it is asked. Not built, for the Owner's call: a rule-book bypass switch (practice and the deposit change remove the reason the team wanted it); the deposit as an Owner counter-offer condition; an Owner notification channel beyond the Home page and the webhook (a Rocket.Chat incoming webhook would do it with no code); a dashboard line against the phone-call baseline. Checks: records 1113 (3.12); the five page checks as before (home keeps its three stale navigation failures).
- **One page per request, presets instead of a bypass, 5 November (main; local runtime).** After the seminar the Owner found the pages hard to navigate: a request opened from the Requests list was a read-only timeline, the same request opened from the Decide list could be decided inline, a form request had a third page, and Staff reached the information form only from the chat card. Decided: (1) the timeline page (`#/decision-cases/<id>`) is the request's page: it carries the one action that is the reader's, the Owner's Decide row (the same row and code as the Decide list, review.js; a decision there refreshes the page) or, for Staff, the "Provide the information" button while Nucleon waits for them (the expiry words when it lapsed). (2) The Review page is "Decide" in the navigation and its title: a work list, not a reading page; its row link reads "Request page". (3) Requests rows go to the next step: a prepared form request opens the request page of its decision case (the old case page stays for a request still being prepared or asking Staff a question); a Staff row waiting for information opens the information form. (4) The rule-book bypass the team asked for is two presets on the control panel, each saved as a new policy version with its name in the note: "Fits the fictional records" (the demo bounds, no deposit) and "Wide open for trying things" (every bound at its maximum, nothing held, no deposit, no business identity asked). (5) The business identity of a new customer is a policy switch (`newCustomers.requireIdentity`, default on, strict), off in the wide-open preset; the evidence item reads "not required" then. Checks: records 1114 (3.12); Decide/request page 84/84, control panel 67/67, home 58/61 (the same three stale navigation failures).
- **The card's dates back on the timeline, and the Requests pane header, 5 November evening (main; local runtime).** Two findings from the user's walk through the demo runbook. (1) The decision card's key-facts bar held unlabelled markers only (a 4a33b74 choice, so no text could overlap), and read as a slider: the dates were in the rows above, the bar said nothing on its own. Now `lab/card.py` `date_bar` draws an axis with a pin per date, the short date and its role written at each pin (odd pins below the axis, the first and last anchored to the edges, so neighbours never collide), the extension span (due date to requested due date) filled green and the overdue stretch (due date to the as-of date) red beneath, as the earlier Nucleon timeline had them. Test rewritten for the new markup. (2) On the Requests page the queue header put the lede and the "Send one without the assistant" button side by side, so at the desk's rail width the lede became a one-word column and the button overflowed the pane; the header is now a column (lede full width, button under it), and the start panel's hint sits on its own line under its button. 1114 prototype and 131 Lab tests pass on 3.12. The Python 3.9 run in `bin/check` was found spinning at 200% CPU for 83 minutes on 5 Nov and was stopped; not investigated.
- **A small amount over a money limit, 5 November night (main; local runtime).** A tester had seen a tiny request escalate and the user asked for a switch: when the only thing wrong is a money limit exceeded by a little, the agent approves anyway. Decided: a new policy section `smallOverage` {enabled, maxShare, maxAmount, rule 'either' | 'both'}, validated like the others (a share 0–1, money in the workspace currency, both nullable; with the switch on at least one must be set, both when both must hold), off by default, and in the digest only when on, so every earlier version keeps its fingerprint. `delegation.small_overage` runs before the exception band and needs no model score and no comparables: it applies only when every failing check is one of the four money limits (decision, customer total, trial exposure) and each is over by at most the share of its limit and/or the amount; days, identity, overdue invoices, earlier dealings, a held customer and incomplete records are never covered, and in advisory or paused mode it never applies. Covered checks read 'exception' with the margin said on them; the card's reasons and warnings say whether it applied and, if not, why. The control panel got the fieldset "A little over a money limit" and a summary row; the preset "Fits the fictional records" now turns it on at 10% or AUD 50 (the 'Wide open' preset has no limits to exceed). On the card, the extension span is now filled by state: orange while nothing is decided, green once approved, hollow once declined or overridden (it was green throughout, which read as approved before anything was). Checked on a fresh seed under the preset: Northside at AUD 850 (exposure 650, 8% over 600) is approved by the agent, AUD 900 (17% over) goes to the Owner. 1119 prototype and 131 Lab tests pass; the delegation page check passes 67/67.
- **Tester feedback round, 6 November afternoon (main; local runtime).** Tony tested the runbook; two steps "failed" because he had hand-filled the policy with "Records must be confirmed complete above" AUD 3.00, which nothing on the card or the panel explained. A request that fails only "Records must be confirmed complete above this exposure" now says the level is the Owner's own setting and that Staff cannot supply it, the control panel explains that field and the two money limits, and the summary shows the coverage level; the Model page no longer redraws over a what-if reason being typed; the Requests list says who decided ("Approved by you / the owner / the assistant"); the Owner can withdraw their own approval on Review (same path as an agent override, not counted as one); the customer search tells the agent what to say about a customer the records do not hold; Home opens with three "Where to start" steps per role.
- **Tester feedback round, 6 November evening (main; local runtime).** Hoang tested the extension flow end to end (it worked) and found eight things. The assistant, told to handle one of two requests, sent both: the Staff instructions now say to handle only the request Staff named, and the records refuse a service session's second new case for another customer within 20 seconds (ONE_AT_A_TIME, nothing opened, the model told what to say); a hard guarantee is impossible without the conversation, and every Staff chat shares one service session, so the window is short. The Owner's pages opened the Staff assistant: config `ownerAssistantUrl` gives the Owner their own link. The Owner's assistant reported one of two waiting cases: workQueue's code-written sentence now names every decision case, and the Owner agent is told to repeat it. The evidence item 'Records complete' (readable records) contradicted the warning that the records are not confirmed complete (the Owner's coverage): it is 'Records readable' now. The navigation count stayed stale after a decision on Review or a case page: both refresh it. The sign-in page no longer claims codes change at restart (this instance has fixed ones; the probe before sign-in still reveals nothing). Staff Home listed 26 notices about cases of earlier testers that the reset had removed: notices and case events are data tables now, cleared by the console reset and the demo reseed. Switching to Staff on an Owner-only page left 'Page not found': it goes Home. Tony's training-table download as the Owner failed because a plain link sends no role header and his browser held both roles (400 ROLE_REQUIRED): the two download links name the role in the address. Both LibreChat agents were updated (agents backup in the runtime's backup folder) and told not to restate the card. 1123 prototype and 131 Lab tests pass; the delegation page check 67/67; home page check 58/61 (the 3 stale expectations).
- **Staff add information unasked (6 November, main; local runtime).** A trial-credit case the Owner has (awaiting or on hold) now takes information Nucleon did not ask for: the case page offers Staff "Add information" when the frozen evaluation left a deposit, a business identity or a trade reference unverified, POST api/decision-cases/<id>/evidence-request opens an evidence action for exactly those (the evaluation's own needs, else generic ones), and the usual form and path follow: the facts are kept with the case and it is evaluated again on the current policy, so the Owner's row says it changed. One open action per case; nothing for an extension (a payment goes into Records), nothing once decided or while a request is already open. Requested by Tony (a deposit received after the request) and deferred on 6 Nov; done the same evening. 1125 prototype and 131 Lab tests pass; delegation page check 67/67.
- **Hoang's second round, 6 November night: the form reads written dates, and Review lists form requests.** Two findings from the retest. (1) The form path ("Send one without the assistant") runs the mock adapter on this instance, whose disclosed parser read only ISO dates, so "to 14 November 2026 because of a temporary cash-flow delay" asked Staff for the date again and dropped the reason. `deterministic_extract` is now v0.3: ISO, "14 November 2026", "Friday 30 October" (weekday checked), "Nov 14"; a date after "from", "instead of" or "due" is the current due date, not the requested one; a date with no year takes the as-of year or the next; relative wording ("next Friday") is still never read; the clause after "because" / "due to" is quoted as the reason statement. The mock adapter passes the as-of date from the extraction prompt and quotes the reason in the brief; the fallback passes the evidence's as-of date. (2) The Review page listed decision cases only, so a form request waiting for the Owner (no decision case of its own) was absent while Requests showed it. `reviewLoad` now also reads `/api/requests`; a request in `awaiting_owner` with no case is a row under Waiting for you ("Sent through the form", counted) with one button to its own page, where it is decided. Checks: test_agent parser cases, test_workflow from/to case, review_page_check B3 (form row, count, withdraw).
- **Quick setup beside the Control panel, and extension days counted three ways, 11 November (branch `feat/quick-setup`; not deployed).** After the NTK owner session of 10 Nov (about an hour to set the Control panel up with Hoang explaining; the saved policy let the agent approve none of the 20 open invoices, mostly because days counted from long-past due dates and "nothing else overdue" was on by default), the user chose a helper beside the Control panel, not a replacement. Decided and built: (1) `#/quick-setup`, Owner only: three assurances, how to start (decide from today, after reviews, or only recommend), eight plain questions, a live preview of what the answers would do with each open invoice, a plain summary, and Save as an ordinary policy version. Answers map to settings by fixed code (`delegation.quick_setup_policy`); no model guesses the Owner's preferences. The preview runs `delegation.evaluate` with the unsaved policy and writes nothing. (2) Two optional extension limits beside the days after the current due date: days after the day the request was received (a case records `receivedDate`, so a re-check counts the same) and days after the original due date (which stops a chain of extensions that each stay inside the per-extension limit: four 20-day extensions under a 30-day limit were approved in a row before). A policy without them keeps its digest. Spec and plan: `docs/superpowers/specs/2026-11-11-quick-setup-design.md`, `docs/superpowers/plans/2026-11-11-quick-setup.md`.
- **The Doctor: the Owner's questions answered by code, and one tool for the Owner's assistant, 11 November (branch `feat/doctor`; not deployed).** The user asked for a way to answer "why do I still get so many requests, which setting is unreasonable?" and "why do I keep correcting the agent?". A trial the same day gave the local model (Qwen3.5-35B-A3B) a facts sheet written by code and 24 questions: it kept to the sheet's numbers, said when something was not worked out and refused to change settings, but 5 of 24 answers went wrong (1 empty, 2 compared against the wrong starting number, 1 left out a change's cost, 1 guessed an uncomputed figure) and each took one to three minutes. Decided and built: (1) `doctor.py`, six preset questions answered by code from the live cases (why requests come to the Owner, with what-ifs on those same cases including combinations of changes; why the Owner corrects the agent, with the tighter limit that catches most corrections and what it would also catch; how much the agent helps; whether approved extensions were paid; which customers come most; which rules never matter or block everything). Every suggestion states its starting number, its gain and its cost; with fewer than five cases it says there are too few. (2) `#/doctor`, Owner only; a suggestion opens Quick setup filled in, nothing saved. (3) The Owner tool `doctor` returns the same code-written lines to the Owner's chat assistant, as an experiment for questions nobody predicted; no model is called by Nucleon. Spec and plan: `docs/superpowers/specs/2026-11-11-doctor-design.md`, `docs/superpowers/plans/2026-11-11-doctor.md`.
