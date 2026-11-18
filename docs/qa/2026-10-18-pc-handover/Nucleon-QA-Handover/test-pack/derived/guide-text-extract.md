<!-- DERIVED FILE made during packaging: plain-text extraction of
test-pack/original/Nucleon-Team-Test-Pack/Nucleon-Team-Testing-Guide.docx for searchability.
Formatting is approximate; the .docx is authoritative. Not part of the original pack. -->

# Project NucleonTeam Use Testing Guide

Revised guide  |  Shared practice release a9ce30d  |  18 October 2026

Use this guided walkthrough to find confusing steps and incorrect behaviour. Allow 15 minutes for T1 and T2, or about 45 to 60 minutes for T1 to T7. These are planning estimates. Record actual time and any help needed. Work in order because later tasks use earlier records.

Website: https://nucleon.dracooz.top

### Start with your own test folder

Extract Nucleon-Team-Test-Pack.zip first. In the testers folder, open the folder bearing your name. Its four CSVs already contain your tag. You do not need to edit them. For a pair, use one person’s folder and tag for the whole run. TAG below means that exact tag, not the literal word TAG.

| Tester folder | TAG to use |
| Hanting-HL1815A | HL1815A |
| Hoang-HN1815A | HN1815A |
| Phu-PD1815A | PD1815A |
| Chris-CC1815A | CC1815A |
| Tony-TT1815A | TT1815A |

Repeat tests need a fresh tag: copy a tester folder and replace its old tag in all four CSVs and the manual examples. The optional templates folder contains the original TESTTAG versions. Do not import multiple testers’ folders.

### Sign in and navigate

At the first screen, paste the Staff access code into Access code and click Sign in. The code selects the role. Once inside, Staff and Owner are the buttons at the top. Clicking Owner asks for its code the first time. A pair may instead use separate browsers, one signed in as each role. Codes are supplied privately by Hanting and change on restart or deployment.

Records opens data management. Click the Nucleon name at top left to return to the case desk. A mobile back arrow may return to the case list. If another tester’s case appears, locate your tag before acting.

### Shared instance rules and dates

Use only your tagged fictional records. Do not use Demo console, Reset, Restore or Start empty. Do not change shared settings or choose All customers in a note or completeness statement. Leave your records for review. A generated reply stays unsent.

At the top of Records, check Today is and Amounts in. These examples need AUD and a business date from 16 October to 13 November 2026. The practice date may differ from your computer date. If outside that range, ask Hanting to adapt the examples. First-run setup is a separate isolated test, not part of this shared session.

## Manual records and an owner decision

### T1 Add two customers with a shared invoice number

1. As Staff, open Records and scroll to Add a customer. Add TAG Manual A fictional, then TAG Manual B fictional. For example, Hanting uses HL1815A Manual A fictional.

2. In Add an invoice, deliberately select the correct customer each time. Existing sample customers may be selected by default. Enter the two invoices below. Leave Amount still owed and its as-of date blank. Click Add invoice for each.

| Field | Manual A | Manual B |
| Invoice number | TAG-001 | TAG-001 |
| Invoice date | 5 October 2026 | 5 October 2026 |
| Invoice amount | 1000.00 | 200.00 |
| Due date | Leave blank | 10 October 2026 |

Check: Both invoices exist under your two customer names. A’s due date is Not on record. An invoice total alone does not establish the remaining debt.

### T2 Record context and finish a request

1. In Records, find What you already know and Add what you know. Enter TAG fictional test customer. Prefers a written payment date, replacing TAG. Under About select your Manual A, keep Context to know selected and click Save note. As Staff, the note is a draft.

2. Switch to Owner. Find that exact note and click Confirm. Return to Staff and click the Nucleon name. In New request paste the message below, replacing TAG, then click Send to the agent:

Test TAG. Could we pay invoice TAG-001 on 14 November 2026 instead?

3. If prompted with Which customer’s invoice is it, select your Manual A and submit the answer. If it asks for an invoice number or date instead, give TAG-001 and 14 November 2026, then check the customer. Do not accept a silent choice of the wrong customer.

4. When the case is With the owner, switch to Owner and open it. Check customer, invoice, confirmed note and missing data. Select Approve 14 November, enter reason Fictional test only, and submit the decision using the enabled button. Switch to Staff to inspect Copy reply.

Check: The approved date is 14 November. Original due date and exact debt remain unknown. The note is available to the owner. The reply says Not sent. Save the case link or reference in your feedback.

## Invoice import preview and repeat import

### T3 Import the two invoice rows

1. In your tester folder use 01-invoices.csv. Do not use the templates folder. In Records, scroll to Import a CSV file and select Invoices. Enter TAG Invoice test in Where is this file from. Upload the file, or paste its full text including the header row. Click Preview.

2. Check the mappings below. No amount-still-owed or amount-paid column should be selected. ISO dates such as 2026-10-05 are unambiguous, so Dates are written can stay Work it out.

| App field | CSV heading |
| Customer | Customer |
| Invoice number | Invoice number |
| Invoice date | Invoice date |
| Invoice amount | Invoice amount |
| Due date | Due date |

3. Under Customers not in the records, choose Create a new customer for both tagged Imported customers. Do not map them to existing Manual or sample customers. Click Update preview. The apply button stays disabled while required choices are unresolved.

4. Leave the optional completeness choice at Not sure, or not saying. Check the two rows: Imported A has 1000.00, Imported B has 200.00, both numbered TAG-CSV-001, dated 5 October and due 10 October. Click Apply 2 rows. Close the preview if needed to return to the upload form.

5. Import that same file again with exactly the same source label TAG Invoice test. It should show Already recorded, with zero new rows. If Apply 0 rows is offered, you may use it, then click Close. Do not change source names or create different customers just to force an import.

Check: There is still one TAG-CSV-001 under each Imported customer. Compare your own invoices and totals rather than the global customer count, which other testers can change.

### T3b Check errors without importing them

Upload 03-invalid-preview-only.csv as Invoices, source TAG Invalid preview. Click Preview. Expect one row rejected for 2026-02-31, one rejected for 1O0.00 where O is a letter, and one valid row for 250.00. Read the reasons and click Close. Do not click Apply: rejected rows do not prevent a valid row from being imported.

If you accidentally apply the valid row, record it in your feedback. It is a separate invoice and does not change the expected amount on TAG-CSV-001. Do not revert other imports to remove it.

### If an import will not proceed

Recheck the selected file type, column mappings and customer decisions, then click Update preview. If records changed during preview, refresh that preview and inspect it again. An unwanted preview can be closed; no records change until Apply. Use a new upload if you need to undo an already resolved review choice.

## Payments and an exact amount with a date

### T4 Import and inspect payments

1. Import 02-payments.csv from your own folder. Select Payments received, source TAG Payment test, then Preview. Check Customer, Date received, Amount received, Payment reference and Invoice it pays against the matching CSV columns. Leave completeness unset and click Update preview if you changed anything.

2. Check the two rows before Apply 2 rows: Imported A received 600.00 on 12 October for its own TAG-CSV-001; Imported B received 50.00 with a blank invoice reference. Then inspect Payments and credits.

Check: A’s payment is allocated to A’s invoice. Its invoice shows At most AUD 400.00. B’s 50.00 remains unallocated. The same invoice number must not cause payment to cross between customers.

3. Repeat the import with the same source TAG Payment test. Expect zero new payments and no second allocation. Close the preview when finished. Do not manually record another 600.00 payment.

### T5 Establish a complete basis for Imported A only

1. Switch to Owner. In Customers and invoices, find your Imported A customer heading and click Add an opening balance. Enter the following, then Save opening balance:

| Field | Value |
| As at | 30 September 2026 |
| Amount and direction | 0.00 and Owed by the customer |
| Credits or prepayments | It includes none |
| Where this figure comes from | Fictional test dataset starts from zero |

2. In Completeness, use Only these customers and tick your Imported A only. Select Payments received only. Set From to 1 October and To to 16 October 2026. How you know: Fictional test pack contains the full payment history. Read and tick the confirmation, then Confirm completeness. This statement is about this fictional exercise only.

3. Check A’s invoice is exactly AUD 400.00 as of 16 October. B must remain unconfirmed. If not exact, open Why not exact and record its explanation rather than changing values to obtain the expected answer.

4. As Staff, send: Test TAG. Could we pay invoice TAG-CSV-001 on 14 November 2026 instead? Choose Imported A when asked. As Owner, check the amount, date and calculation basis, then approve with reason Fictional test only. Save this completed case link for T6.

For reference: stated is a source’s dated claim; at most is an upper bound from available evidence; exact is a dated calculation supported by the required records and confirmations. None automatically means the amount is current today.

## Changed evidence corrections and reversal

### T6a Add a missing payment after confirmation

1. After completing T5, as Staff open Records and Record a payment or credit. Select Money received and explicitly select your Imported A. Date received: 14 October 2026. Amount: 10.00. Reference: TAG-LATE-ENTRY. Click Record it and leave it unallocated.

Check: This new entry falls inside the period you had already confirmed. A’s exact claim should disappear and its completeness statement should show why it no longer holds. The earlier completed case should show an evidence-change flag when reopened, while its original decision stays unchanged. Do not reconfirm completeness during this task.

### T6b Correct a manual invoice

1. Find your Manual B invoice TAG-001, not Imported B’s invoice. Click Correct, change Invoice amount from 200.00 to 220.00, enter reason Fictional correction test, and click Save correction.

Check: The row shows 220.00, a correction source and a higher version. There is no history-details viewer in this version. Do not spend time looking for one. Record the invoice reference so Hanting can inspect stored history separately if needed.

### T6c Revert only the dedicated test import

1. Import 04-revert-only.csv as Invoices, source TAG Revert test. Resolve its single new customer, click Update preview, then Apply 1 row. It creates a separate Revert Demo customer and a 75.00 invoice. Do not add notes, payments, opening balances or cases to this customer.

2. In Import history, locate 04-revert-only.csv with your TAG Revert test source. Click that row’s Revert, enter Fictional reversal test and submit. If an impact review appears, read it before confirming. Stop if it lists anything outside your dedicated test data.

Check: That batch becomes reverted and its invoice is no longer active. The other batches and cases remain. A disabled or blocked revert must explain its dependency. Do not revert 01-invoices.csv or 02-payments.csv.

### T7 Phone layout and sign out

On an actual phone if available, open the case list, your case and Records. Switch Staff and Owner and test navigation and sign-out. If using only a narrow desktop browser, say so. The top bar may wrap to two rows. Report page-wide sideways scrolling, off-screen controls, overlapping text or unusable fields. Wide data tables may scroll within their own area.

### When a case seems stuck

Preparing normally takes several seconds and may be longer while the model is busy. Record elapsed time. If it is still there after two minutes, take the case URL and status and tell Hanting. Do not send the same request repeatedly. Needs your answer is a clarification to complete. Couldn’t prepare is a technical failure: record it, use Prepare again once, then report a repeated failure. A sign-in screen after a restart needs the current code, not a reset.

## Feedback and facilitator notes

Tester ____________________   Partner ____________________   TAG ____________________

Time ____________________   Device and browser ____________________________________

Mark Alone, Help, Blocked or Not tested. Include waiting time. A completed guided task is not evidence of business accuracy or time savings.

| Task | Result | Minutes | Help or issue |
| T1 Manual records |  |  |  |
| T2 Note and decision |  |  |  |
| T3 CSV and errors |  |  |  |
| T4 Payments |  |  |  |
| T5 Exact amount |  |  |  |
| T6 Changes and revert |  |  |  |
| T7 Phone or narrow screen |  |  |  |

### What needs improving

Which step needed help, and what wording or action did you expect?

________________________________________________________________________________

Could you tell why an amount was uncertain or exact, and the date it applied to?

________________________________________________________________________________

What work did this remove, and what new entry or checking did it introduce?

________________________________________________________________________________

For each issue include task ID, TAG, role, steps, expected and actual result, case link or invoice reference, time and a screenshot if useful. Exclude access codes. Send feedback through the team’s existing channel and leave your test data intact.

### For Hanting

Share the revised ZIP and current Staff and Owner codes privately. Ask each pair to use one folder. Capture hints given, model waiting time and confusion separately. This guide is a source-checked walkthrough, not a claim that these new tester files were run against the shared service.

Optional T8 uses a separate fresh database and URL prepared by the developer. As Owner, test Practice starting empty, AUD, two decimals, Australia/Sydney, one customer/invoice and optional knowledge. Check that an incomplete required item blocks requests. Test skipping optional knowledge. If also checking Real mode with fictional data, use another fresh database and verify sample loading and the console are refused. Never reset the shared URL for this test.

Scope: existing-invoice extensions using fictional data. Full business validation and additional-credit decisions remain outside this walkthrough. Guide revision 2 follows the a9ce30d interface.
