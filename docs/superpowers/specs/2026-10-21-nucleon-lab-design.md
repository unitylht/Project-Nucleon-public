# Nucleon Lab: a reuse experiment on the conversation layer (design, 21 October 2026)

Status: design for an isolated experiment on branch `explore/agent-coordinator-20261019`, to be deployed beside the records site (`/`) and the current preview (`/preview/`, the comparison baseline), with its own fictional data. Nothing here changes the records site. The investigation that led to this design is summarised in §2; its memos are scratch notes, not records.

## 1. Intent

The team asked how far existing projects and frameworks can make Nucleon more natural and maintainable, and asked for a working, deployed experiment tested in a real browser as both roles, compared with the current preview on the same model and equivalent data.

Nucleon's product idea: people and AI agents access, discuss, retain and work with business information in plain words; the owner's knowledge is qualitative and time-sensitive; the agent helps find what is missing and asks the right person; the records system stays the reliable backend; role privacy and consequential business commitments stay explicit.

## 2. What the investigation found (21 October)

**Causes of the seven review findings** (from the preview's own database and code, not from guesswork):

| # | Finding | Cause |
|---|---|---|
| 1 | priorities with stale counts and a Supplies link | the requests tool works one customer at a time with no status filter; the card's link comes from the thread's last single-customer turn, which was a staff turn |
| 2, 3 | "would ten days fit?" unanswered / withheld | no operation compares an extension without preparing one; the guard requires every digit and date to appear in a tool result, so the correct date (which no tool returned) and the owner's own "ten" are withheld |
| 4 | preparing worked | the date arithmetic exists only inside `prepareDecision` |
| 5 | "cancel" became a prepared decline | there is no withdraw operation anywhere; the model picked the nearest tool; the grounding check covered approvals only |
| 6 | staff "waiting on whom" missed Logistics | no per-role work queue across customers; the model checked only the customer in focus |
| 7 | generic phone script | the situation is built for the previous customer; nothing produces a holding message; the model never asked where the requests stand |

Conclusion: the failures are missing **business operations** and a guard that is a **workaround** ("digits must appear in results") for the real rule ("figures are computed by code"). They are not caused by the vanilla front end or by the absence of an agent framework. Three spikes with the same local model (Gemma 4 26B through the gateway) confirmed this: with a `date_after` tool, the ten-day question was answered correctly in 3 s; a `withdraw` tool made "cancel" a withdrawal; a role filter kept staff from preparing anything, while the model still *claimed* to have prepared a decline, which is why a claim check remains a genuine requirement.

**Frameworks and front ends** (official sources read on 21 October; versions in the research notes):

- *LibreChat* (MIT, v0.8.8): a credible stock front end with admin-enforced tool approval and per-user MCP headers, but it needs MongoDB (no Homebrew or Docker on this machine), its config schema changed four times in five weeks, it shows the model's reply as-is (no claim check), and the course brief warns that a generic chatbot does not meet the value proposition. *Open WebUI* supports MCP elicitation but its tool approval is per-user and experimental. *Dify* needs Docker and is a workflow builder.
- *Pydantic AI* (MIT, 2.58.0, Python ≥ 3.11, 45 packages / 106 MB with `[openai]` + `mcp`): tools from functions, per-role `prepare` hooks, dependency injection, output validators with `ModelRetry`, usage limits, `FunctionModel` for tests, AG-UI adapter, approval-required tools. It replaces the loop mechanics (about 270 lines of ours); the prompts, role-scoped views and guard logic stay ours. Its approval flow ends the run and is "not an authorization boundary against an untrusted client". Fast-moving (V2 in June, V3 expected; four security advisories in three weeks).
- *LangGraph* adds graphs, checkpoints and interrupts at 1.5–2× the cost; self-hosting its server for production needs an enterprise licence. Not chosen.
- *assistant-ui* (MIT, 0.15.x): React chat components that build to static files (Vite), with a local runtime adapter, tool-call UIs, thread list and message editing; no Node server at runtime; 0.x churn. *CopilotKit* needs its own TypeScript runtime server or paid tiers for the equivalent and sends telemetry by default. Not chosen.
- *MCP* (spec 2026-07-28, Python SDK `mcp` 2.3.0): exposing Nucleon's operations as an MCP server lets other agents (Claude Code, Open WebUI, LibreChat) use the same reliable operations with the caller's role from a bearer token.

## 3. Decision: what the experiment is

**Nucleon Lab** is a third deployment at `/lab/` with three reused parts and one reusable asset:

1. **The reusable asset: Nucleon's business tool layer.** A framework-neutral set of operations in the records server, available over one HTTP surface (`POST /api/tools/<name>`, role from the session), used by the Lab agent, by the MCP server, and later by the existing desk. Every figure, date and comparison is computed in code; every result carries display text beside ISO values, amounts with their mark, and the subject it is about. Role privacy is enforced inside each operation. New operations close the review's causes: `compareExtension` (calculate, no write), `withdrawPreparation` (distinct from decline), `workQueue` (per role, across customers, with "waiting on whom"), `listRequests` with a status filter, and `prepareHoldingMessage` (a promise-free status text for staff to use outside Nucleon). Human-only operations (`confirmDecision`, `confirmContext`, `createCustomer`) are never offered to an agent.
2. **Reused agent framework: Pydantic AI** for the Lab's conversation loop: tools are the business operations called over HTTP with the person's own session; per-role availability through `prepare` hooks fed by the existing capability registry; the guard becomes output validators (no claim of an action no tool performed; amounts carry their mark; no credit judgement; figures must come from results or from the person's own message, by reference not by recomputation) with one framework retry; `FunctionModel` for tests. **Confirm stays an app action:** the prepared-decision card's button calls the records API directly; the model is never in the commit path.
3. **Reused UI components: assistant-ui** (React, Vite, static files served by the Lab server): streaming replies, tool-call cards (overview, case, work queue, comparison, prepared decision with Confirm, draft customer with Create, holding message with Copy), a thread list, a role chip, links into the records pages. History is rebuilt server-side per role from the Lab's own SQLite; the browser's copy is never trusted.
4. **Reused protocol: MCP.** The same operations as an MCP server (streamable HTTP, bearer token → role from the Lab's configuration) so an external agent can discuss the same fictional business. Demonstrated with an MCP client in the checks.

Not built: LibreChat/Open WebUI deployments (documented as an option with their requirements), LangGraph, CopilotKit, hosted model APIs (configurable, untested, offered as the next comparison).

## 4. Goals, non-goals, anti-goals

Goals: a person speaks naturally, explores alternatives (compare before preparing), gives informal knowledge, changes their mind (withdraw), and advances work (prepare, confirm) without learning the workflow; the agent identifies what is missing and asks; both roles get a cross-customer picture; consequential commitments are explicit; the same operations serve people and agents; a fair comparison with the preview on the same model and data.

Non-goals: replacing the records interface; multi-tenant hosting; outbound messages; migrating `agent.py`'s intake, extraction and suggestion tasks (they stay as they are and are reached through the records API).

Anti-goals: the model computing dates or amounts; an agent committing a decision; staff seeing owner-only lines; wording-specific rules; a demo that only works on preloaded phrases.

## 5. Constraints

- Fictional data only; no secrets in git; the records site (`/`, `f95f50f`) untouched; the preview (`/preview/`, `df10ab6`) kept as the baseline; the Lab isolated: its own records instance, database, cookies (`nucleonl_`, Path `/lab`), ports (records 8623, Lab 8622), launch agents (`local.nucleon.lab-records`, `local.nucleon.lab`), logs and Caddy route (`/lab/*`, `/lab/records/*`).
- Local-model-first: the same Gemma gateway (`127.0.0.1:1236`), temperature 0; hosted endpoints configurable but marked untested.
- Dependencies live in the Lab's own venv (`~/srv/nucleon-lab/runtime`); the records server stays stdlib-only. Pinned versions.
- Write-capable checks run only on scratch servers (`deploy/scratch_only.js`).
- Every business boundary is enforced in the operations layer, not in prose patterns: the owner alone confirms; staff never receive private context; every figure is computed by code; nothing leaves Nucleon.

## 6. Decided by the team (from the brief)

Reuse where it cuts maintenance; the business API/tool layer as the reusable asset; configurable capabilities with all implemented tools enabled per role in the experiment; role privacy; clear consequential commitments; address general causes, not sentences; cancelling a proposal is distinct from declining a request; compare on the same model and data; test in a real browser as both roles with full conversations and unfamiliar wording; disclose any preloading; local-model-first with hosted APIs as a later comparison.

## 7. Decided by the builder (my calls, stated so they can be overturned)

- Confirm is a button to the records API, not a framework approval (safer, no extra model call, no trust in the client).
- The Lab talks to the records instance over HTTP with the person's cookie rather than importing the App in-process (thin integration; the same surface the MCP server and any future front end use).
- assistant-ui's local runtime with a custom adapter over a plain server-sent-events endpoint, rather than the AG-UI protocol (fewer moving parts; the AG-UI client and adapter versions are mid-transition).
- The Lab keeps its own conversation store (SQLite) with one general thread per workspace plus case threads, mirroring the preview so the comparison is like for like.
- The guard's figure rule in the Lab: a number or date in the reply must appear in a tool result of this run *or* in the person's own message; the model is told to quote results' display text. The claim, mark and judgement rules are unchanged.
- The MCP server maps a bearer token to a role from the Lab's config (fictional workspace only); no OAuth.

## 8. Left to the builder

File layout under `lab/`; the SSE event shape; the exact component set; test doubles; the deploy script's shape (a third `nucleonctl` instance plus a Lab launcher).

## 9. Validation

- Unit tests for every new operation (role filtering, calculations, withdraw, queue), the Lab validators with `FunctionModel`, the SSE endpoint and the session passthrough.
- Mock and live conversation checks for the Lab (reusing `conversation_check.js` scenarios where the API shape allows, plus the seven review examples and new broad ones).
- Browser testing by the builder through the public URL as owner and staff: discover work, understand a case, compare options, prepare, revise or withdraw, confirm; subject changes and broad questions; the same conversations on the preview for comparison; business state inspected after each commit.
- A comparison record (`docs/qa/LAB-COMPARISON.md`) with the actual replies, state changes, timings, and attribution: which gains come from the operations layer (reproducible without the framework) and which from the framework or UI.
