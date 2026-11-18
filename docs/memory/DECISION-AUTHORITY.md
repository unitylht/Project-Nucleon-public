# Adaptive Decision Authority — design discussion
Status: principles **accepted by the user** (see the confirmed refinement below).
- **Implementation:** a first POC slice is **built and tested in isolation** (2026-10-26, see `docs/ADAPTIVE-DECISION-AUTHORITY.md`).
- **Still open:** the real thresholds, an Owner auto-decline, and validation claims. **No real Owner has authorised a policy.**

## Core evaluation: three separate axes
1. **Evidence sufficiency:** what is actually known about this customer/request, freshness, verified invoice/payment coverage, contradictory data, opening balances and reliable supporting documents. Unknown != zero.
2. **Business risk:** amount, days, total outstanding exposure, existing overdue amounts, relationship and contractual restrictions; risk may be high even with complete data.
3. **Demonstrated AI reliability:** agreement on comparable Owner-reviewed cases, validation size, business outcome follow-up, shifts/drift and uncertainty; LLM self-rated confidence is not validated accuracy.

Do not turn these into a single unexplained scalar.

## Candidate handling outcomes
- **Auto Approve:** only when explicit Owner policy allows and backend verifies relevant bounds and prerequisites.
- **Recommend & Escalate:** informed recommendation but outside policy, material uncertainty or high consequence.
- **Request More Information:** let agent request achievable evidence before involving Owner.
- **Policy-Based Hold:** block conflicting/non-negotiable cases, or escalate for an explicit exception. Do not confuse hold with autonomous permanent denial.

## Candidate Owner UX (illustrative, NOT decided)
- Autonomy choice: Advisory / Balanced (conditional) / Expanded delegated.
- Maximum automatic **exposure**, ideally account-level aggregate not just single invoice.
- New customer policy: always Owner-review, suggestions first, or explicitly enabled limited trial credit.
Advanced restrictions for days, overdue conditions, completeness and conflicting data; keep Owner-facing controls comprehensible. Default numerical examples such as AUD 300 or AUD 1,000 are **illustrative**, never real thresholds.

## New customer principle under discussion
Neither blindly approve unfamiliar customers nor always escalate. Use available external or supplied evidence, analogies clearly labelled as analogies, smaller exposure and shorter duration, request extra evidence first. Proposed 'Limited Trial Credit' requires explicit Owner opt-in, strict bounds and verified conditions. Team and Owner have NOT ratified it.

## Performance measurement
- **Owner agreement** = agreement on reviewed comparable cases; not proof of commercial success.
- **Business outcome** = repayment/late/loss for observable approved cases, with time horizons and selection bias noted.
- **Eligible automation coverage** = share of requests falling inside approved policy; not 'accuracy'.
- Require sample size, context and performance distribution; small/fictional sample accuracy must not be presented as validated real-world performance.
- Separate training/feedback cases from held-out evaluation; avoid presenting simulated decisions or inferred approvals as ground truth.

## Intended workflow (future)
Staff/customer trigger -> agent gathers records and asks for missing info -> model proposes recommendation/evidence -> backend checks current verified facts, policy version, role, risk/exposure -> execute only when Owner-delegated scope is satisfied; otherwise defer/hold -> record outcome and later feedback -> Owner may narrow/pause/expand policy. Execution and idempotency must be enforced by code, not free-text model replies.

## Existing Phase A/B and what it does NOT establish
Phase A/B has tested deterministic **human confirmation of request creation** followed by Owner review. It does NOT implement delegated auto-approval, evaluation of AI accuracy, Owner policy controls, or a production-ready approval gateway. Do not globally hard-code 'Owner person must approve everything forever'. Conversely, do not use an Owner service token to bypass undeveloped policy enforcement.

## Design questions for team
1. Which request types are actually eligible for delegated decision (extension, limit increase, first credit)?
2. How much maximum outstanding exposure per customer, across all requests, and over what time?
3. What is a tolerable false approval versus Owner time saved?
4. What records are mandatory versus optional; what if payment/invoice coverage is unconfirmed?
5. What new-customer trial evidence is acceptable, and is auto-decline permitted?
6. How do we assess the agent before allowing autonomy; sample size, independent cases and Owner correction path?
7. What is reversible, and what must trigger immediate policy suspension?
No Claude implementation until product decisions are consciously accepted.

## Confirmed refinement — 26 October follow-up
The user (acting as product design lead) explicitly confirms **delegated AI decisions can become binding immediately** within Owner-authorised bounds, without routine Staff/Owner clicks. This concerns **internal credit decisions**, not automatic emailing, fulfilment or contract changes. Staff can supply evidence, supervise and perform external operations separately. Existing prototype's Owner-review guard remains a safe temporary default for non-delegated workflows, not the intended final approval model.

The user also confirms cross-customer reasoning, actively requesting evidence from Staff, and using bounded new-customer trial credit with verifiable deposit as a representative target. The team meeting discussed a progressive delegated policy cap and suggested increases based on comparable cases; **actual amount, risk and confidence thresholds remain open**.

**Anti-over-escalation requirement:** design must measure autonomous resolution, Owner review count, Owner time saved and business risk together. Do not simply stack blanket requirements until all unfamiliar customers are escalated. Use risk-proportionate evidence and information gathering. The goal is to maximise useful autonomy **subject to** explicit risk/authority limits; never auto-relax hard constraints.

Previous wording 'No Claude implementation until product decisions are consciously accepted' now means: the **principles above are accepted**, and the user intends a substantial prototype refactor before rehearsal. Undecided numeric policy limits, human approval exceptions, evidence rules and validation claims must remain explicit assumptions or fictional POC demonstrations; avoid presenting them as verified rules or real business deployment.
