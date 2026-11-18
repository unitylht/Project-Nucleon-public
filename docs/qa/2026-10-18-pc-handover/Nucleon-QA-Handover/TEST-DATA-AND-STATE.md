# Test data and remaining state

Shared instance: https://nucleon.dracooz.top. Tester tag: **CL1018T**. Everything with that tag is fictional
and was created by this test session on 2026-10-18 between 04:34 and ≈04:52 UTC. **No cleanup was done.**
All records below were left in place for investigation. The state described is as of the end of testing;
other people may have changed the shared instance since.

Times in the app are Sydney time (AEDT, UTC+11). Internal ids are given only where they were actually read.
"Unknown" means the id was not recorded.

## 1. Records created by this session (safe to inspect)

### Customers
| Number | Name | How created | State at end |
|---|---|---|---|
| C-0004 | CL1018T Manual A fictional | Add a customer (Staff), T1 | Active |
| C-0005 | CL1018T Manual B fictional | Add a customer (Staff), T1 | Active. Has a Staff-entered opening balance (B2 probe). |
| C-0006 | CL1018T Imported A fictional | Created by import 01 (Staff), T3 | Active |
| C-0007 | CL1018T Imported B fictional | Created by import 01 (Staff), T3 | Active |
| C-0008 | CL1018T Revert Demo fictional | Created by import 04 (Staff), T6c | **Reverted** with the 04 batch; no longer listed |

Internal customer ids: unknown.

### Invoices
| Customer | Invoice | Date | Amount | Due | Source | Internal id | State at end |
|---|---|---|---|---|---|---|---|
| C-0004 | CL1018T-001 | 2026-10-05 | 1,000.00 | none | Entered by staff | invoice_ad0865208be82961 | Active; still owed Not recorded |
| C-0005 | CL1018T-001 | 2026-10-05 | **220.00** (was 200.00) | 2026-10-10 | Corrected by staff · version 2, reason "Fictional correction test" | invoice_46ed931bb654bf2f | Active |
| C-0006 | CL1018T-CSV-001 | 2026-10-05 | 1,000.00 | 2026-10-10 | Import: CL1018T Invoice test | invoice_7058633933bfb4a7 | Active; "At most AUD 400.00" after T6a |
| C-0007 | CL1018T-CSV-001 | 2026-10-05 | 200.00 | 2026-10-10 | Import: CL1018T Invoice test | invoice_a1540f5bf81a8717 | Active; Not recorded |
| C-0008 | CL1018T-RV-001 | 2026-10-05 | 75.00 | 2026-10-10 | Import: CL1018T Revert test | unknown | **Reverted** (kept in history, not used by the agent) |

Not created: CL1018T-BAD-001, CL1018T-BAD-002 (rejected in preview) and CL1018T-VALID-PREVIEW (preview closed,
never applied). The closed preview batch still exists in Import history (B4).

### Payments
| Customer | Date | Amount | Reference | Source | Allocation | Internal id |
|---|---|---|---|---|---|---|
| C-0006 | 2026-10-12 | 600.00 | CL1018T-PAY-001 | Import: CL1018T Payment test | 600.00 to CL1018T-CSV-001 (C-0006) | unknown |
| C-0007 | 2026-10-12 | 50.00 | CL1018T-PAY-002 | Import: CL1018T Payment test | Not allocated | unknown |
| C-0006 | 2026-10-14 | 10.00 | CL1018T-LATE-ENTRY | Entered by staff (T6a); opening-balance question "Not sure" | Not allocated | unknown |

### Opening balances
| Customer | As at | Amount | Credits in it | Source text | Entered in role |
|---|---|---|---|---|---|
| C-0006 | 2026-09-30 | 0.00 owed | It includes none | Fictional test dataset starts from zero | Owner (T5) |
| C-0005 | 2026-09-30 | 0.00 owed | Not stated | CL1018T staff permission probe (fictional) | **Staff** (B2 probe, outside the guide) |

### Note
"CL1018T fictional test customer. Prefers a written payment date." About C-0004, Context to know. Created by Staff,
confirmed by Owner. Internal id unknown.

### Completeness statement
C-0006 only, Payments received only, 2026-10-01 to 2026-10-16. How you know: "Fictional test pack contains the full
payment history". Confirmed by the owner 18 Oct 3:42 pm AEDT. It now shows **"No longer holds … CL1018T-LATE-ENTRY
changed inside the period afterwards."** It was not reconfirmed (as instructed). Internal id unknown.

### Import batches (Import history, newest first)
| App time (AEDT) | File | Source label | Rows | Status at end |
|---|---|---|---|---|
| 18 Oct 3:44 pm | 04-revert-only.csv | CL1018T Revert test | New 1 | **reverted**, reason "Fictional reversal test" |
| 18 Oct 3:40 pm | 02-payments.csv | CL1018T Payment test | Already recorded 2 | preview (closed, never applied) |
| 18 Oct 3:40 pm | 02-payments.csv | CL1018T Payment test | New 2 | applied |
| 18 Oct 3:40 pm | 03-invalid-preview-only.csv | CL1018T Invalid preview | New 1, Rejected 2 | preview (closed, never applied) |
| 18 Oct 3:39 pm | 01-invoices.csv | CL1018T Invoice test | Already recorded 2 | applied (zero new rows) |
| 18 Oct 3:39 pm | 01-invoices.csv | CL1018T Invoice test | New 2 | applied |

Batch ids: unknown. The 01 batch's Revert form was opened and closed without submitting (B3); nothing was reverted
except 04.

### Cases
| Case | Link | Customer / invoice | State at end |
|---|---|---|---|
| req_fcde410df1eff472 (T2) | https://nucleon.dracooz.top/#/case/req_fcde410df1eff472 | C-0004 / CL1018T-001 | Approved to Sat 14 Nov 2026, reason "Fictional test only", decided 18 Oct 3:38 pm; reply not sent |
| req_35c17a88570d5955 (T5) | https://nucleon.dracooz.top/#/case/req_35c17a88570d5955 | C-0006 / CL1018T-CSV-001 | Approved to Sat 14 Nov 2026, decided 18 Oct 3:43 pm; shows the "records changed after this decision" flag |
| req_366ba0f4763c2935 (extra) | https://nucleon.dracooz.top/#/case/req_366ba0f4763c2935 | C-0005 / CL1018T-001, asked Fri 20 Nov 2026 (date supplied by Staff) | **With the owner, undecided.** Clarification id clarify_3ed5da8f4a0e90fe; one answer was rejected with 422 (past date), then answered |

Approving a case did **not** change the invoice's Due column in Records. C-0006 still shows Sat 10 Oct and C-0004
still shows none (X15, read after both approvals). Whether approval is meant to update the invoice is not stated
in the guide (not filed as a finding).

## 2. What was changed, reverted and left behind
- **Created:** everything in §1.
- **Changed:** C-0005's invoice amount (200.00 → 220.00, version 2). The C-0006 completeness statement became
  invalid after the T6a payment. The note went from draft to confirmed.
- **Reverted:** the 04-revert-only.csv batch (customer C-0008 and invoice CL1018T-RV-001).
- **Not done:** no Reset, Restore, Start empty or console action; no "All customers" choice; no completeness
  reconfirmation; no deletion; no change to settings; no change to other testers' or sample records.
- **Left behind:** all of the above, including two closed-preview batches and one undecided case.

## 3. Records that are NOT from this session (do not modify)
| Record | Notes |
|---|---|
| Harbour Demo Supplies (C-DEMO-01), invoice DEMO-101 | Sample data |
| Harbour Demo Logistics (C-DEMO-02), invoices DEMO-201, DEMO-202 | Sample data |
| Release check café (fictional) (C-0003), invoices RC-1-77, RC-1-78, RC-1; payments "Prepayment RC (fictional)", "EFT RC (fictional)"; its opening balance and completeness statement "Release check (fictional)" | Already present at start, from someone else's release check |
| Cases req_e5bbc9e01e03efe1 (Harbour Demo Supplies, DEMO-101) and req_b5cc77f6db082ca4 (Harbour Demo Logistics, DEMO-201) | Present at start; With the owner |
| Case "Customer not identified yet – Hi, Harbour here…" (17 Oct 2:54 pm) and Release check café RC-1 case (approved to Fri 6 Nov, 18 Oct 2:33 pm) | Present at start; ids not recorded |
| Notes about Harbour Demo Supplies / Logistics, including the draft "Unconfirmed staff impression…" | Not mine; the draft was left as a draft |
| Console backups listed 18 Oct 1:16 am – 2:45 pm | Not mine; not touched |

Other testers' tags in the pack (HL1815A, HN1815A, PD1815A, CC1815A, TT1815A) were **not** used. HL1815A's folder
was only the template for the CL1018T copies. None of those tags were present in the app when this session started.

## 4. Browser authentication state
- **During testing,** all sessions were in a Playwright-controlled Chromium on the Windows PC.
  - Role sessions are cookies named `nucleon_staff`, `nucleon_owner` and `nucleon_operator` (HttpOnly, Secure,
    SameSite=Strict for the owner cookie as observed), plus `localStorage["nucleon.role"]` for the selected role.
  - Cookie values were never read or recorded.
- **Multi-role logout issue (B1):** with Staff and Owner both unlocked, Sign out ends only the selected role, so
  the browser can end up in the other role. Anyone reproducing should click Sign out once per role and confirm
  the sign-in screen appears.
- **At the end of testing (≈04:52 UTC):**
  - The Operator had been signed out (all cookies cleared at ≈04:50:45 UTC).
  - Then a **Staff-only** session was signed in at a 1400×900 window for the extra missing-date check.
  - Owner had not been unlocked again after the last full sign-out.
  - This Staff session was **not** signed out.
- **At packaging time (05:23:09 UTC, X28):** the automation browser was on `about:blank` with **no** cookies for
  nucleon.dracooz.top. It appears to have been restarted. Whether the server still treats the earlier Staff session as
  valid is unknown. The guide says codes change on restart or deployment.
- No access codes, cookie values, tokens or browser profile data are included in this package.
