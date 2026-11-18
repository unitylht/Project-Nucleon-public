# Nucleon — product charter
Status: durable user-confirmed direction, *not* full team/Owner ratification. Updated 2026-10-26.

## Product
INFS3605 Stream 1: Founder's Second Brain. Initial pilot: small B2B manufacturer/gelato supplier with credit requests and overdue-payment exceptions. Owner currently supplies tacit judgement and handles escalations.

## Problem and desired outcome
Avoid replacing owner decisions with merely another portal, dashboard or per-request approval queue. An agent should retrieve facts, clarify gaps, recommend, act through tools within authorised limits and escalate genuine exceptions. Reduce **net Owner time**, including setup, review and maintenance, while keeping decisions explainable and reviewable.

## Confirmed guiding principles
- Owner determines **what discretion to delegate**, but need not personally perform every credit decision indefinitely.
- Model-written confidence is not authority. A server-enforced Owner delegation policy decides what the agent can execute. Do not conflate inference, financial record verification, permission or business outcome.
- POC user-facing roles: Staff and Owner. Separate service identity or provenance is a technical security distinction, **not** a request for a many-person account system.
- Local-first POC; published M6 demo is separate from Mac M3 local development. Never deploy to M6 without explicit instruction.
- Existing manual confirmation and Owner review remain useful as default/fallback or early rollout, not mandatory forever.
- Record the evidence, business inputs, model recommendation, policy version, actor (human/agent), action, Owner corrections and later outcomes. Do not invent historical approvals from late-payment proxies.

## What 'learning' means initially
Decision memory / retrieval of similar reviewed cases, explicit Owner preferences, policy versioning and evaluation. Continuous model fine-tuning is NOT required for POC. A one-off Owner exception is not automatically a reusable policy.

## Success metrics to validate
Net Owner workload removed (subtract added friction), appropriate automation coverage, agreement with Owner decisions, business repayment outcomes, false approval cost, data completeness, override rate and traceability. No threshold adopted, no accuracy substantiated by NTK data.

## Unresolved product choices
Specific authority tiers and policy limits; limited trial credit for new customers; risk category design; sufficient evidence and sample size; when to request more information vs defer; acceptable false approval cost; whether auto-denial is ever authorised; pilot proof and rollout gates.

## User-confirmed operating model — 26 October follow-up
- **Within explicit Owner delegation**, an AI internal credit decision may take effect directly; Staff does not approve it again as a formality. Staff may gather missing information, supervise exceptions, or complete separate outbound actions.
- Staff reluctance to assume credit-approval responsibility is a primary real-world bottleneck; shifting the approval click from Owner to Staff is not the product objective.
- Agent should seek evidence from Staff as well as the customer, and draw from comparable reviewed cases across customers rather than needing several Owner approvals **per new customer**.
- The long-term aspiration is to remove more of the Staff's repetitive work, but this is not a POC delivery commitment.
- User considers the concrete case of small new-customer exposure, verified deposit and explicit Owner trial delegation an acceptable **target automation example**; eligibility thresholds still require design.
- Value proposition uses two horizons: **Day-one value — Immediate assistance** and **Long-term value — Growing autonomy**. Preserve for presentation and marketing, without implying validated automatic approvals exist today.
- For feature/marketing inventory see [FEATURE-REGISTER.md](FEATURE-REGISTER.md).
