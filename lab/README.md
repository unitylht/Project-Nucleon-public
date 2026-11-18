# Nucleon Lab

**As of 30 October 2026 the Lab is MCP-only.** It serves a Model Context Protocol server (streamable HTTP) at `mcp/` and the read-only
cards for MCP-UI clients; the chat page, the internal Pydantic AI agent, its guards and prompts, the conversation store and the web build
were removed in this commit. Their history is under the tag `poc-week7`. The Lab maps a bearer token to a role and calls the records
instance's business tool surface (`GET /api/tools`, `POST /api/tools/<name>`) with a records session for that role. Fictional data only.

## Set up (its own venv; the records server stays stdlib-only)

    ~/srv/nucleon/runtime/python-3.12.14/bin/python3 -m venv <venv>
    <venv>/bin/pip install -r lab/requirements.txt

Run every command from the repository root.

## Run

    cp lab/config.example.json <config.json>     # recordsUrl, mcpTokens, recordsLog ...; replace the mcpTokens placeholders: see MCP server below
    <venv>/bin/python -m lab --config <config.json>

`rootPath` (`/lab`) is uvicorn's root path behind a proxy that strips the prefix. A config file written before 30 October may still hold
`store` and `model`; they are ignored.

Config keys (`lab/config.py`; the defaults in brackets):

- `host` [`127.0.0.1`], `port` [8630]: where uvicorn listens. Deployed: 8622.
- `rootPath` [`/lab`]: the prefix the proxy strips. Use `""` when the Lab is served at the root, as the scratch checks do.
- `recordsUrl` [`http://127.0.0.1:8631`]: the records instance, reached directly, not through the proxy. Deployed: 8623.
- `publicOrigins`, `mcpTokens`, `recordsLog`, `recordsCodes`, `recordsPublicUrl` [`[]`, `{}`, null, `{}`, null]: for the MCP server, below.
- `timingLog` [null]: a file path (a relative one is under the Lab's working directory, e.g. `logs/tool-timing.jsonl`); unset, nothing is written. See "Tool timing log" below.

## Test

Run from the repository root; `-m` puts the root on the path, so `lab` and `prototype/` import, and `-t .` must not be added:

    <venv>/bin/python -m unittest discover -s lab/tests -q

`test_mcp`, `test_mcp_idempotency` and `test_controlled_actions_mcp` start a scratch records server through `lab/tests/harness.py`
(`deploy/ui_check_server.py`: the fictional sample, the demo console) on a free port with its database in a temporary directory.
`test_mcp` also serves the Lab with uvicorn on a free port and talks to `mcp/` with the `mcp` client. `test_card`, `test_decision_card` and
`test_action_card` test the cards (`lab/card.py`) against fixtures.

After a deploy, read-only:

    python3 deploy/e2e_lab_check.py https://nucleon.dracooz.top
        # mcp/ refusing a made-up token, records/api/session not signed in, / and /preview/ still 200

## MCP server (`mcp/`)

The same operations for an external agent: an MCP server (the `mcp` SDK's low-level `Server`, streamable HTTP, stateless) at
`mcp/` under the app root, so **https://nucleon.dracooz.top/lab/mcp/** when deployed (keep the trailing slash) and
`http://127.0.0.1:<port>/mcp/` locally. Config keys:

- `mcpTokens`: `{"<token>": "owner" | "staff"}`. A client sends `Authorization: Bearer <token>` and acts as that role; a missing or
  unknown token gets 401. A token has 32 characters or more (`python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`),
  so the example's placeholders are refused at start. Real tokens live only in the deployed config, never in git.
- `recordsLog`, `recordsCodes`: how the Lab signs in to the records for a role (`POST api/demo/login`), once, at first use; it
  keeps the cookie per role and signs in again when the records answer 401 (they restarted). It uses the records' **service
  codes**, never the access codes people use: a session made with a service code is marked `channel: 'service'` by the records,
  which never let such a session confirm or cancel an action. The Lab sends no channel and reads `GET api/session` back; unless
  it says `service` for that role the Lab ends the session and refuses to operate (fail closed). The service codes rotate on every
  records start unless the records config fixes them (`serviceCodes`), so they come from `recordsLog` (the records instance's
  service log: the `STAFF service code:` and `OWNER service code:` lines after the last ` URL: http` line), else from
  `recordsCodes` (`{"staff": "...", "owner": "..."}`, service codes). They are never logged or returned.
- `recordsPublicUrl`: the Nucleon records address a person's browser opens, `http://127.0.0.1:8631` (the local runtime) or
  `http://127.0.0.1:18631` (the isolated test instance); nothing else is accepted. The action cards (`prepareRequest`,
  `actionStatus`) use it with the action id of the result to build their one button's link
  (`<recordsPublicUrl>/#/actions/<actionId>`); unset, the card has no button and says to open the action in Nucleon.
- `publicOrigins`: behind the proxy the Host header is the public one, which the SDK refuses (421) unless allowed. Each origin
  here (`["https://nucleon.dracooz.top"]` when deployed) allows its host and origin, beside loopback.

What a role gets:

- **Tools:** the role's records registry (`GET /api/tools`) less `openRequest` (an agent's words never become a case's intake)
  and less every `act` kind except `withdrawPreparation` and `requestSuggestion`. Prepare kinds stay: they only prepare, and the
  owner confirms on the records page. Staff therefore get no `prepareDecision`, `interpretStatement`, `withdrawPreparation` or
  `requestSuggestion`, and staff results carry no day limit from guidance the owner has not shared.
- **Card (MCP-UI):** a successful `customerOverview` or `invoices` result is followed by a second content item, a read-only HTML card
  (`ui://nucleon/card/<tool>/<customerId>`, `text/html`, made by `lab/card.py`) for clients that render MCP-UI (LibreChat 0.8.x shows it in
  the tool-call panel, and inline if the model writes the `\ui{id}` marker). The first item, the JSON, is unchanged and stays what the
  agent reads. The card only shows what the records returned (never a sum or a completeness judgement), says Unconfirmed unless
  `balanceEstablished` is true, and has no links, forms, buttons or actions; its one fixed script reports the card's height to the host.
  Errors carry no card, and a card that cannot be made leaves the plain result. `lab/tests/make_card_fixtures.py` rebuilds the test fixtures.
- **Action cards (Phase B of docs/CONTROLLED-AGENT-ACTIONS.md):** a successful `prepareRequest` or `actionStatus` result (when the owner has
  turned them on) is followed by an action card (`ui://nucleon/card/<tool>/<actionId>`): the customer and invoice, current → requested due date
  and days, the assistant's drafted reason, the expiry (UTC), the records' completeness caveat when the records are not confirmed complete, and a
  banner: "PROPOSED — NOT SUBMITTED. A person must confirm it in Nucleon." for a proposal, "SUBMITTED FOR OWNER REVIEW — request <id>; the owner has
  not decided." only for an executed action, and the plain state otherwise. The one button ("Review and confirm in Nucleon", or "View in Nucleon"
  once there is nothing to confirm) posts `{type: 'link', payload: {url}}` to the host on a click and writes nothing; `url` is `recordsPublicUrl` +
  `/#/actions/<actionId>`, built only when it fits the contract with LibreChat patch 0003 (else no button). It has its own fixed script, allowed by
  its own hash in the card's CSP. `lab/tests/make_action_card_fixtures.py` rebuilds the test fixtures.
- **Input:** each tool's input schema is the registry's `parameters` plus an optional `message`: the person's own words, passed to
  the records as the call's message. prepareDecision and prepareCustomer keep only what the message gives, so without it
  prepareDecision answers that something is missing. `current` is never set: name the `customerId` or `requestId`.
- **Result:** the records `result` as JSON text, or `{error, message}` (plus the records' structured `hint`, if the refusal has one) with `isError` when the
  records refuse. A tool the role is not given is a protocol error ("Unknown tool").
- **Text for the model, full result for the card (S3):** when the records' result holds a `forModel` object (the decision tools and the S3 read tools
  `whatIsNeeded`, `comparableCases`, `customerStatus`, `policyBacktest`, `impactSummary`), the text item is the JSON of `forModel` (plus `hint` if the result has one):
  a few hundred characters written by code, instead of the 8-10k characters of the full result. The card (second item) is made from the full result and is
  unchanged; the full JSON is never sent to the model. Every other tool's text is the records' result as before.

## Tool timing log

With `timingLog` set, the Lab appends one JSON line per tool call (also refused calls), for the processing-time metric (S4/S5 read it):
`{"tool", "role", "caseId" (null unless the result has one), "start" (UTC, ms), "durationMs", "ok", "resultChars" (the full result), "forModelChars" (the compact text the
model read; null if the tool has none)}`. It holds no arguments, text, token or customer name. The directory is created; a write failure is logged and never
fails the call. `durationMs` is the Lab's time for the call, including the wait for the records. Example: `{"timingLog": "logs/tool-timing.jsonl"}` with the Lab started from `~/Developer/nucleon-local`.

Connect Claude Code (the header follows the URL):

    claude mcp add --transport http nucleon-lab https://nucleon.dracooz.top/lab/mcp/ --header "Authorization: Bearer <token>"

Any streamable-HTTP client works the same way, for example the `mcp` SDK's `streamable_http_client(url, http_client=
httpx2.AsyncClient(headers={"Authorization": "Bearer <token>"}))` with a `ClientSession`, as `lab/tests/test_mcp.py` does.
