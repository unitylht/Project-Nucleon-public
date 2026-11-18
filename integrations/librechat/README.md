# LibreChat integration (patches, agent scripts, config examples)

Nucleon's chat front end is LibreChat **v0.8.8** (upstream commit `e8f3be08623663d4ad7f7241e693c94469b63bb0`) with five small client patches. This folder holds everything needed to rebuild our version, without copying LibreChat's own history.

**The working repository:** it stays on the maintainer's Mac, at `~/Developer/LibreChat-card-visibility-dev`. It has no GitHub remote, and **must never be pushed to the upstream LibreChat repository**.

## Patches (apply in order with `git am`)
| Patch | Commit there | Image | What it does |
|---|---|---|---|
| `0001` | `15c5316` | rc1/`-poc` | Shows MCP-UI cards by default in the tool-call panel |
| `0002` | `32bf745` | rc2 | Reveals the card's phases, and remembers a manual collapse |
| `0003` | `4783ee4` | rc3-test | Opens an allow-listed Nucleon confirmation or evidence link from a card (loopback origins only) |
| `0004` | `cf32892` | rc4-tailnet (live on 3080 until the public switch) | Adds the Tailscale origin `https://nucleon.tail492813.ts.net:8443` to that allowlist (Tailscale is retired, plan decision D6) |
| `0005` | `a130836` | **rc5-cf (public PoV)** | Adds the Cloudflare origin `https://nucleon.dracooz.top` to that allowlist |

- **Contents:** the patches hold code only; the long notes are in `NUCLEON-PATCH.md` here.
- **Checked:** applied to a clean checkout of `e8f3be0`, the five patches give a source tree identical to `a130836`, with no file different apart from `NUCLEON-PATCH.md` (repeated 31 Oct 2026 for 0005).
- **To rebuild:**

```
git clone https://github.com/danny-avila/LibreChat.git && cd LibreChat && git checkout e8f3be0
git am /path/to/Project-Nucleon/integrations/librechat/patches/000*.patch
docker build -f Dockerfile --build-arg NODE_MAX_OLD_SPACE_SIZE=5120 -t librechat:nucleon-card-v0.8.8-rc5-cf .
```

**Tests for the patches:** run them in a Node container; see `NUCLEON-PATCH.md` for the command.

**The card-link contract must match on both sides:** the origins in `ALLOWED_ORIGINS` (LibreChat, `client/src/utils/nucleonLinks.ts`, patches `0003`-`0005`) and `CONFIRM_ORIGINS` in `lab/card.py` (plus the `recordsPublicUrl` check in `lab/config.py`) are the same list, and a change needs a LibreChat image rebuild:

| Origin | What it is |
|---|---|
| `http://127.0.0.1:8631` | local Records |
| `http://127.0.0.1:18631` | isolated test instance |
| `https://nucleon.tail492813.ts.net:8443` | Records over Tailscale Serve (Tailscale is retired, plan decision D6; entry kept) |
| `https://nucleon.dracooz.top` | **Records through the Cloudflare Tunnel, behind Cloudflare Access (public PoV)** |

`recordsPublicUrl` in `lab.json` must be one of these four; for the public PoV it is `https://nucleon.dracooz.top`. An https origin that is not listed gets no card button on the Lab side and is refused by the client.

## Config examples
- **`librechat.env.example`:** only the `.env` keys that change for the public PoV, with comments: `DOMAIN_CLIENT` and `DOMAIN_SERVER` = `https://creditease.dracooz.top`, `TRUST_PROXY=1`, `ALLOW_REGISTRATION=false`, `ALLOW_SOCIAL_REGISTRATION=false` (and an optional `SESSION_COOKIE_SECURE`). The live `.env` is never committed. Exact names supported by v0.8.8:
  - **`TRUST_PROXY`:** a hop count, read as `Number(TRUST_PROXY) || 1` in `api/server/index.js` and given to Express `trust proxy`. Unset, `0` and non-numeric all mean 1. The ban logic (`BAN_VIOLATIONS`, `checkBan.js`) keys on `req.ip`, so with the tunnel in front it must see the visitor from `X-Forwarded-For`, not the loopback address of `cloudflared`.
  - **`DOMAIN_CLIENT`, `DOMAIN_SERVER`:** feed the same-origin guard on the login endpoints (`requireSameOrigin`), the OAuth and email links, and the base path. `DOMAIN_SERVER` also decides the Secure flag of the session cookies (`SESSION_COOKIE_SECURE=true|false` overrides it).
  - **`ALLOW_REGISTRATION`, `ALLOW_SOCIAL_REGISTRATION`:** as in LibreChat's `.env.example` (lines "Registration and Login"). The accounts created earlier with `bin/team-accounts` keep working.
- **`librechat.yaml.example`:** the live configuration.
  - **Tokens:** the MCP tokens come from environment variables (`${NUCLEON_*_MCP_TOKEN}`) set in LibreChat's `.env`, which is **never** committed.
  - **Group member accounts:** `interface.agents.create` is left out on purpose, so ADMIN and USER keep separate settings.
  - **M6 connections:** the remote M6 servers have `chatMenu: false`.
- **`docker-compose.override.yml.example`:** the live override.
  - **Image:** it selects the patched image.
  - **Ports:** LibreChat is bound to `127.0.0.1` only. Remote access goes through the Cloudflare Tunnel (`cloudflared` connects to 127.0.0.1:3080 and 127.0.0.1:8631), behind Cloudflare Access; see `docs/DEPLOYMENT.md`.

## Agent scripts (`agents/`)
They run with `docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < <script>`, and change Mongo directly.

| Script | Purpose |
|---|---|
| `seed_ada_agent_3080.js` | Creates "Nucleon ADA Staff (Qwen)" on the live stack |
| `update_ada_agent_instructions.js` | Adds "resolve once" to its instructions |
| `update_ada_agent_clarify.js` | Adds "ask instead of guessing" (`docs/KNOWN-LIMITATIONS.md` L-001) |
| `update_ada_agent_steps.js` | Rewrites the instructions as explicit steps. **This is the version in force until `update_ada_agent_hints.js` is run.** |
| `update_ada_agent_hints.js` | S3, **not run yet**: the instructions below (use `hint`, read `forModel`, one `whatIsNeeded` read) and the tools `whatIsNeeded`, `customerStatus` added to the Staff agent |
| `instructions_staff.txt`, `sync_instructions.py` | The one source of those instructions (the model bench reads it too); the script rewrites the block inside `update_ada_agent_hints.js`, `--check` verifies it |
| `seed_owner_agent_3080.js` | S3, **not run yet**: creates "Nucleon ADA Owner (Qwen)", a read-only assistant for the Owner (MCP entry `nucleon-local-owner`) |
| `seed_ada_agent.js`, `seed_phaseb_agent.js`, `seed_fixtures.js` | Seeds for the isolated test stack (port 3081) |

### Staff agent instructions after S3 (`instructions_staff.txt`, joined by spaces into the agent's instructions)

*Changed 31 Oct 2026 (D15): the steps are now findCustomers then resolveDecision with an ambiguity check; the earlier text had assessDecision and whatIsNeeded steps and stopped early (bench A4/A5 in `docs/research/MODEL-BENCH-20261031.md`).*

<!-- BEGIN STAFF INSTRUCTIONS (generated by agents/sync_instructions.py) -->
> You help a member of staff handle customer credit requests. Use tools for every business fact; never invent numbers, dates, ids or invoice numbers.
>
> Each request is exactly one kind: a trial credit for a new customer (order amount and terms in days) or an extension of one existing invoice (its invoice number and the new due date). If the message mixes the two, or an extension names no invoice, ask Staff one short question about what they mean and stop; do not guess.
>
> If a tool result has a hint, ask Staff exactly hint.question (and list hint.options, if there are any) and stop: make no further tool call this turn, and never retry with made-up values. If a tool returns INVALID_ARGUMENT or a schema error without a hint, ask Staff for the missing detail instead of retrying.
>
> Before any decision tool, classify the message. If it names an order amount or payment terms AND also an invoice, a due date or an extension, or if it is unclear which kind it is, it is mixed: ask Staff one short question about which they mean and stop, calling no decision tool. Only a message that is clearly one kind goes on to the steps.
>
> When Staff answer your question by naming one request ("the extension first", "Bayview"), handle only that one and stop: the other request waits for a message of its own. Never send two requests from one message unless Staff name both in it.
>
> Steps for a request: 1) findCustomers (and the invoice for an extension). 2) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning; the backend assesses the request itself and applies the Owner's policy. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. Do not call assessDecision or whatIsNeeded. 3) Stop calling tools: the request is finished.
>
> Every message that asks about a request gets the steps, even a message you have answered before, word for word, and even if you refused it a moment ago: Staff repeat a request when something changed outside the chat, usually the Owner deciding in Nucleon, so an earlier tool result (a CASE_OPEN refusal, a status) is history, not the current state. Never answer such a message from an earlier turn, never say "as I explained", and do not look it up with decisionStatus: call resolveDecision again for the request; the backend knows the earlier cases and refuses again itself if one is still open, and only its new result is the answer.
>
> Decision tool results are compact: status, handling, statusText, why, nextStep and a few keyFacts. Reply in at most two sentences: statusText as it is, then what nextStep says. Do not restate the card: no amounts, lists or sections from the result; the card under your reply shows them.
>
> The backend applies the Owner's delegation policy: report ONLY the outcome the tool result states; never say something is approved unless the result says decided/approved. If information is needed from Staff, tell them to use the button on the card. Nothing is ever sent to the customer by Nucleon; Staff informs the customer.
>
> Use decisionStatus (for one case) or customerStatus (for a customer) only when asked where something stands, and then answer from its result.
<!-- END STAFF INSTRUCTIONS -->

To roll out S3 on the live stack (the product lead does this, in this order; nothing here restarts LibreChat or Docker except step 3 if the MCP entry is new):
1. Switch the tools on as the Owner: Setup, "Agent tools", or `POST /api/agent-tools {"tool": "<name>", "enabled": true}` (Owner person, CSRF token) for `whatIsNeeded`, `comparableCases`, `customerStatus`, `policyBacktest`, `impactSummary`.
2. Restart the Lab so it runs the S3 code (the text for the model is then the compact `forModel`; the card is unchanged).
3. Owner agent only: add the `nucleon-local-owner` entry from `librechat.yaml.example` to the live `librechat.yaml`, put `NUCLEON_LOCAL_OWNER_MCP_TOKEN` in LibreChat's `.env` (the same value as the Owner token in the Lab config), restart LibreChat, then run `seed_owner_agent_3080.js`.
4. Staff agent: run `update_ada_agent_hints.js`.

## Related
- **Local runtime and demo tools:** `deploy/m3-local/` holds the Nucleon start/stop script, `demo-reset`, `demo-launcher` and `team-accounts`.
- **Known agent and model limitations:** `docs/KNOWN-LIMITATIONS.md`.
- **Deployment record:** `docs/ADA-LOCAL-ROLLOUT-PLAN.md`.

## Conversation titles (1 Nov 2026)

LibreChat titles each new chat with a second model call. Qwen3.5 reasons for about 2,000 characters before a five-word title (measured: 6 to 8 s, longer than the reply itself), and LM Studio's MLX template ignores every "no thinking" request parameter; the only thing that works is pre-filling an empty think block in the assistant turn, which LibreChat cannot do. So the LM Studio endpoint points at `deploy/m3-local/bin/title-proxy` (127.0.0.1:1235, started by `nucleon-local start`), a pass-through that recognises LibreChat's default title instruction (a single user message starting with "Provide a concise, 5-word-or-less title") and adds the pre-fill. Titles now take about 0.3 s; every other request, streaming included, is forwarded unchanged. Note: the agents endpoint ignores a custom `titlePrompt`, so the proxy matches the default text (and the marker `[title]`, for other setups).
