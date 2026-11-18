# Controlled Agent Actions — Design and Implementation Plan

Status: **Phase A (the deterministic Records backend) is implemented on branch `feat/controlled-actions-server-20261026` (from `a12e121`; commit `1324a2e`). Phase B (three security corrections to Phase A, the confirmation page, and the proposal card) is implemented on branch `feat/controlled-actions-ui-20261026` (from `1324a2e`; not deployed, not yet reviewed end to end in a browser with LibreChat). Phases C to E are not started.** Nothing is enabled: `prepareRequest` and `actionStatus` are off by default (the owner switches them on under Setup → Agent tools), so they are in no registry (desk, tool surface, MCP, LibreChat). The LibreChat side (patch 0003) is not part of this repository's branch. The design was written 26 October 2026 on `docs/controlled-agent-actions-20261026` (from `c69d521`, the MCP write idempotency commit); prefer function names to line numbers. Sections marked **Phase A as built** correct the original design where the implementation differs; Phases B to E are still the original plan.

The first controlled action: **a Staff member asks the assistant in LibreChat to prepare a payment-extension request; the assistant prepares a preview; a person confirms it in Nucleon; Nucleon opens the request, which then waits for the Owner's decision.** Staff confirming that a request is *submitted* is never the Owner *approving* the extension.

**The invariant.** The business effect of a confirmed action is fixed by Nucleon's code. After a person confirms, no model and no later answer can change the customer, the invoice, the requested date, or what it is (a request for the owner to decide, never an approval). Any path that would let one do so fails closed: it refuses, or discards the result. Section 8 lists the paths and the guard on each; `prototype/test_controlled_actions.py` holds each of them.

---

## Phase B: the three corrections to Phase A, enforced in code

Written 26 October 2026 after reviewing Phase A. Where a later section of this document still describes the Phase A behaviour, this section wins.

**A. The owner's review cannot be bypassed.** A request opened from a confirmed action (`r['intake']['structured']` is set) is decided only by the owner, through the owner's own paths (`POST /api/requests/<id>/decisions`, which includes the prepared-decision Confirm). The one staff path that could decide a request, `actWithinAuthority` (`DeskTools._actWithinAuthority`), now refuses it first, before anything is assessed, escalated, claimed or stored: **409 `OWNER_REVIEW_REQUIRED`**. Every path that can set a request `decided` or `completed` was audited: only two lines in the code set `decided` (`App.decide`, owner role only; `_actWithinAuthority`, staff, now guarded); `finish` sets `completed` and is called only by those two. `prepareDecision` keeps a preparation (the owner's `decide` is what commits it). The desk agent, the Lab/MCP surface and the AI Agent identity reach `actWithinAuthority` only through `POST /api/tools/actWithinAuthority` (offered to no agent: `roles: []`, `pressedBy: staff`), which runs the same method, so the guard covers all of them. Staff reaching `decide` is 403 whatever the request. `answer` stays 409 `CONFIRMED_FIELDS_LOCKED`; `owner_question` and `reanalyse` decide nothing. A source-level test pins that no third line sets `decided`. An unrelated request keeps staff-within-authority exactly as before (tests). Known and unchanged: the AI Agent test account's *owner* session is an owner session and can decide any request, a confirmed one included (it is a shared testing account, role-level like the rest); the Lab's owner token reaches no `decide` (only reads, prepare kinds and two acts).

**B. The reason is frozen.** Confirming executes exactly the proposal that was shown. The request's reason is `params.reasonDraft`, the assistant's draft, fixed when the proposal was made. The confirm body is `{version}` only; a body that carries a `reason` field different from the frozen one (any type, a trailing space, `null` when a reason was drafted) is **400 `REASON_FROZEN`** and nothing changes, before and after execution alike. Restating the frozen reason, or sending none, is the same confirmation. A replay of an executed action no longer compares reasons (there is nothing to compare): it returns the stored answer, `replayed: true`. The page shows the reason read-only and says that to change the wording the proposal is cancelled and a new one prepared.

**C. Service and person sessions are decided by the server, from the code used.** Phase A trusted a `channel: 'service'` field the *client* sent at login, so a script that left it out was indistinguishable from a person. Now:

* There are **service codes**, one per case role (`staff`, `owner`), distinct from the person access codes. Config `serviceCodes: {"staff": "...", "owner": "..."}` (each at least 6 characters; different from every access code, the agent code and each other, else the server will not start); otherwise random per start. They are printed to the records log on their own lines, apart from the access codes: `STAFF service code: …`, `OWNER service code: …` (the scripts that read `… access code: …` lines never see them; `nucleonctl logs` and `labctl logs` hide both kinds).
* A login with a service code makes a session with `channel: 'service'`, set by the server. A login with a person access code, or the AI Agent's code, always makes `channel: 'person'`. The `channel` field of the login body is ignored. `/api/session` and the login answer return the session's `channel`.
* The Lab signs in with the **service** codes only: config `recordsCodes` now means service codes and `codes_from_log` reads the `… service code: …` lines. It sends no channel, and after signing in it reads `/api/session` back and **fails closed**: unless the session says `channel: 'service'` for that role it ends the session and raises, so the Lab never operates on a person's session (a person's access code put into `recordsCodes`, or a records instance that predates service codes, cannot make the Lab act as a person).
* **CSRF.** Every session gets its own `csrf` token (`secrets.token_urlsafe`) when it is created. `/api/session` returns it to its own page. `POST /api/actions/<id>/confirm` and `/cancel` also require `X-Nucleon-CSRF` equal to that session's token (constant-time compare), else **403 `CSRF_REQUIRED`**. The checks keep their order and all remain: the `Origin` header present and in the allow-list, JSON content type, `Idempotency-Key`, role staff to confirm, the AI Agent identity refused, a service session refused (`PERSON_REQUIRED`, told first). A refused call never changes anything.
* **Said plainly:** the sign-in is role-level and shared. Anyone holding the person *staff access code* can sign in to a browser and confirm; the Lab, and anything holding only the Lab's configuration (service codes, MCP tokens), cannot, because a service code can never make a person session. Records still has no per-person identity (`staff_demo`, `owner_demo`, `ai_agent`).

**D. `prepareRequest`** says in its description and annotations that it *stores a proposal* (a record in Nucleon, not a request) and *supersedes the previous live proposal for the invoice*, and submits nothing. It stays not read-only and not in `NON_DESTRUCTIVE` (the Lab's annotations do not claim it harmless), and both tools stay `defaultEnabled: False`.

**Phase B as built (besides the corrections).**

* **Confirmation page** `#/actions/<actionId>` (`prototype/web/actions.js`, desktop): see section 9. It reads `GET /api/actions/<id>`; every fact, date, warning and state is the backend's; it does no arithmetic. The case list now carries `confirmedAction` (the action id) for a request opened from one, so the web app can tell it without reading the case.
* **Proposal card** (`lab/card.py`, shown by `lab/mcp_server.py` after the JSON of `prepareRequest` and `actionStatus`): see section 5. Contract with LibreChat patch 0003 (confirmUrl format, one link button, nothing sent on load): the card's one click handler posts `{type: 'link', payload: {url}}`.
* Tests: Records 807 → 826 (Phase A's confirm tests updated for the frozen reason and the csrf token; new classes for csrf, owner review, service codes and the page's source contract); Lab 333 → 355 (service-code sign-in and fail-closed, the cards, the example config). The page itself was checked in a real headless Chromium against a scratch server (see `docs/PHASE-B-TEST-ENVIRONMENT.md`).

---

## 1. Current write-operation architecture (what exists)

| Piece | Where | What it does today |
|---|---|---|
| Request creation | `App.create(actor, body, key)` (server.py) | Staff only. Body is `messageText` only (1–8000 chars). Saves the request (`req_<random>`), the event and the `idempotency` row **in one transaction**, schedules the analysis run. |
| Create idempotency | `App.dedup` / `App.remember`, table `idempotency` | Scope `actor.id:create:<key>`; same key + same body returns the same request; other body `KEY_REUSED`. **Never pruned** (only reset/restore clear it). |
| Analysis | agent run (`agent.py`), worker thread | Extracts customer, invoice, requested date from the intake text (model, or the mock parser: one `DEMO-\d+` reference, one written date such as `2026-11-14`, `14 November 2026` or `Friday 30 October`, and the clause after "because"; a date after "from" or "instead of" is the current due date); code checks that quoted references and dates appear literally. States: `received → analysing → needs_information | awaiting_owner` (or `preparation_failed`). |
| Owner decision | `App.decide`, `POST /api/requests/<id>/decisions`; prepared via `prepareDecision`, confirmed on `#/requests/thread/thread_<id>` | Owner only. Confirm checks `STALE_VERSION`, `STALE_EVIDENCE` (analysisId + evidenceVersion), `STALE_PREPARATION`, `STALE_SUGGESTION`. |
| Staff within authority | `actWithinAuthority` (pressedBy staff, no agent) | Re-assesses now; acts only if the recomputed recommendation is within the owner's limits. |
| Tool surface | `App.tool_call`, `POST /api/tools/<name>` | Role check, then once-per-key for act/prepare tools (and keyed `assessRequest`) in `record_ops` (`pending → applied → done`, 90-day retention; see DECISIONS, 26 October). |
| MCP | `lab/mcp_server.py` | Bearer token → role; the Lab holds **one records session per role** (`staff_demo` / `owner_demo`). Exposes read + prepare kinds and `ACTS`; never `openRequest` ("an agent's words never become a case's intake"). Optional client key in `_meta` `nucleon.lab/idempotencyKey`. |
| Browser confirm keys | `prototype/web/core.js` `keyFor(id)` | One `crypto.randomUUID()` per logical press, kept in memory until success; lost on reload (staleness checks then catch a repeat). |
| Card | `lab/card.py` | Read-only MCP-UI HTML for `customerOverview` / `invoices`; CSP `default-src 'none'`, one hashed script that only posts `ui-size-change`. No links, buttons or forms. |
| LibreChat v0.8.8 (rc2) | `client/src/utils/index.ts` `handleUIAction` | Handles only `intent`, `tool`, `prompt`, and each **becomes a chat message to the model** ("Execute the tool … using the tools available to you"). `link`/`notify` are ignored. Iframe sandbox is exactly `allow-scripts`. `MCPManager.callTool` sends no `_meta`, so every LibreChat call gets a fresh `mcp-<uuid>` key. |

Classification by what a call stores (audited 25–26 October): pure reads store nothing; `assessRequest` keeps an assessment version;
`prepareDecision` and `proposeImport` keep a preparation/proposal (nothing decided or imported); `withdrawPreparation`,
`requestSuggestion`, `raiseConcern`, `answerConcern`, `openRequest`, `decide`, `actWithinAuthority`, `withdrawRequest`,
`applyImportProposal` commit business changes.

**Gaps this design closes:** (1) no structured, code-checked preview of a new request; (2) no identity that survives LibreChat
retries, reloads and restarts (LibreChat sends no key); (3) no way for a *person*, rather than the model, to confirm from a
conversation; (4) no hard protection against two open requests for the same invoice (only the informational `duplicateIntake` flag in
`summary()`).

## 2. First Staff workflow (selected)

**Prepare a payment-extension request for Owner review**, built on the existing request record, case builder and Owner decision flow. No second request or approval system.

Why this slice: it is the requested business value; its effect is reversible and bounded (a request awaiting the Owner, which staff or the Owner can withdraw); the Owner's decision stays exactly as today. Considered and not chosen first: `raiseConcern` (simpler, no analysis run, but a lower-value action on an existing case — the fallback if coupling to the analysis run proves troublesome); `withdrawRequest` (destructive); Owner decisions (higher authority; Phase E).

**Phase A as built:** the request is created by the same code as `App.create` (`App.new_request`: the same record, first event and idempotency row; `create` is that plus the model's analysis), but it is **not analysed by a model**. Its customer, invoice, requested date and reason are the confirmed values, written when it is created, and its case is built at once, in the same transaction, by application code (`structured_case`, section 8). The original plan sent a code-generated sentence through the analysis run and compared the result with the action afterwards; that would have let a model's reading stand in for the confirmed values, so it was dropped.
## 3. Confirmation mechanism (selected)

**A Nucleon-owned confirmation page in the Records web app, opened from the assistant's card through a small allow-listed `link`
handler added to our LibreChat patch.**

| Option | Verdict |
|---|---|
| MCP-UI card button using a `tool` / `intent` action | **Rejected.** LibreChat turns it into a prompt to the model, which then decides what to call. A click cannot be told apart from model initiative, and a confirm tool the model can see is one it can call unprompted. |
| LibreChat backend integration that calls Nucleon on click | **Rejected for now.** Needs LibreChat server code and credentials for Nucleon inside LibreChat, a larger patch to carry on every upgrade, and LibreChat users are not Nucleon identities. |
| **Nucleon confirmation page** (`#/actions/<id>` in `prototype/web`) | **Selected.** The person signs in to Nucleon with their own session; the existing Confirm conventions apply (`keyFor`, staleness codes); the model never sees or reaches the confirm endpoint; works unchanged on M6 later. |

The card cannot open a page by itself (sandbox `allow-scripts`, `link` ignored). LibreChat patch **0003** adds one generic branch to
`handleUIAction`: for `type: 'link'`, open `payload.url` with `window.open(url, '_blank', 'noopener,noreferrer')` **only if** its
origin is in a build-time allow-list (`VITE_MCP_UI_LINK_ORIGINS`, default `http://127.0.0.1:8631`); otherwise do nothing. No
sandbox, sanitisation or CSP change. Fallbacks if the link is unavailable: the page is listed under the Records "Requests" area
(`#/actions`), and the result carries `confirmUrl` for the reply. The trade-off: one extra tab for the confirmation itself; everything
else stays in the conversation.

## 4. Stable operation identity lifecycle

The identity is **minted by Nucleon at preview time and persisted as business state**: `actionId = act_<random>` in a new `actions` table. It is bound to the kind (`open_request`), the invoice, the preparing role, the frozen values, and the facts it was prepared from.

```
prepareRequest (tool, model)     -> action proposed   (no request exists; nothing to approve)
person on the confirmation page  -> POST /api/actions/<id>/confirm {version}   (HTTP: a person's session, Origin, Idempotency-Key, X-Nucleon-CSRF)
                                    ONE transaction under the lock: load -> revalidate against the records now -> new_request ->
                                    case built by code -> idempotency row 'action:<id>' -> action executed       (all or nothing)
```

**Phase A as built:** there is **no `confirming` state and no three-transaction sequence**. Confirmation is one SQLite transaction, so a crash or an exception before the commit leaves the action `proposed` with no request, and a retry executes it once; after the commit every retry replays. There is no window in which the request exists and the action does not say so.

* **Retries, timeouts, repeated clicks:** every confirm of the same action is the same operation. Executed: the stored result with `replayed: true` (Phase B: the body carries no reason to compare; one that differs from the frozen one is 400 `REASON_FROZEN`). The `Idempotency-Key` header is required by convention; the action id is the identity, so a different key does not make a second request.
* **Lost response:** the page re-reads `GET /api/actions/<id>`; the assistant reads `actionStatus`. "Outcome requires verification" is a client state, resolved by reading the action. Never a new action.
* **Reopened conversations / reloads:** the card and the page carry the `actionId`; its state is read from the records.
* **Backend restart:** state is in SQLite; sessions are not (the person signs in again; the action is unchanged).
* **A deliberate new action:** a new `prepareRequest` call mints a new `actionId`. A newer proposal for the same invoice **supersedes** older live proposals (or marks them `expired`) in the same transaction, so only one is confirmable; and none is made while a request is open on the invoice.
* Arguments are never the identity. `prepareRequest` runs once per Idempotency-Key like every prepare tool (a retried call returns the same `actionId`); LibreChat's random per-call keys only create more non-binding proposals, each superseding the last.
## 5. API / MCP contract changes

**Records (prototype/server.py, coordinator.py) — Phase A as built**

* `CAPABILITIES`: `prepareRequest` — kind `prepare`, roles `['staff']`, `needsConfirmation: True`, **`defaultEnabled: False`**. Args: `customerId` (or `"current"`), `invoiceId` or `invoiceReference` (exactly one; a number that exists for several customers must be given as `invoiceId`), exactly one of `days` (whole number 1 to 90, after the current due date) and `requestedDueDate`, `reason` (optional, at most 500 characters: the assistant's draft). Refused with a code, nothing kept: unknown customer, invoice not that customer's, invoice not open, no due date on record, date not after the current due date and the as-of date, a request already open on the invoice (`OPEN_REQUEST_EXISTS` with its `requestId`).
  Result (dated): `{actionId, status: 'proposed', expiresAt, preview: {fromRecords: {customer, invoice{id, reference, amount, amountText, mark, amountAsOf, issuedOn, currentDueDate}}, completeness (the existing object for the customer, caveat included), proposedChange {currentDueDate, requestedDueDate, days}, draftedByAssistant {reason}, requires {confirmation, ownerDecision}, effect: 'Opens a payment-extension request for the owner to decide.'}, supersededActionIds}`. The amount and mark are the invoices tool's own; no balance is claimed beyond them. `message` is not used.
* `actionStatus` — kind `read`, roles staff and owner, **`defaultEnabled: False`**, args `actionId`: the action view (below). It writes nothing, not even an expiry.
* HTTP, **person sessions only** (section 7): `GET /api/actions/<id>` (staff or owner); `POST /api/actions/<id>/confirm` `{version}` (Phase B; was `{version, reason}`); `POST /api/actions/<id>/cancel` `{}`. Both POSTs need the page's `Origin`, an `Idempotency-Key` and (Phase B) `X-Nucleon-CSRF`. A listing (`GET /api/actions`) is not built.
  Action view: `{id, kind, status (expired computed from expiresAt), version, createdAt, expiresAt, preparedBy{role}, params{customerId, customerName, invoiceId, invoiceReference, currentDueDate, requestedDueDate, days, reasonDraft}, preview, outcome{code, message}, requestId, confirmed{at, role, reason}, request{id, status, label}}`, the label in the viewer's role's words; nothing owner-only (no brief, suggestion or owner notes).
  Confirm: `{action, request (the case list's summary), replayed?}`; refusals: 401 `NO_SESSION`; 403 `PERSON_REQUIRED`, `ORIGIN_REQUIRED`, `FORBIDDEN`; 400 `INVALID_INPUT`, `IDEMPOTENCY_REQUIRED`, `INVALID_CONTENT_TYPE`; 404 `NOT_FOUND`; 400 `REASON_FROZEN` (Phase B), 403 `CSRF_REQUIRED` (Phase B), 409 `ACTION_NOT_LIVE`, `ACTION_EXPIRED`, `STALE_ACTION_VIEW`, and, after settling the action as `invalidated`, `RECORDS_CHANGED`, `INVOICE_NOT_OPEN`, `UNKNOWN_DUE_DATE`, `INVALID_DATE`, `OPEN_REQUEST_EXISTS`.
* A request opened from an action carries `intake = {channel: 'confirmed_action', text (written by code from the confirmed values), receivedAt, structured: {actionId, customerId, invoiceId, invoiceReference, requestedDueDate, currentDueDate, days, reason}}`. The HTTP body of `POST /api/requests` stays `messageText` only. `answer` refuses such a request (409 `CONFIRMED_FIELDS_LOCKED`).
* Phase B: `POST /api/demo/login` ignores any `channel` the client sends; the session's `channel` (`service` for a service code, else `person`) is set by the server and returned by `/api/session`, which also returns the session's `csrf` token (section 7). `actWithinAuthority` on a request opened from an action is 409 `OWNER_REVIEW_REQUIRED` (section on the corrections).
* Not built: `confirmUrl` in the tool result (the card builds it from the Lab's `recordsPublicUrl` and the result's `actionId`), `GET /api/actions` (a list).

**Lab (lab/mcp_server.py, lab/card.py)**

* `prepareRequest` is a prepare kind, so `exposed()` lists it for the staff token once the owner turns it on; `actionStatus` is a read (added to `READ_ONLY`). **No confirm tool exists on any surface the model can reach.** (Phase B: the Lab's `sign_in` uses the service codes, sends no channel, and checks the session says `service`.) Nothing else in the Lab changed in Phase A, except that the Lab's own "tools the owner turned off" line no longer lists tools that are off by default.
* **Phase B as built:** `card.py` has an action card for `prepareRequest` and for `actionStatus` (both in `CARD_TOOLS`; the customerOverview and invoices cards are byte for byte what they were, pinned by digests). Content, all from the result's own preview: customer, invoice and amount with its mark, current → requested due date and days, the assistant's drafted reason (labelled), the expiry (UTC), the records' completeness caveat verbatim when the records are not explicitly confirmed complete, and a banner. **A proposal reads "PROPOSED — NOT SUBMITTED. A person must confirm it in Nucleon."**; only an `actionStatus` result whose status is `executed` says "SUBMITTED FOR OWNER REVIEW — request <id>; the owner has not decided." (once the request has a decision, the request's own label is shown instead); expired, replaced, cancelled and records-changed states say so plainly with the records' outcome message; an unknown state says nothing shows it was submitted. One button, only when the Lab config `recordsPublicUrl` (exactly `http://127.0.0.1:8631` or `http://127.0.0.1:18631`; validated at config load) plus the result's `actionId` make a URL that fits the contract `^http://127\.0\.0\.1:(8631|18631)/#/actions/act_[0-9a-f]{16}$` (else no button, and the text says to open the action in Nucleon). The label is **Review and confirm in Nucleon** for a live proposal and **View in Nucleon** for any other state. The url is in a `data-url` attribute; a second fixed script, allowed by its own hash in the CSP (`script-src` lists the size script's hash and this one; nothing else changes), posts `{type: 'link', payload: {url}}` on a click only. Without a button the card's CSP and script are the existing ones. No token, cookie or session is in the HTML. A card that cannot be made leaves the JSON result as before.

**LibreChat (patch 0003, isolated checkout first)**: the allow-listed `link` branch of `handleUIAction`, with unit tests. No agent configuration change until Phase C, and then only on a new test agent.
## 6. Database persistence and recovery

```sql
CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, invoice_id TEXT,
                                    created_at TEXT NOT NULL, data TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_live_action ON actions(kind, invoice_id) WHERE status = 'proposed';
```

Additive: an older database gets the table when it is opened, and the table is inert without the tool. `actions` is in `DATA_TABLES`, so a demo reset or "start empty" clears it (an old action id is then `NOT_FOUND`).

`data` (JSON): `version` (1), `preparedBy {role, actorId, actorKind, channel}` (no tokens or session ids), `preparedAt`, `expiresAt` (`ACTION_TTL_HOURS = 24`), `params` **frozen** `{customerId, invoiceId, invoiceReference, currentDueDate, requestedDueDate, days, reasonDraft}`, `basis {evidenceVersion: ev.version_for(invoiceId), currentDueDate, invoiceOpen}`, `preview` (as returned), and, as it happens, `confirmed {at, role, actorId, reason}`, `requestId`, `outcome {code, message}`, `supersededBy`, `history [{at, status, role}]`.

**Phase A as built: five states, minimal.**

| Status | Meaning | Next |
|---|---|---|
| `proposed` | Prepared, not submitted. Past `expiresAt` a read reports `expired` without writing | executed, cancelled, superseded, invalidated, expired |
| `executed` | A person confirmed it and the request was opened (`requestId`); the view shows the request's own status | — |
| `invalidated` (with `outcome.code`) | Refused at confirm because the records or the business state changed; nothing was opened | a new proposal |
| `cancelled` / `superseded` / `expired` | Not submitted. `expired` is written when a confirm or cancel meets one, or a newer proposal settles it | a new proposal |

There is no `confirming` state: confirmation is one transaction (section 4), so nothing can be committed but unrecorded. Why not more states: every extra state is a window to resume from; this design has none. The Phase A tests inject a failure at four points inside the transaction and one after it.

`prepareRequest` can answer `OPERATION_RESULT_UNAVAILABLE` (a crash after its commit but before its answer was kept, the record_ops rule); the assistant then reads the action with `actionStatus` or prepares again.

**Retention:** action rows and the `idempotency` row `<actor>:create:action:<id>` are permanent business records until the data is reset; they are not pruned by the 90-day tool-operation retention, and no archiving exists (future work). After any expiry a duplicate request is still prevented by the business check in section 8, not by an idempotency record.
## 7. Authorization model

| Who | May |
|---|---|
| Assistant via MCP (staff token) | `prepareRequest`, `actionStatus`, existing reads (when the owner has turned the two on). Cannot confirm, cancel or open a request. |
| Staff person (Records session, role staff, `channel: person`) | View, confirm or cancel `open_request` actions. Confirming submits a request; it approves nothing. |
| Owner person | View and cancel actions; cannot confirm (`403 FORBIDDEN`). Decides the request through the existing `prepareDecision` + Confirm or `decide`, including approving another date than the one asked: that is the owner's decision, not a change to the request. |
| Owner-only, unchanged | Decisions, limits, suggestions, answers to concerns, agent-tool settings (including turning the two tools on). |

Enforcement is in Records code, never in prompts or displayed controls. **Phase A as built**, `confirm` and `cancel` require, beyond the existing write checks (JSON content type, `Origin` if present in the allow-list, a valid session):

* an **`Origin` header that is present** and in the allow-list: a caller with none (a script, a service) is refused, 403 `ORIGIN_REQUIRED`; a foreign origin 403 `FORBIDDEN`. Browsers send it on every cross-site-capable POST; the cookie is `HttpOnly; SameSite=Strict`.
* an `Idempotency-Key` header (the action id is the identity);
* a **person session**: `actor.kind != 'agent'` (the AI Agent account, whatever role it acts as) and `actor.channel != 'service'`, else 403 `PERSON_REQUIRED`. Phase B: the channel is set by the server from the code used at login (a service code makes `service`; any access code, `person`); the client's `channel` is ignored. (Phase A trusted the client's field.)
* the session's own **csrf token** in `X-Nucleon-CSRF` (Phase B), else 403 `CSRF_REQUIRED`.
* role staff to confirm; staff or owner to cancel.

Auth failures never change the action. Reads (`GET /api/actions/<id>`, `actionStatus`) are open to any staff or owner session, including a service's.

* **Known limit, stated plainly:** Records has **no per-person identity** (`staff_demo`, `owner_demo`, `ai_agent`); the sign-in is role-level and shared. "A person" means a session obtained with the person *staff access code*. Phase B makes the service/person line the server's: a service code (known to the Lab's configuration and the records log) can only ever make a service session, and a person access code can only ever make a person session. Anyone holding the person staff access code can confirm from a browser; the Lab and anything holding only the Lab's configuration cannot. The structural guards remain: no tool in any registry leads to the confirm endpoint, the Lab only calls `/api/tools/<name>`, a call with no `Origin` is refused, and a call without the page's csrf token is refused. Per-person accounts are the real fix and are out of scope.
* Expired or revoked sessions: Records sessions are in memory with no idle expiry; a restart or sign-out ends them, and the page asks the person to sign in again; the action is unaffected and still expires at `expiresAt`. Revoking an MCP token stops new proposals; live proposals stay confirmable only by a person, and either role can cancel them.
## 8. Revalidation and concurrency

**Phase A as built.** `App.confirm_action`, under `App.lock`, in this order, in ONE transaction:

1. The action exists (404); `executed` replays or is `ACTION_ALREADY_EXECUTED` (section 4); any other status except `proposed` is `ACTION_NOT_LIVE`; a proposed one past `expiresAt` is written `expired` and refused `ACTION_EXPIRED`.
2. The body carries no reason, or the frozen one (else 400 `REASON_FROZEN`, checked first, also for an executed action); the page's `version` equals the action's (`STALE_ACTION_VIEW`). Neither changes anything.
3. **Revalidation against the records now**, the first failure writes `invalidated` with the code and plain-words message, commits, and refuses with 409: customer and invoice exist and still belong together (`RECORDS_CHANGED`); the evidence version `ev.version_for(invoiceId)` is the one prepared on (per customer: any invoice edit, new payment or allocation, due-date change, opening balance or note; the business date moving on also counts) (`RECORDS_CHANGED`); the current due date is the one prepared on (`RECORDS_CHANGED`); the invoice is open (`INVOICE_NOT_OPEN`); the requested date is after the current due date and the as-of date (`INVALID_DATE`); and **no other request is open on this invoice**: any request in `STATES_BEFORE_DECISION` naming it, or an executed action whose request is still `received` or `analysing` (`OPEN_REQUEST_EXISTS` with its id). This is the business uniqueness that outlives any idempotency retention.
4. **Execute**: `new_request` with the confirmed values, `structured_case` (below), the idempotency row `<actor>:create:action:<id>`, the action `executed`. Credit limits are not a confirm condition: they govern the Owner's decision and `actWithinAuthority`, which recompute them when used.

Concurrency: the lock serialises confirms, cancels and proposals in-process (Records is one process); the partial unique index allows one `proposed` action per invoice; the `idempotency` primary key makes the request once per action even if code changed. Two confirms at once: one executes, the other replays. A proposal and a confirmation at once: either the proposal supersedes the one being confirmed (its confirm is `ACTION_NOT_LIVE`) or the request opens first and the proposal is `OPEN_REQUEST_EXISTS`; never both a request and a live proposal for the invoice, never two requests.

**The case of a confirmed request is built by code only (`structured_case`, sharing `code_case` with the manual fallback).** It takes customer, invoice and requested date only from `intake.structured`: never from an answer, the parser or a model. It gives `aiStatus: 'not_used'`, adapter `confirmed-action-v1`, task mode `structured`, a requested-date source of origin `confirmed_action` (`interpretedBy: application_code`), an open item saying it was opened from the action and that no model read it, and events `analysis.finished` only. If the records no longer support the frozen values when it is built again (invoice paid, removed, or the date no longer after its due date), the case becomes `needs_information` with `missingFields: []` and a question telling staff to withdraw the request and prepare a new action; nothing is answerable and the request still names what was asked. The guards, one per path that could otherwise change the fields:

* `execute` (the worker) builds a structured request by code and never reaches the model runner, for a new run, a run resumed by `recover()` at startup, `prepare_stale_cases` (records changed) and "Prepare again" alike;
* `commit_outcome` discards any model outcome for a structured request (event `analysis.discarded`) and builds it by code;
* `fallback_or_fail` has no manual fallback for it (the fallback reads the invoice and date from answers and the message): a failed build is `preparation_failed`, fields untouched, and `fallback` itself refuses;
* `answer` refuses (409 `CONFIRMED_FIELDS_LOCKED`);
* suggestions need task mode `agent`, so a structured case gets none (the owner decides it without one; this is a limit, not a bug).

Owner `decide` and `withdrawRequest` are unchanged: the owner may approve another date, which does not alter the request that was made. **Phase B correction:** `actWithinAuthority` refuses a request opened from an action (409 `OWNER_REVIEW_REQUIRED`), so staff can never decide it, within the owner's limits or not; every other request keeps it. Known gap: a request opened the ordinary way whose invoice the model has not yet identified is not seen as "open on this invoice" (the existing informational `duplicateIntake` flag is all that covers it).
## 9. Proposed UI interaction

```
Staff:     Prepare a 10-day extension request for Harbour Demo Logistics.
Assistant: (findCustomers, invoices, prepareRequest) I found DEMO-202. Here is what would be submitted for the owner to review.
           Nothing has been submitted yet.
┌ PREPARED — NOT SUBMITTED ───────────────────────────────────────────┐
│ From the records   Harbour Demo Logistics · DEMO-202 · AUD 2,100.00 │
│                    Due Fri 6 Nov 2026 → requested Mon 16 Nov (10 d) │
│                    UNCONFIRMED: records not confirmed complete …    │
│ Drafted by the assistant   Reason: "cash flow timing" (edit it)     │
│ What confirming does   Opens a request for the owner to decide.    │
│ Owner decision     Not made                                         │
│ [ Review and confirm in Nucleon ]   expires Tue 27 Oct, 10:15        │
└─────────────────────────────────────────────────────────────────────┘
(confirm page, Nucleon tab: the same facts, editable reason, Confirm / Cancel; after Confirm:
 "Request opened (req_…). Waiting for the owner's decision." and a link back)
Staff:     Done?
Assistant: (actionStatus) Submitted: request req_… is awaiting the owner's decision.
```

**Phase B as built (page).** The confirmation page differs from the sketch above in one respect: the reason is **read-only** ("Drafted by the assistant, and submitted exactly as shown. To change the wording, cancel this proposal and ask the assistant to prepare a new one"). It shows customer (linked to the customer page), invoice, the amount still owed with its mark, original due date, proposed due date, extension days, prepared and expiry times (Sydney time), the records' completeness caveat verbatim, the plain statement "Confirming submits this request to the owner for review. It does not approve the extension.", and the controls **Submit for owner review** (never "Approve") and **Cancel proposal**. States, each from the backend's view: awaiting confirmation, expired, replaced, cancelled, no longer valid (the backend's outcome message), submitted (request id, its label in the viewer's words, link to the request), already submitted (replayed; nothing submitted twice), outcome uncertain. Confirm sends `{version}` with `Idempotency-Key: keyFor('confirm-action:'+id)` and `X-Nucleon-CSRF`, and the button is disabled while the call is in flight. On a network error or a 5xx the page reads the action again and shows the recorded state; if it is still proposed it offers "Try again" (the same key, the same action); it never prepares a new action (it has no way to: it calls no tool). The owner sees the page read-only with Cancel only; the AI Agent identity and a service session are offered neither control. A deep link `#/actions/<id>` survives the sign-in. The case page for a request opened from an action says it is not AI-prepared, shows "Submitted by staff for your review (confirmed action act_…)" to the owner, shows the request as confirmed rather than as "what the customer wrote", gives staff no answer form (the details are fixed; withdraw and prepare again), and the owner's decision form is unchanged.

Visual grammar, used in the card, the page and the assistant's instructions: **From the records** (backend facts, with marks);
**Drafted by the assistant** (model text, always editable before confirm); **Proposed** (not submitted); **Submitted / executed**
(with the request id); **Owner decision** (only from `decision`). The assistant's prompt states that preparing submits nothing and
that only the person's confirmation in Nucleon does; a guard withholds "submitted"/"created" claims unless `actionStatus` says
`executed`.

## 10. Test and acceptance plan

**Phase A, done:** `prototype/test_controlled_actions.py` (fictional records, a model stub that fails the test if it is called) and `lab/tests/test_controlled_actions_mcp.py` (scratch Lab and records servers). Preparation: authorised staff; owner refused; unknown customer, invoice, another customer's invoice, ambiguous number; invalid days and dates; incomplete records carry the unconfirmed caveat and no balance is claimed; a replacement supersedes atomically; no request or event is made; off by default; a retried prepare returns the same action. Confirmation: exactly one request awaiting the owner, task mode `structured`, fields equal the frozen values, no model call, no decision; 401, owner 403, agent identity and service session `PERSON_REQUIRED`, missing or foreign Origin, non-JSON; expired, changed invoice, new payment, allocation, changed due date, an extension approved elsewhere, a conflicting open request; replay, a different reason after execution, a stale version; two confirms at once, a lost response, a restart, a proposal racing a confirmation, an exception inside the transaction (four points) and one after it. The invariant: records change, "Prepare again" and a restart rebuild by code with the fields unchanged; a paid invoice leaves nothing answerable; `answer` refused; a model outcome discarded; a failed build never falls back to the parser. Recovery and compatibility: views after each outcome, no write on read, reset, an older database, `create` and the manual fallback unchanged.

**Phase B, done:** see the Phase B section above; the tests are in `prototype/test_controlled_actions.py` (csrf, owner review required, service codes, REASON_FROZEN, the page's source contract) and `lab/tests/test_action_card.py`, `test_controlled_actions_mcp.py` (cards, button rules, service-code sign-in, fail closed). **Still to do (Phases C to E):** the allow-listed `link` handler (LibreChat patch 0003: allow-listed origin opens, other origins, `javascript:` and malformed URLs do nothing), and end to end (isolated LibreChat on 3081 + scratch Nucleon, Playwright): ask, card, button opens the page, sign in, confirm, request awaiting the owner, back in chat `actionStatus` says submitted; reload the conversation shows the same action; press Confirm twice and after a Records restart, still one request; the Owner sees it in the queue and decides with the existing flow.
## 11. Implementation stages and dependencies

* **Phase A — Records actions (server only). Implemented** on `feat/controlled-actions-server-20261026`: `actions` table, `prepareRequest`, `actionStatus` (both off by default), `/api/actions/*`, revalidation, one-transaction confirm, service-session flag and Origin requirement, the code-only case builder for confirmed requests (replacing the original "intake template + mismatch check"), the Lab's `sign_in` flag and `READ_ONLY` entry, tests. Depends on `c69d521`.
* **Phase B — Confirmation surface.** Nucleon side **implemented** on `feat/controlled-actions-ui-20261026` (the three corrections, the `#/actions/<id>` page that sends the `version` it was shown and no reason, the Lab card and `recordsPublicUrl`, service codes, csrf; the needs-information state of a confirmed request says "withdraw and prepare again"). LibreChat patch 0003 built as `librechat:nucleon-card-v0.8.8-rc3` and verified on the isolated 3081 instance only: not part of this branch.
* **Phase C — One Staff workflow end to end** on a *new* test agent (existing agents untouched), isolated first; the 3080 switch needs its own approval.
* **Phase D — Acceptance:** section 10 in full, then a short controlled run on local 3080 with fictional data.
* **Phase E — Owner decisions**, only after D: reuse `prepareDecision` + the existing thread Confirm through the same link-out pattern (an `actions` kind is not needed there, the preparation already has `(requestId, version)` identity and staleness checks).
## 12. Known limits and rollback

Limits: **role-level identities only** (section 7: no per-person accounts; the service/person line is the server's, set by the code used; anyone with the person staff access code can confirm; the Lab and its configuration cannot); **the Lab and the records must be deployed together** (a new Lab refuses an old records instance that prints no service codes; an old Lab would sign in with person access codes, which the old records treated as people); the AI Agent test account's owner session can decide a confirmed request like any request (shared testing account, role-level); any invoice edit or new payment for a customer invalidates that customer's live proposals (by design: the evidence version is per customer); one confirmation tab outside the chat; the allow-list is build-time (a rebuild per environment); Records sessions have no idle expiry; a confirmed request gets no model-written suggestion (suggestions need task mode `agent`); the confirmed request's needs-information state has nothing a person can answer and says to withdraw it; action rows and their idempotency rows are permanent until reset (no archiving); LibreChat still sends no `_meta` key, so MCP-level dedup applies only to clients that send one (not needed on this path); upgrading LibreChat means re-applying patches 0001–0003.

Rollback: the Owner turns `prepareRequest` off in the agent-tool settings (existing `agentTools` override), which also removes it from MCP; revert the LibreChat image to rc2 (`docker-compose.override.yml` image line); the `actions` table is additive and inert without the tool; requests already opened are ordinary requests and follow the normal withdraw/decide paths.
