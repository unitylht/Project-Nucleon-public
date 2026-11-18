# Nucleon repository working rules

**Read first:** [README](README.md) → [docs/INDEX.md](docs/INDEX.md) → [docs/memory/START-HERE.md](docs/memory/START-HERE.md). For implementation read [Product charter](docs/memory/PRODUCT-CHARTER.md), [Decision authority](docs/memory/DECISION-AUTHORITY.md), [Decision register](docs/memory/DECISION-REGISTER.md), [27 Oct engineering status](docs/memory/ADA-STATUS-20261027.md), and [PoV roadmap](docs/product/POV-ROADMAP-20261030.md).

## Current purpose (30 October 2026)

Week 7 PoC has been presented. Weeks 8–10 focus on **real Owner/Staff proof of value, a coherent agent-first MVP, verifiable decision/outcome history and honest impact measurement**. The Week 7 transcript and feedback are [recorded here](docs/team/WEEK07-PRESENTATION-FEEDBACK-20261030.md). Product lead's development direction is in the roadmap; its tasks are *plans*, not implementation claims or Owner-authorised real credit limits.

## Engineering and authority rules

- Keep the distinction between **confirmed direction / proposal / built locally / tested / deployed / commercial outcome validated**. No inference of readiness from a narrated class video.
- The M3 application source is **not** this GitHub documentation branch. The 27 Oct handover reports normal M3 local ADA at `da95220` (post-fix) and 17/17 browser checks on precursor `2b2b786` with fictional data. Recheck current code/runtime; M6 public demo is separate, not ADA.
- Owner delegates **classes of internal decisions**, not every click. Agent reasons and uses tools; backend authorises and records business effects. Without active Owner scope, do not approve. Staff can confirm evidence but must not be forced to approve each case as a substitute.
- Keep evidence sufficiency, business risk/exposure and independently demonstrated reliability distinct. A model confidence claim or similar case cannot grant permission.
- Never convert Staff-observed deposits to recorded ledger payments; unknown is not zero; historical late payments do not establish approved extension labels.
- No unilateral changes to finance permissions, external sending/fulfilment, live data access, public hosting or M6 deployment. Financial calculations, audit, permissions, idempotency and policy checks remain deterministic and testable.
- Do not disclose real customer records, secrets, private interviews or contact details in GitHub. Fictional numbers and tests must be labelled.
- Changes to the UI must preserve existing regression coverage and authoritative backend cards; resolve duplicate/ambiguous status wording without weakening policy enforcement.

## Updating the shared record

- Put observed feedback in dated, source-attributed notes and validated decisions in [Decision register](docs/memory/DECISION-REGISTER.md). Never silently promote an AI proposal into a team or Owner decision.
- `docs/project-state.json` owns generated `docs/PROJECT-STATE.md`; both are **16 Oct historical** until reconciled. For a substantive regeneration change JSON and run `python3 tools/build_brief.py`; do not hand-edit Markdown.
- Keep `meeting-brief.html` and `tools/brief-template.html` untouched: HTML maintenance stopped on 16 Oct.
- Respect concurrent work and unpublished M3 commits. Prefer reviewable documentation branches and PRs; do not overwrite, force-push or merge surprises.
