# Nucleon — feature and value register

> **Dated status clarification (30 October 2026):** The 27 October developer handover reports local normal-M3 browser acceptance **17/17 on predecessor \`2b2b786\`**, followed by a tested/recorded post-fix \`da95220\` deployment; the earlier \`3080 browser acceptance pending\` wording has been superseded. Normal policy was returned to **advisory v0**, so no automatic decisions occur without an Owner saving a *fictional delegated policy*. These are developer-reported observations, not independently verified current services or real NTK credit accuracy. The early feature rows below retain their **26 October historical status**; use [27 Oct ADA status](ADA-STATUS-20261027.md) and [30 Oct roadmap](../product/POV-ROADMAP-20261030.md) for recent context.

Updated 2026-10-26. Maintained for product design, INFS3605 demonstrations, future pitch deck and promotional page. **Feature status != claimed implementation.**

## Product positioning
**A founder's second brain that turns accumulated business judgement into progressively delegated, evidence-based decisions.** It should reduce Owner workload today by handling research/triage and increasingly remove review work as validated decision memory and Owner-approved authority expand. Credit/payment exceptions are the first vertical, not the theoretical boundary of the architecture.

### Two time horizons (retain this wording for presentations)
- **Day-one value — Immediate assistance:** retrieves records, computes verified financial metrics, checks completeness, gathers additional evidence (including by asking Staff), assembles cases, explains choices and avoids repeated fact-finding even before AI has learned Owner-specific approval preferences.
- **Long-term value — Growing autonomy:** reuses similar cross-customer cases, captures Owner decisions/reasons and repayment outcomes, proposes policy improvements and performs **authorised internal decisions** without per-case Owner or Staff approval. External commitments/actions have distinct permissions.
Do not claim day-one automatic approval is already validated against real owner outcomes. Avoid promising an exact learning period.

## Feature catalogue
| ID | Capability | Product importance | Decision | Current engineering evidence |
|---|---|---|---|---|
| F01 | ChatGPT-like conversational front end with role-aware tools | Core UX | Confirmed direction | LibreChat rc2 on normal M3; rc3 isolated |
| F02 | Business/customer, invoice and payment tools | Core | Existing | Tested Nucleon Records + Lab; verify current services |
| F03 | Record completeness, not-confirmed vs confirmed zero, explicit caveats | Core trust | Existing | Backend financial completeness + persistent MCP-UI |
| F04 | **Cross-customer case transfer** to unfamiliar requests | Core differentiation | Confirmed product direction | NOT implemented/validated as a decision-memory system |
| F05 | **Evidence acquisition**: ask Staff for missing details; seek appropriate customer documents | Core agent action | Confirmed product direction | Full workflow not implemented |
| F06 | **Delegated AI credit decisions** within Owner-enforced rules without a Staff/Owner click per decision | Core differentiation | Confirmed product goal and authority model | NOT implemented; current Phase A/B is human-confirmed submission only |
| F07 | Configurable Owner risk/amount/exposure/new-customer limits | Core control | Confirmed direction; exact policy pending | NOT implemented |
| F08 | Suggested changes to Owner delegation policy based on evaluated cases/outcomes | Long-term differentiator | Meeting-supported proposal | NOT implemented |
| F09 | Decision memory: evidence, recommendations, Owner rationale, actual repayment outcomes | Core learning mechanism | Confirmed direction; operational form pending | Partial data/knowledge records exist; full loop NOT implemented |
| F10 | Advisory / conditional / delegated autonomy modes | Owner UX | Proposed interaction | NOT implemented; tiers/thresholds not adopted |
| F11 | Limited trial credit for new customers with bounded exposure, verified deposit and sufficient substitute evidence | Representative case | User-approved target automation level | NOT implemented; exact safeguards pending |
| F12 | Autonomous resolution / Owner time saved + case-quality metrics | Business value measurement | Confirmed measurement direction | Dashboard NOT implemented |
| F13 | Key Facts timeline: due date, as-of date, requested date, extension length | Useful retained visual | User-requested design reference | Historical UI screenshot only; rebuild in new UI |
| F14 | Decision Handling dashboard: autonomous / evidence gathering / Owner review | Owner console | User-requested future concept | Console NOT started; metrics shown are illustrative |
| F15 | Separate authority for outward commitments (emails, delivery, contracts) | Safety boundary | Confirmed concept | No autonomous outbound messaging in POC |
| F16 | Deterministic human-confirmed Staff request and idempotent action ID | Technical foundation | Existing code tested in isolation | Phase A/B local branches, not running on normal M3 |
| F17 | Inventory/forecasting and other founder decisions | Possible expansion | Outside current POC | Not implemented, do not claim general-prediction capability |
| F18 | Complete replacement of Staff work in this decision category | Product vision | Long-term aspiration | Explicitly out of POC scope |

## Feature claim labels for demos/marketing
- **Live / verified:** only when tested on the exact demo environment.
- **Built but not deployed:** code passed isolated testing, not available in normal demo.
- **Design / future direction:** not implemented, use conditional/future wording.
- **Simulation:** fictional data and outcomes, NEVER implied as verified on NTK cases.

## Primary differentiator for a short talk
Other workflows may simply transfer a phone approval into an online approval queue. Nucleon should **reuse owner knowledge across customers, gather missing evidence and make authorised low-exposure decisions**, escalating only cases that actually require Owner judgement, while making evidence, policies and actions inspectable.


## Late 27 Oct feature verification update
The M3 normal environment now runs backend `da95220` and LibreChat rc3-test; 17/17 real Qwen+LibreChat checks were run successfully on the immediate precursor `2b2b786` and post-fix scenarios were re-recorded/verified. Three flagship fictional scenarios are Northside delegated new-customer credit, Harbourline Owner escalation and Lakeside evidence acquisition from Staff. Bayview extension, Owner pause and override, Riverside completeness warning and status retrieval were verified in the 17/17 acceptance. Full Owner Console, outbound communication, automatic denials, generalized evidence collection, real commercial reliability and public/M6 deployment remain **not implemented**. Current Owner policy v0 is advisory until explicitly changed by a signed-in Owner.

### Local 27 October additions (from the code branch)

Evidence column as stated on the code branch (isolated-stack wording; compare with the dated 30 October clarification at the top of this file).

| ID | Capability | Product importance | Decision | Current engineering evidence |
|---|---|---|---|---|
| F01 | ChatGPT-like conversational front end with role-aware tools | Core UX | Confirmed direction | LibreChat 3080 on rc3-test since 27 Oct (normal local M3); separate ADA agent |
| F04 | **Cross-customer case transfer** to unfamiliar requests | Core differentiation | Confirmed product direction | Built & tested in isolation: comparable reviewed cases from other customers, labelled analogies (fictional memory) |
| F05 | **Evidence acquisition**: ask Staff for missing details; seek appropriate customer documents | Core agent action | Confirmed product direction | Built & tested in isolation: evidence request to Staff via Nucleon page (deposit, identity, trade reference); customer documents not implemented |
| F06 | **Delegated AI credit decisions** within Owner-enforced rules without a Staff/Owner click per decision | Core differentiation | Confirmed product goal and authority model | Built & tested in isolation (fictional policy/data): agent decisions take effect within an Owner policy; NOT deployed; no auto-decline |
| F07 | Configurable Owner risk/amount/exposure/new-customer limits | Core control | Confirmed direction; exact policy pending | Built & tested in isolation: Owner page #/delegation, versioned, pause; thresholds are fictional |
| F08 | Suggested changes to Owner delegation policy based on evaluated cases/outcomes | Long-term differentiator | Meeting-supported proposal | Built (minimal): deterministic suggestions only; Owner must save a new version |
| F09 | Decision memory: evidence, recommendations, Owner rationale, actual repayment outcomes | Core learning mechanism | Confirmed direction; operational form pending | Built (minimal): decision_cases memory, Owner feedback/override, outcome from records; fictional seeds |
| F10 | Advisory / conditional / delegated autonomy modes | Owner UX | Proposed interaction | Built (two modes): advisory / delegated (+ pause); three-tier wording not adopted |
| F11 | Limited trial credit for new customers with bounded exposure, verified deposit and sufficient substitute evidence | Representative case | User-approved target automation level | Built & tested in isolation: limited trial credit with verified deposit; fictional limits |
| F12 | Autonomous resolution / Owner time saved + case-quality metrics | Business value measurement | Confirmed measurement direction | Minimal live counts only on the Owner page; no dashboard |
| F13 | Key Facts timeline: due date, as-of date, requested date, extension length | Useful retained visual | User-requested design reference | Built: Key Facts rows + marker bar in the MCP-UI decision card (backend dates) |
| F15 | Separate authority for outward commitments (emails, delivery, contracts) | Safety boundary | Confirmed concept | Enforced: no outbound action exists; every result says Nucleon sent nothing |
| F16 | Deterministic human-confirmed Staff request and idempotent action ID | Technical foundation | Existing code tested in isolation | Code present on normal local M3 since 27 Oct (2b2b786); prepareRequest/actionStatus off by default there |
