# Nucleon project memory — start here

**Updated 30 October 2026.** This is the working entry point for team members, ChatGPT and Claude Code. See the [complete documentation index](../INDEX.md) and the repository [README](../../README.md).

## Current phase and priorities

- **Week 7 PoC presentation: completed.** The team received strong qualitative feedback on delegated autonomy despite a narrated-video Teams audio failure. [Feedback and recording timecodes](../team/WEEK07-PRESENTATION-FEEDBACK-20261030.md).
- **Week 8–10: Proof of Value and MVP readiness.** [Product lead's roadmap](../product/POV-ROADMAP-20261030.md), [Owner/Staff validation plan](../research/POV-VALIDATION-PLAN-20261030.md), [short team handover](../team/NEXT-STEPS-WEEK08-10.md).
- Primary design: the Owner sets explicit scoped authority; AI acts **only** inside server-enforced permissions and gathers evidence, while out-of-bound cases return to Owner. *Human in the loop* does not mean manually approving all cases.
- Main Week 7 improvement requests: demonstrate the **complete decision/repayment feedback loop** and produce an evidence-based **AI impact report**.
- Current priorities: real-user validation, a unified agent-first interface, preservation of backend controls/tests, clear case histories and truthful impact metrics. No speculative feature expansion before reliable core PoV.

## Latest engineering evidence — 27 October developer handover

[ADA status and limits](ADA-STATUS-20261027.md) reports the normal **local M3** Records/Lab at `da95220`, separate Qwen/LibreChat ADA agent, 17/17 real-browser acceptance checks on predecessor `2b2b786` and post-fix tested/recorded scenarios. Tests used **fictional data**; normal policy was returned to **advisory v0** and no real-world accuracy or commercial outcome was validated.

**Important:** This repository is documentation/shared memory, not the current M3 application code. The M3 changes were reported local/unpushed; M6 public services were not migrated to ADA. Do not convert handover statements into independent runtime verification. Re-read the latest code and services before implementation/deployment claims.

## Source and decision hierarchy

1. The latest explicit product lead/user decision for product direction; Owner's actual consent and business authority for **real** financial decisions.
2. Current verified source/runtime/tests for implementation facts, with environment, exact commit and date.
3. Sourced team/Owner evidence, with a clear distinction between first-hand interviews and teammate reports.
4. Proposals, historical demos and fictional test results, never promoted automatically into factual outcomes.

## Core documents in reading order

1. [Product charter](PRODUCT-CHARTER.md) — durable product goal.
2. [Decision authority](DECISION-AUTHORITY.md) — policy/evidence/risk approach, with **proposals clearly labelled**.
3. [27 Oct ADA status](ADA-STATUS-20261027.md) — implementation truth as reported.
4. [Decision register](DECISION-REGISTER.md) — accepted directions, supersessions and open items.
5. [Feature register](FEATURE-REGISTER.md) — feature scope and dated status; early rows are historic.
6. [Working agreement](WORKING-AGREEMENT.md) — maintenance and safe update rules.
7. [Design meeting (26 Oct)](MEETING-2026-10-26-DESIGN-FOLLOWUP.md), [UI references](UI-DESIGN-REFERENCES.md) and [ML evidence review](HOANG-ML-EVIDENCE-REVIEW.md).
8. [Historical project state](../PROJECT-STATE.md) — **16 Oct**, generated from [JSON](../project-state.json), not today's implementation snapshot.

## Non-negotiable integrity rules

- Permissions, financial numbers, status transitions, policy versioning and idempotency are enforced by backend code, never model prose.
- No general autonomous approval without current Owner policy; no autonomous denial or external customer action is implied by an internal decision.
- Separate fictional demonstration, developer-reported testing, deployment, real user testing and eventual repayment outcomes.
- Case retrieval/policy suggestions do not equal a retrained LLM, nor does a late payment prove a historical approved extension.
- Preserve M3/M6/local branch boundaries; no public exposure or migration without explicit authorisation.
- Preserve historical records; do not maintain the abandoned HTML brief or hand-edit generated Markdown.

### Local 27 October additions (from the code branch)

- **27 Oct 2026 (evening):** group members reach the M3 demo over a private Tailscale share, and agent/model limitations found in rehearsal are recorded in [KNOWN-LIMITATIONS](../KNOWN-LIMITATIONS.md) (L-001 ask instead of guessing, L-002 Qwen needs a 32,768-token context).
