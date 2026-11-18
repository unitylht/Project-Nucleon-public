# Nucleon patch: MCP-UI cards visible by default (LibreChat v0.8.8)

Status: release candidate rc2, verified in an isolated instance. The live LibreChat has NOT been switched over.

## Base and series

- Base: LibreChat tag `v0.8.8` = `e8f3be08623663d4ad7f7241e693c94469b63bb0`.
- Branch: `feat/nucleon-mcp-ui-default-visibility` in `~/Developer/LibreChat-card-visibility-dev`.
- Patch series (client only), regenerated with `git format-patch e8f3be0..32bf745 -o nucleon-patches`:
  1. `0001-feat-client-show-MCP-UI-cards-by-default-in-tool-cal.patch` (commit `15c5316`, the earlier "poc" image).
  2. `0002-feat-client-reveal-card-phases-and-remember-manual-c.patch` (commit `32bf745`, rc2).
  3. to 6.: `0003` (confirmation link), `0004` (tailnet origin), `0005` (Cloudflare origin), `0006` (Nucleon link in the left nav); see the rc3 to rc6 sections below.
- Images (local only): `librechat:nucleon-card-v0.8.8-poc` (= 0001), `librechat:nucleon-card-v0.8.8-rc2` (= 0001 + 0002). The official `registry.librechat.ai/librechat-ai/librechat:v0.8.8` is untouched.

## Behaviour

A call "has a card" iff its attachments contain `ui_resources` entries that pass the existing `isSupportedUIResource` (text/html). Generic: no matching on output text, tool names or server names. Shared helper: `client/src/components/MCPUIResource/supported.ts`.

1. `ToolCall`: opens when a card is present; a card arriving after first render (completion, hydration) reveals once (ref-tracked).
2. `ToolCallGroup`: a group holding a card does not auto-collapse, reveals once on late arrival, and is no longer held shut by the "inside a completed phase" suppression.
3. `ActivityPhaseGroup` (rc2): a folded activity section (server-labelled phase, or the client-synthesised fold, including the live "Running..." section) whose calls carry a card is not folded shut, does not fold after its entrance animation, and reveals once if the card arrives late.
4. `ToolCallInfo`: card first; raw output behind a collapsed "Output" disclosure (existing key `com_ui_output`), then Parameters. Calls without a card render as before.
5. `cardDisclosure.ts` (rc2): a module-scoped in-memory `Map` records only the reader's MANUAL collapse/expand choice, for calls (`call:<toolCallId>`), groups (`group:<first call id>`) and sections (`phase:<first call id>`). It is consulted before auto-opening, written only by manual toggles and only for cards, and lives for the page session (a reload of a saved conversation reveals the card again). No localStorage or Recoil.
6. Unchanged: `autoExpandTools` behaviour, calls without cards, the iframe sandbox, the renderer, sanitisation, `onUIAction`/`handleUIAction`, permissions, errors/OAuth/progress UI.

## Files changed (12; +873/-67 including tests)

Source: `MCPUIResource/supported.ts` (new), `MCPUIResource/Renderer.tsx` (re-exports `isSupportedUIResource`), `Chat/Messages/Content/{ToolCall,ToolCallGroup,ToolCallInfo,ActivityPhaseGroup}.tsx`, `Chat/Messages/Content/cardDisclosure.ts` (new).
Tests: `__tests__/{ToolCall,ToolCallInfo,ToolCallGroup,ActivityPhaseGroup}.test.tsx` extended, `__tests__/ToolCall.mcpui.test.tsx` (new, real renderer).

## Test results

### Automated (node 24.16.0-alpine container, repo bind-mounted; the host has no node)
- Targeted (ToolCall*, ActivityPhaseGroup): 6 suites, 198 tests pass. Mutation checks: with card detection forced off, 12 ToolCall/ToolCallGroup tests and 4 phase tests fail.
- `src/components/Chat/Messages` + `src/components/MCPUIResource`: 102 suites, 1674 tests pass. In each parallel run two unrelated suites (different ones each time: HoverButtons and styles.spec this time; ContentParts.integration and HeaderLabel earlier) report a suite-level failure with 0 failed tests, and pass when run alone (36 and 81 tests): load flakiness, not caused by the change.
- `tsc --noEmit` (client), ESLint and Prettier on touched files: clean.

### Browser-verified (rc2 image, isolated instance 127.0.0.1:3081, Chrome for Testing 1440x900, fresh profile, `autoExpandTools` unset)
Script `nucleon-test/browser_check_rc2.py`; results `nucleon-test/evidence/rc2/result_rc2.json`; screenshots in `nucleon-test/evidence/rc2/`.

Saved fixtures were seeded into the isolated Mongo only (`nucleon-test/seed_fixtures.js`). Shapes and the real Nucleon card attachment (balanceEstablished false, caveat text) are copied from a real earlier test conversation; the tool calls are adjacent as in a parallel step; tool-call ids are unique per conversation. Fixture A is one assistant message with a group of three calls (findCustomers, invoices, customerOverview with the card). Fixture B is the same calls split into two labelled batches, which the client folds into an Activity Section. Both end with "Harbour Demo Logistics owes AUD 2,580.00." (no caveat). One live Qwen run (terse agent) covers async arrival and omission.

| # | Check | Result |
|---|-------|--------|
| 1 | Ordinary card auto-expands | pass: customerOverview row expanded, card visible, no click |
| 2 | Grouped calls: only the card call opens | pass: group "Ran 3 actions" open; findCustomers and invoices rows closed; customerOverview open (`01_grouped_calls_card_open.png`) |
| 3 | Folded Activity Section with a card is revealed | pass: a section card rendered (`activity-phase-card` count 1), header "Opened the customer overview" expanded, the ordinary labelled group ("Looked up ... and its invoices") closed, the card batch open (`04_activity_section_revealed.png`) |
| 4 | Manual collapse sticks, incl. remount | pass: collapsed the card row, switched conversation in-app via the sidebar and back without reload: still collapsed, 0 card iframes (`02_grouped_manual_collapse.png`, `03_grouped_after_remount_still_collapsed.png`) |
| 5 | Async arrival (live run) | pass: card visible while the run was still streaming (first card at 2.9 s of 9.2 s, live "Running..." section already open) (`05_live_card_arrives_mid_run.png`) |
| 6 | Saved-conversation reload | pass: after a full page reload the card call is open again (no recorded choice) |
| 7 | Omission: warning visible without clicking | pass: the final answer has no caveat wording; the card shows the UNCONFIRMED banner and the "worked out" mark. On reopening a saved conversation the card top, amount and UNCONFIRMED banner are inside the initial 1440x900 viewport (card top y=382); the lower part of the card (invoice list) and the final answer line need scrolling (`07_omission_reopen_viewport.png`, `06_live_final_answer_and_card.png`) |
| 8 | Ordinary calls unchanged | pass: findCustomers/invoices rows stay `aria-expanded=false` in all runs |
| 9 | Console | 0 console errors, 0 page errors, 0 HTTP errors |
| 10 | Sandbox | all card iframes have `sandbox="allow-scripts"` exactly |

Not tested in the browser: mobile width; a server-labelled phase marker (same component as the synthesised fold, covered by unit tests).

## Build

```
cd ~/Developer/LibreChat-card-visibility-dev
docker build -f Dockerfile --build-arg NODE_MAX_OLD_SPACE_SIZE=5120 \
  --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_BRANCH=feat/nucleon-mcp-ui-default-visibility \
  -t librechat:nucleon-card-v0.8.8-rc2 .
```
Tests and typecheck run in a container: `docker run --rm -v "$PWD":/app -w /app node:24.16.0-alpine sh -c 'npm ci && npm run build:data-provider && npm run build:client-package && cd client && npx jest --ci --coverage=false <paths>'`. The `node_modules` in this clone are Linux binaries.

## Isolated test instance

`nucleon-test/` is git-ignored (`.git/info/exclude`: `.env` with generated secrets, `mongo-data/`, credentials, evidence). It holds `docker-compose.yml` (project `lc-cardtest`, containers `lc-cardtest-api` and `lc-cardtest-mongo`, own network, bind-mounted Mongo, api on 127.0.0.1:3081 only) and `librechat.yaml` (LM Studio qwen3.5-35b-a3b, `nucleon-local-staff` MCP only).
```
cd nucleon-test
docker compose -p lc-cardtest up -d                 # http://127.0.0.1:3081
docker exec -i lc-cardtest-mongo mongosh --quiet LibreChatCardTest --file /dev/stdin < seed_fixtures.js   # idempotent
docker compose -p lc-cardtest down                  # never -v
```
Scripted `/api/*` calls need a browser User-Agent.

## Switchover to the live stack (documented only; NOT executed)

1. Back up: `cp ~/Developer/LibreChat/docker-compose.override.yml ~/Developer/LibreChat/docker-compose.override.yml.bak-pre-card-rc2`.
2. In that override change only `services.api.image` from `registry.librechat.ai/librechat-ai/librechat:v0.8.8` to `librechat:nucleon-card-v0.8.8-rc2`.
3. `cd ~/Developer/LibreChat && docker compose up -d --force-recreate api` (api only; do not touch mongodb, meilisearch, rag_api or vectordb; never `down -v`).
4. Check `docker logs LibreChat`, open a customerOverview chat and confirm the card opens by itself.

## Rollback

Restore the backup override (or set `image:` back to `registry.librechat.ai/librechat-ai/librechat:v0.8.8`, still present locally and unchanged) and run `docker compose up -d --force-recreate api`. Data volumes are not involved.

## Reapply to a future LibreChat version

`git checkout -b <branch> <new-tag> && git am nucleon-patches/000*.patch` (or `git apply --3way`). Likely conflicts: `ToolCallInfo.tsx` (Parameters block became `Disclosure`), `ToolCall.tsx` (`showInfo` initial state, effects, `hasInfo`), `ToolCallGroup.tsx` (`autoCollapse`, `suppressAutoExpand`, initial `isExpanded`/`userOverride`, `handleToggle`), `ActivityPhaseGroup.tsx` (`foldsIn`, `isExpanded`, the fold effect, `handleToggle`), `MCPUIResource/Renderer.tsx`. The tests mock `~/utils` and `~/hooks` strictly, so keep new helpers out of `~/utils`. Re-run the six targeted suites.

## Remaining hiding mechanisms and limitations

- The choice record is per page session: a hard reload or a new tab reveals the card again, by design.
- Keys come from the first tool call id of a group or section; if that first call changes after a manual choice, the disclosure reads as new and reveals again.
- A card that is not `text/html` is not treated as a card (unchanged `isSupportedUIResource`), so such calls stay collapsed.
- Parallel-lane layouts (`ParallelContentRenderer`) and subagent panels were not inspected for fold behaviour.
- With `autoExpandTools` on, live folding is off and behaviour is the stock one plus the card reveal.
- The card is about 650 px tall at 1440 px width: on open, its top and the UNCONFIRMED banner are in the first viewport, but its invoice list and the final answer need scrolling.

## Deployed (live stack, port 3080)

- Switched on 2026-10-25T20:57:57Z (container clock, UTC) with the user's explicit approval. Only the `api` service was recreated: `docker compose up -d --no-deps --force-recreate api` in `~/Developer/LibreChat`.
- Image before: `registry.librechat.ai/librechat-ai/librechat:v0.8.8` (`sha256:5b706bcee1ca…`). After: `librechat:nucleon-card-v0.8.8-rc2` (`sha256:c667b1fda4b7f99e6ffcec3f35ac85d54efa0c4b2bca7a6fda51770a15682ee8`).
- Change: one line in `docker-compose.override.yml` (`services.api.image`). `.env` and `librechat.yaml` untouched.
- Smoke results (browser, fresh profile, `autoExpandTools` unset; script and screenshots in `nucleon-test/deploy-3080/`): login and history intact (agents all 6 listed; conversations 138 before, 140 after = the two smoke chats); "Nucleon LOCAL Staff (Qwen)" customerOverview card opens by itself, findCustomers stays collapsed, card above the raw output (Output disclosure), same after reload; "Nucleon CARD TEST – terse (Qwen)" answer omits the caveat and the UNCONFIRMED banner is visible without a click (card top inside the first 1440x900 viewport), same on reopen; iframes `sandbox="allow-scripts"`; startup log: 0 errors, MCP initialised with 3 configured servers / 46 tools (LibreChat's own startup connect). The other four containers kept their original start times; nucleon-local on 8630 healthy.
- Backups (permissions preserved, chmod 600): `/Users/unitylht/Developer/LibreChat-card-visibility-dev/nucleon-test/deploy-3080/backup-pre-rc2-20261026-075754/` (docker-compose.override.yml, .env, librechat.yaml). Not committed.
- Rollback: `cp -p /Users/unitylht/Developer/LibreChat-card-visibility-dev/nucleon-test/deploy-3080/backup-pre-rc2-20261026-075754/docker-compose.override.yml ~/Developer/LibreChat/docker-compose.override.yml && cd ~/Developer/LibreChat && docker compose up -d --no-deps --force-recreate api`.

## rc3-test (patch 0003): allow-listed confirmation link

Status: test image only (`librechat:nucleon-card-v0.8.8-rc3-test`). Not deployed to the live stack; rc2 (live) and the `-poc` image are untouched. Branch `feat/nucleon-confirm-link`, based on rc2 (`0b3b5d7`). Patch file: `nucleon-patches/0003-*.patch` (`git format-patch -1`).

### What it does (client only)
`handleUIAction` (`client/src/utils/index.ts`) used to ignore MCP-UI `link` actions. It now has a `link` branch that NEVER sends anything to the model (no `ask`) and opens a page only when `client/src/utils/nucleonLinks.ts` accepts the URL and the user has just clicked:

- `new URL(raw)` parses, protocol is exactly `http:`, `url.origin` is in `ALLOWED_ORIGINS` = `http://127.0.0.1:8631` (local Nucleon runtime) and `http://127.0.0.1:18631` (isolated Phase B test instance);
- no username/password, pathname exactly `/`, no query (a bare `?` is refused too), hash matches `^#/actions/act_[0-9a-f]{16}$`;
- the raw string has no whitespace or control characters and equals the re-serialised canonical URL `<origin>/<hash>` (no case, port, encoding or backslash tricks);
- transient user activation: `navigator.userActivation?.isActive === true`; if the API is missing the link is refused.

Then `window.open(url.href, '_blank', 'noopener,noreferrer')`. Anything else logs a URL-free `console.warn` and does nothing. All three call sites (`ToolCallInfo`, `UIResourceCarousel`, `MCPUIResource`) go through `handleUIAction`, so the tool-call panel and inline markers both reach the branch. Not changed: iframe sandbox (`allow-scripts`), `sandboxPermissions`, sanitisation, CSP, and `tool`/`intent`/`prompt`/`notify` behaviour; patches 0001/0002 behaviour is intact.

### Limitation: local only
The allow-list is a compile-time constant (rebuild the image to change it) and contains plain-http loopback origins only. A remote deployment needs an authenticated HTTPS origin added to `ALLOWED_ORIGINS`; do not add arbitrary hosts. Contract with the card: `<origin>/#/actions/<actionId>`, sent from the card's click handler as `postMessage({type:'link', payload:{url}})`.

### Tests (node 24.16.0-alpine container)
- New `client/src/utils/__tests__/nucleonLinks.spec.ts` (69 tests): validator accept/refuse matrix (other host/port/scheme, `javascript:`/`data:`/`file:`, suffix host, `localhost`, credentials, query, other path/hash, uppercase or extra id characters, percent-encoding, whitespace/control characters, non-strings), handler opens only with activation (window.open mocked), `link` never calls `ask`, `tool`/`intent`/`prompt` unchanged.
- Previous targeted set (ToolCall*, ActivityPhaseGroup): 6 suites, 198 tests pass. Wider (`src/components/Chat/Messages` + `src/components/MCPUIResource`): 102 suites, 1,710 tests pass (rc2 recorded 1,674; the same 102 suites, the difference is suites that failed at suite level in the earlier flaky run). `src/utils`: 73 suites, 1,894 tests pass. `tsc --noEmit`, ESLint, Prettier on touched files: clean.

### Build
```
cd ~/Developer/LibreChat-card-visibility-dev
docker build -f Dockerfile --build-arg NODE_MAX_OLD_SPACE_SIZE=5120 \
  --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_BRANCH=feat/nucleon-confirm-link \
  -t librechat:nucleon-card-v0.8.8-rc3-test .
```

### Run on the isolated 3081 instance
In `nucleon-test/docker-compose.yml` (git-ignored; not edited by this change) set the `api` service `image:` line to `librechat:nucleon-card-v0.8.8-rc3-test`, then `cd nucleon-test && docker compose -p lc-cardtest up -d --force-recreate api` (http://127.0.0.1:3081). Never touch the live stack on 3080 for this.

### Rollback to rc2
Set that image line back to `librechat:nucleon-card-v0.8.8-rc2` and recreate `api` as above. The rc2 and -poc images are not retagged. Source rollback: `git checkout feat/nucleon-mcp-ui-default-visibility`.

## rc4-tailnet (patch 0004): the Nucleon tailnet origin, live on 3080 since 27 Oct 2026
- **What changed:** `cf32892`, on branch `feat/nucleon-confirm-link-tailnet` from `4783ee4`. It adds `https://nucleon.tail492813.ts.net:8443` to `ALLOWED_ORIGINS` in `client/src/utils/nucleonLinks.ts`. That address is the local Nucleon Records behind Tailscale Serve, tailnet and its shares only.
- **Protocol check:** `https:` is now accepted for listed origins. The origin list still pins the scheme, so `https://127.0.0.1:8631` stays refused.
- **Tests:** `nucleonLinks.spec.ts` passes 74/74, with 5 new tailnet cases: the tailnet origin is accepted; http on that host, a missing port, a suffix host and another tailnet machine are refused.
- **Patch file:** `nucleon-patches/0004-*.patch`.
- **Image:** `librechat:nucleon-card-v0.8.8-rc4-tailnet`, built from `cf32892` with the same `docker build` command as rc3. It is the live 3080 image; only `services.api.image` changed in `docker-compose.override.yml`, and only `api` was recreated.
- **Browser check over the tailnet (member account, real Qwen):** the decision card appeared after 12 s, and its *Provide information in Nucleon* button opened `https://nucleon.tail492813.ts.net:8443/#/actions/act_…`, already signed in as Staff. Login and history on `127.0.0.1:3080` are unchanged.
- **Rollback:** copy `docker-compose.override.yml` back from `~/Developer/nucleon-local/backup/pre-tailnet-*/` (it names rc3-test), then run `docker compose up -d --no-deps --force-recreate api`.

### Live config changes in the same round (`librechat.yaml`, git-ignored; backup in `~/Developer/nucleon-local/backup/pre-team-accounts-*/`)
- **Agent creation:** `interface.agents.create` was removed from the file, so each role keeps its own value: ADMIN may build agents, USER (group member accounts) may not. With `create` set explicitly, LibreChat overwrites both roles at every start. The USER role was set to `AGENTS.CREATE=false` in Mongo `roles`.
- **M6 connections:** `chatMenu: false` was set on the remote M6 servers `nucleon-staff` and `nucleon-owner`. LibreChat enforces this on the server (`filterChatSelectableMCPServers`), so a member can't attach them to a chat. The agents that use them are unchanged.
- **ADA agent:** "Nucleon ADA Staff (Qwen)" is shared to role USER as `agent_viewer`, through the ACL (`aclentries`).
- **DOMAIN_CLIENT and DOMAIN_SERVER:** left at `http://localhost:3080` on purpose. That keeps the cookies non-Secure, so both `127.0.0.1:3080` and the tailnet HTTPS address work.

## rc5-cf (patch 0005): the Nucleon Cloudflare origin, for the public PoV (31 Oct 2026)
- **What changed:** `a130836`, on branch `feat/nucleon-confirm-link-cloudflare` from `9764d1d`. It adds `https://nucleon.dracooz.top` to `ALLOWED_ORIGINS` in `client/src/utils/nucleonLinks.ts`. That hostname is the Nucleon Records service published through a Cloudflare Tunnel, behind Cloudflare Access (email one-time code). The loopback and tailnet entries stay (Tailscale is retired, but the entry is harmless and keeps rc4 behaviour); the list is still a compile-time constant.
- **Scheme and port stay pinned:** the check compares `url.origin` with the list, so `http://nucleon.dracooz.top`, `https://nucleon.dracooz.top:8443`, `https://creditease.dracooz.top` (the LibreChat host itself), suffix and lookalike hosts and userinfo forms are all refused.
- **Tests:** `nucleonLinks.spec.ts` passes 81/81 (74 before): the allow-list pin has four entries, the origin is accepted, and six new refusal cases (http, port, suffix host, lookalike host, other dracooz.top host, credentials). Run in `node:24.16.0-alpine` with the repo bind-mounted: `docker run --rm -v "$PWD":/app -w /app/client node:24.16.0-alpine npx jest --ci --coverage=false src/utils/__tests__/nucleonLinks.spec.ts`.
- **Patch file:** `nucleon-patches/0005-*.patch` (`git format-patch -1 --start-number 5`), also kept in the Nucleon repo at `integrations/librechat/patches/`. Check: `git am` of 0001-0005 on `e8f3be0` in a throwaway worktree applies cleanly and the tree equals `a130836` (the only difference is this file, which is not part of the series).
- **Image:** `librechat:nucleon-card-v0.8.8-rc5-cf` (`sha256:32500f25564e…`, 4.55 GB), built from `a130836` with the same command as rc3, `BUILD_BRANCH=feat/nucleon-confirm-link-cloudflare`. The built client bundle contains the new origin. It is NOT tagged `latest`, and the live stack still runs rc4-tailnet until the coordinating session switches `services.api.image`.
- **Build:**
```
cd ~/Developer/LibreChat-card-visibility-dev
docker build -f Dockerfile --build-arg NODE_MAX_OLD_SPACE_SIZE=5120 \
  --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_BRANCH=feat/nucleon-confirm-link-cloudflare \
  -t librechat:nucleon-card-v0.8.8-rc5-cf .
```
- **Rollback:** set `services.api.image` back to `librechat:nucleon-card-v0.8.8-rc4-tailnet` (still present locally) and recreate `api` only. Note rc4 cannot open the Cloudflare link, so with it the card button does nothing for `https://nucleon.dracooz.top`.
- **Must match on both sides:** `CONFIRM_ORIGINS` in the Nucleon `lab/card.py` and the `recordsPublicUrl` check in `lab/config.py` carry the same four origins.
- **LibreChat v0.8.8 environment (checked in this tree, `api/server/index.js`, `packages/api/src/oauth/csrf.ts`, `packages/api/src/middleware/origin.ts`):** `TRUST_PROXY` is a hop count (`Number(TRUST_PROXY) || 1`, so unset, 0 or non-numeric all mean 1) passed to Express `trust proxy`; `DOMAIN_CLIENT` and `DOMAIN_SERVER` feed the same-origin guard on login endpoints and, through `DOMAIN_SERVER`, the Secure flag of the session cookies (`SESSION_COOKIE_SECURE=true|false` overrides the heuristic); `ALLOW_REGISTRATION` and `ALLOW_SOCIAL_REGISTRATION` are read as before. Details are in the Nucleon `integrations/librechat/README.md` and `docs/DEPLOYMENT.md`.

## rc6-nav (patch 0006): a Nucleon link in the left rail (S6b, 31 Oct 2026)
- **Series:** `0006-feat-client-nucleon-link-in-the-left-nav.patch` (`git format-patch -1 -o`), commit `93fdcd7` on `feat/nucleon-confirm-link-cloudflare`, on top of 0001-0005. Client only; applies cleanly after 0005.
- **Behaviour:** `client/src/components/Nav/NucleonLinkButton.tsx` renders an icon button (atom icon, tooltip and `aria-label` "Nucleon") in the left icon rail of the unified sidebar, under New chat and the Agent Marketplace button. The rail is also visible when the sidebar is collapsed, so the link is too. It is a plain `<a href=... target="_blank" rel="noopener">`: it opens a new tab and leaves the chat as it is. No Nucleon-specific logic beyond the label and the address. The mobile drawer is not changed.
- **Address:** LibreChat 0.8.8 has no runtime config field for an external link in the startup config (`interface.customFooter` is a footer, not a nav item), so the address is a build-time Vite env: `VITE_NUCLEON_URL`, default `https://nucleon.dracooz.top`. A change needs an image rebuild: pass `--build-arg VITE_NUCLEON_URL=https://...` (the Dockerfile gained `ARG VITE_NUCLEON_URL=`, empty means the default).
- **Test:** `ExpandedPanel.spec.tsx` gains one test (href, `target=_blank`, `rel=noopener`, label, expanded and collapsed); the sidebar suites pass (9 suites, 50 tests); `tsc`, ESLint and Prettier clean. The `react/jsx-no-target-blank` rule wants `noreferrer`; the line carries an eslint-disable because `noopener` was specified (Nucleon may receive the Referer).
- **Image:** `librechat:nucleon-card-v0.8.8-rc6-nav`, built with the command above (same as rc5-cf with `BUILD_COMMIT` of `93fdcd7`). Live on 3080 since S6b.
- **Build:**
```
cd ~/Developer/LibreChat-card-visibility-dev
docker build -f Dockerfile --build-arg NODE_MAX_OLD_SPACE_SIZE=5120 \
  --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_BRANCH=feat/nucleon-confirm-link-cloudflare \
  -t librechat:nucleon-card-v0.8.8-rc6-nav .
```
- **Rollback:** set `services.api.image` in `~/Developer/LibreChat/docker-compose.override.yml` back to `librechat:nucleon-card-v0.8.8-rc5-cf` (backup: `docker-compose.override.yml.bak-pre-rc6-nav`) and run `docker compose up -d api`.
- **Config in the same slice (runtime, `librechat.yaml`):** `interface.presets/prompts/bookmarks/multiConvo/parameters: false`, `modelSelect` and `agents.use` stay true, `interface.customWelcome` set (a key in 0.8.8, `packages/data-provider/src/config.ts`). `agents.create` is still not set.
