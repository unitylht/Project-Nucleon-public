# Proof of Value (PoV) — owner and staff validation protocol

**Draft test plan, 30 October 2026.** No tests, results, agreements or numerical targets are claimed here. Week 8 asks teams to return to users and assess meaningful business value, not just a running PoC.

## Questions to answer

1. Would the Owner delegate **any** defined class of internal credit decision to this system? What factual checks and limits would be required?
2. Can Staff provide missing evidence and act on a backend-grounded decision without taking over approval responsibility or calling the Owner again?
3. Does the workflow remove measurable **net** work, compared with the business's current process?
4. Does the Owner understand what the AI may act on, what was actually decided, what remains pending, and how to override/pause safely?
5. Can we link subsequent real repayment outcomes to a decision without inventing historical approval labels or claiming automatic ML training?

## Representative tasks (consented/synthetic first)

| Case | User task | Observation |
| --- | --- | --- |
| Northside-like new customer | Staff requests small trial credit with a documented deposit under **fictional Owner test policy** | Agent gathers evidence; backend autonomously applies permitted **internal** approval; no customer message |
| Harbourline-like high exposure | Staff requests credit exceeding one or more limits | No AI approval; Owner review with clear failed bounds |
| Lakeside-like missing data | Agent requests Staff verification of deposit/identity | Record basis for Staff check without converting it to a ledger receipt; re-evaluate |
| Owner control | Owner examines, pauses, adjusts or overrides an internal decision with reason | Policy version/actor/event history remain visible; external commitments are not silently reversed |
| Lifecycle explanation | Owner looks for repayment outcome and past decisions | Pending is distinct from on-time, late, missing data or actual bad debt |

Use real cases only with explicit permission, appropriate handling of private information and a clear boundary between simulation and real commercial authorisation.

## Minimum evidence capture

For **each participant/session**, with consent:
- User role and relevant current manual workflow (no unnecessary identifying information).
- Test date, environment/version, policy mode, scenario and task prompt.
- Start/end timestamps, any interruptions, clicks/prompts and Owner/Staff follow-up actions.
- Success/failure, incomplete actions, wrong/ambiguous claims, override, escalation, source of evidence.
- Screen/voice recordings only with permission; de-identify before sharing.
- Direct feedback: what was trusted, confusing, not useful, or unacceptable, and why.

### Net-time measurement (do not invent)

Compare an equivalent real/manual baseline and the full system-assisted process. Count **setup, data entry, checking, corrections and maintenance**, not merely model response time. Explicitly report sample size and assumptions.

`net owner time saved = comparable manual owner time − (assisted owner time + allocated onboarding/review/maintenance time)`

For session metrics, distinguish:
- Autonomous decisions / **eligible** cases; not all requests.
- Owner escalations / total requests.
- Overrides / decisions exposed to Owner.
- Case handling duration / comparable manual duration.
- Verified later repayment outcome / outcome-eligible matured cases.
- Time-to-backend-card versus time until the model finishes its prose.

A small sample can demonstrate usability but cannot establish reliable real default risk or AI model accuracy.

## Reporting format

1. Method and source: who, what, when, environment, task, consent.
2. Raw observations: logs, timestamps, quotes, confusion, task completion.
3. Comparison: manual versus assisted net workload with assumptions.
4. What is **validated**, **partially supported**, **not validated** or **disproved**.
5. Product changes motivated by evidence; avoid claiming a fix is deployed until retested.
6. Known limitations, notably the lack of long-run repayment results in a two-week course window.

## Access/safety prerequisites

- Current M3 localhost service is not a public endpoint. Agree a scheduled supervised session or separately authorised authenticated remote access; do not expose a private service to the internet by default.
- The M6 public instance is a separate version and not the ADA M3 POC according to the 27 Oct handover.
- Default policy v0 advisory until a signed-in Owner deliberately enables *fictional/demo* delegated rules; no real automatic credit should be granted during testing.
- Do not write personal customer names, ABNs, credentials, bank evidence or proprietary transactions to this repository.
