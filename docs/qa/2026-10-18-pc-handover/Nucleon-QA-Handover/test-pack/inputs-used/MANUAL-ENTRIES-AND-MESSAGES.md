# Manual entries and messages used (tag CL1018T)

Every value typed by hand during the session, in order. All are fictional. Access codes were typed into
password fields at the sign-in prompts. They are deliberately **not** recorded here.

| # | Task | Role | Where | Values entered |
|---|---|---|---|---|
| 1 | T1 | Staff | Records > Add a customer | `CL1018T Manual A fictional` → C-0004 |
| 2 | T1 | Staff | Records > Add a customer | `CL1018T Manual B fictional` → C-0005 |
| 3 | T1 | Staff | Records > Add an invoice | Customer C-0004; number `CL1018T-001`; date 2026-10-05; amount `1000.00`; due blank; still owed blank; **as-of cleared** (was pre-filled 2026-10-16); opening-balance question left "Not sure" |
| 4 | T1 | Staff | Records > Add an invoice | Customer C-0005; number `CL1018T-001`; date 2026-10-05; amount `200.00`; due 2026-10-10; still owed blank; as-of cleared |
| 5 | T2 | Staff | Records > Add what you know | Note `CL1018T fictional test customer. Prefers a written payment date.`; About C-0004; Kind "Context to know" |
| 6 | T2 | Owner | Records > note | Confirm (on the CL1018T note only) |
| 7 | T2 | Staff | New request | `Test CL1018T. Could we pay invoice CL1018T-001 on 14 November 2026 instead?` |
| 8 | T2 | Staff | Clarification | First sent with nothing selected (validation check); then chose CL1018T Manual A fictional (C-0004) |
| 9 | T2 | Owner | Case decision | "Approve Sat 14 Nov"; reason `Fictional test only` |
| 10 | T3 | Staff | Import a CSV file | Invoices; source `CL1018T Invoice test`; file 01-invoices.csv; both unknown customers → "Create a new customer"; Update preview; Apply 2 rows |
| 11 | T3 | Staff | Import a CSV file | Same file and source again; Apply 0 rows |
| 12 | T3b | Staff | Import a CSV file | Invoices; source `CL1018T Invalid preview`; file 03-invalid-preview-only.csv; Preview; **Close** (not applied) |
| 13 | T4 | Staff | Import a CSV file | Payments received; source `CL1018T Payment test`; file 02-payments.csv; Apply 2 rows |
| 14 | T4 | Staff | Import a CSV file | Same file and source again; **Close** (not applied) |
| 15 | T5 | Owner | Add an opening balance (C-0006) | As at 2026-09-30; amount `0.00`; Owed by the customer; credits "It includes none"; source `Fictional test dataset starts from zero` |
| 16 | T5 | Owner | Confirm records are complete | Only these customers: CL1018T Imported A fictional; Payments received; From 2026-10-01; To 2026-10-16; How you know `Fictional test pack contains the full payment history`; confirmation ticked |
| 17 | T5 | Staff | New request | `Test CL1018T. Could we pay invoice CL1018T-CSV-001 on 14 November 2026 instead?`; clarification answer CL1018T Imported A fictional (C-0006) |
| 18 | T5 | Owner | Case decision | "Approve Sat 14 Nov"; reason `Fictional test only` |
| 19 | T6a | Staff | Record a payment or credit | Money received; customer C-0006; date 2026-10-14; amount `10.00`; reference `CL1018T-LATE-ENTRY`; opening-balance question left "Not sure"; left unallocated |
| 20 | T6b | Staff | Correct invoice (C-0005 CL1018T-001) | Invoice amount `220.00` (from 200.00); reason `Fictional correction test`; other pre-filled fields untouched |
| 21 | T6c | Staff | Import a CSV file | Invoices; source `CL1018T Revert test`; file 04-revert-only.csv; customer → "Create a new customer"; Update preview; Apply 1 row |
| 22 | T6c | Staff | Import history > Revert (04 row) | Reason `Fictional reversal test` |
| 23 | Extra (B3) | Staff | Import history > Revert (01 "New 2" row) | Form opened and closed; **nothing typed or submitted** |
| 24 | Extra (B2) | Staff | Add an opening balance (C-0005) | As at 2026-09-30; amount `0.00`; direction and credits left at defaults (Owed by the customer / Not stated); source `CL1018T staff permission probe (fictional)` |
| 25 | Extra | Staff | New request | `Test CL1018T. Could we pay invoice CL1018T-001 a bit later?` |
| 26 | Extra | Staff | Clarification | Chose CL1018T Manual B fictional (C-0005); first no date (validation check); then date 2026-10-12 (rejected, 422); then 2026-11-20 (accepted) |
