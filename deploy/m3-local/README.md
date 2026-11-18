> **Copy for the repository.** This is the README of the maintainer's local runtime folder `~/Developer/nucleon-local`, and `bin/` and `lib/` are copies of its scripts. The runtime's `config/` (codes, tokens, passwords), `data/` (databases), `backup/` and `demo-launcher.html` are **not** included and must never be committed. The scripts read them at run time. See `integrations/librechat/README.md` for the LibreChat side.

# Local Nucleon dev environment

Independent, fictional-data copy of the Nucleon records backend and Lab (MCP) on this Mac, wired to the existing LibreChat.
Nothing here touches M6 (`https://nucleon.dracooz.top`). Repo code is used unchanged from `~/Developer/Project-Nucleon`
(branch `explore/agent-coordinator-20261019`, HEAD 574fe1c; code equals the commit deployed on M6, 0d54e9f).

## Architecture

```
LibreChat (docker, 127.0.0.1:3080)
  agent "Nucleon LOCAL Staff (Qwen)" --LM Studio qwen3.5-35b-a3b (host :1234)
  MCP nucleon-local-staff  --http://host.docker.internal:8630/mcp/  (Bearer, staff)
        |                      (Lab publicOrigins lets this Host header through)
        v
Lab / MCP server      127.0.0.1:8630   python -m lab  (venv, py3.12), model: mock, never calls a model
        | HTTP, signs in with recordsCodes
        v
Records backend       127.0.0.1:8631   prototype/server.py (stdlib), agentMode mock, sampleData (fictional)
        v
SQLite  data/records.sqlite3     (Lab keeps its own data/lab.sqlite3)
```

Existing LibreChat servers `nucleon-staff` / `nucleon-owner` still point at the REMOTE M6 and are unchanged.
There is deliberately no owner connection to the local Lab in LibreChat (an owner token exists in the Lab config for tests only).

## Paths, ports

| What | Where |
|---|---|
| Root (L) | `~/Developer/nucleon-local` |
| Records config / Lab config (chmod 600, contain the secrets) | `config/records.json`, `config/lab.json` |
| Databases | `data/records.sqlite3`, `data/lab.sqlite3` |
| Logs / pids | `logs/records.log`, `logs/lab.log` / `run/*.pid` |
| venv (uv, Python 3.12, `lab/requirements.txt`) | `venv/` |
| Control script | `bin/nucleon-local` |
| MCP checks | `tests/mcp_check.py` (writes `tests/last_outputs.json`) |
| Backups of LibreChat `.env` / `librechat.yaml` before the edit | `backup/` |
| Ports | records 127.0.0.1:8631, Lab 127.0.0.1:8630 (both loopback only) |

Note: the records server prints its access codes into `logs/records.log` at start-up even when they are configured; the log dir is chmod 700.

## Commands

```
~/Developer/nucleon-local/bin/nucleon-local start|stop|restart|status|logs [n]|test-mcp
```
nohup + pid files; Records and Lab do not start at login (only the two public-access agents below use launchd). Optionally `ln -s` the script into `~/.local/bin`.

## Demo tools (27 Oct 2026)

| Command | What it does |
|---|---|
| `bin/demo-reset` | Stops Nucleon, keeps a copy of the current database in `backup/pre-reset-<time>.sqlite3`, reseeds the clean fictional ADA demo data at policy v0 (advisory), and starts Nucleon again. It then checks that Qwen is loaded in LM Studio with a 32,768-token context, and prints the fix command if it isn't. Run it after any rehearsal and before the live demo. |
| `bin/demo-launcher [--no-open]` | Writes `demo-launcher.html` (mode 600; it **contains the codes and passwords**, so never share or screen-share it). The page has a login link and copy buttons for LibreChat, Nucleon Staff and Nucleon Owner, plus "Copy password" and "Copy invite message" for each group member account. |
| `bin/team-accounts [--count N]` | Creates the group member LibreChat accounts `member<N>@nucleon.local`, role USER. Each password is set once and stored in `config/team-members.json` (mode 600); it never changes on later runs. The accounts get view access to "Nucleon ADA Staff (Qwen)". Uses `lib/librechat-team-accounts.js` inside the LibreChat container. |

**Remote access (Tailscale Serve, tailnet and its shares only, never Funnel):**
- **Addresses:** `https://nucleon.tail492813.ts.net` goes to LibreChat 3080, and `https://nucleon.tail492813.ts.net:8443` goes to Records 8631.
- **CLI:** `/Applications/Tailscale.app/Contents/MacOS/Tailscale serve status`, and `serve reset` to remove the forwards.
- **Config that must match the address:**
  - `config/records.json` `publicOrigins` includes the tailnet origin; this makes Nucleon's cookies Secure.
  - `config/lab.json` `recordsPublicUrl` is the tailnet origin, so the card buttons open it.
  - LibreChat image rc4-tailnet allows that origin for card links.
- **Group members:** they join through a Tailscale share of this Mac. Their guide is https://claude.ai/artifact/7x6HdHuHQAMSVxVemQAuVs (private until the owner shares it).

**Public access (Cloudflare Tunnel, 31 Oct 2026):** the PoV is public at `https://nucleon.dracooz.top` (Records) and `https://creditease.dracooz.top` (LibreChat), behind Cloudflare Access. Full description, rollback and security notes: `docs/DEPLOYMENT.md`, section "Public access for the PoV". Files here:

| File | What it is |
|---|---|
| `launchd/com.nucleon.cloudflared.plist` | LaunchAgent that keeps `cloudflared tunnel run --token-file config/cloudflared-token` running (log: `logs/cloudflared.log`). Copy to `~/Library/LaunchAgents/`, then `launchctl bootstrap gui/$(id -u) <file>`; `launchctl bootout gui/$(id -u)/com.nucleon.cloudflared` makes the services loopback-only again. |
| `launchd/com.nucleon.caffeinate.plist` | LaunchAgent that runs `/usr/bin/caffeinate -dimsu` so the Mac does not sleep while the tunnel is up. |
| `bin/pov-check [--local]` | Read-only PASS/FAIL line per check, exit 1 on any FAIL: Records 8631 and Lab 8630 answer 401, LibreChat 3080 answers 200, Qwen loaded at context 32768, cloudflared running and registered within 24 h, caffeinate running, and both public hostnames answer from the edge (200, 302 or 303). `--local` skips the two edge checks. |

**LM Studio:** Qwen must run with a 32,768-token context. At the default 8,192 the agent loses its own tool results and loops; see `docs/KNOWN-LIMITATIONS.md` L-002 in the Nucleon repo.
- **Load it with:** `~/.lmstudio/bin/lms load qwen3.5-35b-a3b --context-length 32768 --identifier qwen3.5-35b-a3b -y` (a manual load has no idle unload).
- **Saved default:** 32,768 is saved as the model's default for on-demand loads, in `~/.lmstudio/.internal/user-concrete-model-default-config/mlx-community/Qwen3.5-35B-A3B-4bit.json`.

**Don't script against LibreChat's API with curl or urllib.** One such call bans the user and the Docker gateway address for 2 hours, which locks out every login from this Mac. To clear it, delete the `ban:*`/`BANS:*` documents in the Mongo `logs` collection, then restart the `LibreChat` container. Use Playwright with in-page `fetch` instead.

## Reset the local DB

**For the ADA demo, use `bin/demo-reset` (above).** The steps below are the older generic reset with the original sample fixtures.


`bin/nucleon-local stop; rm -f data/*.sqlite3*; bin/nucleon-local start` (sample data is re-created from `prototype/fixtures.json`).
Reset also clears Lab sessions/assessments. Fixtures: C-DEMO-01 Harbour Demo Supplies (DEMO-101 AUD 1,250.00 due 20 Oct),
C-DEMO-02 Harbour Demo Logistics (DEMO-201 AUD 480.00 due 9 Oct, DEMO-202 AUD 2,100.00 due 6 Nov), no payments, asOfDate 2026-10-16.

## Rotate local tokens

1. Edit `config/lab.json` (`mcpTokens`: new `secrets.token_urlsafe(32)` values; keep one "staff", one "owner"). To change access codes, change them in BOTH `config/records.json` `accessCodes` and `config/lab.json` `recordsCodes`.
2. Put the new staff token in `~/Developer/LibreChat/.env` as `NUCLEON_LOCAL_STAFF_MCP_TOKEN=...` (the "Local Nucleon dev" block at the end).
3. `bin/nucleon-local restart`, then `cd ~/Developer/LibreChat && docker compose up -d --force-recreate api`. (Never `down -v`.)

## LibreChat wiring

- `.env`: one line, `NUCLEON_LOCAL_STAFF_MCP_TOKEN`.
- `librechat.yaml`: server `nucleon-local-staff` (streamable-http, `http://host.docker.internal:8630/mcp/`, `requiresOAuth: false`, timeout 120000) and
  `mcpSettings.allowedAddresses: ['host.docker.internal:8630']`. LibreChat v0.8.8 blocks MCP URLs that resolve to private IPs
  (`packages/api/src/auth/domain.ts`: `isDomainAllowedCore` -> `isSSRFTarget`/`resolveHostnameSSRF`; documented in `librechat.example.yaml`, `mcpSettings`).
  `allowedAddresses` exempts exactly that host:port. `allowedDomains` was NOT used: setting it activates an allowlist and would block the remote M6 servers.
- Agent "Nucleon LOCAL Staff (Qwen)": qwen3.5-35b-a3b via LM Studio, temperature 0.2, same instructions as the other Nucleon agents,
  10 read-only tools of `nucleon-local-staff` (findCustomers, customerOverview, invoices, ownerContext, cases, caseDetails, whereIs, compareExtension, workQueue, listRequests).
  No assessRequest (it writes), no prepare/propose tools.

## Tests and results (2026-10-25)

- Records: `cd ~/Developer/Project-Nucleon && python3 -m unittest discover -s prototype -p 'test_*.py'` -> 687 tests OK.
- Lab: `venv/bin/python -m unittest discover -s lab/tests -q` (run from the repo root) -> 279 tests OK. Both leave ignored `__pycache__` dirs in the repo; remove them (`PYTHONDONTWRITEBYTECODE=1` avoids them).
- MCP: `bin/nucleon-local test-mcp` -> 33 checks, 0 failed: 401 without/with wrong token, 421 on a foreign Host, staff 14 tools, owner 18 tools,
  owner-only tools and `openRequest`/`answerConcern` rejected for staff, unknown tool -> JSON-RPC -32602, read-only calls return the fixtures.
- Never run `deploy/ui_check_server.py` against these DBs (it deletes the DB at its path).

## Differences from M6

- Data: 2 fictional customers / 3 invoices (asOf 2026-10-16) instead of the QA data (C-0022, "QA Sameday ...", requests).
  No requests or cases exist, so `assessRequest` (marked "read" but WRITES an assessment version) was not exercised here.
- Mock model in Lab and records (`agentMode: mock`); the MCP layer never calls a model anyway.
- No Caddy / public URL / TLS, no launchd, no web UI build or demo console (`demo` off). Lab `rootPath` is "" (M6: `/lab`), so the MCP URL is `/mcp/`, not `/lab/mcp/`.
- Python 3.12 venv for the Lab; the records server runs on system python3 (3.9.6), as in the test baseline.
- Lab accepts the Host `host.docker.internal:8630` via `publicOrigins`; everything else non-loopback gets 421.

## Findings that matter for prompts (record completeness)

- `customerOverview` is the only tool that states completeness: `balanceLine` = "Owed now AUD 2,580.00 (worked out; invoices not confirmed complete; payments not confirmed complete): ...", plus `completeTo: {invoices: null, payments: null}`.
- `invoices` carries no completeness wording; it has per-invoice `amountText` "AUD 480.00 (stated)", `totalText` "The original invoice amount is not recorded.", `allocationsText` "No payment is allocated to this invoice."
- "No payments" is expressed only as `payments: []` and `notAllocated` "AUD 0.00 (as recorded, received, not matched to an invoice)" in customerOverview; there is no sentence "no payments recorded".
  A prompt asking for "recorded payments" must make the agent call customerOverview, not only invoices.
- Unknown customer: `findCustomers` -> `count 0, matches [], similar [...]` (not an error); `customerOverview`/`invoices` -> tool error INVALID_ARGUMENT "No customer matches ...".

## Remaining gaps / M6 handover

- Not deployed anywhere; M6 is untouched. A targeted M6 handover would need: (1) nothing from the repo (code is identical to 0d54e9f);
  (2) on M6, only what differs: real data and its tokens/codes, `rootPath` `/lab`, Caddy route, launchd units; (3) in LibreChat, a new MCP server entry pointing at the M6 URL (already exist: `nucleon-staff`/`nucleon-owner`) and, if the new agent's prompt/tool set is wanted against M6, a copy of the agent with `_mcp_nucleon-staff` tool ids.
  Prompt/instruction changes arising from the completeness findings belong in the agent instructions (LibreChat) or Lab tool text (repo), which is a separate task.
- Owner flows (prepareDecision etc.) and `assessRequest` persistence are untested locally (owner not wired to LibreChat; no request fixture).
- No autostart: services stop on reboot; run `bin/nucleon-local start`.
- Local qwen runs are with the shared LM Studio model; latency depends on it.
