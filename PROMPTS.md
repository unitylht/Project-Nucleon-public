# PROMPTS.md — how Team Nucleon used AI tools

INFS3605, Term 3 2026, seminar W14A-9. This file has two parts:

1. **How the team used AI tools** while doing the project: research, meeting records, building, testing, the report and the video.
2. **The prompts inside the product**: the instructions and tools given to the two assistants in Nucleon, as they run today.

Our working rule throughout: an AI tool may draft, but a person decides, and every number we publish is checked against its source or against what the system recorded. Conversation logs are not reproduced here: they are long and contain private details of the businesses we worked with. The prompts below are the requests as given, translated where they were written in Chinese and shortened where they named people or businesses.

---

## Part 1. How the team used AI tools

### Tools

| Tool | Used for | Who |
| --- | --- | --- |
| Claude Code (Anthropic), Claude Opus and Fable models, with smaller models (Sonnet, Haiku) for simple subtasks | Writing and testing the software, model benchmarks, documentation, the operating manual, the report pack and this report; research and source checking | Hanting, on behalf of the team |
| A local open model, Qwen3.5-35B-A3B, in LM Studio | Inside the product: the Staff and Owner assistants (Part 3) | The product |
| Speech-to-text (Parakeet v3, Whisper Large v3 Turbo), run locally | Transcribing recordings of interviews, seminars, test sessions and narration | Hanting |
| AI chat assistants and AI meeting summaries | Research reports, meeting minutes from recordings, interview transcripts | Members (Part 2) |

The AI coding assistant cost about USD 2,500 in usage over the project, shared between the build, research and writing.

### Representative prompts, by stage

Each entry gives the request, what came back, and how we checked it.

**1. Turning discovery into a plan (Week 4).**
Prompt: "Here are the seminar transcripts, the workshop slides and today's owner interview. Catch me up on what the seminars established and prepare what the team needs for the Week 4 Solution Design workshop."
Result: a preparation pack with a candidate problem statement, evidence chains marked as owner report or assumption, personas, user stories and a platform shortlist.
Check: the team discussed it in the workshop. The next day the team chose a different focus (credit, not delivery planning), so most of the pack was not used. The evidence-versus-assumption habit stayed.

**2. Assembling an interview transcript.**
Prompt: "Merge the three recordings of the owner interview into one transcript with source timestamps. Keep the owner separate from the two interviewers, keep the wording, and list every correction you make."
Result: one transcript with a correction list and speaker labels marked as inferred.
Check: speaker labels were treated as provisional; quotes used in the report were checked against the recording.

**3. Designing the decision rules (26 October).**
Prompt (summary): "The owner should delegate a category of credit decisions with limits, not approve every case. Design how the agent may decide, what it may never do, and how the owner stays in control. The model must not be the authority."
Result: the Adaptive Decision Authority design: a versioned owner policy, checks in code, four outcomes, staff-confirmed evidence, owner override and pause.
Check: the design was written up, reviewed by the developer, and every rule was pinned by automated tests (1,259 unit tests by 13 Nov) and browser acceptance runs with the real model (17 of 17).

**4. Choosing the local model by measurement (31 October).**
Prompt (summary): "Build a benchmark that sends the five standard staff requests, judges each run by what the records stored rather than what the model said, and repeat every run. Compare the candidate models and tell me which one passes at least 9 of 10 runs."
Result: a benchmark and a qualification process; ten models screened; the instruction change that took the chosen model from 5/10 to 20/20 runs.
Check: results come from the database, not from the model's text; every result was repeated.

**5. Acting on tester feedback (6–13 November).**
Prompt examples: "Here are Tony's test notes. Fix what is broken and explain anything that is working as designed." / "The owners' first policy let the agent decide 0 of 20 invoices. Find out why, and design a set-up that shows the owner the effect before they save."
Result: changes the same day (pages 29 and 30 of the report list them), Quick setup, the Doctor and Get started.
Check: each change came with tests and a re-test on the live instance; the feedback register records which finding led to which change.

**6. Checking a live session against the records (12 November).**
Prompt: "Here is the audio transcript, the facilitator's handwritten notes and the system's records from the owner session. Write what happened, with times taken from the records, and note where the sources disagree."
Result: the account in the report (pages 27–29), with times from the system's own timestamps.
Check: the facilitator (Tony) confirmed the account; quotes were used only with the owner's permission.

**7. Research for the report (13 November).**
Prompt (to a research subagent): "Verify these figures the team already uses against their original sources, not blogs that repeat them. Open every page; never invent a reference; if a figure differs from the source, say so."
Result: 11 figures checked; two found wrong (a late-payment share that came from a different survey than the one named, and a business-share percentage from an earlier year) and corrected before the report was written.
Check: the 14 references with a DOI were then checked a second time against the publisher records at doi.org, and all references were imported into Zotero.

**8. Writing the report (13–14 November).**
Prompt (summary): "Merge the four members' evidence compendiums into the master document. Then write the 35-page report as a slide deck that reads like a report. Check it against the assessment outline. Label every number as measured, reported or estimated."
Result: this report, built from the team's documents.
Check: every page was read by the team; the go-to-market and unit-economics pages were marked for a member to review; defensive over-qualification was edited out in a second pass.

**9. The video script in the narrator's own voice (13 November).**
Prompt: "Tony would like the script to sound like the way he actually spoke in his last recording, so he does not have to rewrite it."
Result: a script rewritten from the transcript of his earlier narration (his sentence openers, tense and pace).
Check: Tony recorded it in his own words; the captions come from his recording, and every number on screen comes from the system's records, not from the narration.

### What AI did not do

It did not choose the business problem, decide what to build, or stand in for testing with real people. The owners' sessions were run by team members in person.

---

## Part 2. The prompts inside the product

What runs in the product today, copied from the project's prompt register (current as of 11 November 2026). Every earlier version and every change, with dates, is in [docs/PROMPT-REGISTER.md](docs/PROMPT-REGISTER.md). Data in the examples is fictional or anonymised (customer numbers only).

### Current assistants (as of 11 November 2026)

This section is current. Everything under "History (October 2026)" further down is kept as a record of how the project started and is no longer what runs. All business data in the tests quoted here is fictional unless a line says otherwise.

#### 1. What runs

| Part | What it is |
| --- | --- |
| Chat front end | LibreChat, with two agents (assistants): Staff and Owner. |
| Model | Qwen3.5-35B-A3B in LM Studio, on the Owner's own machine, context 32,768 tokens, temperature 0.2. No cloud model is used. |
| Link to Nucleon | MCP tools served by `lab/` (`lab/mcp_server.py`). Each tool call goes to the Records backend (`prototype/server.py`), which checks the caller's role. |
| Why this model | `docs/research/MODEL-BENCH-20261031.md` and `docs/research/MODEL-QUALIFICATION-PROCESS-20261031.md`. Ten other models were screened. The 9B model passed the bar once (9 of 10 runs) and failed it in an identical second sample (2 of 10). The 27B model passed (9 of 10) but took about 70 s per prompt, five times the 35B. Others failed on correctness, opened a case for an ambiguous message, or were too slow (one needed a median of 221 s). |

**Principle: the model proposes, code decides.** The model reads a message and recommends. `prototype/delegation.py` applies the Owner's delegation policy and decides whether a request is approved, needs evidence from Staff, or goes to the Owner. The model's words never approve anything. A tool result says what happened, and the instructions tell the model to report only that. Nothing is sent to a customer by Nucleon.

#### 2. The Staff assistant

##### 2.1 Instructions (verbatim)

This is `integrations/librechat/agents/instructions_staff.txt`, one paragraph per line. It is the source file of the live agent (checked against the repository, not against the running agent).

```text
You help a member of staff handle customer credit requests. Use tools for every business fact; never invent numbers, dates, ids or invoice numbers.
Each request is exactly one kind: a trial credit for a new customer (order amount and terms in days) or an extension of one existing invoice (its invoice number and the new due date). If the message mixes the two, or an extension names no invoice, ask Staff one short question about what they mean and stop; do not guess.
If a tool result has a hint, ask Staff exactly hint.question (and list hint.options, if there are any) and stop: make no further tool call this turn, and never retry with made-up values. If a tool returns INVALID_ARGUMENT or a schema error without a hint, ask Staff for the missing detail instead of retrying.
Before any decision tool, classify the message. If it names an order amount or payment terms AND also an invoice, a due date or an extension, or if it is unclear which kind it is, it is mixed: ask Staff one short question about which they mean and stop, calling no decision tool. Only a message that is clearly one kind goes on to the steps.
When Staff answer your question by naming one request ("the extension first", "Bayview"), handle only that one and stop: the other request waits for a message of its own. Never send two requests from one message unless Staff name both in it.
Steps for a request: 1) findCustomers (and the invoice for an extension). 2) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning; the backend assesses the request itself and applies the Owner's policy. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. Do not call assessDecision or whatIsNeeded. 3) Stop calling tools: the request is finished.
Every message that asks about a request gets the steps, even a message you have answered before, word for word, and even if you refused it a moment ago: Staff repeat a request when something changed outside the chat, usually the Owner deciding in Nucleon, so an earlier tool result (a CASE_OPEN refusal, a status) is history, not the current state. Never answer such a message from an earlier turn, never say "as I explained", and do not look it up with decisionStatus: call resolveDecision again for the request; the backend knows the earlier cases and refuses again itself if one is still open, and only its new result is the answer.
Decision tool results are compact: status, handling, statusText, why, nextStep and a few keyFacts. Reply in at most two sentences: statusText as it is, then what nextStep says. Do not restate the card: no amounts, lists or sections from the result; the card under your reply shows them.
The backend applies the Owner's delegation policy: report ONLY the outcome the tool result states; never say something is approved unless the result says decided/approved. If information is needed from Staff, tell them to use the button on the card. Nothing is ever sent to the customer by Nucleon; Staff informs the customer.
Use decisionStatus (for one case) or customerStatus (for a customer) only when asked where something stands, and then answer from its result.
```

##### 2.2 Tools

The agent is given eight tools. The Owner can switch every tool on and off under Setup, "Agent tools"; an agent only sees the tools that are on.

| Tool | What it does | On by default |
| --- | --- | --- |
| `findCustomers` | Finds customers by name, customer code or invoice reference. | yes |
| `customerOverview` | What one customer owes, with open invoices and requests. | yes |
| `invoices` | Lists one customer's open, overdue or all invoices. | yes |
| `resolveDecision` | Staff only. Gives the assistant's recommendation (approve, decline, escalate) on a credit request. The backend then assesses it, and approves inside the Owner's delegation, asks Staff for evidence, or sends it to the Owner. | no, the Owner switches it on |
| `assessDecision` | Shows what would happen to a request under the policy. Stores nothing. The current instructions tell the model not to call it. | no |
| `decisionStatus` | The backend status of one decision case. | no |
| `whatIsNeeded` | What evidence a request would need now. Stores nothing. The current instructions tell the model not to call it. | yes |
| `customerStatus` | Where one customer's decision cases stand. | yes |

Source of the defaults: `defaultEnabled` in `prototype/coordinator.py`. A refused call can carry a `hint` (see section 5).

##### 2.3 How the wording was reached

The bench (`tools/modelbench/bench.py`) runs five standard prompts against a scratch copy of Nucleon with the Staff agent's real tool definitions. It judges each prompt by the state of the backend, not by what the model says. The bar is at least 9 of 10 runs in which all five prompts are correct with at most 4 tool calls each. Each row below is the 35B model at context 32,768, 10 runs, fictional data.

| Step | Change | Runs on the bar | Prompts correct | Wrong approvals |
| --- | --- | --- | --- | --- |
| 1. Original steps | findCustomers, then whatIsNeeded or assessDecision, then resolveDecision | 5 of 10 | 47 of 50 | 0 |
| 2. Nudge | An automatic user message after an early stop (empty reply, or assessDecision/whatIsNeeded with no resolveDecision) | 6 of 10 | 47 of 50 | 0 |
| 2b. Instruction line | "End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing." | 2 of 10 | 42 of 50 | 0 |
| 3. Fewer steps, first try | Drop the whatIsNeeded paragraph (`variants/instructions_no_whatisneeded.txt`) | 4 of 10 | 43 of 50 | 0 |
| 4. Resolve-only | findCustomers, then resolveDecision once (`variants/instructions_resolve_only.txt`) | 17 of 20 over two samples (8 of 10, then 9 of 10) | 97 of 100 | 0 |
| 5. Resolve-only plus ambiguity rule | One paragraph added: classify the message first, ask Staff if it mixes a trial credit and an extension (`variants/instructions_resolve_only_ambiguity.txt`) | 10 of 10, then 10 of 10 again | 50 of 50 | 0 |

What each step taught:

- The early stops came from the extra steps. A nudge or an instruction line did not remove them. Removing the steps did, and it cut tokens by about 30 percent and time per prompt from about 15 s to 8 to 11 s.
- Resolve-only submitted the ambiguous "mixed" message as a case in 2 of 20 runs. The backend sent both to the Owner and approved nothing, but no case should exist. The ambiguity rule brought that to 0 of 20 runs.
- Three extra ambiguous prompts (an extension with no invoice, "Please approve this for Harbourline", an amount and a due date with no terms) were each answered with a question to Staff in 10 of 10 runs, with no case and no wrong approval. The clear prompts were never answered with a question instead of a decision (40 of 40).
- Across the final 80 runs there were 0 wrong approvals and 0 provider errors. The evidence is 20 runs on the original set and 10 per new prompt, and the new prompts were written after seeing the failure. The bench records this limit.

The live file has since grown beyond variant 5. It adds the turn-taking paragraph ("When Staff answer your question by naming one request..."), the paragraph about repeated messages (added 4 Nov, see 4b) and a shorter reply rule ("at most two sentences"). The variant files are the tested versions, not a copy of the live text.

#### 3. The Owner assistant

The Owner assistant is read-only. No tool it has decides, approves, declines, overrides, gives feedback or saves a policy. For any action it sends the Owner to the Decide page or the Control panel.

##### 3.1 Tools (12)

`decisionStatus`, `customerStatus`, `comparableCases`, `policyBacktest`, `impactSummary`, `doctor`, `modelStatus`, `cases`, `workQueue`, `customerOverview`, `invoices`, `findCustomers`.

| Tool | What it does | On by default |
| --- | --- | --- |
| `workQueue` | What waits on whom: cases waiting for the Owner and for others. | yes |
| `decisionStatus` | Backend status of one case. | no |
| `customerStatus` | Where one customer's cases stand. | yes |
| `comparableCases` | The reviewed cases a request would be compared with, as analogies. | yes |
| `policyBacktest` | What the policy with some changes would have decided on reviewed cases. Saves nothing. | yes |
| `impactSummary` | Impact figures of live cases, each with its source. | yes |
| `modelStatus` | The classifier: model in force, agreement with the Owner, promotion. | yes |
| `doctor` | The Doctor's answers about how the setup is working, written by code from the Owner's own cases. Changes nothing. | yes |
| `cases`, `customerOverview`, `invoices`, `findCustomers` | Reads of requests, customers and invoices. | yes |

The Owner can switch each tool off.

##### 3.2 Instructions (verbatim)

The live text is the seed (`seed_owner_agent_3080.js`) plus the additions of three update scripts, applied in place in this order: `update_owner_agent_queue.js` (6 Nov), `update_owner_agent_doctor.js` (11 Nov), `update_owner_agent_decide.js` (11 Nov). I could not read the live database, so I give each script's text separately instead of one merged block. `<RECORDS>` stands for the address of the Records pages that the script fills in.

**Seed.** One paragraph per line. Paragraphs 7 and 8 (Doctor and the two page addresses) were added to the live agent by the doctor script. The seed file now contains them too, and already says "Decide page".

```text
You are a read-only assistant for the business Owner. You explain decisions, list what is waiting, answer what-if questions and summarise impact. Use tools for every business fact; never invent numbers, dates, ids, names or reasons. If a tool you need is not in your list, say the Owner must switch it on under Setup -> Agent tools; never say the capability does not exist.
You cannot change anything. No tool you have decides, approves, declines, overrides, gives feedback or saves a policy, and you never say or imply that you did. For any action (deciding a waiting case, agreeing or disagreeing with a decision, overriding one, pausing the agent, changing the policy) tell the Owner to use the Decide page (<RECORDS>/#/review) or the Control panel (<RECORDS>/#/delegation), state the case's current status from decisionStatus in one sentence, give that link, and stop.
For any question about the model, the machine learning, the classifier, its accuracy, its training data or whether it decides anything: modelStatus, and repeat its text. The model is a shadow: it only ever sends a case to the Owner, and only once the Owner has promoted it on the Model page (<RECORDS>/#/research).
To explain a decision or say where a case or a customer stands: decisionStatus (one case) or customerStatus (a customer). decisionStatus takes a caseId from workQueue, or a customerId from findCustomers in the customerId argument, never a name or a code in requestId. After one NOT_FOUND, call cases or customerStatus instead of retrying. Repeat its statusText as it is and add what its nextStep says. To list what waits for the Owner: workQueue, and report its decisionCasesForYou (customer, exposure, since when) with the Decide link; cases lists requests, and an empty list of requests does not mean no decision case waits.
What-if questions ("what if the extension limit were 45 days?"): policyBacktest with only the settings to change, for example {"extensions": {"maxDays": 45}}. Report its numbers as they are, side by side (now and with the change). For "one step further" with no named setting, ask which setting (for example extensions.maxDays or newCustomers.maxExposure) or run policyBacktest with {} first and list the cases whose outcome differs. Say that the fictional counts are a simulation, that the live counts are the Owner's own reviews, and that nothing was saved.
Impact ("how is the agent doing?"): impactSummary. Report each figure with its numerator, denominator and source; a figure that is not known yet is not zero; time saved is an assumption nobody measured. Comparable cases for a request: comparableCases, always as analogies, not that customer's history.
Doctor ("why do I still get so many requests", "why do I keep correcting the agent", "what should I change"): call doctor, with the question that fits (came, corrections, help, outcomes, customers, rules) or with none to see all six headlines. Report only the lines it returns. Keep each number with its starting point, its gain and its cost; never add, subtract or estimate a number yourself. If the tool has not worked something out, say so. You cannot change settings: the Owner does that in Quick setup, which shows the effect before saving.
Quick setup is at <RECORDS>/#/quick-setup and the Doctor page, with a button under each suggestion that opens Quick setup filled in, is at <RECORDS>/#/doctor. Give these two addresses, not the Control panel, when a Doctor answer suggests a change. When you repeat a suggestion, keep its "now" number and what it would decide on today's open invoices.
Customer facts: findCustomers first, then customerOverview or invoices; quote amounts and caveats exactly as the tool gives them. Keep answers short: a few sentences or a short list.
```

**Addition 1, `update_owner_agent_queue.js` (6 Nov).** Added after a test with two waiting cases, where the assistant reported only one and restated the decision card under its reply. Appended to the end of the instructions.

```text
What is waiting: workQueue. Repeat its summaryText as it is and name every case in decisionCasesForYou; never leave one out, and never say nothing waits while that list has cases.
Do not restate a card: no amounts, lists or sections from a result that the card under your reply already shows. One or two sentences, then the next step.
```

**Addition 2, `update_owner_agent_doctor.js` (11 Nov).** Adds the `doctor` tool and the Doctor paragraph (paragraph 7 above) and, after the live trial, the two page addresses (paragraph 8 above). Appended to the end of the instructions.

**Addition 3, `update_owner_agent_decide.js` (11 Nov).** No new text. It renames "Review page" to "Decide page" and "the Review link" to "the Decide link" in the existing text, because the Owner's work list is called Decide in the navigation.

##### 3.3 Live trial of the doctor tool (11 Nov)

Two trials are recorded (`docs/handbook/pack/INFO-PACK.md` row 10, `docs/KNOWN-LIMITATIONS.md` L-004, `docs/DECISIONS.md`).

- Before the tool existed, the local model was given a facts sheet written by code and 24 questions. 19 answers were right and 5 wrong (1 empty, 2 used the wrong starting number, 1 left out a cost, 1 guessed a figure not on the sheet). Each took 1 to 3 minutes. So Nucleon answers the six preset questions itself (the Doctor page, `#/doctor`), with no model.
- Live trial of the Owner assistant's `doctor` tool: the right question every time, 18 to 27 s each, core numbers all correct. It dropped one figure, added judgement words and once muddled an explanation. It also named the Control panel's address for Quick setup and dropped the "now" numbers, which is why paragraph 8 exists. Verdict: keep the tool as a pointer; the page is the source of truth.

#### 4. Notes added to a message outside the system prompt

The proxy `deploy/m3-local/bin/title-proxy` sits between LibreChat and LM Studio. It forwards everything byte for byte, except in three cases. Two of them append a short note to the user's message. A note beside the message held where a rule in the system prompt did not.

##### 4a. Title pre-fill

LibreChat asks the model for a conversation title. Qwen reasoned for about 2,000 characters first, so a title took 6 to 8 s, longer than the reply. The proxy recognises the title request and adds an empty think block as the start of the answer, so the model answers at once (0.2 s measured on 1 Nov 2026). This is not a prompt for the assistant's work.

##### 4b. Repeat note (4 Nov)

When the newest user message repeats an earlier user message of the same chat word for word, this is appended to it:

```text
[Nucleon note: this message repeats an earlier message of this chat word for word. Treat it as new: something may have changed outside the chat since (the Owner decides in Nucleon), so do not answer from earlier turns or earlier tool results. If it is a request, run the steps and call resolveDecision for it again; if it is a question, answer it from a fresh tool call.]
```

Why: the Owner decides in Nucleon, outside the chat. Staff then repeat the same message to see the new state. The model answered such repeats from its earlier turns with no tool call. The system prompt had a rule saying not to do that (it is still in the Staff instructions, the paragraph that starts "Every message that asks about a request gets the steps"). The rule did not hold against four identical turns. The note placed next to the message did.

##### 4c. Vague-request note (11 Nov)

Applies only to requests that carry the decision tool, so only the Staff assistant. The proxy looks for a message asking for more time (extension wording) and checks whether it names an invoice and gives a date or a number of days. Status questions are left alone. It appends one of three notes.

Names no invoice:

```text
[Nucleon note: this message asks for more time but names no invoice. Do not choose an invoice yourself, and do not take the longest extension the policy allows. Ask Staff one short question: which invoice it is about? Call no decision tool this turn.]
```

Gives no date or number of days:

```text
[Nucleon note: this message asks for more time but gives no new payment date and no number of days. Do not choose a date or a number of days yourself, and do not take the longest extension the policy allows. Ask Staff one short question: until what date, or for how many days? Call no decision tool this turn.]
```

Names no invoice and gives no date or number of days:

```text
[Nucleon note: this message asks for more time but names no invoice and gives no new payment date or number of days. Do not choose an invoice, a date or a number of days yourself, and do not take the longest extension the policy allows. Ask Staff one short question: which invoice it is about, and until what date? Call no decision tool this turn.]
```

Evidence, from the live test on the real-data instance on 11 Nov 2026 (a real small business's records, anonymised):

| | Result |
| --- | --- |
| Before the note | Staff wrote "Customer 0010 wants more time to pay." (no invoice, no date). The model picked the customer's most recent open invoice and exactly the 30 days the policy allows. The backend saw a complete request inside the policy and approved it. The system prompt already said "ask, do not guess". |
| After the note | Three vague messages ("... wants more time to pay.", "... asks for more time on invoice 00000065.", "... wants two more weeks.") each got one clarifying question and created no case. |
| Not affected | A clear request, a status question and an Owner-assistant question. |

The data was restored to its snapshot after both runs. This is a small live test, not a bench. The proxy has a self-test (`title-proxy --selftest`) for the matching rules.

#### 5. Other places where text is given to a model

| Place | What the model gets |
| --- | --- |
| Compact results (`forModel`) | For the decision and read tools, the Lab (`lab/mcp_server.py`, `model_text`) gives the model only the `forModel` object of the result, about 200 to 600 characters (up to 1,500 for tools with figures), instead of the full result of 8,000 to 10,000. The full result goes to the card shown under the reply. Other tools' results are unchanged. |
| Hints | A refused call carries `hint` with `ask` (kind, invoice, customer, amount, terms or dueDate), `question` and sometimes `options`. The Staff instructions say to ask Staff exactly `hint.question`, list `hint.options` and stop. The hint holds no private data. |
| Tool descriptions | Each tool's description (`prototype/coordinator.py`) is part of what the model reads. |
| Not a model | The form parser `deterministic_extract` in `prototype/agent.py` is plain code (regular expressions). It reads one invoice reference, one written date and a reason, with no language model. It is used by the mock adapter and as a fallback. |

#### 6. Known prompt-level weaknesses (seen 11 Nov in live conversations; status on 12 Nov)

1. The Owner assistant answered "What is waiting for my decision?" with internal field names (`decisionCasesForYou`, `forYou`) and listed only some of the waiting cases. **Fixed 12 Nov:** it now lists every waiting request in plain words.
2. Asked "What are my current rules?", the Owner assistant described which rules send requests to the Owner instead of giving the policy's values, and spoke of "the Owner" in the third person. **Fixed 12 Nov:** it now states the rules in force.
3. The Staff assistant was told a customer is new and not in the records. It asked for a customer id instead of telling Staff to add the customer under Customers first. **Partly fixed 12 Nov:** it now says the customer was not found, but does not always add the instruction.
4. For a customer who "cannot promise a date", the Staff assistant still recommended approval once the information is confirmed. **Fixed 12 Nov:** such a customer is now recommended for decline.

None of these approves anything wrongly, because the backend decides. They are wording and judgement faults in what the model says or recommends.

#### 7. How to change a prompt safely

1. Edit the source. For Staff that is `integrations/librechat/agents/instructions_staff.txt`; then run `python3 integrations/librechat/agents/sync_instructions.py` (use `--check` to test) so the copy inside `update_ada_agent_hints.js` and the README match. The model bench reads the text file.
2. Test the wording on the bench first (`tools/modelbench/bench.py --instructions-file <file> --runs 10`), on fictional data, and compare with the table in 2.3.
3. Back up the LibreChat agents collection before any live change.
4. Apply the change with an update script in `integrations/librechat/agents/` that edits the agent in place. The scripts are idempotent: running one twice changes nothing more.
5. Never re-seed the Owner agent (`seed_owner_agent_3080.js`). The seed deletes and recreates the agent, which changes its id and its author. To change the Owner's text, write an update script like the three above.
6. Test live on a copy of the data, and restore the data afterwards.
7. For a rule the model keeps breaking, prefer a note beside the message (section 4) or a change in code over a longer system prompt.

---
