# Nucleon backend policy enforcement — explainer for presenters
Updated 27 October 2026. Based on user-uploaded `ADAPTIVE-DECISION-AUTHORITY.md` describing the built first vertical slice; exact current implementation should still be checked against `2b2b786` before claiming a precise runtime rule.

## One-sentence explanation (15 seconds)
**Qwen proposes a decision, but a separate Python backend independently checks the facts, the Owner's current policy, credit exposure and reliability constraints before anything can change in the business records.** If a check fails, the Agent cannot grant itself permission.

## Compact architecture
LibreChat (chat) → Qwen (reasoning) → MCP `assessDecision / resolveDecision / decisionStatus` → Records `prototype/delegation.py` policy evaluation → transactional business record and decision history (SQLite).

## What the code checks
1. **Evidence sufficiency.** Known amounts and dates, invoice completeness and confirmation coverage, verified deposit/identity/trade reference when relevant, contradiction detection. New customer with no personal history is not automatically negative.
2. **Risk and hard authority.** Policy version and pause, whether extension/trial credit class enabled, single-decision **net exposure**, total customer's exposure, active autonomous 30-day exposure, maximum days/terms, unusual size and customer-specific holds. Deposit cannot be double counted or reused for another trial.
3. **Demonstrated reliability.** Comparable reviewed cases and category backtesting, with provenance and sample size. Current model track record for the POC uses **fictional evaluation cases**; no validated real NTK accuracy.
4. **Decision application.** If within policy and model recommends approval, backend atomically records internal approval, actor, policy version, evidence, data state and the business effect. Otherwise request Staff evidence, recommend Owner review or hold. No autonomous denial and no outbound email.

## Worked *fictional* trial example
- Northside order AUD 800, **eligible recorded deposit** AUD 200 → **new credit exposure AUD 600**.
- Hypothetical v1: maximum single decision AUD 1,000; new trial AUD 600; customer total AUD 1,500; checks on term days, deposit ratio, running totals and factual provenance still apply.
- Because the order is AUD 800, it is inaccurate to describe 'AUD 800 risk' or 'AUD 800 granted'; the system should communicate **AUD 600 net exposure**.
- **Do not use this as a general risk calculation**: actual available customer exposure may include other outstanding obligations and adjustments. The backend assesses total, not merely this new transaction.

## Key separation
- **Agent reasoning** explains facts and chooses recommendations; it is not permission.
- **Owner delegation** determines permitted classes/limits, cannot be changed by the model.
- **Backend enforcement** evaluates against the current policy and known authoritative records at execution time.
- **Internal decision** can be valid immediately with the correct delegation.
- **External communication/fulfilment** remains a separate, unautomated responsibility in the POC.

## Presenter Q&A if pressed
**Could Staff simply type 'deposit received' and force approval?** No: a customer statement does not count; Staff checked evidence is a distinct level with a separate Owner-set cap, and no Staff claim is automatically turned into a recorded ledger payment. This remains a role-based POC with shared identities.

**What if someone splits a request?** The backend checks customer aggregate exposure, concurrent requests, deposit reuse and recent autonomous approvals, not only the amount in an individual prompt. Two bypasses were fixed in `2b2b786`.

**Can the agent increase its own limit?** No. It can recommend a new limit; a signed-in human Owner must save a new policy version. Policy pause disables automatic decisions.

**What if Qwen says 'approved' when checks fail?** The stored backend case and authoritative status card determine the real result; Qwen wording alone does not change invoices.

**Is there actual financial-risk prediction accuracy?** Not established; synthetic Owner cases and fake outcomes support demonstration/testing only.

**Why use Python code rules rather than model confidence?** Deterministic logic is testable, auditable, repeatable and prevents unbounded writes. The model contributes flexible case interpretation, not uncontrolled authorisation.
