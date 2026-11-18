# Home-server test deployment

Recorded: 16 October 2026, Australia/Sydney. Updated the same day for the structured-brief release (prompt extension-v0.3, brief format brief-v2), and on 17 October for the redesigned interface and the demo console.
Status: a test deployment of the fictional prototype for the team and the Week 7 demonstration, not a production system. No real customer data. Consistent with D001 (local/home-server first, no cloud).

## Public access for the PoV (Cloudflare Tunnel + Access), 31 Oct 2026

Status: code, assets and image are ready (slice S4, code part); the switch on the M3 is a runtime step, done by the coordinating session (checklist at the end of this section). Everything below that follows this section (Caddy, `local.nucleon.prototype`, port 8620, "Address and access") describes the **old M6 home server, retired on 30 Oct 2026**. It is kept as history only. The hostname `nucleon.dracooz.top` no longer points at M6: it now points at the tunnel described here, and so serves the M3 Records. Decision D6 in `docs/product/POV-IMPLEMENTATION-PLAN-20261030.md`; Tailscale is retired.

### Architecture

```
tester browser ──HTTPS──► Cloudflare edge  (proxied DNS, Cloudflare Access: email one-time code)
                              │  Access checks the login first; only then is the request sent through the tunnel
                              ▼
                    cloudflared on the M3  (tunnel "nucleon-m3", outbound connections only, no router port)
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
 https://nucleon.dracooz.top        https://creditease.dracooz.top
 → http://127.0.0.1:8631            → http://127.0.0.1:3080
   Records (prototype/server.py)      LibreChat (docker, api container)
                                        │ MCP http://host.docker.internal:8630/mcp/ (Bearer)
                                        ▼
                                      Lab 127.0.0.1:8630 → Records 8631      (Lab is NOT published)
```

- **Nothing listens on a public address.** Records, Lab and LibreChat stay bound to `127.0.0.1`; the only way in is the tunnel, which `cloudflared` opens from the Mac to Cloudflare.
- **Lab (8630) has no hostname.** LibreChat reaches it over the Docker gateway as before.
- **LM Studio** (127.0.0.1:1234) is local only: Qwen `qwen3.5-35b-a3b`, context 32,768.

### What is configured on Cloudflare (dashboard, Zero Trust)

| Item | Setting |
|---|---|
| Tunnel | `nucleon-m3`, remotely managed (ingress is kept on Cloudflare, so the Mac only holds the token) |
| Public hostname 1 | `nucleon.dracooz.top` → service `http://127.0.0.1:8631` |
| Public hostname 2 | `creditease.dracooz.top` → service `http://127.0.0.1:3080` |
| DNS | two proxied (orange cloud) CNAME records, `nucleon` and `creditease`, → `<tunnel id>.cfargotunnel.com`. `nucleon` used to be an A record to M6 (DNS only, see the old "Topology" below) and was replaced |
| Access application | "Nucleon PoV", self-hosted, covering both hostnames, identity provider One-time PIN (email code) |
| Access policy | Allow, include "Emails" = the tester allow-list (the PoV participants and the product team). Nobody else gets a code |
| Service token (optional) | for automated checks: a token plus a "Service Auth" policy on the same application. Export `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` for `bin/pov-check` so the edge checks reach the origin (see below). Create it only if needed; never commit it |
| Tunnel token | on the Mac only: `~/Developer/nucleon-local/config/cloudflared-token` (mode 600). Not in Git |

The Cloudflare proxy has a 100 s timeout per request; the Lab/Records calls and a Qwen turn are streamed or short, but a single request that is silent for more than 100 s would be cut.

### Nucleon configuration changes (files on the Mac, not in Git)

`~/Developer/nucleon-local/config/records.json`:
- `publicOrigins`: add `"https://nucleon.dracooz.top"` (keep `"http://127.0.0.1:8631"`). An https origin makes the Records cookies `Secure` and the Origin check accepts writes from that host only.
- `assistantUrl`: `"https://creditease.dracooz.top/c/new?agent_id=<the ADA Staff agent id>"` (it is currently `http://127.0.0.1:3080/c/new?agent_id=...`; the id stays).

`~/Developer/nucleon-local/config/lab.json`:
- `recordsPublicUrl`: `"https://nucleon.dracooz.top"`. Lab refuses any value outside its four contract origins (`lab/config.py`); the card button opens `<recordsPublicUrl>/#/actions/act_<16 hex>`.
- `publicOrigins` for Lab stays `http://host.docker.internal:8630` (the Host header LibreChat sends); Lab is not on the tunnel.

Restart the services afterwards: `~/Developer/nucleon-local/bin/nucleon-local restart`.

Code (this commit series): `lab/card.py` `CONFIRM_ORIGINS` and `lab/config.py` accept `https://nucleon.dracooz.top`; the LibreChat client allow-list (patch 0005) has the same origin. **Both sides must list it**, otherwise the card has no button (Lab) or the click does nothing (client).

### LibreChat changes

- **Image:** `librechat:nucleon-card-v0.8.8-rc5-cf` (patches 0001-0005, built from `a130836` of `~/Developer/LibreChat-card-visibility-dev`, branch `feat/nucleon-confirm-link-cloudflare`). Set only `services.api.image` in `~/Developer/LibreChat/docker-compose.override.yml` (the example is `integrations/librechat/docker-compose.override.yml.example`) and recreate only `api`: `docker compose up -d --no-deps --force-recreate api`. Back up the override and `.env` first.
- **`.env` keys** (`integrations/librechat/librechat.env.example`; names checked against v0.8.8):

| Key | Value | Why |
|---|---|---|
| `DOMAIN_CLIENT` | `https://creditease.dracooz.top` | the public address; used by the same-origin guard on the login endpoints and for generated links |
| `DOMAIN_SERVER` | `https://creditease.dracooz.top` | same; also makes the session cookies `Secure` (HTTPS host, `NODE_ENV=production`) |
| `TRUST_PROXY` | `1` | hop count for Express `trust proxy` (`Number(TRUST_PROXY) \|\| 1`, so 1 is also the default). The ban logic uses `req.ip` |
| `ALLOW_REGISTRATION` | `false` | nobody can sign up through the public hostname |
| `ALLOW_SOCIAL_REGISTRATION` | `false` | same for social sign-in (already off; set explicitly) |

- **Remove the old Tailscale reasoning:** the previous note "DOMAIN_CLIENT/DOMAIN_SERVER stay `http://localhost:3080` on purpose" no longer holds. The public address has to be there, because the login endpoints compare the browser's Origin with it.
- **Loopback login:** with Secure cookies, `http://127.0.0.1:3080` should still work in Chrome (it treats loopback as a secure context) but may not in Safari or Firefox. If local use matters, add `SESSION_COOKIE_SECURE=false`; the cost is the cookie flag only (the public side is still HTTPS). Test it in the runtime step.
- **Registration off:** the existing accounts (Owner, Staff, `member<N>@nucleon.local` from `bin/team-accounts`) keep working. New testers are created by an admin, not by sign-up.

### Why `TRUST_PROXY` matters

LibreChat's ban logic (`BAN_VIOLATIONS`, `api/server/middleware/checkBan.js`) and its rate limiters key on `req.ip`. Express computes `req.ip` from `X-Forwarded-For` only as far as `trust proxy` allows. Behind the tunnel every request reaches LibreChat from `cloudflared` on the Docker gateway; if the proxy were not trusted, `req.ip` would be that one address for all testers, and one violation (a non-browser request, a rapid burst) would ban **everybody**, including the owner. With one trusted hop, `req.ip` is the visitor address that Cloudflare put in `X-Forwarded-For`, so a violation bans that tester's IP only. Do not raise it above 1: the path has exactly one proxy in front of LibreChat (cloudflared), and a higher value lets a visitor forge the address with their own `X-Forwarded-For`. Acceptance test (plan S4): a deliberate non-browser request from one tester IP bans that IP only.

### LaunchAgents

Files in `deploy/m3-local/launchd/`, copied to `~/Library/LaunchAgents/` and loaded with `launchctl bootstrap gui/$(id -u) <plist>`:
- `com.nucleon.cloudflared.plist`: RunAtLoad, KeepAlive; `/Users/unitylht/Developer/nucleon-local/cloudflared/cloudflared tunnel run --token-file /Users/unitylht/Developer/nucleon-local/config/cloudflared-token`; stdout and stderr to `~/Developer/nucleon-local/logs/cloudflared.log`. The token is read from the file; it is not on the command line, so `ps` does not show it.
- `com.nucleon.caffeinate.plist`: `/usr/bin/caffeinate -dimsu`. Without it the Mac sleeps and the tunnel drops.
- Records and Lab are still started with `bin/nucleon-local start` (nohup, no launchd): after a reboot, start them yourself, then check.

### `bin/pov-check`

`deploy/m3-local/bin/pov-check` (read-only; `--local` skips the edge checks) prints one PASS or FAIL line per check and exits 1 on any FAIL: Records 8631 answers 401, Lab 8630 answers 401, LibreChat 3080 answers 200, Qwen loaded at context 32768, cloudflared running, cloudflared log shows `Registered tunnel connection` within 24 h, caffeinate running, and both public hostnames answer from the edge with 200, 302 or 303 (5xx or no answer = tunnel down).
- **Limit of the edge check:** Access answers with a 302 to its login page before the request reaches the tunnel, so without a service token an edge 302 does not prove the tunnel is up. The "cloudflared registered" line is what detects a down tunnel. With `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` set, the request passes Access and a dead tunnel shows as a 5xx.
- **24 h window:** the registration line is written when `cloudflared` connects. A tunnel that has stayed connected for more than a day shows a FAIL there; `launchctl kickstart -k gui/$(id -u)/com.nucleon.cloudflared` reconnects it and logs a fresh line.

### Rollback

- **To loopback only:** `launchctl bootout gui/$(id -u)/com.nucleon.cloudflared`. The hostnames then return a 502/530 from the edge; nothing else on the Mac changes. (Or disable the Access application, which is the opposite: it would open the tunnel without a login, so do not.)
- **LibreChat image:** set `services.api.image` back to `librechat:nucleon-card-v0.8.8-rc4-tailnet` (still local), restore the `.env` and recreate `api`. The old tailnet card link no longer works anyway (Tailscale retired).
- **Config:** restore the `records.json` and `lab.json` backups taken before the edit. Each side is one commit (Nucleon, LibreChat dev repo).

### Security notes

- **Access is the gate.** Both hostnames are behind Cloudflare Access with an email allow-list and a one-time code; the apps (LibreChat login, Records access codes) are a second layer. Keep the allow-list to named testers and review it after the sessions.
- **Registration is off** in LibreChat (`ALLOW_REGISTRATION=false`, `ALLOW_SOCIAL_REGISTRATION=false`). Tester accounts are created by an admin with strong passwords; rotate the Records access codes before opening.
- **Secure cookies behind HTTPS:** Records sets `Secure` once `publicOrigins` holds an https origin; LibreChat sets it from the https `DOMAIN_SERVER`. Cookies are `HttpOnly`, and Records' are `SameSite=Strict`.
- **Origin checks:** Records only accepts writes whose Origin is in `publicOrigins`; LibreChat's login endpoints compare against `DOMAIN_CLIENT`/`DOMAIN_SERVER`. The card link is limited to the exact `https://nucleon.dracooz.top/#/actions/act_<16 hex>` form (no query, no userinfo, no other host) by both Lab and the client, and needs a live user click.
- **TRUST_PROXY=1** so a violation bans one visitor and not every tester (section above).
- **Not exposed:** Lab/MCP (8630), LM Studio (1234), MongoDB and the other LibreChat containers have no hostname and no published port beyond loopback.
- **Secrets:** the tunnel token, the Cloudflare API token and the service token are files or environment values on the Mac only. This document, the plists and the examples contain none.
- **Data:** fictional data only. Testers must not enter real customer data.

### Runtime steps (not done by the code change; the coordinating session does them)

1. Back up `records.json`, `lab.json`, LibreChat `.env` and `docker-compose.override.yml`.
2. Edit the Nucleon configs as above and `nucleon-local restart`.
3. Edit the LibreChat `.env`, switch the image to rc5-cf, recreate `api` only.
4. Install and load the two LaunchAgents; remove the old Tailscale Serve forwards and the retired M6 leftovers (plan S4).
5. `bin/pov-check` all PASS; then the external test from an outside network (Access login, Northside, Harbourline, Lakeside, evidence link, the TRUST_PROXY ban test).

## Address and access

- URL: **https://nucleon.dracooz.top**
- Login: separate STAFF, OWNER and OPERATOR (demo console) access codes. They are generated at every service start and rotate on restart, crash recovery or redeploy. They are never committed and are shared privately.
- Get the current codes on the server: `~/srv/nucleon/bin/nucleonctl codes` (prints only the codes from the latest start).
- One browser can stay signed in as staff, owner and console at once; the buttons at the top switch roles. Sessions end when the service restarts; sign in again with the new codes. Saved records remain.

## Topology

```
browser ──HTTPS──► router :443 ──► Caddy (LaunchAgent local.rp.caddy, Let's Encrypt)
                                      │  site nucleon.dracooz.top
                                      ▼
                    127.0.0.1:8620  prototype/server.py   (LaunchAgent local.nucleon.prototype, one process)
                                      │  OpenAI-compatible chat completions, no credential
                                      ▼
                    127.0.0.1:1236  existing home gateway (loopback, no token) ──► LM Studio 127.0.0.1:1234
                                                                                    model loaded as "gemma-rp"
```

- **DNS:** Cloudflare A record `nucleon`, DNS only (grey cloud), pointing to the same address as the other dracooz.top hosts. An orange-cloud proxy would add a 100 s timeout and block Python clients.
- **Backend binding:** the backend binds loopback only. The LAN address on port 8620 is refused.
- **Allowed write origin:** `https://nucleon.dracooz.top` (`publicOrigins`), plus loopback for local use. Any other Origin gets 403, including `http://nucleon.dracooz.top` and DNS-rebinding hosts.
- **Session cookie:** `HttpOnly; SameSite=Strict; Secure`.
- **Caddy site file:** `~/.config/caddy/sites/nucleon.caddy`, a copy of `deploy/nucleon.caddy`. It is imported by the main Caddyfile. `~/Documents/aiRP/bin/caddy-setup.sh` now also writes that import line, so regenerating the main config keeps the site.
- **Caddy access log:** `~/Library/Logs/nucleon/caddy-access.log`.

## Model

- **Model:** `gemma-4-26b-a4b-it-heretic-zh-rp` (publisher wwlwwl, Gemma 4 26B-A4B mixture-of-experts, GGUF Q4_K_M), the model already loaded on the server, with a 65,536-token context.
  - LM Studio lists it under the identifier `gemma-rp`. Until 2026-10-17 the identifier was `qwen2-rp`, so runs recorded before then show that name in their serving entry.
  - It is a community fine-tune: "heretic" means reduced refusals, and it is tuned for Chinese role-play. It is not Google's base instruction model.
  - It was used because it is the model the server already runs. It is not a team model selection.
- **Shared service:** SillyTavern and other clients share the same model. Requests queue, so a case can take longer while someone else is generating.
- **Failures:** if a call exceeds 120 s, or the model service is stopped (`rp stop`), the case falls back to the disclosed manual path (`aiStatus=failed`).
- **Settings:** in `~/srv/nucleon/config/production.json` (shape: `prototype/config.example.json`). No credentials are needed or stored.
- **Workspaces and sample data (branch `feat/setup-records-20261017`; deployed 18 Oct in `89b92d8`, see Earlier release: Slice 2).** The server no longer fills an empty database with the fictional sample. Each database holds one workspace, practice or real, and an explicit workspace always takes precedence over `"sampleData"`.
  - **The production database.** It is recorded as a **practice** workspace on first start (origin "migration"). Its sample and cases stay as they are, and the demo console stays available. This was checked on a copy on 18 Oct: the records document was unchanged, all 3 cases kept their status, and both cases waiting for the owner still had current evidence.
  - **`sampleData`.** Add `"sampleData": true` to `production.json` **only for this practice instance**. `nucleonctl isolate` copies that file, so fresh test databases then start as practice with the sample, as the deployed checks expect.
  - **Real data.** Never set `sampleData` in a config used for real records. A real workspace refuses the sample and has no console.
  - `production.json` got `"sampleData": true` at the 18 October deploy, and no other config change.

### Model access (recorded 20 October 2026, branch `explore/agent-coordinator-20261019`)

- **The shared site at `/` still runs `f95f50f`**, the records interface (E016), with its configuration unchanged. Since 20 October the exploration branch runs only as a separate preview under `/preview/` (see "Preview instance (agent-coordinator branch)" below; E019).
- **Implemented:** a single OpenAI-compatible chat-completions adapter (`prototype/model_adapter.py`). It supports native tools, strict JSON-schema output, per-task token limits and timeouts, and an optional bearer key read from the environment variable named by `apiKeyEnv`. The key is never stored in the config, Git, logs or records.
- **Tested:** against LM Studio on the home server only, through the loopback gateway at `127.0.0.1:1236` (above). On the branch, the coordinator's tasks use the same adapter: since 20 October evening the desk agent loop (`coordinator-v0.3`, native tools; `coordinator-v0.4` since 21 October), `interpret_statement`, `plan_needs` and `suggest`. Their live output was examined in `live_coordinator_check.py` (v0.1), the preview checks below, and `conversation_check.js --live` ([qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md); [PROMPTS.md](../PROMPTS.md), "Observed behaviour: coordinator-v0.3" and "Observed behaviour: coordinator-v0.4"; the v0.4 runs were on scratch servers only, before the preview deploy). All of it was the local model.
- **Intended, untested:** a hosted OpenAI-compatible endpoint, by configuration only (`baseUrl`, `model`, `apiKeyEnv`). No hosted endpoint has been connected or tested; the team decided on 19 October that none would be provided for this slice. Not established: whether a hosted endpoint accepts the schemas and the LM Studio-oriented settings (`extraBody`, the identity probe) as written, its latency and its output quality.
- **Other wire formats**, for example Anthropic's Messages API, would need a second adapter behind the same interface. None exists.
- **Data:** fictional only. A hosted model with real records needs the owner's confirmation of data handling first (Q08).

### A second inference machine (planned, not configured)

Recorded 21 October 2026. The team has an M3 Max MacBook Pro with 48 GB of memory, which could serve a model to the Mac mini. Nothing is configured, and no remote access is assumed: it would be reached on the local network only.

What the Lab would need from it:
- LM Studio or llama.cpp's server listening on the LAN interface, not only on localhost, with an OpenAI-compatible chat-completions endpoint and tool calling enabled;
- a fixed LAN address or hostname that the Mac mini can reach;
- a model served under a known id;
- then only a change of `model.baseUrl` and `model.model` in `~/srv/nucleon-lab/config/lab.json`, followed by `labctl restart`.

The records instances' own tasks reach the model through the home gateway at `127.0.0.1:1236` (their config's `model.baseUrl`). They would need the gateway's configuration, or their own `model` block, changed the same way. Their identity probe (`identityUrl`, `expectArch`) is written for this LM Studio.

A LAN endpoint is open to every device on that network. Whether to require a key there (`model.apiKey` can carry one) is not decided.

Whether a model on it is suitable must be established by actual memory and tool-use tests on scratch servers, not by its size. The tests are the Lab's scenario runner (`deploy/lab_conversation_check.js --live`) and the records' live checks (`deploy/conversation_check.js --live`, `deploy/live_coordinator_check.py`, `prototype/live_gemma_check.py`).

## Files on the server (outside Git)

| What | Where |
| --- | --- |
| Python runtime | `~/srv/nucleon/runtime/python-3.12.14` (python-build-standalone 20260924; system Python is 3.9) |
| Deployed code | `~/srv/nucleon/app` (git clone, detached at the deployed commit) |
| Config | `~/srv/nucleon/config/production.json` (canonical) → `service.json` (active copy) |
| Production database | `~/srv/nucleon/data/nucleon.sqlite3` (mode 600; directory 700) |
| Isolated test databases | `~/srv/nucleon/data/test-*.sqlite3` |
| Database backups | `~/srv/nucleon/backups/` (directory 700, files 600; taken automatically before every deploy) |
| Service log (contains access codes) | `~/Library/Logs/nucleon/service.log` (mode 600; directory 700) |
| Test reports and screenshots | `~/srv/nucleon/reports/` |
| Control script | `~/srv/nucleon/bin/nucleonctl` (copy of `deploy/nucleonctl`) |
| LaunchAgent | `~/Library/LaunchAgents/local.nucleon.prototype.plist` (generated from `deploy/local.nucleon.prototype.plist.template`; KeepAlive, RunAtLoad, umask 077) |

The code is deliberately outside `~/Desktop` and `~/Documents`: macOS privacy protection blocks launchd-started processes from those folders.

## Commands

```bash
~/srv/nucleon/bin/nucleonctl status        # launchd state, deployed commit, loopback + HTTPS health
~/srv/nucleon/bin/nucleonctl codes         # current STAFF/OWNER/OPERATOR codes
~/srv/nucleon/bin/nucleonctl restart       # restart (codes rotate; records persist)
~/srv/nucleon/bin/nucleonctl logs 50       # service log without the code lines
~/srv/nucleon/bin/nucleonctl deploy <sha>  # back up the production DB, fetch, check out, run the unit suite, restart
~/srv/nucleon/bin/nucleonctl backup        # consistent SQLite backup of the production DB into backups/
~/srv/nucleon/bin/nucleonctl clone-db <db-file> <name>   # consistent copy into data/test-<name>.sqlite3
~/srv/nucleon/bin/nucleonctl stop | start
```

The service starts at login and launchd restarts it after a crash. A pending model run is marked `interrupted` and re-run; a kill -9 during inference was verified.

**Testing without touching the demo data:**

- `nucleonctl isolate <name> [unreachable-model|truncated-model]` restarts the same service on `data/test-<name>.sqlite3`.
- The optional fault simulates an unavailable model or real-model output cut off by a tiny token limit.
- `nucleonctl production` restores the production config.

## Preview instance (agent-coordinator branch)

Recorded 20 October 2026, Sydney. A second, separate instance so the team can review branch `explore/agent-coordinator-20261019` in a browser (E019). It is not a release: the shared practice site at `/` still runs `f95f50f` and was not touched.

- **URL:** **https://nucleon.dracooz.top/preview/**. `/preview` redirects there with a 301.
- **Deployed commit:** `8084bee`. That is the branch with E018, the staff-question change (`c20e02d`), the path-prefix support (`124a343`) and the deploy change itself. Since 10:53 on 20 October: `f3dd129`, which fixes the three findings below ("Fix and re-check"). Since 11:04: `9cc6d75`, the day-limit guard ("Day-limit guard and re-check"). **Since 19:46: `65982b8`, the conversational desk (`coordinator-v0.3`, E020; "Conversational desk and verification" below). Since 02:26 on 21 October: `df10ab6`, situation, capabilities and prepared actions (`coordinator-v0.4`, E021; "Third slice (21 October)" below).**
- **Arrangement:**
  - A second launch agent, `local.nucleon.preview`, generated from the same template. It runs one process on `127.0.0.1:8621`.
  - Its files are in `~/srv/nucleon-preview/`:
    - `app`: a clone of the GitHub repository, detached at the deployed commit;
    - `config`: `production.json` → `service.json`;
    - `data/preview.sqlite3`: its own database, a practice workspace with the fictional sample (`sampleData`);
    - `backups` and `bin/nucleonctl`;
    - `reports`;
    - `runtime`: a symlink to `~/srv/nucleon/runtime`.
  - Log: `~/Library/Logs/nucleon-preview/service.log`. It holds the access codes.
  - Caddy, in the same site file (`deploy/nucleon.caddy`): `redir /preview /preview/ 301`, then `handle_path /preview/*` → `127.0.0.1:8621` with the prefix stripped. Everything else still goes to 8620.
  - Cookies are `nucleonp_staff`, `nucleonp_owner` and `nucleonp_operator`, with `Path=/preview` (config `cookiePrefix` and `cookiePath`). Browser storage keys are `nucleon-preview.*`.
    - Root cookies (`nucleon_*`, `Path=/`) also reach `/preview/`, but the preview ignores them.
    - Preview cookies never reach `/`.
  - `publicOrigins` is `https://nucleon.dracooz.top`. The demo console is enabled, with its backups in `backups/`.
- **Model:** live, through the same local Gemma gateway as production (`127.0.0.1:1236`; the log says `agent mode: live`). Production, the preview and other clients share it, so requests queue.
- **Access codes** rotate on every restart: `NUCLEON_BASE=~/srv/nucleon-preview NUCLEON_LABEL=local.nucleon.preview NUCLEON_LOGDIR=~/Library/Logs/nucleon-preview ~/srv/nucleon-preview/bin/nucleonctl codes`. The same prefix works with `status`, `logs 50` and `restart`. Put the variables on the command line, not in `export`: never run `~/srv/nucleon/bin/nucleonctl` (production) with them set.
- **Update:** `NUCLEON_BASE=~/srv/nucleon-preview NUCLEON_LABEL=local.nucleon.preview NUCLEON_LOGDIR=~/Library/Logs/nucleon-preview ~/srv/nucleon-preview/bin/nucleonctl deploy <sha>`. It backs up `preview.sqlite3`, fetches from GitHub (so the commit must be pushed first), checks out the commit, runs the unit suite and restarts.
- **Reset its data:** use the demo console on the preview (`/preview/`, OPERATOR code). It resets the preview's database only. It also clears the owner context and the threads (E018 ruling 1).
- **Production:** untouched. `nucleonctl status` still reports `f95f50f` on `data/nucleon.sqlite3`. `https://nucleon.dracooz.top/static/desk.js` gives 404, and a preview sign-in is not a sign-in at `/` (checked below).

### Verification (20 October 2026, 10:39–10:41 Sydney; live model; public URL)

A scratch Playwright script, not committed, signed in as the owner and as staff in separate browsers. Screenshots are in `~/srv/nucleon-preview/reports/preview-check-2026-10-20/` and show no codes. The case used was the sample's Harbour Demo Supplies, invoice DEMO-101: due Tue 20 Oct 2026, AUD 1,250.00 stated.

| # | Check | Result |
| --- | --- | --- |
| 0 | Codes read from the log (never printed); both roles signed in through the public URL; `agentMode` live | PASS |
| 1 | The owner's paragraph in the general thread gives an "understood" card about Harbour Demo Supplies, every line quoting the paragraph | PASS: 6 lines, 10.2 s |
| 1 | Confirm: the card shows "Confirmed", and the server agrees (owner-only, customer scope) | PASS |
| 2 | Staff type the request at `#/requests/new`; the view moves to the case thread | PASS: 2.4 s |
| 2 | The case settles `awaiting_owner`; no `needs_information`, no staff question | PASS: 15.1 s |
| 2 | Staff see none of the owner's words and no suggestion | FAIL as scripted, but the behaviour is correct (see below) |
| 2 | Staff get a questions card only when a question is addressed to them | PASS: none |
| 3 | Owner: the facts card names the invoice; "What you have said" holds the confirmed lines; cards in the order facts, context, questions, decision | PASS (3 checks) |
| 3 | "Turn them on" sets `GET api/suggestions` to `{on: true}`; with a question open, the suggestion is withheld | PASS (2 checks): 0 s, no model call |
| 3 | The answer "Up to 14 days this time" shows as Answered | PASS |
| 3 | The suggestion ends given, withheld or failed | PASS: **failed** after one model call (3.9 s; shown after 5.2 s) |
| 4 | The decision is recorded with the owner's date and reason, and the reply draft shows | PASS: approve Tue 3 Nov 2026 (the due date + 14 days, because no suggestion was given), 0.1 s |
| 4 | The "remember" text is kept as owner-only guidance from the decision | PASS |
| 5 | Staff ask "what does Harbour Demo Supplies owe?" and get an answer card whose amount matches `GET api/records` | PASS: AUD 1,250.00 Stated, 2.0 s |
| 6 | At 390×844, the desk list and the case thread fit the width | PASS (2 checks) |
| 7 | `/` serves the records interface; `static/desk.js` gives 404 at `/` and 200 at `/preview/` | PASS |
| 7 | The preview cookie (`nucleonp_owner`, `Path=/preview`, the only cookie) does not sign you in at `/`; storage is `nucleon-preview.role` | PASS |
| 7 | `/preview` → 301 `/preview/` | PASS |
| 8 | `GET api/suggestions/counters` (owner) | PASS: given 0, withheld 0, failed 1, accepted 0, changed 0, declinedAgainst 0 |
| | No JavaScript or console errors; no 4xx or 5xx responses in the pages | PASS (2 checks) |

**Result:** 25 of 26 checks passed.

**The one FAIL is the script's expectation, not the app.** The script expected staff to get no context card. But the sample's confirmed, staff-visible note ("Fictional relationship context: a regular customer. Any extension still needs owner approval.") gives staff a "What the owner shared" card. The staffq report records the same wrong expectation. A read-only probe of the staff payload for the case thread found:
- none of the owner's words;
- no questions and no `contextShown`;
- suggestion status `off`.

The staff payload does include the decision's reason in `context.decisions`.

**What the live model did (one run):**
- **Understood card** (2 model calls, 10.2 s): observed "Harbour Demo Supplies has struggled recently"; relationship "I have known them for years"; observed "They have an event next month" (until Mon 30 Nov 2026); expects "should recover"; guidance "I would consider a small extension"; constraint "I don't want their debt to increase for now".
- **Preparation:** 6 model calls with 5 tool calls (7.6 s), then the needs step (1 call, 5.0 s).
- **The owner's question** (kind `recommend`): "Do you want to grant the requested extension for invoice DEMO-101 until Tue 10 Nov 2026?" Why: "Needed to suggest; without it the suggestion is withheld."
  - The reason repeats the example in the `plan_needs` prompt word for word.
  - The question asks the owner for the decision itself.
- **The suggestion** failed after one call (3.9 s), showing "The agent could not form a suggestion." The server keeps only the status. The run record has no reply and no rejection reason, so why it failed is not established. The same sentence also appears in the facts card under "Worth checking".
- **The staff question** was routed as `owes` (1 call, 1.9 s).
- **Waits** were far below the 10–40 s expected: every agent step took 2–15 s.

**Left on the preview by the check** (fictional; the demo console's reset removes it):
- one confirmed owner statement (6 lines, owner-only);
- case `req_063b2e03af44a00f`, approved to Tue 3 Nov 2026 with its draft, its answer line and its "remember" line (case scope, owner-only);
- the staff turns in the general thread.

DEMO-101's due date is now Tue 3 Nov 2026. **Suggestions were left on.**

**Remaining limitations:**
- The effort comparison did not show fewer owner actions (S1 4→4, S2 5→6; [qa/EFFORT-COMPARISON.md](qa/EFFORT-COMPARISON.md)).
- Guide revision 4, for the Requests area, is pending. Revision 3 describes the old pages, which are at `#/cases` here.
- A hosted model is untested.
- Staff questions are rare with the live model, because the records conflict is not in the facts it is given.
- The two unbuilt §10 scenarios (re-asking an expired expectation; a staff fact that conflicts with an owner line) must not be claimed.
- This is one live run of one scenario. In it the suggestion failed and the question asked for the decision.

### Fix and re-check (20 October 2026, 10:53–10:56 Sydney; live model; public URL)

**The fix**, `f3dd129`, was pushed and then deployed with the preview's `nucleonctl deploy`. The deploy backed up `preview-20261020-105408.sqlite3` (1 case), ran the suite (344 OK) and restarted the service, so the codes rotated. Production still reports `f95f50f`.
- **`plan_needs`:**
  - The prompt now says what a need is, never to ask the owner whether to approve or decline, and to return an empty list when nothing is missing. It gives one good and one bad example question. Its `why` example is gone.
  - `classify_needs` drops a question that asks for the decision itself, and a need that repeats an example from the prompt. Each drop leaves a fixed check (PROMPTS.md, "Code-side guards").
- **The suggestion:**
  - A failed check now gives the owner a second fixed sentence, for example "The agent cited evidence that was not loaded."
  - The raw reason is kept for tuning as `suggestReason`, owner-only. It is in the suggest run's `suggestionStats`, or in `analysis.stats` when the check failed at preparation.
  - A cite without its id's prefix now names the loaded id, when exactly one matches.
- **The desk:**
  - The decision form says "The agent doesn't recommend an outcome." only while suggestions are off.
  - A failed suggestion is shown once, on its own line. It no longer also appears under "Worth checking".
- **Checks before the deploy:**
  - unit suite: 344 OK (338 before);
  - `desk_check.js` on a fresh mock server: 49/49, with one new check of the decision-form sentence;
  - a scratch probe on the same server: a case with nothing said and suggestions on shows "The agent could not form a suggestion. The agent named no evidence." once, and the form does not say the agent recommends no outcome;
  - `coordinator.py --print-prompts` matches PROMPTS.md's 12 blocks.

**Re-check** (10:55:38–10:56:01 Sydney). A scratch Playwright script, not committed, read the codes from the log and never printed them. Screenshots and `results.json` are in `~/srv/nucleon-preview/reports/preview-check-2026-10-20-2/` and contain no codes.
- **Setup:** `GET api/suggestions` was already `{on: true}`. The sample has only two customers, Harbour Demo Supplies (used on the first run) and Harbour Demo Logistics, so the re-check used Harbour Demo Logistics, invoice DEMO-201: due Fri 9 Oct 2026, AUD 480.00 stated, 7 days overdue.
- **The request:** staff typed "Hi, Harbour Demo Logistics here. Could we pay invoice DEMO-201 on 2026-10-30 instead?" on the desk, 21 days after the due date.
- **Preparation:** `awaiting_owner` after 15.9 s. The runner made 6 model calls (8.1 s), and the needs step made 1 (4.2 s). The only context was the sample's shared note `note_demo_03`; there was no owner statement about this customer.
- **The owner's question** (kind `recommend`, from the owner): "Regarding the 'newer customer since August 2026', what is the maximum number of days you would typically allow for an extension?" Why: "Knowing your typical threshold for new customers would help determine if a 21-day delay is acceptable."
  - It does not ask for the decision.
  - Its reason is not a prompt example.
  - No question was dropped.
- **The suggestion:** withheld at preparation, with no model call.
  - The owner answered "Up to 14 days this time". The suggestion was then **given** after 1 call (2.5 s; shown after 3.6 s): **approve, Fri 30 Oct 2026**, citing only the answer line (its full id).
  - Its sentence: "The suggestion is based on the provided guidance regarding the duration of the extension."
  - No reason was stored, because none was needed.
- **The page:** the decision form had no "doesn't recommend" sentence, before or after the answer. No failure line was shown.
- **Staff:** the staff payload has suggestion status `off`, no suggest run and no `suggestReason`.
- **Errors:** no JavaScript or console errors, and no 4xx or 5xx responses.
- **Not exercised live:** the suggestion was given at the first attempt, so the failure reason and the bare-cite rule have not been seen on the live model. Only the unit tests and the mock probe cover them.
- **Finding:** the given suggestion approves 21 days while citing the owner's "Up to 14 days this time". Code checks that a cite was loaded, not that the suggestion agrees with it. The suggestion is advisory and not evaluated (E017), and this is one run.

**Left on the preview by the re-check:** case `req_b1819e749212286d` (DEMO-201), `awaiting_owner` with its suggestion. It is not decided. Its answer line is case-scoped and owner-only. The staff turn is in the case thread. Suggestions are still on.

### Day-limit guard and re-check (20 October 2026, 11:04–11:07 Sydney; live model; public URL)

**The guard**, `9cc6d75` (prompt `coordinator-v0.2`), was pushed and deployed with the preview's `nucleonctl deploy`. The deploy backed up `preview-20261020-110459.sqlite3` (2 requests), ran the suite (346 OK) and restarted the service, so the codes rotated. `status` reports `9cc6d75`, with loopback 200. The public `/preview/` returns 200. Production still reports `f95f50f`: `/` returns 200 and `/static/desk.js` 404s there.
- **What changed:**
  - The server reads a limit from each loaded answer or guidance line of this case, or of this customer, whose quote says "up to N days".
  - An `approve` dated later than the current due date plus that limit is withheld. The owner sees "The agent could not form a suggestion. The suggested date goes beyond the days you allowed."
  - The `suggest` prompt says never to suggest a date beyond a limit the owner stated (PROMPTS.md, "Changes from v0.1").
- **Checks before the deploy:**
  - unit suite: 346 OK. Two tests are new: the guard's bounds, and a server test where the mock approves 21 days against "Up to 14 days this time" and is withheld with the new sentence;
  - `desk_check.js` on a fresh mock server: 49/49;
  - `coordinator.py --print-prompts` matches PROMPTS.md's 12 blocks.

**Re-check** (11:06:52–11:07:15 Sydney). It used the scratch Playwright script of the last re-check, adapted and not committed. It read the codes from the log and never printed them. Output, with no codes, is in `~/srv/nucleon-preview/reports/preview-check-2026-10-20-3/`.
- **The request:** staff typed "Hi, Harbour Demo Logistics here. Could we pay invoice DEMO-202 on 2026-11-27 instead?". DEMO-202 is due Fri 6 Nov 2026, so the request is 21 days later and the limit date is Fri 20 Nov 2026.
- **Preparation:** `awaiting_owner` after 14.5 s. One owner question: "Since this is a 'newer customer since August 2026', what is the maximum number of days you would typically allow for an extension?". It does not ask for the decision. The suggestion was withheld, with no model call.
- **The answer and the suggestion:** the owner answered "Up to 14 days this time" on the page. It became a case-scoped `guidance` line with source `answer`.
  - After 1 call (2.5 s; shown after 4.7 s), the suggestion was **given: decline**, with no date, citing that answer line.
  - Its sentence: "The requested extension exceeds the maximum duration specified in the guidance."
- **Outcome:** no date beyond the limit was suggested. The model declined rather than approve, so **the guard itself did not fire live**. The withheld path is covered by the unit and server tests only.
- **Staff and errors:** staff see suggestion status `off`, no suggest run and no `suggestReason`. There were no JavaScript or console errors and no 4xx or 5xx responses.

**Left on the preview:**
- case `req_c7721b59db48248b` (DEMO-202), `awaiting_owner`, undecided, with its decline suggestion;
- case `req_b1819e749212286d` (DEMO-201), unchanged. It keeps the suggestion stored under `f3dd129` (approve, 21 days), because the guard applies only when a suggestion is formed.

Suggestions are still on.

### Conversational desk and verification (20 October 2026, 19:46–19:54 Sydney; live model; public URL)

**The deploy.** `65982b8` (the conversational desk, prompt `coordinator-v0.3`, E020, and its records) was pushed and deployed at 19:46 with the preview's `nucleonctl deploy`.
- The deploy backed up `preview-20261020-194616.sqlite3` (3 requests), ran the unit suite (372 OK) and restarted the service, so the codes rotated.
- `status`: `65982b8`, loopback 200, live mode. The public `https://nucleon.dracooz.top/preview/` returns 200.
- **Production unchanged:** `~/srv/nucleon/bin/nucleonctl status`, run without the preview variables, still reports `f95f50f` on `data/nucleon.sqlite3`, loopback 200. `https://nucleon.dracooz.top/` returns 200 and `/static/desk.js` 404s there (re-checked at 19:54).

**Checks before the deploy** (scratch servers on this machine; fictional data):
- unit suite 372 OK; `desk_check.js` 60/60 (mock);
- `conversation_check.js`: mock 169/169; live (local Gemma, scratch server on port 8769) 170/170, 3 INFO, no reply withheld ([qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md), "Re-run with coordinator-v0.3");
- `coordinator.py --print-prompts` equals PROMPTS.md's 12 `coordinator-v0.3` blocks.

**Check scripts that write are scratch-only** (since `e000009`). `conversation_check.js`, `desk_check.js`, `ui_check.js`, `guide_check.js`, `effort_compare.js`, `layout_check.js --seed` and `live_coordinator_check.py` exit 2 before any request unless the base URL's host is `127.0.0.1` or `localhost`, the port is neither 8620 (shared) nor 8621 (preview), and the named service log is neither `~/Library/Logs/nucleon/service.log` nor `~/Library/Logs/nucleon-preview/service.log` (symlinks resolved; `deploy/scratch_only.js`). `browser_check.js` and the `e2e_*_check.py` scripts are not guarded, by design: they run through the deployed URL after `nucleonctl isolate`. **`browser_check.js` still defaults to the production URL**, and its live mode resets demo data.

**Verification** (19:49–19:54 Sydney). A scratch Playwright script, not committed, signed in as staff and as the owner in separate browsers through the public URL. It read the codes from the preview log after its last ` URL: http` line and never printed them. Screenshots and JSON results are in `~/srv/nucleon-preview/reports/preview-check-2026-10-20-conv/` and contain no codes. Every answer reported `coordinator-v0.3`. The preview was **not** reset: it kept the earlier checks' cases, and DEMO-101's due date was Tue 3 Nov 2026 from the first check. Waits are from Send until the reply was stored.

| # | Check | Result |
| --- | --- | --- |
| S1 | Staff: "Give me a short overview of Harbour Demo Logistics: what they owe, overdue invoices, and anything the owner has shared" gives one card about Logistics answering all three parts | PASS, 7.8 s. "Harbour Demo Logistics owes DEMO-201 AUD 480.00 (stated) and DEMO-202 AUD 2,100.00 (stated). One invoice is overdue: DEMO-201 for AUD 480.00 (stated), which is 7 days overdue. The owner has shared: Fictional relationship context: newer customer since August 2026. Any extension still needs owner approval." Overview, overdue invoices and the shared context, all three open. |
| S2 | "What do they owe, and which of their invoices are overdue?" stays on Logistics | PASS, 4.7 s. "Harbour Demo Logistics owes DEMO-201 AUD 480.00 (stated); DEMO-202 AUD 2,100.00 (stated). One invoice is overdue: DEMO-201 for AUD 480.00 (stated)." |
| S3 | "and Supplies?" switches, and the chip says so | PASS, 5.8 s. "Harbour Demo Supplies still owes DEMO-101 AUD 1,250.00 (stated). There are no overdue invoices. The owner has shared: Fictional relationship context: a regular customer. …" Chip: "About Harbour Demo Supplies ×". |
| S4 | "where do I add a customer?" gives where, the steps, and one next step | PASS, 3.7 s. "You can add a customer on the Customers page." with the three steps, and one link, "Add customer" to `#/customers`. |
| S5 | "add Riverside Bakery as a customer" gives a draft and creates nothing; Create customer opens the Add customer dialog with the name filled in; once saved, the customer exists | PASS, 3.7 s. Riverside Bakery is in the records once, the thread says "Customer Riverside Bakery added.", and the chip moves to it. **Wording:** the prose repeats the manual steps ("Open Customers and press "Add customer"…") above a card whose one control is Create customer. |
| O1 | Owner: a context paragraph gives one understood card, then Confirm | PASS, 6.8 s. "About Harbour Demo Supplies": relationship "Harbour Demo Supplies have been a steady customer for years.", guidance "If they ask for more time I would give them a short extension, up to 14 days.", constraint "I do not want their balance to grow." Confirmed, owner-only. |
| C1 | Case 1. Staff: "Hi, Harbour Demo Supplies here. Could we pay invoice DEMO-101 on 2026-11-24 instead?" (21 days after Tue 3 Nov; the limit date is Tue 17 Nov) opens a case thread | PASS on re-read. The thread opened in 3.3 s. The script's own check read the thread before the invoice was identified (`invoiceReference` null) and printed FAIL; once prepared, the thread is "Harbour Demo Supplies · DEMO-101". |
| C2 | The case is prepared for the owner | PASS, 22 s from Send. One owner question: "You said 'If they ask for more time I would give them a short extension, up to 14 days'; does this request for 21 days fall outside that limit?" |
| C3 | The owner's first screen at 1366×900 | PASS. Request line "Harbour Demo Supplies asks to pay invoice DEMO-101 on Tue 24 Nov 2026 instead of Tue 3 Nov 2026, an extension of 21 days.", the customer's words under it, "AUD 1,250.00 Stated", and the decision form at 467 px. The suggestion line read "Suggestion withheld until the questions below are answered or skipped.", because the question was open. |
| C4 | After "Decide without this", a suggestion within the 14 days | **FAIL.** After 4.7 s the model suggested approve Tue 3 Nov 2026, the current due date. Code withheld it, and the owner saw "The agent could not form a suggestion. The suggested date was not valid." The stored raw reason: `date: approve to "2026-11-03", as of 2026-10-16, due 2026-11-03`. |
| C5 | The owner decides | PASS. Approve Tue 17 Nov 2026 (the current due date plus 14 days), typed into the form, with no suggestion on screen; the reply draft is shown. |
| C6 | Staff: one status line and none of the owner's words | PASS on reload: "Decided: Approved to Tue 17 Nov.", with no owner phrase in the page or the thread payload. The run's own read came before the page refreshed and showed "With the owner since 20 Oct 2026, 7:51 pm; nothing for you to do." |
| C1–C3 | Case 2. The same, for DEMO-101 now due Tue 17 Nov, asked Tue 8 Dec 2026 (limit Tue 1 Dec) | PASS. Prepared in 18 s, again with one question: "…is the requested 21 days still acceptable?" The first screen had the same layout. |
| C4 | The owner answered "Up to 14 days this time"; a suggestion within the limit | PASS, 4.1 s. **Approve Mon 30 Nov 2026**: 13 days, within the limit, earlier than asked. "The suggestion is based on the request for a short extension within the allowed limit." It does not say that it is shorter than asked. |
| C5 | The owner decides | PASS. "Use this date", then approve Mon 30 Nov 2026; `suggestionSeen` is `accepted`. |
| C6 | Staff | PASS on reload: "Decided: Approved to Mon 30 Nov.", with no owner phrase. The run's own read was again early (FAIL as printed). |
| P | Production | PASS: `f95f50f`; `/` 200; `/static/desk.js` 404; `/preview/` 200. |
| E | Errors in the pages | PASS. No JavaScript or console errors, and no 4xx or 5xx, apart from the script's own call to `/api/state`, a route that does not exist (404). |

**Result:** 25 scripted checks, 22 PASS and 3 FAIL as printed.
- One FAIL is the model: case 1's suggestion, which code withheld as invalid.
- The other two were the script reading too early (case 1 C1, case 2 C6). Both pass on a re-read.

**Findings:**
1. **The suggestion is not reliably within the stated limit on the first try.** Asked to skip the question, the model gave the current due date (case 1); code withheld it, as built. With the owner's answer it gave a date within the limit (case 2). These are two runs. Whether the model copied the earlier decision's date (Tue 3 Nov, in `<decisions>`) is not established.
2. **The needs step asks a question that code could answer.** "Does this request for 21 days fall outside that limit?" The owner stated 14 days, and 21 is more. The question withholds the suggestion until it is answered or skipped.
3. **The draft card's words describe the manual route** while its control is Create customer.
4. **Amounts in the prose carry their marks.** The model wrote invoice references beside the amounts and did not total them.

**Left on the preview** (fictional; the demo console's reset removes it):
- the customer Riverside Bakery;
- the owner's confirmed statement about Harbour Demo Supplies (3 lines, owner-only, with "up to 14 days");
- case `req_bd76448de17dc8f6`, approved to Tue 17 Nov 2026, with no suggestion;
- case `req_cbd133862ab03347`, approved to Mon 30 Nov 2026 as suggested, with its case-scoped answer line "Up to 14 days this time";
- DEMO-101 is now due Mon 30 Nov 2026;
- the staff turns in the general thread.

Suggestions are still on. The earlier cases on DEMO-201 and DEMO-202 are unchanged.

### Third slice (21 October): situation, capabilities, prepared actions

**What the next deploy will carry.** The branch from `e7a45be` (plan) to `50233e5` and the `coordinator-v0.4` records (E021; P003 "Revision 4"; [PROMPTS.md](../PROMPTS.md), "coordinator-v0.4"):
- one role-filtered situation that the desk page draws and the agent reads at the start of every case-thread turn, and the `caseDetails` tool;
- the capability registry, the owner's **Setup → Agent tools** page and `api/agent-tools` (below);
- `prepareDecision` with one **Confirm decision**, `requestSuggestion` through the existing guarded suggestion step, and next steps from the workflow (`actions_for`);
- the reply's `detail` (a closed Details expander, one summary line per block, or the blocks open), each invoice and each context block once, the chip's three kinds, and one retry of a withheld reply before "Here is what the records show about <name>.";
- the fix wave's changes (rounds `f83ddfc`, `6ca8d69`, `80d164f`, `50233e5`; [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md), "Re-run after the fix wave").

No configuration change is needed. The registry's defaults turn every implemented tool on for its roles, and no tool sends anything outside Nucleon. Overrides are kept in the preview database's meta (`agentTools`), and the demo reset keeps them, as it keeps the suggestions setting. Stored threads keep working: a focus stored before this slice reads as a customer focus, and a card stored before it renders its blocks open.

**Checks before the deploy** (scratch servers on this machine; fictional data), at `50233e5`: unit suite 428 OK; `desk_check.js` 73/73 (mock); `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 at `d5d165a`, with no page code changed after; `conversation_check.js` mock 310/310 (18 live-only assertions skipped) and live (local Gemma, scratch server on port 8769) 325/325, 3 INFO, no reply withheld, no retry, no model failure, no failed suggestion; `coordinator.py --print-prompts` equals PROMPTS.md's 12 `coordinator-v0.4` blocks. The earlier live runs (round 2 323/323 at `6ca8d69`; the controller's 312/318 at `80d164f`) are in [qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md), "Re-run after the fix wave".

**Deployed:** `df10ab6` (round 4 of the fix wave, `50233e5`, plus the records), pushed and deployed at 02:26 on 21 October (Sydney) with the preview's `nucleonctl deploy`. The deploy backed up the preview database first (`backups/preview-20261021-022659.sqlite3`, 5 requests), ran the unit suite on the deployed tree (428 OK) and restarted `local.nucleon.preview`; `/preview/` and `/` both answered 200 afterwards. The shared site was not touched: `~/srv/nucleon/app` is still at `f95f50f` and its service kept its process.

**Verification** (02:28:34–02:29:13 Sydney). A scratch Playwright script, not committed, signed in as the owner and as staff in separate browsers through the public URL. It read the codes from the preview log after its last ` URL: http` line and never printed them; its output and screenshots are in `~/srv/nucleon-preview/reports/preview-check-2026-10-21/` and contain no codes (a first run, `…-run1`, found no case thread because the script read the thread list wrongly; its staff turns are also in the general thread). Every answer reported `coordinator-v0.4`. The preview was **not** reset, so the review's own DEMO-202 case thread of 20 October was reused.

- **Owner, in the DEMO-202 thread.** The situation carried the case line "Up to 14 days this time", the day limit (14 days, latest Fri 20 Nov 2026) and the comparison (asked 21, limit 14, beyond). The review's first message ("Explain why this request is being declined. Could a shorter extension fit…") was answered in 9 s, shown, with no block: "The request is being declined because the requested extension of 21 days exceeds the maximum duration specified in your guidance, which is "Up to 14 days this time". A shorter extension would fit if it was for up to 14 days, making the latest date Fri 20 Nov 2026." The second ("What guidance have I already given for DEMO-202?") answered in 3 s: "You have said: Up to 14 days this time (said on Fri 16 Oct 2026)." with the context block. "What are my options here, in one or two sentences?" listed deciding, a new suggestion and telling the agent something to keep, from the workflow's steps. No decision was prepared or recorded.
- **Owner, Setup → Agent tools.** The table showed 12 tools; `api/agent-tools` answered 200 for the owner and 403 for staff, and the staff Setup page has no table.
- **Staff, general thread.** "What does Harbour Demo Logistics owe? Two short sentences please." → `summary`, the overview folded, the balance line quoted with its marks, 6 s. "What should I do next as staff?" with Logistics in focus → a navigation answer about what the desk can do; it no longer says to enter requests, but it did not name the two cases waiting on the owner (see "Still open"). "Supplies, what's their balance?" → about Supplies. "Can you add Seaview Catering as a customer?" → a draft, the chip "About Seaview Catering (not yet a customer)" with no records link; no owner-only line in any staff payload; no horizontal overflow at 390 px.
- The script's own tally was 25/28: its three failures were its assumption that a desk turn returns 200 (every turn, owner and staff, returned 202 with the reply stored), not product findings.
- Still open from this check: in the general thread, staff asking "what should I do next" with a customer in focus got a navigation answer rather than the two cases waiting on the owner; the workflow's steps are drawn in a case thread and when the agent reads the customer's cases, and the model chose neither here.

**Where to inspect the agent's tools and permissions.**
- **On the page:** sign in as the owner and open **Setup** (`#/setup`, at `/preview/#/setup` on the preview). The **Agent tools** section lists every tool the agent can be given: Tool, What it does, Kind (Read, Prepare or Act), Roles (staff, the owner or both), Needs confirmation, and Enabled with an "On" checkbox. Turning a tool off takes effect from the next message: a disabled tool is neither offered to the model nor executed, even when the model names it (`FORBIDDEN`), and the steps that need it read "turned off under Setup → Agent tools". Confirmation is separate from both: a tool marked "Needs confirmation" still only prepares, and the person's own button (Create customer, Confirm, Confirm decision) commits. Staff see none of the section, and their browser sends no request for it. Turning off customerOverview does not hide the overview the page shows; the agent can still state a balance from it.
- **Through the API** (owner only; staff get 403): `GET api/agent-tools` gives `{tools: [{name, kind, roles, needsConfirmation, defaultEnabled, description, enabled}]}` in registry order. `POST api/agent-tools {tool, enabled}` with an `Idempotency-Key` sets one override and returns the same table; an unknown tool, `reply`, an `external` kind or a non-boolean `enabled` is refused with 400.
- **In the code:** the registry is `coordinator.CAPABILITIES` in `prototype/coordinator.py`. `check_capabilities` refuses at import a kind that is not implemented (`external`) or a desk tool without exactly one entry; `tools_for(role, overrides)` gives each role's tools; `DeskTools.execute` in `prototype/server.py` refuses any other.

## Lab instance (reuse experiment)

Recorded 21 October 2026, Sydney. A third, separate instance for the reuse experiment on the conversation layer (design: [superpowers/specs/2026-10-21-nucleon-lab-design.md](superpowers/specs/2026-10-21-nucleon-lab-design.md); plan: [superpowers/plans/2026-10-21-nucleon-lab.md](superpowers/plans/2026-10-21-nucleon-lab.md)), from the same branch `explore/agent-coordinator-20261019`. It is not a release. The shared site at `/` (`f95f50f`) and the preview at `/preview/` (`df10ab6`, the baseline the Lab is compared with) are not touched.

- **URL:** **https://nucleon.dracooz.top/lab/** (the chat). `/lab` redirects there with a 301. Its records instance (sign-in, the records pages, the demo console) is at **https://nucleon.dracooz.top/lab/records/**.
- **Arrangement:**
  - Two launch agents:
    - `local.nucleon.lab-records`: the records server for the Lab, generated by `nucleonctl` from `deploy/local.nucleon.prototype.plist.template`. It runs one process on `127.0.0.1:8623`. Its config is made like the preview's: `cookiePrefix` `nucleonl_`, `cookiePath` `/lab`, `sampleData`, the demo console on, `publicOrigins` `https://nucleon.dracooz.top`.
    - `local.nucleon.lab`: the Lab itself (`python -m lab --config config/lab.json`), generated by `labctl render-plist` from `deploy/local.nucleon.lab.plist.template` (KeepAlive, RunAtLoad, umask 077). It runs one process on `127.0.0.1:8622` with root path `/lab`, from `app/` (it imports `prototype/`) with the Lab's own venv. It calls the records instance at `http://127.0.0.1:8623` directly, not through Caddy.
  - Its files are in `~/srv/nucleon-lab/`:
    - `app`: a clone of the GitHub repository, detached at the deployed commit. Both agents run from it;
    - `config/production.json` → `service.json`: the records instance, as on the preview;
    - `config/lab.json`: the Lab (shape: `lab/config.example.json`). It holds `port` 8622, `rootPath` `/lab`, `recordsUrl` `http://127.0.0.1:8623`, `store` `../data/lab-conversations.sqlite3` (relative to the config file), `model`, and for the MCP server `mcpTokens`, `recordsLog` (`~/Library/Logs/nucleon-lab/service.log`, the records instance's log, where it reads the current access codes) and `publicOrigins` (`["https://nucleon.dracooz.top"]`, so the MCP transport accepts the public Host). The real tokens are only in this file (mode 600), never in Git;
    - `data/lab.sqlite3`: the records database, a practice workspace with the fictional sample;
    - `data/lab-conversations.sqlite3`: the Lab's threads and turns;
    - `backups`, `reports`, and `bin/nucleonctl` and `bin/labctl` (copies of `deploy/nucleonctl` and `deploy/labctl`);
    - `runtime`: a symlink to `~/srv/nucleon/runtime`, used by the records server;
    - `runtime-lab/venv`: the Lab's venv, from the pinned `lab/requirements.txt`. `labctl install` creates it with `~/srv/nucleon/runtime/python-3.12.14` and builds the chat page into `app/lab/web/dist` (Node 24, `npm ci && npm run build`).
  - Logs in `~/Library/Logs/nucleon-lab/`: `service.log` (the records instance; it holds the access codes) and `lab.log` (the Lab).
  - Caddy, in the same site file (`deploy/nucleon.caddy`): `redir /lab /lab/ 301` and `redir /lab/records /lab/records/ 301`, `handle_path /lab/records/*` → `127.0.0.1:8623`, and `handle_path /lab/*` → `127.0.0.1:8622` with `flush_interval -1` for the server-sent events. Both strip their prefix. Caddy tries the longer path first whatever the order in the file; `caddy adapt` puts `/lab/records/*`, `/preview/*` and `/lab/*` in that order, in one mutually exclusive group. Everything else still goes to 8620.
  - Cookies are `nucleonl_staff`, `nucleonl_owner` and `nucleonl_operator`, with `Path=/lab`, set by the records instance at sign-in.
    - The browser sends them to `/lab/api/…` and `/lab/records/api/…` alike; the Lab forwards the Cookie header to the records instance.
    - Root cookies (`nucleon_*`, `Path=/`) also reach `/lab/`, but neither Lab process reads them. Preview cookies never reach `/lab/`, and Lab cookies never reach `/` or `/preview/`.
  - Browser storage keys of the records pages under `/lab/records/` are `nucleon-lab-records.*`. The chat's history is kept on the server, per role.
- **Model:** live, through the same local Gemma gateway (`127.0.0.1:1236`, `gemma-rp`, temperature 0), for the Lab's agent and for the records instance's own tasks. Production, the preview, the Lab and other clients share it, so requests queue.
  - **Model access for the Lab** (recorded 21 October). The Lab's agent does not use `prototype/model_adapter.py`. Pydantic AI's OpenAI-compatible chat model is set by `model` in `config/lab.json` (`{"provider": "openai", "baseUrl", "model", "apiKey"}`), with one attempt per request, one tool call at a time and a required tool call every turn.
  - **A hosted API is untested.** A hosted OpenAI-compatible API would only be a different `model.baseUrl`, `model.model` and `model.apiKey` there. No hosted endpoint has been connected. Not established: whether one accepts the required tool choice with the Lab's output tool, its latency and its output quality.
  - **The key.** It would sit in `config/lab.json` (mode 600), not in an environment variable as the records' `apiKeyEnv` does, and never in Git. Fictional data only; Q08 applies before any real records.
  - The records instance's own tasks keep the records' model settings ("Model access", above). A second machine is described under "A second inference machine (planned, not configured)".
- **Access codes** are the records instance's; the Lab has none of its own. Sign in at `/lab/` with the STAFF or OWNER code. They rotate on every restart of `local.nucleon.lab-records`: `NUCLEON_BASE=~/srv/nucleon-lab NUCLEON_LABEL=local.nucleon.lab-records NUCLEON_LOGDIR=~/Library/Logs/nucleon-lab ~/srv/nucleon-lab/bin/nucleonctl codes`. The same prefix works with `status`, `logs 50`, `restart` and `stop`. Put the variables on the command line, not in `export`. The MCP server reads the codes of the records instance's latest start from its log (`recordsLog` in `config/lab.json`) and signs in again when the records answer 401, so a restart of the records instance needs nothing done in the Lab.
- **The Lab's commands** (`~/srv/nucleon-lab/bin/labctl`; they never print codes or tokens):

```bash
~/srv/nucleon-lab/bin/labctl status          # launchd state of local.nucleon.lab, deployed commit, loopback api/session (401 expected)
~/srv/nucleon-lab/bin/labctl restart
~/srv/nucleon-lab/bin/labctl logs 50         # lab.log
~/srv/nucleon-lab/bin/labctl install         # venv (if missing), pip install -r lab/requirements.txt, build lab/web
~/srv/nucleon-lab/bin/labctl deploy <sha>    # fetch, check out, refresh bin/labctl, install, run lab/tests, restart the Lab only
~/srv/nucleon-lab/bin/labctl render-plist    # write ~/Library/LaunchAgents/local.nucleon.lab.plist; then launchctl bootstrap gui/$(id -u) <that file>
```

- **MCP endpoint:** **https://nucleon.dracooz.top/lab/mcp/** (streamable HTTP). It offers the same business operations to an external agent, as the role its bearer token maps to in `config/lab.json` (`mcpTokens`). The tokens are shared privately, like the codes. A client connects with the header `Authorization: Bearer <token>`. For Claude Code: `claude mcp add --transport http nucleon-lab https://nucleon.dracooz.top/lab/mcp/ --header "Authorization: Bearer <token>"`. See `lab/README.md` for the tools and what each role gets.
- **Update** (the commit must be pushed first, since both commands fetch from GitHub):
  1. `NUCLEON_BASE=~/srv/nucleon-lab NUCLEON_LABEL=local.nucleon.lab-records NUCLEON_LOGDIR=~/Library/Logs/nucleon-lab ~/srv/nucleon-lab/bin/nucleonctl deploy <sha>`. It backs up `lab.sqlite3`, checks out the commit, runs the records unit suite and restarts the records instance.
  2. `~/srv/nucleon-lab/bin/labctl deploy <sha>`. It checks out the same commit (already there), installs, runs `lab/tests` (they start their own scratch records server) and restarts the Lab. It also refreshes `bin/labctl` from the checked-out `deploy/labctl`. If a test fails it stops before the restart and leaves the checkout on the new commit while the Lab keeps running the old code. Revert both halves to the commit `labctl status` showed before step 1: `labctl deploy <previous sha>` and the records `nucleonctl deploy <previous sha>`. The failure message names the commit the checkout was on before `labctl deploy`, which after step 1 is already the new one.
  3. Run `python3 deploy/e2e_lab_check.py https://nucleon.dracooz.top`. It only reads: `/lab/` serves the built chat page, `/lab/api/session` is 401 without a session, `/lab/records/api/session` answers "not signed in", `/lab/mcp/` refuses a made-up token, and `/` and `/preview/` still answer 200.
  - When `deploy/nucleon.caddy` changes, copy it to `~/.config/caddy/sites/nucleon.caddy` and reload Caddy. When `deploy/local.nucleon.lab.plist.template` changes, run `labctl render-plist`, then `launchctl bootout` and `launchctl bootstrap` the agent.
- **Reset its data:** use the demo console on the Lab's records instance (`/lab/records/`, OPERATOR code). It resets `lab.sqlite3` only. The Lab's conversations are separate and would then refer to cases that no longer exist. To clear them too, stop the Lab (`launchctl bootout gui/$(id -u)/local.nucleon.lab`), move `data/lab-conversations.sqlite3` into `backups/`, and run `labctl restart`.
- **Rollback:** stop both agents: `launchctl bootout gui/$(id -u)/local.nucleon.lab`, then the records instance's `nucleonctl stop` with the prefix above. `/lab/` then answers 502. The root site and the preview are unaffected: they have their own agents, ports, databases and cookies. To remove the route as well, delete the Lab lines from the installed site file and reload Caddy.
- **Deployed:** `3e52328` (the Lab after its fix wave, `lab-v0.2`; the records instance at the same commit with the tool surface and `coordinator-v0.4` prompts), 21 October, about 09:00 Sydney: `nucleonctl deploy 3e52328` for `local.nucleon.lab-records` (unit suite 443 OK, ready on 8623) and `labctl deploy 3e52328` for `local.nucleon.lab` (venv rebuilt, UI built, Lab tests OK, ready on 8622). Earlier the same morning the Lab first went live at `c454d9d` (`lab-v0.1`) for the browser comparison. The root site (`f95f50f`) and the preview (`df10ab6`) were not touched; both answered 200 before and after.
- **Verification** (09:01–09:07 Sydney). `deploy/e2e_lab_check.py https://nucleon.dracooz.top` → 6/6 (UI index 200; `/lab/api/session` 401 without a cookie; `/lab/records/api/session` not signed in; `/lab/mcp/` with a made-up token 401; `/` and `/preview/` 200). An MCP client (`mcp` 2.3.0, streamable HTTP) with the owner token listed 16 tools and read the work queue; the staff token listed 12. The builder's browser sessions as the owner and as staff through the public URL, with the replies and the business state after each commit, are in [qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md) ("After the fix wave"). No codes or tokens appear in any record.

### Second deploy (21 October): revisions and presentation

**What it carries.** The Lab's second iteration, from `1d1840a` (design and plan) to the final commit after the second fix wave, with `lab-v0.4` for the Lab's agent and `coordinator-v0.7` for the records (E023; P003 "Revision 6"; [PROMPTS.md](../PROMPTS.md), "coordinator-v0.7" and "lab-v0.4"):
- the records keep a history of prepared decisions, and a revision keeps what the owner did not change;
- `dueNow` and `originalDue`, a request's number on its invoice, and a likely-duplicate flag;
- staff concerns (`raiseConcern`), and the app's "still holds?" question;
- the page puts the prose first, with "Records (N)" and "Activity" folded and one open card. Proposal cards come from live state, with Confirm only on the current version;
- a case header, and thread titles with the status and the asked date.

**coordinator-v0.7.** The Lab's records instance (`local.nucleon.lab-records`) runs the same commit as the Lab, so it runs `coordinator-v0.7`. The preview at `/preview/` stays at `df10ab6` (`coordinator-v0.4`), and the root site at `/` is unchanged (`f95f50f`). Until that deploy, the deployed `a0ab50d` runs the v0.7 and lab-v0.4 texts under the labels `coordinator-v0.6` and `lab-v0.3`.

**What else changes, and what does not:**
- No configuration change, new port or new route.
- The update follows "Update" above: both halves, records first.
- Preparations made before this code have no history. Their cards read "No longer current" (DEMO-201 carries two from the morning's review).

**Deploys during the iteration** (the build ledger; for the builder's browser checks):
- `a0ba992`, then `8fa7b5b`, `cf3cbaf`, `f3f616e` (`e2e_lab_check.py` 6/6), `d080fd6` and `6038696`;
- `6038696` was demonstrated from 14:22 Sydney time. Deploys and restarts were frozen during the demonstration, since the access codes rotate on a records restart.
- `a0ab50d` (fix wave 2) was deployed at about 15:20 Sydney on 21 October for a team demonstration. The team then imported the NTK ledger into this instance through the records' Imports page. The data files stay local and are ignored by Git (`.gitignore`, `5b33eda`). This is real business data on the Lab's records instance, not the fictional sample: Q08 (data handling and model destination before real data) is still open in [FACTS-AND-OPEN-QUESTIONS.md](FACTS-AND-OPEN-QUESTIONS.md).

**Checks before the deploy** (scratch servers; fictional data):
- records unit suite 463;
- `desk_check.js` 76/76;
- Lab tests 115;
- `lab_check.js` 99/99, re-run at `a0ab50d`;
- `lab_conversation_check.js`:
  - 319/319 on the mock (51 skipped);
  - 354/364 live at `6038696` ([qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Second iteration");
  - after fix wave 2, a live re-run of the 9 affected scenarios: 223/223 at `a0ab50d` (2 INFO, 0 withheld, 0 errors, 597 s; 212/222 before), as recorded in "After fix wave 2" there.

**Deployed:** the second iteration went to the Lab in steps during the builder's own testing on 21 October (`a0ba992` 11:46, `8fa7b5b`, `cf3cbaf`, `f3f616e`, `d080fd6`, `6038696` 13:51), and `a0ab50d` (fix wave 2) at about 15:20 for the team's demonstration; the root site and the preview were untouched throughout.

**Verification:** the builder's browser sessions as owner and staff through the public URL, with the replies and the business state after each step, are in [qa/LAB-COMPARISON.md](qa/LAB-COMPARISON.md) ("Second iteration" and its re-check); the scripted runs are in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md) (mock 319/319; live 354/364 before the fix wave, 223/223 on the nine affected scenarios after it); `deploy/e2e_lab_check.py` 6/6 after each deploy.

### Third deploy (21 October): agent-assisted import

**What it carries.** Agent-assisted import (E024; `lab-v0.5` for the Lab's agent and `coordinator-v0.8` for the records; [PROMPTS.md](../PROMPTS.md)): the records' `proposeImport` and `applyImportProposal`, the stdlib xlsx reader, the Lab's attachment, `prepareImport` and the import card. The code is on the branch from `b97e50b` and `43781d6`, with the records commit that sets the versions.

**What changes, and what does not:**
- No new port, route or configuration key. The update follows "Update" above: both halves, records first.
- **The raised body limit.** The records route `POST /api/tools/proposeImport` accepts a body up to 4 MB (the 2.5 MB file in base64); `/api/imports` stays at 2.5 MB and every other route at 64 KB. Caddy sets no body limit for the Lab. The Lab itself refuses an attachment over 2.5 MB decoded with 413 `FILE_TOO_LARGE`.
- **Where the proposals are stored.** In the Lab's records database, `~/srv/nucleon-lab/data/lab.sqlite3`, in the `meta` table under `importProposals:<id>`. The five most recent are kept, and only the newest keeps the attached file. Resetting the Lab's data with the demo console deletes them. The file is not written anywhere else, and the Lab's conversation store keeps only the file name.
- No live-model run of the import has been done. The controller runs the team's file on the Lab after the demonstration.

**Checks before the deploy** (scratch servers; fictional data): records unit suite 484; Lab tests 119; `lab_check.js` 113/113; `desk_check.js` 76/76.

**Deployed:** `6358e6a` at 17:13 Sydney on 21 October (both halves; the records half runs `coordinator-v0.8`, the Lab `lab-v0.5`), after the team's demonstration on `a0ab50d` ended. At 17:32 the import fix round `526dc7e` followed (sheet scoring, Vietnamese ledger headings, a sheet selector on the card), after the first live test had picked the wrong sheet.

**Verification:** `deploy/e2e_lab_check.py` 6/6 at 17:13 and again after the final deploy; the root site (`f95f50f`) and the preview (`df10ab6`) answered 200 before and after. The builder then signed in as staff through the public URL, attached the team's spreadsheet in the Lab chat and read the import proposal card: at `6358e6a` it chose the first sheet ("Raw Data") and mapped nothing; at `526dc7e` it chose "Cleaned Data" (score 7.5 against 7), read it as a ledger, mapped customer, invoice number, dates, debit, credit and credit term by itself, proposed 21 customers, 137 invoices and 116 payments with 7 rows to check, and one press of Import wrote two batches (137 new invoices, 116 new payments; records then 23 customers, 140 invoices, 116 payments, both batches revertable from the Imports page): the same result as the morning's manual import of the same file, which had taken 28 dropdown choices and two uploads. Backups before the test: `backups/lab-20261021-171412.sqlite3` and `backups/lab-conversations-20261021-171412.sqlite3`; the records were reset to the fictional sample first.

### Fourth deploy (21-23 October): week 7 core flow

**What it carries.** The week 7 core flow (E025; `lab-v0.7` for the Lab's agent and `coordinator-v0.10` for the records at the end, `lab-v0.6` and `coordinator-v0.9` at the first deploy; [PROMPTS.md](../PROMPTS.md)): unit detection and the refusal of a mismatched file, payment references, the live state of an import proposal, `current` as a hint, `datasetId` and the read-only threads from before a reset, the ledger replay, `assessRequest`, the owner's authority settings, `actWithinAuthority`, the decision fields and `remember.until`, and the Lab's assessment card, Authority panel and failed-read replies. The code is on the branch from `60a9f59`.

**What changes, and what does not:**
- No new port or route prefix. New records routes: `GET /api/records/imports/proposals/<id>` and `GET/PUT /api/setup/authority`; `POST /api/demo/reset` accepts `{"to": "empty"}`. The update follows "Update" above: both halves, records first.
- The Lab's conversation store gains a `dataset_id` column on its threads (a migration at start; old rows are read as "earlier" unless the records still list the case).
- The root site (`f95f50f`) and the preview (`df10ab6`) are not touched.

**Checks before the first deploy** (scratch servers; fictional data): records unit suite 542; Lab tests 137; `desk_check.js` 76/76; `lab_check.js` 152/152; `lab_conversation_check.js` on the mock 443/443 (51 skipped), [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Third iteration".

**Deployed:** to the Lab only, both halves, records first, with the local model (Gemma 4 26B-A4B through the home gateway, config label). Prompt versions at the end: `coordinator-v0.10`, `lab-v0.7`.
| Commit | Time (AEDT) | What it was |
| --- | --- | --- |
| `c792a43` | 00:50, 22 October | The branch after the final review's fixes. |
| `f1cabf9` | 00:55, 22 October | Records and Lab UI tolerate proposals stored before the upgrade. |
| `3efe379` | 01:27, 22 October | Live-test fixes L1-L9. |
| `d74c33c` | 23:41, 22 October | L10-L13, the overdue-unknown rule, the stale-proposal re-check, the "New workspace" console button (`1169eef`), stated-only invoices in the overview. Deployed just before the VND transition. |
| `7f6f64b` | 00:25, 23 October | Concern loop (`coordinator-v0.10`, `lab-v0.7`), normalised invoice references, opening-balance batch, staff replies. The import was pressed on this build. |
| `7c6bec4` | 00:48, 23 October | Replay fixes (recorded allocations first, prepayments and opening credits carried forward), credits shown as customer credit, still-owed header, capability line. |
| `db86293` | 01:21, 23 October | **Final code commit.** Review fixes (staff status in the records UI, queue order, `openRequest` refused in a case at both layers) and `withdrawRequest` pressed by a person only. |

`deploy/e2e_lab_check.py` gave 6/6 after each deploy. The root site (`f95f50f`) and the preview (`df10ab6`) were not touched and still answered 200. Backups before the first deploy: `backups/lab-20261022-004846.sqlite3` (records) and `backups/lab-conversations-20261022-004846-before-week7.sqlite3` (the Lab's conversations).

**Transition to a VND workspace (done, 22 October, 23:42-23:46 AEDT).**
1. **Backups** (in `backups/`): `lab-20261022-233242.sqlite3`, `lab-20261022-233242-before-vnd-reset.sqlite3`, `lab-conversations-20261022-233242-before-vnd-reset.sqlite3`, and `lab-20261022-234205-before-reset.sqlite3` (made by the console itself when the reset was pressed).
2. **Reset** through the new console button **New workspace** (`1169eef`), pressed as the operator. It clears the data and the currency. An earlier attempt to reset with a scripted call had been declined by the tool permission classifier, so the product got a real button and a person pressed it.
3. **Setup**, as the owner: currency VND, 0 decimal places, time zone `Asia/Ho_Chi_Minh` (the team should confirm the zone), business name "NTK Co (team ledger, demo)". Authority: staff may approve up to 14 days, only when nothing else is overdue, up to VND 500,000,000 outstanding, 2 concern rounds.
4. **The Lab's conversation store was retired** to `backups/lab-conversations-20261022-234305-retired-before-vnd.sqlite3` and the Lab restarted, so the Lab starts with no old threads. To restore it: stop the Lab, copy that file back to `data/lab-conversations.sqlite3`, start the Lab.
5. **Import** at 00:27 on 23 October on `7f6f64b`, one press by staff in the Lab chat: 21 customers, 137 invoices, 113 payments, 60 allocations, 4 opening balances. 60 of the 113 payments were matched by normalised references; 13 name an invoice that is not in the file; 40 have no reference. The 4 opening balances are dated 2 September 2025, the day before the first entry, because the file states no date. Three netting or adjustment rows and two negative reversals were left out and flagged; the card says "balance excludes it". Three batches were written, each revertable from the Imports page.
6. **Validation against the source** (`deploy/validate_import.py`, added in `c674329`): checks 1-6 passed (customers, invoices including VAT sums and dates, payments, allocations, openings, positions). Check 7, the replay against an independent hand computation, passed after two replay fixes (recorded allocations are reserved first; prepayments and opening credits are carried forward; lateness on the same day is judged once per day). Two customers reconcile only up to an unapplied credit (a payment with no invoice, and an overpayment); the validator reports these as notes. On the final build: self-test ok and 0 discrepancies on a copy of the live records.

**Checks at `db86293`** (scratch servers, mock model, fictional data): records suite 585; Lab suite 148; `lab_check.js` 174/174; `desk_check.js` 78/78; `lab_conversation_check.js` on the mock 472/472 (51 live-only skipped). The live runs are in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Live run, 22 October" and "Live run on the VND workspace, 23 October".

*Seen in the browser by the controller (22 October, 00:50-01:10 AEDT, owner and staff sessions, `f1cabf9`; fictional or already-ledgered ids only):*
- Staff looked up a customer by its original code (`0014`) and by a sample name; a new request opened from a quoted call; the assessment card showed facts, checks, a recommendation and evidence.
- The owner's Authority panel saved and persisted. An owner decision through Confirm read "Approved to ... Due now, Originally due" and "Approved by the owner. There was no approve or decline recommendation to follow."
- Staff acted within authority through the card's two-step button: `decisionSource` `staff_within_authority`, `followedRecommendation` true. Both decisions persisted across a reload.
- Threads from before the reset were read-only; old import cards read live. Staff asking for the owner's limits got nothing owner-only. The page was readable at 390 px. The VND ledger was refused in the then-AUD workspace.

*Findings that night, each fixed and redeployed (L1-L13):*
- **Honesty of numbers.** L1 the date fact and the oldest-first matching are said apart. L2 the overview says overdue is not known where no amount still owed is recorded. L10 invoices carrying only a stated outstanding amount count as open, and an unreadable invoice makes the picture incomplete and the recommendation escalate.
- **Import.** L11 the money unit is detected across all sheets and a doubtful magnitude is refused. L12 the payment-reference card says how many name an invoice and how many match. L13 the unit line no longer shows twice.
- **Behaviour.** L6 an explicit outcome wins over the "is that a decision?" question.
- **Timeouts.** L5 the Lab's records client now waits 300 s and a run 330 s, and a read timeout is reported in words.
- **Display.** L3, L4, L8, L9.
- L7, the AUD labelling of all amounts, was closed by the VND transition above.

**Live tests on the final build (23 October, 00:28-01:22 AEDT, local Gemma model, owner and staff, cross-checked against the records).** Full table in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md).
- Retrieval: customer `0014` by code; invoice 59 reads as Customer `0001`, settled; "BNSO" gets an honest "no customer by that name"; a correction to `0004` gives VND 0 owed and the last payment on 16 December 2025.
- Routine case (`0011`, invoice `00000087`, asked for 10 November): within the owner's limits; staff pressed Act within authority (two steps); recorded `staff_within_authority`, `followedRecommendation` true.
- Escalation case (`0001`, invoice `00000079`, asked for 15 November, 34 days against a 14 day limit): the assessment escalated; staff raised a concern; the owner asked staff whether they could pay half (`needs_info`) and both roles then saw "Waiting on staff"; staff replied (stored as a reply, not a concern round); the owner approved with a reason, revised to 8 November keeping the reason (version 1 superseded), withdrew without declining (version 2 withdrawn, no Confirm button), then asked for "the 15th after all" and was asked for the full date; version 3 was confirmed with `decisionSource` owner and `followedRecommendation` null. Staff then saw "Approved by the owner" and the concern thread.
- A stray request opened by the model from the staff reply was found. `openRequest` is now refused in a case at both layers, and the stray was withdrawn with the new header button (reason recorded).

**What the resumed round changed (22-23 October).** Concern loop: the owner's answer to a staff concern (`answerConcern`: `needs_info`, `explain` or `guidance`) sets the status and the next person (`withStaff`, "Waiting on staff"); staff replies to an owner's question are stored as replies, not concern rounds. `withdrawRequest` is pressed by a person, never offered to the model. An opening-balance batch in the importer. Normalised invoice references with unmatched reasons. Replay fixes. The capability line "Numerical analysis of the ledger and the owner's policy checks; no approval predictor." replaces the old "No approval model runs here." heading. The case header shows invoice value, allocated payments and "still owed not stated" for requests analysed after the deploy (older cases keep the old sentence until re-analysed). The demo console gains **New workspace**.

**What remains.**
- **Private context trimming rests on the prompt** (review 2, item 3). `answerConcern` only checks that the stored text appears in the owner's message; if the model passes the whole message, owner-private words could reach staff. A live scenario with mixed private and shared content is not yet run.
- **Minors from review 2, not fixed:** a past `until` date is accepted on guidance; the opening as-at date rule changes if a longer ledger is re-imported, and the existing opening is then rejected as different; `invoice_key` normalisation equates "1.05" with "1.5"; recorded allocations that exceed the payment are not capped to the payment.
- **Bare day-of-month dates** ("the 15th") are not resolved against the asked date or an earlier preparation; the assistant asks for the full date.
- **A reason must be in the current message or an earlier preparation.**
- **Local-model cold start:** the first call after idle can exceed the run limit; the retry works. Hosted APIs remain untested.
- **No approval predictor.** Building one depends on validated decision records, and collecting decisions alone does not validate a predictor.
- **Act and Withdraw are buttons a person presses.** That is the current execution mode. Automatic action within the owner's authority is the intended product; tool availability to the model, preparation and execution are separate things and are kept apart in the design.

#### Repair round after the independent browser review (23 October)

An independent browser review of `db86293` found five failures (F1 to F5; causes in [DECISIONS.md](DECISIONS.md) E025). Four commits repaired them: `79a72ae` (repair A), which went out with the first deploy, then the three below. Each deploy updated both halves of the Lab, records first, with the local Gemma model. `deploy/e2e_lab_check.py` passed 6/6 after each. The root site (`f95f50f`) and the preview (`df10ab6`) were not touched.

| Commit | AEDT, 23 October | What it carries |
|---|---|---|
| `1720b0d` | 15:09 | Repairs A and B: same-day facts in the assessment, invoice facts in tools and cards, customer resolution by name or code, a live "Request opened" card, a two-date comparison; who acts next after an owner's answer, and the recorded decision reason reaching staff |
| `08b0a07` | 15:27 | Repair C: assessment figures grounded without marks, recommendation and decision fallbacks, original against moved due dates, count wording, verbatim quotes exempt from the validators |
| `eb8eef0` | 15:36 | Repair C6: a withheld invoice answer is built from the invoice rows; a withheld reply is logged. The final code commit of the round |

**Counts at `eb8eef0`:** records 606, Lab 177, `lab_check` 185/185, `desk_check` 78/78, conversations on the mock 522/522 (51 live-only skipped). Prompt versions `coordinator-v0.12` (records) and `lab-v0.10` (Lab), verbatim in [PROMPTS.md](../PROMPTS.md). The Lab's records half now runs with fixed access codes (commit `8946934`); the codes are not recorded here.

**What the controller verified live, as staff and as owner** (full table in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Repair round, 23 October"):
- Invoice 59 gives the original amount, the matched payment and what is still owed; invoice 00000087 gives the original amount, says no payment is allocated and that still owed is not recorded.
- Customer 0004 is reached by name mid-conversation with no internal text, and invoice 70 reads correctly.
- Two same-day invoices for a fictional QA customer are stored, assessed on current facts (VND 603,000,000 owed, over the VND 500,000,000 limit, escalate, no Act button), and the staff concern leaves the case with the owner.
- Two dates are compared in one answer with nothing prepared.
- The owner's guidance that keeps the decision leaves the case with the owner (prose, header, card and records agree); guidance that needs a staff action sends it to staff, and staff see both owner answers without owner-only text.
- The "Request opened" card shows the resolved customer, invoice, date and current status, and keeps them after navigation.
- Staff are told the recorded decision reason verbatim (QA-ESCALATE).
- The original and the moved due date of invoice 00000087 (30 Oct and 10 Nov 2026) are both stated.

**What remains:** the model sometimes classes an information request as guidance or the reverse (the next person is still set correctly by the records); the assessment prose can name the outcome word where the card does; broad dirty-data compatibility, private-context trimming on the prompt, local-model cold start and untested hosted APIs stay as listed in [reviews/2026-10-22-week7-handover.md](reviews/2026-10-22-week7-handover.md).

#### Round F (23 October): retest findings and the AI Agent testing account

A second independent retest of `2c30d9f` found five faults (A to E, causes in [DECISIONS.md](DECISIONS.md) E025, "Round F"). They were repaired, and a testing account for AI agents was added. Both halves of the Lab were updated each time, records first, with the local Gemma model. `deploy/e2e_lab_check.py` passed 6/6 after each. The root site (`f95f50f`) and the preview (`df10ab6`) were not touched.

| Commit | AEDT, 23 October | What it carries |
|---|---|---|
| `991cf31` | 20:43 | Repair E: an unknown overdue state is shown as unknown (A), the decided-by line names who decided (B), an older owner guidance card no longer invents a staff reply (C), a manually entered amount names who entered it (D), the "Request opened" card refreshes by itself while the case is prepared (E) |
| `196c3ee` | 21:12 | The AI Agent testing account: one code, three roles, a role switch in the Lab and the records, a Demo console link, actor name and role in the audit trail. The final code commit of the round |

**Counts at `196c3ee`:** records 628, Lab 187, `lab_check` 213/213, `desk_check` 89/89, conversations on the mock 530/530. Prompt version `lab-v0.11` (Lab); `coordinator-v0.12` (records) is unchanged. Both are verbatim in [PROMPTS.md](../PROMPTS.md).

**Configuration.** The account exists only when the records config has the key `accessCodes.agent` (at least 6 characters, different from the other codes). The value is not recorded here. It is set in the Lab's service config, on demo instances only; leave it out for real records and there is no such account.

**Live scenario (rows 19 to 25 of the table).** One login with the agent code opened the Lab as "AI Agent" in the Staff role with a Staff/Owner switch and a Demo console link, and no further codes. As staff the agent raised a concern on the QU-TARGET case. Switching to Owner without a code, it answered the concern asking staff for more information, and the case went back to staff. The Demo console link opened the console without a sign-in. After a refresh the Lab still showed Owner. Switching back to Staff, the sidebar and header showed "Waiting on staff" with the owner's question. The records Activity named the two actions "AI Agent (as staff)" and "AI Agent (as owner)", and so did the Lab header, with the stored events carrying the actor name and role.

**Five retest findings verified live (rows 14 to 18):**
- B: the case page and Activity for a staff decision within authority say "Staff, within the owner's authority", not the owner.
- C: two owner guidance cards on one case read "Followed by a later answer from the owner" and "Decided: declined", with no invented staff reply.
- E: the "Request opened" card and the sidebar update by themselves within 20 seconds while a new request is prepared.
- A: with an open invoice that has no due date, the facts say "Overdue not known", the nothing-else-overdue check shows as unknown, the recommendation is escalate and there is no Act button.
- D: a manually entered amount shows "Entered by staff on Fri 23 Oct 2026 · Not verified", not "Customer's words".

The full table is in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Round F, 23 October". Limitation: analyses stored before `991cf31` keep the older provenance wording.

#### Round G (23 October, late evening): attribution fix, cleared workspace, full journey test

The remaining attribution error from Round F was fixed, the Lab's fictional business data was backed up and cleared through the console's New workspace button (by the AI Agent account, 22:11 AEDT), and the complete user journey was tested in the deployed browser with the AI Agent login: setup, import, everyday staff use, owner review and staff follow-up, then boundary checks. Faults found on the way (G1 to G8) were repaired and deployed; three (G9 to G11) stay open with work-arounds. Both halves each time, records first, local Gemma, `deploy/e2e_lab_check.py` 6/6 after each deploy. Root `f95f50f` and preview `df10ab6` untouched. Causes in [DECISIONS.md](DECISIONS.md) E025, "Round G"; the full table (rows J1 to J53) in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Round G, 23 October".

| Commit | AEDT, 23 October | What it carries |
|---|---|---|
| `0a7f612` | 22:21 | Due-date provenance names the actual decider: the owner, staff within the owner's authority, or the AI Agent under its role (the last attribution error from Round F; regression in `test_assessment.py`, `test_agent_account.py`, desk check D16) |
| `7bb2e09` | with 4b1b901 | One selected role shared by the Lab and the records UI for the AI Agent account (cookie `nucleonl_lab_role`, `POST /api/session/role`, a 409 `ROLE_CHANGED` for a marked request); fixes J12, where the records stayed Owner while the Lab showed Staff |
| `4b1b901` | 23:09 / 23:10 | G1 a staff message after any owner answer is a reply, not a concern round; G2 recorded payment terms in the overview; G3 who entered a payment or allocation; G4 `assessRequest` on a case still being prepared answers `CASE_PREPARING` and is not sent in the same turn as `openRequest`; G5 "current" resolves to the customer's one open case outside a case thread, clearer message, recovered tool errors show no alert; G6 the "understood" card with "nothing is recorded until you confirm it"; G8 staff cannot change the limits and the Lab says so. Prompt `lab-v0.12` (verbatim in PROMPTS.md) |
| `5282b3d` | 23:21 / 23:22 | G7 the recorded-reason guard runs after the private-context rewrite, so a quoted reason is kept (regression from the live turn); G4 follow-up: a same-turn assess ends with the request-opened card and one sentence, never a step-limit error. The final code commit of the round |

**Counts at `5282b3d`:** records 638, Lab 198, `lab_check` 218/218, `desk_check` 93/93, conversations on the mock 531/531. Prompt versions `coordinator-v0.12` (records, unchanged) and `lab-v0.12` (Lab).

**Files imported.** Raw export `1021/NTK Co 12mon (1).xlsx` (sha256 2f7fc6b7…, sheet "Báo cáo", 537 rows, Vietnamese headings on row 3, grouped by a "Tên KH : <name>" header row per customer) was tried first through the normal card: the first proposal mapped Customer to the group-header column (0 rows); after choosing CUSTOMER NAME in the card's own dropdown and Update proposal it read 21 customers, 137 invoices and 116 payments, but the file carries no credit-term or due-date column and no transaction-type column, so no due dates could be set and three netting rows counted as payments. It was not imported. Supported input: a sheet with one row per transaction, a customer name or code on every row, an invoice number, a document date, debit and credit columns, and either a credit term or a due date; a transaction-type column separates netting and adjustment rows. Hoang's cleaned workbook `NTK Co 12mon - Python cleaned.xlsx` (sha256 1969e373…, sheet "Cleaned Data", 511 rows) was then imported once with one press: 21 customers, 137 invoices, 113 payments, 60 allocations, 4 opening balances as at 2 Sep 2025. `deploy/validate_import.py` on a read-only copy reported 0 discrepancies against the workbook (customers, invoice totals including VAT, dates, payments, allocations, opening balances; corrected 24 Oct: the validator's hand replay then matched references without the payment date, so it could not see the three payment-before-invoice allocations, H1; the corrected validator on a fresh import gives 0 discrepancies with those references unmatched, see the Round H addendum). A repeat import of the same file was recognised as a duplicate (no Import button, no new records).

**Backups and restore.** Before the clearing: `~/srv/nucleon-lab/backups/lab-20261023-221041.sqlite3` and `lab-20261023-221041-before-journey-test.sqlite3` (records), `lab-conversations-20261023-221041-before-journey-test.sqlite3` (Lab conversations), and the console's own `lab-20261023-221125-before-reset.sqlite3`; the conversation store was retired as `lab-conversations-20261023-221147-retired-before-journey-test.sqlite3`. Each deploy added a records backup (`lab-20261023-222054`, `-230938`, `-232137`). To restore the pre-test state: records through the demo console's Restore from `lab-20261023-221041-before-journey-test.sqlite3`; conversations by stopping the Lab service, copying the retired file back to `data/lab-conversations.sqlite3` and `launchctl kickstart -k gui/$(id -u)/local.nucleon.lab`. No restore was performed; the test state is kept for review.

**Workspace state at the end of the round (kept, not cleared).** "NTK Co (team ledger, journey test)", VND, 0 decimals, Asia/Ho_Chi_Minh; authority 14 days, nothing else overdue, VND 500,000,000, 2 concern rounds. 21 customers, 137 imported invoices plus 00000099 (Customer 0014, VND 12,000,000, no due date, entered by hand), 113 imported payments plus one test payment (BANK-TEST-20261020, Customer 0014, VND 43,200,000, allocated to 00000053), 4 opening balances. Seven requests: 00000087 (Customer 0011) approved by staff within authority to 6 Nov; 00000079 (Customer 0001) approved by the owner to 13 Nov after a concern, an information-only question, two guidance answers and a staff reply; 00000081 (Customer 0012) declined by the owner; 00000099 (Customer 0014), 00000084, 00000082 and 00000073 (Customer 0018) with the owner, 00000084 carrying a concern, a guidance answer and a staff reply. The AI Agent login session and the Playwright evidence are retained.

**Findings of the round**
- G1, fixed (`4b1b901`, live J47 and J51): a staff report-back after an owner's guidance was stored as a second concern and counted toward the escalation rounds; it is now a reply.
- G2 and G3, fixed (`4b1b901`, live J50): the overview carries the recorded payment terms and who entered each payment or allocation, so "what terms are recorded" and "who recorded that payment" are answered from the records.
- G4, fixed (`4b1b901` and `5282b3d`, live J49): "open a request … then assess it" in one message produced a raw "Invalid JSON or field format." alert (an internal ValueError on a case still being prepared); the records now answer `CASE_PREPARING`, the Lab does not assess in the same turn, and the turn ends with the request-opened card and one sentence.
- G5, cause found and mitigated (`4b1b901`, live J48): the "current" refusals happened because a role switch returns the view to General (G9), so the message had no case thread; in a case thread "current" works, outside one it now resolves to the customer's one open case, and a refused call followed by a successful retry shows no alert.
- G6, fixed (`4b1b901`, live J43): an owner's "record a private note" produced a bare "I have understood…" with nothing stored and no card; the "understood" card now states that nothing is recorded until the owner confirms it on the records page, with the link, and a guard withholds a reply that omits this.
- G7, fixed (`5282b3d`, live J48): the two-part staff question (exact decline reason + what the owner shared) lost the reason because the private-context rewrite ran after the reason check and merged the sentences; the reason check now runs last and the fallback quotes the recorded reason.
- G8, fixed (`4b1b901`, live J40): staff asking to change the limits were told "I've noted the new limits"; the Lab now answers "Only the owner can change the limits (the Authority panel). Nothing was changed." with no tool call.
- G9, open (UX): switching Acting as returns the Lab view to General without saying so; the composer then posts to General. Work-around: re-open the case thread after a switch.
- G10, open (wording): owner guidance written on a case that has no staff concern is read as a statement to confirm on the records page, not as case guidance; the Lab does not say that case guidance answers a concern. Work-around: answer the staff concern.
- G11, open (model retrieval): a question by due date ("which invoices were due on 16 August 2026") was answered about an unrelated invoice; the all-invoices card on the same turn is right. Work-around: ask by invoice number.
- Cosmetic, open: the duplicate-import card reads "0 of them match … 73 name an invoice not in this file" for a file already imported; the staff answer about an approval names "the owner" rather than the AI Agent account; the first guidance card on a case says "The owner changed the guidance"; the stored intake text of a request typed by staff includes the staff instruction ("Then assess it") around the customer's words, although the case page underlines only the request.

#### Round H (23–24 October): date selection, role switch, guidance before a concern, J37 reconciled

A focused repair-and-verification round on the retained Round G workspace (not cleared, not restored). Both halves each time, records first, local Gemma, `deploy/e2e_lab_check.py` 6/6 after each deploy; root `f95f50f` and preview `df10ab6` untouched. Causes in [DECISIONS.md](DECISIONS.md) E025, "Round H"; the table (rows H1 to H18 and J37-R) in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Round H".

| Commit | AEDT, 24 October | What it carries |
|---|---|---|
| `dc8893f` | 00:24 / 00:25 | G11 `invoices` takes `dueOn`/`issuedOn`, rows say whether the original or the approved due date matched, a filter card and a guard; G9 the selected case survives a role switch; "current" outside a case thread resolves only with exactly one open case and otherwise asks which; G10 first guidance on a case reads "the owner gave guidance", case guidance before any concern is routed to answerConcern with a guard; H1 a payment reference matches only an invoice issued on or before the payment date, `validate_import.py` reports payment-before-invoice allocations; H2 the debt sentence names the remaining part of the opening balance; H3 Lab requests carry the tab's role and a stale tab gets 409 ROLE_CHANGED, a notice and a refreshed header |
| `a19f3d6` | 00:38 | G11 the prose names every date-selected invoice (the one-presentation rule had cut it to two sentences); H5 a saved guidance is never contradicted by a "no guidance saved" fallback; prompt `lab-v0.14`. The final code commit of the round |

Counts at `a19f3d6`: records 645, Lab 209, `lab_check` 224/224, `desk_check` 93/93, conversations on the mock 540/540. Prompt versions `coordinator-v0.12`, `lab-v0.14`.

**J37 reconciled independently.** A payment-by-payment re-implementation of the replay (ledger folder, `j37-breakdown-round-h.md`) shows for Customer 0018 as of 23 Oct 2026: open invoices VND 2,452,226,400 (00000070 in part, 00000073, 00000078, 00000082, 00000084), VND 85,779,000 of the VND 315,360,000 opening balance remaining (owed, age unknown, not overdue), total VND 2,538,005,400. The replay was right; the Round G hand expectation (opening balance untouched, credit ordered by due date) was wrong. The gap led to two defects, H1 and H2 below, both fixed.

**Remaining live checks (all on the retained workspace, fictional fixtures):** a staff payment BANK-TEST-20261023-STAFF (VND 7,000,000, Customer 0014) recorded and allocated to 00000066 by the AI Agent as staff, the Lab then reporting VND 41,060,000 still owed and the provenance (H1a–c); two fictional customers with invoices issued on the business date 23 Oct 2026: "QA Sameday 20261023" (QS-A VND 1,000,000 and QS-B VND 600,000,000) gave exposure VND 601,000,000 inclusive of today, 0 invoices and VND 0 before today, escalate with no Act (H2); "QA Sameday Small 20261023" (QS-C VND 1,000,000 and QS-D VND 2,000,000) gave VND 3,000,000, every check passing, and staff acted within authority (H3, H3b: decision by the AI Agent as staff, decisionSource staff_within_authority, followed the recommendation); the role switch is disabled while an answer runs (H4a); the historical same-day due dates (Customer 0018, 16 Aug 2026) are a separate retrieval test (H6, H15).

**Findings of the round**
- G11, fixed (`dc8893f`, `a19f3d6`; live H6, H7, H8, H15): a question by due date is answered by a deterministic filter on the original and the approved due date; three matches, one match, no match and an approved-date match verified live.
- G9, fixed (`dc8893f`; live H9, H10): the selected case stays after a Staff/Owner switch and the next message is stored in that case thread.
- "current" fallback, verified (`dc8893f`; live H12, H13, H14): with three open cases the owner is asked which (nothing prepared); with one and with none the model resolved the case itself through the case list, so the records-side rule for those two is covered by tests only.
- G10, fixed (`dc8893f`, `a19f3d6`; live H11, H16): an owner's case guidance before any staff concern is stored on the case with the next person set, shown as "Guidance on the case", and the prose agrees with the stored state.
- H1, fixed in the importer and the validator (`dc8893f`; live H5): a 2025 payment of Customer 0018 naming "54" was allocated VND 85,779,000 to invoice 00000054 issued 293 days later; two more allocations link a payment to an invoice issued 1–2 days later. The retained workspace keeps these three allocations until a re-import; the corrected replay for Customer 0018 would show the same total owed (VND 2,538,005,400) with all of it overdue.
- H2, fixed (`dc8893f`; live H17): the debt sentence named the full opening balance as included in the debt; it now names the remaining part.
- H3, fixed (`dc8893f`; live H18): a second tab executed a Lab turn under the role chosen in another tab while still showing the old role; it is now refused with a notice and the header refreshes.
- J37 corrected (H19 / J37-R): the hand expectation was wrong, not the replay; the "all figures matched exactly" claim is withdrawn for the overdue amount.
- Open, cosmetic: the refused stale-tab message is dropped rather than kept for re-sending; the opening-balance sentence repeats the figure; the one-open-case and no-open-case "current" paths were not exercised live by the model.

**Workspace additions (kept):** customers "QA Sameday 20261023" and "QA Sameday Small 20261023" with four invoices; payment BANK-TEST-20261023-STAFF; requests QS-A (with the owner), QS-C (approved by staff within authority); owner guidance on 00000082 and 00000073 (both now waiting on staff); an unconfirmed prepared decline on 00000099 (from the one-open-case check). The login session and the Playwright evidence are retained.

**Addendum (24 October, 01:30 AEDT): the validator's hand replay.** `61ab06b` fixes `deploy/validate_import.py`: `hand_replay()` matched payment references without the payment date, so the validator reserved early payments against later invoices as the old importer did and agreed with it on H1 for the wrong reason. The fix passes the payment's received date; the self-test gains three hand-computed regressions (the reproduction: opening 100, a payment of 100 naming an invoice issued later, as-of after its due date → debt 100, opening remaining 0, overdue 100; an ordinary match; an unmatched advance kept as credit), and the records suite runs the self-test (646). The commit touches no served code, so the deployed application stays `a19f3d6`. The cleaned workbook was imported into an isolated fresh database through the normal importer (57 allocations: the three issued-after references stay unmatched) and the corrected validator reports 0 discrepancies there; Customer 0018 then shows VND 2,538,005,400 owed, all overdue, and no opening balance remaining. The retained deployed workspace is unchanged and still holds the three allocations. Earlier "0 discrepancies" claims (Round G J6, Round H H5) are qualified in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md).

#### Finishing phase (24 October, overnight): calculation details, demo script, team briefing, full behaviour test

Three deliverables and a behaviour test on an isolated live pair (records and Lab started from a worktree on scratch ports with the local model, an empty workspace, fictional codes), so that resets, imports, policy changes and fixtures never touched the retained shared workspace. Both Lab halves were then deployed (records first, backups taken), `deploy/e2e_lab_check.py` 6/6, and a live smoke test run on the deployed Lab. Root `f95f50f` and preview `df10ab6` untouched. Causes in [DECISIONS.md](DECISIONS.md) E025, "Finishing phase"; the full table in [qa/LAB-CONVERSATIONS.md](qa/LAB-CONVERSATIONS.md), "Overnight finishing phase"; the demo script in [DEMO-SCRIPT.md](DEMO-SCRIPT.md); the team briefing in [reviews/2026-10-24-team-briefing.md](reviews/2026-10-24-team-briefing.md).

| Commit | Deployed (AEDT, 24 October) | What it carries |
|---|---|---|
| `0709426` | with 076d324 | Calculation details: `CALCULATION_VERSION = 'calc-v1'`; the replay records its own trail (per invoice issued, per payment: recorded allocations, oldest-first applications, to the opening balance, to customer credit, late marks; remainders, remaining opening balance, credit held; the stated-only, undated, no-due-date, unplaced and unreadable lists with their effects); the assessment stores a `basis` (records included with links, current exposure against strictly-prior history, missing information and assumptions, every policy check with actual value and threshold, the recommendation); a decision freezes the assessment it rested on in `decision.basis`; `GET /api/requests/<id>/basis`; the Lab's closed "Calculation details" section on assessment and decided cards; the records Evidence tab section; prompt lab-v0.15 |
| `8c9724c` | with 076d324 | O1 decided-case questions answered from the decision (outcome, decider, date, "not sent"); first attempt at the ambiguous-case rule; O2 "owed by the customer" wording; the Setup page no longer says imports are not in this version; prompt lab-v0.16 |
| `076d324` | 11:08 | The ambiguous-case check applies to every write outside a case thread whatever requestId the model found (the message must name the case or the customer, or there must be one open case); a date-dependent test fixed. The final code commit |

**Counts at `076d324`:** records 663, Lab 218, `lab_check` 236/236, `desk_check` 96/96, conversations on the mock 540/540. Prompt versions `coordinator-v0.12` (records, unchanged), `lab-v0.16` (Lab); calculation version `calc-v1`.

**What the browser tests covered with the live model (isolated pair, rows 1-1 to 6-2; 61 rows: 57 pass, 3 fail (2-5, 4-13 and 5-6, each fixed and re-tested as 5-1 and 5-10), 1 inconclusive (4-17a, environment)).** Clean start and import (setup, proposal with 57 matches and 3 issued-after references, one Import, duplicate refused, corrected validator 0 discrepancies with the source-data notes separated); the routine Staff journey (open-then-assess in one message with the card filling in place, assessment against the validator's figures, Act within authority, saved decision with actor, role, date, reason and basis, reload, retrieval); the exception and Owner journey (escalation with no Act, concern, role switch keeping the case, two-date compare without preparing, guidance kept with the owner then changed to require staff action with no invented reply, staff reply stored as a reply, approval and a separate decline through Confirm, the two-part reason question, owner-private context confirmed owner-only on the records desk and never surfaced to staff); boundaries (same-day invoices within and above the limit with inclusive exposure and strictly-prior history, a missing due date reported as unknown, changed evidence re-checked at execution, an authority change applied to new assessments only with the decision basis frozen byte for byte, date filters with three, one, no and approved-date matches, ambiguous customer and case references, stale role, role persistence, the switch disabled during an answer, staff and the model unable to change the limits); and the Calculation details compared with hand expectations on Customer 0005 and Customer 0018, in the Lab and on the records Evidence tab.

**Findings**
- O1, fixed (`8c9724c`; live 5-1 and the deployed smoke test): a staff question about a decided case ("what was decided, who decided it, has anything gone to the customer") was answered with invoice facts; it now answers from the decision and says the reply is a draft, not sent.
- O4, fixed for the action (`8c9724c`, `076d324`; live 5-10): "Decline the QA request" with three QA customers' cases prepared a decline on the thread's focus customer silently; now nothing is prepared and the open cases are listed. Open nit O7: the fallback wording names the focus customer rather than asking "Which case do you mean?".
- O2, fixed (`8c9724c`): "owed to the customer" wording is sent back to the model.
- Open cosmetic: O3 the stale Act card keeps its old Pass lines and buttons under the refusal alert; O5 the "Nothing else overdue" check row shows words instead of "VND 0 overdue besides this invoice" in the Actual cell when nothing else is overdue; O6 a refusal alert shown twice in a decided thread; O8 three retained Round H threads on the shared Lab still read "New request · Preparing" in the sidebar; the Setup page's "Not in this version" sentence (fixed); the duplicate-import card's references line and the two dates it shows (business date and real clock) for one import.
- Environment, not product: the isolated scratch Lab was stopped once by a concurrent scratch run's cleanup (4-17a) and restarted under a different process name; the stale-tab refusal path was therefore re-verified only through its tests and the Round H live check (H18), while the tab's re-read of the shared role on focus was observed live (4-17b).

**Rehearsal timing (observed, isolated pair, local Gemma).** Model latency per turn from the conversation store: open request 10–16 s, assessment 14 s (43 s for the first of the session, model cold), concern 11 s, compare 19 s, guidance 3–18 s, staff reply 14 s, prepare decision 16 s; median of the night's 24 turns 13.6 s, longest 44.9 s. The automated run spanned 2.6 min (Journey 1) and 9.8 min (Journey 2) because it paused 30–60 s to read each screen; a human-paced run is projected at about four minutes without the two optional owner steps, and still has to be timed before the recording.

**Shared workspace.** Unchanged in content: the retained Round G/H data, the three historical mis-allocations and the test history stay; the deploy added records backups (`lab-20261024-110204.sqlite3`, the deploy's own) and a conversation-store copy (`lab-conversations-20261024-110205-before-overnight-deploy.sqlite3`). The isolated pair's database and conversation store are in the session scratchpad (`live/records.sqlite3`, `live/lab-conversations.sqlite3`) with the import copy `overnight-after-import.sqlite3`.

### Fifth deploy (24 October, 17:22 AEDT): final repair and acceptance round, `ac87e27`

- **Deployed:** `ac87e27` to both Lab halves from the pushed branch `explore/agent-coordinator-20261019` (fa40855..ac87e27 pushed first). `nucleonctl deploy ac87e27`: 670 tests OK, ready on 127.0.0.1:8623 (17:22:18–17:22:47); `labctl deploy ac87e27`: web built, Lab tests OK, ready on 127.0.0.1:8622 (17:22:47–17:22:55). Root site `f95f50f` and preview `df10ab6` untouched; nothing merged into main.
- **Backups before the deploy:** `backups/lab-conversations-20261024-172217-before-final-round-deploy.sqlite3` (integrity ok, 126 turns) taken by hand; `backups/lab-20261024-172218.sqlite3` (9 requests, 276 events, integrity ok) taken by `nucleonctl deploy` before switching. The labelled `nucleonctl backup <label>` form expects a database path, not a label, and printed a traceback; it was not relied on.
- **After the deploy:** `deploy/e2e_lab_check.py https://nucleon.dracooz.top` 6/6; signed-in checks on the deployed Lab: build line `ac87e27`, presenter panel on the fictional workspace, retained threads titled from the records, the pre-calc-v1 decision's note "Calculation details were not recorded by the application version that made this decision (before calc-v1)", one live staff smoke turn answered from the decision, Keep warm pings 0.3 s. Shared workspace, test history, sessions and the three retained mis-allocations unchanged.
- **What the release carries** (after `076d324`): `3abff6b` interface states follow the records after a refusal, a reload or a role switch; `8ea5ee2` truthful failure recovery and writes keyed by the turn (a resend writes once; no automatic replay); `a4faa3a` per-request and per-phase latency in the turn meta, owner-only staff asks answered without the model; `5f385ae`, `5318e61`, `16d3ac9` the opt-in presenter panel (fictional only, right-hand column, Keep warm 30 s kept per tab, never presses Send/Act/Confirm); `c167509`, `2b6018c`, `ac87e27` guards for the owner's private note, ambiguous customer references and staff pointed at a missing Act. No caching of model answers.
- **Latency finding:** the long first turns (105–141 s before, 199 s once) are the local model paged back in after about 90 s idle on the 32 GB machine with swap nearly full; a 6.3k-token prompt costs about 6 s on an active model and the tool schemas add nothing measurable. With Keep warm on, Journey 1's first request fell from 141 s to 7.8 s. Operator rule: Keep warm on (or a message every minute) and quit memory-heavy applications before the demo.
- **Rehearsals** (operator-paced on fresh isolated workspaces): 4:23 and 4:29; target 3:30–3:45 not reached at 10–15 s narration per card (see `docs/DEMO-SCRIPT.md`).
- **Counts at `ac87e27`:** records 670, Lab 244, `lab_check` 275/275, `desk_check` 97/97, conversations on the mock 540/540; prompts `coordinator-v0.12`, `lab-v0.17`; `calc-v1`.

### Sixth deploy (24 October, 22:34 AEDT): replay, balance and stale-instruction round, `0d54e9f`

- **Deployed:** `0d54e9f` to both Lab halves from the pushed branch `explore/agent-coordinator-20261019` (65ccd83..0d54e9f pushed first). `nucleonctl deploy 0d54e9f`: 687 tests OK, ready on 127.0.0.1:8623; `labctl deploy 0d54e9f`: Lab tests OK, web built, ready on 127.0.0.1:8622. The root site (`f95f50f`) and the preview (`df10ab6`) were not touched; nothing merged into main.
- **Backups before the deploy:** `backups/lab-conversations-20261024-223431-before-replay-round-deploy.sqlite3` taken by hand (integrity ok, 128 turns, 10 threads); `backups/lab-20261024-223434.sqlite3` (9 requests) taken by the records deploy.
- **Migration:** the conversation store gained `turns.reply_to` (the person turn an agent turn answers) on start; the 128 earlier turns are unchanged and keep it empty (an older answer is replayed only when it is the very next row with the same visibility).
- **After the deploy:** `deploy/e2e_lab_check.py https://nucleon.dracooz.top` 6/6. Signed in as the AI Agent on the deployed Lab: build `0d54e9f`, presenter panel on the fictional workspace; Keep warm went from off to "Model ready: … took 0.2 s" and was switched off again; the retained 00000079 case (decided 23 Oct) shows its earlier answers folded under "What the Lab said at the time" with "Since this answer: approved to Fri 13 Nov 2026 by AI Agent (as owner) on 23 Oct 2026." and no Confirm text or button; one staff smoke turn in General ("What does Customer 0012 owe now, and how much of it is overdue?" → "Customer 0012 owes VND 272,687,040 (worked out), and all of it is overdue.", 15.5 s), stored as turns 129–130 with the answer linked to its message.
- **What the release carries** (after `ac87e27`): `732165f` replay answers only the turn it belongs to and only to a role that may see it, conflicting turnIds refused, truthful unsaved replies; `171fe39` Keep warm on the server with truthful readiness (`9d21aba` adds "slow" and a warm-up history); `4e120d0`, `df2abb8`, `06d559c` what a customer owes (owed now from the replay, its parts, the recorded net only under its own label, counts and the case invoice from the same figures); `36252ae` prompt versions `coordinator-v0.13`, `lab-v0.18`; `e0267fa` earlier answers fold behind what the records now say; `b28410d`/`da6f501` overdue by the original due date named; `8df738c` an assessment that no longer holds drops Act; `44b1d33`, `afa50fc`, `79dd6bc`, `0d54e9f` presenter Fill and Open case; `a8ab624` the phone key line.
- **Correction to the fifth deploy's latency finding:** the long first turns were not the model paged back in after idle. Every slow request measured on 24 October (afternoon and evening) coincided with a generation by another application on this network using the same LM Studio model, which serves one request at a time. See `docs/DEMO-SCRIPT.md`, "Observed timings".

## Current release: interface redesign (18 October 2026, 23:24 Sydney)

- **Deployed application revision:** `f95f50f`, from branch `feat/ux-redesign-20261018`, not merged into main. It replaced `a9ce30d`, at Hanting's explicit instruction.
  - `f95f50f` is the reviewed candidate `33272b7` plus one fix found after deploying it, deployed on Hanting's approval.
  - The candidate brings the task-area interface (E013), the review changes (E014: sign-out, the phone customer page, evidence keys format 2 with a startup migration), and revert provenance and the sign-out wording (E015).
  - **The fix:** `33272b7` went live at 23:14. 24 of 30 fresh loads of the public sign-in page then lost at least one file to a 502. Caddy logged "dial tcp 127.0.0.1:8620: connect: connection reset by peer". The redesigned page opens 8 connections at once (the earlier page opened 3), and Python's default listen queue of 5 reset the rest. `f95f50f` raises the queue to 128 and adds a regression test. Afterwards 0 of 30 fresh loads failed. The same 502s appear in the Caddy log on 16 and 17 October, under earlier releases.
- **Config:** unchanged. `service.json` equals `production.json` (port 8620, live model, `publicOrigins`, demo console, `sampleData` for this practice instance).
- **Data:** nothing reset or removed. All 7 earlier cases, their decisions and flags, the sample, the testers' records and imports, and the earlier "Release check café (fictional)" are kept.

**Before the deploy** (all on copies; the service untouched until step 3):
1. **Running state:** `a9ce30d` on `data/nucleon.sqlite3`, live mode; loopback and HTTPS 200. The candidate `33272b7` was the pushed branch head, and the server's checkout was clean. The control script, launch agent, Caddy site and config shape are unchanged by the release.
2. **Fresh copy:** `nucleonctl clone-db` → `data/test-ux-predeploy.sqlite3`: integrity ok; 7 cases, 161 events, 6 imports, 8 customers, 11 invoices, 5 payments.
   - **Provenance scan** (`deploy/provenance_scan.py`, the candidate's): no record credited by the old revert rule, none credited to a reverted import, and no kept conflicts.
   - **Migration rehearsal** with an export of exactly `33272b7`, first start on a further copy:
     - 3 decided cases re-baselined, 3 pending cases re-stamped, 0 flagged, 0 disagreements backfilled;
     - every case kept its status, version, flags and decision; the analyses were unchanged apart from the evidence-version stamp;
     - the only new events were the format events; no case was queued for preparation again;
     - records and imports identical; a second start changed nothing.

**Backups** (in `~/srv/nucleon/backups/`):
| When | Database | Configs and revision note |
| --- | --- | --- |
| Before `33272b7`, service stopped | `nucleon-20261018-231400.sqlite3` (integrity ok; 7 cases, 161 events; evidence keys as `a9ce30d` wrote them) | `predeploy-ux-20261018-231359/` (`production.json`, `service.json`, `REVISION`: `a9ce30d`) |
| Taken by `nucleonctl deploy 33272b7` | `nucleon-20261018-231404.sqlite3` | |
| Before `f95f50f`, service stopped | `nucleon-20261018-232355.sqlite3` (integrity ok; 7 cases, 167 events; evidence keys format 2) | `predeploy-queue-20261018-232354/` (`REVISION`: `33272b7`) |
| Taken by `nucleonctl deploy f95f50f` | `nucleon-20261018-232359.sqlite3` | |

**After the deploy** (production database, public URL):
| Check | Result |
| --- | --- |
| Unit suite run by `nucleonctl deploy` | 247 OK (`33272b7`), 248 OK (`f95f50f`) |
| `nucleonctl status` | Running `f95f50f` on `data/nucleon.sqlite3` in live mode; loopback and HTTPS 200 |
| Evidence-key migration (startup log, at the first start of `33272b7`) | `evidence keys: format 2 {'rebaselined': 3, 'restamped': 3, 'flagged': 0, 'disputes': 0}`, the same as the rehearsal on the fresh copy. Case by case against `nucleon-20261018-231400`, all 7 cases kept status, version, flags and decision, and records and imports are identical. The restart for `f95f50f` ran no migration (the marker is set). |
| Fresh loads of the public sign-in page | 24/30 lost a file under `33272b7`; 0/30 under `f95f50f` |
| `e2e_records_check.py production --compare backups/nucleon-20261018-231400.sqlite3` (read-only) | 15/15, under both revisions |
| `layout_check.js` (read-only, public URL) | 12/13 under `33272b7` (the Imports page script lost to a 502); 156/156 under `f95f50f` |
| `e2e_stage3_check.py smoke` (writes one labelled customer) | 26/26, with live Gemma. The 7 existing cases were compared before and after: no new flag, no re-preparation, no new event. |
| Browser, public site (read-only; staff): the five areas after a reload, the deployed scripts served, a case to its customer and back, Imports and an applied import's "What reverting would do", sign-out confirmed with the server, 390 px phone layout (bottom bar, no sideways scroll, a customer page with "Add invoice" on the first screen), no script errors or 5xx | 15/15. Screenshots in `~/srv/nucleon/reports/ux-deploy-20261018/` (no codes). |

**Left on the shared instance by the checks:**
- the customer "Release check café 1018122524 (fictional)", its invoices (RC1018122524, -77, -78), a credit, a payment, its opening balance and its completeness statement;
- case `req_d043fff343c27954`: approved for Fri 6 Nov 2026, with the reply drafted and not sent.

All of it is clearly labelled, and nothing else was changed. The copies `data/test-ux-predeploy`, `-postdeploy`, `-presmoke` and `-postsmoke` were left in place, like the earlier test databases.

**Rollback from `f95f50f`:** the earlier release would read the format-2 evidence keys as changes. So never run earlier code on this database:
1. `nucleonctl backup`, to keep the current state.
2. `nucleonctl stop`.
3. Copy `backups/nucleon-20261018-231400.sqlite3` over `data/nucleon.sqlite3`, removing `-wal` and `-shm`.
4. Restore the configs from `backups/predeploy-ux-20261018-231359/` if they changed.
5. `nucleonctl deploy a9ce30d`.

This discards everything recorded since 23:14, which is why step 1 keeps it.

## Previous release: phone top-bar fix (18 October 2026, 14:45 Sydney)

- **Deployed application revision:** `a9ce30d`. It replaced `4f45ca7` (Stage 3).
  - The only application change is the stylesheet: at 820 px and below, the top bar wraps its controls onto a second row instead of widening the page. Every control stays visible, and nothing clips overflow page-wide.
  - No behaviour, data or config change.
- **Check tools:**
  - `deploy/layout_check.js` is new and read-only; together with the corrected phone checks in `browser_check.js`, it is in `a9ce30d`.
  - The production comparison's sample check was corrected in `0854b86`. It had assumed the sample was the only record set.
  - This record is the commit that adds it. The application code in both commits is identical to `a9ce30d`, and the server's checkout is `a9ce30d` exactly.
- **Backups:**
  - **Before the deploy:** `backups/nucleon-20261018-144453.sqlite3` (4 cases; integrity check ok), taken with the service stopped.
  - **Config files and revision note:** `backups/predeploy-topbar-20261018-144453/`.
  - `nucleonctl deploy` took its own copy too: `backups/nucleon-20261018-144501.sqlite3`.
- **Config:** unchanged. `sampleData` stays on for this practice instance only.
- **Data:** untouched. No reset and no deleted cases. All 4 cases, the sample, and the labelled "Release check café (fictional)" customer and case remain. The disposable test databases were left in place.

**What `layout_check.js` measures.** It measures real layout boxes against the configured width, not `innerWidth`.
- **Widths:** 375 and 390 px, each with and without mobile emulation, and 1366 px.
- **Pages:** the case list, a case, Records and the demo console.
- **On each page:**
  - the document is no wider than the configured width;
  - every top-bar control is inside the viewport and not covered;
  - nothing outside a scroll box sticks out.
- **Actions:** Staff ↔ Owner switching, the Records link, the brand back to the cases, opening the console (nothing is reset), signing out of every role, and no script errors.
- It submits nothing, so it is safe on this instance.

**Before the deploy.** These ran on a local server of the fix with the demo console enabled, on a copy of the production database.

| Check | Result |
| --- | --- |
| `layout_check.js` against the previous release (public URL, read-only) | 64/100. The defect reproduced: the document was 430–441 px wide at 375 and 390 px, and Sign out was off-screen. Desktop passed. |
| `layout_check.js` against the fix | 100/100 |
| Width sweep, 320–1366 px in 2 px steps, case list and Records | No document or top-bar overflow at any width. The bar wraps to two rows (83 px) below about 450 px. |
| `browser_check.js` live and `--records` (scratch databases) | 27/27, 11/11 |

**After the deploy** (production database, public URL):

| Check | Result |
| --- | --- |
| Unit suite run by `nucleonctl deploy` | 215 tests OK |
| `nucleonctl status` | Running `a9ce30d` on `data/nucleon.sqlite3` in live mode; loopback and HTTPS 200; the served stylesheet has the fix |
| `e2e_records_check.py production --compare backups/nucleon-20261018-144453.sqlite3` (read-only) | 14/14. The first run was 13/14 because the check assumed sample-only records; the check was corrected in `0854b86` with no application change. |
| `layout_check.js` (read-only) | 100/100 |

**Rollback from `a9ce30d`:** with the production config active, run `nucleonctl deploy 4f45ca7`. Only the stylesheet differs, so the database needs no restore.

## Earlier release: Stage 3 (18 October 2026, 14:33 Sydney)

- **Deployed application revision:** `4f45ca7`. It replaced `89b92d8` (Slice 2).
  - It adds records in tables, payments and credits with explicit allocation, payment-list import, opening balances and inclusion, completeness statements, and exact amounts only from complete records (E008–E010).
  - The release-check tools and these instructions are on `efff0fd` (and its record, this commit). The application code there is identical to `4f45ca7`; the server's checkout is `4f45ca7` exactly.
- **Backups:**
  - **Before the deploy:** `backups/nucleon-20261018-143302.sqlite3` (3 cases), taken with the service stopped.
  - **Config files and revision note:** `backups/predeploy-stage3-20261018-143302/`, holding `production.json`, `service.json` and `REVISION`.
  - `nucleonctl deploy` took its own copy too, at the same moment: `backups/nucleon-20261018-143308.sqlite3`.
- **Config:** unchanged. `production.json` keeps `"sampleData": true`; this is the shared practice demo, and no real records were introduced.
- **On first start**, the production database moved into tables: 2 customers, 3 invoices and 3 notes, with the document fingerprint stored. All 3 cases were kept with their status, and the two pending briefs were re-stamped, not prepared again.

**Isolated checks before the release.** These ran through `https://nucleon.dracooz.top`, with the service on disposable databases and running `4f45ca7`.

| Check | Database | Result |
| --- | --- | --- |
| `e2e_records_check.py production --compare` | `test-s3-release` (a copy of production) | 14/14 |
| `e2e_stage3_check.py smoke` | the same copy | 26/26 |
| `e2e_stage3_check.py full` (live Gemma), then `nucleonctl restart`, then `after-restart` | `test-s3-full` (empty practice) | 53/53, 10/10 |
| `e2e_stage3_check.py fallback` (`isolate … unreachable-model`) | `test-s3-fallback` | 19/19 |
| `browser_check.js --records` | `test-s3-brecords` | 11/11 |
| `browser_check.js` (live) | `test-s3-blive` (practice with the sample) | 27/27 |

Earlier the same day, the full suite ran against local servers of the candidate ("Release validation" below). It was not rerun, because no code changed.

**Live checks after the deploy** (production database, public URL):

| Check | Result |
| --- | --- |
| `e2e_records_check.py production --compare backups/nucleon-20261018-143302.sqlite3` (read-only): sign-in and cookies, practice workspace, sample, every case and status, pending cases readable, Records data and script, console | 14/14 |
| `e2e_stage3_check.py smoke`: one labelled fictional customer ("Release check café (fictional)"); an opening balance whose make-up a person confirmed; a credit and a payment applied; completeness; "AUD 400.00 (exact, as of Fri 16 Oct 2026)" in the owner case prepared by live Gemma; an approved decision with an unsent reply draft; sample records untouched | 26/26 |
| Browser, read-only (owner): sign-in form, case list (4 cases), Records page with the new rows; no script errors | passed |

**Left on the shared instance by the checks:** the fictional customer "Release check café (fictional)", its records, and one completed case. These are clearly labelled. The demo console's **Reset demo data** clears them, together with every other case, after saving a backup.

**Known issue at this release, existing since before it; fixed by `a9ce30d` (see Previous release: phone top-bar fix).** On a 390 px phone with the demo console enabled, the top bar is 441 px wide ("Sign out" ends off-screen), so the page scrolls sideways.
- `89b92d8` shows the same, measured the same way.
- `browser_check.js` missed it: it compares with `innerWidth`, which mobile emulation widens to fit the content.
- Fixing it needs a code change and a new candidate.

**Rollback from `4f45ca7`:**
1. `nucleonctl backup`, to keep the upgraded state.
2. `nucleonctl stop`.
3. Copy `backups/nucleon-20261018-143302.sqlite3` over `data/nucleon.sqlite3`, removing `-wal` and `-shm`.
4. Restore the configs from `backups/predeploy-stage3-20261018-143302/` if they changed.
5. `nucleonctl deploy 89b92d8`.

This discards everything recorded since the deploy, which is why step 1 keeps it. Rehearsed 14/14 (`deploy/rehearse_stage3_upgrade.py`). A code-only rollback is not enough (see "Next release" below, kept for its record).

## Earlier release: Slice 2 (18 October 2026, 01:16 Sydney)

- **Deployed:** `89b92d8` (Slice 2: workspaces, Records, CSV invoice-list import). It replaced `d59af7a` at 01:16 Sydney time on 18 Oct.
- **Before the deploy:**
  - **Database:** `backups/nucleon-20261018-011602.sqlite3` (3 cases).
  - **Config files and previous revision:** `backups/predeploy-slice2-20261018-011602/`.
- **Config:** `production.json` now has `"sampleData": true`. This instance is the shared **practice** demo. Never copy this setting to a config used for real records.
- **On first start**, the production database was recorded as a practice workspace ("migration"). Its sample and all 3 cases are unchanged, and the two cases waiting for the owner kept current evidence.

**Rollback from `89b92d8`:**

1. **If nobody added records on the Records page since the deploy:** run `nucleonctl deploy d59af7a`. The previous release reads a migrated database; this was checked on 18 Oct by running `d59af7a` against a migrated copy (login, case list and a pending case all work).
2. **If records were added after the deploy:** the previous release cannot read the new record fields. Run `nucleonctl stop`, then copy `backups/nucleon-20261018-011602.sqlite3` over `data/nucleon.sqlite3` (remove its `-wal`/`-shm` first), then `nucleonctl deploy d59af7a`. This loses changes made after the deploy, so back them up first with `nucleonctl backup`.
3. **Config:** restore `production.json` from `backups/predeploy-slice2-20261018-011602/`, or simply remove `"sampleData"`, which the previous release ignores. Then run `nucleonctl production`.

**Checks after the deploy** (`deploy/e2e_records_check.py`; all fictional; isolated databases for anything that writes):

| Check | Result |
| --- | --- |
| production (read-only): workspace, sample, every case and status compared with the backup, pending cases readable, Records script served | 14/14 |
| practice (fresh isolate, sampleData): manual customer; an invoice number another customer also has; live-Gemma case where staff choose, then owner decision; CSV preview, apply and re-import | 24/24 |
| empty (database seeded as an empty practice workspace): stays empty despite sampleData; requests refused until setup; settings, manual invoice, live case to decision, unknowns stated | 16/16 |
| real (seeded real workspace): sample refused, no console; settings, CSV import and re-import, live case to decision | 23/23 |
| existing `e2e_https_check.py` (fresh isolates): approve / clarify / console | 30/30, 22/22, 27/27 |
| existing `browser_check.js` (live, headless Chromium) | 27/27 |

Screenshots: `docs/screenshots/9-records-setup.png`, `10-import-preview.png` and `11-shared-number-choice.png`, taken on an isolated practice database through the public URL.

Not checked on the deployed instance: the first-run choice screen. With `sampleData` on, a fresh database starts as practice with the sample. The screen was checked locally on 17 Oct.

**Fixed access codes (23 October, 01:40 AEDT).** `c2dbb3d` adds an `accessCodes` option to the records config for demo instances; the Lab's records half runs it with short fixed codes set in `config/service.json`, so the codes no longer change on restart. They are given out privately, never written here. Remove the option for real records.

**Guard fix after the boundary review (23 October, 15:44 AEDT).** A focused review of the repair commits found one important weakness: the exemption for quoted recorded lines also stripped the same sentence when unquoted, so a restatement of a recorded reason could pass the claim check as the assistant's own claim. `0711955` limits the exemption to quoted text of twelve or more characters (Lab test added); deployed to the Lab half at 15:44 AEDT (`deploy/e2e_lab_check.py` 6/6). The records half stays at `eb8eef0` (no records code changed). The deployed application is therefore `0711955`.

**Repair D (23 October, 17:59 AEDT).** The reviewer reproduced a second false-authorisation path at `0711955`: an active invoice with a total and a stated amount but no issue date was dropped from the current facts (and the overdue check) because the selection still required an issue date; a 600,000,000 overdue invoice vanished and a 1,000,000 request became eligible within staff authority. Rule now (`prototype/behaviour.py`): every active record with any amount counts for exposure and, when its due date is known, for overdue; missing timing excludes it only from the strictly-prior history, with a stated basis sentence; a record the replay cannot place (an open invoice with no due date; a payment with no received date and no allocation; an allocation to an invoice that is not in the records) makes the assessment incomplete, the recommendation escalate and `actWithinAuthority` refused. Every exclusion branch was audited (list in the ledger). Six regressions fail at `0711955` and pass at `2c30d9f` (records suite 615, Lab 178, `lab_check` 185/185, `desk_check` 78/78, conversations mock 522/522). Deployed to both halves at 17:59 AEDT (`deploy/e2e_lab_check.py` 6/6). Live reproduction on the Lab with a fictional customer (a dated 1,000,000 invoice entered in the form; the undated 600,000,000 invoice inserted directly, since the form and the importer refuse a missing date): the assessment shows VND 601,000,000 owed, VND 600,000,000 overdue 22 days, the overdue and amount checks failing, "Escalate to the owner", and no Act button; the stored recommendation is escalate. The deployed application is `2c30d9f`.

### Stage 3 release preparation (deployed 18 Oct 2026 at 14:33; see Earlier release: Stage 3 above; kept as the record of how it was prepared)

It covers payments and payment import, opening balances, completeness statements and exact amounts. It has been built and checked on scratch databases and fresh copies of the production database. **It is not merged or deployed**; deploying it is a team decision.

**What the first start does.**
- It copies the records document into tables and checks the copy is lossless. From then on the document row is a frozen snapshot that this release never writes.
- Cases waiting for the owner keep their prepared brief: their evidence version is re-stamped, not prepared again.
- Decided cases get a baseline, so that later records changes are flagged on them.
- No configuration change is needed. Keep `sampleData` on this practice instance only.

**Rehearsal on 18 Oct.** Command: `deploy/rehearse_stage3_upgrade.py`, run on fresh copies of `data/nucleon.sqlite3`, which was only read. It used `89b92d8` extracted with `git archive`, and the test agent. Result: **14/14**, and 14/14 again after the correctness pass (E010).

| Step | Result |
| --- | --- |
| Upgrade a copy | Records unchanged; all 3 cases kept with their status; both pending briefs re-stamped, not prepared again |
| Use it | A payment, an allocation, an answer, an opening balance, a completeness statement and a decided request recorded |
| **Code-only rollback** (`89b92d8` on the upgraded copy) | It starts. It shows the records **as they were at the upgrade**: no payments, opening balances or completeness, and none of the Stage 3 answers. Cases, including the decision made after the upgrade, are still listed. After it saved one records change, Stage 3 **refused to start** and named the reason |
| **Restore rollback** (pre-upgrade backup, then `89b92d8`) | It starts, with cases and records exactly as before the upgrade |
| Forward again (Stage 3 on its own copy) | Everything made after the upgrade is there |

**What each rollback discards:**
- **Restoring the pre-upgrade backup** discards everything after the upgrade. In the rehearsal that was:
  - 1 payment, 1 allocation, 1 opening balance and 1 completeness statement;
  - 65 events;
  - the new decided request;
  - the state changes of a pending case. The test agent can't read natural-language dates, so it re-prepared that case into "needs information"; live Gemma would not.

  In general it also discards imports, answers, corrections, notes and every request, decision or reply made after the upgrade.
- **A code-only rollback** discards nothing, but **hides** everything made after the upgrade: records, answers and statements. The previous release then works from the frozen snapshot.
  - Any records change it saves is written only to that snapshot.
  - Stage 3 then refuses to start rather than ignore it.
  - Use it only for a quick look. The way back after any change is the restore rollback.

**Rollback procedure:**
1. `nucleonctl stop`.
2. Back up the current database with `nucleonctl backup`. It holds everything since the upgrade, in case it is needed.
3. Copy the backup taken before the deploy over `data/nucleon.sqlite3`, removing `-wal` and `-shm`.
4. `nucleonctl deploy 89b92d8`.

**Measured cost (fictional data, this Mac, after E010).** Measured with `prototype/perf_records.py` and a headless Chromium page load.

| Records | Records page (server) | Evidence | Prepare one case (test agent) | One records change | Page load in the browser |
| --- | --- | --- | --- | --- | --- |
| 515 | 0.01 s | 0.01 s | 0.02 s | 0.02 s | – |
| 5,150 | 0.16 s | 0.10 s | 0.23 s | 0.26 s | about 1 s |
| 20,600 | 0.81 s | 0.54 s | 1.33 s | 1.37 s | 2.6–3.2 s (17.5 MB, about 17,000 table rows) |

The cost was per invoice × all records before E010. At 5,150 records that meant 1.96 s for the page and 4.66 s per case; at 20,600, 45.5 s and 84.9 s. A live case adds the model's 7–13 s.

**Release blockers** (Stage 3 to the shared practice demo):
1. **A team decision** to merge and deploy (not taken).
2. **Deployed-URL checks** on an isolate of the service. They need the shared service, so were not run: `deploy/e2e_records_check.py` (all scenarios), `deploy/e2e_https_check.py` and `browser_check.js`. `browser_check.js` may need updating, because the Records page changed.
3. **At deploy time:** a fresh backup and a fresh rehearsal (below).

None of these is a code defect known today.

For real records, beyond the practice demo, these are still open:
- the business questions in P002 13.2: B4, B6, B7, B8 and B9;
- usability with real staff;
- an opening-balance file import: opening balances are entered by hand, one customer at a time;
- credit-note documents: credits are recorded only as amounts held;
- record volumes far beyond 20,000. The page draws every row; drawing rows per customer on demand would be the next step.

**Release validation, 18 Oct 2026 (candidate `4f45ca7`; check tooling `2d5591f`, application code identical).** These checks ran against local servers of the candidate, on copies or fresh databases, with the production config (live Gemma) and the demo-console backups redirected to a scratch folder. They do **not** cover Caddy, TLS or the launchd service; only the deploy below does.

| Check | Result |
| --- | --- |
| `e2e_records_check.py production --compare` (a copy of production under the candidate) | 14/14 |
| `e2e_records_check.py` practice / empty / real | 24/24, 16/16, 23/23 |
| `e2e_https_check.py` approve, restart, stale, change-date, decline, clarify, console | 30/30, 9/9, 13/13, 17/17, 16/16, 22/22, 27/27 |
| `e2e_https_check.py` fallback-unavailable, fallback-invalid, legacy (`test-legacy-approve` copy) | 12/12, 12/12, 12/12 |
| `e2e_stage3_check.py` full (live Gemma), after-restart, fallback, smoke (production copy) | 53/53, 10/10, 19/19, 26/26 |
| `browser_check.js` live, --fallback, --legacy, --records | 27/27, 9/9, 7/7, 11/11 |
| `live_gemma_check.py` | 15/15, 0 rejected tool calls |
| `rehearse_stage3_upgrade.py` (fresh copies of production) | 14/14 |

**Deploy attempt, 18 Oct 2026, stopped before any candidate code ran on the service.**
1. Production was backed up: `backups/nucleon-20261018-141726.sqlite3` (3 cases).
2. A copy was made (`data/test-s3-prodcopy.sqlite3`) and the service was isolated on it, still running `89b92d8`.
3. `nucleonctl deploy 4f45ca7` was then refused by the session's permission rules, which ask for explicit approval of a production deploy.
4. The service was put back on the production config at `89b92d8`. Its database was never opened by Stage 3 code (no Stage 3 tables, the same 3 cases).

**Remaining steps once the deploy is approved** (run on the server):
1. `nucleonctl clone-db ~/srv/nucleon/data/nucleon.sqlite3 s3-release && nucleonctl isolate s3-release`
2. `nucleonctl deploy 4f45ca7`: this restarts on the isolated copy, because `deploy` uses the active config.
3. Through the public URL:
   - `e2e_records_check.py production --compare <backup>`, then `e2e_stage3_check.py smoke`;
   - on fresh isolates: `e2e_stage3_check.py full`, `nucleonctl restart`, `after-restart`;
   - `e2e_stage3_check.py fallback` (`isolate … unreachable-model`);
   - `browser_check.js --records` and `browser_check.js` (live).
4. The release:
   - `nucleonctl stop`;
   - `nucleonctl backup`;
   - copy `config/production.json` and `config/service.json` to `backups/predeploy-stage3-<time>/`, with the previous revision `89b92d8`;
   - `cp config/production.json config/service.json`;
   - `nucleonctl deploy 4f45ca7`.
5. Verify on production:
   - `e2e_records_check.py production --compare <that backup>`;
   - `e2e_stage3_check.py smoke`: one labelled fictional customer and one decision.
6. If anything fails:
   - keep a copy of the failed upgraded database (`nucleonctl backup`);
   - then follow the rollback procedure above.

**Before deploying:**
- Back up the database.
- Rerun the rehearsal on a fresh copy, plus the deployed-URL checks in an isolate: `nucleonctl clone-db` and `isolate`, then `deploy/e2e_records_check.py` (all scenarios), `deploy/e2e_https_check.py` and `browser_check.js`. These were **not** run against Stage 3, because they need the shared service.
- Run `prototype/live_gemma_check.py` (14 scenarios).

## Demo reset and recovery

The demo console is enabled in `config/production.json` (`"demo": {"enabled": true, "backupDir": "/Users/jason/srv/nucleon/backups"}`). Use it between demonstrations:

1. Sign in with the OPERATOR code and open **Demo console** from the top bar.
2. **Reset demo data** backs up the current data, then clears every case and restores the original fictional invoices and due dates. Sign-ins and settings stay as they are.
3. Reset by mistake? Click **Undo** straight away, or **Restore** any backup listed under **Backups**. A restore saves the cases it replaces as a new backup first.

If the console itself isn't reachable, restore a backup by hand:

```bash
~/srv/nucleon/bin/nucleonctl stop
cp ~/srv/nucleon/backups/<backup>.sqlite3 ~/srv/nucleon/data/nucleon.sqlite3 && rm -f ~/srv/nucleon/data/nucleon.sqlite3-wal ~/srv/nucleon/data/nucleon.sqlite3-shm
~/srv/nucleon/bin/nucleonctl start
```

Every deploy also saves a backup (`nucleon-<date>-<time>.sqlite3`); the console lists those alongside its own reset and restore backups.

**Rollback:**

- Run `nucleonctl deploy <previous sha>`; the deploy takes a backup first.
- Rolling back from the redesign (`01b154c` and later) to `23e6bdb` was tested on a copy of new-release data:
  - the older release ignores the new `meta` table and lists and reads the cases;
  - it doesn't know the per-role cookies, so people sign in again;
  - the demo console isn't available in the older release.
- No schema migration was needed for the structured-brief release; stored records are JSON and readable in both directions.
- The previous release (`8c15be0`) can still open and decide records written by this one. It shows only the code-written summary of a `brief-v2` brief, because it does not know the new fields.
- To return to a database state from before a deploy, stop the service and copy the backup file over `data/nucleon.sqlite3`.
- **Branch `feat/ux-redesign-20261018`, when it is deployed: roll back by restoring the backup, not by redeploying alone.**
  - At its first start it moves stored evidence keys to format 2 ([EVIDENCE-KEYS.md](EVIDENCE-KEYS.md)), and logs `evidence keys: format 2 {…}` with the counts.
  - `a9ce30d` would read format-2 keys as changes: at its first records change it would flag every decided case, and at startup it would prepare every pending case again.
  - So first `nucleonctl stop`, then copy the backup that the upgrade's deploy took over `data/nucleon.sqlite3` (as above), and only then `nucleonctl deploy <previous sha>`. Started on the migrated database, the earlier release would already prepare the pending cases again.
- **Before deploying that branch,** run `python3 deploy/provenance_scan.py` on a fresh copy of the production database (`nucleonctl clone-db`). The shared instance keeps the old revert rule until then. If the scan lists any record under `credited`, report it, and do not rewrite it. That record was credited to a later import when its own import was reverted. The result on 18 October was none (E015).

**Checking compatibility with older data:**

1. `nucleonctl clone-db <old database> <name>`
2. `nucleonctl isolate <name>`
3. `python3 deploy/e2e_https_check.py legacy --db ~/srv/nucleon/data/test-<name>.sqlite3`
4. `NODE_PATH=… node deploy/browser_check.js --legacy`

**Removing the deployment:**

1. `launchctl bootout gui/$(id -u)/local.nucleon.prototype`
2. Delete the plist and `~/.config/caddy/sites/nucleon.caddy`.
3. Run `~/.local/bin/caddy reload --config ~/.config/caddy/Caddyfile --adapter caddyfile`.

## Deployed-URL checks

**Which version of the browser checks to use.** On branch `feat/ux-redesign-20261018`:
- `browser_check.js` and `layout_check.js` follow the redesigned interface, and `ui_check.js` and `guide_check.js` are new.
- The shared instance runs the redesign (`f95f50f`) since 18 October 23:24, so these scripts apply to it. For `a9ce30d`, use the scripts from `1f5a21d` (`git show 1f5a21d:deploy/layout_check.js > /tmp/layout_check.js`).
- The Python checks work with both versions, with two exceptions that hold only for the redesign branch:
  - `e2e_https_check.py` expects the reply date written out ("Friday 30 October 2026"), and reads the backup folder from `~/srv/nucleon/config/service.json`;
  - `e2e_records_check.py production` checks that `customers.js` is served.
  For `a9ce30d`, use both scripts from `1f5a21d`.

Slice 2 flows (records, import, shared invoice numbers, workspaces):

```bash
python3 deploy/e2e_records_check.py production --compare <pre-deploy backup>      # read-only
nucleonctl isolate <new-name> && python3 deploy/e2e_records_check.py practice
python3 deploy/e2e_records_check.py seed ~/srv/nucleon/data/test-<name>.sqlite3 practice|real
nucleonctl isolate <name> && python3 deploy/e2e_records_check.py empty|real
```


On the server, after `nucleonctl isolate <scenario>`:

```bash
python3 deploy/e2e_https_check.py approve | restart | stale | change-date | decline | clarify | console | fallback-unavailable | fallback-invalid | legacy --db <file>
NODE_PATH=<dir with node_modules/playwright> node deploy/browser_check.js [--fallback | --legacy]
```

The scripts read the current codes from the private log and send every request through the public HTTPS URL with a browser-style Origin header. The browser check saves screenshots, which never show a code, to `~/srv/nucleon/reports/browser/`. Results are recorded in [DECISIONS.md](DECISIONS.md): E002 covers the first deployment, E003 the structured-brief release, and E004 the redesigned interface and demo console.

Use new `isolate` names for fresh scenarios; reusing a name reopens that test database with its earlier records. Finish with `nucleonctl production` and confirm with `nucleonctl status` that the active database is `data/nucleon.sqlite3`.
