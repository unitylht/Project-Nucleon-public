# Phase B test environment (isolated stack)

Status: 26 October 2026. Both halves are written and were exercised end to end in a browser on 26 October (see section 11). Fictional data only. Nothing here touches the running services (records 8631, Lab 8630), their data, LibreChat on
3080, Docker's other containers, or M6. Design and behaviour: `docs/CONTROLLED-AGENT-ACTIONS.md` (Phase B).

## 1. What the isolated stack is

| Piece | Where | Port |
|---|---|---|
| Records (this branch, `feat/controlled-actions-ui-20261026`) | a separate checkout (`~/Developer/Project-Nucleon-phaseB`), its own database file outside the repository | **18631** (loopback) |
| Lab (this branch) | the same checkout, its own store | **18630** (loopback) |
| LibreChat (patched test build `librechat:nucleon-card-v0.8.8-rc3-test`), compose project `lc-cardtest` | its own container and Mongo, not the 3080 one | 3081 |

The records instance must be reachable by the person's browser at `http://127.0.0.1:18631` (that is the origin of the confirmation link), and the
Lab by the LibreChat container at `http://host.docker.internal:18630`.

## 2. Configuration

**`records.json`** (`python3 prototype/server.py --config records.json`). Fixed codes make the stack restartable without re-reading a log;
they are fictional, at least 6 characters, and all different:

```json
{
  "port": 18631,
  "db": "/absolute/path/outside/the/repository/phaseB.sqlite3",
  "agentMode": "mock",
  "sampleData": true,
  "publicOrigins": ["http://127.0.0.1:18631"],
  "accessCodes": {"staff": "<person staff code>", "owner": "<person owner code>"},
  "serviceCodes": {"staff": "<lab staff service code>", "owner": "<lab owner service code>"},
  "demo": {"enabled": false, "backupDir": "backups"}
}
```

`serviceCodes` must differ from every access code, the agent code and each other, or the server refuses to start. Left out, they are random per
start and are printed as `STAFF service code: …` / `OWNER service code: …` (the Lab can then read them from the records log with `recordsLog`).
`accessCodes` are what people type; never give a person a service code and never configure the Lab with an access code (it will refuse, see 4).
`publicOrigins` must include the origin the person's browser uses (the confirm and cancel calls require an `Origin` in this list).

**`lab.json`** (`python -m lab --config lab.json`, the venv):

```json
{
  "host": "127.0.0.1",
  "port": 18630,
  "rootPath": "/lab",
  "recordsUrl": "http://127.0.0.1:18631",
  "recordsPublicUrl": "http://127.0.0.1:18631",
  "recordsCodes": {"staff": "<lab staff service code>", "owner": "<lab owner service code>"},
  "mcpTokens": {"<random token of 32+ characters>": "staff", "<another>": "owner"},
  "publicOrigins": ["http://host.docker.internal:18630"],
  "store": "lab.db",
  "model": {"provider": "mock"}
}
```

`recordsCodes` are the records' **service** codes (the same values as `serviceCodes` above). `recordsPublicUrl` is exactly
`http://127.0.0.1:18631` here (the local runtime would use `http://127.0.0.1:8631`; the Lab refuses any other value at start). Real tokens are
generated on the test machine and never committed.

## 3. Which tools are on

`prepareRequest` and `actionStatus` are **off by default**. The owner turns them on, on the scratch workspace only: sign in as the owner →
Setup → Agent tools → switch both on (or `POST /api/agent-tools {"tool": "prepareRequest", "enabled": true}` as the owner, once per tool). Staff then
get both through the Lab's MCP server; the owner's MCP token gets `actionStatus` only. No tool that confirms, cancels or executes exists on any
surface the model can reach.

## 4. Authentication model (what is checked where)

* The model reaches Nucleon only through the Lab's MCP tools, signed in by the Lab with a **service** session (`channel: 'service'`, decided by the
  records from the service code; the Lab checks it and fails closed). That session can read and prepare; it cannot confirm or cancel.
* A person confirms in their own browser, signed in with the person staff access code, on `#/actions/<actionId>`. Confirm and cancel need: an
  `Origin` in `publicOrigins`; a JSON body; an `Idempotency-Key`; the **session's own csrf token** (`X-Nucleon-CSRF`, from `/api/session`); role staff
  (the owner may cancel only); not the AI Agent identity; not a service session.
* Role-level and shared: anyone holding the person staff access code can confirm. The Lab and anything holding only the Lab's configuration cannot.
* A request opened from a confirmed action is decided only by the owner (staff-within-authority on it is 409 `OWNER_REVIEW_REQUIRED`).

## 5. Where an action id comes from

`prepareRequest` mints it in Nucleon: `act_` + 16 lowercase hex digits (`uid('act')`), stored with the frozen proposal (customer, invoice, dates, days,
the assistant's drafted reason, the evidence version it rests on) in the `actions` table. The model never chooses it; the card and the page carry it,
and the card builds `http://127.0.0.1:18631/#/actions/<actionId>` only if the whole URL fits the contract with LibreChat patch 0003.

## 6. Duplicate prevention

One live proposal per invoice (a partial unique index), so a new proposal supersedes the previous one in the same transaction; no proposal while a
request is open on the invoice; confirming is one transaction, keyed by the action id (`<actor>:create:action:<id>`), so two presses, two tabs or a
retry make one request and the others replay it; any invoice, payment, allocation, due-date or note change for the customer invalidates the live
proposals (the evidence version is per customer).

## 7. Lost responses and recovery

The page keeps one `Idempotency-Key` per action until it gets an answer, and after a network error or a 5xx reads the action again: submitted → it
says so; still proposed → "Try again" with the same key; unreachable → "Outcome uncertain", with "Check again". The assistant reads `actionStatus`.
A restart of the records keeps the actions (SQLite) but ends sessions: the person signs in again and the deep link survives the sign-in. A records
restart with random service codes changes them: the Lab signs in again when the records answer 401, reading the new codes from the log (or, with fixed
`serviceCodes`, nothing changes).

## 8. Checking the page without LibreChat

`deploy/action_page_check.py` starts a scratch records server on a free loopback port and drives the page in a headless Chromium (Playwright's cached
`chromium_headless_shell`, through a small DevTools client in `deploy/cdp_min.py`, standard library only). It signs in through a deep link, confirms
(triple click: one request), reloads, checks the owner's read-only view and cancel, a dropped request and a lost response with the same key, an
expired and a superseded proposal, a refusal after the records changed, a stale csrf token, and the AI Agent identity. It creates fictional records on
its own scratch database only.

## 9. LibreChat build, launch and rollback

All of this is the isolated `lc-cardtest` instance in `~/Developer/LibreChat-card-visibility-dev/nucleon-test/` (api on `127.0.0.1:3081`, its own
bind-mounted Mongo in `mongo-data/`). The **live** LibreChat on 3080 stays on `librechat:nucleon-card-v0.8.8-rc2`; nothing here touches it, `~/Developer/LibreChat`,
or the running Nucleon services on 8630/8631.

**Image.** `librechat:nucleon-card-v0.8.8-rc3-test` is LibreChat v0.8.8 with patches 0001-0003. Patch 0003 lets a card open only
`http://127.0.0.1:8631|18631/#/actions/act_<16 hex>` after a real click; the allow-list is a compile-time constant (`client/src/utils/nucleonLinks.ts`), so a
different origin needs a rebuild. To rebuild, follow the "rc3-test (patch 0003)" section of `~/Developer/LibreChat-card-visibility-dev/NUCLEON-PATCH.md`
(`docker build ... -t librechat:nucleon-card-v0.8.8-rc3-test .` from that repository, branch `feat/nucleon-confirm-link`).

**What was changed in `nucleon-test/` for this stack** (backup of the originals: `nucleon-test/backup-pre-phaseb-20261026-112817/`: `docker-compose.yml`, `librechat.yaml`, `.env`):

* `docker-compose.yml`: the `api` image is `librechat:nucleon-card-v0.8.8-rc3-test` (was `...-rc2`).
* `librechat.yaml`: the MCP server `nucleon-local-staff` (live Nucleon, 8630) is replaced by `nucleon-phaseb-staff` = `http://host.docker.internal:18630/mcp/`, bearer
  `${NUCLEON_PHASEB_STAFF_MCP_TOKEN}`; `mcpSettings.allowedAddresses` is `host.docker.internal:18630` only. So this instance cannot reach 8630.
* `.env` (mode 600): one new variable `NUCLEON_PHASEB_STAFF_MCP_TOKEN` = the scratch Lab's staff token (`~/Developer/nucleon-phaseb-test/config/staff-mcp-token`). Never print it.
* One test agent, "Nucleon PHASE-B TEST Staff (Qwen)" (LM Studio, `qwen3.5-35b-a3b`), created in the isolated Mongo by `nucleon-test/seed_phaseb_agent.js`
  (re-runnable; it deletes and recreates that one agent; the id is written to `agent-ids-phaseb.json`). Its tools, and only these:
  `findCustomers`, `customerOverview`, `invoices`, `prepareRequest`, `actionStatus` from `nucleon-phaseb-staff`.

**Which tools are on, and where.** `prepareRequest` and `actionStatus` are off by default in Nucleon. On the scratch workspace the owner turned them on (section 3;
this lives in the scratch database, so it is repeated after a fresh database). The scratch Lab then lists 16 staff tools (the 14 existing + these two) and 19 owner
tools (the existing 18 + `actionStatus`). In LibreChat the agent uses the five above; nothing that confirms, cancels or executes exists on any model-reachable surface.

**Launch the whole isolated environment.**

```
~/Developer/nucleon-phaseb-test/bin/phaseb start            # scratch records 18631 + Lab 18630 (loopback), configs in ~/Developer/nucleon-phaseb-test/config (mode 600)
cd ~/Developer/LibreChat-card-visibility-dev/nucleon-test
docker compose -p lc-cardtest up -d                          # mongo + api (rc3-test) on http://127.0.0.1:3081 ; LM Studio must be serving qwen3.5-35b-a3b on 127.0.0.1:1234
```

The test user is in `nucleon-test/test-credentials.txt`; the person who confirms signs in to `http://127.0.0.1:18631` with the scratch **staff access code**
(`accessCodes.staff` in `config/records.json`). On a first start of a new database, turn the two tools on as the owner (section 3).
Status: `phaseb status`. Stop: `phaseb stop` and `docker compose -p lc-cardtest stop api` (leave mongo alone, never `down -v`).
`phaseb` uses the Lab's interpreter from `~/Developer/nucleon-local/venv` read-only and the checkout in `PHASEB_REPO` (default `~/Developer/Project-Nucleon-phaseB`).

**Roll lc-cardtest back to the rc2 setup.**

```
cd ~/Developer/LibreChat-card-visibility-dev/nucleon-test
cp -p backup-pre-phaseb-20261026-112817/{docker-compose.yml,librechat.yaml,.env} .
docker compose -p lc-cardtest up -d --force-recreate api
```

The Phase B agent stays in the isolated Mongo (harmless; its tools are unavailable without the server). The rc2 and `-poc` images are never retagged.

## 10. Rollback of the Nucleon side

1. The owner turns `prepareRequest` and `actionStatus` off (Setup → Agent tools): they leave every registry, MCP included.
2. Stop the isolated records and Lab processes; delete the isolated database, store and configs (they hold only fictional data and fictional codes).
3. The running records and Lab (8631, 8630) were never touched. If this branch were ever deployed over them: a records restart creates new random
   service codes unless fixed, the Lab must be deployed with it (it reads the `service code` log lines), and requests already opened from an action are
   ordinary requests that follow the normal withdraw/decide paths. The `actions` table is additive and inert without the tool.

## 11. End-to-end browser acceptance, 26 October 2026

Run on this isolated stack (Playwright, Chromium 1440x900, fresh profile, `autoExpandTools` unset), two real Qwen runs (prepare, then status). Evidence:
`~/Developer/nucleon-phaseb-test/evidence/` (`result.json`: 63 checks, 61 pass; the two non-passes are explained there: Qwen did not call `customerOverview` in the
live run, so that card was checked on a saved conversation, and one check of mine compared the request version, which legitimately rises when the records change).

* S1 success: Qwen called `prepareRequest`; the card opened without a click (and, as the model also wrote the inline marker, a second copy sits in the message body);
  "Review and confirm in Nucleon" inside the card opened `http://127.0.0.1:18631/#/actions/act_a509cd4429ff8951` in a new tab; staff sign-in kept the deep link; the page showed
  customer, DEMO-202, 6 Nov to 16 Nov (10 days), the reason read-only, the completeness warning and "does not approve"; Submit created one request (awaiting the owner);
  the status question made Qwen call `actionStatus` and the card read SUBMITTED FOR OWNER REVIEW; both cards persist after a reload.
* S2 cancel, S3 records changed (RECORDS_CHANGED, invalidated, no request), S4 duplicates (double click, same key, new key: one request), S5 model independence
  (request fields equal the action params; a records change re-prepares the open request deterministically, no model, fields unchanged), S6 security
  (401 / PERSON_REQUIRED / CSRF_REQUIRED / ORIGIN_REQUIRED / foreign Origin / owner 403 / OWNER_REVIEW_REQUIRED): all as designed.
* Not exercised in a browser: the patch refusing a card URL to a non-allow-listed origin (covered by the 69 unit tests in the patch).
