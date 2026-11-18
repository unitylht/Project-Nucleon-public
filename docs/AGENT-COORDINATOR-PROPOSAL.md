# P003 — Nucleon as a coordinating agent: direction and first slice

Date: 19 October 2026, Australia/Sydney. Revision 2, after the team's decisions of 19 October on revision 1.
Status: **proposal**, written by Hanting's development session. Not owner authority, not implemented. Where the team decided something on 19 October it is marked **[team, 19 Oct]**; where this document takes a position it is marked **[my call]**. The shared practice site is unchanged (`f95f50f`, E016; baseline tag `baseline-records-ui-20261019`). Exploration happens on branch `explore/agent-coordinator-20261019`.

Implementation (added 20 October): a first slice is built on that branch, not deployed. See "Implementation notes (first slice)" at the end and DECISIONS E018.

Revision 3 (20 October): the conversational desk, a second slice on the team's direction of 20 October, revises §6 and §10 for that slice and runs on the preview only. See "Revision 3" at the end and DECISIONS E020.

Revision 4 (21 October): situation, capabilities and prepared actions, a third slice on the team's direction of 21 October, for the preview only. See "Revision 4" at the end and DECISIONS E021.

Revision 5 (21 October): the business tool layer as the reusable asset, and the Nucleon Lab at `/lab/` (DECISIONS E022). Revision 6 (21 October, afternoon): the Lab's second iteration, with revisions, prose first and understandable state (DECISIONS E023). See both at the end.

Related: [MINIMUM-FLOW.md](MINIMUM-FLOW.md) (P001), [SETUP-AND-RECORDS-PROPOSAL.md](SETUP-AND-RECORDS-PROPOSAL.md) (P002 §6.2, §6.4, §9), [PROMPTS.md](../PROMPTS.md), [DECISIONS.md](DECISIONS.md) E003 and E017, [FACTS-AND-OPEN-QUESTIONS.md](FACTS-AND-OPEN-QUESTIONS.md), [COURSE-REQUIREMENTS.md](COURSE-REQUIREMENTS.md).

## 1. The direction, in one paragraph

Nucleon becomes an agent that coordinates the work: it reads a request, gathers what the records and earlier conversations hold, works out what is missing and why it matters, asks the right person only for that, and moves the case on. People say what they want in their own words; the system answers with conversation and with things to act on. The owner's knowledge is acquired progressively through work, kept as said with its source, time and uncertainty, and reused with appropriate scope. Structured records stay underneath for arithmetic, state and execution. The current application is kept and recoverable; it may become the records and administration entry point behind NucleonAI. Advice and authorised action stay distinct.

## 2. Evidence: what is inspected and what is reported

**Inspected by me** (the repository, 19 October):
- Money, state, versions and authority are in code; the model sees minimised summaries and can only read through six tools and hand a case to a person. Every fact shown to the owner is code-rendered with its source (E003, brief-v2). Nothing in the direction requires changing this.
- The agent is a pipeline: one extraction, one tool loop, stop at the first hand-off. It can ask staff for two fields and the owner for nothing. It has no notion of "this would help but is not required".
- Owner knowledge is a flat note (`kind`, `scope`, `text`, `status`); the model receives only the text. Confirmed notes are visible to staff. P002's decision-time capture and conversation-to-summary are designed, not built.
- The model adapter speaks OpenAI-compatible chat completions with native tools and strict JSON schema, and takes a bearer key from an environment variable. It has only ever been run against LM Studio through the home gateway.
- The current POC configuration takes 7–13 s per case on the home server. That is a measurement of one configuration, not a product constraint **[team, 19 Oct]**.

**Reported by the team**, not inspected by me: the first-time-user interview (motivation to reduce navigation and data entry), the earlier team discussions (the owner's knowledge is largely in their head: relationships, promises, intuition, expectations about market conditions; some managers could decide but hesitate over authority), and the owner interview S2 (I have read only the summary in PROJECT-STATE, not the transcript). Nutek's terms are second-hand and conflicting (P002 §1.2) and are not entered anywhere. NTK and Art of Gelato stay separate. The team will supply the source interviews or written summaries; this document will be updated against them.

## 3. Retain, change, separate

**Retain** `records.py`, `importer.py`, the records part of `server.py`, the evidence keys and flags, revert and provenance, the tests and release checks; the guard pattern in `agent.py`; the Customers, Imports, Knowledge and Setup areas; the stack and the deployment. Additive, not a rewrite **[team, 19 Oct; my recommendation]**.

**Change**
1. Requests becomes a **desk** where conversation is a primary way to work (§6).
2. Owner knowledge is **structured internally and confirmed as one interpretation** (§4).
3. The runner becomes a **coordinator** that distinguishes what it needs to calculate, to recommend, and to act, explains why, and continues with a partial result when it can (§5).
4. An **advisory suggestion**, clearly labelled, off by default, owner-only (§7) **[team, 19 Oct]**.
5. A **small read-only conversational capability for staff** (§6) **[team, 19 Oct]**.
6. Model access is **deployment-neutral**: local or hosted through the same adapter interface (§8).

**Separate**: the coordinator is its own module with its own prompt version (`coordinator-v0.1`), recorded in PROMPTS.md; the model adapter interface is unchanged.

**Changes to existing restrictions, named explicitly** (point 6 of the team's decisions):

| Today | Proposed | Why |
| --- | --- | --- |
| No recommendation of any kind (E003) | An advisory suggestion, labelled, off by default, owner opt-in, stored apart from the decision (E017) | Team decision of 19 Oct; the conditions E003 set for real use are **not** met (§7) |
| The agent can ask only staff, only for two fields | It can ask the owner, and explain why a question matters | The judgement questions are the owner's |
| The model receives note text only | It receives kind, scope, date and certainty of items | It cannot weigh "said in March, 'should recover'" without them |
| Confirmed notes are visible to staff | Owner context is owner-only unless the owner marks it for staff (§4) | Question 1 below; internal context must not leak into staff instructions or replies by default |
| Brief format `brief-v2` | `brief-v3`: adds `context`, `questions`, `suggestion`; old briefs read as before | Additive |

## 4. Owner knowledge: structured inside, one confirmation outside

**The owner says** (the brief's example): "This customer has struggled recently, but I have known them for years. They have an event next month and should recover. I would consider a small extension, but I don't want their debt to increase for now."

**What is stored.** One **statement**: the verbatim text, who said it, when (business date), in which thread, about which customer. Attached to it, an **interpretation** the agent proposes: a short list of what it understood, each line labelled internally (`observation`, `relationship`, `expectation` with a proposed end, `guidance`, `constraint`), each linked to the words it came from. The labels and links are internal structure; the owner sees the statement and a short reading of it.

**What the owner does.** One card: "Here is what I understood", the interpretation as four or five lines, **Confirm** or **Correct**. Correcting edits a line or removes it; nothing else is asked. Only when a distinction materially affects a decision or authority is a separate question asked, and then at the moment it matters, not at capture **[team, 19 Oct]**. The agent proposes the customer when the text names one; the card asks for it only when it cannot tell.

**Scope, time and uncertainty.** Each line carries: scope (this customer, or the business, chosen by a person; the model never widens scope on its own), the business date it was said, an end where the words give one ("next month" proposes a date; the owner can change it; expired lines are shown as expired, not dropped), and the speaker's own hedge kept as words ("should"). A later statement that contradicts an earlier line supersedes it, and the earlier one stays in history.

**Guidance is not permission.** "I would consider a small extension" is guidance. When a 21-day request arrives, the agent may ask "You said you'd consider a small extension; is 21 days acceptable here?" and explain that the answer is needed to suggest, not to decide. The answer is stored **for this case**. The card offers "also keep this for Bayside" as an opt-in; nothing becomes a definition of "small" for all customers, ever **[team, 19 Oct]**.

**Reuse and asking again.** Lines are reused by customer, business scope, kind, end date and recency. The agent asks again when a line has expired, when a staff-reported fact conflicts with an owner line (the conflict is shown and the owner asked which stands), when the customer's records changed materially since the line was said (a new unpaid invoice, a broken completeness statement), or when a request turns on something the owner left open.

**Who sees what.** A statement and its lines are visible to the owner. The owner may mark a line "staff should know"; staff then see it as an owner instruction with the words "not enforced by the system". Nothing from a statement enters a customer-facing draft: the reply draft stays a template built from the committed decision, as today **[team, 19 Oct]**. See question 1.

**Constraints that touch unresolved policy.** "I don't want their debt to increase for now" is kept as an owner constraint with scope "Bayside" and end "for now" (no date). The case shows it to the owner with the words "No operational restriction has been applied"; its scope (orders? further extensions?) is asked only if an action would depend on it, and in the first slice no action does **[team, 19 Oct]**.

**Staff context** follows the same model as drafts ("staff say"), labelled, never as owner knowledge.

**Migration.** Existing notes become statements with one line each; `context` maps to `observation`, `rule` to `guidance`; visibility stays as it is for migrated notes (they were already visible to staff) and the owner can change it.

## 5. The coordinator: three kinds of need, and partial results

Per case, after triage and gathering (tools as today, plus `getContext` returning lines with kind, scope, date, certainty and prior decisions with reasons), the coordinator lists what it needs. **Code classifies every item into one of three kinds** **[team, 19 Oct]**; the model proposes the list and the explanations, code decides the kind:

| Kind | Examples | Effect |
| --- | --- | --- |
| **Needed to calculate** | Which customer; which invoice (unclear identity, a number two customers share); the requested date; a conflict in the records themselves (two positions that contradict) | The case cannot be prepared: one question to staff, as today, with the reason |
| **Needed to recommend** | Undefined guidance ("small"); an expired expectation; a staff-reported fact that conflicts with an owner line; no owner context at all for a customer the owner has said is sensitive | The facts are prepared and the decision card is shown; the **suggestion is withheld** and the card says why; the question is attached to the card with "answer" and "decide without this" |
| **Needed to act** | Any authority beyond the owner's own decision | In the first slice, acting *is* the owner deciding; this kind exists so that tier 2 (§7) has a place, and so that the card can say "the agent may not do this" |

**Explaining why.** Every question states what it is needed for ("to calculate", "to suggest") and what happens without it. **Partial results** are the rule: a case with unresolved recommendation needs still gets facts, context, prior decisions and the decision controls.

**Initiative without authority.** The coordinator may gather, classify, ask, propose an interpretation, propose a suggestion, draft. It may not commit a decision, change a term, send a message, confirm a line, widen a scope, or classify a need as blocking that code does not. Two new write tools, `proposeInterpretation` and `attachQuestions`, create records only a person can confirm or answer. Every other boundary in PROMPTS.md "Human boundaries" stands.

**Other request types.** Triage recognises a message that is not an extension (more credit, a new order on account). The slice records it as a case of type `other`: facts and context gathered, no calculation, no suggestion, the owner decides in words and the decision is stored. No exposure arithmetic is invented (P002 §1.1).

## 6. The desk: conversation as a primary way to work

**Hypothesis, to be measured, not decided** **[team, 19 Oct]**: people express intent, ask, or give context in their own words; the system replies with a mixture of prose and actionable cards; processing is asynchronous where it takes time. Whether cards or conversation carry more of the work is settled by the measure below, not by the current model's speed.

**What people can say in the first slice**
- **Staff:** paste or type a request ("Bayside want INV-1001 on 14 Nov"); answer the agent's questions; ask a small set of **read-only questions** answered from existing evidence under existing permissions **[team, 19 Oct]**: what a customer owes (with the certainty mark and the "why not exact" on expansion), which of a customer's invoices are open or overdue, the status of a request, what the owner has said that staff may see. The model maps the question to one of a few read tools and the customer; code writes the numbers and the marks. Anything else gets "I can look up …; for other things, open the records".
- **Owner:** give context in their own words; answer questions; ask the same read-only questions; decide with the card's controls. Decisions typed in words are a later slice; words do not commit money.

**Cards:** *Facts* (code-rendered, certainty marks), *What you have said* (lines, dated, expired ones marked), *What I need* (questions with their reason and "decide without this"), *Decision* (today's controls, the suggestion when on, "remember for this customer"), *Reply draft* (template), *Here is what I understood* (one confirmation), *Answer* (to a read-only question). Every card expands to its sources and links to the records page behind it.

**The accounting distinctions** stay, placed where they matter: one headline amount per case with its mark; the explanation and the full position on expansion and on the records page.

**Asynchronous because the work is** (the agent runs in the background, several people use one instance, a model may be remote), not because of any particular latency; replies arrive in the thread as they are ready **[my call]**.

**The measure: how much work the user does to reach the goal** **[team, 19 Oct]**. For three fictional scenarios (a complete request; a request needing one owner judgement; a staff question about what a customer owes), count on the current interface and on the desk: user actions (messages typed, taps, fields filled, pages opened), people involved, and elapsed time; record both in the evaluation. The desk must win on actions for the owner, or the hypothesis is wrong.

## 7. Authority: three tiers, and what the advisory suggestion does not establish

| Tier | Agent | Person | Status |
| --- | --- | --- | --- |
| 0 | Prepares facts, context, questions | Owner decides every case | Today |
| 1 | Adds an **advisory suggestion** (outcome, date, the lines and facts it cites, one sentence), labelled "suggestion, not evaluated in real use" | Owner accepts in one tap, changes the date, or declines; the suggestion is stored as a suggestion, never copied into the decision | **First slice [team, 19 Oct]**: off by default, turned on by the owner only, shown to the owner only |
| 2 | Within a confirmed standing instruction whose structured part code can check (customer, maximum days, how often, until when), records the decision and notifies the owner | Owner can reverse within a window | Designed, not built, until Q03 |

**The suggestion is model-written in a separate `suggest` step** after facts and context, with a JSON schema. Code verifies that every cited line and fact was loaded in this run, that the date is valid and later than the current due and as-of dates, and runs the prose guard; day arithmetic is code's. It is withheld when any "needed to recommend" item is open (§5). When an owner answer arrives, only this step re-runs **[my call]**.

**What this does and does not establish** (E003, and the team's instruction of 19 Oct):
- E003 disabled recommendations until there was an owner-confirmed approval policy and an evaluation method that includes refusals. **Neither exists.** Fictional scenarios demonstrate and test the workflow; they do not establish real-world decision quality.
- Therefore the suggestion is advisory, labelled, off by default, and the decision record never contains it. The counters recorded (suggested, accepted, changed, declined, withheld, by scenario) are a workflow test, not an accuracy claim.
- **Decision to revisit, flagged:** whether the agent may recommend in *real* use stays open (DECISIONS "Still open"); it needs the owner's policy (Q03) and owner-reviewed cases including refusals (Q05). E017 records the prototype-only change.
- A test scenario in which the context argues against approval guards against E003's observed failure ("approve in every complete case").

## 8. Model access: local or hosted, through one interface

**Implemented today:** an OpenAI-compatible chat-completions adapter with native tools, strict JSON schema, per-task token limits, timeouts and a bearer key from an environment variable; exercised only against LM Studio on the home server.

**Intended deployment options** **[team, 19 Oct]**: a local model for businesses that keep data in their own environment; a hosted model API for others. The first slice keeps the single adapter interface and adds nothing provider-specific; a hosted OpenAI-compatible endpoint is a configuration change. **No hosted integration is claimed working until one is connected and tested**; the status is recorded in PROMPTS.md and DEPLOYMENT.md as "untested" until then. A provider with a different wire format (for example Anthropic's) would need a second adapter behind the same interface; not in the slice.

**Data handling** follows Q08: before any real record is sent to a hosted model, the owner's confirmation of data handling is needed; fictional data only until then.

**The coordinator's model steps** are triage, interpretation, needs planning, suggestion, and read-only question routing; each is a JSON-schema task that any adapter with structured output can serve. Latency is measured and reported per step, per deployment; the POC tolerates some.

**Demonstration preparation** **[team, 19 Oct]**: preloading records, precomputing stable summaries and warming the model are acceptable. The demo script states what is prepared (the fictional workspace, the owner's earlier statements, a warm model) and what runs live (the new request, the interpretation of new owner text, the questions, the suggestion, the decision). New input and changed evidence must change the result: the acceptance scenarios include a changed record between preparation and decision.

## 9. Assumptions and calls

Team decisions of 19 October are above. My calls, open to challenge:

1. **Asynchronous threads** (§6), independent of latency.
2. **Extensions remain the only computed workflow**; other requests are triaged and recorded (P002 §1.1).
3. **One model, one adapter in the slice**; the current local model stays unless the team supplies a hosted endpoint to test (question 3).
4. **Threads are their own records** (a `conversations` store: the general thread and one per case). Typing into a case thread does not bump the request version; confirming an interpretation re-runs nothing; an owner answer re-runs only the suggestion step. Lines are not part of a pending case's evidence version; the decision records the line ids and versions it was shown with.
5. **Additive**: `/api/requests` and brief-v2 reading stay; brief-v3 adds fields; existing tests keep passing; the QA pack gets a revision 4 for the Requests area.
6. **Dates on statements use the workspace's business date**; the real clock is the audit timestamp. The demo console gains "advance the business date" for practice workspaces.
7. **Verbatim statements, minimal structure**, confirmed in one interaction (§4).
8. **Read-only staff questions are a fixed small set** mapped to existing read tools; code writes every number.
9. **Channel**: the prototype inbox; real channels wait on Q08. **Businesses**: all fictional.

## 10. First slice: "the agent knows what you told it, and tells you what it needs"

**Goal:** on fictional data, the agent coordinates one real workflow, uses unstructured owner context, asks only what it needs and says why, gives an advisory suggestion the owner can take or leave, and answers a staff question; the owner and staff do measurably less than on the current interface.

**Scope**
1. Statements and interpretation (§4): store, migration, one-confirmation card, scope/end/supersession, visibility flag, "remember for this customer". Model task `interpret_statement` (schema; every line must quote its words).
2. The desk (§6): threads, one input, the eight card types; the records areas unchanged and linked.
3. Coordinator (§5): triage, `getContext`, needs with the three kinds classified by code, questions with reasons attached to the decision card, partial results, reuse and re-asking rules, `other` cases.
4. Advisory suggestion (§7) with the `suggest` step, guards, owner setting, counters.
5. Read-only questions for staff and owner (§6): four question types.
6. Measurement: per-case counters (questions asked, by kind; owner and staff actions; elapsed per step; lines reused; suggestion outcomes) and the three-scenario effort comparison against the current interface.
7. Conversations store; business-date advance in the console; PROMPTS.md for every new task; DEPLOYMENT.md for the model-access status.
8. Tests for every guard, classification rule, reuse rule, the migration, the withheld-suggestion cases, and the changed-evidence case.

**Out of the slice:** tier 2, additional-credit arithmetic, external channels, a second adapter, a general assistant, decisions typed in words, changes to the records areas.

**Demo (under four minutes; prepared parts named):**
*Prepared:* the fictional workspace with records, a warm model, and the owner's earlier statement about Bayside confirmed last week. *Live:* everything below.
1. Staff paste "Bayside here, could we pay INV-1001 on 14 November?" (21 days).
2. The thread shows facts (exact amount, marks), what the owner said (dated), prior decisions, and one question to the owner with its reason: "You said you'd consider a small extension; is 21 days acceptable here? Needed to suggest; you can decide without it." The suggestion is withheld, and the card says so.
3. The owner answers "up to 14 days this time" on the card. The suggestion step runs: "Suggest 14 Nov", citing the relationship line, the expectation, the answer and the constraint, labelled advisory.
4. The owner approves 14 Nov with one tap; the reply draft appears, not sent; the constraint is shown to the owner with "no operational restriction applied".
5. Staff ask "what does Bayside owe now?" and get the answer card with the exact amount and its date.
6. The owner types a new sentence about another customer; one "Here is what I understood" card; one Confirm.

**Acceptance scenarios (fictional, each a test):** complete request with context, no question; undefined guidance, one owner question, suggestion withheld then given; expired expectation shown expired and re-asked; staff fact conflicting with an owner line, one conflict question; context arguing against approval, suggestion "decline" or withheld, never "approve"; owner declines against a suggestion, both stored apart; a record changed after preparation, the case re-prepared and the suggestion withdrawn; AI unavailable, the existing fallback with lines shown and no suggestion; staff ask about a customer they may see and one they may not; effort comparison recorded for the three scenarios.

## 11. Open business questions, kept visible

Unchanged and still owned by teammates (FACTS-AND-OPEN-QUESTIONS Q01–Q08; P002 §13.2 B1–B11; meeting actions A01–A13):

| Needed for | Question | Until then |
| --- | --- | --- |
| Recommendations in real use | Q03 (authority) and Q05 (owner-reviewed cases including refusals) | Advisory only, labelled, fictional evaluation |
| Tier 2 | Q03 with scope and examples | Designed only |
| Real terms | B3, Q04 | None recorded; unknown due dates stay unknown |
| Ordering after an extension | the unresolved meeting question | Constraint kept, scope asked before any action, nothing enforced |
| Hosted model with real data | Q08 | Fictional data only |
| Pilot business | Q01 | Fictional |

None blocks the slice.

## 12. Questions for the team

Only where the answer changes the design, and mostly about authority:

1. **Staff visibility of owner context.** Proposed: owner-only by default; the owner marks a line "staff should know"; migrated notes keep their current visibility. This changes today's behaviour (confirmed notes are visible to staff). Agree, or keep everything visible to staff as now?
2. **"Remember for this customer" at the decision moment.** Proposed: the owner's answer to a case question is case-scoped unless the owner ticks "also keep this for [customer]"; business-wide scope is never offered on the card, only in the Knowledge area. Agree?
3. **A hosted model to test against.** If the team can supply an OpenAI-compatible endpoint and key (held in an environment variable on the home server, never in the repository), the slice can report the hosted path as tested on fictional data; otherwise it is documented as untested. Will one be available before Week 7?

## 12a. Decisions after revision 2 (team, 19 October)

Recorded in the implementation plan, §0 ([superpowers/plans/2026-10-19-agent-coordinator-slice-1.md](superpowers/plans/2026-10-19-agent-coordinator-slice-1.md)): owner context owner-only by default with visibility per statement; case-scoped answers and "remember" with the outcome kept apart from reusable guidance; no hosted endpoint, hosted compatibility untested; staff questions as a capability scope with natural phrasing and follow-ups; "needed to act" empty; evaluation covers owner effort, work shifted to staff, correctness and understanding. The slice proceeds on the exploration branch.

## 13. Left to the builder

Prompt wording and schemas; card layout within UX-REDESIGN.md's system; the end-date inference for words like "next month" (always confirmable); the four read-only question types' exact phrasing; the format of the effort comparison and the counters report.

## Implementation notes (first slice, 19–20 October 2026)

- **Source:** recorded by the development session from the task reports and the build ledger of the slice (`.superpowers/sdd/2026-10-19-agent-coordinator-slice-1/`, kept on the development machine and not in Git), and checked against the code.
- **Where:** branch `explore/agent-coordinator-20261019`. **Not deployed and not merged**; the shared practice site still runs `f95f50f`.
- **Commits, by task:**
  - plan: `27df9cb`;
  - stores: `191038b`, `fca3a84`;
  - `coordinator.py`: `da104f2`, `b9e8f2e`, `9be0102`;
  - desk API: `367b0c8`, `c617519`;
  - needs: `0429653`;
  - suggestion: `1935dab`, `eff8060`;
  - questions: `d27f3e9`;
  - desk interface: `77f9e47`;
  - checks and the effort comparison: `ec80ea3`, `23d4604`, `7cd920d`, `2b628ab`, `9e7f52c`;
  - records: `51b48d8`;
  - the final review's fix wave: `1f26b36` (server and coordinator), `dc1768c` (desk and checks), `bba6529` (live check), and its record.
- **Data:** fictional only.
- **The proposal above is unchanged.** Where the build differs from it, this section says so. The exact prompts, schemas, guards and mock rules are in [PROMPTS.md](../PROMPTS.md), "coordinator-v0.1". The decision record is [DECISIONS.md](DECISIONS.md) E018.

### Staff questions (20 October 2026)

The ruling "staff see no case questions" is replaced: staff see and answer the questions addressed to them; owner questions stay owner-only; a staff question that repeats private context is moved to the owner. Staff see a `from: staff` question (`calculate`, asked while code finds a records conflict) as `id, kind, from, question, why, status, answeredBy`, in the current brief and in the briefs kept in the activity, and its `question.*` events, which now carry `from`. They still never see `contextShown`. When the case is stored, `coordinator.staff_safe` moves a staff question to the owner, with a code check, when its question or why repeats 12 or more characters of an owner-only quote the needs step was given. Staff answer on the desk with Answer only. The answer is a proposed statement shared with staff, one case-scoped `observation` line, which the model is not given until the owner confirms it; staff cannot skip, and cannot answer the owner's questions. The mock never asks staff, because the facts it reads do not say that the records conflict, so the browser check does not cover this path; the unit tests do (`test_case_coordinator`). Rules: [PROMPTS.md](../PROMPTS.md), "Staff visibility"; decision: [DECISIONS.md](DECISIONS.md) E018, ruling 20.

### What was built, by section

- **§3 Separate.**
  - `prototype/coordinator.py`, with prompt version `coordinator-v0.1`, has four model tasks: `route_turn`, `interpret_statement`, `plan_needs` and `suggest`. Each is one call with a strict JSON schema, code-side validation, and a deterministic mock.
  - The adapter interface is unchanged. The extraction prompt stays `extension-v0.3`.
- **§4 Owner knowledge.**
  - **Built:**
    - statements, each with its verbatim text, who said it, the business date, its thread, scope, visibility, status, lines (kind, quote, end, hedge word), a version and a history;
    - `interpret_statement`, with every line quoting its words;
    - one "What I understood" card with Confirm, Correct (kind, end date, remove a line, choose the customer, share with staff) and Discard (retire with a reason);
    - scope from an exact customer match or the case thread, and otherwise `unassigned`, which is never retrieved;
    - expired lines kept and marked;
    - owner-only by default, shared per statement;
    - "Keep this for <customer>" on case answers;
    - staff see a shared `guidance` or `constraint` line marked "not enforced by the system", and read a shared statement as its active lines only, without the owner's full text or its history.
  - **Differs:** existing notes were **not migrated** into statements. Confirmed notes are read alongside statements as lines (context → observation, rule → guidance) and stay visible to staff, as §12a decided for existing notes.
  - **Not built:**
    - supersession of an earlier line by a later, contradicting statement (the line fields exist, but nothing sets them).
- **§5 The coordinator.**
  - **Built:**
    - `plan_needs` runs after preparation, and code classifies each need. A need is `calculate`, asked of staff, only while a condition code found remains; in this slice the only one is a records conflict. Anything else is `recommend`, asked of the owner.
    - The questions carry their reason, on the case, with Answer and "Decide without this".
    - Partial results: the case always reaches the owner with its decision controls.
    - Answers are case-scoped unless kept for the customer. Answering or skipping changes no version and re-runs only the suggestion.
    - "Needed to act" is empty, by the team's decision.
  - **Differs:**
    - `getContext`, `proposeInterpretation` and `attachQuestions` are not model tools. Code reads the context (`context_for`) and gives it to the needs and suggest steps, and stores interpretations and questions from the validated JSON.
    - Triage on the desk is `route_turn`. The request form still goes straight to the extension-v0.3 extraction.
  - **Not built:**
    - the `other` request type: Task 8 was cut;
    - code rules for re-asking. Re-asking after an expiry, a staff fact that conflicts with an owner line, or a material change in the records is left to the model's reading of the lines. The prompt names these cases, the mock does not do them, and no named test covers them.
- **§6 The desk.**
  - **Built:**
    - threads: the general thread and one per case, with every case listed, including those entered through the form;
    - one input;
    - the seven card types of §6, plus plain text turns;
    - the old queue and form at `#/cases` and `#/cases/new`;
    - read-only questions for staff and the owner in four categories, phrased naturally, with follow-ups that keep the customer per role, a capability explanation for anything else, and "Which customer do you mean?" when the name is unclear.
  - **How it runs:** a desk turn waits for its model call or calls before the reply appears. Case preparation and suggestion runs happen in the background worker, and the desk polls for them.
  - Layout details are in [UX-REDESIGN.md](UX-REDESIGN.md), "The desk".
- **§7 Authority.** Tier 1 is built:
  - an advisory suggestion, off by default, turned on by the owner only, shown to the owner only, and labelled "Suggestion, not evaluated in real use";
  - withheld while a question is open, and run again after an answer or a skip;
  - a suggestion from before a records change or a business-date move can no longer be accepted (409 `STALE_SUGGESTION`); the case is prepared again with a new one;
  - stored apart from the decision. The suggestion on screen is kept beside the decision as the case's `suggestionSeen` (version, outcome, date, and the relation `accepted`, `changed` or `declined_against`, computed by code), owner-only. It is null when none was shown, and the decision record and its event hold none of it (fix wave);
  - a line kept at a decision (source `decision`) is shown, but never cited: code leaves it out of the citable ids (fix wave);
  - counters at `GET /api/suggestions/counters`;
  - a test in which context argues against approval gives "decline".

  Tier 2 is not built.
- **§8 Model access.** Status as in PROMPTS.md and [DEPLOYMENT.md](DEPLOYMENT.md), "Model access": the one adapter has been tested only against LM Studio through the home gateway, and hosted endpoints are untested. Latency per step is recorded on each case and turn. On the live model, in two runs of `deploy/live_coordinator_check.py`: 1.4–2.0 s for `route_turn` alone, 7.3–8.2 s for owner context (route, then interpret), 5.8–6.5 s for `plan_needs`, and 2.3–2.8 s for `suggest`.
- **§9 Assumptions, as built.**
  - **1.** Preparation and suggestions run asynchronously. A desk turn is answered once its model calls return.
  - **4.** Threads, turns and statements have their own tables. Typing into a thread does not change the request version. Confirming an interpretation re-runs nothing, and does not refresh a suggestion already given. An owner answer re-runs only the suggestion step.
  - **4 (continued).** The decision records its `analysisId`, and that analysis's brief lists the line and decision ids the needs step was given (`contextShown`). Line versions are not recorded.
  - **5.** `/api/requests` and the reading of `brief-v2` stay. `brief-v3` adds `contextShown`, `questions`, `suggestion`, `suggestionStatus` and `withheldBecause`. QA pack revision 4 has not been written.
  - **6.** Statements carry the business date. The console's "advance the business date" exists, and it prepares waiting cases again.
  - 2, 3, 7, 8 and 9 hold as written, except that `other` requests (2) were cut.
- **§10 Scope.**
  - **Item 6:** the measurement covers the suggestion counters, model calls and latency per step on each case, and the effort comparison. A per-case report of questions by kind, actions and lines reused was not built.
  - **The demo:** `desk_check.js` follows the demo's steps in mock mode: the owner's statement, typed and confirmed; the staff request; one question; the suggestion withheld; the answer; the suggestion; approval; the draft with the constraint note; and the staff question. It has not been run with a warm live model. `deploy/live_coordinator_check.py` walks the same steps through the API on the live model, except the decision and the draft.

### Assumptions recorded while building (the ledger's rulings)

- **Stores and reset.**
  - Owner context does not survive a demo reset. Reset and start-empty clear statements, threads, turns and the moved business date: a reset is a clean rehearsal, and the sample's fixed ids would otherwise re-attach stale context.
- **Guards.**
  - The coordinator's validators raise an adapter error on a malformed shape, as `validate_extraction` does. The existing failure paths cover it.
  - A need can be answered only by a line whose source is an answer (`answer_ids`), never by the guidance that raised it.
- **Who may do what on the desk.**
  - Requests stay staff-submitted. An owner's message routed as a request creates nothing and gets an owner-only explanation. The owner has context, answers and decisions, not intake.
  - Every turn the owner types, and the agent's reply to it, is owner-only. This fails closed on private context the router might mislabel.
  - Staff see no case questions and no `contextShown`, because the questions quote the owner's words. One consequence: a staff `calculate` question would be invisible to staff. The records conflict still shows to them as an open item. *Superseded on 20 October: see "Staff questions" below.*
- **Suggestions and remember.**
  - "Remember" stores reusable guidance only, and the decision keeps the outcome. The field is labelled "Guidance to keep for <customer>, not the decision". A later question raised by guidance whose meaning is unclear is intended.
  - `byScenarioLabel` was dropped from the counters, because the prototype has no scenario label. The effort comparison labels its scenarios itself.
  - `suggestionShown` is sent whenever a suggestion is on screen, so a decision made against it is recorded.
  - From the final review: a line whose source is `decision` is never cited. Its words were kept when the owner decided another case, and AGENTS.md says "Do not generalise a one-off decision into a reusable rule". The model loses one hint; the owner still sees the line.
  - From the final review: the suggestion shown is stored beside the decision (`suggestionSeen`), as E017 words it: "stored apart from the decision and never copied into it".
  - From the final review: staff see only the event kinds in an allowlist (`STAFF_EVENTS`), so the `question.*` events stay with the owner. The brief keeps its key-by-key scrub, because an allowlist of brief keys would also have to carry the `brief-v1` keys.
  - From the final review: re-asking after an expiry and staff facts that conflict with owner lines stay unbuilt (see "Not built" under §5). The demo must not claim them.
- **Scope of the slice.**
  - Task 8, the `other` request type, is cut. The demo does not need it, and the existing behaviour stands: an extra ask is quoted as "another request". A message that is not about an extension still opens an extension case or a clarification.
- **The desk interface.**
  - The desk lists every case, including those created through `POST /api/requests` or the old form. A case's thread record is created the first time it is opened.
  - From the Task 9 report: `#/cases/new` is the old form. The list view's header shows staff "New request (form)" beside "New request", which goes to the desk.
- **Process.**
  - No git worktree: the work was done in place on the exploration branch, which the user chose.
  - Commit attribution follows the line the harness gives.

### Effort comparison (copied from [qa/EFFORT-COMPARISON.md](qa/EFFORT-COMPARISON.md))

**Caveats:** fictional data and a mock agent, one run per scenario, on 20 October at `2b628ab`. It is not a measure of real-world value. The method choices are stated in that file:
- on the old list view, staff find the form already open beside the list;
- the S2 context is a confirmed Knowledge note on the old pages and a confirmed statement on the desk;
- elapsed times are tiny because the mock answers within the request.

Its Reading section, the human judgement, is not filled in. A re-run after the fix wave, at `dc1768c`, gave the same counts (17/17 checks). The file keeps the `2b628ab` run.

Actions are messages typed + taps or clicks + fields filled.

| Scenario | Staff, old pages | Staff, desk | Owner, old pages | Owner, desk |
| --- | ---: | ---: | ---: | ---: |
| S1 complete request | 2 | 2 | 4 | 4 |
| S2 one owner judgement, context given | 2 | 2 | 5 | 6 |
| S3 staff ask what a customer owes | 2 | 2 | – | – |

- **The owner's action count did not fall:** S1 4 → 4, S2 5 → 6. §6 set the test: "The desk must win on actions for the owner, or the hypothesis is wrong". On this comparison the desk did not win.
- **Pages opened fell for the staff question:** S3 went from 2 to 0. Staff actions were the same in every scenario. The same number of people were involved: two in S1 and S2, one in S3.
- **Correctness:** all six runs stored or showed the intended result. In S2 both interfaces stored approve to 3 Nov 2026; on the desk the suggestion was accepted.

### What remains open

- **Guide revision 4.** The guide's Requests steps describe the old pages, which on this branch are at `#/cases` and `#/cases/new`. `guide_check.js` opens them directly, so it no longer walks "Requests → New request" as the guide words it.
- **The hosted model is untested.** No endpoint was provided. Q08 applies before any real data.
- **The coordinator on the live model has been checked in two runs of one scenario** by `deploy/live_coordinator_check.py`, through the desk API and not the browser (PROMPTS.md, "Observed behaviour: coordinator-v0.1"). In run 1 the model cited an id without its `line_` prefix, so code withheld the suggestion. In run 2 the guard dropped a question that stated an amount. Both suggestions were decline. This is not an evaluation of quality.
- **`other` requests** (Task 8, cut).
- **Tier 2**, until Q03.
- **Recommendations in real use:** E003's and E017's conditions, Q03 and Q05, are not met.
- **Acceptance scenarios of §10 without a named test** (unbuilt, by the final review's ruling):
  - an expired expectation re-asked;
  - a staff fact conflicting with an owner line.

  The other two now have tests in `test_suggestion.py`: `test_a_complete_request_with_context_asks_nothing_and_suggests` and `test_ai_unavailable_shows_lines_and_no_suggestion`.

  In the prototype staff may see every customer's records, so "a customer they may not see" applies only to owner context, which is tested.
- **Known limits:**
  - The digit guard matches digit runs individually, so a date built from known parts passes, and it does not catch number words.
  - `prose_problems` passes "The extension will be approved." This is pre-existing.
  - Mock routing reads month and weekday names as customer names, and its request rule matches customer codes.
  - The coordinator prompt version behind a case's questions is not stored on the case.
  - A request-status answer lists only cases already prepared.
- **Unverified or cosmetic, from the ledger:**
  - restoring a backup made before the new tables existed;
  - the console's "Fixed at <date>" wording after an advance;
  - "Suggestions are off" showing for a case that cannot have a suggestion. It is fixed for cases prepared without the agent, which now say "No suggestion: the case was prepared without the agent.";
  - earlier analyses in a case's history still listing "no confirmed owner notes" for the owner;
  - the list view's two-button header at phone width, which no person has looked at beyond `layout_check.js`.
- **Next:** a team review on a local preview, then a decision on whether to deploy.

## Revision 3 (20 October): the conversational desk

- **Source:** recorded by the development session from the plan (`docs/superpowers/plans/2026-10-20-conversational-desk.md`), its build ledger and task reports (`.superpowers/sdd/2026-10-20-conversational-desk/`, kept on the development machine and not in Git), and [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md), checked against the code.
- **Where:** branch `explore/agent-coordinator-20261019`, commits `c3af0db` (plan) to `b888db8` and the records after it. **Deployed to the preview only** (`/preview/`, [DEPLOYMENT.md](DEPLOYMENT.md), "Preview instance"). The shared practice site still runs `f95f50f`. Not merged.
- **Status:** an engineering slice on the team's direction of 20 October. Not owner policy, and not a decision to adopt the desk. Decision record: [DECISIONS.md](DECISIONS.md) E020. Prompts, schemas, guards and mock rules: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.3".

### The team's direction (20 October)

As given to the development session:

1. A natural working conversation: people say what they need in their own words, follow up, change customer and give context.
2. The agent combines tools to gather what the answer needs.
3. Permissions and calculations stay in code.
4. Answer first.
5. Simplify.
6. Prepare actions for the person to take.
7. Both hosted and local models.
8. Validate with varied wording.

### What revision 3 changes in this proposal (the plan's §0)

The plan's §0 revises §6 and §10 for this slice:

1. **The agent composes the answer.** The model writes the reply's words; code guards them. Every number and date in them must be in the same run's tool results, or the words are withheld. Cards show only code's figures.
2. **Tools, not intents.** The four read-only question types of §6 (and `route_turn`) are **superseded** by read tools (`findCustomers`, `customerOverview`, `invoices`, `ownerContext`, `cases`), a navigation tool over a fixed map of the application (`whereIs`), action tools (`openRequest` for staff, `interpretStatement` for the owner, `prepareCustomer`), and a terminal `reply`.
3. **A current customer** per thread and role. Pronouns follow it, a new name switches, and an unknown name gets "which customer?".
4. **One answer card:** the words first, then only the blocks asked for, then at most one next step. The supporting links appear once per thread.
5. **The case thread:** decision first for the owner, one status line for staff, nothing repeated.
6. **A shorter alternative:** beyond a day limit the owner stated, the suggestion proposes the latest date within it.
7. **Permissions unchanged.** Staff see no owner-only context or trace of it. The agent creates nothing except staff's request and the owner's proposed statement. The owner decides.
8. **Models:** the same adapter; at most 8 tool calls and 6 model turns per desk turn; a deterministic mock. Hosted endpoints stay configuration, untested.
9. **Validation is conversational:** scenarios with varied wording, follow-ups, switches and multi-part asks, on the mock and on the live model, with a reader's judgement. Counts alone do not pass a scenario.

### What was built

| Task | Commits | What |
| --- | --- | --- |
| 1. The desk loop, reply guard and answer card | `49b7b6a`, `47ccd28` | `desk_run`, `DeskTools`, `guard_reply`, the `answer` card; `route_turn` removed |
| 2. Actions | `c97ce48`, `a1c83d3` | `prepareCustomer` and the draft card (Create opens the existing Add customer dialog); `WHERE_IS` with steps; the shorter alternative; counts keyed by noun |
| 3. Focus and continuity | `2811a28`, `a8941dd` | a current customer per role; follow-ups; "yes, add it"; accent-insensitive names |
| 4. The case thread | `cbd0ad2` | decision first for the owner; one status line for staff; one footer per thread |
| 5. Conversational validation | `5957a4f` | `deploy/conversation_check.js` and 13 scenarios; [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md) |
| Fix wave (Task 4 review, Task 5 live findings) | `832979d`, `a5f7ce0`, `6a59776`, `83a4392`, `d046f32` | no `"current"` after a miss; correct amounts shown; staff's fixed sentence; one clause per part; the customer's words under the request line; `layout_check --seed` guard |
| Fix wave 2 (final review) | `b837dc6`, `e000009`, `05ddb82`, `dab9705` | action and decision claims withheld; amounts carry their mark; counts with words between; check scripts that write run only against a scratch server; a test race |
| 6. Records and preview | `b888db8` and the records | `balanceLine`; "never total amounts"; `coordinator-v0.3`; these records; the preview |

### Where the build differs from §0 and from revision 2

- **Amounts in the reply (§0.1).** The plan said never to write an amount. On the live model that withheld correct answers ("Bayside Café owes AUD 1,200.00…"). Now an amount may appear when it is one the tools returned, with the certainty mark the tool gave it (ruling below). The model's own totals are still withheld. Since Task 6, code also gives it a `balanceLine` to quote.
- **Staff and the owner's context.** A sentence saying the owner gave no context is replaced in code by "The owner has not shared anything about <customer> with staff.". `ownerContext` is called only when the message asks what was said, shared or known.
- **The draft card** is the one control: no navigation block or second link beside Create customer. A name already in the records gets "Open <name>".
- **The case thread (§0.5):** "What the agent needs" opens while a question is open, because the suggestion waits for it. The turns follow the case block. The customer's own words are quoted under the request line. The owner's header shows the chip alone for waiting and completed cases.
- **The footer's "Customer records"** in the general thread follows the latest answer's customer.
- **Supporting changes:** a `note` route (the thread records "Customer <name> added." when the person saves the dialog) and a `focus` route (the chip "About <name> ×" clears it). `WHERE_IS` lives in `coordinator.py`. `agent._norm` folds accents, which also affects `findCustomers` in the case flow. An interpretation's short lead-in ("Between us,") stays with the line it introduces.
- **Check scripts** that write or reset (`conversation_check`, `desk_check`, `ui_check`, `guide_check`, `effort_compare`, `layout_check --seed`, `live_coordinator_check.py`) refuse any server but a scratch one on this machine, and refuse the shared and preview ports and logs.

### Assumptions recorded while building (the ledger's rulings)

1. Task 1 shipped with no current customer; Task 3 filled it in. (Task 3 re-added the continuity assertions Task 1 had deleted, including "staff's last customer is not the owner's follow-up".)
2. Counts the model may state must be explicit fields in the tool results (`openCount`, `overdueCount`, `caseCount`, later `invoiceCount`), and ids and links are left out of the known text. This closes the hole where a hex id's digits matched a figure. Cost if wrong: a correct count phrased from a list's length is withheld until the field exists.
3. After a `findCustomers` that matched nobody in a run, `"current"` is refused and the model must ask which customer. The wrong-customer finding broke trust in continuity. Cost if wrong: an extra "which customer?" when the person did mean the current one.
4. For staff, any sentence about the absence of owner context is replaced by the fixed sentence "The owner has not shared anything about <customer> with staff.", in code, not by the prompt. Cost if wrong: none.
5. An amount may appear in the reply only with the certainty mark the tool returned for it (exact, stated as of …, at most, as recorded), enforced by the guard; otherwise the sentence is withheld, and the card shows the marked figures. Cost if wrong: more withheld sentences on the live model until the prompt teaches the form. (Seen in run 5: 5 withheld totals; after Task 6, run 6: none.)

**Deferred and carried items from the ledger, with their state:**

- Counted nouns keyed to their fields (from Task 1): done in Task 2.
- The loose status-label mask (from Task 1): narrowed in fix wave 2 to multi-word labels only.
- `prepareCustomer`'s name check folding accents and reading the person's recent turns (from Task 2): done in Task 3.
- **Staff completeness steps still say "Confirm completeness"** (from Task 2): the label is "Completeness statements" for staff; the steps were not changed. Open.
- **The Create customer button stays on the card after use** (Task 2 review): a second press opens the dialog, which refuses the duplicate. Open.
- **ø and ł are dropped by the accent fold** (Task 3 review; pre-existing limit). Open.
- Task 4 review items (the owner's chip and headline, a dead class, the request line's current due date, the customer's message): done in the fix wave.
- `layout_check --seed` could write into the shared instance (Task 4 review): guarded in the fix wave, and all writing check scripts in fix wave 2.
- Amounts in the reply without their mark (fix wave): done in fix wave 2.
- **The model totals invoices itself** (fix waves 1 and 2): withheld by the guard; Task 6 added `balanceLine` and the prompt rule. Run 6 showed no total, which is one run on one model.
- **"owes AUD 0.00" for a customer with no invoices** (fix wave 2): Task 6's prompt rule; run 6 said "has no invoices recorded". The model is still sent `recordedNet` AUD 0.00.
- **No browser check for the three-open-blocks rule or the paragraph split** (fix wave). Open.
- **Final review items 7–11, left for later:** (7) the owner's pasted request and staff's context are handled by the prompt only on the live model; (8) answer cards stored before the loop render their old note only; (9) a fault other than a tool error in a desk tool gives a 500; (10) the accent fold can make two names ambiguous; (11) the staff hint's wording list. Open.
- **Counts are matched by noun only** (fix wave 2): a known limit (PROMPTS.md).
- **`browser_check.js` and the `e2e_*_check.py` scripts are not guarded, by design:** they run through the deployed URL after `nucleonctl isolate`. `browser_check.js` still defaults to the production URL, and its live mode resets demo data. Open.
- The intermittent `test_evidence_keys…flagged_at_startup` failure: fixed in `05ddb82` (the test now waits for the startup worker).

### Validation

- **Unit suite:** 372 OK at `b888db8`, and `desk_check.js` 60/60 there. `layout_check.js --seed` 217/217 at fix wave 2, and `ui_check.js` 150/150 at the first fix wave; no page code changed after either.
- **Mock conversations:** `RESULT conversation: 169/169`, 4 live-only assertions skipped.
- **Live model** (local Gemma, temperature 0, 13 scenarios, 50 turns): Task 5 159/161 twice (2 FAIL: the wrong customer after a miss); after the fixes 172/172, 170/170, 172/172 and 167/167; with `coordinator-v0.3`, **170/170, 3 INFO, no reply withheld**, and every one of the 11 "what does X owe" turns showed its sentence.
- **The reader's judgement:** the rubric in [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md) was filled in by a model reader (the agent that wrote the scenarios), from transcripts, not from the page. **The human column is empty.** Scripted wording, one local model, fictional data: not a usability result.
- **Through the public preview URL:** deployed as `65982b8` at 19:46 on 20 October and checked through the public URL with the live model: the three-part ask, the follow-up, the switch, "where do I add a customer", adding Riverside Bakery and the owner's context passed; of two requests beyond the owner's "up to 14 days", the first got a suggestion of the current due date, which code withheld, and the second, after the owner's answer, approve Mon 30 Nov 2026 within the limit. Production still runs `f95f50f` ([DEPLOYMENT.md](DEPLOYMENT.md), "Conversational desk and verification"). The needs step asked the owner a question code could answer ("does this request for 21 days fall outside that limit?"), and the draft card's words described the manual route.

### What remains open

- The deferred items marked "Open" above.
- **The four-category restriction of §6 is superseded** by the tools; its read-only scope (what the records, the context and the cases show this role) stands.
- **Hosted models:** the direction asks for both hosted and local. Only the local model was run; hosted endpoints remain configuration, untested. Q08 applies before any real data.
- **Guide revision 4** (the Requests area and the desk) is pending; revision 3 describes the old pages.
- **The effort comparison** has not been re-run on the conversational desk. The last one (first slice) did not show fewer owner actions.
- The model's quality is not evaluated, and no person has used the desk in this slice.

## Revision 4 (21 October): situation, capabilities and prepared actions

- **Source:** recorded by the development session from the plan (`docs/superpowers/plans/2026-10-21-situation-and-capabilities.md`, §0), its build ledger and task and fix-wave reports (`.superpowers/sdd/2026-10-21-situation-and-capabilities/`, kept on the development machine and not in Git), and [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md), checked against the code.
- **Where:** branch `explore/agent-coordinator-20261019`, commits `e7a45be` (plan) to `50233e5`, with the records in `25e3e59` and after it. **For the preview only** (`/preview/`, [DEPLOYMENT.md](DEPLOYMENT.md), "Preview instance", "Third slice (21 October)"); at the time of writing it is not yet deployed there (it was deployed afterwards as `df10ab6`, E021). The shared practice site still runs `f95f50f`. Not merged.
- **Status:** an engineering slice on the team's direction of 21 October. Not owner policy, and not a decision to adopt the desk. Decision record: [DECISIONS.md](DECISIONS.md) E021. Prompts, tools, guards and mock rules: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.4".

### The team's direction (21 October)

As given to the development session, six decisions:

1. **Nucleon serves people and AI agents.** The agent works from the same role-appropriate context of a case that the person sees, and has a case-details capability to obtain it.
2. **Availability, permission and confirmation are distinct concerns.** In the preview the defaults enable every implemented tool for its roles, and nothing has a silent outbound effect.
3. **Prepared decisions with one confirmation.** Calculable questions are answered from code.
4. **Suggestions the owner asks for** go through the guarded suggestion mechanism.
5. **Workflow actions are derived by code.**
6. **Fix the stale focus, repeated details and failed responses** the review found, and avoid phrase-specific fixes.

### What revision 4 changes in this proposal (the plan's §0)

The plan's §0, on top of revision 3:

1. **One situation, two readers.** Code builds the role-filtered picture the page shows (the case with its day limit and the days asked against it, the customer, the focus and the next steps); the desk page draws its case block from it, and the agent reads a rendering of it at the start of every case-thread turn. `caseDetails` and `customerOverview` return it for any case or customer. Context retrieval passes the case id.
2. **Capabilities are registered, not hard-coded in prompts.** `coordinator.CAPABILITIES` gives each tool its kind, roles, confirmation and default. Availability (offered to the model), permission (executed by the server) and confirmation (a person's button before the effect) are kept apart. The owner overrides them under Setup → "Agent tools". An `external` kind does not exist and cannot be enabled.
3. **Prepared decision.** `prepareDecision` resolves the owner's words ("14 days") to a date from the current due date, checks it as `decide` does, and stores a preparation that one **Confirm decision** commits through `decide`. Ambiguity returns what is missing, and the model asks.
4. **On-demand suggestion.** `requestSuggestion` runs the existing guarded suggestion step now and stores the next version; explaining the stored one needs no tool.
5. **Actions from the workflow.** `actions_for` gives each role's next steps per case and customer, allowed or not and why; the model answers "what next" from them, and never computes days or limits.
6. **Presentation follows the question.** The reply's `detail` (`none`, `summary`, `full`) sets how code shows the blocks; overlapping blocks are merged by code.
7. **Focus follows the subject:** a customer, a draft "(not yet a customer)" or a name "(not found)"; the records link only for a customer.
8. **Recovery.** A withheld reply is asked again once with the exact reason; if it is still withheld, the card says "Here is what the records show about <subject>." with the blocks. The guard is unchanged.
9. **Provenance in words:** every block and the situation carry their source labels, and the model keeps the mark with each figure.
10. **Boundaries unchanged.** Owner-only context never reaches staff; the agent commits nothing without a person's confirmation; decisions stay the owner's; no outbound messages exist.

### What was built

| Task | Commits | What |
| --- | --- | --- |
| 1. The shared situation and case access | `506e51a`, `aaa17b4` | `App.situation` and `render_situation`; the desk page's case block from it; `caseDetails`; case lines in `ownerContext`; summary lines in `cases`; the card's withheld reason in code's words |
| 2. Capability registry, permissions and the Agent tools page | `ae3dfd8` | `CAPABILITIES`, `tools_for`, `desk_system`; `GET`/`POST api/agent-tools`; Setup → Agent tools; a disabled tool neither offered nor executed |
| 3. Prepared decision, on-demand suggestion, workflow actions | `f791731`, `99c9b63` | `prepareDecision` and Confirm decision (`preparedVersion`); `requestSuggestion`; `actions_for`; the day-limit line on the case block |
| 4. Presentation, focus and recovery | `d5d165a`, `3351fd2` | `detail` and the Details expander; each invoice once; the three focus kinds; the retry and "Here is what the records show …" |
| 5. Validation | `ccb8b50` | 10 scenarios (58 turns) and five assertions in `conversation_check.js`; [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md) |
| Fix wave (Task 5's live findings, the reviews and the controller's live re-run), four rounds | `f83ddfc`, `6ca8d69`, `80d164f`, `50233e5` | short answers as a summary; the card's subject after `caseDetails`; codes and references as ids; a repeated call answered from above; "current" with a draft or a name not found; reference digits are no count; the owner's quoted line; suggestion claims against the comparison, asked again once; one context block; the draft kept on a search for its own name; the page's date words in results; step numbers are no figures; a lead-in added to a short answer does not keep it open; the runner records the owner's limit when no question was asked |
| 6. Records | `25e3e59` and the final records pass | `coordinator-v0.4`; these records. The preview deploy and its verification are pending. |

### Where the build differs from §0

- **§0.6, detail.** §0.6 lets the reply's `detail` decide and says "list their invoices" renders `full`. Code overrides a `full` that the model sends on a reply of at most two sentences carrying a figure, and shows it as `summary`, whatever the blocks; a last sentence ending in ":" is not counted (round 4), so a lead-in the model adds to a short answer ("Here are their invoices:") does not keep it open; a lead-in alone, or a short reply without a figure ("Here are the open invoices for Bayside Café."), stays `full`. On the live model the prompt line alone did not work (31 of 51 cards `full` in run 7). Recorded as a decision in E021.
- **§0.6, merging.** It is per invoice: with an "open" or "all" invoices block the overview's list goes; with an "overdue" block the overview keeps the invoices that are not overdue. Two invoices blocks, and the overview's open requests against a cases block, are not merged. Identical context blocks are merged (fix wave). Prepared-customer and prepared-decision blocks are never folded.
- **§0.1 and §0.2, the situation and a disabled tool.** The situation still carries the customer overview when `customerOverview` is off: it is what the page shows, and the registry governs tools, not the picture. A live model can still answer "what do they owe?" in words from it.
- **§0.2, the prompt.** Only lines that begin with a tool's name are dropped for a disabled tool; tool parameter descriptions still name other tools. Permission is also re-checked against the live setting at execution. `needsConfirmation` describes each tool; the confirmation is each flow's own button.
- **§0.3, the owner's words.** Days and dates are used only when the owner's message holds them, and a reason only in the owner's own words; the records changing since the analysis asks for a refresh. A new suggestion version withdraws a preparation (so does answering an owner question, which forms one).
- **§0.5, actions.** They reach the agent only; the page does not draw them. A step whose tool is off is "not now", "turned off under Setup → Agent tools".
- **§0.7, focus.** The unknown focus is set only from a name without digits (a code or reference that matched nobody sets none; marked `shortcut:` in the code). A search that finds nobody for the draft's own name keeps the draft. Stored string focuses read as customers.
- **§0.8, recovery.** The retry is one model call beyond the 8/6 caps; any tool it calls but `reply` is not run, and later calls in the withheld reply's batch are answered `NOT_RUN`. The subject of the fallback sentence is the one customer the blocks show, else the focus or the case's customer; after a search that found nobody, or with two customers, it names none.
- **Not in §0, added in the fix wave:** step numbers in a list not read as figures; customer codes and invoice references taken as ids; a repeated identical call refused unrun ("already answered"); the reference-digit and quoted-line guard changes; the suggestion's claim checked against code's comparison and asked again once; the page's date words beside ISO dates in four tools' results.

### Assumptions recorded while building (the ledger's rulings)

1. Task 1 stubbed `actions_for` as `[]`; Task 3 filled it.
2. The situation keeps the overview when `customerOverview` is off (by design, above). Cost if wrong: the agent can still state a balance in words with that tool off.
3. A tool's days and date arguments must be grounded in the owner's text (digits, numbers spelled up to twelve, weeks; ISO or day and month): a provenance check, not a phrase rule. Cost if wrong: one extra question.
4. A new suggestion version drops the preparation. Cost: the owner prepares again.
5. A name a search found nobody for becomes the "not found" focus, and a following "their" asks which customer (§0.7). Cost: one extra question after a miss.
6. Code demotes `full` to `summary` for a short answer (fix wave A), then only when the short answer carries a figure (A2), so a lead-in keeps `full`: the §0.6 deviation above. Cost: one click on Details. Scenarios for short asks accept `none` or `summary`.
7. `caseDetails` sets the card's subject to the case's customer (B). Scenario expectations that were wrong about correct behaviour (owner-case #6's block, pronoun-follow-ups #4's overview) were changed, not the product.
8. Tools accept display codes ("C-0003", the invoice reference) as ids; a repeated identical call is refused as already answered (C). The message for staff's empty `ownerContext` (C3) was dropped in round 2, because it made the model skip the overview.
9. Digits after a letter and a hyphen start no count (E), and a range of digits still does (round 3).
10. A word-for-word quote of a known line is exempt from the payment-judgement check only (F).
11. The refusal of `"current"` names a draft or a name not found (G); the prompt says to copy dates as written (H); identical context blocks are shown once (K).
12. The suggestion's within/beyond claim is withheld only when it is wrong for both the suggested and the asked date, and asked again once (I, I2).
13. A search that finds nobody for the draft's own name keeps the draft; results carry the page's date words beside ISO dates (round 2).
14. The implementers' commits carry the session's Opus co-author line rather than the one their dispatches named; history is not rewritten.
15. A last sentence ending in a colon does not count toward the two-sentence rule, and the `detail` prompt no longer describes a lead-in (round 4): at `80d164f` the model appended "Here are their invoices:" to short answers, which kept them open.
16. When the needs step asks no question, the runner's answer step records the owner's limit itself, by saying it in the case thread and confirming it as guidance (round 4; checks only, the product is unchanged).

**Recorded, not fixed (ledger):** "one open invoice for DEMO-1,250.00 (stated)" passes the guard; with a tool off the first reply can echo the owner's words; live wording is not stable between runs of the same code; a cite id the model truncated by one character failed a suggestion (owner-case #4 at `80d164f`), a model error with no code change.

### Validation

- **Unit suite:** 428 OK at `50233e5` (372 before the slice; 427 at `80d164f` and with the version bump). `desk_check.js` 73/73 at `50233e5` (60 before the slice). `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 at `d5d165a`; no page code changed after it.
- **Mock conversations:** `RESULT conversation: 310/310` with 18 live-only assertions skipped at `50233e5`, as at `80d164f`: 23 scenarios, 108 turns. At `ccb8b50` it was 310/310 with 17 skipped, and the 13 earlier scenarios were unchanged at 169/169.
- **Live model** (local Gemma, temperature 0, 23 scenarios, 108 turns): after round 4 of the fix wave, at `50233e5`, **325/325, 3 INFO, no reply withheld, no retry, no model failure, no failed suggestion**, 601 s. Earlier runs, as history:
  - run 7 (`3351fd2`), the slice before its fix wave: 307/317, 10 INFO, 3 replies withheld plus 1 recovered on the retry, 2 model failures;
  - round 1 (`f83ddfc`): 314/320, 7 INFO; round 2 (`6ca8d69`): 323/323, 4 INFO, no reply withheld;
  - round 3 (`80d164f`, the controller's re-run): 312/318, 10 INFO, 621 s. Its failing turns: numbered steps "1. 2. 3." read as figures (navigation #1 and #2 withheld); "Here are their invoices:" appended to short answers to keep them open (two-sentence-asks #1–#3); a 21-day suggestion where the needs step asked no question, so the runner recorded no limit (new-suggestion #4 and #7, a runner gap); a cite id truncated by one character (owner-case #4). Round 4 fixed the first three and passed all of them.

  The runs up to `80d164f` reported `coordinator-v0.3`; the version was bumped in `25e3e59`.
- **What the runs showed:** every way the owner gave a decision in words was prepared with code's date, and Confirm decision committed exactly that; a disabled tool was neither run nor drawn as Confirm; asking for a new suggestion in natural words formed a newer version and withdrew the preparation; every recall cited the case line "Up to 14 days this time"; no reply computed a day count of its own.
- **The reader's judgement:** the rubric for the new scenarios (run 7) was filled in by a model reader, from transcripts, not from the page. **The human column is empty.** Scripted wording, one local model, fictional data: not a usability result.
- **Through the public preview URL:** pending ([DEPLOYMENT.md](DEPLOYMENT.md), "Third slice (21 October)").

### What remains open

- **Known limits from the build:**
  - the guard's known text includes the situation's JSON, so every digit in it is a known number, and multi-word `label` values are masked like status labels;
  - spelled numbers beyond twelve do not ground a number of days ("fourteen days" asks again), and any other number in the owner's message can ground `days` (the prepared block shows the date before Confirm);
  - the same message sent twice while the model reads can prepare twice; a stale Confirm in the general thread is refused with a message;
  - the retry's other tool calls are neither run nor answered;
  - `caseDetails("current")` in a case thread reads the thread's case whatever the focus;
  - `customerOverview` and `invoices` still give dates in ISO form only;
  - on the search path the model is not told a name is a draft, so it can say the customer was not found while the chip says "(not yet a customer)";
  - not exercised live: the suggestion's claim retry (unit tests), the step-number rule (unit tests; the model did not number its steps in round 4) and the runner's no-question path (a scratch mock probe; the needs step asked a question in round 4);
  - a list after a colon ("Steps: 1. …") is still read as figures;
  - a cite id the model truncates fails the whole suggestion; tolerating a unique prefix would be a separate decision;
  - live wording is not stable between runs of the same code;
  - Task 3 did not check the prepared block at 375 or 390 px, and no later report records such a check.
- **Recorded, not fixed:** the three items above under the rulings, and the needs step's questions about late fees and a maximum amount.
- **The preview** deploy and its verification through the public URL, as both roles, are pending.
- **Hosted models:** still configuration only, untested. Q08 applies before any real data.
- **Guide revision 4** is pending, and **the effort comparison** has not been re-run on the desk.
- The model's quality is not evaluated, and no person has used the desk in this slice.
- The deferred items marked "Open" under revision 3 are unchanged.

## Revision 5 (21 October): the business tool layer as the reusable asset; the Lab

- **Source:** recorded by the development session from these sources, checked against the code:
  - the design, `docs/superpowers/specs/2026-10-21-nucleon-lab-design.md` (§2 the investigation, §3 the decision, §7 the builder's calls);
  - the plan, `docs/superpowers/plans/2026-10-21-nucleon-lab.md`;
  - the build ledger, task reports and fix-wave report (`.superpowers/sdd/2026-10-21-nucleon-lab/`, kept on the development machine and not in Git);
  - [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md) and [qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md);
  - the research notes of 21 October, which are scratch notes and not records.
- **Where:** branch `explore/agent-coordinator-20261019`, from `6d1ee1b` (design and plan) to `3e52328`, plus the records commit. It runs as a separate instance at `/lab/`, with its records instance at `/lab/records/` ([DEPLOYMENT.md](DEPLOYMENT.md), "Lab instance (reuse experiment)"). `lab-v0.1` went out first, at `c454d9d`; the Lab now runs `3e52328` (`lab-v0.2`). The preview at `/preview/` still runs `df10ab6` (`coordinator-v0.4`) and is the comparison baseline. The shared practice site still runs `f95f50f`. Not merged.
- **Status:** an experiment on the team's direction of 21 October. Not owner policy, and not a decision to adopt a framework, a front end or the Lab. Decision record: [DECISIONS.md](DECISIONS.md) E022. Prompts, tools and validators: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.5" and "lab-v0.2".

### The team's direction (21 October, the reuse question)

As given to the development session (design §1 and §6):

1. Investigate how far existing projects and frameworks can make Nucleon more natural and easier to maintain.
2. Deploy a working experiment, and test it in a real browser as both roles, with full conversations and unfamiliar wording.
3. Compare it with the current preview on the same model and equivalent data, and disclose any preloading.
4. Reuse where it cuts maintenance, and treat the business API and tool layer as the reusable asset.
5. Make capabilities configurable, with all implemented tools on per role in the experiment.
6. Keep role privacy, and keep consequential commitments explicit.
7. Address general causes, not sentences. Cancelling a proposal is distinct from declining a request.
8. Local model first; hosted APIs are a later comparison.

### What revision 5 changes in this proposal (design §3)

1. **The business tool layer is the reusable asset, not the conversation loop.** The causes of the review's seven findings were missing operations (design §2), not the front end or the absence of a framework. The records server therefore gains framework-neutral operations behind one HTTP surface, `GET /api/tools` and `POST /api/tools/<name>`, with the role from the session. The same registry (`coordinator.CAPABILITIES`) governs what each role is offered, and every result carries display text and its `subject`.
2. **Five operations close the causes:**
   - `compareExtension`, a comparison that prepares nothing;
   - `withdrawPreparation`, distinct from a decline;
   - `workQueue`, per role and across customers, with "waiting on whom";
   - `listRequests`, with a status filter;
   - `prepareHoldingMessage`, a promise-free status text written by code.

   The desk gets them too (`coordinator-v0.5`).
3. **Any conversation layer is a client of the surface.** That covers the desk, the Lab's agent and an external agent over MCP. Confirm, Create and the owner's confirmations stay buttons that call the records API, so no model or framework is in the commit path.
4. **The Lab tests reuse on top of it**: a Pydantic AI loop, assistant-ui components and an MCP server, as a third instance with its own fictional data. The comparison with the preview attributes each gain to the operations, the loop or the UI.
5. **Boundaries unchanged.** Owner-only context never reaches staff, the agent commits nothing, decisions stay the owner's, and nothing leaves Nucleon.

### What was built

| Task | Commits | What |
| --- | --- | --- |
| Design and plan | `6d1ee1b` | the investigation's summary, the decision, the builder's calls |
| 1. The business tool surface | `73e95d4`, `98e2448`, `f4e4c99` | `GET`/`POST api/tools`, the five operations, `subject` on every result; one result per Idempotency-Key, with the lock held for tools that do not call the model; openRequest only from the person's message; model unavailable as a refusal; withdrawPreparation's `invoiceReference` |
| 2. The Lab service | `922f62c`, `32b1ccf` | the Pydantic AI agent, 17 tools over HTTP with the person's cookie, five output validators, the SQLite store, the SSE API; one run at a time per thread |
| 3. The front end | `c454d9d` | assistant-ui 0.15.30 (Vite, React): a card per tool result, Confirm, Create, Copy, the thread list, a role chip, an "About" chip; `deploy/lab_check.js` |
| 4. The MCP server | `4b05f5d`, `b31fe2a` | streamable HTTP, stateless, bearer token → role; the exposure allow-list; codes from the records log |
| 5. Deployment | `0305cfc`, `2aa4acc`, `8bea1c5` | `labctl`, the launch agent, the Caddy routes `/lab/*` and `/lab/records/*`, `deploy/e2e_lab_check.py` |
| 6. Validation | `b2b890e` | `deploy/lab_conversation_check.js`, 11 scenarios; [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md) |
| Fix wave (the browser comparison and Task 6's findings), two rounds | `7b23cd8`, `b90ea4d`, `f3f75f9`, `781c1b5`, `52d8cb1`, `f10ee37`, `409d95f`, `14225ea`, `5165050`, `b44c31b`, `3e52328` | `lab-v0.2`; see the list below the table |
| 7. Records | this records commit | `coordinator-v0.5`; these records |

The fix wave changed:
- the reply became an output tool;
- claims in any voice need the tool that did them;
- a retry with no tool called asks for the tools;
- a case thread is shown its case each turn;
- turned-off tools are named;
- notes were added to results, and staff get the ownerOnly sentence;
- references are no figures;
- the repeat rule, and then only reply;
- error turns keep their calls;
- the composer is closed during a run;
- the runner's claim detector was fixed.

### Where the build differs from the design

- **§3.2, the reply.** In the design the guard became validators on a text reply. The build makes the reply an output tool (`lab-v0.2`), so every model turn is a tool call, as the desk's hand-written loop always did. With plain text allowed (`lab-v0.1`), the model skipped tools later in a thread and answered from history.
- **§7, the claim rule.** The design kept the claim rule unchanged. The build reads any assertion that an action happened (first person, perfect, past passive, "is now", "is being", what a tool did, a sentence starting with the participle). A stated state passes only when this run's results show it.
- **§7, the figure rule.** It is as designed, plus: the case shown at the start of a case-thread turn counts as results; digits after a letter and a hyphen are a reference; and each reference must appear in the results or the person's message.
- **Not in the design, staff wording.** Staff are told "The owner's guidance, limits and preparations are never shown to staff." rather than any untrue absence. A sentence that negates the owner's items is replaced by it; this is a phrase rule, accepted by ruling as a privacy guard on wording.
- **§3.3, streaming.** Tool cards stream as each call runs. The reply's text arrives once, after the validators pass (`delta`), so text that may be withheld is never shown. There is no separate `card` event: one card per tool result.
- **§3.3, the page.**
  - Refusals are shown inline in the card (`role=alert`), not as toasts.
  - There is no New-thread button, and no Edit or Regenerate.
  - The thread list loads once.
  - A prepared card learns that it was replaced only from this page's Confirm or a withdrawal in the thread.
  - `withheld` is kept but not displayed, so staff get no hint.
- **§3.1, kinds.** `compareExtension` is kind `read`: the registry implements read, prepare and act, and no calculate kind.
- **The records routes** differ from the plan's names:
  - sign-in is `api/demo/login {accessCode}`;
  - Confirm is `api/requests/{id}/decisions`, with the case's versions read just before;
  - the case link is `#/case/{id}`.
- **§3.4, MCP.**
  - The tools are the role's registry less openRequest, and less every act kind but withdrawPreparation and requestSuggestion. Each tool gains an optional `message`.
  - The SDK's low-level `Server` is used, stateless, so the role always comes from the request's own token.
  - The records' access codes are read from the records log, so a records restart needs nothing done.
- **§9, validation.** It uses a new Lab runner with 11 scenarios rather than `conversation_check.js`, because the APIs differ. The seven review messages are verbatim.

### Assumptions recorded while building (the ledger's rulings)

1. The desk's registry gets the five tools, on by default. The preview's baseline is a fixed commit, so gains are attributed by commit.
2. In the mock, the compare rules precede the prepare rules ("would N days fit" is a comparison).
3. Staff's `forYou` leaves out reply drafts, since drafts carry no sent status. listRequests keeps the customer's excerpt, marked untrusted.
4. openRequest over the surface needs the person's `message`, and never the model's `text`.
5. A request without a session gets 401, as every `api/` route does.
6. The amount mark "stated" is accepted, as the records write it.
7. One `delta` with the checked text, and no `card` event.
8. MCP is documented before deployment, with sequencing: Task 4 landed before the deploy.
9. After the browser comparison:
   - the reply is an output tool;
   - the claim check is widened;
   - a retry with no tool called says "call the tools first".
10. History stays text-only, and a case thread is shown its case as the person sees it, each turn.
11. The staff denial replacement is accepted as a privacy guard on wording.
12. Round 2 rewrote three LAB_SYSTEM lines that were phrase patches as general rules.

### Validation

- **Records:**
  - the unit suite is 443 OK (428 before the tool surface), and `desk_check.js` is 74/74;
  - at `73e95d4`: `ui_check.js` 150/150, `layout_check.js --seed` 217/217, and the desk's `conversation_check.js` 310/310 on the mock.
- **Lab:**
  - 87 unit tests at `b44c31b`;
  - `lab_check.js` 58/58 (a browser on scratch servers, the mock model, both roles, 390 and 375 px);
  - `python -m lab --print-prompts` is equal to PROMPTS.md's `lab-v0.2` block (22 blocks).
- **Lab conversations, mock:** 188/188.
- **Lab conversations, live** (local Gemma, temperature 0):

  | Run | Code | Result | Withheld | Errors |
  | --- | --- | --- | ---: | ---: |
  | `lab-v0.1` | `4b05f5d` | 187/205 (18 FAIL) | 5 | 1 |
  | After the fix wave | `5165050` | 218/218 | 0 | 0 |
  | Round 2 | `b44c31b` | 214/216 as scored; 216/216 re-scored | 1 | 0 |

  Round 2's two FAILs were the runner's own detector, fixed in `3e52328`. The runs between are in PROMPTS.md, "Observed behaviour: lab-v0.1 and lab-v0.2".
- **Browser comparison** (the builder's sessions through the public URLs; [qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md)):
  - the tool surface closed review findings 2, 3, 5 (partly), 6 and 7 on its own;
  - the Lab at `lab-v0.1` fabricated a withdrawal and a re-preparation, which the fix wave addressed;
  - no owner-only line reached staff on either site.

  The public re-run after the fix wave is the controller's (LAB-COMPARISON.md, "After the fix wave").
- **The reader's judgement:** the rubric was filled in by a model reader. The human column is empty. Scripted wording, one local model, fictional data: not a usability result.

### What remains open

- **The recommendation** (the controller's reading in LAB-COMPARISON.md) is for the team:
  - reuse the tool surface and the UI components;
  - keep the loop small;
  - the framework is optional.

  Nothing is adopted.
- **From fix-wave round 2:**
  - with prepareDecision off, the owner is no longer told it is turned off;
  - the state rule accepts "has been decided" or "approved" whenever any decision appears in the results;
  - staff asking to approve get the fixed sentence;
  - the guard is regex over wording.
- **The page:**
  - a replaced or already decided prepared card keeps Confirm until the records refuse it;
  - the thread list loads once;
  - one browser holds one role;
  - the bundle is one chunk of about 770 KB;
  - the composer's lost text was not reproduced; the box is closed during a run instead.
- **The desk.** It has the five operations in code (`coordinator-v0.5`), but they are not deployed to the preview.
- **Maintenance:**
  - the Lab's venv holds 42 pinned packages;
  - the page needs Node and Vite to build;
  - the framework and the MCP SDK move fast;
  - the records server stays stdlib-only.
- **Hosted models:** configuration only, untested. Q08 applies before any real data.
- **No person** other than the builder has used the Lab, and no external agent has connected through the public URL in a recorded check.

## Revision 6 (21 October, afternoon): revisions, prose first, understandable state; Tony's ideas

- **Source:** the design `docs/superpowers/specs/2026-10-21-lab-revisions-and-presentation-design.md`, the plan of the same date, the build ledger and task reports (`.superpowers/sdd/2026-10-21-lab-revisions-and-presentation/`, kept on the development machine and not in Git), and [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md) and [qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md), "Second iteration".
- **Where:** branch `explore/agent-coordinator-20261019`, from `1d1840a` to `a0ab50d` (fix wave 2), plus the records commits. Prompts are `lab-v0.4` and `coordinator-v0.7`; the code carried the labels `lab-v0.3` and `coordinator-v0.6` until the final records commit, and fix wave 2 changed the text under them (PROMPTS.md). The Lab was demonstrated at `6038696`, then deployed at `a0ab50d` at about 15:20 for a team demonstration, and the final deploy follows ([DEPLOYMENT.md](DEPLOYMENT.md), "Second deploy (21 October): revisions and presentation"). The preview (`df10ab6`, `coordinator-v0.4`) and the shared site (`f95f50f`) are unchanged.
- **Status:** an iteration on the team's direction after the independent review: a natural assistant that stays understandable and dependable when the person changes their mind. Not owner policy. Decision record: [DECISIONS.md](DECISIONS.md) E023.

**What revision 6 adds to this proposal:**

1. **The revision lifecycle** (§7, authority).
   - A prepared decision is a versioned proposal: `current`, then `superseded`, `withdrawn` or `confirmed`.
   - A change the owner asks for is a revision, and what the owner did not change is kept: the outcome, the days or date, the reason.
   - Only the current version can be confirmed, and the records refuse any other (409).
   - The history is stored on the request, so the page and the agent read the same picture, and the agent explains earlier proposals from it.
2. **Presentation defaults** (§6, the desk). A reply is its prose. Tool results fold under one closed "Records (N)", except the one card that is the answer or the action: a prepared decision, a draft, a holding message, a comparison that is the whole answer, or a list asked for. The steps fold under "Activity", and a run in progress shows one human line per step. A proposal card is drawn from live state, so a replaced or withdrawn proposal shows no button after navigation or reload.
3. **State fields** (§5, the coordinator).
   - A case gains `originalDue`, `dueNow` and `dueNowFrom`, `ordinal`, `flags` (a likely duplicate, never merged), `concerns`, `preparations` and `activePreparation`. Staff get no preparations.
   - Thread titles carry the status and the asked date, plus "(2nd request)" when there is an earlier request on the invoice.
   - A case thread opens with a header.
4. **Tony's ideas, scoped** (§4, owner knowledge).
   - **Adopted:**
     - the app asks the owner whether an earlier line still holds, when the case relies on an expectation said before today or on a line more than 30 days old;
     - staff raise a concern in their own words (`raiseConcern`), and the owner's queue lists the case "because staff raised a concern";
     - owner involvement stays explicit: "waiting on you", and Confirm.
   - **Kept separate:**
     - a one-off approval is not reusable guidance;
     - an extension is not a credit-limit or new-order decision;
     - "good standing" is context, not a recommendation.
   - **For the team:** a yes "from now on" and for how long; the reasons-skipped path; the A08 question set.
   - **Future:** decisions on standing authority, and periodic relationship reviews.
   - Notes: [reviews/2026-10-21-tony-questionnaire-response.md](reviews/2026-10-21-tony-questionnaire-response.md).

**Validation and what remains open:** as in E023. In brief:
- **Checks after fix wave 2:** records 463, desk 76/76, Lab tests 115 and `lab_check` 99/99.
- **Conversations:** 319/319 on the mock, and 354/364 live at `6038696`.
- **Fix wave 2** made one general change for each of that live run's six findings:
  - the reason clause from the owner's message;
  - a limit statement is guidance;
  - no card echo;
  - the app's question asked;
  - no open holding card for a decision ask;
  - no "today" about a date, which is model-limited.
- **The 9 affected scenarios** then went from 212/222 to 223/223 live at `a0ab50d`.

## Revision 7 (21 October, evening): honest numbers, usable imports, explicit authority

- **Source:** the design `docs/superpowers/specs/2026-10-21-week7-core-flow-design.md`, the plan of the same date, the team materials in [reviews/2026-10-21-team-meeting-and-model-review.md](reviews/2026-10-21-team-meeting-and-model-review.md), and [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Third iteration".
- **Where:** branch `explore/agent-coordinator-20261019`, from `60a9f59` onward. Prompts are `lab-v0.6` and `coordinator-v0.9`. Not deployed. Not owner policy. Decision record: [DECISIONS.md](DECISIONS.md) E025.

**What revision 7 adds to this proposal:**

1. **A numerical result that is a fact, not a prediction** (§5, the coordinator). `assessRequest` replays the ledger by code (debt, overdue, days past due, earlier receipts made while overdue, relationship length; Hoang's feature names), checks it against the owner's limits and recommends `approve_within_authority`, `escalate` or `decline_by_policy`. No approval model runs: the team's labels are proxies, so there is no probability or percentage anywhere. The same feature names are the place a model attaches when real decisions exist.
2. **Explicit authority** (§7). The owner sets the limits in Setup; with none set everything escalates. Staff act only through `actWithinAuthority`, which the records refuse unless the assessment allows it. A decision records who made it, on what footing (`owner` or `staff_within_authority`), the recommendation it saw and whether it followed it. After two concerns on an assessed case, the case waits for the owner with the reason on it.
3. **A scope for "from now on"** (§4). `remember.until` is one line with an end date; the Lab asks "this request only, or this customer from now on, and until when?" only when the owner's words reach beyond one case.
4. **Imports that are correct before they are convenient** (§8). The money unit is read from the file and a mismatch with the workspace is refused with nothing written; a payment that names an invoice is matched to it; "still owed" states its basis; a proposal's card shows its live state (proposed, applied, refused, duplicate).
5. **A failure that is not an empty answer** (§6). A customer or case that no longer exists is reported as gone; a failed read is reported as unreadable; conversations from before a records reset are read-only.

**For the team:** whether the authority limits match how the owner decides (Q03); real decisions to label a model with (Q05); the currency and unit of the real ledgers; whether staff would ask the AI first.

**Not built:** an approval model; credit-limit requests; multi-currency workspaces; a rotating owner questionnaire; customer communications.

**Validation and what remains open:** as in E025. In brief: records 542, Lab tests 137, `desk_check` 76/76, and the conversation check 443/443 on the mock (51 skipped). No live-model run of this iteration has been made.
