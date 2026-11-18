# ADA implementation and deployment status — 27 October 2026

**Latest reported status (27 Oct): ADA is deployed on M3 normal services at commit `da95220`; 17/17 real Qwen+LibreChat browser acceptance checks passed against backend records on precursor `2b2b786`, followed by a re-check-loop fix and post-fix scenario recording/testing on deployed `da95220`. The local POC is now browser-validated with fictional data; not commercially validated or deployed publicly.** Last reviewed from developer/Claude handover and user's uploaded `Nucleon-Team-Handoff-Review.zip`; ChatGPT has **not independently run** tests or inspected M3 runtime. All test financial data and policy limits are fictional. Never portray as real NTK approvals or validated commercial decision quality.

## Environment matrix
| Scope | Status / versions | What it proves |
|---|---|---|
| ADA isolated | `feat/adaptive-decision-authority-20261026`, pre-rollout iterations through `7b12a7d`, later fix `2b2b786` | Isolated Qwen+LibreChat rounds and regression reported passing; scratch stack stopped |
| **Normal M3 Records/Lab** | `~/Developer/Project-Nucleon`, `2b2b786`, `127.0.0.1:8631` Records / `:8630` Lab running | Deterministic backend acceptance passed; does **not** alone prove the 3080 Agent flow |
| **Normal M3 LibreChat** | `127.0.0.1:3080`, `librechat:nucleon-card-v0.8.8-rc3-test`; agent **Nucleon ADA Staff (Qwen)** (6 tools) | App running and agent configured; **browser round blocked by permission prompt; still pending** |
| **Current Owner delegation** | Advisory/default **policy v0** | **No autonomous approval on normal M3 until Owner explicitly creates a delegated fictional policy** |
| M6 public site | Separate older version, untouched | **NOT ADA**; no public ADA service |
| Current team handover | M3 local `044d16a`, feature/memory local `77e5778` (reported); uploaded review ZIP | Documents describe deployment + browser acceptance pending; local commits not pushed |

Report of 27 Oct: normal LibreChat MongoDB and all **141** conversations preserved, other six agents unchanged, new credentials generated, service token rotated, and M6 not contacted. Source and deployment status are based on the developer's account, not new independent verification.

## Reported verification
- Records **950 tests**, Python 3.9 and 3.12; Lab **382**.
- Web delegation pages **59/59**; Phase B human-confirmation page **42/42**.
- Deployed-backend scripted acceptance: all scenarios passed, report `~/Developer/nucleon-local/tests/ada-acceptance/evidence/backend_acceptance.json`.
- Four real Qwen + LibreChat browser rounds **passed in the isolated test stack** (final round no retries), not on normal 3080.
- Older sample-specific MCP smoke gave **three known mismatches** after demo data/tool list changed; it is not a fresh proof of 3080 compatibility. Check smoke assumptions.
- Last blocking acceptance: first 3080 test-agent browser turn was stopped by Claude Code's **Modify Shared Resources** permission. No bypass attempted.
- Backups for controlled M3 rollout: `~/Developer/nucleon-local/backup/pre-ada-20261027-000207/`. Reversal instructions: `docs/ADA-LOCAL-ROLLOUT-PLAN.md` (M3 local, not on this remote branch).

## Features complete in code / reported tested
1. **Owner versioned policy**, pause/resume, advisory/delegated mode; human Owner person session alone writes; no policy = no automatic decision.
2. Three independent evaluations: **evidence sufficiency, business risk, demonstrated reliability**, no one magical LLM confidence.
3. **Authorized autonomous internal approvals**: new-customer bounded `trial_credit` and invoice `extension` (existing due-date code updates invoice); no per-request Staff or Owner approval click when delegated policy permits.
4. **Missing Staff evidence**: a scoped evidence action and Staff fact-confirmation page; re-evaluates immediately after submission. Implemented mainly for trial credit, NOT general outreach to customer or arbitrary tasks.
5. **Comparable cases** across customers labelled analogies; structured decision memory, Owner feedback/override, policy version and decision provenance. Reliability evaluation on **fictional cases**, not validated live Owner accuracy or an LLM retraining pipeline.
6. Minimal Owner delegation page, live case counts, minimal policy-change suggestions (Owner approval required), backend-grounded Key Facts/decision cards.
7. Separate Phase B human-confirmed submission path preserved.
8. **No autonomous denials**, **no outbound customer communications**, **no complete console**, **no general multi-person accounts**, **no verified real NTK outcomes**.

## Three important safety fixes in `2b2b786`
**Evidence provenance**: distinguishes ledger recorded payment; Staff checked bank; Staff checked document; customer-reported (never counts). Staff basis is retained, and Staff verification never silently creates a ledger receipt. Owner sets an exposure cap under which Staff-checked deposit may count; currently implemented for the bounded trial-credit pathway.

**Aggregate exposure**: fixed deposit counted twice against net exposure, and receipt reused for a second trial credit. Existing checks handle split requests, multiple invoices, concurrent 30-day rolling autonomous cap, retries and unknown amount != 0.

**Override**: stale case version rejected, double click idempotent across restart, provenance includes replaced policy version and Owner sign-in. Internal due-date reversal or trial-credit revocation **cannot undo a past external customer commitment**. No outbound action currently.

## Representative isolated test scenarios (fictional)
| Case | Reported isolated result | Caveat |
|---|---|---|
| Bayview +23 days | Agent changed invoice due from 18 Oct to 10 Nov under v1 | Effective only with an actively delegated current policy |
| Northside new customer | Recorded deposit; effective internal trial credit, AUD 600 at risk | Newness by itself doesn't force escalation |
| Lakeside no initial information | Agent requested Staff evidence; bank-checked deposit subsequently permitted AUD 450 net trial | Must preserve evidence level; Qwen timing/interaction more variable |
| Harbourline AUD 5,000 | Owner review, no automatic decision, even on 'just tell them yes' | Risk exposure in report AUD 4,000, outside fictional limit |
| Cityside/Riverside | Escalated due to unusually large / incomplete evidence | Not autonomously declined |
| Owner override/pause | Reversal with history; pause prevents automatic decision | No external action retracted |

## Known limits and next gate
- No full Owner Console; dashboard '60% auto / 25% gathering / 15% review' is an **illustrative UX**, not an observed business metric.
- Evidence gathering is trial-credit specific; customer uploads and general-purpose Staff outreach NOT implemented.
- Decision memory/analogies are a limited deterministic POC, not proven self-improvement on actual commercial results.
- No real individual accountability with shared Staff and Owner logins.
- Test access links use Mac-local `127.0.0.1`, not remotely reachable by teammates from other computers; M3 sleeps or travels.
- Model sometimes phrases order total as amount at risk; **backend card is authoritative**.
- Existing Phase B and ADA tools should stay in separate Qwen agents due to observed mixing.
- **Next:** authorised real 3080 Qwen browser round, confirm end-to-end latency distribution, correct team demo docs to use 3080/8631 rather than isolated 3081/18631. Verify script and system after any change.
- **Demo readiness:** conditionally deploy-tested; **not signed off** until real normal-browser acceptance. Disable/defer external exposure. Remain advisory except for bounded, supervised fictional rehearsal.
- Public M6 migration and internet publishing both explicitly **deferred by product lead** as of this discussion.

## Provenance
Source: Claude Code M3 deployment handover copied into user chat (27 Oct); developer-generated `Nucleon-Team-Handoff-Review.zip` uploaded to ChatGPT. Latest exact code state should be re-verified against the M3 worktree if new commits occur.


## 27 October late update — final local browser verification and 4-minute handoff
This section **supersedes the previous 'browser round pending' blocker elsewhere in this historical document**. The older stage is retained as a dated record, not the latest position.

- **Final real browser acceptance:** 17/17 checks on normal M3 port 3080 using Qwen + LibreChat, each confirmed in authoritative backend records, while code was `2b2b786`. Checks covered financial completeness card, Bayview due-date extension, Northside trial credit (recorded AUD 200 deposit, AUD 600 net at risk), Lakeside Staff bank-checked deposit (no ledger receipt created), Harbourline Owner escalation and pressure probe, Owner override/pause/resume, status retrieval and absence of outbound actions.
- **Post-acceptance fix:** `da95220` makes already-resolved re-assessment return stored status rather than a misleading new escalation preview; no repeated business decision. Reported Northside tool calls fell **12→7** and reply completion **55→33 seconds**. Records tests now **955** under Python 3.9/3.12, Lab **383**, page checks **59/59**; the complete 17-check round was not explicitly repeated on the newer commit, but subsequent recorded live Qwen scenarios ran with `da95220` and backend verification.
- **Current environment:** normal Nucleon Records/Lab `da95220`, LibreChat `rc3-test` on 3080, M3-only, using fictional data. Owner delegation returned to **advisory policy v0**, so no autonomous approval until Owner explicitly sets a fictional delegated policy.
- **Measured on code `da95220` during recording:** first visible ~0.5 s, authoritative card Northside **12.7 s**, Harbourline **12.2 s**, Lakeside first evidence-needed card **9.7 s**, Staff submit→effective internal decision **4.2 s**; Qwen text finish Northside 33.3 s, Harbourline 41.8 s, Lakeside 49.2 s. Read the backend card when it appears rather than waiting for prose.
- **Video deliverable:** true recording with accelerated waits clearly labelled, 3:58.842, 2560×1600/30fps H.264, Evan (Enhanced) synthetic narration and burned-in English captions plus subtitle track. Video is a rehearsed/edited **recording**, not a continuous real-time demo.
- **Known UI blemish:** after Lakeside evidence submission the heading still says 'Information needed' and deposit text is repeated; green backend status remains correct. No auto-decline, email, full Owner Console, real individual identities, verified commercial outcomes or 24h public hosting.
- **Handoff:** reviewed from user-uploaded `Nucleon-Demo-Handoff.zip`; original local docs/video/code are unpushed; remote GitHub docs here are an independent status record and NOT proof those local commits have been published. Team handouts contained stale isolated-only language to fix before distribution.
- **Operational next move:** watch video with audio for pronunciation/quality; correct residual team-document contradictions; rehearse with clean fictional data and pre-authenticated Staff/Owner browser profiles. Group review may use the recording; a live rehearsal should allow for model latency.
