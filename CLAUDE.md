# Claude Code / AI session entry point

Start at [AGENTS.md](AGENTS.md), then [docs/INDEX.md](docs/INDEX.md) and [docs/memory/START-HERE.md](docs/memory/START-HERE.md).

**Phase:** Week 7 PoC demonstrated; Week 8–10 are PoV + MVP consolidation. Read [30 Oct roadmap](docs/product/POV-ROADMAP-20261030.md), [user test protocol](docs/research/POV-VALIDATION-PLAN-20261030.md) and [presentation feedback](docs/team/WEEK07-PRESENTATION-FEEDBACK-20261030.md) before making product changes.

**Keep source boundaries straight:** GitHub here contains the shared *documentation* record. Recent ADA commits and 4-minute demo assets were reported on the developer's local M3 worktree, not pushed here; M6 public demo is a separate old environment. Read [27 Oct status](docs/memory/ADA-STATUS-20261027.md), then inspect current local sources and deployments rather than inferring them from these Markdown files.

**Product rule:** Owner-controlled, versioned backend policy may delegate scoped **internal** credit decisions. Agent cannot create its own authority or send external commitments. A persistent case/outcome log is not model-weight retraining. Preserve verified regression scenarios as you unify chat, business records and Owner controls.

**Documentation rule:** `docs/PROJECT-STATE.md` is generated from the still-old 16 Oct `docs/project-state.json`. Do not hand-edit generated Markdown or restart archived HTML brief maintenance. Update the decision register for substantive product choices, state evidence quality clearly, and avoid overwriting other branches.

## Decision checklist for every product recommendation (D13, 30 Oct 2026)

Before recommending a product or policy behaviour, answer these four questions in writing, in the same message as the recommendation:

1. Does it **reduce or add** the Owner's net work (setup, review and maintenance included)?
2. Does it **advance growing autonomy**, or add a permanent human gate? A "safe default" that routes more cases to the Owner must be called out as such: "this is the conservative default and works against growing autonomy".
3. Is it **deterministic and verifiable** by backend code and tests, independent of model prose?
4. Is it **reversible and Owner-configurable**? Restrictive behaviour is an Owner setting with a default, never a hard-coded rule.

Always show the **autonomy-maximising alternative** next to the recommendation, even when not recommending it. Record accepted decisions in [the decision register](docs/memory/DECISION-REGISTER.md) with the principle served and the principle traded. At each milestone run a **vision audit**: walk the three standard journeys (Northside trial credit, Harbourline escalation, Lakeside evidence) and count where the Owner still has to click.

Why: on 30 Oct the reliability-gate recommendation was framed as a risk parameter and contradicted the anti-over-escalation requirement in [DECISION-AUTHORITY.md](docs/memory/DECISION-AUTHORITY.md); the product lead caught it. See [the PoV implementation plan](docs/product/POV-IMPLEMENTATION-PLAN-20261030.md).

**Code is on `main` since 30 Oct 2026.** Read [the engineering inventory](docs/ENGINEERING-INVENTORY-20261030.md) before investigating the code; do not re-derive what it records.
