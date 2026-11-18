# PoV development roadmap — product lead direction

**Updated 30 October 2026 · INFS3605 Weeks 8–10**  
**Status:** Hanting's product/development direction, informed by Week 7 feedback. This is a prioritized roadmap **not a claim that every task is implemented, independently tested, or Owner-approved**.

## Objective

Turn a technically demonstrated local **proof of concept** into a coherent, trustworthy, easy-to-test **proof of value / MVP**. Preserve the Founder's Second Brain premise:

> **The Owner delegates a category of decisions and risk boundaries, not an approval click for every individual case.**

An agent should retrieve facts, ask Staff for missing evidence, evaluate the available tools, make an **internal** decision only when the **current Owner policy authorises it**, and escalate genuine exceptions. The backend, not language-model prose, controls financial calculations, permissions, exposure, idempotency and effective state. No outbound customer commitments without separately authorised workflows.

## Baseline to preserve before modifying code

The latest 27 Oct **developer-reported** local M3 handover claims:
- Nucleon Records/Lab `da95220`, separate LibreChat/Qwen ADA Staff agent; normal-browser 17/17 acceptance on `2b2b786`, follow-up fix tested/recorded on `da95220`.
- Scoped new-customer trial credit, invoice extensions, Staff evidence gathering, Owner policy versioning/pause/override and backend-grounded cards on **fictional** data.
- Default normal policy restored to **advisory v0**; no blanket automatic credit approval.
- Missing: one unified production-quality front end, general evidence acquisition, outbound communications, validated real commercial outcomes and a complete impact report.
- M3 application commits were reported local/unpushed; separate M6 deployment not upgraded to ADA. **Recheck current worktree before coding.**

These are **current documentation baselines**, not proof of live status on 30 Oct. See [engineering record](../memory/ADA-STATUS-20261027.md).

## Sequencing and acceptance criteria

| Order | Workstream | Deliverable | Acceptance / evidence |
| --- | --- | --- | --- |
| **P0** | Real Owner/Staff PoV testing | Guided and then independently attempted representative credit cases using an accessible, consented test environment | Observations, direct quotations, per-case outcomes, friction log, limitations; no invented ROI |
| **P0** | Unified agent-first UX | One coherent login/navigation and role-aware experience for chat, requests, records, customer context, Owner policies and history | Staff and Owner can complete target journeys without bouncing between unrelated sites or hunting for actions |
| **P0** | Existing policy-engine regression | Keep bounded autonomous internal approval, evidence provenance, over-limit escalation, override/pause, no double execution | Real Qwen/tool browser checks + deterministic backend tests; demonstrate failed policy checks prevent execution |
| **P1** | Explicit decision-and-outcome lifecycle | Link request, facts, model suggestion, actual authority, policy version, actor, Owner correction and later repayment observation when available | View one case from request to recorded decision; clearly identify later outcomes as **unknown/pending** until observed |
| **P1** | Minimal AI impact report | Counts and denominators for agent-resolved, evidence-needed and Owner-reviewed cases; processing time and overrides | All displayed numbers trace to actual records; estimated labour saving explicitly labelled with measured/manual baseline |
| **P1** | Owner-usable onboarding and controls | Simple business setup, versioned policy, default advisory, understandable delegation/hold/pause | Owner can explain the consequences of a policy change; no silent authority expansion |
| **P1** | Final demo reliability | Rehearsed real-service scenarios, screen-readable cards, captioned recording, tested audio fallback | Narration and screen share work in final venue; does not conflate sped-up video with real-time latency |
| **P2** | Broader forecasting/credit-limit optimisation, general outbound workflows | Explicitly deferred unless core PoV succeeds | Separate research, security, authority and time budget; never weaken safeguards to add breadth |

### Product and engineering decisions to preserve

- **An agent-first UI, not “just another dashboard.”** Traditional records/policy views remain for auditability and infrequent complex tasks.
- **Avoid false staff delegation.** Staff can supply evidence but need not accept a credit-approval liability merely to confirm an AI decision.
- **Three distinct checks:** evidence sufficiency, business risk/exposure, demonstrated reliability. A free-text LLM “confidence” is not authority or validated accuracy.
- **Policy changes are Owner-authorised.** Comparable cases can motivate proposals; neither AI nor an individual prior Owner exception automatically grants wider permission.
- **Evidence provenance matters.** “Customer says paid”, “Staff checked bank” and “recorded ledger receipt” are different sources; unknown is not zero.
- **Real outcomes arrive later.** Maintain pending/unknown, late, on-time and loss states without inferring outcomes from toy fixtures.
- **Safe iteration.** Keep the currently demonstrated behaviours and test matrix intact during UI refactoring; do not replace the functioning backend to gain cosmetic consistency.

## Working implementation slices (proposed)

1. **Audit/contract:** verify actual M3 branches, tool surfaces, deployed ports and role permissions; snapshot current regression and identify which chat-to-backend calls the unified UI must preserve.
2. **UX shell:** unified navigation, role landing pages, owner policy/requests/history, Staff chat and evidence flow; one entry point, consistent language and state labels.
3. **Agent reliability:** trace tool invocation → verified facts → policy check → authoritative card/action → audit entry. Remove duplicate or contradictory status text. Re-test cancellation, retries, permissions and audit.
4. **Lifecycle:** add explicit case event timeline and links to eventual repayment evidence, with “not yet known” as a valid outcome; retain immutable history for corrections.
5. **Impact and PoV:** instrument case handling and session friction, run owner/staff tests, fix high-impact issues, produce defensible before/after evidence.
6. **Final handoff:** compact system overview, deployment truth, end-to-end use case, PoV evidence and known limitations.

## Definition of meaningful PoV

Technical correctness is necessary but insufficient. Evidence should show the owner would **actually authorise/use** the workflow, users can operate it, the Agent removes net work rather than moving it to Staff, its reasoning and actions can be challenged, and business records remain correct. Record failed tests as evidence too.

Success thresholds and real-world risk caps have **not** been ratified. Do not fabricate targets, accuracy, savings or representative customer outcomes.

## Dependencies and non-goals

- Week 8 user testing requires **scheduled, reliable access**; a localhost URL on the M3 cannot be used directly from the Owner's computer. Use an explicitly approved, access-controlled deployment or supervised remote demonstration; do not silently expose services or transfer sensitive data to public hosting.
- The project pilot's real records/relationships are sensitive; use consented and minimised inputs. Fictional-case approval cannot represent legally or commercially effective real credit.
- This phase does **not** require full automated ML retraining, autonomous credit denial, automatic customer email, public rollout, general-person login infrastructure, or unrelated product verticals.
