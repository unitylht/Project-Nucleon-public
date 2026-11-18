# Local fictional workflow with a live local-model agent

> **31 Oct 2026: the Records desk chat was removed** (the page at `#/`, `/api/desk/*`, the desk prompt and its reply guard). Sections below that describe it are history; `#/` is now the role landing page, the agent's tools are reached through `POST /api/tools/<name>` and the MCP server, and the full desk code is under the tag `poc-week7`.

Requires Python 3.10+ and a modern browser. No package installation is needed.

**Service codes (for the Lab).** Beside the access codes, the server makes one **service code** per case role (`staff`, `owner`), printed on their own log lines (`STAFF service code: …`, `OWNER service code: …`). A session made with one is marked `channel: 'service'` by the server (it is the code that decides, never the client): it works as that role for reading and the tools, but can never confirm or cancel a controlled action. The Lab signs in with them. `"serviceCodes": {"staff": "...", "owner": "..."}` fixes them for a test instance (each at least 6 characters, different from every access code, the agent code and each other); otherwise they are random at every start. Never give them to people.

**Link to the assistant.** The config may set `"assistantUrl"`, the address of the chat that talks to this server through the Lab (for LibreChat: `http://127.0.0.1:3080/c/new?agent_id=<the agent's id>`, which opens a new chat with that agent chosen). It must be an `http` or `https` link; a bad value stops the server at start. It is optional: unset, the Records pages show no assistant link. Signed-in pages read it from `GET /api/session` (`assistantUrl`, `null` when unset) and open it in a new tab (`target="_blank" rel="noopener"`) from the navigation and the landing page (`#/`). `config.example.json` shows the key with a placeholder id.

**Notices.** Each role's Home page lists what happened since they last looked (a case needs the Owner; a decision, an override or an information request for Staff; an information request about to expire or expired). `"notifications": {"webhook": "https://...", "publicUrl": "https://nucleon.example"}` in the config also POSTs each notice as JSON (`{text, role, kind, caseId, link}`; a Rocket.Chat or Slack incoming webhook reads `text`) on its own thread with a short timeout.

**The team's model (research).** Every case keeps a numeric feature row; the Owner's Model page (`#/research`) fits model versions on the Owner-labelled training table (by hand, or every N verdicts), shows the model's agreement with the Owner, and holds the promotion bar after which the score escalates cases at step 9 (off by default). Config: `"shadowModel": "/path/model.json"` is an optional bootstrap model (used until the first version is saved); `"researchProvider": {"kind": "builtin"}` (default, no packages) or `{"kind": "http", "url": "http://127.0.0.1:8640"}` for the team's own service (`tools/model-service/`). Format, endpoints and the rules in [docs/research/SHADOW-MODEL-20261102.md](../docs/research/SHADOW-MODEL-20261102.md).

**Fixed access codes for a demo instance.** The config may set `"accessCodes": {"staff": "...", "owner": "...", "operator": "..."}`; those replace the random codes and survive restarts (each at least 6 characters, all different). Only for fictional data behind a URL the team shares; leave it out for real records. A fourth key, `"agent"`, turns on the **AI Agent testing account**: one sign-in with that code holds a session for staff, owner and (where the console is on) the demo console at once, all acting as the actor `ai_agent` ("AI Agent"). The records' "Acting as" switch and the Lab's role switcher change the role without another code; each request is checked as the role its `X-Nucleon-Role` header names, so staff mode meets the real staff restrictions. Records made by it keep the actor id and add `actorName` and `actorRole`, and the pages show "AI Agent (as staff)" or "AI Agent (as owner)". Leave `agent` out and there is no such account.

## Run it

```bash
python3 prototype/server.py --sample-data                     # mock mode: no model, deterministic
python3 prototype/server.py --config my-service.json          # live mode: copy config.example.json, set "db"
python3 prototype/server.py --sample-data --agent-mode unavailable --db /tmp/nucleon-fallback.sqlite3 --port 8766
```

**Workspaces and the sample.** Each database holds one workspace: **real** or **practice** (fictional).

- **First run.** The owner chooses real, practice starting empty, or practice with the sample, then sets currency, decimal places and time zone under **Setup**. Until the required setup items are done, new requests are refused with `409 NO_RECORDS`, and Requests links to Setup.
- **The explicit workspace always wins** over `--sample-data` / `"sampleData": true`. That option only sets up a database that has no workspace yet, as a practice workspace with the sample.
  - A practice workspace started empty stays empty.
  - A real workspace refuses the sample (409), and has no demo console (404).
- **Upgrading the sample.** A newer `fixtures.json` replaces practice records only if they still match the sample exactly as loaded (a stored fingerprint). Changed practice records are kept, and the skipped upgrade is logged.
- **Older databases.** A database from before workspaces is recorded as practice or real according to its data mode. Cases and records are unchanged; this was checked on a copy of the deployed database.
- **Today.** Outside the sample, "today" is the current date in the workspace's time zone. The sample keeps its fixed demo date.

Open http://127.0.0.1:8765 (or the configured port). The log prints separate STAFF and OWNER access codes, plus an OPERATOR code when the demo console is enabled. Codes are generated at startup, never committed, and rotate on restart; the server assigns the role after checking the code. One browser can hold a staff, an owner and a console sign-in at the same time (one cookie per role); the buttons at the top switch between them. **Sign out** ends every role this browser holds (other browsers keep theirs), and a role prompt refuses a code for a different role with a message. Persisted records survive restarts.

The front end lives in `web/`: `index.html`, `app.css`, and one script per area, `core.js` (formatting, API, dialogs, sessions, routing and the page frame), `requests.js`, `desk.js` (the desk, on branch `explore/agent-coordinator-20261019`), `customers.js`, `imports.js`, `knowledge.js`, `setup.js` and `console.js`. It uses Arial and has no font files. The structure and design system are in [docs/UX-REDESIGN.md](../docs/UX-REDESIGN.md). There is no build step. The server sends the page with a Content-Security-Policy that allows only its own files, so keep scripts and styles out of the HTML.

Live mode needs an OpenAI-compatible chat-completions endpoint with native tool calling and JSON-schema output. `config.example.json` shows the home-server settings: endpoint, model name, timeouts, token limits and the optional `apiKeyEnv` (name of an environment variable; no key is needed on the home server). Keep real config files and databases outside Git. `--public-origin https://host` (or `publicOrigins` in the config) adds an exact origin allowed to write through an HTTPS proxy. A second instance behind a proxy that strips a path prefix (Caddy `handle_path /preview/*`) sets `"cookiePrefix": "nucleonp_"` and `"cookiePath": "/preview"` so its sessions stay apart from the one at `/`; the page follows the prefix it is served under, and keeps its browser storage under `nucleon-preview.*`.

The deployed test instance, service commands and access-code retrieval are in [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md). Exact prompts and model settings are in [PROMPTS.md](../PROMPTS.md).

## Records (Slice 2 of the [setup proposal](../docs/SETUP-AND-RECORDS-PROPOSAL.md))

In the redesigned interface the records are under **Customers** (one page per customer: invoices, payments and credits, opening balance and completeness, notes, requests), **Imports**, **Knowledge** and **Setup**; old `#/records` links open Customers. Every change happens in a dialog that names the customer and says what it affects. For staff and owner:

- **Setup checklist.** Required / recommended / good to have, with Skip for the last two. It also says what is not needed for extensions and what is not in this version.
- **Customers and invoices.** Number, date, amount; optional due date; optional amount still owed, which always carries the date it was stated.
  - Identity is (customer, invoice number), so two customers may share a number.
  - **Correct** saves a new version with a reason, and keeps the old values.
  - **Remove** applies to hand-entered records only. It is blocked when other records depend on the record, and asks for confirmation when cases use it.
- **What you already know.** Notes scoped to the whole business or one customer, as context or as a rule (shown to the owner, never enforced). The owner's notes are confirmed when saved with the tick. Staff notes are drafts until the owner confirms them. The agent only sees confirmed notes.
- **Import an invoice list (CSV).** Columns are suggested from their headings, and choices are remembered for files with the same headings.
  - The day/month order is asked when the dates are ambiguous.
  - One "amounts as of" date is required when an amount-owed or amount-paid column is used.
  - The preview sorts rows into new, already recorded, update, conflict, rejected (with a reason), unknown customer (create, map, or leave out) and left out.
  - Re-importing changes nothing. A typed-in invoice is matched, never duplicated, and a person's correction wins unless they choose to replace it.
- **Import history and Revert.**
  - Revert restores earlier versions, and keeps records that a later import also contained.
  - It is blocked when something changed afterwards.
  - It asks for confirmation when cases use the invoices. Decided cases keep their decision and get a visible flag.
  - What a revert would do (records reverted, restored or kept, what blocks it, cases affected) is shown before anyone confirms (`GET /api/imports/<id>/impact`); the server checks again on submit.
- **Import drafts.** An upload is a draft until applied. It can be kept and resumed, or discarded (`POST /api/imports/<id>/discard`); a discarded draft can never be applied. Every row's values (dates, amounts, due date or invoice paid) show before Apply.

**After any records change**, cases waiting for the owner are prepared again, and decided cases about a changed invoice are flagged.

**Not built yet:** opening balances, completeness statements, payment terms used in calculations, ledger-account or XLSX imports, and decision-time capture.

**In cases:**
- "Outstanding" is either the sample's figure, "stated as of D", or "Not recorded".
- Days overdue are calculated only from the sample or from an amount stated as of today.
- A stated zero sends the case back to staff, with the reason written by code.
- When an invoice number belongs to several customers, staff choose the invoice from a list. Nothing is ever picked silently.
- If even the no-AI fallback fails, the case shows **Couldn't prepare** with **Prepare again**. It does not retry by itself.

## Payments, opening balances and completeness (Stage 3; deployed to the shared practice demo on 18 October 2026, `4f45ca7`)

Records are kept in tables: customers, invoices, notes, payments, allocations, opening balances and completeness statements, each with its id, version and history. An older database is moved into them once, at startup, and the move is checked to be lossless. The old records document is then kept frozen. If an earlier release changed that document afterwards, startup stops and explains why.

- **Payments.** Customer, date received, amount and an optional reference. A possible duplicate needs a tick to confirm it is a different payment: the same reference, or, with no reference, the same date and amount. Corrections keep versions. Removal is blocked while money from the payment is allocated.
- **Allocate.** Only to the same customer's invoices, and only up to what is left on the payment and the invoice. Removing an allocation that cases use asks for confirmation, and decided cases are flagged.
- **A stated amount and payments.** "X still owed as of D" may already reflect payments made on or before D.
  - Payments after D come off it.
  - Earlier ones count as already reflected only when a person says so (**Needs attention**); amounts that reconcile are shown as a suggestion. Otherwise they are not taken off, and the amount is "at most".
  - Contradicting records are a conflict, never "settled".
- **Opening balances.** Per customer: owed or held in credit as at a date, with its source, and what it includes in credits: none, every one recorded here, or not stated. Invoices and payments dated on or before it are asked about: part of it, missed from it, or not sure (the default; not counted either way).
  - When the unanswered invoices' amounts at that date add up to it, that is only a suggestion (a missing invoice and a missing credit would add up as well); a person confirms it in one step.
  - A **credit** held for the customer (a credit note, or a prepayment carried in the balance) is recorded like a payment, marked *credit*, and is applied to invoices or marked *not for an open invoice*.
  - The balance from it is the whole account, shown apart from any one invoice.
- **Completeness.** Only the owner confirms that records of some types, for some customers, are complete for a period. They do it here, or with an import: the customers in the file, or all customers. For payments, that also means there are no credit notes or adjustments, which this version can't record.
  - Nothing else makes records complete. The latest date on record is shown separately.
  - A record added to, or taken out of, a confirmed period afterwards ends the statement for that customer.
- **What is shown.**
  - Per invoice: "exact, as of D", only when there is an opening balance whose credits are stated, the payment records are complete, every payment or credit is allocated or marked, and nothing about the customer is unresolved; otherwise "at most X", "stated as of D" or "not recorded", with **Why not exact**.
  - Per customer: the balance from the opening balance, recorded payments and money not allocated (money a person marked as not for an open invoice is shown apart).
  - A missing payment is "not recorded", never "unpaid".
- **Import a payment list (CSV).** Choose **Payments received** for the file.
  - Re-imports and overlapping exports add only new payments.
  - A reference repeated with different values, or an unreferenced row that looks like a payment already recorded, waits for a person: same payment, a different one, or leave it out.
  - An invoice column allocates to that customer's invoice only, within what is left; the rest stays unallocated, with a note.
  - Revert waits while the import's money has been allocated afterwards.
- **In cases.**
  - The owner sees "AUD 150.00 (exact, as of …)" with its steps, or "At most AUD 400.00" with why it is not exact, and the customer balance as a separate point.
  - Days overdue are stated with an exact amount only when records are complete to today.
  - A settled invoice goes back to staff.
  - A decided case is flagged with the amount before and after when its evidence changes; the decision is never changed.
- **Sample files** for trying it: [samples/](samples/) (fictional). Walkthroughs are in [DEMO-SCRIPT.md](../docs/DEMO-SCRIPT.md), Parts B and C.

## The desk (branch `explore/agent-coordinator-20261019`, 19–21 October 2026; preview only)

The first slice of [P003](../docs/AGENT-COORDINATOR-PROPOSAL.md) (E018), made conversational in the second slice (E020, P003 "Revision 3"), and given a shared situation, registered capabilities and prepared actions in the third (E021, P003 "Revision 4", 21 October). The shared practice site still runs `f95f50f` without any of this. Fictional data only. Prompts, tools, guards and mock rules: [PROMPTS.md](../PROMPTS.md), "coordinator-v0.4" (and "coordinator-v0.3" for what it builds on), with the addenda "coordinator-v0.5" for the business tool surface (E022, below) and "coordinator-v0.7" for the second iteration (E023, below).

Since 20 October it runs as a separate preview, with its own database, cookies and codes, at https://nucleon.dracooz.top/preview/ (live model, E019; the conversational desk since the evening of 20 October; the third slice since 21 October, `df10ab6`, `coordinator-v0.4`). The business tool surface and the second iteration below are not deployed there.
The arrangement, codes, updates, reset and the live-model check results are in [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md), "Preview instance (agent-coordinator branch)".

**Where things are**

| Route | What it shows |
| --- | --- |
| `#/requests` | The desk. On the left (on a phone, its own page) is the thread list: **Nucleon**, the general thread, first, then one thread per case, newest first. Every case is listed, including cases entered through the form. On the right is the open thread. |
| `#/requests/thread/<id>` | One thread. A case thread is `thread_<request id>`, stored the first time it is opened. |
| `#/requests/new` | The desk with the general thread open and its input focused. |
| `#/cases` | **List view**: the old queue, unchanged, linked from the desk's header. |
| `#/cases/new` | The old request form, with the practice samples. Staff see "New request (form)" in the list view's header. |
| `#/case/<id>` | The full case page, unchanged. |

**What people type.** There is one input with **Send**; Ctrl or Cmd+Enter also sends. Each message is one run of the desk agent (`coordinator.desk_run` over `server.DeskTools`): the model calls read tools over the records, the context and the cases, then replies; code guards its words and writes every block under them.

- **Staff:**
  - **Requests.** The model hands the message to `openRequest`; the case is created from the message as typed, through the same path as the form, and the view moves to its thread.
  - **Questions in their own words,** several at once and with follow-ups: what a customer owes, their open or overdue invoices, a request's status, what the owner has shared, where something is done in the app, what the desk can do. One answer card holds the words first, then the blocks asked for, then at most one next step.
  - **"Add <name> as a customer":** a draft card with **Create customer**, which opens the existing Add customer dialog with the name filled in. Nothing is added until the person saves it. A name already in the records gets a link to that customer instead.
  - **Context** from staff gets "Only the owner adds context; staff notes go in the records." Staff notes stay in Knowledge.
- **The owner:**
  - **Context** about a customer or the business. It becomes one **What I understood** card: **Confirm**, **Correct** (kind, end date, remove a line, choose the customer, share with staff) or **Discard** (with a reason).
  - **The same questions** as staff, with the owner's own context.
  - **Requests** typed by the owner are not entered; the reply says staff enter them.
- **The current customer.** Each thread keeps one per role, shown as "About <name> ×" above the input (press it to clear). "they", "their" or a question naming nobody stay on it; a new name switches; an unknown name or "another customer" gets "Which customer do you mean?", with names. Since the third slice the chip also reads "About <name> (not yet a customer) ×" for a prepared customer and "About <name> (not found) ×" for a name the records do not hold; only a customer has the records link.

**The third slice (21 October).**

- **One situation.** `App.situation(role, …)` in `server.py` builds, for each role, the case and customer picture the page shows; the case block is drawn from it, and the agent reads it at the start of every case-thread turn (`coordinator.render_situation`). `caseDetails` gives it for any case. Staff's situation holds none of the owner's lines, questions, suggestion or prepared decision.
- **The agent's tools are registered** in `coordinator.CAPABILITIES`: each tool's kind (read, prepare, act), roles, whether a person confirms its effect, and its default. The owner turns tools off or on under **Setup → Agent tools** (`#/setup`; staff see nothing of it). A tool turned off is neither offered to the model nor run. Confirmation is separate: it is each flow's own button. In this fictional preview every implemented tool is on by default, and no tool sends anything outside Nucleon.
- **Prepared decisions.** The owner says a decision in words in a case thread ("approve 14 days, then"); `prepareDecision` works out the date from the current due date, compares it with the date asked and the day limit, and shows a **Prepared decision** with one **Confirm decision** button. Nothing is decided before it is pressed. `requestSuggestion` forms a new advisory suggestion on request, through the same checks as the automatic one.
- **Next steps** come from the workflow (`actions_for`), and the agent answers "what should I do next?" from them.
- **Presentation.** A short answer shows its words and one closed **Details** expander; a summary adds one line per block; a list shows the blocks open. Each invoice appears once. A withheld reply is asked again once, then reads "Here is what the records show about <name>." with the blocks.

**The business tool surface (21 October; `coordinator-v0.5`; E022).** The desk's operations, open to any client over HTTP. The Nucleon Lab experiment uses them, at `/lab/`, through its agent and its MCP server; see [lab/README.md](../lab/README.md).

- `GET /api/tools` → `{tools: [{name, kind, needsConfirmation, description, parameters}]}`: the tools this role is offered now (the registry with the owner's overrides under Setup → Agent tools), with the model-facing descriptions and JSON schemas. `reply` is not listed. 401 without a session; 403 for the demo console's role.
- `POST /api/tools/<name>` with `{args, message?, current?: {customerId?, requestId?}}` runs one tool through `DeskTools` as the session's role. The result is `{ok: true, result}` (dated, with `subject`) or `{ok: false, error, message}`.
  - 404 for an unknown tool, `reply` included. 403 for a tool this role is not offered now.
  - A `prepare` or `act` tool needs an `Idempotency-Key`: it runs once per key, and the same key with another body gives 409 `KEY_REUSED`.
  - `message` is the person's own words. `prepareDecision` and `prepareCustomer` take only what it gives, and `openRequest` opens a case only from it.
  - A tool that calls the model answers `MODEL_UNAVAILABLE` when the model cannot be reached.
- **Five operations added** (also given to the desk, on by default):
  - `compareExtension` (read): the date a number of days gives, or the days a date gives, against the date asked and, where this role may see it, the day limit; it prepares nothing.
  - `withdrawPreparation` (act, owner): removes a prepared decision; it is not a decline.
  - `workQueue` (read): what waits on whom across every customer, for this role.
  - `listRequests` (read): one customer's, one invoice's or every customer's requests, open, decided or all.
  - `prepareHoldingMessage` (prepare): a promise-free status text for the customer, written by code and not sent.

**The second iteration (21 October, afternoon; `coordinator-v0.7`, labelled `coordinator-v0.6` in the code until the final records commit; E023).** Built for the Lab's revisions and presentation, and run by the Lab's records instance; the desk has it too.

- **The preparation lifecycle.**
  - A request keeps `preparations`, `[{version, status, outcome, approvedDueDate, approvedDueDateText, days, reason, by, at, replacedBy?, decidedAt?}]` on `GET api/requests/<id>`, beside `preparedDecision`, the current one or none.
  - The status is one of:
    - `current`;
    - `superseded`, with `replacedBy`, when a new preparation replaces it;
    - `withdrawn`, by `withdrawPreparation`, by deciding through the form, or by the app (`by: null`) when the case is prepared again or a new suggestion arrives;
    - `confirmed`, when `decide` names its version.
  - Each change is an event: `decision.superseded`, `decision.withdrawn` and `decision.confirmed`. Staff never see `preparations`.
  - `decide` still refuses any version but the current one (409 `STALE_PREPARATION`).
- **prepareDecision revises.** While a decision is prepared, a new call gives only what changes, and the rest keeps its prepared value. The result adds `revisionOf`, `retained`, `reasonFrom` and `figuresFrom`.
  - A reason is accepted when it is in the message, or when it equals an earlier preparation's reason, or it is kept from the current preparation on a revision.
  - An earlier preparation's days or date stand in only when the message states no figure.
  - A day count or date said implies approve. A new decline needs a decline word, and a decline word blocks the implied approve.
  - Fix wave 2: when the reason passed is not in the message, the message's reason clause ("because …", "since …", "so that …", "reason: …") is the reason (`coordinator.said_reason`, `reasonFrom: 'message'`). With nothing prepared, a limit phrase ("up to", "at most", "no more than", "maximum") and no decision word gets "Is that a decision to approve, or guidance to keep?"; `DESK_SYSTEM` says a limit statement is guidance to keep.
  - When something is missing it answers `missing` with an ask: "How many days, or until which date?" or "Approve or decline?".
- **State fields.**
  - Every case summary has `originalDue`, `dueNow` and `dueNowFrom` (`invoice` or `decision`), with their text forms.
  - The list routes, `workQueue` and `caseDetails` add `ordinal` (the request's number among the open requests on its invoice) and `flags`. `flags` holds a likely duplicate (`duplicateIntake`: an earlier open request on the same invoice for the same date), computed live, never stored, merging and refusing nothing.
  - `caseDetails` and the situation add `concerns`, `preparations` and `activePreparation` (both `null` for staff).
  - The desk page shows "Due now: …; originally due …" once a case is decided.
- **`raiseConcern(requestId, text)`** (staff, act, on by default): staff's own words, which must be in the message. The concern is kept on the case for both roles, and is listed with what was said and drawn on the desk under the case's lines ("raised by staff"). While the case is undecided it also waits on the owner, and the owner's `workQueue` gives the reason "staff raised a concern". It is refused for a decided case.
- **The "still holds?" question.** In the needs step, after the model's questions, code adds one question per line: "On <date> you said '<quote>'. Does that still hold for this request?" (`from: 'code'`, `kind: 'check'`).
  - It is asked about an owner line the case cites (quoted by a question, answering one, or giving the day limit), when the line is an expectation said before today or is more than 30 days old. Expired lines are left out.
  - It is answered through the usual answer route, which keeps a line for the case, and it stays answered when the case is prepared again.
  - While it is open, it holds back the suggestion, as any open owner question does. Staff never see it.
- **`workQueue`** marks the caller's own items `waitingOn: 'you'` and adds `summaryText`, written by code.
- **Checks:** unit suite 463 after fix wave 2 (461 before it, 443 before the iteration; `test_preparations.py` is new), `desk_check.js` 76/76, and at `9672de1` `ui_check.js` 150/150 and `layout_check.js --seed` 217/217.

**Statements and threads.**

- **Stored records:** what the owner says is a statement, kept with its verbatim text, who said it, the business date, its thread and its scope. Statements, threads and turns are stored in their own tables.
- **Lifecycle:** a statement is proposed until the owner confirms it once. Correcting or retiring it keeps a history.
- **Who sees it:** owner-only by default. "Share with staff" applies per statement and needs a customer.
- **Scope:** a statement that names no customer stays unassigned and is never used. Expired lines are kept and marked "expired". Confirmed Knowledge notes are read alongside statements.
- **The owner's own turns,** and the agent's replies to them, are visible to the owner only.

**A case thread** (since the second slice) starts with the case, then the turns; one footer per thread holds **Open the full case**, **Customer records** and **Sources**.

- **Owner:** one card with the request line, the customer's own words, the amount still owed with its mark, the suggestion when on, and the decision panel (with the optional field "Guidance to keep for <customer>, not the decision", and "No operational restriction has been applied." when a constraint line is in the context). Then folded sections with counts: **What the agent needs** (each question with "Why I ask", **Answer**, "Keep this for <customer>" and **Decide without this**; open while a question is open; questions never block the decision), **What you have said**, **Facts and sources**, and **Reply draft** (not sent) after deciding.
- **Staff:** one status line ("With the owner since …; nothing for you to do.") or the question addressed to them, the request line with the customer's words, folded **Facts**, **What the owner shared** when something is shared, and the **Reply draft** once decided.

**Suggestions setting.**

- **Default:** off. Only the owner turns it on (**Turn them on** on the decision card, or `POST /api/suggestions {on}`).
- **When it is on:**
  - a waiting case's suggestion is withheld while a question is open;
  - after an answer or a skip only the suggestion step runs again;
  - **Use this date** fills in the decision form;
  - the case records the suggestion that was on screen beside the decision (`suggestionSeen`, owner-only), never inside it.
- **Turning it off** withdraws waiting suggestions.
- **Counters:** `GET /api/suggestions/counters` (owner only) counts the workflow on fictional data, not decision quality.

**API added**

- `GET /api/desk/threads` and `GET /api/desk/threads/<id>` (with `focus`, the viewer's own current customer: `{name}|null` before the third slice, `{kind, name, customerId?}` since; and since the third slice `situation`).
- `GET /api/agent-tools` and `POST /api/agent-tools {tool, enabled}` (owner only; the POST needs an `Idempotency-Key`): the registry with each tool's `enabled`.
- `GET /api/tools` and `POST /api/tools/<name>`: the business tool surface (above).
- `POST /api/desk/threads/<id>/turns {text}`.
- `POST /api/desk/threads/<id>/note {text, customerId?}`: a plain turn of the person's own, with no model call (the Create customer flow's "Customer <name> added."); a `customerId` moves this role's current customer.
- `POST /api/desk/threads/<id>/focus {customerId|null}`: sets or clears this role's current customer.
- `GET /api/desk/statements/<id>` (staff: a confirmed, shared statement's id, status, visibility, scope, date and active lines only), `POST /api/desk/statements/<id>/confirm {customerId?, visibility?, lines?}` and `POST /api/desk/statements/<id>/retire {reason}`.
- `POST /api/requests/<id>/questions/<qid>/answer {text, keepForCustomer}` and `.../skip`.
- `GET` and `POST /api/suggestions`, and `GET /api/suggestions/counters`.
- `POST /api/requests/<id>/decisions` also takes `suggestionShown` and `remember {text, keepForCustomer}`, and since the third slice `preparedVersion` (409 `STALE_PREPARATION` for a replaced preparation).
- The turn, note, statement, question and decision writes need an `Idempotency-Key`. `POST /api/suggestions` and the focus route do not.

**Demo console.**

- `POST /api/demo/advance {days}` moves the business date forward by 1–366 days. It is for the operator only, in practice workspaces only.
- Waiting cases are prepared again for the new date.
- Reset and start-empty clear statements, threads, turns and the moved date.

**Owner brief `brief-v3`** adds `contextShown`, `questions`, `suggestion`, `suggestionStatus` and `withheldBecause` to every `brief-v2` key. Staff see none of them filled, except the questions asked of staff (since 20 October). Older briefs read as before.

**Phone.** The list is one page and a thread is another, with "← Requests" to go back. Up to 760 px wide, the input sits fixed above the tab bar.

**Checks** (fictional data; mock agent unless stated):

- **Unit tests:**
  - `test_desk_store.py`: stores, context and the business date.
  - `test_coordinator.py`: schemas, guards and the mock.
  - `test_desk_api.py`: threads, turns, confirm and retire.
  - `test_case_coordinator.py`: needs, questions and brief-v3.
  - `test_suggestion.py`: the setting, withholding, stale suggestions, remember and the counters.
  - `test_desk_agent.py`: the desk agent loop, the reply guard end to end, staff visibility in every view and model payload, the current customer, the prepared customer and the balance line.
  - `test_situation.py`: the situation for each role, `caseDetails`, case lines in context, dates in words and the card's subject.
  - `test_capabilities.py`: the registry, tools per role and per override, the Agent tools API, and a disabled tool never offered or run.
  - `test_prepared_actions.py`: prepared decisions and Confirm, `requestSuggestion` through the day-limit check, and the workflow's steps.
  - `test_presentation.py`: `detail`, each invoice once, the focus kinds, the retry of a withheld reply and repeated calls.
  - `test_tool_surface.py`: `GET`/`POST api/tools` (roles, overrides, keys, refusals), the five operations, one result per key under concurrent retries, and staff never seeing owner-only words in `workQueue` or `listRequests`.
  - `test_preparations.py`: the preparation lifecycle and its events, revisions and what they keep, the due dates, the ordinal and duplicate flag, `raiseConcern`, and the "still holds?" question.
- **Browser checks:** run them on a fresh scratch server from `deploy/ui_check_server.py <db> <port>`, never on the shared site. Since 20 October the scripts that write or reset (`desk_check`, `conversation_check`, `ui_check`, `guide_check`, `effort_compare`, `layout_check --seed`, `live_coordinator_check.py`) refuse any server that is not on `127.0.0.1` or `localhost`, the shared and preview ports (8620, 8621) and their logs (`deploy/scratch_only.js`).
  - `node deploy/desk_check.js <base> <service-log> <out-dir>`: the desk as the owner and staff use it, at 375 and 390 px too (D12 since the tool surface: "would 10 days fit?" shows a comparison block).
  - `node deploy/conversation_check.js <base> <service-log> <out-dir> [--live]`: 23 scripted conversations, 108 turns (`deploy/conversations.json`), with transcripts. With `--live`, on a scratch `server.py --config` in live mode with the sample and the demo console, wording assertions are INFO; see [docs/qa/CONVERSATION-REVIEW.md](../docs/qa/CONVERSATION-REVIEW.md).
  - `node deploy/effort_compare.js <base> <service-log> <out-dir>`: three scenarios on the old pages and on the desk. It writes [docs/qa/EFFORT-COMPARISON.md](../docs/qa/EFFORT-COMPARISON.md).
- **Live-model check:** `python3 deploy/live_coordinator_check.py <base> <service-log>` on a scratch server in live mode with the fictional sample (`server.py --config` with its own `db`, the demo console and `"sampleData": true`). It walks the demo through the desk API and prints the model's wording. It skips when the model does not answer.
- **Last results, the second iteration** (21 October, `coordinator-v0.7`): unit suite 463 after fix wave 2 (`58c7a7f`; re-run for the records commit that sets v0.7), 461 at `6038696`; `desk_check.js` 76/76 at `6038696` and after fix wave 2; `ui_check.js` 150/150 and `layout_check.js --seed` 217/217 at `9672de1`. No desk `conversation_check.js` run is reported for the second iteration. The Lab's runs against these records are in [lab/README.md](../lab/README.md) and [docs/DECISIONS.md](../docs/DECISIONS.md) E023.
- **The business tool surface** (21 October, `coordinator-v0.5`): unit suite 443 at `3e52328` and in the records commit after it; `desk_check.js` 74/74 at `98e2448`; at `73e95d4`, `ui_check.js` 150/150, `layout_check.js --seed` 217/217 and `conversation_check.js` 310/310 on the mock. No live desk run was made for v0.5. The Lab's own checks are in [lab/README.md](../lab/README.md), and their results in [docs/DECISIONS.md](../docs/DECISIONS.md) E022.
- **Third slice** (21 October, after round 4 of its fix wave, `50233e5`, `coordinator-v0.4`):
  - unit suite 428;
  - `desk_check.js` 73/73;
  - `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 (at `d5d165a`; no page code changed after);
  - `conversation_check.js` 310/310 on the mock (18 live-only assertions skipped), and 325/325 with the live model (3 INFO, no reply withheld, no retry, no model failure, no failed suggestion). Earlier live runs of the slice, 307/317 to 323/323, and the controller's 312/318 at `80d164f`, are in [docs/qa/CONVERSATION-REVIEW.md](../docs/qa/CONVERSATION-REVIEW.md), "Re-run after the fix wave";
  - the preview through its public URL with the live model: deployed as `df10ab6` and checked as both roles on 21 October ([docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md), "Third slice (21 October)").
- **Second slice** (20 October, `b888db8`): unit suite 372, `desk_check.js` 60/60, `conversation_check.js` 169/169 on the mock and 170/170 (3 INFO) live on `coordinator-v0.3`; the preview: [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md), "Conversational desk and verification".
- **First slice** (before the conversational desk): `guide_check.js` 58/58 with the live model through the old pages, `effort_compare.js` 17/17, and `live_coordinator_check.py` 18/18 and 20/20 (PROMPTS.md, "Observed behaviour: coordinator-v0.1"). These were not re-run on the second slice.

### Importing a spreadsheet by proposal (E024; `lab-v0.5` and `coordinator-v0.8`)

Two tool-surface operations, both run once per Idempotency-Key through `POST api/tools/<name>`:

- **`proposeImport`** (staff and owner; also a desk tool, where only the rows pasted in the person's message are read) takes an attached
  file (`fileBase64`, .xlsx or CSV, at most 2.5 MB decoded; the route's body limit is 4 MB), `csvText`, a `sheet`, a `proposalId` (the next
  version of that proposal, from its stored file) and `hints` (shape, mapping, customer prefix, credit days, date order, customer choices).
  It returns the proposal and imports nothing: shape (invoices, payments or ledger), mapping with who chose each column (heading, model or
  person), naming and due-date rules, counts, doubtful rows, each batch's preview against the records now, and `ready`.
- **`applyImportProposal`** (`pressedBy` staff and owner; offered to no agent role, so the desk agent gets FORBIDDEN) takes the proposal id
  and the version shown, and optionally corrections (which make the next version and apply it at once). It re-runs the preview under the
  lock and refuses (`RECORDS_CHANGED`) if a row's status or the customers to create differ; otherwise it writes the invoices batch and the
  payments batch through the importer's upload, mapping and apply, each with its revert. Refusals: `STALE_VERSION`, `NOT_READY`,
  `ALREADY_APPLIED`, `NOT_FOUND`.

`prototype/xlsx.py` is the stdlib workbook reader (zip and ElementTree; shared and inline strings, numbers, serial dates by cell style; a
DOCTYPE anywhere in a part, an oversized part or more than 20,050 rows is refused). `importer.propose` finds the header row, tells the
shape, maps columns by heading synonyms in English and Vietnamese and asks the model (`classify_columns`) only about columns no heading
names, sending headings and three sample rows; each answer is checked against the whole column. A ledger is split by code: an invoice is
the sum of its debit lines once, credit rows are payments.

Proposals are kept in the records database, in the `meta` table under `importProposals:<id>`: the five most recent (`KEPT_PROPOSALS`),
and only the newest keeps its file; an applied proposal keeps its summary and batches, not its file. Reset and start-empty delete them.
The Lab's side is in [lab/README.md](../lab/README.md), "Importing a spreadsheet". Tests: `test_import_proposal.py` (20); the unit suite is 484.

### Week 7 core flow: unit, references, assessment, authority (E025; `lab-v0.6` and `coordinator-v0.9`)

- **Import correctness.**
  - `importer.detect_unit` reads the unit from the file (a currency column or token VND, AUD, USD, đ, "$"; Vietnamese ledger headings mean VND). `applyImportProposal` refuses a mismatch with the workspace before it writes anything: `UNIT_MISMATCH`, the proposal's status `refused`, the message in `lastError`. A file that does not say its currency imports as the workspace currency and says so.
  - A payment's invoice is read from its description or a reference column (`HĐ 73`, `hóa đơn 73`, `HD73`, `invoice 73`, `số HĐ 73`) into `invoiceNumber`; several references mean `multipleInvoices`, flagged and unallocated. The proposal's `references` counts payments, those that name an invoice, those left unmatched and those naming several. FIFO is never applied at import. Codes become aliases of the customers the import created.
  - `GET /api/records/imports/proposals/<id>` (staff, owner) returns the proposal as it stands: `status` `proposed`, `applied` (with its batches), `reverted` (every batch was reverted; `revertedAt`), `refused` or `duplicate` (a file with the same hash was already applied and a batch of it is still applied), with `unit`, `workspace`, `references`, `counts`, `lastError`, `message`, and the card's `view`. Pressing Import twice returns the same batches; a failed apply reverts what it wrote and leaves the proposal `proposed`.
- **`current` is a hint.** A `customerId` or `requestId` in `current` that no longer exists is dropped and the result carries `notes`; it is not a refusal. `GET /api/records` and `GET /api/tools` carry `datasetId` (the last reset's time, or the creation time). `POST /api/demo/reset` with `{"to": "empty"}` leaves an empty workspace with no settings.
- **`prototype/behaviour.py`** (stdlib): `replay` gives the deterministic part of Hoang's pipeline with his feature names, from recorded allocations where they exist and FIFO for the rest (`allocationBasis`), reconciled against the customer balance (`reconciles`, `difference`). It runs as of the business date.
- **Two tools.**
  - `assessRequest` (read; staff and owner) returns `{facts, policy, model, recommendation, evidence, limitations}` and stores the assessment on the case. `model` is always `{status: 'unavailable', reason}`: no approval model runs, so there is no probability or percentage. `recommendation.outcome` is `approve_within_authority`, `escalate` or `decline_by_policy`, derived only from `policy.checks`.
  - `actWithinAuthority` (act; staff; pressedBy: offered to no agent, as Import is; the staff member presses Act within authority on the assessment card (the records tool, run as that person); the assistant never records it) records the approval, with `decisionSource: 'staff_within_authority'`, the limits and the checks, only when the current assessment says `approve_within_authority`. Otherwise `NOT_WITHIN_AUTHORITY`, and the case is marked `escalated` with the failing check ("escalated: <check>" in the owner's queue).
- **Authority settings** (`GET/PUT /api/setup/authority`, owner only; the whole object, absent keys take their defaults, unknown keys 400): `staffMayApproveUpToDays` (1 to 365 or null), `maxOutstanding` (money or null), `requireNothingOverdue` (default true), `maxPriorLateShare` (0 to 1 or null), `hardRules` (check names), `maxConcernRounds` (1 to 10, default 2). With every limit null, everything escalates. They are not on the tool surface for writing.
- **Decision fields.** The owner's `decide` records `decisionSource: 'owner'`, `recommendation` and `followedRecommendation`. `remember` takes `until` (YYYY-MM-DD) and `prepareDecision` carries `remember` on the preparation; `decide` uses the preparation's when the body has none. A concern on an assessed case records `disagreesWith`; at `maxConcernRounds` the case is `escalated: 'concern rounds'`.
- **Tests:** `test_behaviour.py` (8), `test_assessment.py` (13 and the review fixes), `test_tool_surface.py` (stale `current`), `test_demo_reset.py` (3), and more in `test_import_proposal.py`; the unit suite is 547. `desk_check.js` 76/76 (20 agent tools in the Setup table).

## Walk through the case (live mode)

On branch `explore/agent-coordinator-20261019`, Requests opens the desk (next section). These steps use the old pages, now at **List view** (`#/cases`) and its form (`#/cases/new`), where the samples are.

1. Sign in with the STAFF code. Choose **Try a sample**, then **Clear request** (DEMO-101, "on Friday 30 October"), and **Send to the agent**.
2. The case opens with live progress while the agent reads the message and calls `findCustomers`, `getInvoiceFacts`, `getConfirmedKnowledge`, `calculateExtension` and `prepareApprovalTask`. Observed: about 7–13 s on the home server.
3. Click **Owner** at the top. The first time, it asks for the owner code; after that one click switches. The case is under **For you**. It opens with:
   - a due-date timeline: today Fri 16 Oct, due Tue 20 Oct, asked for Fri 30 Oct, +10 days;
   - the app-calculated facts: AUD 1,250.00 outstanding, 10 days extension, not overdue;
   - the customer's words, with the agent's quotes underlined;
   - the decision panel.
4. Approve the requested date, approve a different date, or decline, with a short reason. There is no recommendation to accept or reject.
5. Switch back to **Staff**. The case shows the reply to send and **Copy reply**. Nothing is sent.
6. Other samples: **Missing date**, **Unclear date** ("next Friday", sent on a Friday) and **Unclear customer** each make the agent ask staff for a detail. **Overdue invoice** (DEMO-201) shows the late stretch in red on the timeline.

**Evidence and sources**, **Activity** and **Technical details** sit folded at the bottom of each case. A case prepared without AI, by the test agent, or by an earlier version always says so under its title.

## Demo console

Enable it only for fictional demo data. Set `"demo": {"enabled": true, "backupDir": "..."}` in the service config; a relative `backupDir` sits next to the database. The server then prints an OPERATOR code, and **Demo console** at the top opens it.

- **Reset demo data** first saves a backup (SQLite online backup, mode 600). It then clears every case, event, run and retry key and puts back the original fictional invoices and due dates.
  - Sign-ins, access codes, model settings and configuration are untouched.
  - A model run still in progress is discarded when it finishes.
  - On data that is already in the starting state, it does nothing and makes no backup.
- **Undo** appears right after a reset. **Restore** works on any listed backup.
  - Both replace the current cases and save them as a backup first.
  - Work that was in progress in the backup is resumed.
- **Before you present** shows the agent status, who is signed in, and the fixed demo date. **Demo messages** lists the samples with copy buttons.

Staff and owner codes cannot use the console, and the operator code cannot submit, answer or decide cases. Without `demo.enabled`, or with non-fictional data, the console endpoints answer 404 and no operator code exists.

## What does the work

| Step | Live mode | Mock mode (tests) | Model failed or unavailable |
| --- | --- | --- | --- |
| Read message: invoice/customer, requested date, reason, ambiguities | **Gemma** (`extract_request`, strict JSON schema); code checks every value against the message | regex: one `DEMO-###` and one ISO date | regex, disclosed as fallback |
| Choose and call lookup/calculation tools | **Gemma** native tool calls; dispatcher validates and executes | scripted calls through the same dispatcher | code sequence (`manual_fallback`) |
| Lookups, money/date arithmetic, snapshots, evidence versions | application code | application code | application code |
| Owner brief | **Gemma** selects verbatim customer quotes (checked against the message); **code** writes the summary, the typed facts, notes and open points; the page draws the timeline from those facts | scripted (no quotes) | code only |
| Recommendation (approve/decline) | **none**: disabled in the backend until an owner policy exists | none | none |
| Create clarification or owner-approval task | **Gemma** tool call, committed by code after version re-check | scripted | code |
| Commit approve / changed date / decline | owner only | owner only | owner only |
| Reply draft | deterministic template from the committed decision, `not_sent` | same | same |

Every analysis records `aiStatus`: `live` (successful model run), `mocked` (deterministic adapter) or `failed` (model error, then manual fallback with the failure reason). A fallback is never labelled live.

## Controls

- **Tool permissions:** the model sees only the six tools listed in PROMPTS.md. Unknown tools (for example `approveCredit` or `sendMessage`), server-controlled fields (`requestId`, `businessId` and similar), unknown arguments and malformed JSON are rejected and recorded as `tool.rejected`, never executed. Text that describes a tool call executes nothing; after one nudge the run fails.
- **Untrusted input:** customer messages and retrieved notes are delimited data. Extracted values must appear in the message. Explicit date wording is cross-checked, for example "Thursday 30 October" is rejected because 30 October 2026 is a Friday. The requested date passed to `calculateExtension` must match the verified extraction or a staff answer. Instruction-like text in a message adds an open point for the owner.
- **Evidence lookups:** customer IDs must come from `findCustomers`. Invoices must belong to the customer. Several matching customers or open invoices return `AMBIGUOUS`, which leads to clarification. Unconfirmed notes are excluded.
- **Structured brief (format `brief-v2`):** the model cannot write facts.
  - `prepareApprovalTask` accepts only a snapshot ID and verbatim customer quotes, each with a topic. A quote must appear in the message. It is stored as `attribution: customer, verified: false` and never becomes an account fact. If a quote contains the requested-date wording, code relabels it as `request`.
  - The material facts are typed fields built by code from the trusted lookup and calculation results:
    - outstanding amount and original due date: invoice fields;
    - current due date: the invoice field, or the owner decision that moved it;
    - requested date: the customer's words or a staff answer, unverified;
    - as-of date: a fixed setting;
    - extension and overdue days: calculations with named inputs.
  - Code renders the summary and the facts table from these fields. A model-supplied value or a reference ID cannot change or legitimise a fact. Legacy reference IDs are gone.
- **Recommendation boundary:** suggestion fields a model sends anyway (`suggestedOutcome` and similar) are stripped before validation and recorded as a `suggestion.suppressed` event. `suggestedOption` is always stored as `null`, decisions no longer copy a suggestion, and the UI states "No recommendation".
- **Remaining model prose:** clarification questions, field reasons and extraction notes are checked by a small guard. Text that states amounts, describes payment history, reliability or risk, states an approval or refusal, or gives a confidence figure is rejected (clarifications) or removed with a visible code note (extraction notes).
- **Older records:** briefs stored before `brief-v2` are labelled `brief-v1-legacy` at read time. Their model-written text is shown as legacy and unverified, and their suggestion appears as `historicalSuggestion` (`historical_unvalidated`). Stored rows are never rewritten. A legacy owner task can still be decided, or prepared again in the new format.
- **Input validation:** errors name the field (`messageText`, `requestedDueDate`, `invoiceReference`, `approvedDueDate`, `reason`). The page shows each error under its field and keeps what was typed. Clarification answers are checked immediately: the date must be after the current due date, and the invoice must exist. Retries reuse the same idempotency key.
- **Bounds:** one extraction call, at most 10 tool-calling turns, 12 tool calls, 120 s per model call and 300 s per run. The run stops when a human task is created.

## Concurrency and recovery

- Intake, answers and reanalysis save the request and a durable `runs` row, then return immediately in live mode. The page polls for progress.
- One worker thread performs inference without holding the application lock. The lock is taken only briefly to record events and commit the result.
- A unique index allows only one `running` run per request. Reanalysis during a run supersedes the old run, and its late result is discarded.
- Before saving, the result is re-checked against:
  - the run status;
  - the request version;
  - the active run ID;
  - for approval tasks, the invoice-scoped evidence version.

  If evidence changed during inference, for example the owner approved another request for the same invoice, the result is discarded and a fresh run starts (at most twice).
- On startup, runs left `running` are marked `interrupted` and pending requests are re-queued. Decided requests without drafts are finished.
- `GET /api/model-status` (signed-in users) reports whether the model service is reachable and loaded. It is cached for 20 s and probed without the application lock. Request sockets time out after 30 s.
- Run exactly one server process per database; sessions and the lock are process-local.

## Differences from the wider interface proposal

- The brief's typed facts carry their own source or calculation inputs. The analysis snapshot keeps a flat `facts` copy of the same values for compatibility.
- The interface proposal allowed an optional `suggestedOption`. This release always stores `null`, because no owner approval policy or validated recommendation method exists.
- Tool results given to the model are minimised summaries (e.g. formatted amount, snapshot id `S1`); stored records keep full EvidenceRefs.
- `saveResponseDraft` is not exposed to the model, and the `draft_reply` model role is not implemented. Drafts come from a deterministic template.
- Clarification fields are limited to `invoiceReference` and `requestedDueDate`. Answers have no `sourceRef`.
- The fixture is version 2: two fictional customers and three invoices. DEMO-101 is unchanged. Older databases are upgraded at startup; any pending owner task then needs reanalysis.
- Single business per database, demo access codes instead of accounts, invoice-list and payment-list CSV import only (no ledger accounts or XLSX), no external messaging or accounting writes, no rule learning.

The fictional fixture uses AUD and Australia/Sydney solely for this demo. It is unrelated to NTK or Art of Gelato and supplies no evidence about their terms or currency. Existing invoice terms are preserved; approvals are stored as separate single-invoice decisions.

## Checks

```bash
python3 -m unittest discover -s prototype -p 'test_*.py' -v      # deterministic tests, no model (547 on branch explore/agent-coordinator-20261019, 22 Oct)
python3 prototype/live_gemma_check.py --config my-service.json    # REAL model: 15 fictional scenarios
python3 prototype/perf_records.py                                 # cost at about 500, 5,000 and 20,000 fictional records
```

- `test_workflow.py` contains the original 13 HTTP workflow checks.
- `test_agent.py` covers:
  - adapter parsing and failure normalisation (malformed, truncated, HTTP error, timeout, unreachable);
  - dispatcher validation (disallowed tools, injected server fields, cross-customer and ambiguous lookups, swapped dates);
  - the structured brief: regressions for the three accepted v0.2 errors (swapped day counts, swapped dates, unsupported credit claim), fact-to-source binding, decision-sourced due dates, rejected model replacement values, verbatim quotes, suppressed recommendations;
  - legacy v1 records, field-specific validation and model status;
  - lock release during inference, stale request and stale evidence results, the single-running-run constraint and restart recovery;
  - the origin allowlist and the anonymous session probe.
- `test_records.py` covers workspaces and sample loading, manual records and corrections, owner knowledge, CSV preview, re-import, conflicts and revert, and the importer's parsing.
- `test_store.py` covers the record tables: the lossless move, never deleting on save, per-customer evidence versions, re-stamping, and the startup guard.
- `test_payments.py` covers payments and allocations: limits, duplicates, corrections, removal, statements of what was owed, and what cases show.
- `test_payment_import.py` covers payment-list import with the sample files: allocation within the customer, re-import and overlap, review of ambiguous rows, corrections, stale previews, and revert.
- `test_balances.py` covers where stated amounts meet payments: no second subtraction, reconciliation, answers and their statement, conflicts, later and higher statements, reverts, migration, and decided-case flags.
- `test_openings.py` covers opening balances and inclusion; `test_coverage.py` covers completeness statements; `test_exact.py` covers exact amounts and their reasons, in cases too and on the no-AI path.
- `test_full_flow.py` runs the whole workflow, from an empty workspace to a decision and a revert.
- `test_credits.py` covers credits held at the opening balance and amounts that only appear to reconcile (offsetting omissions, several possible combinations).
- `test_demo.py` covers:
  - console access (enabled only by configuration, operator only, no case work for the operator);
  - reset (backup first, initial invoices and due dates, sessions kept, no-op when already clean);
  - restore (listed names only; replaced data saved first; WAL mode kept; pending work resumed);
  - a model result arriving after a reset;
  - the approved extension stored with the owner's decision;
  - several roles signed in in one browser;
  - static files and their security headers.
- `live_gemma_check.py` calls the configured model and reports model identity, prompt version, executed and rejected tools, and latency.
- Deployed-URL and browser checks are in `deploy/`, with `rehearse_stage3_upgrade.py` for the Stage 3 upgrade and rollbacks on database copies.

None of these checks validates business accuracy, owner agreement or real-world time savings.
