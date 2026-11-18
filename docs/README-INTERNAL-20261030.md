# Project Nucleon

**INFS3605 · Stream 1: Founder's Second Brain · CreditEase**  
**Project phase (30 October 2026):** Week 7 proof of concept presented; Week 8–10 focus is **proof of value (PoV), product consolidation and final MVP readiness**.

Nucleon aims to remove repetitive credit-exception decisions from a small B2B business owner's workload. A conversational agent retrieves evidence, asks for missing facts and makes **internal** decisions only within a versioned, server-enforced Owner delegation policy. Exceptions go to the Owner. A decision is not permission to send a customer message or fulfil an order.

## Start with the current record

| Purpose | Document |
| --- | --- |
| **Documentation map and current-vs-historical status** | [Documentation index](docs/INDEX.md) |
| **Week 7 presentation, Microsoft/teaching feedback and audio incident** | [Week 7 feedback](docs/team/WEEK07-PRESENTATION-FEEDBACK-20261030.md) |
| **Product lead's next development direction** | [PoV development roadmap](docs/product/POV-ROADMAP-20261030.md) |
| **Real-user PoV testing and measurement** | [PoV validation plan](docs/research/POV-VALIDATION-PLAN-20261030.md) |
| **Short team handover** | [Week 8–10 next steps](docs/team/NEXT-STEPS-WEEK08-10.md) |
| Product principles, authority and decisions | [Project memory](docs/memory/START-HERE.md) |
| **Latest documented engineering evidence** | [27 October M3 ADA status](docs/memory/ADA-STATUS-20261027.md) |

## Implementation truth and important limits

The latest **documented developer handover** (27 October) reports local M3 Nucleon Records/Lab at `da95220`, a separate Qwen/LibreChat agent, and **17/17** normal-browser acceptance checks on precursor `2b2b786`; the follow-up fix was tested/recorded on `da95220`. Tests use **fictional business data**. The normal local Owner policy was left in **advisory mode (v0)**. These are developer-reported results, not independent verification of today's live services.

**This GitHub repository is the shared project/documentation record, not the authoritative current M3 application source tree.** The M3 app commits and handoff assets were reported as *local and unpushed*; the separate public M6 environment was not upgraded to ADA. Do not mistake documentation commits or class video playback for a public production deployment or validated real credit accuracy.

## How to maintain this repository

- Read [AGENTS.md](AGENTS.md) and [docs/INDEX.md](docs/INDEX.md) before technical or documentary work. Product decisions belong in [the decision register](docs/memory/DECISION-REGISTER.md) with provenance and status.
- Record dated feedback and test evidence separately from proposals, implementation assertions and independently verified outcomes.
- The older `docs/project-state.json` generates `docs/PROJECT-STATE.md` via `python3 tools/build_brief.py`. Both still describe the **16 October historical snapshot** and are **not** the current project summary. Reconcile the JSON before regenerating; never hand-edit generated Markdown.
- `meeting-brief.html` and `tools/brief-template.html` are historical snapshots. HTML brief maintenance was stopped on 16 October; do not restart it by default.
- Keep secrets, raw customer ledgers, private interview transcripts and identifying data outside commits. Demonstration cases must be identified as fictional.
- No force-push, surprise production deployments, M6 migration or public exposure. Verify local worktrees and live state before making technical claims.

## Application code

The application code (Records `prototype/`, Lab/MCP `lab/`, deployment and check scripts `deploy/`, LibreChat patches and agent scripts `integrations/librechat/`, local M3 tools `deploy/m3-local/`) is merged into `main` as of 30 October 2026. Tag `poc-week7` marks the Week 7 code (`83b3efb`). Code facts: [engineering inventory](docs/ENGINEERING-INVENTORY-20261030.md). Plan: [PoV implementation plan](docs/product/POV-IMPLEMENTATION-PLAN-20261030.md). The paragraph above saying this repository is "not the authoritative current M3 application source tree" is historical from the PR #4 documentation round; from this merge on, `main` is the source tree.
