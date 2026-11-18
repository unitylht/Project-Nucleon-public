# Controlled local M3 rollout plan: Adaptive Decision Authority

**Status: EXECUTED on 27 Oct 2026, with the user's approval.** The browser acceptance on 3080 **passed** (17/17), and the deployed code was then updated to `da95220`. See "Deployment record" at the end. Never run this on M6.

## What changes when this is deployed
- **Nucleon (Records :8631 + Lab :8630).** The normal runtime `~/Developer/nucleon-local` moves from `c69d521` to this branch, whose last code commit is `81c9e6e`. That brings Phase A/B and the delegation slice with it.
  - **Tables:** four tables are added: `actions`, `delegation_policies`, `decision_cases` and `confirmed_facts`. The migration is additive.
  - **Safe default:** the policy starts at **version 0 (advisory, nothing executes)**, and every new tool is off by default.
- **LibreChat :3080.** The cards' "Provide information" and "Review and confirm" buttons need the rc3 image (patch 0003, which allows `http://127.0.0.1:8631/#/actions/act_…`). The decision and Key Facts cards display on rc2 too, but **their buttons don't work there**.

## Preconditions (all must hold)
1. The isolated acceptance is accepted by the user (`~/Developer/nucleon-ada-test/evidence/result.json`, rounds 1–4).
2. Records and Lab are deployed **together**, from the same commit. The Lab signs in with the Records **service codes**.
3. The normal environment's data is fictional. Back up both databases and the configs first.
4. LM Studio is serving `qwen3.5-35b-a3b`, and the default model is unchanged.

## Steps
1. **Back up.**
   - Stop the local services (`~/Developer/nucleon-local/bin/nucleon-local stop`).
   - Copy `data/records.sqlite3`, `data/lab.sqlite3` and `config/*.json` to `backup/pre-ada-<timestamp>/` with mode 600.
   - Note the current commit in `~/Developer/Project-Nucleon` (`c69d521`).
2. **Code.**
   - In `~/Developer/Project-Nucleon`, run `git switch feat/adaptive-decision-authority-20261026`. The branch is already local; don't rewrite history or merge into main.
   - Alternatively, point the runtime at the `~/Developer/Project-Nucleon-ada` worktree.
3. **Config** (keep the secrets out of Git, files mode 600):
   - **`records.json`:** add `serviceCodes` (new random staff and owner service codes), and make `publicOrigins` include `http://127.0.0.1:8631`.
   - **`lab.json`:** set `recordsCodes` to the **service** codes, not the person access codes, and set `recordsPublicUrl` to `http://127.0.0.1:8631`.
4. **Start** both services, then check:
   - `curl` `/api/tools` gives 401 without a session;
   - the Lab's `/api/session` reports channel `service`;
   - `deploy/delegation_page_check.py` passes against a scratch copy, never against the normal database.
5. **Smoke test** (read-only first):
   - the existing MCP check `tests/mcp_check.py` passes, which means the financial cards still work;
   - the existing Staff agent on 3080 is unchanged, with read tools only.
6. **LibreChat :3080 to rc3 (a separate approval).**
   - Back up `docker-compose.override.yml`.
   - Change its image line from `...-rc2` to `librechat:nucleon-card-v0.8.8-rc3-test`.
   - Run `docker compose up -d --no-deps --force-recreate api`. Never use `down -v`.
7. **Enable (a separate approval, as the Owner).**
   - Sign in to `http://127.0.0.1:8631` as the **Owner person** and save a policy on `#/delegation`. Start in **advisory**: it only recommends.
   - Turn on `assessDecision`, `resolveDecision` and `decisionStatus` under Setup → Agent tools.
   - Create a **new** LibreChat agent, for example "Nucleon LOCAL ADA Staff (Qwen)", with those three tools plus `findCustomers`, `customerOverview` and `invoices`, using the instructions in `nucleon-test/seed_ada_agent.js`.
   - Don't change the existing Staff agent.
8. **Move to delegated** only after the Owner reviews advisory results, with **small** limits.

## Verification after each step
- **Tests and health:** test counts as in the isolated round, and `nucleon-local status` is healthy.
- **Phase B:** one human-confirmed request through `prepareRequest` still opens a request that waits for the Owner.
- **Delegation:** with a policy saved, one delegated decision is recorded as `delegated_policy` vN, and a pause stops execution.

## Rollback
1. **Turn off:** pause the policy, then turn the three tools off. An agent already created can be left in place; its tools become unavailable.
2. **Stop and restore:** stop the services, then restore `data/*.sqlite3` and `config/*.json` from `backup/pre-ada-<timestamp>/`. **Both the database and the code must be rolled back together**, because the older code doesn't know the new tables.
3. **Code:** `git switch feat/mcp-write-idempotency-20261026` (`c69d521`) in `~/Developer/Project-Nucleon`, then start.
4. **LibreChat:** restore `docker-compose.override.yml` (rc2), then `docker compose up -d --no-deps --force-recreate api`.

## Known limits to accept before rollout
- **Shared logins:** shared role codes, so the audit names Staff or Owner, not a person.
- **Private network only:** since 27 Oct 2026 (evening) the demo is also reachable through a Tailscale share at `https://nucleon.tail492813.ts.net` (Nucleon on `:8443`), and the card links use that address. Nothing is on the public internet.
- **Model wording:** Qwen's wording can be loose, and the card is the source of truth.
- **No automatic declines and no outbound messages.**
- **Thresholds:** the demo thresholds are fictional. The Owner must set real ones.

## Deployment record (27 Oct 2026, 00:02–00:40 AEDT, Claude Code)

**Backup:** `~/Developer/nucleon-local/backup/pre-ada-20261027-000207/` (mode 700). It holds:
- `records.sqlite3` and `lab.sqlite3`;
- `records.json` and `lab.json`;
- `librechat/` with `docker-compose.override.yml`, `librechat.yaml`, `.env` and a full `mongo-dump.archive`;
- `data-moved/`, the old live database files;
- `state-before.txt`.

**What was done.**
- **Code:** `~/Developer/Project-Nucleon` was detached at `2b2b786`; it was on `feat/mcp-write-idempotency-20261026`, `c69d521`.
- **Credentials:** new person access codes and new service codes were written to `records.json` (with `publicOrigins` `http://127.0.0.1:8631`). The Lab's `recordsCodes` are now the service codes, `recordsPublicUrl` is set, and **new MCP tokens** are in place: the old ones were printed into a Claude tool output during the check, so they were rotated. Only `NUCLEON_LOCAL_STAFF_MCP_TOKEN` in LibreChat's `.env` was replaced; the M6 tokens are untouched. Nothing earlier exposed in test output is reused.
- **Database:** a fresh fictional database. The existing MCP check passed 33/33 on the standard sample. The fictional ADA demo was then loaded at policy **version 0 (advisory)**, with the Owner enabling `assessDecision`, `resolveDecision` and `decisionStatus`.
- **LibreChat 3080:** `docker-compose.override.yml` now uses the image `librechat:nucleon-card-v0.8.8-rc3-test` (it was `...-rc2`), and only `api` was recreated. Mongo is untouched: 141 conversations and 282 messages remain. rc2 and -poc are still tagged.
- **New agent:** "Nucleon ADA Staff (Qwen)" (`agent_biPGuKnO2VgHEQ67HsLHL`), created by `LibreChat-card-visibility-dev/nucleon-test/deploy-3080/seed_ada_agent_3080.js`, with the tools findCustomers, customerOverview, invoices, assessDecision, resolveDecision and decisionStatus. The six existing agents are unchanged.

**Verified.**
- **Deterministic backend acceptance** on the deployed stack (`~/Developer/nucleon-local/tests/ada-acceptance/evidence/backend_acceptance.json`):
  - advisory mode executes nothing; a Staff write to the policy is 403;
  - the financial card data includes completeness;
  - the Bayview extension is decided by the agent, its due date moves, and an override reverts it with history kept;
  - Northside is decided with a recorded deposit; Lakeside is decided after a bank-checked deposit, with no ledger payment created;
  - Harbourline goes to the Owner; a second trial goes to the Owner;
  - pause, revoke (advisory) and restore all work;
  - there are no outbound events, and the counts are live-only.
- The acceptance database is kept as `backup/ada-backend-acceptance-*.sqlite3`, and the live database was then re-seeded clean at version 0.
- `tests/mcp_check.py` now reports 3 mismatches (14 vs 17 staff tools, and the old sample customers). Its expectations are pinned to the standard sample with the ADA tools off. That is not a regression.

**Pending.** The real Qwen + LibreChat browser round on 3080 was stopped by Claude Code's permission check ("modify shared resources") before its first scenario. It needs the user's approval to run. The rollout is **not** declared successful until it passes.

## Exact rollback (as deployed)
```
B=~/Developer/nucleon-local/backup/pre-ada-20261027-000207
~/Developer/nucleon-local/bin/nucleon-local stop
cp -p $B/records.json $B/lab.json ~/Developer/nucleon-local/config/
cp -p $B/data-moved/records.sqlite3* ~/Developer/nucleon-local/data/     # the pre-ADA live database (or: sqlite3 restore from $B/records.sqlite3)
cp -p $B/lab.sqlite3 ~/Developer/nucleon-local/data/lab.sqlite3
git -C ~/Developer/Project-Nucleon switch feat/mcp-write-idempotency-20261026   # c69d521
~/Developer/nucleon-local/bin/nucleon-local start
cd ~/Developer/LibreChat && cp -p $B/librechat/docker-compose.override.yml $B/librechat/.env . && docker compose up -d --no-deps --force-recreate api   # rc2, old local MCP token
```

**The ADA agent:** it can stay; without its tools it does nothing. To delete it, remove the agent named "Nucleon ADA Staff (Qwen)" and its ACL entry in the `chat-mongodb` `LibreChat` database.

**Mongo:** never `down -v`. `mongo-dump.archive` is the last resort (`mongorestore --archive`).

## Update: browser acceptance and da95220 (27 Oct 2026)
- **Acceptance:** the real Qwen + LibreChat browser acceptance on 3080 passed **17/17**, with evidence in `~/Developer/nucleon-local/tests/ada-acceptance/evidence/final_acceptance.json` and screenshots.
- **Agent instructions:** two sentences were added to the ADA agent's instructions (resolve once, don't re-assess) by `deploy-3080/update_ada_agent_instructions.js`.
- **Code update:**
  - **The fix:** `da95220` makes `assessDecision` return the stored status for a request already handled. It cuts Qwen's re-check loop from 12 to 7 tool calls for Northside, and its reply finished after 33 s instead of 55 s.
  - **Deployment:** it is deployed by `git switch --detach da95220` in `~/Developer/Project-Nucleon`, followed by a restart.
- **State after recording:** this line originally said clean fictional demo data at policy version 0. That was wrong: the second recording session's decisions and policy v1 were still in the database until 27 Oct, 21:40 AEDT. The data was reset then with `bin/demo-reset` (see below).
- **Saved databases:** `ada-browser-acceptance-*.sqlite3` and `ada-recording-session-*.sqlite3` are in `~/Developer/nucleon-local/backup/`.
- **Rollback:** unchanged (back to `c69d521`, with the database, config and image restored as above).

## Update: group access over Tailscale, member accounts, agent fixes (27 Oct 2026, evening)
- **Remote access:** Tailscale Serve on this Mac, tailnet only, never Funnel. `https://nucleon.tail492813.ts.net` goes to LibreChat 3080, and `:8443` goes to Records 8631. Group members reach it through a Tailscale share of this Mac.
- **Code:**
  - **Lab:** `83b3efb` adds the tailnet origin to the card-link contract.
  - **LibreChat:** commit `cf32892` (branch `feat/nucleon-confirm-link-tailnet`) adds the same origin to patch 0003's allowlist. It is image `librechat:nucleon-card-v0.8.8-rc4-tailnet`, now live on 3080.
  - **Config:** `records.json` `publicOrigins` gained the tailnet origin, which makes the Nucleon cookies Secure (`127.0.0.1` still works in Chromium). `lab.json` `recordsPublicUrl` is the tailnet origin.
- **Member accounts:** six LibreChat accounts with role USER, made by `~/Developer/nucleon-local/bin/team-accounts`.
  - **What they can do:** they can use the ADA agent, but not build agents.
  - **Lock-downs:** the M6 connections are hidden from their chat menu (`chatMenu: false`), and the USER role has `AGENTS.CREATE=false`.
- **Agent and model fixes:** see [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md).
  - **L-001:** the agent asks instead of guessing.
  - **L-002:** Qwen must run with 32,768 tokens of context; `bin/demo-reset` checks it.
- **Clean data:** `~/Developer/nucleon-local/bin/demo-reset` keeps a copy of the current database, then reseeds the clean fictional demo data at policy v0.
- **Backups:** `~/Developer/nucleon-local/backup/pre-team-accounts-*`, `pre-tailnet-*` and `pre-reset-*`.
- **Verified (27 Oct 2026, real Qwen, in a browser):**
  - **Member account (member1) in LibreChat:** signs in over the tailnet as role USER. It sees only "Nucleon ADA Staff (Qwen)"; creating an agent is refused with 403; the M6 servers report `chatMenu: false`; it sees none of the admin's conversations. The admin still sees all 7 agents and their history.
  - **Remote flow:** over the tailnet, the Lakeside request showed its card after 12 s, and the card's button opened the evidence page at the `:8443` address, already signed in as Staff. Nucleon Staff sign-in also still works at `127.0.0.1:8631`.
  - **The five demo prompts at a 32,768-token context:** each finished in 3 tool calls, 26–32 s, with the backend outcomes as expected. The ambiguous prompt got a clarifying question after 1 call. Details are in [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md).
- **Incidents in this round:**
  - **LibreChat ban:** a check script that wasn't a browser triggered LibreChat's non-browser ban, for the member account and the Docker gateway `172.18.0.1`. That briefly blocked every login from this Mac. It was cleared within minutes (the ban documents were deleted from Mongo `logs`, and LibreChat restarted). Later checks used Playwright.
  - **Funnel permission:** while HTTPS was being enabled in the Tailscale admin, Tailscale Funnel was also allowed by mistake; this added a `funnel` node attribute to the tailnet policy. Funnel was never used: both forwards stayed "tailnet only", and public DNS has no record. The owner then removed the attribute, and the Mac's Funnel capability is now gone.
  - **Demo data:** the database still held the recording session's decisions (see the correction above). It was reset with `bin/demo-reset`.
- **Clean-up after the rehearsal:**
  - **Demo data:** reset again with `bin/demo-reset`, to policy v0 with no live decisions.
  - **Test conversations:** the 17 created by Claude Code in the member1 and member2 accounts were deleted, after a JSON export to `~/Developer/nucleon-local/backup/member-test-chats-*.json`. The member's own rehearsal chat and the admin's 156 conversations were kept.
- **Member setup guide:** https://claude.ai/artifact/7x6HdHuHQAMSVxVemQAuVs (private until the owner shares it).
- **Rollback of the access change:** `tailscale serve reset`, then restore `records.json`, `lab.json` and `docker-compose.override.yml` from `pre-tailnet-*`. Switch the main checkout back to `da95220`, restart Nucleon, and recreate the LibreChat `api` container.
