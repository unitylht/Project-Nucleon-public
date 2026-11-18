# Engineering snapshot — provenance-aware

> **LATEST: 27 October 2026** — normal M3 Records/Lab updated to `2b2b786` and LibreChat `:3080` to rc3-test; scripted backend acceptance passed; **real 3080 Qwen browser acceptance is pending** and current Owner policy remains advisory v0. Read [ADA-STATUS-20261027.md](ADA-STATUS-20261027.md) for verification and detailed safety fixes. The older snapshot below is retained for historical commit lineage only, **not** active deployment status.

As of user's reports 2026-10-26. **Not independently verified against local M3 filesystem**; several commits are not pushed to GitHub.

## Boundaries
- Main M3 local Nucleon working checkout runs on :8630 (Lab/MCP) and :8631 (Records), loopback only, reported from `c69d521`. Database migrated in place and contains disposable fictional data. 33/33 MCP checks passed.
- Main LibreChat :3080 custom `librechat:nucleon-card-v0.8.8-rc2`, existing Staff read-only agent (10 read tools), financial cards auto-open and show backend completeness warnings. LM Studio local Qwen3.5-35B-A3B, reasoning on, sometimes slow/empty visible output.
- M6 public demo `https://nucleon.dracooz.top` separate; no recent changes deployed there.
- LibreChat test :3081 and scratch Records/Lab :18631/:18630 for Phase B. Test environment used fictional records. rc3-test image `librechat:nucleon-card-v0.8.8-rc3-test` is NOT on main :3080.
- POC accounts Staff/Owner; current shared codes do not identify individual people.

## Development lineage as reported
| Work | Local commit | Result | Deployment |
|---|---|---|---|
| Completeness/financial UI and rc2 frontend | `7750e8a`, `e87eade`, `f4a9b96`; LibreChat rc2 patch | Backend completeness, persistent MCP-UI cards, default visibility | M3 local |
| MCP write idempotency | `c69d521` | `_meta[nucleon.lab/idempotencyKey]` from capable clients; durable `record_ops` 3-state dedup, role/identity binding, recovery | M3 local :8630/:8631 |
| Controlled-actions design | `a12e121` | Nucleon page confirmation architecture | Docs in M3 branch |
| Phase A deterministic action backend | `1324a2e` | Frozen proposals, atomic Staff confirm to `awaiting_owner`, no model rewriting | Tested, NOT normal runtime |
| Phase B UI & isolated integration | Nucleon `f4febc2`; LibreChat `4783ee4` | Confirm page, proposal card, approved-link patch, request status; no auto approval | Isolated :3081 and :18631/:18630 only |

Reported Phase B results: Records 826, Lab 355, Chromium page 42/42, LibreChat wider client tests 1710, browser scenarios 6 passed (61/63 checks, two nonfunctional check limitations). Scope: human-confirmed request creation; owner decision unchanged. Do not interpret as delegated-autonomy validation.

## Important technical facts
- A generic LibreChat repeated MCP call has no stable operation ID; server idempotency is effective only if key is preserved. Phase A/B persistent `actionId` makes confirmation retries safe.
- The finite 90-day general record-op retention does not replace durable business uniqueness constraints.
- Staff human confirmation and Owner approval are distinct business operations. Phase B blocks Staff `actWithinAuthority` for confirmed requests, with `OWNER_REVIEW_REQUIRED` per report. Future delegated AI approvals require **new explicit policy capability**, not secretly disabling this guard.
- Existing AI Agent has Staff and Owner service paths; any final automatic decision must be authorised as a separate delegated act with policy evidence; service identity must not be treated as an arbitrary human Owner.
- Current completeness data distinguishes missing data, confirmed zero, recorded amounts and actual verified account balances. LLM summaries can omit caveats, so cards must surface backend caveats.
- Test-only instance exposed signing/encryption keys in its own output; rotate before reusing the environment for non-test purpose.

## Next engineering move
**Pause the previous Phase B 'human Owner only' security rollout prompt.** Product design conversation first. If deploying existing human-confirmation UI for separate evaluation, preserve role and auth constraints and keep owner-reviewed mode explicit; do not imply delegated approvals are implemented.

## Need reconciliation before code changes
Inspect actual local branches/worktrees, commits, service scripts, current deployment versions and existing docs; compare with this summary. No automatic push/merge/deploy. GitHub main as of this snapshot is older than current M3 local work.

### Local 27 October additions (from the code branch)

#### Deployment to the normal local M3 environment (27 Oct 2026, Claude Code, with the user's approval)

**What runs where.**
- **Nucleon:** the normal runtime (`~/Developer/nucleon-local`, Records :8631, Lab :8630) runs **`2b2b786`**: `~/Developer/Project-Nucleon` is detached at that commit.
- **Data:** a fresh fictional ADA demo database, policy version 0 (advisory).
- **LibreChat:** :3080 runs `librechat:nucleon-card-v0.8.8-rc3-test`.
- **Agent:** a new agent "Nucleon ADA Staff (Qwen)"; the existing agents are unchanged.

**Credentials:** rotated (person codes, service codes, and the local MCP token).

**Safety verification before deployment** (commit `2b2b786`).
- **Deposits:** they have explicit verification levels, and a customer's word never counts.
- **Exposure:** two bypasses were fixed: a deposit double-counted in the customer total, and a deposit reused for a second trial.
- **Overrides:** they are versioned and idempotent, and state that only the internal decision is reversed.
- **Tests:** Records 950 (Python 3.9 and 3.12), Lab 382, and page checks 59/59 and 42/42.

**Results.** The deterministic backend acceptance on the deployed stack passed. **The real Qwen browser acceptance on 3080 is still pending** (stopped by a local permission check), so the rollout is not declared successful.

**Backups and rollback:** see `docs/ADA-LOCAL-ROLLOUT-PLAN.md` (deployment record).

**M6 untouched.**

#### Status by category, 27 Oct 2026 (verified by Claude Code on the M3)
| Category | What |
|---|---|
| **Built** | Owner delegation policy (versioned, pause); assess/resolve/status tools; three-dimension evaluation; deposit verification levels; evidence requests to Staff; decision memory, comparables, Owner feedback and override, suggestions, live counts; decision/Key Facts card; Owner page `#/delegation`; evidence page |
| **Tested** | Records 955 (Python 3.9 and 3.12), Lab 384, LibreChat link validator 74/74, page checks 59/59 and 42/42; deterministic backend acceptance on the deployed stack |
| **Deployed** | Normal local M3: Nucleon `83b3efb` (Records :8631, Lab :8630); LibreChat :3080 on `librechat:nucleon-card-v0.8.8-rc4-tailnet`; agent "Nucleon ADA Staff (Qwen)" (step-by-step instructions, asks instead of guessing); Qwen at a 32,768-token context; private group access over Tailscale (`https://nucleon.tail492813.ts.net`); six member accounts; left in **advisory mode (v0)** with clean demo data |
| **Browser-verified** | Real Qwen + LibreChat on 3080, **17/17**: extension decided by the agent; Northside trial decided by the agent; Lakeside evidence then decided; Harbourline to the Owner plus the "just say yes" probe; override with history; pause and resume; financial card completeness; no outbound actions; no ledger payment from Staff evidence. A 4-minute demo video was recorded there. |
| **Deferred** | Autonomous declines; any outbound communication; full Owner Console and Decision Handling analytics; personal accounts in Nucleon (LibreChat has member accounts, Nucleon still has shared role codes); public internet access; ML training pipeline |
| **Future roadmap** | Shadow evaluation on real Owner-reviewed cases before widening limits; Owner-ratified thresholds; explicit permissions for external actions; broader decision domains |

**Known issues.**
- **Model wording:** with a 32,768-token context, Qwen finishes in 3 tool calls (replies take 26–32 s). At LM Studio's default 8,192 it loops; see [KNOWN-LIMITATIONS](../KNOWN-LIMITATIONS.md) L-001 and L-002. Its wording can be loose, and the card is authoritative.
- **Evidence page:** after Submit, the heading still says "Information needed" and the deposit line appears twice (cosmetic).
- **MCP check:** `tests/mcp_check.py` is pinned to the old sample data.

