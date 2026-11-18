# Conversational review: the desk agent, second slice

**Fictional data. 13 scripted conversations, a mock agent and one local model. Not a usability result.**

- Date: 2026-10-20
- Commit tested: `cbd0ad2` (branch `explore/agent-coordinator-20261019`), plan `docs/superpowers/plans/2026-10-20-conversational-desk.md`, Task 5 (§0.9).
- Scripts: `deploy/conversation_check.js` and `deploy/conversations.json`.
- Live model: the configured local Gemma 4 26B-A4B (served as `gemma-rp`, OpenAI-compatible adapter, temperature 0, `reasoning_effort: none`). Prompt version reported by the server: `coordinator-v0.2`. The desk prompt is the Task 1–3 text that `--print-prompts` prints; PROMPTS.md is updated in Task 6.

## Method

- **Scenarios.** `deploy/conversations.json` holds 13 scenarios and 50 turns. Each turn is something staff or the owner types (`say`) or a control they use (`do`: confirm what was understood, answer the agent's question, decide, create the customer a draft prepared). Each turn lists its assertions. The scenarios cover:
  - five wordings of "what does X owe", alternating customers;
  - pronoun follow-ups;
  - a customer switch mid-thread ("and Supplies?");
  - a three-part ask;
  - three navigation questions;
  - adding a customer by conversation, then a duplicate;
  - the owner's context, staff's request and the owner's case (a question, an answer within the stated limit, the suggestion, a decision);
  - a request beyond the stated limit;
  - staff asking for the owner's private context;
  - an unknown customer;
  - a vague ask;
  - "what can you do?";
  - the owner asking "what did I tell you about Bayside?".
- **Runs.** Before each scenario the runner resets the practice data through the demo console. Each scenario therefore starts with a fresh general thread, no focus and no context. It then adds Bayside Café with invoice DEMO-501 (AUD 1,200.00 stated, due Tue 20 Oct 2026) beside the sample's Harbour Demo Supplies and Harbour Demo Logistics. The business date is Fri 16 Oct 2026. Everything goes through the HTTP API with both roles signed in. The access codes are read from the service log and never printed.
- **Assertions per turn:**
  - `about`: the customer the answer card names.
  - `blocks` / `blocksAbsent`: the blocks the card has or must not have, in any order.
  - `amountsMatchRecords`: every invoice amount in the overview and invoice blocks, and the overview totals, equal `/api/records`, and each row belongs to the block's customer. A card with no amounts fails this.
  - `noOwnerOnlyText`: for staff, none of the owner's own turns, private lines or answers anywhere in the turn's response or staff's thread view.
  - `nextStep`: the kind, and optionally the target.
  - `textContains` / `textLacks`: whole words in the reply prose.
  - `withheld`: whether the prose was replaced by the guard sentence.
  - `askedWhichCustomer`: the prose asks which customer, and no customer block is shown.
  - `focus`: the thread's current customer for that role after the turn.
  - `caseOpened`, `draftPrepared`, `statementProposed`, `customers` (how many customers have a name in the records), `questionAsked`, `suggestion` (`status`, `outcome`, `withinDays` after the current due date, `shorter` than asked) and `decided`.
  - Each `do` step also has a `done` check.
- **Live-optional and live-only.**
  - `liveOptional` lists, per turn, the assertions that depend on the model's wording (mostly `withheld`, `textContains` and `askedWhichCustomer`). With `--live` their failures print as INFO and are not counted.
  - Structural assertions always count, live or mock: `about`, `blocks`, amounts, staff visibility, case/draft/statement, suggestion and focus.
  - `liveOnly` (4 assertions, two turns) marks wording the mock's keyword rules do not read: "anything I should know about…" and "what did I tell you about…". Without `--live` these print as SKIP and are not counted.
- **Transcripts.** The runner writes `transcripts.json` and one Markdown file per scenario to its output folder. Live run 1's transcript is condensed below. A second live run sent the model calls through a scratch logging proxy, so the raw text of any withheld reply could be read. The server itself keeps only the kind of reason, by design.
- **Reader.** The rubric was filled in from the live transcripts by a model reader (Claude Opus, the agent that wrote this check), not by a person. The human column is left empty.

Commands (scratch paths outside the repository):

```
deploy/ui_check_server.py <scratch>/m1.sqlite3 18871
node deploy/conversation_check.js http://127.0.0.1:18871 <scratch>/m1.log <scratch>/mock1
prototype/server.py --config <scratch>/live-config.json    # config.example.json with a scratch db, port 8769, sampleData, demo console
node deploy/conversation_check.js http://127.0.0.1:8769 <scratch>/live.log <scratch>/live1 --live
```

## Mock result

**164/164 assertions passed. 4 were SKIP (live only).** A second run on a fresh mock server gave identical lines. A negative probe with deliberately wrong expectations made every assertion type fail. That probe used a scratch copy, not committed.

The mock follows the plan's rules: "which customer?" for Seaview, the focus kept, three blocks for the three-part ask, a draft and nothing created, a suggestion of Tue 3 Nov 2026 (14 days) against a 21-day request. Its keyword rules do not read two wordings. To "anything I should know about Bayside?" and "what did I tell you about Bayside?" it gives the capability sentence, with the focus still set to Bayside Café. This is a limit of the test double, not of the product. The follow-up turns in those scenarios pass on the mock.

## Live result

Two live runs, each about 200 s for 50 turns (2–11 s per turn). Both gave **159/161 counted assertions, 7 INFO and the same 2 FAILs**. Run 1 is tabled below; run 2 differed only in wording, noted after the transcripts.

| Scenario | PASS | FAIL | INFO | What happened |
| --- | ---: | ---: | ---: | --- |
| owe-five-ways | 21 | 0 | 2 | All five on the right customer, with the records' amounts. Turn 2's wording was withheld; it stated a correct amount. |
| pronoun-follow-ups | 18 | 0 | 0 | "their", "overdue ones" and "they" stayed on Logistics. |
| switch-mid-thread | 15 | 0 | 0 | "and Supplies?" switched; "their" stayed on Supplies; "another customer" asked which, with the focus kept. |
| three-part-ask | 10 | 0 | 0 | All three blocks on one card; only the shared lines; the prose names two of the three parts. |
| navigation | 14 | 0 | 1 | Page, steps and an "open" control each time; the prose does not name the button. |
| add-customer | 17 | 0 | 1 | Draft, nothing created, created by the person, focus moved; the duplicate is named but has no link. |
| owner-case | 14 | 0 | 0 | Question, answer, suggestion Tue 10 Nov (within 30 days), approved; staff status "Approved to Tue 10 Nov"; no owner words for staff. |
| beyond-limit | 11 | 0 | 0 | Suggestion Tue 3 Nov 2026: 14 days, shorter than the 21 asked, "shorter than requested but within the allowed limit". |
| staff-owner-context | 11 | 0 | 1 | Nothing private reached staff; the prose says the owner provided no context, which is untrue. |
| unknown-customer | 4 | **2** | 1 | **Wrong customer:** for Seaview it showed Logistics' overview instead of asking which customer. |
| vague-ask | 9 | 0 | 0 | Overview and (empty) context for Bayside Café; the follow-up's wording was withheld (a correct amount). |
| capabilities | 4 | 0 | 1 | A plain list of what to ask, with the pages block. |
| owner-recall | 11 | 0 | 0 | The owner's own words, paraphrased in the prose and listed in the block; "nothing overdue" said plainly. |

`noOwnerOnlyText` passed on every staff turn in both runs (6 turns, up to 8 owner-only phrases each).

## Live transcript (run 1, condensed)

Each turn: what was typed or done, the reply prose as shown, what the card showed (amounts are the card's), the tools called and the seconds taken. Lines that are not PASS follow the turn.

#### owe-five-ways

1. **Staff:** What does Harbour Demo Logistics owe?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 5 s
2. **Staff:** How much is Supplies owing us at the moment?
   - **Nucleon:** The agent's wording was withheld; the details below are from the records.
   - *Shown:* overview of Harbour Demo Supplies: DEMO-101 AUD 1,250.00 (stated), not overdue | open invoices of Harbour Demo Supplies: DEMO-101; tools findCustomers, customerOverview, invoices; 4 s
   - INFO withheld (withheld); INFO textContains (Supplies)
3. **Staff:** Logistics, what's their balance?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
4. **Staff:** Can you give me an overview of what Supplies owes?
   - **Nucleon:** Harbour Demo Supplies has 1 open invoice. There are no overdue invoices or open requests for this customer.
   - *Shown:* overview of Harbour Demo Supplies: DEMO-101 AUD 1,250.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
5. **Staff:** how much do logistics still owe us
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue | open invoices of Harbour Demo Logistics: DEMO-201; DEMO-202; tools customerOverview, findCustomers, customerOverview, invoices; 5 s

#### pronoun-follow-ups

1. **Staff:** What does Harbour Demo Logistics owe?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
2. **Staff:** and their invoices?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* open invoices of Harbour Demo Logistics: DEMO-201; DEMO-202; tools invoices; 2 s
3. **Staff:** what about overdue ones?
   - **Nucleon:** There is 1 overdue invoice for Harbour Demo Logistics. It is 7 days overdue.
   - *Shown:* overdue invoices of Harbour Demo Logistics: DEMO-201; tools invoices; 2 s
4. **Staff:** do they have any open requests?
   - **Nucleon:** Harbour Demo Logistics has no open requests.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue | requests: none; tools customerOverview, cases; 3 s

#### switch-mid-thread

1. **Staff:** What does Harbour Demo Logistics owe?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
2. **Staff:** and Supplies?
   - **Nucleon:** Harbour Demo Supplies has 1 open invoice.
   - *Shown:* overview of Harbour Demo Supplies: DEMO-101 AUD 1,250.00 (stated), not overdue | open invoices of Harbour Demo Supplies: DEMO-101; tools findCustomers, customerOverview, invoices; 4 s
3. **Staff:** and their invoices?
   - **Nucleon:** Harbour Demo Supplies has 1 open invoice.
   - *Shown:* open invoices of Harbour Demo Supplies: DEMO-101; tools invoices; 2 s
4. **Staff:** What about another customer?
   - **Nucleon:** Which customer would you like to look up?
   - *Shown:* no blocks; tools ; 1 s

#### three-part-ask

1. **Owner:** Harbour Demo Logistics are rebuilding their delivery fleet this quarter.
   - **Nucleon:** What I understood (Harbour Demo Logistics): observation "Harbour Demo Logistics are rebuilding their delivery fleet this quarter."; 8 s
2. *Owner confirm (shared with staff)*
3. **Owner:** Between us, I think Harbour Demo Logistics may be sold next year.
   - **Nucleon:** What I understood (Harbour Demo Logistics): relationship "Between us,"; observation "I think Harbour Demo Logistics may be sold next year."; 4 s
4. *Owner confirm*
5. **Staff:** Can I get an overview of Harbour Demo Logistics, their overdue invoices and anything the owner has shared about them?
   - **Nucleon:** Here is the overview for Harbour Demo Logistics. There is 1 overdue invoice.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue | overdue invoices of Harbour Demo Logistics: DEMO-201 | context of Harbour Demo Logistics: 2 line(s); tools findCustomers, customerOverview, invoices, ownerContext; 5 s

#### navigation

1. **Staff:** where do I add a customer?
   - **Nucleon:** You can add a new customer from the Customers page. Follow these steps to do so.
   - *Shown:* navigation addCustomer (#/customers, "Add customer") | next step open #/customers "Add customer"; tools whereIs; 2 s
   - INFO textContains (Add customer)
2. **Staff:** how do I import a payment list?
   - **Nucleon:** You can import a payment list from the Imports page. Follow these steps to do so.
   - *Shown:* navigation import (#/imports, "Import a CSV file") | next step open #/imports "Import a CSV file"; tools whereIs; 2 s
3. **Staff:** How do I record a payment?
   - **Nucleon:** You can record a payment from the Customers page. Follow these steps.
   - *Shown:* navigation recordPayment (#/customers, "Record payment or credit") | next step open #/customers "Go to Customers"; tools whereIs; 2 s

#### add-customer

1. **Staff:** add Riverside Bakery as a customer
   - **Nucleon:** I have prepared a draft for Riverside Bakery. You can complete the creation process yourself.
   - *Shown:* navigation addCustomer (#/customers, "Add customer") | draft Riverside Bakery | next step draft "Create customer"; tools prepareCustomer, whereIs; 3 s
2. **Staff:** yes, add it
   - **Nucleon:** I have prepared a draft for Riverside Bakery. You can complete the creation process yourself.
   - *Shown:* navigation addCustomer (#/customers, "Add customer") | draft Riverside Bakery | next step open #/customers "Add customer"; tools prepareCustomer, whereIs; 3 s
3. *Staff createCustomer Riverside Bakery*
4. **Staff:** what does it owe?
   - **Nucleon:** Riverside Bakery does not owe anything. There are no open or overdue invoices recorded.
   - *Shown:* overview of Riverside Bakery:  | all invoices of Riverside Bakery: none; tools customerOverview, invoices; 3 s
5. **Staff:** add Harbour Demo Supplies as a customer
   - **Nucleon:** Harbour Demo Supplies already exists.
   - *Shown:* no blocks; tools prepareCustomer; 2 s
   - INFO nextStep (none)

#### owner-case

1. **Owner:** Bayside Café has struggled recently, but I have known them for years. They have an event next month and should recover. I would consider a small extension, but I don't want their debt to increase for now.
   - **Nucleon:** What I understood (Bayside Café): observation "Bayside Café has struggled recently"; relationship "I have known them for years"; observation "They have an event next month"; expectation "should recover"; guidance "I would consider a small extension"; constraint "I don't want their debt to increase for now"; 9 s
2. *Owner confirm*
3. **Staff:** Hi, Bayside Café here. Could we pay invoice DEMO-501 on 2026-11-10 instead?
   - **Nucleon:** I opened a case for this request in its own thread.; tools findCustomers, openRequest; 2 s
4. *Owner answer: 'Up to 30 days is fine this time'*
   - Agent's question: "Regarding your comment that you 'would consider a small extension', does a 21 day delay fall within that range?"
   - Suggestion: approve 2026-11-10: "The suggestion is based on the guidance to consider a small extension within the allowed timeframe."
5. *Owner decide*
   - Decision: approve 2026-11-10
6. **Staff (case thread):** what's the status of this request now?
   - **Nucleon:** The request for invoice DEMO-501 is currently Approved to Tue 10 Nov.
   - *Shown:* requests: DEMO-501 Approved to Tue 10 Nov; tools cases, cases; 4 s

#### beyond-limit

1. **Owner:** Bayside Café has struggled recently, but I have known them for years. They have an event next month and should recover. I would consider a small extension, but I don't want their debt to increase for now.
   - **Nucleon:** What I understood (Bayside Café): observation "Bayside Café has struggled recently"; relationship "I have known them for years"; observation "They have an event next month"; expectation "should recover"; guidance "I would consider a small extension"; constraint "I don't want their debt to increase for now"; 10 s
2. *Owner confirm*
3. **Staff:** Hi, Bayside Café here. Could we pay invoice DEMO-501 on 2026-11-10 instead?
   - **Nucleon:** I opened a case for this request in its own thread.; tools findCustomers, openRequest; 2 s
4. *Owner answer: 'Up to 14 days this time'*
   - Agent's question: "Regarding your note that you 'would consider a small extension', does a 21 day delay fall within what you consider small?"
   - Agent's question: "You noted 'They have an event next month' but also said 'I don't want their debt to increase for now'; will the event impact their ability to pay this invoice?"
   - Suggestion: approve 2026-11-03: "The suggested date is shorter than requested but within the allowed limit."
5. **Owner (case thread):** what have I said about them?
   - **Nucleon:** Here is what you have said about Bayside Café.
   - *Shown:* context of Bayside Café: 6 line(s); tools ownerContext, ownerContext; 4 s

#### staff-owner-context

1. **Owner:** Bayside Café has struggled recently, but I have known them for years. They have an event next month and should recover. I would consider a small extension, but I don't want their debt to increase for now.
   - **Nucleon:** What I understood (Bayside Café): observation "Bayside Café has struggled recently"; relationship "I have known them for years"; observation "They have an event next month"; expectation "should recover"; guidance "I would consider a small extension"; constraint "I don't want their debt to increase for now"; 11 s
2. *Owner confirm*
3. **Staff:** what has the owner said about Bayside?
   - **Nucleon:** The owner has not provided any context for Bayside Café.
   - *Shown:* context of Bayside Café: 0 line(s); tools findCustomers, ownerContext; 4 s
   - INFO blocksAbsent (context)
4. **Staff:** Give me an overview of Bayside Café, including what the owner said.
   - **Nucleon:** Here is the overview for Bayside Café. No context has been provided by the owner.
   - *Shown:* overview of Bayside Café: DEMO-501 AUD 1,200.00 (stated), not overdue | context of Bayside Café: 0 line(s); tools customerOverview, ownerContext; 3 s

#### unknown-customer

1. **Staff:** What does Harbour Demo Logistics owe?
   - **Nucleon:** Harbour Demo Logistics has 2 open invoices. One invoice is overdue by 7 days.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
2. **Staff:** What does Seaview owe?
   - **Nucleon:** I couldn't find a customer named Seaview. I have shown the overview for Harbour Demo Logistics instead.
   - *Shown:* overview of Harbour Demo Logistics: DEMO-201 AUD 480.00 (stated), 7 days overdue; DEMO-202 AUD 2,100.00 (stated), not overdue; tools findCustomers, customerOverview; 3 s
   - FAIL about (Harbour Demo Logistics); FAIL blocksAbsent (overview); INFO askedWhichCustomer (did not ask)

#### vague-ask

1. **Staff:** anything I should know about Bayside?
   - **Nucleon:** Here is the current information for Bayside Café. There are no specific notes from the owner in the records.
   - *Shown:* overview of Bayside Café: DEMO-501 AUD 1,200.00 (stated), not overdue | context of Bayside Café: 0 line(s); tools findCustomers, customerOverview, ownerContext; 4 s
2. **Staff:** what do they owe?
   - **Nucleon:** The agent's wording was withheld; the details below are from the records.
   - *Shown:* overview of Bayside Café: DEMO-501 AUD 1,200.00 (stated), not overdue; tools customerOverview; 2 s

#### capabilities

1. **Staff:** what can you do?
   - **Nucleon:** This desk is for managing customer requests. You can ask about a customer's balance, invoices, or the status of their requests.
   - *Shown:* navigation whereAmI (#/requests, "Requests"); tools whereIs; 2 s
   - INFO textContains (owes)

#### owner-recall

1. **Owner:** Bayside Café has struggled recently, but I have known them for years. They have an event next month and should recover. I would consider a small extension, but I don't want their debt to increase for now.
   - **Nucleon:** What I understood (Bayside Café): observation "Bayside Café has struggled recently"; relationship "I have known them for years"; observation "They have an event next month"; expectation "should recover"; guidance "I would consider a small extension"; constraint "I don't want their debt to increase for now"; 9 s
2. *Owner confirm*
3. **Owner:** what did I tell you about Bayside?
   - **Nucleon:** You mentioned that Bayside Café has struggled recently but you have known them for years. You also noted they have an event next month and should recover, adding that you would consider a small extension but don't want their debt to increase for now.
   - *Shown:* context of Bayside Café: 6 line(s); tools findCustomers, ownerContext; 4 s
4. **Owner:** and what is overdue for them?
   - **Nucleon:** There are no overdue invoices for Bayside Café. There is one open invoice due on 2026-10-20.
   - *Shown:* overview of Bayside Café: DEMO-501 AUD 1,200.00 (stated), not overdue | overdue invoices of Bayside Café: none; tools invoices, customerOverview; 3 s

**Run 2 differences** (same prompts, same data, same assertions):

- owner-case: the agent asked two questions instead of one. The second was "You mentioned 'They have an event next month'; should the payment timing be adjusted based on this event?"
- beyond-limit: one question instead of two; the same suggestion (Tue 3 Nov 2026).
- vague-ask turn 1: "There is no additional context recorded for Bayside Café. They have one open invoice due on 2026-10-20."
- Otherwise only small rewordings ("The request regarding invoice DEMO-501…").
- The two withheld replies were withheld again. Their raw text, read through the proxy:
  - owe-five-ways #2: "Harbour Demo Supplies has 1 open invoice. The amount owed is AUD 1,250.00."
  - vague-ask #2: "Bayside Café owes AUD 1,200.00 according to the records. There is one open invoice for this amount due on 2026-10-20."

## Rubric (live run 1)

The three questions:

- **Q1:** Is the answer understandable at a glance?
- **Q2:** Could the person complete the task without splitting the request or assembling meaning across cards?
- **Q3:** Is the next step clear when one is needed?

The model reader judged from the transcript text and the blocks listed, not from the rendered page.

| Scenario | Q | Model reader (Opus) | Human reader |
| --- | --- | --- | --- |
| owe-five-ways | Q1 | Mostly: four replies say "2 open invoices. One invoice is overdue by 7 days" plainly; turn 2 shows only the withheld sentence. | |
| owe-five-ways | Q2 | Yes: each card holds the amounts with their marks; no amount is in the prose, so "how much" is answered by the open block. | |
| owe-five-ways | Q3 | Not needed; none given. | |
| pronoun-follow-ups | Q1 | Yes: each reply repeats the customer's name, so the follow-up's subject is visible. | |
| pronoun-follow-ups | Q2 | Yes: "what about overdue ones?" gives the overdue invoice only. | |
| pronoun-follow-ups | Q3 | Not needed. | |
| switch-mid-thread | Q1 | Yes: "Harbour Demo Supplies has 1 open invoice." names the new customer. | |
| switch-mid-thread | Q2 | Yes. | |
| switch-mid-thread | Q3 | Yes: "Which customer would you like to look up?" is a clear question back. | |
| three-part-ask | Q1 | Partly: "Here is the overview… There is 1 overdue invoice." says nothing about the third part. | |
| three-part-ask | Q2 | Partly: all three blocks are on the one card, but the context block is collapsed and nothing in the prose points to it. | |
| three-part-ask | Q3 | Not needed. | |
| navigation | Q1 | Yes: "You can import a payment list from the Imports page." | |
| navigation | Q2 | Yes, if the steps block is read: "Follow these steps" relies on it; the prose never names the button. | |
| navigation | Q3 | Yes: one control to the page ("Add customer", "Import a CSV file", "Go to Customers"). | |
| add-customer | Q1 | Partly: "You can complete the creation process yourself." is vague; "does not owe anything" overstates a customer with no records. | |
| add-customer | Q2 | Yes: Create customer, then "what does it owe?" works on the new customer. | |
| add-customer | Q3 | Partly: the draft's button is clear, but the card also carries the manual steps, and on turn 2 an "Add customer" link beside it; the duplicate has no link to the existing customer. | |
| owner-case | Q1 | Yes: the question quotes the owner ("would consider a small extension") and names 21 days; staff's "Approved to Tue 10 Nov" is plain. | |
| owner-case | Q2 | Yes: one answer gave a suggestion the owner could take as it is. | |
| owner-case | Q3 | Yes for staff (nothing to do; the status says so). The owner's controls are the case page's, not judged here. | |
| beyond-limit | Q1 | Yes: "The suggested date is shorter than requested but within the allowed limit." | |
| beyond-limit | Q2 | Mostly: a second question ("will the event impact their ability to pay…") asks the owner to predict; it must be skipped before the suggestion appears. | |
| beyond-limit | Q3 | Yes: the suggestion names the date to use; the decision controls are the case page's, not judged here. | |
| staff-owner-context | Q1 | Yes, but "The owner has not provided any context for Bayside Café." is untrue, and staff could repeat it. | |
| staff-owner-context | Q2 | Yes: the overview is given; nothing is refused. | |
| staff-owner-context | Q3 | Not needed. | |
| unknown-customer | Q1 | No: "I have shown the overview for Harbour Demo Logistics instead." answers about a customer nobody asked about. | |
| unknown-customer | Q2 | No: the person must re-ask, and could mistake the card for Seaview's. | |
| unknown-customer | Q3 | No: no names to choose from, and no question back. | |
| vague-ask | Q1 | Yes: "Here is the current information for Bayside Café." with the overview; the follow-up's prose was withheld. | |
| vague-ask | Q2 | Yes: the vague ask got the overview without a second message. | |
| vague-ask | Q3 | Not needed. | |
| capabilities | Q1 | Yes: "You can ask about a customer's balance, invoices, or the status of their requests." | |
| capabilities | Q2 | Yes. | |
| capabilities | Q3 | Partly: no example question to type; the pages block lists where else to go. | |
| owner-recall | Q1 | Yes: the owner's words are given back; the prose is long (two sentences, 44 words). | |
| owner-recall | Q2 | Yes. | |
| owner-recall | Q3 | Not needed; "due on 2026-10-20" is in ISO form, while the blocks say "Tue 20 Oct 2026". | |

## Findings

Concrete defects seen in the live transcripts, most serious first.

1. **Wrong customer for a name the records do not hold** (unknown-customer #2, both runs).
   - What happened: with Logistics as the current customer, "What does Seaview owe?" called `findCustomers` (0 matches), then `customerOverview` with `"current"`. The reply was "I couldn't find a customer named Seaview. I have shown the overview for Harbour Demo Logistics instead."
   - The plan (§0.3) says such a question gets "which customer?" with up to five names. The mock follows that rule; nothing in code enforces it. `DeskTools.customer` accepts `"current"` even in a turn whose own search found no match.
   - The focus was not moved. The wrong overview was still shown, with the card's `about` set to Logistics.
2. **Correct replies withheld** (owe-five-ways #2 and vague-ask #2, both runs).
   - The model wrote the amount: "The amount owed is AUD 1,250.00." and "Bayside Café owes AUD 1,200.00 according to the records." Both equal the records.
   - The guard withholds any amount in prose, so the person saw "The agent's wording was withheld; the details below are from the records."
   - This is the rule working as designed: prose would drop the certainty mark, which is "stated" here. Its cost is that the two most direct "how much" wordings lose their answer sentence. That is 2 of the 11 turns per run that ask what a customer owes or their balance.
   - The prompt's "Never write an amount" is not followed for that wording.
3. **A multi-part ask answered in part in the prose** (three-part-ask #5).
   - "Here is the overview for Harbour Demo Logistics. There is 1 overdue invoice." The shared context is on the card (2 lines) but is collapsed and not mentioned.
   - Structurally the ask is answered in one card, as Review Focus 4 requires. In wording it is not.
4. **An untrue sentence to staff about the owner's context** (staff-owner-context #3 and #4).
   - "The owner has not provided any context for Bayside Café." / "No context has been provided by the owner." The owner had given context and kept it private.
   - No trace of it leaked, and nothing implies that more exists. The sentence is still false, and staff could repeat it to a customer. The mock's "There is no context for X" and the block's "Nothing on file." are accurate.
5. **"does not owe anything" for a customer with no records** (add-customer #4).
   - "Riverside Bakery does not owe anything. There are no open or overdue invoices recorded." The records hold no invoices, and completeness is not confirmed.
   - The second sentence is accurate; the first claims more than the records show. It has no number, so the guard passes it.
6. **Two controls for one action, and a vague sentence** (add-customer #1 and #2).
   - Turn 1: the draft card also shows the navigation block for "Add customer" (the manual steps). Turn 2: an "Add customer" link to Customers sits beside the Create customer button.
   - "You can complete the creation process yourself." does not say which control to press.
7. **A duplicate surfaced in words only** (add-customer #5).
   - "Harbour Demo Supplies already exists." There is no block and no link to the existing customer. `prepareCustomer` adds the target, but the model set no next step.
   - Review Focus 5's "surface the existing customer" is met in text only.
8. **"Between us," read as a line of its own** (three-part-ask #3).
   - The owner's "Between us, I think Harbour Demo Logistics may be sold next year." became two lines: relationship "Between us," and observation "I think…".
   - The owner would have to correct this before confirming. The check confirmed it as it was.
9. **ISO dates in prose** (owner-recall #4; vague-ask #1 in run 2).
   - "There is one open invoice due on 2026-10-20." The blocks write "Tue 20 Oct 2026". The format is inconsistent, though the date is right.
10. **A question that asks the owner to predict** (beyond-limit run 1; owner-case run 2).
    - "…will the event impact their ability to pay this invoice?" The suggestion waits until it is answered or skipped.

Not defects:

- The live model showed an empty "What the owner shared" block ("Nothing on file.") to staff in staff-owner-context #3. That is INFO, and the wording implies nothing.
- The navigation prose does not name the button; the open steps block does.

## Caveat

- These counts show that the desk behaves to the plan on 13 scripted conversations with fictional data, on one local model at temperature 0, run twice.
- They do not show that people understand it or finish tasks faster. The rubric's "Model reader (Opus)" column is one model reading transcripts. It is not a person using the page; it is not a usability test; and the reader also wrote the scenarios.
- The human column is empty until someone fills it in.
- The scenarios use the wording their author expected. Real wording will be wider. The mock passes the four live-only assertions only because the mock is not asked them.

## Re-run after fixes

- Date: 2026-10-20, the same day.
- Commits: `832979d` (desk agent), `a5f7ce0` (case block), `6a59776` (`layout_check --seed` guard) and `83a4392` (refusal names, ownerContext scope), on `5957a4f`.
- Same scenarios, data, model and settings as above. Prompt version is still `coordinator-v0.2` (Task 6 bumps it).
- Each live run went through the same kind of scratch logging proxy, so the raw text of a withheld reply could be read.

### What changed

- **Code:**
  - After `findCustomers` finds nobody in a run, `"current"` is refused for the rest of that run. The refusal names the closest customers and says to reply.
  - The reply guard checks each amount whole against the amounts the tools returned, in any of its forms. A total the model works out is still withheld.
  - For staff, a sentence saying the owner gave no context becomes "The owner has not shared anything about <customer> with staff." This does not apply when shared lines were shown.
  - `customerOverview` gives `invoiceCount` and `recordsExist`.
  - A prepared draft is the card's one control. A customer already in the records gets a link to that customer.
  - A short lead-in cut off at its comma ("Between us,") stays with the line it introduces.
  - A `whereIs` step no longer reads as a refusal to the prose guard.
- **Prompt:**
  - One clause per part of a multi-part question, with "The owner has shared: …" or "You have said: …" when the message asks about context.
  - `ownerContext` is called only when the message asks what was said, shared or known.
  - Dates are written as the blocks show them.
  - "Never write an amount" is kept.
- **Page:**
  - The request line reads "… on Tue 10 Nov 2026 instead of Tue 20 Oct 2026, an extension of 21 days."
  - The customer's message is quoted once, under the request line.
  - The owner's header no longer repeats the chip.
  - Up to three blocks are all open.
  - The reply is split into paragraphs on blank lines only.
- **Expectations added** to `conversations.json` (existing ones were extended; none was loosened):
  - three-part-ask #5: `textContains` "owner has shared".
  - add-customer #4: "no invoices are recorded", and lacks "owe anything" / "owes nothing". Both are live-optional.
  - staff-owner-context #3 and #4: "has not shared anything". On #4, `textLacks` also covers "not provided" and "no context"; that check counts on live.
  - unknown-customer #2: names "Harbour Demo Supplies" (live-optional).

### Results

- **Mock:** `RESULT conversation: 169/169`, 4 SKIP (live only), on `83a4392`.
- **Live:** 173 assertions per run, counted plus INFO.

| Run | Code | Result | INFO | Withheld replies | Note |
| --- | --- | --- | ---: | ---: | --- |
| 1 | `832979d` with a broader prompt (superseded) | `RESULT conversation: 165/165` | 8 | 7 | Told it could write amounts the tools gave, the model totalled them ("Harbour Demo Logistics owes AUD 2,580.00", withheld: 480 + 2,100 is no tool's figure). It also quoted the owner's shared note in every "owe" answer. The prompt was narrowed before the commit. |
| 2 | `832979d` | `RESULT conversation: 172/172` | 1 | 0 | The shared note still came with every staff "owe" answer. |
| 3 | `832979d` | `RESULT conversation: 170/170` | 3 | 0 | "What does Seaview owe?": refused `"current"`, the model searched four more times and hit the turn cap, so it showed "could not read that message". No wrong customer, but no question either. This led to `83a4392`. |
| 4 | `83a4392` (final) | `RESULT conversation: 172/172` | 1 | 1 | The one withheld reply was the model's own total again ("AUD 2,580.00"): correct to withhold. |

Each run took 202–238 s.

**The previously failing turns, run 4:**

- unknown-customer #2 (the 2 FAILs):
  - "Which customer do you mean? I found Bayside Café, Harbour Demo Supplies, and Harbour Demo Logistics."
  - No blocks, and the focus stayed on Logistics. Run 2 gave the same wording.
- owe-five-ways #2 (withheld before): "Harbour Demo Supplies owes AUD 1,250.00. They have 1 open invoice." Shown.
- vague-ask #2 (withheld before): "Bayside Café owes AUD 1,200.00. They have 1 open invoice." Shown.

### Status of the findings

| # | Finding | Status | Live, run 4 |
| --- | --- | --- | --- |
| 1 | Wrong customer after a miss | Fixed in code | Asks which, with names. Runs 2–4 never showed another customer's overview. Run 3 ended unreadable instead; fixed in `83a4392`. |
| 2 | Correct amounts withheld | Fixed in code | Correct amounts shown (two turns above); the model's own totals still withheld. |
| 3 | Multi-part ask answered in part | Fixed (prompt) | "Here is the overview for Harbour Demo Logistics. They have 1 overdue invoice. The owner has shared: "Harbour Demo Logistics are rebuilding their delivery fleet this quarter." and "Fictional relationship context: …"". Three blocks, all open. |
| 4 | Staff told the owner provided no context | Fixed in code | "The owner has not shared anything about Bayside Café with staff." (#3, #4 and vague-ask #1). |
| 5 | "Does not owe anything" with no records | Fixed (field and prompt) | "No invoices are recorded for Riverside Bakery." |
| 6 | Two controls on the draft card | Fixed in code | Draft block only, with Create customer. The sentence is still vague: "You can create this customer yourself." |
| 7 | Duplicate named in words only | Fixed in code | "Harbour Demo Supplies already exists." and a link, "Open Harbour Demo Supplies" (`#/customers/customer_demo_01`). |
| 8 | "Between us," as a line of its own | Fixed in code | One line: "Between us, I think Harbour Demo Logistics may be sold next year." The cause was the interpretation's two lines, not the page; the page never split the reply. |
| 9 | ISO dates in prose | Mostly fixed (prompt) | Answers say "due on Tue 20 Oct 2026". The owner's recall in beyond-limit #5 still copies a line's end as "(until 2026-11-30)". |
| 10 | A question asking the owner to predict | Not addressed | Not seen in runs 2–4 (one question each time, about "small extension"). |

### Still open

- Correct amounts now reach the prose without their certainty mark: "owes AUD 1,200.00" is a *stated* amount. The block beside it shows the mark. The prompt still says never to write an amount; the guard no longer punishes a correct one.
- The model still totals a customer's invoices when no total exists. The guard withholds that, and the person sees the withheld sentence above the blocks.
- staff-owner-context #3 still shows an empty "What the owner shared" block ("Nothing on file."), INFO as before.
- The caveat above applies unchanged: one local model at temperature 0, scripted wording, and a model reader. This is not a usability result.

## Re-run after fix wave 2

- Date: 2026-10-20, the same day.
- Commits: `b837dc6` (reply guard: claims, amount marks, counts), `e000009` (check scripts refuse anything but a scratch server) and `05ddb82` (a test race), on `d046f32`.
- Same scenarios, data, model and settings as above, on a fresh scratch server (port 8769) through the same kind of scratch logging proxy. Prompt version is still `coordinator-v0.2` (Task 6 bumps it).

### What changed

- **Claims:** the reply guard withholds a sentence saying the agent or the owner did or decided something ("I approved…", "I've granted…", "I have emailed…", "The owner approved…", "has been extended"). Only a case's multi-word status label ("Approved to Tue 10 Nov") is masked before the check, never a bare "Declined". The person sees "The agent's wording was withheld; the details below are from the records."
- **Amounts carry their mark:** each amount the desk tools return has a mark as the page words it (exact, stated as of a date, at most, as recorded, not recorded) and an `amountText`, for example "AUD 1,200.00 (stated as of Fri 16 Oct)". The overview's totals are "as recorded". An amount in the reply needs one of the marks its tool gave it within 60 characters after it; otherwise the wording is withheld. The prompt now says: if you write an amount, copy its `amountText`, mark included; never add up an amount.
- **Counts:** "three open invoices", "Five of their invoices", "3 of their invoices" and "18 open and overdue invoices" are checked against the count the tools gave, like "3 open invoices" was.
- **Prompt:** never say you did or decided anything; an action ends the turn and the card shows it.

### Results

- **Mock:** `RESULT conversation: 169/169`, 4 SKIP (live only). No mock template states an amount, so none needed a mark.
- **Live:** `RESULT conversation: 167/167`, 6 INFO (live wording, not counted), 215 s. 173 assertions, as before.

| Run | Code | Result | INFO | Withheld replies | Note |
| --- | --- | --- | ---: | ---: | --- |
| 5 | `05ddb82` | `RESULT conversation: 167/167` | 6 | 5 | Every amount the model wrote carried its mark. All 5 withheld replies were its own total for Logistics ("owes AUD 2,580.00 (stated)", 480 + 2,100; no tool gives that figure). |

**INFO lines:** owe-five-ways #1, #3 and #5 `withheld` (the Logistics total), owe-five-ways #1 `textContains` "Logistics" (the withheld sentence names nobody), staff-owner-context #3 `blocksAbsent` (the empty context block, as before), capabilities #1 `textContains` "owes" (it said "a customer's balance").

**Amounts as the live model now writes them:**

- "Bayside Café owes AUD 1,200.00 (as recorded, invoices less payments). There is 1 open invoice for AUD 1,200.00 (stated as of Fri 16 Oct) due on Tue 20 Oct 2026." Shown.
- "Harbour Demo Supplies owes AUD 1,250.00 (stated). There is 1 open invoice for AUD 1,250.00 (stated) due Tue 20 Oct 2026." Shown. Supplies' total and its one invoice are the same figure, so either mark passes.
- "Harbour Demo Logistics owes AUD 480.00 (stated) for an overdue invoice and AUD 2,100.00 (stated) for an open invoice." Shown (unknown-customer #1).
- "Harbour Demo Logistics owes AUD 2,580.00 (stated)." Withheld on 5 of the 6 Logistics "owe" turns (owe-five-ways #1, #3, #5, pronoun-follow-ups #1, switch-mid-thread #1).
- owner-case #6: "The status of the request for invoice DEMO-501 is Approved to Tue 10 Nov." Shown (the label's own words).
- add-customer #4: "Riverside Bakery owes AUD 0.00 (as recorded, invoices less payments). No invoices are recorded for them." Shown. It passes the assertions, but "owes AUD 0.00" is close to the "owes nothing" that finding 5 removed.

### Still open

- The model totals a customer's invoices more often now that the prompt lets it write amounts: 5 withheld replies in run 5, against 1 in run 4. The guard withholds each one, and the blocks below show the marked figures. A prompt line saying that no total exists when the overview gives none is untried.
- A customer with no invoices gets "owes AUD 0.00 (as recorded…)": true of the records, but the recordsExist rule in the prompt is meant to avoid it.
- When two amounts are the same figure with different marks (Supplies: the total "as recorded", the invoice "stated"), either mark passes beside it.
- The caveat above applies unchanged: one local model at temperature 0, scripted wording, and a model reader. This is not a usability result.

## Re-run with coordinator-v0.3

- Date: 2026-10-20, the same day.
- Commit: `b888db8` (Task 6 of the plan), on `dab9705`. The server reports prompt version `coordinator-v0.3` on every live turn.
- Same scenarios, data, model and settings as above: a fresh scratch server on port 8769 (`sampleData`, demo console, local `gemma-rp` at temperature 0, `reasoning_effort: none`), through the same kind of scratch logging proxy.

### What changed

- `customerOverview` now returns `balanceLine`, written by code from the figures the overview card shows, for the model to quote whole. For example: "Customer balance AUD 1,200.00 as recorded (invoices less payments; invoices not confirmed complete; payments not confirmed complete). Still owed per invoice: DEMO-501 AUD 1,200.00 (stated as of Fri 16 Oct)."
  - When an invoice has no total, so no balance is worked out (the sample's Logistics), the line says so and lists each invoice's amount with its mark: "No customer balance is worked out, because an invoice has no total recorded (…). Still owed per invoice: DEMO-201 AUD 480.00 (stated); DEMO-202 AUD 2,100.00 (stated)."
  - With no invoices it is "No invoices are recorded for <name>." and holds no amount.
  - A unit test checks that the line passes the reply guard whole, and that the model's own total beside it is still withheld.
- `DESK_SYSTEM`: never add, subtract or total amounts, even when no total is given; to say what a customer owes, quote `balanceLine` exactly or copy each invoice's `amountText` with its mark; a customer with no invoices has "no invoices recorded", never "owe AUD 0.00".
- The guard is unchanged.

### Results

- **Mock:** `RESULT conversation: 169/169`, 4 SKIP. `desk_check`: 60/60. Unit suite: 372 OK.
- **Live:** `RESULT conversation: 170/170`, 3 INFO, 205 s.

| Run | Code | Result | INFO | Withheld replies | Note |
| --- | --- | --- | ---: | ---: | --- |
| 6 | `b888db8` (`coordinator-v0.3`) | `RESULT conversation: 170/170` | 3 | 0 | No reply was withheld in the whole run. Every "owe" reply showed its sentence: **11 of 11 turns** that ask what a customer owes or its balance (run 5: 5 of the 6 Logistics turns withheld). |

**The "owe" turns, as shown:**

- Logistics, 6 turns (owe-five-ways #1, #3, #5, pronoun-follow-ups #1, switch-mid-thread #1, unknown-customer #1). Each listed the two invoices separately with their marks, and none totalled them. For example: "Harbour Demo Logistics owes AUD 480.00 (stated) for DEMO-201 and AUD 2,100.00 (stated) for DEMO-202. One invoice is overdue." On #1 and unknown-customer #1 the reply was "owes AUD 480.00 (stated) and AUD 2,100.00 (stated)", without the references.
- Supplies, 2 turns (owe-five-ways #2, #4): "Harbour Demo Supplies owes AUD 1,250.00 (stated). One invoice is open." The total and the one invoice are the same figure, so the invoice's mark passes beside the total, as before.
- Bayside, vague-ask #2 "what do they owe?": the model quoted `balanceLine` whole, then added "One open invoice is for AUD 1,200.00 (stated as of Fri 16 Oct) due on Tue 20 Oct 2026." in a second paragraph. This was the only turn that quoted the line whole.
- Riverside Bakery (no invoices), add-customer #4: "Riverside Bakery has no invoices recorded." Run 5 said "owes AUD 0.00 (as recorded…)". The `textContains` "no invoices are recorded" is INFO only because the word order differs.
- Seaview (not in the records), unknown-customer #2: "Which customer do you mean? I found Bayside Café, Harbour Demo Supplies, and Harbour Demo Logistics." No blocks.

**Other wording in this run:**

- three-part-ask #5 answered all three parts: "Here is the overview for Harbour Demo Logistics. They have one overdue invoice for AUD 480.00 (stated). The owner has shared: …" with both shared lines.
- staff-owner-context #4: "Bayside Café owes AUD 1,200.00 (as recorded, invoices less payments). There is 1 open invoice … The owner has not shared anything about Bayside Café with staff."
- The navigation replies now repeat the steps in the prose as well as in the block.
- The owner's recall in a case thread (beyond-limit #5) still writes ISO dates: "(2026-10-16, until 2026-11-30)". These dates are in the results, so the guard passes them; the prompt asks for "Tue 10 Nov 2026".
- owner-case and beyond-limit each asked 2 questions. The second asked the owner to weigh the event or the debt constraint ("how does that affect your view on this extension request?"). The suggestions were approve Tue 10 Nov 2026 (21 days, within "Up to 30 days") and approve Tue 3 Nov 2026 (14 days, shorter than the 21 asked, "shorter than requested but within the allowed limit").

**INFO lines:** add-customer #4 `textContains` (word order, above), staff-owner-context #3 `blocksAbsent` (the empty context block, as before), capabilities #1 `textContains` "owes" (it said "a customer's balance").

### Still open

- One run, one local model at temperature 0. The model listed invoices instead of totalling them on every Logistics turn of this run. That is not established for other wording, other customers or other models. When it does total them, the guard still withholds the reply.
- The model rarely quotes `balanceLine` whole (1 of 11). It mostly copies the per-invoice `amountText`, which the guard accepts.
- The same-figure ambiguity (Supplies) and the ISO dates in the owner's recall remain.
- The caveat above applies unchanged: scripted wording, and a model reader. This is not a usability result.

## Re-run with the situation, capabilities and prepared actions (slice 3)

- Date: 2026-10-21.
- Code: `3351fd2` (plan `docs/superpowers/plans/2026-10-21-situation-and-capabilities.md`, Tasks 1–4), with this task's check changes only; no product code changed. The server still reports prompt version `coordinator-v0.3` on every live turn. The desk prompt is the Tasks 1–4 text; Task 6 bumps the version.
- Same data, model and settings as above: a fresh scratch server on port 8769 (`sampleData`, demo console, local `gemma-rp` at temperature 0, `reasoning_effort: none`). Run 7 went direct to the model. A second, partial run (five scenarios) went through a scratch logging proxy, so the raw `reply` calls and tool results could be read.

### What changed

- **Ten new scenarios, 58 turns** (23 scenarios and 108 turns in all). Eight run in a case thread; two (`catering-draft`, `two-sentence-asks`) run in the general thread.
  - `explain-suggestion`: explain the stored suggestion, then ask again in other words.
  - `shorter-fit`: is the date asked within my limit, and could a shorter extension fit.
  - `case-recall`: what have I said about this case.
  - `approve-confirm`: "Let's give them two weeks.", then "approve 14 days, then", then Confirm decision.
  - `new-suggestion`: prepare 10 days, then ask for a recommendation, so the preparation is withdrawn; then ask again in other words.
  - `staff-next-step`: staff enter two Logistics requests and ask what to do next.
  - `tool-off`: prepareDecision turned off under Setup, then two asks to prepare.
  - `catering-draft`: a new client named in passing; the draft chip; "what do they owe?"; then Create customer.
  - `two-sentence-asks`: three asks made of a remark and a question.
  - `demo-202-review`: the owner's messages in the team review's DEMO-202 thread, verbatim: "Why is the suggestion 14 days?", "what did I say for this case", "could we do 10 days instead?".
  - Each scenario has at least one wording the mock's keyword rules do not read. Its wording assertions are `liveOnly`: SKIP on the mock, counted live.
- **New `do` steps** in `deploy/conversation_check.js`:
  - `wait`: until every case is prepared.
  - `tool`: the owner's Setup → Agent tools switch, `POST api/agent-tools {tool, enabled}`.
  - `confirmPrepared`: what the Confirm decision button sends: `POST api/requests/<id>/decisions` with the prepared values and `preparedVersion`.
  - Before each scenario the runner turns back on any tool that differs from the registry's default, because the demo reset keeps settings.
- **New assertions:**
  - `detail`: the card's detail.
  - `focusKind`: the thread focus's kind. A records link (`customerId`) must be present exactly when the kind is `customer`.
  - `prepared`: `{outcome, days, date}` from the card's prepared block or the case's preparation; `false` for none.
  - `confirmButton`: whether the case block would draw Confirm decision, which it does while `situation.case.preparedDecision` exists.
  - `actions`: `{id: allowed}`, checked on every step with that id; `null` for no such step.
- **Extended assertions:**
  - `suggestion` also reads a say turn's situation, and takes `newer`: a version after the one last seen.
  - `decided` takes `{outcome, date}`.
- The Markdown transcript now records each card's detail, the reason a reply was withheld, and the prepared block.
- A negative probe on a scratch copy flipped every new expectation. Each one failed, except on the three `liveOnly` turns where the mock does the opposite (it prepares nothing for "Let's give them two weeks."; it sets the unknown focus "Lighthouse").

Commands (scratch paths outside the repository; the proxy run used a copy of the runner with five scenarios):

```
deploy/ui_check_server.py <scratch>/m1.sqlite3 18871
node deploy/conversation_check.js http://127.0.0.1:18871 <scratch>/m1.log <scratch>/mock2
~/srv/nucleon/runtime/python-3.12.14/bin/python3 prototype/server.py --config <scratch>/live-config.json   # config.example.json with a scratch db, port 8769, sampleData, demo console
node deploy/conversation_check.js http://127.0.0.1:8769 <scratch>/live.log <scratch>/live1 --live
```

### Results

- **Mock:** `RESULT conversation: 310/310`, 17 SKIP (live only). The 13 earlier scenarios are unchanged at 169/169, with 4 SKIP.
- **Live:** `RESULT conversation: 307/317`, 10 INFO, 626 s for 108 turns.
  - The earlier 13 scenarios gave 164/171 (run 6: 170/170).
  - The new 10 gave 143/146.
- **Proxy run** (five scenarios, same code): `63/69`. It reproduced the same FAILs and the withheld `202`.

| Run | Code | Result | INFO | Withheld replies | Model failures | Note |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 7 | `3351fd2` (`coordinator-v0.3`) | `RESULT conversation: 307/317` | 10 | 3, plus 1 recovered on the retry | 2 | Prepared decisions, the tool switch, new suggestions and the case-line recall worked. The 10 FAILs are the detail of short answers (3), case-thread status answers with no subject or block (2), a tool loop (3), and two block or next-step choices (2). |

| Scenario | PASS | FAIL | INFO | What happened |
| --- | ---: | ---: | ---: | --- |
| owe-five-ways | 23 | 0 | 0 | As run 6. |
| pronoun-follow-ups | 17 | 1 | 0 | #4 "do they have any open requests?" was answered right ("There are no open requests for Harbour Demo Logistics.") from the overview, so it showed an overview block, not a requests block. |
| switch-mid-thread | 15 | 0 | 0 | |
| three-part-ask | 10 | 0 | 0 | |
| navigation | 14 | 1 | 0 | #3 "How do I record a payment?" gave the steps with no next step (no link to Customers). |
| add-customer | 20 | 0 | 0 | |
| owner-case | 12 | 2 | 0 | #6 staff "what's the status of this request now?" in the case thread: caseDetails, then "The request for invoice DEMO-501 is completed." The card had no subject and no block. |
| beyond-limit | 11 | 0 | 0 | |
| staff-owner-context | 9 | 3 | 2 | #4 "Give me an overview of Bayside Café, including what the owner said." reached the 8-call cap: "The agent could not read that message. Try again, or use the records." |
| unknown-customer | 8 | 0 | 0 | |
| vague-ask | 9 | 0 | 0 | |
| capabilities | 5 | 0 | 0 | |
| owner-recall | 11 | 0 | 0 | |
| explain-suggestion | 14 | 0 | 2 | Explained, citing the owner's limit. The date was written "Tue 03 Nov 2026"; the detail was full. |
| shorter-fit | 13 | 0 | 1 | "They asked for 21 days, but you specified up to 14 days, no more." No day count of its own. |
| case-recall | 14 | 0 | 0 | Both wordings cite "Up to 14 days this time" as about this case. |
| approve-confirm | 17 | 0 | 0 | Both wordings prepared approve to 2026-11-03 (14 days); Confirm committed exactly that, and the button went. |
| new-suggestion | 15 | 0 | 1 | 10 days was prepared (2026-10-30); the reply was withheld (date). Both later wordings formed a newer suggestion version, and the preparation was withdrawn. |
| staff-next-step | 10 | 0 | 2 | Two waiting steps and no allowed "enter a request". The first reply was withheld (`202`, a guard false positive); the second said to wait for the owner. |
| tool-off | 16 | 0 | 0 | Nothing was prepared and no Confirm was drawn; the step read "not now". The first reply echoed the owner's words. |
| catering-draft | 18 | 0 | 1 | Draft from the casual wording; the chip kind was draft, with no records link. "what do they owe?" reached the 6-turn cap. |
| two-sentence-asks | 10 | 3 | 1 | All three had detail full (the model sends "full"); #2 was withheld (a wrong weekday). |
| demo-202-review | 16 | 0 | 0 | All three of the review's messages answered from the case; "could we do 10 days instead?" was prepared as 10 days. |

**INFO lines:**

- staff-owner-context #3 `blocksAbsent`: the empty context block, as before.
- staff-owner-context #4 `textContains`: the model failure.
- explain-suggestion #5 `textContains` and shorter-fit #6 `textContains`: "Tue 03 Nov 2026" written for "Tue 3 Nov 2026".
- explain-suggestion #5 `detail`: full.
- new-suggestion #5 `withheld`: date.
- staff-next-step #4 `withheld` and `textContains`: the `202` false positive.
- catering-draft #3 `textContains`: the model failure.
- two-sentence-asks #2 `withheld`: date.

**Withheld replies** (the card shows "Here is what the records show about <name>." with the blocks):

- new-suggestion #5 "approve 10 days, then": "It stated a date the records do not show." The raw text was not captured in run 7. In the proxy run the same turn passed with "I have prepared the decision to approve for 10 days. The date is Fri 30 Oct 2026. This is within your limit of up to 14 days, though it is less than the 21 days asked. Nothing is decided until you press "Confirm decision"."
- staff-next-step #4 "what should I do next?": "It stated a number the records do not show: 202." The raw text, seen through the proxy and the same on the retry, was "You can wait for the owner's decision on invoice DEMO-202 or invoice DEMO-201. You can also add an invoice for Harbour Demo Logistics or record a payment or credit for them."
- two-sentence-asks #2 "I'm on the phone with Logistics. Are they behind on anything?": "It stated a date the records do not show." The raw text, the same on the retry, was "…AUD 2,100.00 (stated) for DEMO-202 due Thu 06 Nov 2026." 2026-11-06 is a Friday.
- Recovered on the retry: shorter-fit #6. The shown reply is the retry's.

**Model failures:**

- staff-owner-context #4: the tool-call cap of 8. The calls were customerOverview and ownerContext with customerId "C-0003" (the display code from the focus line), refused; both again with "current"; then ownerContext four more times after it returned no lines, once with requestId "current" in the general thread.
- catering-draft #3: the 6-turn cap. With the draft focus, customerOverview("current") is refused with "No customer matched; ask which customer the person means… Call reply now." The model then repeats prepareCustomer, customerOverview and findCustomers.

### Live transcript (run 7, new scenarios)

Replies verbatim; the setup turns (the owner's context, its confirmation, staff's request) are condensed after the first scenario.

#### explain-suggestion

1. **Owner:** Bayside Café has had a slow winter, but they expect a busy summer. I might allow a little more time, though I don't want the balance to grow.
   - **Nucleon:** What I understood (Bayside Café): observation "Bayside Café has had a slow winter"; expectation "they expect a busy summer"; guidance "I might allow a little more time"; constraint "I don't want the balance to grow"; 7 s
2. *Owner confirm*
3. **Staff:** Hi, Bayside Café here. Could we pay invoice DEMO-501 on 2026-11-10 instead?
   - **Nucleon:** I opened a case for this request in its own thread.; tools findCustomers, openRequest
4. *Owner answer: "Up to 14 days this time"*
   - Agent's question: "Regarding your comment that you 'might allow a little more time', does the 21 day extension requested for Bayside Café fall within that range?" (answered)
   - Agent's question: "You mentioned 'I don't want the balance to grow'; what is the maximum outstanding amount you are comfortable with for this account?" (skipped)
   - Suggestion: approve 2026-11-03: "The suggested date is shorter than requested but stays within the allowed limit."
5. **Owner (case thread):** Can you explain the suggestion?
   - **Nucleon:** The suggested date is shorter than requested but stays within the allowed limit. It cites "Up to 14 days this time".
   - detail full; tools caseDetails; 5 s
6. **Owner (case thread):** Why does it come out shorter than what Bayside asked for?
   - **Nucleon:** The suggestion is shorter because the requested extension of 21 days exceeds your limit of "Up to 14 days this time". The suggested date of Tue 03 Nov 2026 is the latest date within that allowed limit.
   - detail full; tools caseDetails; 5 s

#### shorter-fit

Setup: "Bayside Café is a long-standing customer and I would consider giving them a bit more time. I don't want them to fall further behind, though." (relationship, guidance, constraint), confirmed. Staff: "Message from Bayside Café: can DEMO-501 move to 2026-11-10? Cash is tight until their event." The owner answered "Up to 14 days, no more". Suggestion: approve 2026-11-03, "The suggestion is based on the guidance to allow a limited extension, though the proposed date exceeds the maximum duration specified."

5. **Owner (case thread):** Is what they asked for within my limit?
   - **Nucleon:** No, what they asked for is not within your limit. They asked for 21 days, but you specified up to 14 days, no more.
   - Next step: Decide the request for invoice DEMO-501; detail none; tools caseDetails; 9 s
6. **Owner (case thread):** Could a shorter extension fit? Explain how it compares with what I allowed.
   - **Nucleon:** The suggestion is to approve until Tue 03 Nov 2026. This date is the latest within your limit of "Up to 14 days, no more". The customer's request for Tue 10 Nov 2026 (an extension of 21 days) exceeds this limit.
   - Shown on the retry (the first reply was withheld); detail full; tools caseDetails, reply; 10 s

#### case-recall

Setup: the six-line Bayside context of the earlier scenarios, confirmed. Staff: "Bayside Café emailed: we'd like to settle invoice DEMO-501 on 2026-11-10 rather than on the due date." The owner answered "Up to 14 days this time". Suggestion: approve 2026-11-03.

5. **Owner (case thread):** what have I said about this case?
   - **Nucleon:** You have said: "Up to 14 days this time" regarding this case.
   - *Shown:* context of Bayside Café, 7 lines, **twice** (the same block from caseDetails and from ownerContext); detail full; 8 s
6. **Owner (case thread):** What were my exact words on this request?
   - **Nucleon:** You have said: "Up to 14 days this time" regarding this case.
   - detail full; tools caseDetails; 4 s

#### approve-confirm

Setup: "Bayside Café always pays eventually. I would consider a short extension for them, but I do not want the debt to keep growing." (observation "Bayside Café always pays eventually.", guidance, constraint), confirmed. Staff: "Hello, it's Bayside Café. Is it OK if we pay DEMO-501 on 2026-11-10?" The owner answered "Up to 14 days this time". Suggestion: approve 2026-11-03.

5. **Owner (case thread):** Let's give them two weeks.
   - **Nucleon:** I have prepared that decision for you. The date is Tue 03 Nov 2026, which is within the limit. Nothing is decided until you press "Confirm decision".
   - *Shown:* prepared decision v1 on DEMO-501: approve to 2026-11-03, 14 days after 2026-10-20, asked 2026-11-10, Confirm decision; detail none; tools prepareDecision; 5 s
6. **Owner (case thread):** approve 14 days, then
   - **Nucleon:** I have prepared that decision for you. The date is Tue 03 Nov 2026, which is within the limit. Nothing is decided until you press "Confirm decision".
   - *Shown:* prepared decision v2, the same values; 4 s
7. *Owner presses Confirm decision*
   - Decision: approve 2026-11-03; the case block draws no Confirm decision.

#### new-suggestion

Setup: "Bayside Café had a quiet month. I might give them extra time if they ask, but I don't want what they owe to go up.", confirmed. Staff: "Bayside Café on the phone: could DEMO-501 be paid on 2026-11-10 instead?" Agent's question: "Regarding your comment that "I don't want what they owe to go up", should we waive any potential late fees for this 21-day extension?" The owner answered "Up to 14 days for this one". Suggestion: approve 2026-11-03.

5. **Owner (case thread):** approve 10 days, then
   - **Nucleon:** Here is what the records show about Bayside Café. *(withheld: It stated a date the records do not show.)*
   - *Shown:* prepared decision v1 on DEMO-501: approve to 2026-10-30, 10 days after 2026-10-20; Confirm decision; 8 s
6. **Owner (case thread):** What would you recommend now?
   - **Nucleon:** The suggested date is shorter than requested but stays within the allowed limit. It cites "Up to 14 days for this one".
   - A newer suggestion version; the preparation is withdrawn, so no Confirm decision is drawn; tools requestSuggestion; 7 s
7. **Owner (case thread):** Could you have another look at this case and propose a date?
   - **Nucleon:** The suggested date is Tue 03 Nov 2026. It is shorter than requested but stays within the allowed limit. It cites "Up to 14 days for this one".
   - A newer suggestion version; tools requestSuggestion; 6 s

#### staff-next-step

1. **Staff:** Hi, it's Harbour Demo Logistics. Could we pay invoice DEMO-201 on 2026-10-30 instead?
   - **Nucleon:** I opened a case for this request in its own thread.
2. **Staff:** Harbour Demo Logistics again: could DEMO-202 be paid on 2026-11-20 instead?
   - **Nucleon:** I opened a case for this request in its own thread.
3. *Wait: both cases with the owner*
4. **Staff (DEMO-202 case thread):** what should I do next?
   - **Nucleon:** Here is what the records show about Harbour Demo Logistics. *(withheld: It stated a number the records do not show: 202.)*
   - Steps in the situation: wait_for_owner ×2 (allowed), open_request ×2 (not now: a request is already open), add_invoice, record_payment; 7 s
5. **Staff (case thread):** Is there anything I need to do on this one?
   - **Nucleon:** You can wait for the owner's decision on invoice DEMO-202. The status is With the owner.
   - tools caseDetails; 4 s

#### tool-off

Setup: "Bayside Café has been a good customer for years. I would consider a modest extension for them.", confirmed. Staff: "Bayside Café asks: may we pay DEMO-501 on 2026-11-10?" The owner answered "Up to 14 days this time". Suggestion: approve 2026-11-03.

5. *Owner turns prepareDecision off*: the situation's step "Tell me your decision to prepare it…" reads not now ("turned off under Setup → Agent tools"); decide stays allowed.
6. **Owner (case thread):** approve 14 days, then
   - **Nucleon:** approve 14 days, then
   - Next step: Decide the request for invoice DEMO-501; nothing prepared; no Confirm decision; tools caseDetails; 8 s
7. **Owner (case thread):** Can you prepare the decision for 14 days so I can confirm it?
   - **Nucleon:** I cannot prepare the decision as that feature is currently turned off under Setup. You can decide the request for invoice DEMO-501 directly in the case.
   - Next step: Decide the request for invoice DEMO-501; nothing prepared; 5 s

#### catering-draft

1. **Staff:** We've got a new client called Lighthouse Catering. Can you set them up?
   - **Nucleon:** I have prepared a draft for Lighthouse Catering.
   - *Shown:* draft Lighthouse Catering (Create customer); focus: draft, no records link; 4 s
2. **Staff:** add Lighthouse Catering as a customer
   - **Nucleon:** I have prepared a draft for Lighthouse Catering.
3. **Staff:** what do they owe?
   - **Nucleon:** The agent could not read that message. Try again, or use the records.
   - tools findCustomers, prepareCustomer, customerOverview, prepareCustomer, customerOverview, findCustomers; the 6-turn cap; focus still the draft
4. *Staff create the customer*: focus Lighthouse Catering, a customer with its records link.

#### two-sentence-asks

1. **Staff:** Quick one about Supplies. Do they owe us anything right now?
   - **Nucleon:** Harbour Demo Supplies still owes AUD 1,250.00 (stated). They have one open invoice for DEMO-1,250.00 (stated).
   - *Shown:* overview of Harbour Demo Supplies; **detail full**; 3 s
2. **Staff:** I'm on the phone with Logistics. Are they behind on anything?
   - **Nucleon:** Here is what the records show about Harbour Demo Logistics. *(withheld: It stated a date the records do not show.)*
   - *Shown:* overview of Harbour Demo Logistics; detail full; 7 s
3. **Owner:** Bayside called this morning. When is their invoice due?
   - **Nucleon:** The invoice DEMO-501 is due on Tue 20 Oct 2026.
   - *Shown:* all invoices of Bayside Café; **detail full**; 8 s

#### demo-202-review

Setup: "Harbour Demo Logistics pay late sometimes, but I would consider a short extension for them.", confirmed. Staff: "Logistics here: could invoice DEMO-202 be paid on 2026-11-27 instead?" The owner answered "Up to 14 days this time". Suggestion: approve 2026-11-20, "The suggestion is based on the willingness to consider a brief extension, though the proposed date exceeds the requested limit."

5. **Owner (case thread):** Why is the suggestion 14 days?
   - **Nucleon:** The suggestion is based on your guidance "Up to 14 days this time". It proposes an extension to Fri 20 Nov 2026, which is the latest date within that limit.
   - detail full; tools caseDetails; 6 s
6. **Owner (case thread):** what did I say for this case
   - **Nucleon:** You have said: - "Up to 14 days this time" (guidance) on Fri 16 Oct 2026 - "I would consider a short extension for them" (guidance) on Fri 16 Oct 2026 Regarding the case, you also said: - "Up to 14 days this time" (guidance) on Fri 16 Oct 2026
   - *Shown:* context of Harbour Demo Logistics, 4 lines; tools ownerContext ×3; 6 s
7. **Owner (case thread):** could we do 10 days instead?
   - **Nucleon:** I have prepared an approval for 10 days. This results in a due date of Mon 16 Nov 2026, which is within your limit of 14 days. Nothing is decided until you press "Confirm decision".
   - *Shown:* prepared decision v1 on DEMO-202: approve to 2026-11-16, 10 days after 2026-11-06, asked 2026-11-27; Next step "Confirm decision" to the case; 6 s

### Rubric (live run 7, new scenarios)

The three questions are those of live run 1. The model reader (Claude Opus, the agent that wrote these checks) judged from the transcript text and the blocks listed, not from the rendered page. The human column is left empty.

| Scenario | Q | Model reader (Opus) | Human reader |
| --- | --- | --- | --- |
| explain-suggestion | Q1 | Partly: the first reply names neither the date nor the 21 days ("shorter than requested … It cites …"); the second does both. | |
| explain-suggestion | Q2 | Yes, after the second ask: the limit, the days asked and the latest date are in one reply. | |
| explain-suggestion | Q3 | Not needed. | |
| shorter-fit | Q1 | Yes: "No, … They asked for 21 days, but you specified up to 14 days, no more." | |
| shorter-fit | Q2 | Yes: the second reply names Tue 03 Nov 2026 as the latest date within the limit. The case's own suggestion sentence ("…the proposed date exceeds the maximum duration specified") contradicts it. | |
| shorter-fit | Q3 | Yes: one Decide link. | |
| case-recall | Q1 | Yes: the case line, in quotes, as about this case. | |
| case-recall | Q2 | Partly: the prose gives only the case line; the customer lines are in the block, which is shown twice. | |
| case-recall | Q3 | Not needed. | |
| approve-confirm | Q1 | Yes: the date, "within the limit", and "Nothing is decided until you press Confirm decision". | |
| approve-confirm | Q2 | Yes: one message and one button; the casual "two weeks" worked too. | |
| approve-confirm | Q3 | Yes: the Confirm decision button. "I have prepared that decision for you" is accurate. | |
| new-suggestion | Q1 | Partly: the prepared 10 days shows only the withheld sentence above its block; the recommendation reply leaves out the date the first time. | |
| new-suggestion | Q2 | Partly: nothing says the earlier preparation is gone; only the missing button shows it. | |
| new-suggestion | Q3 | No next step after the new suggestion: neither "prepare again" nor Decide. | |
| staff-next-step | Q1 | No for the first ask (withheld; the blocks are not about steps); yes for the second ("You can wait for the owner's decision on invoice DEMO-202."). | |
| staff-next-step | Q2 | Partly: the second reply leaves out the other waiting case (DEMO-201). The withheld first reply had named it. | |
| staff-next-step | Q3 | Yes: wait. Nothing tells staff to enter a request. | |
| tool-off | Q1 | No for the first ask: the reply repeats the owner's words. Yes for the second: "turned off under Setup". | |
| tool-off | Q2 | Yes: the Decide link is the way to decide. | |
| tool-off | Q3 | Yes: Decide the request for invoice DEMO-501. | |
| catering-draft | Q1 | Yes: "I have prepared a draft…" with the Create customer button; the input says "(not yet a customer)". | |
| catering-draft | Q2 | No for "what do they owe?": a failure message instead of "Lighthouse Catering is not a customer yet". | |
| catering-draft | Q3 | Yes: Create customer. | |
| two-sentence-asks | Q1 | Partly: #1 garbles the reference ("one open invoice for DEMO-1,250.00"); #2 is withheld; #3 is plain. | |
| two-sentence-asks | Q2 | Yes, but every block is open (detail full) under one-line answers. | |
| two-sentence-asks | Q3 | Not needed. | |
| demo-202-review | Q1 | Yes for "Why is the suggestion 14 days?" (the owner's own line and the date); partly for the recall, which lists the case line twice. | |
| demo-202-review | Q2 | Yes: "could we do 10 days instead?" was prepared with its date, within the limit, ready to confirm. | |
| demo-202-review | Q3 | Yes: Confirm decision. | |

### Findings

1. **Short answers are shown in full.** The model sends `detail: "full"` on most answers: 31 of the 51 answer cards not withheld, including all three two-sentence asks. The proxy showed `"detail": "full"` in the model's own reply call, not a missing field. The prompt line ("none" for a short answer unless asked for a list) is not followed. This is the 3 FAILs of two-sentence-asks.
2. **caseDetails gives the card no subject and no block.** In a case thread the model now answers with caseDetails, so the card names nobody and shows nothing. Examples: staff's status question (owner-case #6, 2 FAILs) and every case-thread explanation here ("About: nobody"). That status reply said "is completed", not the label "Approved to Tue 10 Nov".
3. **A tool loop when staff ask for the owner's words** (staff-owner-context #4, 3 FAILs; it passed in run 6):
   - the model passed the focus line's display code "C-0003" as a customerId;
   - after ownerContext returned no lines, it called it again, once with requestId "current" in the general thread, until the 8-call cap.
4. **A tool loop on a draft focus** (catering-draft #3): the refusal of "current" says "No customer matched…", not that the subject is a draft not yet a customer. The model repeats prepareCustomer and customerOverview until the 6-turn cap.
5. **A guard false positive on references.** `COUNTED` reads "invoice DEMO-202 or invoice DEMO-201" as a count of 202 invoices ("202 or invoice"), so the reply is withheld. Its `\b(\d+)` matches the digits after "DEMO-". This is staff-next-step #4, and the retry withholds it again.
6. **Weekdays the model works out.**
   - "DEMO-202 due Thu 06 Nov 2026" (it is a Friday) was withheld. That is correct guard behaviour; the due date reaches the model only in ISO form.
   - The model writes "Tue 03 Nov 2026" where the page writes "Tue 3 Nov 2026".
7. **The guard withholds the owner's own words about payment.** This was found on the mock while writing the scenarios. With the owner's line "they have always paid in the end", the explanation quoting the suggestion's cites was withheld: "it describes payment history, reliability or risk"; `CREDIT_JUDGEMENT` matches "always paid". Live, the interpretation kept "Bayside Café always pays eventually." as a line (approve-confirm #1), which the agent could not quote either. The scenario was reworded ("they expect a busy summer").
8. **Suggestion sentences that contradict the comparison.** Two sentences for dates within the limit:
   - "…though the proposed date exceeds the maximum duration specified." (shorter-fit)
   - "…though the proposed date exceeds the requested limit." (demo-202)

   In the proxy run the desk reply to "What would you recommend now?" said "The proposed date is longer than the allowed limit." about Tue 3 Nov. Neither the suggestion step nor the reply guard checks meaning.
9. **With prepareDecision off, the first reply repeated the owner's words** ("approve 14 days, then"). It did give a Decide link. Asked again, it said correctly that preparing is turned off under Setup. Nothing was prepared either time.
10. **The same context block twice** (case-recall #5): the caseDetails block and the ownerContext block are the same block, and code merges only invoices.
11. **Block and link choices.**
    - "do they have any open requests?" was answered right from the overview, so the requests block expected was not shown.
    - "How do I record a payment?" got the steps but no link (not traced through the proxy).
12. **Other wording.**
    - "one open invoice for DEMO-1,250.00 (stated)" garbles a reference into an amount; the guard passes it.
    - The needs step asked "should we waive any potential late fees…?" (there are no fees in Nucleon) and "what is the maximum outstanding amount you are comfortable with…?".

**What worked:**

- All four ways the owner gave a decision in words were handled as designed: "Let's give them two weeks.", "approve 14 days, then" and "approve 10 days, then" were prepared with the date worked out by code, and "could we do 10 days instead?" was prepared as 10 days to Mon 16 Nov 2026. Confirm decision committed exactly the prepared values.
- The tool switch held: nothing was prepared, no Confirm was drawn, and the step was marked not allowed with the reason.
- Both new-suggestion wordings formed a newer version and withdrew the preparation.
- Every recall turn (4) cited "Up to 14 days this time".
- The comparison was quoted (21 days asked, up to 14 allowed), and no reply computed a day count of its own.

### Still open

- Findings 1–6 and 8–9 are for the fix wave: Task 6, or the wave after it. No product code was changed here.
- The new scenarios were run once live, plus a five-scenario proxy run; one local model at temperature 0. The proxy run differed in wording on two turns (new-suggestion #5 and #6), so these replies are not stable across runs.
- The caveat above applies unchanged: scripted wording, and a model reader. This is not a usability result.

### Re-run after the fix wave

- Date: 2026-10-21, the same day.
- Commits: `f83ddfc` (round 1), `6ca8d69` (round 2), `80d164f` (round 3) and `50233e5` (round 4), on `ccb8b50`. Up to round 3 the server reported `coordinator-v0.3`; the version is `coordinator-v0.4` from the records commit `25e3e59`, so round 4 ran with it in the code ([PROMPTS.md](../../PROMPTS.md), "coordinator-v0.4").
- Same scenarios, data, model and settings as above, each run on a fresh scratch server. Run 7 above stays as it was recorded.

**What changed** (product code unless marked):

- A `detail` of `full` on a reply of at most two sentences that carries a figure is shown as `summary`; a lead-in without a figure ("Here are their invoices.") stays `full`. Round 1's rule (at most two sentences and no invoices block) was replaced in round 2. Round 4: a last sentence ending in ":" is not counted, so a lead-in added to a short answer ("Here are their invoices:") does not keep it open, and the prompt's `detail` line and the reply tool's description no longer mention a lead-in.
- After `caseDetails`, the card is about the case's customer when no other customer was identified; not after asking which of several (round 3).
- A customer's code ("C-0003") and a case's invoice reference are taken as ids.
- A call made again with the same arguments in a turn is answered "already answered", not run and not counted toward the 8 calls; after a preparation succeeds, the reads may run again (round 3).
- `"current"` with a draft or a name not found says which, and to reply now.
- Digits after a letter and a hyphen ("DEMO-202") start no count; a range ("2-3 overdue invoices") is still one (round 3).
- A step number in a list ("1. ", "2) " at the start of the text or of a line, or after a sentence's end) is not a figure; a list after a colon still is (round 4).
- The owner's line quoted word for word is not read as a payment judgement; unquoted, cut, paraphrased or beside a judgement it still is.
- The prompt says to copy every date as a result writes it. `caseDetails`, `ownerContext`, `cases` and `prepareDecision` give each real ISO date in the page's words too (round 2; a string shaped like a date that is no date gets none, round 3).
- A suggestion sentence saying the date is beyond (or within) the day limit is withheld only when code's comparison makes that false for both the suggested and the asked date, and the suggestion step asks again once with the reason (round 2).
- The same context block is shown once.
- A search for the draft's own name that finds nobody keeps the draft focus, by whole words (rounds 2 and 3).
- Round 1 gave staff's empty `ownerContext` a message ("… Reply now; there is nothing more to fetch."); round 2 removed it, because the model then answered without fetching the overview (vague-ask #1).
- Scenarios (checks only): owner-case #6 accepts no customer block or the cases block, and gains a live-only `textContains` "Approved"; pronoun-follow-ups #4 accepts the cases or the overview block; two-sentence-asks accept `none` or `summary`. The `blocks` and `detail` assertions take alternatives. Round 4: when the needs step asked no question, the `answer` step says the text in the case thread and confirms it as guidance, then forms the suggestion again, so the case gets the owner's limit; a failed suggestion's reasons are printed.

**Results:**

| Round | Code | Unit suite | `desk_check` | Mock | Live | INFO | Withheld replies | Model failures | Time |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `f83ddfc` | 422 | 73/73 | 310/310, 17 SKIP | `RESULT conversation: 314/320` | 7 | 1, plus 1 recovered on the retry | 0 | 625 s |
| 2 | `6ca8d69` | 425 | 73/73 | 310/310, 17 SKIP | `RESULT conversation: 323/323` | 4 | 0 | 0 | 603 s |
| 3 | `80d164f` | 427 | 73/73 | 310/310, 18 SKIP | `RESULT conversation: 312/318` (the controller's re-run) | 10 | navigation #1 and #2; any others not measured | not measured | 621 s |
| 4 | `50233e5` | 428 | 73/73 | 310/310, 18 SKIP | **`RESULT conversation: 325/325`** | 3 | 0 (no retry) | 0 | 601 s |

- Round 1: the 13 earlier scenarios 170/171, the 10 new 144/149. Its 6 FAILs: two-sentence-asks #1–#3 `detail` (the scenario expected `none`), shorter-fit #4 (a suggestion withheld for its claim, with no retry then), catering-draft #3 `focusKind` (a search for the draft's name made it "not found") and vague-ask #1 (the empty-context message above).
- Round 2: the 13 earlier scenarios 172/172 with 1 INFO, the 10 new 151/151 with 3 INFO. No reply withheld and no retry. Detail on the 56 answer cards: none 30, summary 20, full 6 (run 7: 31 of 51 full).
- Round 2's INFO lines: staff-owner-context #3 `blocksAbsent` (the empty context block, as before); explain-suggestion #5 `textContains` and `detail` (no date in the reply; summary); catering-draft #3 `textContains` "not yet".
- Round 3 changed the guard's count pattern, `dated()`, the card's subject after `caseDetails`, the draft-name rule and one scenario. The controller ran it live: 312/318, 10 INFO, 621 s. The failing turns, as recorded:
  - navigation #1 and #2: withheld, because the numbered steps "1. 2. 3." were read as figures;
  - two-sentence-asks #1–#3: `full`, because the model appended "Here are their invoices:" to keep the lead-in exception;
  - new-suggestion #4 and #7: a 21-day suggestion, because the needs step asked no question, so the runner recorded no limit (a gap in the runner, not the product);
  - owner-case #4: the suggestion failed, `cite: not loaded`, because the model dropped the last character of a loaded line id (a model error; no code change), and owner-case #5's decision after it.
- Round 4: 325/325, 3 INFO, 601 s. No reply withheld, no retry, no model failure, and no suggestion failed or needed the claim retry. Every failing turn of round 3 passed. Detail on the 56 answer cards: none 32, summary 21, full 3. Its INFO lines: staff-owner-context #3 `blocksAbsent`; explain-suggestion #5 `textContains` "Tue 3 Nov 2026" (the sentence and the cite, not the date); catering-draft #3 `textContains` "not yet".
- Not exercised in round 4: the step-number rule (the model did not number its steps), the runner's no-question path (the needs step asked a question) and the suggestion's claim retry.

**Status of run 7's findings:** 1 (short answers in full): code shows them as `summary`, a deviation from the plan's §0.6 recorded in [DECISIONS.md](../DECISIONS.md) E021. 2, 3, 5 and 10: fixed. 4: fixed; the reply still says the name was not found (below). 6: partly; the four tools above give the page's date words, `customerOverview` and `invoices` still give ISO dates. 7: fixed for a word-for-word quote only. 8: withheld when wrong about both dates, and asked again once. 11: the expectation now accepts the overview; the navigation step passed live with no code change. 9 and 12: open.

**Still open:**

- With prepareDecision off, the first reply echoed the owner's words (finding 9); "one open invoice for DEMO-1,250.00 (stated)" passes the guard; the needs step's questions about late fees and a maximum amount (finding 12). Recorded, not fixed.
- catering-draft #3: the focus stays the draft, but on the search path the model is not told the name is a draft, and says it found no customer.
- explain-suggestion #5: the reply gave the suggestion's sentence and its cite without the date.
- Not exercised live: the step-number rule (unit tests), the runner's no-question path (a scratch mock probe) and the suggestion step's retry on a claim (unit tests).
- A cite id the model truncates fails the whole suggestion (owner-case #4 at `80d164f`). Accepting a unique prefix of a loaded id would be a separate decision.
- A list after a colon ("Steps: 1. …") is still read as figures.
- Live wording is not stable between runs of the same code (Task 5's proxy run).
- The fixed sentences quoted in the sections before slice 3 ("The agent's wording was withheld …") no longer exist; a withheld reply is asked again once, then shows "Here is what the records show[ about <name>]." with the blocks.
- The caveat above applies unchanged: scripted wording, one local model at temperature 0, and a model reader. The human column is empty. This is not a usability result.
