# PoV implementation plan — Weeks 8–10

**Status:** draft agreed between the product lead (Hanting) and Claude Code on 30 October 2026, after a read-only review of the documentation (PR #4) and the local M3 code (`83b3efb`). It turns the [PoV roadmap](POV-ROADMAP-20261030.md) into staged slices with acceptance criteria, tests and rollback boundaries. Nothing in this file is implemented yet. The code facts it relies on are in [the engineering inventory](../ENGINEERING-INVENTORY-20261030.md).

All data in development and PoV testing is **fictional**. Thresholds named here are POC values, never real NTK limits.

## 1. Decisions taken on 30 October

| # | Decision | Rationale / consequence |
|---|---|---|
| D1 | **Front end: stitch, not rebuild.** LibreChat stays the chat shell; the Records web app becomes the product shell. No iframe embedding, no new React app. | Two weeks; the 17/17-verified chat → MCP → backend path is kept. The "disconnected" feeling comes from two logins, no back-links and two visual languages, which stitching fixes. |
| D2 | **Prune the dead agent runtimes.** Remove the Lab's own chat page and Pydantic-AI agent, the Records desk chat agent, the old console queue and the deploy checks that only test them. History stays in Git (tag `poc-week7`). | Three runtimes cost investigation time and tests. The `CAPABILITIES` registry in `coordinator.py` is kept because MCP depends on it. **Staged (30 Oct dependency analysis):** the Lab side was removed in S0 (384 → 121 Lab tests). The Records desk is the current landing page (`#/` → desk) and about twelve test files exercise the tool surface through `/api/desk`, so it is removed in S2 together with the new landing page, re-pointing those tests at `/api/tools/<name>`. `prototype/agent.py` is the case-analysis engine (not the desk) and `DeskTools` is the executor behind `/api/tools/<name>`: both are KEEP. |
| D3 | **Policy engine untouched** (`prototype/delegation.py`), except additive keys named below. `server.py` may be split into modules without logic changes. | 129 tests + browser acceptance are the product's trust base. |
| D4 | **Fresh fictional database** for the new version. Old databases are kept in `backup/`, not migrated. | No legacy burden. |
| D5 | **Model: local first, test smaller models, cloud API as an option.** Qwen3.5-35B-A3B remains the reference. A model test bench decides whether a 9–14B model is adequate. A cloud model is supported as an alternative LibreChat agent (zero Nucleon code change), positioned as the choice for businesses without hardware. | Product story: fully offline is possible; online API is an opt-in for low-hardware pilots. |
| D6 | **Hosting for PoV: the M3 MacBook Pro stays online** (a MacBook Air becomes the daily machine from next week) and is the only machine in scope. Public HTTPS access through the product lead's own domain on **Cloudflare: a Cloudflare Tunnel (`cloudflared`, no inbound router port), proxied DNS, and Cloudflare Access (email one-time code) in front of both hostnames** (one for LibreChat, one for Records). Tailscale is retired. M6 and any second machine are out of scope. | The Owner opens a URL in their own browser and shares their screen; no VPN install, no remote-desktop latency. Access adds a login gate the app does not have to provide. |
| D7 | **Reliability gate includes real Owner-reviewed cases.** The track-record check (ladder step 7) counts live Owner verdicts alongside the fictional evaluation set; both counts are shown separately; the Owner sets the thresholds and may switch the fictional bootstrap set off in the control panel. | This is the "growing autonomy" mechanism: advisory mode is shadow mode, agreement accumulates, autonomy unlocks. Small samples are mitigated by Owner-set thresholds and separate labelling, not by excluding real cases. |
| D8 | **Silent Owner:** a control-panel setting "treat an unreviewed autonomous decision as agreed after X days". Recorded as `tacit_agree`, distinct from an explicit `agree`; not applied while the policy is paused or to overridden cases. Plus a batch review page to make explicit feedback cheap. | Memory and agreement metrics stop ignoring agent decisions the Owner never clicked on. |
| D9 | **Owner agent (LibreChat) is read-only** and comes after the batch review page. Any decision, feedback or policy change still happens on a Records page via a card link. | Nice-to-have for the PoV; must never create a second write path. |
| D10 | **Outcomes are stored observations**, not read-time labels. | Required for the commercial-outcome loop and for honest impact numbers. |
| D11 | **Lightweight UI telemetry** (`ui_events`: page enter/leave, key button clicks, decision durations), local only, visible on the dashboard. | Owner intervention time and friction become measured, not estimated. |
| D12 | **GitHub:** tag `poc-week7` at `83b3efb`; merge PR #4 (docs) into `main`; merge the ADA code branch into `main` with a merge commit; one branch per slice, merged with merge commits (no squash); a tag per milestone. | `git log --first-parent main` becomes the project's upgrade line for the retrospective. |
| D13 | **Decision checklist.** Every product recommendation from an AI session answers four questions in writing: does it reduce or add Owner net work; does it advance growing autonomy or add a permanent human gate; is it deterministic and verifiable; is it reversible and Owner-configurable. A bad answer must be stated plainly ("this is the conservative default and works against growing autonomy"). Restrictive behaviour is implemented as an Owner setting, never hard-coded. The autonomy-maximising alternative is always shown next to the recommendation. The decision register records, per decision, the principle served and the principle traded. At each milestone a "vision audit" counts where the Owner still clicks in the three standard journeys. | On 30 Oct the reliability-gate recommendation was first framed as a risk parameter and contradicted the anti-over-escalation requirement in DECISION-AUTHORITY.md; the product lead caught it. The checklist makes that class of error visible before it is accepted. Lives in CLAUDE.md. |
| D14 | **S3 read-only tools default ON** (`whatIsNeeded`, `comparableCases`, `customerStatus`, `policyBacktest`, `impactSummary`; 31 Oct, S6a). `decisionStatus` and all act/prepare tools stay off by default. Principle served: autonomy / less Owner net work (a fresh demo database no longer needs Setup before the Owner agent can answer); principle traded: caution (more read tools offered by default; none stores or decides anything). Reversible and Owner-configurable: each can be switched off under Setup, and nothing else changes. | After `demo-reset` the Owner agent called these tools "unavailable" (browser acceptance, 31 Oct: 1 of 5). Checklist: (1) reduces net work, (2) advances autonomy, (3) a registry flag with tests, (4) Owner switch under Setup. Autonomy-maximising alternative: also default `decisionStatus` on; not taken now. |
| D15 | **Staff agent steps reduced to findCustomers → resolveDecision with an explicit ambiguity check** (31 Oct 2026, S7 phase B). `assessDecision` and `whatIsNeeded` stay available as tools but are not in the Staff steps. Principle served: autonomy and less Owner net work (fewer early stops, fewer wrongly created cases); principle traded: none in the backend, which still decides by policy; the model asks Staff when the request is ambiguous. Reversible: the old text is in git history and in the Mongo backup. | Evidence: bench A4/A5, 20 of 20 runs on the D5 bar, zero mixed-prompt cases, zero wrong approvals (`docs/research/MODEL-BENCH-20261031.md`). Text: `integrations/librechat/agents/instructions_staff.txt`. |

**Explicitly excluded until the core PoV is reliable:** outbound customer communication, autonomous decline, forecasting / limit optimisation, multi-person account infrastructure, LibreChat version upgrade, model fine-tuning, M6 deployment, a Lab React chat page.

## 2. Target shape of the product

Five pages, one visual language, one navigation:

| # | Page | Today | Change |
|---|---|---|---|
| 1 | **AI assistant** | LibreChat, agent "Nucleon ADA Staff (Qwen)"; Staff only | Owner agent (read-only); cards link back to Records pages; Records nav links to the assistant with the right agent preselected |
| 2 | **Control panel** (Owner) | `#/delegation`: policy form, history, pause, queue, suggestions, counts | Add settings: tacit-consent days, track-record thresholds and sources, model/provider note. Keep policy writes Owner-person-only. |
| 3 | **Owner review** (Owner) | Part of `#/delegation` | New page: batch review of autonomous decisions (agree / disagree / override with reason), escalated and held cases, each with a one-line why and a link to the case timeline |
| 4 | **Dashboard** (Owner) | `GET /api/delegation/stats` counts | New page: impact report (section 5) and the loop view (where each case sits in request → evidence → evaluation → decision → feedback → outcome) |
| 5 | **Records** (Staff, Owner) | `#/customers`, `#/imports`, `#/knowledge`, `#/setup` | Kept; restyled to the shared language |

Plus the per-case **timeline** (section 4), reachable from pages 1, 3, 4 and 5.

What the LLM does: understand the request, pick the kind, recommend (approve / decline / escalate) with reasoning, phrase the reply, answer status questions. What code does: everything else — facts, exposure, evidence levels, policy checks, state transitions, idempotency, authority, provenance, metrics.

## 3. Slices

Each slice is a branch. "Done" means the acceptance list passes and the checks in section 6 are green. Rollback is "do not merge the branch" plus, for data, the pre-slice backup.

### S0 — Baseline and hygiene (first)

Scope: tag `poc-week7`; merge PR #4 and the code branch into `main` (resolve README / AGENTS / CLAUDE / INDEX conflicts in favour of the PR #4 text plus a code section); commit the inventory and this plan; the D13 checklist into CLAUDE.md; prune per D2 (only code with no live dependency — the old `#/cases` page stays until S2 replaces it, because escalated extensions are still decided there); fresh fictional DB; `bin/check` script that runs unit tests, `delegation_page_check`, `mcp_check`; rotate the two local MCP tokens and the Records codes.

Acceptance:
- `git log --first-parent main` shows: PR #4 merge, code merge, prune commit, docs commit.
- Unit tests green on Python 3.9 and 3.12 after the prune; the test count drops only by the tests of removed modules (listed in the prune commit message).
- Local services start from `main`, `mcp_check` passes, the ADA agent still completes the Northside, Bayview, Harbourline and Lakeside prompts (one real-Qwen browser round, `accept_final.py`).
- No file in the repo contains a token, code or password (secret scan before any push).

Rollback: tag `poc-week7`; `backup/` of the DB.

**S0 result (30 Oct 2026, local, fictional data):** done except the GitHub push (local `main` only). `git log --first-parent main`: PR #4 → code merge `a59dc23` → inventory/plan → CLAUDE.md checklist → `bin/check` → Lab prune merge `9da0d15` → demo tools and tests under `deploy/m3-local/`. Unit tests 955/955 (3.9 and 3.12), Lab 121/121 after the prune, page check 59/59, MCP check 52/52 (`mcp_check.py` rewritten to be data-driven). Real-Qwen browser round `accept_final.py` on `main`: 16/17 on the first pass; the one failure (5b, the "just say yes" probe) was an LM Studio provider error ("Generation predecessor handoff could not be confirmed"), not a product failure; the probe was re-sent in the same chat and passed (reply refuses, backend unchanged). Evidence: `~/Developer/nucleon-local/tests/ada-acceptance/evidence/final_acceptance.json`. Rotated: Records access and service codes, the two Lab MCP tokens, LibreChat's local MCP token. The tailnet origin was removed from the local configs (Tailscale retired, D6); a Python client could not log in while it was present because the Records cookies were `Secure`. Found for S2: the Owner `#/delegation` page never refreshes itself. Found for S4/S3: the LM Studio error above happens on a follow-up turn in a long chat; record its frequency in the model bench.

### S1 — Decision-loop backend (deterministic, no UI)

Scope:
- `case_events` table (append-only, per decision case): created, evidence_requested, evidence_submitted, evaluated, decided, feedback, override, outcome_observed, tacit_agree. Written in the same transaction as the state change.
- Outcome observations: `observe_outcomes` step (run on import, on demand, and from the dashboard) that writes `outcome_observed` events with vocabulary `on_time | late_paid | partial | open_not_due | open_past_due | written_off | unknown`, `observed_at`, as-of date, policy version. The case view shows the latest observation and keeps the read-time label only as "current ledger says".
- Tacit consent: policy/settings key `feedback.tacitAgreeAfterDays` (null = off); a deterministic sweep records `tacit_agree` where applicable (D8).
- Track record sources: `trackRecord.sources: fictional | live | both` (default `both`), counts reported separately (D7). Live agreement uses explicit and tacit verdicts, labelled.
- Suggestions: add tightening suggestions (a disagree or a bad outcome inside a band proposes lowering that bound); still `suggestionOnly`.
- `GET /api/delegation/impact?from=&to=&policyVersion=`: numerators and denominators for the metrics in section 5, each with `source: measured | derived | assumption` and `dataset`.
- Owner view timestamps: `POST /api/decision-cases/<id>/viewed` (Owner person) → `case_events` kind `viewed`.
- Structured hints for the agent: `assessDecision` / `resolveDecision` errors carry `hint: {ask: 'kind' | 'invoice' | 'amount' | …, options: [...]}`; a `forModel` compact result (status, why, next step, key facts) alongside the full result that feeds the card.

Acceptance (unit tests in `prototype/test_*.py`, deterministic):
- Every state change on a case produces exactly one event; replays produce none.
- Outcome observation is idempotent per (case, as-of date); editing the ledger after an observation does not rewrite the observation.
- Tacit agree never fires while paused, on overridden cases, or before X days; it is excluded when `sources: fictional`.
- Track record with `sources: both` equals the fictional back-test plus live verdicts; with `live` and fewer than `minReviewedCases` live cases, step 7 escalates.
- Impact endpoint totals reconcile with `delegation/stats` for the same window.
- Existing 129 delegation tests unchanged and green.

Rollback: additive schema only (new table, new JSON keys with safe defaults); DB backup before deploy.

### S2 — Owner surfaces and the shared shell

Scope: pages 2, 3, 4 of section 2; case timeline; shared navigation and styling across Records pages; `ui_events` capture (D11); role landing page after sign-in (replaces the desk as `#/`); removal of the Records desk chat (`web/desk.js`, the `/api/desk/*` routes, `desk_run` and the desk mock in `coordinator.py`, statement confirm/retire if nothing else creates proposed statements) with the affected tests re-pointed at `/api/tools/<name>` (test_situation, test_prepared_actions, test_presentation, test_preparations, test_capabilities, test_coordinator ReplyGuardTests, test_desk_store, test_case_coordinator, test_suggestion, test_import_proposal, test_controlled_actions, test_concern_loop; shared helpers `Rewording`, `called`, `SHARED`, `NAMED`, `REQUEST` moved to `prototype/test_helpers.py` first); `threads`/`turns` tables stay in the schema; the Owner pages refresh themselves (the current `#/delegation` page never polls: a case that arrives while the Owner is on the page is invisible until a manual reload, found in the 30 Oct acceptance round); links from cards to case timeline (same allow-list mechanism as the evidence link, extended to `#/cases/<caseId>` and `#/review`).

Acceptance (headless page checks, Playwright, scratch server; extend `deploy/delegation_page_check.py`):
- Owner can review five autonomous decisions in one screen with reasons; a stale version gives 409 and a visible message; double-click is idempotent.
- Timeline shows every `case_events` row in order with actor, policy version and time; outcome shown as pending until observed.
- Dashboard numbers equal the impact endpoint; every tile names its source and dataset.
- Staff sees no Owner reasons anywhere (existing rule).
- Card link to a case opens only allow-listed URLs (same test as the evidence link, LibreChat side unchanged unless the allow-list pattern needs widening — then patch 0005, isolated test first).

Rollback: pages are new files; the nav change is one commit.

**S2a result (31 Oct 2026, branch `s2/owner-surfaces`, local, not pushed): the desk removal and the shared shell are done.** Commits: test helpers to `test_helpers.py` `b2547a1`; desk-driven tests re-pointed at `/api/tools/<name>` `2e91390`; desk code removed (`desk.js`, `/api/desk/*`, `desk_run`, guard, desk mock, statement confirm/retire) `c357929`; deploy checks and README/PROMPTS notes `aa2c391`; `assistantUrl` config and `GET /api/session` `c6804cb`; landing page, one navigation, Review/Dashboard placeholders `5de757d`; control panel self-refresh and `deploy/home_page_check.py` `fcc3fb2`. Unit tests 1089 -> 1027 on 3.9 and 3.12 (the deleted ones tested desk prose, the reply guard or the desk mock; the tool behaviour tests were kept or ported), Lab 122, page checks 59/59 and 56/56, layout 204/204, ui 150/150. Still to do in S2 (S2b): the batch review page, the dashboard, the case timeline, `ui_events` capture and the Owner `viewed` event, the card-link allow-list extension, the track-record and tacit-agree controls in the control panel, and a read-only list of the evidence requests waiting for Staff for the Staff landing page.

**S2b result (31 Oct 2026, branch `s2b/owner-pages`, local, not pushed): the Owner pages and the page-use events are done.** Commits: backend (loop view, `ui_events`, open evidence list, row fields) `c6f027e`; control panel settings (tacit-agreement days, track-record sources with the gate's counts, tacit wording, one place to act) `f89df18`; Review page, case timeline, dashboard, page-use capture and the Staff evidence list on the home page `e28439d`; page checks `e3fca8a`. Done from the S2 scope: batch review page with agree / disagree / override and the Owner `viewed` event; dashboard with the impact report and the loop view; case timeline with links from the control panel, home page and review rows; `ui_events` capture (D11) and its summary on the dashboard; the track-record and tacit-agree controls; the read-only list of evidence requests waiting for Staff. Unit tests 1027 -> 1056 (3.9 and 3.12), Lab 122, page checks: control panel 67, home 61, action 42, review 84, dashboard 34. Not done: the `case_view` route still returns an Owner decision's reason to Staff (the timeline page does not show it); `ui_events` has no retention limit; `layout_check.js` and `ui_check.js` were not run (no Node on this machine).

### S3 — Agent hardening and the model test bench (parallel with S2)

Scope:
- Lab passes the `forModel` compact result as the text content and keeps the full result in the card.
- Agent instructions updated to use hints (ask the hinted question, stop).
- New read-only tools where they remove guessing: `whatIsNeeded` (what evidence a request of kind K for customer C would need now), `comparableCases` (Owner-free view), `customerStatus`.
- **Model test bench** `tools/modelbench/`: runs the five standard prompts (Northside, Bayview, Harbourline, Lakeside, the mixed L-001 prompt) N times against a model served over an OpenAI-compatible API, using the real MCP tool definitions and a minimal tool loop, on a scratch Records/Lab stack; judges by backend state and tool-call count, records latency and tokens; model text is recorded, not judged. Candidates: Qwen3.5-35B-A3B (reference), two or three 9–14B models, one cloud model (cost per run recorded).
- LM Studio stays the server unless the bench shows it limits tool-call quality; `mlx_lm.server` is the headless fallback.
- Owner agent in LibreChat: `nucleon-local-owner` MCP connection, tools `decisionStatus`, `cases`, `workQueue`, `comparableCases`, `policyBacktest` (what-if, read-only), `impactSummary`; instructions: read-only, link to pages for any action.

Acceptance:
- Bench: reference model passes 5/5 prompts in ≥ 9 of 10 runs with ≤ 4 tool calls; a candidate is "adequate" if it matches that; results committed as `docs/research/MODEL-BENCH-<date>.md`.
- Owner agent cannot reach any write tool (`mcp_check` extended with the owner token).
- One real-Qwen browser round (`accept_final.py`) at the end of S3.

Rollback: instructions are scripts in `integrations/librechat/agents/`; tool additions are registry rows with `defaultEnabled: False`.

**S3 result (31 Oct 2026, branch `s3/agent-hardening`, local, not pushed): all six scope items are built; nothing was run against the live LibreChat, Mongo or services.** Commits: Lab text/card split and the optional tool timing log `fbad2b3`; read tools `whatIsNeeded`, `comparableCases`, `customerStatus`, `policyBacktest`, `impactSummary` `1222ba7`; Staff agent instructions with one text source and `update_ada_agent_hints.js` (not run) `e5d46de`; read-only Owner agent script (not run), `nucleon-local-owner` MCP entry and `mcp_check` role rules `720d166`; model bench `5ef99ea`; bench-driven fix to the `whatIsNeeded` next step, reference-model results and `docs/research/MODEL-BENCH-20261031.md` `c8562ee`. Tests: Records 1027 -> 1055 on 3.9 and 3.12, Lab 122 -> 129, bench 7 (new), delegation page check 59/59, MCP check against a scratch stack 63/64 (the one failure is the `host.docker.internal` Host check, which the scratch Lab does not allow). **Bench, reference model, 3 runs: 15 of 15 prompts correct by backend state, 2 of 3 runs with every prompt in at most 4 tool calls (one Bayview run took 5); the 10-run bar is pending**, so the acceptance line "9 of 10 runs" is not yet met or missed. Bench finding: a first draft of the `whatIsNeeded` result made the model stop and ask Staff in chat (Lakeside 0/3); rewording its `nextStep` like `assessDecision`'s fixed it. Still to do in S3: run `update_ada_agent_hints.js`, `seed_owner_agent_3080.js` and the live rollout (README order), the 10-run bench for the reference and candidate models, and the one real-Qwen browser round (`accept_final.py`) at the end of S3.

### S4 — Public access, onboarding, PoV readiness

Scope: `cloudflared` tunnel on the M3 with two proxied hostnames (chat → 3080, records → 8631) and Cloudflare Access (email one-time code, allow-list of tester emails) on both; the public origins made **configuration** on all three sides (Records `publicOrigins`, Lab `recordsPublicUrl` + card `CONFIRM_ORIGINS`, LibreChat link allow-list via patch 0005 reading an env/config value instead of a constant); LibreChat `DOMAIN_CLIENT`/`DOMAIN_SERVER` set to the public hostname and `TRUST_PROXY` set so the ban logic sees the real client IP, not Cloudflare's; Tailscale Serve removed; **M6 leftovers removed from the M3 LibreChat (user-approved 31 Oct):** the `nucleon-staff` and `nucleon-owner` MCP entries (M6 URL, retired 30 Oct) and every agent that used them, including the original read-only "Nucleon Staff POC" and the card-test agents, after a Mongo backup (`mongodump` of `agents` + `conversations` into `nucleon-local/backup/`); only the ADA Staff agent and the new Owner agent remain; LibreChat registration off, tester accounts (Owner, Staff) with strong passwords; Records codes rotated; onboarding page in Records (no secrets) with the three test journeys; consent text; session log template from the [validation plan](../research/POV-VALIDATION-PLAN-20261030.md); `bin/pov-check` (services up, model loaded at 32k ctx, tunnel up, caffeinate on); dress rehearsal with a teammate on an outside network.

Acceptance:
- A teammate on mobile data passes Access, then completes Northside, Harbourline and Lakeside end to end through the public URL in their own browser; evidence link and case link open; no non-browser ban triggered; a deliberate non-browser request from one tester IP bans only that IP (TRUST_PROXY verified).
- `pov-check` green; one real-Qwen browser round on the public URL.
- Security review of the exposed surface (Access policy, registration off, no demo console code in use, secrets out of HTML, rate limits, origin not reachable except through the tunnel) recorded in `docs/DEPLOYMENT.md`.

Rollback: stop `cloudflared` (or disable the Access application) and the services are loopback-only again; the configuration change is one commit per side.

**S4 result, code part (31 Oct 2026, worktree `s4/public-access`):**

| Item | State | Commit / artifact |
|---|---|---|
| LibreChat patch 0005 (Cloudflare origin `https://nucleon.dracooz.top` in `ALLOWED_ORIGINS`) | done (a compile-time constant, as in 0003/0004; not read from env/config) | LibreChat dev repo `a130836` (docs `a2feff3`); Nucleon `7585938`: `integrations/librechat/patches/0005-feat-client-allow-the-Nucleon-Cloudflare-origin-for-.patch`. `git am` of 0001-0005 on `e8f3be0` reproduces `a130836`; client test 81/81 |
| Image `librechat:nucleon-card-v0.8.8-rc5-cf` | built (`sha256:32500f25564e`, 4.55 GB), not tagged `latest`, not deployed | |
| Lab `CONFIRM_ORIGINS` and `recordsPublicUrl` check accept the origin; tests | done, Lab 124/124, Records 1027/1027 | Nucleon `0d0bf95` |
| `launchd/com.nucleon.cloudflared.plist`, `launchd/com.nucleon.caffeinate.plist`, `bin/pov-check` | done (pov-check run once: services and edge PASS, cloudflared/caffeinate FAIL as expected before the agents are loaded) | Nucleon `a2b5ea2` |
| `integrations/librechat/librechat.env.example` (`DOMAIN_CLIENT`, `DOMAIN_SERVER`, `TRUST_PROXY`, `ALLOW_REGISTRATION`, `ALLOW_SOCIAL_REGISTRATION`) and README allow-list table | done | Nucleon `7585938` |
| `docs/DEPLOYMENT.md` section "Public access for the PoV" (architecture, Cloudflare, configs, rollback, security notes) | done; the security review of the exposed surface is written, to be confirmed by the external test | Nucleon `4203c9e` |
| Onboarding page in Records, consent text, session log template, Records code rotation, tester accounts | not part of this code slice | |
| Records `publicOrigins` / `assistantUrl`, Lab `recordsPublicUrl` in the live config files | runtime step, done by the coordinating session | |
| LibreChat image switch to rc5-cf and `.env` keys (recreate `api` only) | runtime step, done by the coordinating session | |
| Tailscale Serve removal; M6 leftovers (MCP entries, agents) removed after `mongodump` | runtime step, done by the coordinating session | |
| Load the two LaunchAgents; start `cloudflared` | runtime step, done by the coordinating session | |
| `pov-check` all green; external test on mobile data (Access, three journeys, TRUST_PROXY ban test); one real-Qwen browser round on the public URL | runtime step, done by the coordinating session | |

**S3/S6 bench status (31 Oct 2026, S6c):** reference model 10 runs = 5/10 runs adequate (47/50 prompts correct), so the D5 bar (9/10) is **not met** by the reference, and **qwen3.5-9b met it in one 10-run sample (9/10) but not in a second (2/10); combined 11/20, not adequate (S6d); **qwen3.8-27b-mlx meets it (9/10 runs, 49/50 prompts) but at about 70 to 85 s per prompt, 5x the 35B**; granite-4.2-30b and muse-glimmer-30b too slow; qwen3.5-27b, 4b, gemma-4-31b not adequate; candidates, 3 runs each: qwen3.5-9b 15/15 correct (2/3 within 4 calls), gemma-4-26b 12/15 (mixed prompt opens a case), gpt-oss-20b 9/15 (stops after `whatIsNeeded`);  see `docs/research/MODEL-BENCH-20261031.md`.

### S6a — The Owner agent works (31 Oct 2026)

Status: **done, merged to `main`.** The browser acceptance of the read-only Owner agent failed 1 of 5 (tools off after demo reset, `workQueue` blind to decision cases, instructions steering to the wrong tools). Fixed: D14 (read tools default on), `workQueue` lists decision cases, Owner instructions; re-run with `deploy/m3-local/tests/accept_owner.py`: 5/5 (Qwen3.5-35B-A3B, fictional data).

### S6b — One entry point (31 Oct 2026)

Status: **done, merged to `main`.** LibreChat is trimmed (presets, prompts, bookmarks, multi-conversation, parameters off; welcome line with the Nucleon address), has a "Nucleon" link in its left rail (patch 0006, image `rc6-nav`), and two role accounts (`owner@`, `staff@`, role USER) so one link serves both roles: Nucleon's landing page routes by the signed-in role. Checked in the browser: link visible (also collapsed) and opens a new tab; the Staff agent still renders the MCP card; Owner sees the Owner and Staff agents, Staff sees only the Staff agent, neither has the agent builder or can edit (PATCH 403). Rollback: previous image tag in the override and `docker compose up -d api`.

### S5 — PoV sessions, fixes, final evidence (Weeks 9–10)

Scope: Owner and Staff sessions (screen-shared, recorded with consent); friction log; fix list limited to blockers for the three journeys; impact report from real session data labelled as such; final demo rehearsal on the actual audio path; handover docs.

Preparation done: see `docs/pov/` (tester guide, consent, session log template, facilitator runbook, feedback register). Dates and tester emails are still to be confirmed by the product lead.

Acceptance: the validation plan's reporting format completed with real session data; the final demo shows the full loop (policy → agent → evidence/exception → recorded decision → Owner feedback → outcome) on one case.

## 4. The decision loop, made explicit

Per case, the timeline reads from `case_events`:

```
request → evidence (asked / given, with level) → evaluation (3 dimensions, policy vN)
→ decision (agent under policy vN | Owner | Owner exception)
→ Owner feedback (agree | disagree | tacit_agree | override, reason)
→ outcome (pending → on_time | late_paid | partial | open_past_due | written_off)
→ used as comparable in later cases (count shown)
```

Two loops, shown separately: the decision-learning loop (feedback feeds comparables and the live track record) and the commercial-outcome loop (observations feed suggestions and the impact report). Neither retrains a model.

## 5. Impact report metrics

| Metric | Numerator / denominator | Source today | After S1 |
|---|---|---|---|
| Autonomous coverage | agent-decided / policy-eligible cases | `decision.by`, `handling` | measured |
| Escalation rate | owner_review + policy_hold / all cases | `handling` | measured |
| Evidence requests | request_evidence cases, turnaround | `actions`, `confirmed_facts` | measured |
| Time to decision | decision.at − created_at | JSON fields | measured, per kind |
| Owner intervention time | decided − viewed, per case; total per week | none | measured (viewed events) |
| Overrides and disagreements | per policy version | `override`, `feedback` | measured |
| Live agreement | agree + tacit / reviewed | partial | measured, labelled |
| Outcomes over time | per observation vocabulary, per policy version | read-time only | measured observations |
| Time saved | manual baseline − assisted | Owner-reported baseline (31 Oct 2026): about 1 request a week, 3 to 5 days each, Owner phones the customer personally; see `docs/pov/README.md` | **assumption** from interviews, labelled |

Fictional and live datasets are never mixed in one number.

## 6. Verification and working method

- **Daily checks:** `bin/check` = unit tests (3.9 and 3.12) + `delegation_page_check` + `mcp_check`. Minutes, no model.
- **Milestone checks:** one real-Qwen browser round (`accept_final.py`) at the end of S0, S3 and S4 only.
- **Model bench:** on prompt or tool changes, and for model selection.
- **Boundaries:** additive schema only; no change to `delegation.py` rules outside the keys named in S1; no LibreChat patch change unless the allow-list must widen (then isolated 3081 test first); no outbound actions anywhere.
- **Token discipline:** the inventory and this plan are the map; implementation by a cheaper model per slice from the acceptance list; review and decisions by the coordinating model; no exploratory agents on questions the inventory answers.
- **Honesty labels** on every number and claim: measured / derived / assumption, fictional / live.

## 7. Open items

- ~~Exact Week 10 submission date~~ set: Monday 16 Nov 2026 (31 Oct). Still open: the final demo venue's audio path.
- Owner consent wording and which fictional cases mirror the Owner's real decision types.
- Whether the cloud-model option is shown in the PoV or only documented.
- Which hostnames under the product lead's domain are used for chat and records.
