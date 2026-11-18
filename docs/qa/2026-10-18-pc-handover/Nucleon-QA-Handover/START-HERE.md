# Nucleon QA handover — start here

A self-contained package from one guided test run of **Project Nucleon** on a Windows PC. It is written for the
developer, who has no access to that PC or to the tester's session. Everything needed to reproduce the findings
is in this folder. Nothing here needs to be executed.

## What was tested

| | |
|---|---|
| Site | https://nucleon.dracooz.top (shared practice instance) |
| Guide | *Nucleon Team Testing Guide*, revision 2, tasks T1–T7 ([test-pack/original/](test-pack/original/)) |
| Application revision | **Unknown.** The guide says "practice release a9ce30d"; this was **not** verified against the running site. |
| Actual test date | Sunday **2026-10-18**, 04:34–≈04:52 UTC (15:34–≈15:52 AEDT) |
| Simulated business date | **Fri 16 Oct 2026**, the app's fixed "today" (Amounts in AUD). App timestamps such as "Decided 18 Oct" use the real clock. |
| Tester tag | **CL1018T** (fresh tag; the Hanting folder with HL1815A replaced) |
| Tester | An AI agent (Claude Code) driving the browser via Playwright, in a visible window. Timings are not comparable with human testers. |
| Browser | Playwright-controlled Chromium, build 155.0.8059.80, language zh-CN. The build was read at packaging time and assumed unchanged. |
| Viewports | Desktop 3840×1958 (inferred from screenshots, device pixel ratio 1); narrow window 390×844 (375 px document width); 1400×900 for one final check (no screenshots). **No real phone.** |
| Roles | Staff, Owner, and Operator (read-only; no console action) |

All T1–T7 checks of business behaviour passed:
- customer disambiguation
- repeat-import idempotency
- rejection of invalid rows
- same-customer payment allocation
- exact 400.00 / 6 days / 35 days calculations
- completeness invalidation after a late entry
- correction versioning
- isolated revert

## Main findings
1. **B1 (High, reproduced 2/2): Sign out ends only the selected role.** After unlocking Staff and Owner in one
   browser, signing out from Staff leaves the browser in **Owner** mode with no code prompt. In the mirror case,
   signing out from Owner leaves Staff.
2. **B3 (unverified risk):** the Revert form for an import batch with dependants shows no dependency warning
   before submit. It was **not submitted**, so the server's behaviour is unknown.
3. **B2 (policy question):** Staff can save opening balances, and nothing shows who entered them. It is unknown
   whether this is intended.
4. **G1/G2:** the guide refers to an import "completeness choice" that doesn't exist. It also asks for amounts and dates to be
   checked in a preview that doesn't show them.
5. **U1:** the invoice customer picker resets to the first sample customer after every save, which invites
   wrong-customer entries.

There are 26 findings in all (B1–B9, U1–U12, G1–G5); see [FINDINGS.csv](FINDINGS.csv).

## Package structure

| Path | What it is |
|---|---|
| [START-HERE.md](START-HERE.md) | This file |
| [TEST-REPORT.md](TEST-REPORT.md) | Full report: environment, results per task (including passes), every finding with role, steps, expected, actual, suspected cause, impact, confidence and evidence; limitations; corrections to the chat report |
| [FINDINGS.csv](FINDINGS.csv) | One row per finding (UTF-8) |
| [TEST-DATA-AND-STATE.md](TEST-DATA-AND-STATE.md) | Every record created, changed or reverted (ids, case links); what belongs to others; browser sign-in state |
| [evidence/EVIDENCE-INDEX.md](evidence/EVIDENCE-INDEX.md) | Index of all evidence and of missing evidence |
| [evidence/screenshots/](evidence/screenshots/) | 16 original screenshots (E01–E16), renamed descriptively |
| [evidence/session-output-excerpts.md](evidence/session-output-excerpts.md) | Verbatim, redacted outputs of test scripts (X01–X28), the main evidence for findings without screenshots |
| [evidence/automation-snapshots/](evidence/automation-snapshots/) | 44 accessibility snapshots saved by the automation tool during the session |
| [evidence/browser-console/](evidence/browser-console/) | Browser console log from T7 onwards (B7 errors, expected 422) |
| [evidence/derived/](evidence/derived/) | One packaging-time contact sheet of E12 (not a new capture) |
| [test-pack/](test-pack/) | Original pack (ZIP + extracted, unchanged), the CSVs and manual values actually used, and tester-authored guide corrections (kept separate) |
| `MANIFEST.sha256` | SHA-256 of every other file. Check with `shasum -a 256 -c MANIFEST.sha256` from this folder. |

Suggested order: this file → TEST-REPORT.md §5–§6 → EVIDENCE-INDEX.md → TEST-DATA-AND-STATE.md.

## Not tested
- A real phone, other browsers, or a screen reader
- Submitting Revert on a batch with dependants or on a zero-row batch (B3)
- Reopening a closed preview (B4)
- Staff Correct/Remove on opening balances, invoices or customers
- Allocate / "Not for an open invoice"; credits
- Whether a correction reason is mandatory
- The "Approve a different date" and "Decline" outcomes
- T8; concurrency with other testers

## Evidence that is missing or was never captured
- No dedicated screenshot for B2 (partly visible in E12), B3, B5–B9, U2, U10, U11 or U12 (the accessible name is
  text-only). Their evidence is text: verbatim script output and snapshots. B4 and U6 are visible in E12 and E05.
- No network HAR or request/response bodies. Only method and path lists were recorded.
- Browser console messages before 04:46:28 UTC are unknown.
- No server logs.
- The application revision is unverified.
- Internal ids for payments, notes, opening balances, completeness statements, import batches and customers were not
  recorded.
- The scripts did not print timestamps, so excerpt times are approximate.

## Redactions and exclusions
- Excluded:
  - access codes, cookie values, session tokens, authentication headers
  - browser profile data
  - cookie names from unrelated websites present in the automation browser
  - the server account username in the console's backup path (B9, shown as `[REDACTED-USERNAME]`)
  - older, unrelated files in the automation output folder
- All three access codes were searched for across the package and found nowhere.
- The meaning of every finding is preserved.
