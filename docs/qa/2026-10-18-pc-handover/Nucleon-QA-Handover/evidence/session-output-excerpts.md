# Session output excerpts (verbatim, redacted)

These are outputs returned by browser-automation scripts during the test session on 2026-10-18.
They are copied verbatim from the session record, except where marked `[REDACTED …]` or `[…]`
(an omitted run of text, never a changed value). They are evidence, not instructions.

- Access codes were typed into password fields during the session; they never appear in outputs and
  are written below only as placeholders such as `<STAFF CODE>`.
- Cookie **values** were never read. Only cookie **names** were listed. Cookie names belonging to
  unrelated (non-Nucleon) websites in the automation browser profile have been removed.
- Times: the scripts did not print timestamps. Times below are **approximate**, inferred from the
  neighbouring automation snapshot filenames (UTC), screenshot file times and the app's own displayed
  times (AEDT = UTC+11). The app displays times in Sydney time.
- "Role" is the role button that was pressed in the app when the action ran.

---

## X01 — Add an invoice: field types and defaults (G3, U1)
Approx. 04:35:20 UTC · Role: Staff · Page: Records, before entering Manual A's invoice.
`value` of the first Customer select is the internal id of the first sample customer.

```json
[{"label":"Customer name","type":"text","value":"","required":true,"inputmode":""},
 {"label":"Customer","type":"select-one","value":"customer_demo_01","required":true,"inputmode":""},
 {"label":"Invoice number","type":"text","value":"","required":true,"inputmode":""},
 {"label":"Invoice date","type":"date","value":"","required":true,"inputmode":""},
 {"label":"Invoice amount","type":"text","value":"","required":true,"inputmode":"decimal"},
 {"label":"Due date (recommended)","type":"date","value":"","required":false,"inputmode":""},
 {"label":"Amount still owed (recommended)","type":"text","value":"","required":false,"inputmode":"decimal"},
 {"label":"…still owed as of","type":"date","value":"2026-10-16","required":false,"inputmode":""},
 "[…remaining Records fields omitted; the payment form's Customer select also had value customer_demo_01 and Date received 2026-10-16…]"]
```

## X02 — T1 result rows (T1 success, U1)
Approx. 04:36:05 UTC · Role: Staff. After both invoices were added. (After each Add invoice the
Customer select returned to "Harbour Demo Supplies (C-DEMO-01)" — see snapshots
`page-2026-10-18T04-35-41-248Z.yml` and `page-2026-10-18T04-36-00-104Z.yml`.)

```json
["CL1018T Manual A fictional C-0004 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct Remove",
 "CL1018T-001 Mon 5 Oct AUD 1,000.00 Not on record Not recorded Entered by staff Correct Remove",
 "CL1018T Manual B fictional C-0005 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct Remove",
 "CL1018T-001 Mon 5 Oct AUD 200.00 Sat 10 Oct Not recorded Entered by staff Correct Remove",
 "Received Amount Allocated to Left",
 "CL1018T Manual A fictional Not confirmed Mon 5 Oct Not confirmed —",
 "CL1018T Manual B fictional Not confirmed Mon 5 Oct Not confirmed —"]
```

## X03 — Wrong-role code at the Owner prompt (U2)
Approx. 04:36:34–04:36:41 UTC. Clicked **Owner** (Staff session) → page heading "Sign in as owner"
with "Or continue as Staff" (snapshot `page-2026-10-18T04-36-34-444Z.yml`). Typed `<STAFF CODE>` and
pressed Enter → app returned to Records with **Staff** pressed and no message (snapshot
`page-2026-10-18T04-36-41-059Z.yml`, banner: `button "Staff" [pressed]`). Clicking Owner again and
entering `<OWNER CODE>` signed in as Owner (`page-2026-10-18T04-36-52-036Z.yml`).

## X04 — Copy reply (U3, U4, T2)
Approx. 04:38:45 UTC · Role: Staff · Case req_fcde410df1eff472. Clipboard read after clicking Copy reply;
`btn` is the button's visible text afterwards.

```json
{"clip":"Your payment extension for invoice CL1018T-001 is approved. The new payment date is 2026-11-14.","btn":["Copy reply"]}
```

## X05 — Import preview table and completeness control (G1, G2)
Approx. 04:39:25 UTC · Role: Staff · 01-invoices.csv preview after Update preview.
`hasCompleteness` tests whether the word "complete" appears anywhere in the import section.

```json
{"tableHTML":"<table class=\"table\"><thead><tr><th>Row</th><th>Customer</th><th>Invoice</th><th>Result</th></tr></thead><tbody><tr><td>2</td><td>CL1018T Imported A fictional</td><td>CL1018T-CSV-001</td>\n      <td>New\n      \n      \n      </td></tr><tr><td>3</td><td>CL1018T Imported B fictional</td><td>CL1018T-CSV-001</td>\n      <td>New\n      \n      \n      </td></tr></tbody></table>",
 "hasCompleteness":false,"hidden":[]}
```

## X06 — T3 after Apply 2 rows (T3 success)
Approx. 04:39:40 UTC · Role: Staff.

```json
{"out":["[…Manual A/B rows as X02…]",
 "CL1018T Imported A fictional C-0006 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct",
 "CL1018T-CSV-001 Mon 5 Oct AUD 1,000.00 Sat 10 Oct Not recorded Import: CL1018T Invoice test Correct",
 "CL1018T Imported B fictional C-0007 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct",
 "CL1018T-CSV-001 Mon 5 Oct AUD 200.00 Sat 10 Oct Not recorded Import: CL1018T Invoice test Correct",
 "[…completeness rows…]",
 "18 Oct, 3:39 pm 01-invoices.csv CL1018T Invoice test New 2 applied Revert"],
 "alerts":["Import applied"]}
```

## X07 — T3 repeat import with the same source label (T3 success, B3 context)
Approx. 04:39:50–04:40:02 UTC · Role: Staff. Preview text, then the state after clicking **Apply 0 rows**.

```text
01-invoices.csv · invoices · CL1018T Invoice test · 2 rows · column choices remembered from an earlier import

This exact file was imported before (18 Oct, 3:39 pm). Rows already recorded show as "Already recorded".
[…mapping selects…]
Already recorded: 2

Update preview
Apply 0 rows
Close
```

```json
{"out":["[…]",
 "CL1018T-CSV-001 Mon 5 Oct AUD 1,000.00 Sat 10 Oct Not recorded Import: CL1018T Invoice test Correct",
 "[…]",
 "CL1018T-CSV-001 Mon 5 Oct AUD 200.00 Sat 10 Oct Not recorded Import: CL1018T Invoice test Correct",
 "[…]",
 "18 Oct, 3:39 pm 01-invoices.csv CL1018T Invoice test Already recorded 2 applied Revert",
 "18 Oct, 3:39 pm 01-invoices.csv CL1018T Invoice test New 2 applied Revert"],
 "alerts":["Import applied"]}
```

Import history table (inline accessibility snapshot, **summarised, not verbatim**, same time): columns When / File / Rows / Status / (button);
row 1 `18 Oct, 3:39 pm | 01-invoices.csv CL1018T Invoice test | Already recorded 2 | applied | Revert`;
row 2 `18 Oct, 3:39 pm | 01-invoices.csv CL1018T Invoice test | New 2 | applied | Revert`.

## X08 — T3b after Close (T3b success, B4)
Approx. 04:40:25 UTC · Role: Staff. Immediately after clicking Close on the 03 preview (0.8 s wait).
`validOccurrences` counts "CL1018T-VALID-PREVIEW" anywhere on the page.

```json
{"hist":"Import history\nWhen\tFile\tRows\tStatus\t\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tAlready recorded 2\tapplied\tRevert\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tNew 2\tapplied\tRevert","validOccurrences":0}
```

## X09 — T4 after Apply 2 rows (T4 success, U6, B4)
Approx. 04:40:45 UTC · Role: Staff.

```json
{"invoices":["[…Manual A/B…]",
 "CL1018T Imported A fictional C-0006 Invoices AUD 1,000.00 · payments and credits AUD 600.00 · unallocated AUD 0.00 · recorded net AUD 400.00, a difference of records, not what is owed Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete (latest Mon 12 Oct) Correct",
 "CL1018T-CSV-001 Mon 5 Oct AUD 1,000.00 Sat 10 Oct At most AUD 400.00 AUD 600.00 allocated Why not exact Import: CL1018T Invoice test Correct",
 "CL1018T Imported B fictional C-0007 Invoices AUD 200.00 · payments and credits AUD 50.00 · unallocated AUD 50.00 · recorded net AUD 150.00, a difference of records, not what is owed Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete (latest Mon 12 Oct) Correct",
 "CL1018T-CSV-001 Mon 5 Oct AUD 200.00 Sat 10 Oct Not recorded Import: CL1018T Invoice test Correct"],
 "payments":["CL1018T Imported A fictional C-0006",
 "Mon 12 Oct CL1018T-PAY-001 AUD 600.00 CL1018T-CSV-001 AUD 600.00 Remove — Import: CL1018T Payment test Correct",
 "CL1018T Imported B fictional C-0007",
 "Mon 12 Oct CL1018T-PAY-002 AUD 50.00 Not allocated AUD 50.00 unallocated Import: CL1018T Payment test Allocate Not for an open invoice Correct"],
 "history":"Import history\nWhen\tFile\tRows\tStatus\t\n18 Oct, 3:40 pm\t02-payments.csv\npayments · CL1018T Payment test\n\tNew 2\tapplied\tRevert\n18 Oct, 3:40 pm\t03-invalid-preview-only.csv\nCL1018T Invalid preview\n\tNew 1, Rejected 2\tpreview\tOpen\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tAlready recorded 2\tapplied\tRevert\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tNew 2\tapplied\tRevert",
 "alerts":["Import applied"]}
```

Payment preview before Apply (inline accessibility snapshot, **summarised, not verbatim**; ≈04:40:35 UTC): mappings Customer→Customer,
Date received→Payment date, Amount received→Amount received, Payment reference (optional)→Payment reference,
Invoice it pays (optional)→Invoice number; "New: 2"; table columns Row / Customer / Reference / Result;
row 2 `CL1018T Imported A fictional | CL1018T-PAY-001 | New — Allocate AUD 600.00 to CL1018T-CSV-001`;
row 3 `CL1018T Imported B fictional | CL1018T-PAY-002 | New`.

## X10 — T4 repeat payment import, then Close (T4 success, B4)
Approx. 04:41:00–04:41:15 UTC · Role: Staff. Preview showed `Already recorded: 2` and `Apply 0 rows`;
Close was clicked (not Apply). State 1 s later:

```json
{"pay":"CL1018T Imported A fictional C-0006\nMon 12 Oct\nCL1018T-PAY-001\n\tAUD 600.00\tCL1018T-CSV-001 AUD 600.00 Remove\t—\tImport: CL1018T Payment test\nCorrect\nCL1018T Imported B fictional C-0007\nMon 12 Oct\nCL1018T-PAY-002\n\tAUD 50.00\tNot allocated\tAUD 50.00\nunallocated\n\tImport: CL1018T Payment test\nAllocate Not for an open invoice Correct\n[…]",
 "hist":"Import history\nWhen\tFile\tRows\tStatus\t\n18 Oct, 3:40 pm\t02-payments.csv\npayments · CL1018T Payment test\n\tNew 2\tapplied\tRevert\n18 Oct, 3:40 pm\t03-invalid-preview-only.csv\nCL1018T Invalid preview\n\tNew 1, Rejected 2\tpreview\tOpen\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tAlready recorded 2\tapplied\tRevert\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tNew 2\tapplied\tRevert"}
```

(The closed repeat-payment preview is not yet listed here; it is listed as `preview · Open` in X17 and in E12.)

## X11 — "Why not exact" on Imported A, before T5 (T4)
Approx. 04:41:20 UTC · Role: Staff.

```text
CL1018T-CSV-001	Mon 5 Oct	AUD 1,000.00	Sat 10 Oct	At most AUD 400.00
AUD 600.00 allocated
Why not exact
No opening balance says what this customer owed, or held in credit, before their records start. A credit from before then could settle this invoice.
Payment records for this customer have no confirmed completeness.
	Import: CL1018T Invoice test	Correct
```

## X12 — Staff sees an active opening-balance form (B2 context)
Approx. 04:41:30 UTC · Role: Staff. Clicked "Add an opening balance" on Imported A. An inline form opened
(not a dialog). Accessibility snapshot excerpt (form was **not** saved here):

```yaml
- heading "Opening balance for CL1018T Imported A fictional" [level=3]
- paragraph: "What CL1018T Imported A fictional owed, or held in credit, as at one date: everything up to that date in one figure. Invoices and payments dated on or before it are then asked about: already part of it, missed from it, or not sure."
- textbox "As at"
- textbox "Amount"
- group "This amount is": radio "Owed by the customer" [checked] / radio "Held in credit for them"
- combobox "Credits or prepayments in this figure": "Not stated" [selected] / "It includes none" / "Every one is recorded here, as a payment or credit dated on or before the as-at date"
- textbox "Where this figure comes from"
- button "Save opening balance"
```

The same Staff snapshot showed `Correct` and `Remove` buttons next to the existing opening balance of
another tester's customer "Release check café (fictional)" (not used).

## X13 — T5 opening balance (Owner) and completeness (T5 success)
Approx. 04:41:50–04:42:30 UTC · Role: Owner (`ownerPressed: "true"`).

```json
{"ownerPressed":"true","vals":[["As at","2026-09-30"],["Amount","0.00"],["Owed by the customer",true],["Held in credit for them",false],["Credits or prepayments in this figure","none"],["Where this figure comes from","Fictional test dataset starts from zero"]]}
```
```json
{"h":"CL1018T Imported A fictional C-0006\nInvoices AUD 1,000.00 · payments and credits AUD 600.00 · unallocated AUD 0.00\nOpening balance AUD 0.00 owed as at Wed 30 Sep · Fictional test dataset starts from zero · no credits in it Correct Remove\nBalance from it: AUD 400.00. The whole account, not one invoice.\nInvoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete (latest Mon 12 Oct)",
 "inv":"CL1018T-CSV-001\tMon 5 Oct\tAUD 1,000.00\tSat 10 Oct\tAt most AUD 400.00\nAUD 600.00 allocated\nWhy not exact\n\tImport: CL1018T Invoice test\tCorrect","alerts":["Opening balance saved"]}
```
Completeness form state just before **Confirm completeness**:
```json
[["Only these customers","radio",true],["CL1018T Imported A fictional","checkbox",true],["Payments received","checkbox",true],["From","date","2026-10-01"],["To","date","2026-10-16"],["How you know","text","Fictional test pack contains the full payment history"],["Every record of these types for these cu","checkbox",true]]
```
After confirming (excerpt):
```text
CL1018T Imported A fictional	Not confirmed	Mon 5 Oct	Fri 16 Oct	Mon 12 Oct
CL1018T Imported B fictional	Not confirmed	Mon 5 Oct	Not confirmed	Mon 12 Oct
CL1018T Imported A fictional: payments complete from Thu 1 Oct to Fri 16 Oct
Fictional test pack contains the full payment history · confirmed by the owner 18 Oct, 3:42 pm
invA: CL1018T-CSV-001	Mon 5 Oct	AUD 1,000.00	Sat 10 Oct	AUD 400.00
exact, as of Fri 16 Oct	Import: CL1018T Invoice test	Correct
invB: CL1018T-CSV-001	Mon 5 Oct	AUD 200.00	Sat 10 Oct	Not recorded	Import: CL1018T Invoice test	Correct
alerts: ["Completeness confirmed"]
```

## X14 — T5 case req_35c17a88570d5955 as prepared, then Owner evidence and decision (T5 success, U8)
Approx. 04:42:40–04:43:20 UTC. Staff answered the customer clarification with Imported A (C-0006);
the case was ready 11.9 s after the answer was sent.

```text
CL1018T Imported A fictional
Invoice CL1018T-CSV-001

Waiting for the owner's decision. Nothing to do yet.
[…]
6 days late
+35 days
Due
Sat 10 Oct
Today
Fri 16 Oct
Asked for
Sat 14 Nov
Key facts
Outstanding
AUD 400.00
exact, as of Fri 16 Oct
Due date now
Sat 10 Oct 2026
Asked to pay on
Sat 14 Nov 2026
Extension
35 days
Overdue today
6 days

Calculated by the app from the invoice, the payments allocated to it and the owner's statement that this customer's payment records are complete. Today is fixed at Fri 16 Oct 2026 for this demo.
[…]
Worth checking
Invoice CL1018T-CSV-001 exists for more than one customer; staff chose the one for CL1018T Imported A fictional.
Exactly AUD 400.00 was still owed on this invoice as of Fri 16 Oct 2026: Invoice amount AUD 1,000.00; Payments and credits allocated to it up to Fri 16 Oct 2026 − AUD 600.00. Payment records for this customer are confirmed complete from Thu 1 Oct 2026 to Fri 16 Oct 2026 (Fictional test pack contains the full payment history, confirmed by the owner), which includes that there are no credit notes or other adjustments in that period; this version cannot record them.
Customer balance (the whole account, not this invoice): AUD 400.00, from an opening balance of AUD 0.00 owed as at Wed 30 Sep 2026 (Fictional test dataset starts from zero) and the records after it. Records for this customer are not confirmed complete, so this balance only reflects what is recorded.
A person said the opening balance includes no credits or prepayments.
There are no confirmed owner notes for this customer.
```
Owner "Evidence and sources" (before deciding):
```text
Outstanding amount	AUD 400.00 (exact, as of Fri 16 Oct 2026)	Calculated by the app: starting amount − payments allocated to it while payment records are confirmed complete
Original due date	Sat 10 Oct 2026	Invoice CL1018T-CSV-001 record
Current due date	Sat 10 Oct 2026	Invoice CL1018T-CSV-001 record, no approved extension on record
Requested date	Sat 14 Nov 2026	Customer's words "14 November 2026", read by the agentNot verified
As-of date	Fri 16 Oct 2026	Fixed date for this demo
Extension requested	35 days	Calculated by the app: requested date − current due date
Days overdue	6 days	Calculated by the app: max(0, as-of date − current due date)
How the agent read the message
Invoice	CL1018T-CSV-001
Customer named	Not stated
Date asked for	Sat 14 Nov 2026 from "14 November 2026"
Reason	None given
```
After **Approve Sat 14 Nov**, reason "Fictional test only":
```text
Reply to send
Your payment extension for invoice CL1018T-CSV-001 is approved. The new payment date is 2026-11-14.

Not sent. Staff send it from their usual email.

Owner's reason: Fictional test only
Decided 18 Oct, 3:43 pm, for this invoice only.
```

## X15 — T6a late entry (T6a success, U7)
Approx. 04:43:40–04:43:56 UTC · Role: Staff. Payment form before **Record it**:
`{"sel":"CL1018T Imported A fictional (C-0006)","vals":[["Money received","payment"],["Date received","2026-10-14"],["Amount","10.00"],["Reference (optional)","CL1018T-LATE-ENTRY"],["Not sure","unsure"]]}`

```json
{"before":"CL1018T-CSV-001\tMon 5 Oct\tAUD 1,000.00\tSat 10 Oct\tAUD 400.00\nexact, as of Fri 16 Oct\n\tImport: CL1018T Invoice test\tCorrect",
 "manualA":"CL1018T-001\tMon 5 Oct\tAUD 1,000.00\tNot on record\tNot recorded\tEntered by staff\tCorrect Remove",
 "alerts":["Payment recorded"],
 "after":"CL1018T-CSV-001\tMon 5 Oct\tAUD 1,000.00\tSat 10 Oct\tAt most AUD 400.00\nAUD 600.00 allocated\nWhy not exact\n\tImport: CL1018T Invoice test\tCorrect",
 "hdr":"CL1018T Imported A fictional C-0006\nInvoices AUD 1,000.00 · payments and credits AUD 610.00 · unallocated AUD 10.00\nOpening balance AUD 0.00 owed as at Wed 30 Sep · Fictional test dataset starts from zero · no credits in it Correct Remove\nBalance from it: AUD 390.00. The whole account, not one invoice.\nInvoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete (latest Wed 14 Oct)",
 "comp":"[…]CL1018T Imported A fictional\tNot confirmed\tMon 5 Oct\tNot confirmed\tWed 14 Oct\n[…]\nCL1018T Imported A fictional: payments complete from Thu 1 Oct to Fri 16 Oct\n\nFictional test pack contains the full payment history · confirmed by the owner 18 Oct, 3:42 pm\nNo longer holds for CL1018T Imported A fictional: CL1018T-LATE-ENTRY changed inside the period afterwards.\n\nThe owner confirms completeness",
 "pay":"[…]Wed 14 Oct\nCL1018T-LATE-ENTRY\n\tAUD 10.00\tNot allocated\tAUD 10.00\nunallocated\n\tEntered by staff\nAllocate Not for an open invoice Correct Remove[…]"}
```
"Why not exact" afterwards:
```text
CL1018T-CSV-001	Mon 5 Oct	AUD 1,000.00	Sat 10 Oct	At most AUD 400.00
AUD 600.00 allocated
Why not exact
Payment records for this customer have no confirmed completeness from Wed 30 Sep 2026.
	Import: CL1018T Invoice test	Correct
```
Later (E12, 04:47:00 UTC) the Records page also showed a **Needs attention** section:
"CL1018T Imported A fictional: a statement that payments were complete no longer holds, because
CL1018T-LATE-ENTRY was added inside its period afterwards. It doesn't count for CL1018T Imported A
fictional until the record is removed or completeness is confirmed again." (read from the screenshot;
this section was not noticed during the session).

## X16 — T5 case reopened after the late entry (T6a success)
04:44:05 UTC (snapshot `page-2026-10-18T04-44-05-424Z.yml`) · Role: Staff. Excerpt of page text:

```text
CL1018T Imported A fictional
Invoice CL1018T-CSV-001

Approved. New payment date: Sat 14 Nov 2026.

Prepared by the Gemma agent, running locally.

The records changed after this decision. Amount still owed: was exactly AUD 400.00 as of Fri 16 Oct 2026; now at most AUD 400.00. The decision stands; check it if it matters. (18 Oct, 3:43 pm)
[…key facts unchanged: Outstanding AUD 400.00 exact, as of Fri 16 Oct; Extension 35 days; Overdue today 6 days…]
```

## X17 — T6b correction and T6c import/revert (T6b, T6c success, B4)
Approx. 04:44:20–04:45:25 UTC · Role: Staff.

Correction form pre-fill for Manual B's CL1018T-001 (form rendered under the Manual B C-0005 row):
```json
{"n":1,"vals":[["Invoice date","date","2026-10-05"],["Invoice amount","text","200.00"],["Due date (recommended)","date","2026-10-10"],["Amount still owed (recommended)","text",""],["…still owed as of","date","2026-10-16"],["Reason for the correction","text",""]]}
```
After changing only the amount to 220.00 and reason "Fictional correction test":
```json
{"alerts":["Corrected"],"rows":["CL1018T Manual B fictional C-0005 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct Remove","CL1018T-001 Mon 5 Oct AUD 220.00 Sat 10 Oct Not recorded Corrected by staff · version 2 Correct Remove"]}
```
Internal invoice ids read from each row's Correct button:
```json
[["CL1018T Manual A fictional C-0004 …","CL1018T-001","AUD 1,000.00","invoices:invoice_ad0865208be82961"],
 ["CL1018T Manual B fictional C-0005 …","CL1018T-001","AUD 220.00","invoices:invoice_46ed931bb654bf2f"],
 ["CL1018T Imported A fictional C-0006","CL1018T-CSV-001","AUD 1,000.00","invoices:invoice_7058633933bfb4a7"],
 ["CL1018T Imported B fictional C-0007","CL1018T-CSV-001","AUD 200.00","invoices:invoice_a1540f5bf81a8717"]]
```
04-revert-only.csv: after "Create a new customer" + Update preview → `New: 1`, row `2 CL1018T Revert Demo fictional CL1018T-RV-001 New`, button `Apply 1 row`. After Apply:
```json
{"alerts":["Import applied"],"rows":["CL1018T Revert Demo fictional C-0008 Add an opening balance Invoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete Correct","CL1018T-RV-001 Mon 5 Oct AUD 75.00 Sat 10 Oct Not recorded Import: CL1018T Revert test Correct"],
 "hist":"Import history\nWhen\tFile\tRows\tStatus\t\n18 Oct, 3:44 pm\t04-revert-only.csv\nCL1018T Revert test\n\tNew 1\tapplied\tRevert\n18 Oct, 3:40 pm\t02-payments.csv\npayments · CL1018T Payment test\n\tAlready recorded 2\tpreview\tOpen\n18 Oct, 3:40 pm\t02-payments.csv\npayments · CL1018T Payment test\n\tNew 2\tapplied\tRevert\n18 Oct, 3:40 pm\t03-invalid-preview-only.csv\nCL1018T Invalid preview\n\tNew 1, Rejected 2\tpreview\tOpen\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tAlready recorded 2\tapplied\tRevert\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tNew 2\tapplied\tRevert"}
```
Clicking that row's **Revert** opened an inline form (no dialog):
```text
Why revert this import?

Nothing is deleted: records from this import are marked reverted, and values it replaced get their earlier version back.

Revert
```
After entering "Fictional reversal test" and clicking the form's Revert (04:45:20 UTC snapshot):
```json
{"alerts":["Import reverted"],"dialogs":0,
 "hist":"Import history\nWhen\tFile\tRows\tStatus\t\n18 Oct, 3:44 pm\t04-revert-only.csv\nCL1018T Revert test\n\tNew 1\treverted\nFictional reversal test\n\t\n18 Oct, 3:40 pm\t02-payments.csv\npayments · CL1018T Payment test\n\tAlready recorded 2\tpreview\tOpen\n[…other rows unchanged, 01 and 02 still applied…]",
 "rows":"[…all CL1018T Manual/Imported rows unchanged; no Revert Demo / CL1018T-RV-001 row…]"}
```
Customer pickers afterwards contained no "Revert Demo"/C-0008 option and the page text had 0 matches
for "Revert Demo|RV-001".

## X18 — B3: opening (not submitting) Revert on the 01 "New 2" batch
Approx. 04:45:30–04:45:45 UTC · Role: Staff. Only the row-level Revert button was clicked, read, and
clicked again to close. **The form's Revert/submit button was never clicked.**

```json
{"disabled":false,"title":null,"nextTxt":"Why revert this import?\n\nNothing is deleted: records from this import are marked reverted, and values it replaced get their earlier version back.\n\nRevert","nextHasForm":1}
```
```json
{"openForms":0,"txt":"[…]18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tAlready recorded 2\tapplied\tRevert\n18 Oct, 3:39 pm\t01-invoices.csv\nCL1018T Invoice test\n\tNew 2\tapplied\tRevert"}
```

## X19 — B2: Staff saves an opening balance on Manual B
Approx. 04:46:05 UTC · Role: Staff (`staffPressed: "true"`). As at 2026-09-30, amount 0.00, direction left
at default "Owed by the customer", credits left at default "Not stated", source
"CL1018T staff permission probe (fictional)".

```json
{"staffPressed":"true","alerts":["Opening balance saved"],"hdrTxt":"CL1018T Manual B fictional C-0005\nOpening balance AUD 0.00 owed as at Wed 30 Sep · CL1018T staff permission probe (fictional) · credits in it not stated Correct Remove\nBalance from it: AUD 220.00. The whole account, not one invoice.\nInvoices not confirmed complete (latest Mon 5 Oct) · payments not confirmed complete"}
```

## X20 — T7 narrow-window measurements (T7, U9)
04:46:28–04:47:30 UTC. `setViewportSize(390×844)`; `clientWidth` 375 because of the vertical scrollbar.

Home (Staff):
```json
{"vw":375,"scrollW":375,"bodyScrollW":375,"headerH":82,"off":[["LI","","",192,479],["BUTTON","","",192,479],["SMALL","","",202,469],"[…same pattern repeated…]"]}
```
(The off-screen LI/BUTTON elements were not visible in the screenshot E09; probably a hidden panel — not verified.)

Case req_35c17a88570d5955: `{"vw":375,"scrollW":375,"off":[]}`; a link with text "All cases" exists.

Records:
```json
{"vw":375,"scrollW":375,"scrollers":[["DIV","scroll",327,528],["DIV","scroll",327,346],["DIV","scroll",327,334]],"offOutside":[],
 "narrowOrOffInputs":[["Yes",56,69,13],["No, it was missed",56,69,13],["Not sure",56,69,13],["Money received",56,69,13],["A credit held for the cus",56,69,13],["Yes",56,69,13],["No, it was missed",56,69,13],["Not sure",56,69,13],["Context to know",56,69,13],["A rule staff should follo",56,69,13],["InvoicesOne row per invoi",56,69,13],["Payments receivedOne row ",56,69,13]]}
```
Role switching and navigation (B8):
```json
[["after Owner click","https://nucleon.dracooz.top/#/records","true","Records"],["owner sees confirm completeness",1],
 ["home","https://nucleon.dracooz.top/#/","2 cases need you. Choose it from the list."],
 ["case","https://nucleon.dracooz.top/#/case/req_fcde410df1eff472","All cases\n\nCL1018T Manual A fictional\nInvoice CL1018T-001\n\nApproved. New payment date: Sat 14 Nov 2026.\n\nPrepared by the Gemma agent, running locally."],
 ["all cases","https://nucleon.dracooz.top/#/",true],["staff","true"],["width",{"vw":375,"sw":375}]]
```

## X21 — B1 first observation: Sign out from Staff lands in Owner mode
04:47:40–04:47:57 UTC (E15, E16). Starting state: Staff and Owner both unlocked earlier in this browser
(Owner code entered 04:36:52 UTC); **Staff** pressed. Clicked the top-bar **Sign out**.

```json
[["signout box",{"x":309.6770935058594,"y":52.333335876464844,"width":50.989593505859375,"height":21}],
 ["after signout","https://nucleon.dracooz.top/#/","Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\nFor you\nHarbour Demo Supplies\nDEMO-101, to Fri 30 Oct\n16 Oct, 11:19 pm\nNeeds your decision\nHarbour Demo Logistics\nDEMO-201, to Fri 23 Oct\n17 Oct, 1:13 am\n"],
 ["deep link records after signout","https://nucleon.dracooz.top/#/records","Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\nRecords\n\nPractice workspace: everything here is fictional. Today is Fri 16 Oct 2026. Amounts in AUD.\n\nSetup\n\nReady"],
 ["deep link case after signout","Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\n\nAll cases\n\nCL1018T Imported A fictional\nInvoice CL1018T-CSV-001\n\nApproved. New payment date: Sat 14 Nov 2026.\n\nPr"],
 ["cookies",[["nucleon_owner",true,true,"Strict"],"[REDACTED: 28 cookie names belonging to unrelated non-Nucleon websites in the automation browser profile]"],"storage keys",["nucleon.role"]]]
```
(Cookie tuple format: name, httpOnly, secure, sameSite. Values were not read.)

Role state after reloading `#/`:
```json
{"role":[["Staff","false"],["Owner","true"]],"ls":{"role":"owner","ss":null},"body":"Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\nFor you\nHarbour Demo Supplies\nDEMO-101, to Fri 30 Oct\n16 Oct, 11:19 pm\nNeeds your decision\nHarbour Demo Logistics\nDEMO-201, to Fri 23 Oct\n17 Oct, 1:13 am\nNeeds your decision\nOther cases\n[…]"}
```
Then **Sign out** again (Owner pressed, only the owner cookie present) — network and result:
```json
{"reqs":[["POST","/api/demo/logout"],["GET","/api/session"]],"body":"Nucleon\n\nPayment extension requests. Enter the staff, owner or demo console code for this demonstration.\n\nAccess code\n\nSign in","cookies":[],"ls":null}
```

## X22 — B1 clean reproduction from a signed-out state
Approx. 04:48:10–04:48:30 UTC. Steps: sign in with `<STAFF CODE>` → click Owner → `<OWNER CODE>` →
click Staff → Sign out. Cookie names for nucleon.dracooz.top and `localStorage["nucleon.role"]` after each step:

```json
[["1 signed in staff","nucleon_staff","staff"],
 ["2 owner unlocked","nucleon_staff,nucleon_owner","owner"],
 ["3 back to staff","nucleon_staff,nucleon_owner","staff"],
 ["4 after Sign out","nucleon_owner","owner","pressed=Owner","signInShown=0",[["POST","/api/demo/logout"],["GET","/api/session"],["GET","/api/session"],["GET","/api/requests"]]],
 ["5 page","Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\nFor you\nHarbour Demo Supplies\nDEMO-101, to Fri 30 Oct\n16 Oct, 11:19 pm\nNeeds your decision\nHarbour Demo Logistics\nDEMO-201, to Fri 23 Oct\n17 Oct, 1:13 am\n"]]
```

## X23 — Console gate checks (U2, U12 context)
Approx. 04:48:40–04:49:20 UTC. After a full sign-out (`["signed out fully","",1]`), signed in with
`<STAFF CODE>` only (`["staff only","nucleon_staff"]`), then opened `#/console`:
```json
["console as staff","https://nucleon.dracooz.top/#/console","Open the demo console\n\nEnter the demo console code.\n\nAccess code\n\nSign in\nOr continue as\nStaff",["Sign in","Staff"],[["password","Access code"]],[]]
```
Entered `<OWNER CODE>` at that console prompt:
```json
{"url":"https://nucleon.dracooz.top/#/","cookies":"nucleon_staff,nucleon_owner","pressed":["Owner"],"main":"2 cases need you. Choose it from the list."}
```
Owner session, open `#/console`:
```json
{"url":"https://nucleon.dracooz.top/#/console","main":"Open the demo console\n\nEnter the demo console code.\n\nAccess code\n\nSign in\nOr continue as\nOwner\nStaff","inputs":["password"]}
```

## X24 — B1 mirror case: Sign out from Owner while Staff is also unlocked
Approx. 04:49:30–04:50:00 UTC. Starting state: both cookies present (X23), **Owner** pressed. Clicked
Sign out. The next scripted step (typing a code into the sign-in field) timed out after 30 s because no
sign-in screen appeared. State read afterwards:
```json
{"url":"https://nucleon.dracooz.top/#/","cookies":"nucleon_staff","body":"Nucleon\nStaff\nOwner\n\nRecords\nConsole\nSign out\nNew request\n\nSend to the agent\nTry a sample\nFor you\nCustomer not identified yet\n[…]","pressed":[["Staff","true"],["Owner","false"]]}
```

## X25 — Operator role, read-only (B9, U11, B7)
Approx. 04:50:00–04:50:45 UTC. Sign out (Staff only) → `{"out1":["",1]}` (no cookies, sign-in shown).
Signed in with `<OPERATOR CODE>` → redirected to `#/console`, cookie `nucleon_operator`, neither Staff nor
Owner pressed, header "Nucleon / Staff / Owner / Console / Sign out" (no Records link). **No console
button was clicked.** Buttons present (all enabled): Reset demo data, Start empty, Copy ×5, Restore ×8.
Console text excerpt:
```text
Demo console

Prepare and repeat demonstrations. Changes here affect everyone using this demo.

Start again

6 cases: 3 completed, 2 waiting for the owner, 1 waiting for staff. Resetting clears every case and restores the original demo invoices and due dates. Sign-ins and settings stay as they are. A backup is saved first, so you can undo it.
[…]
Before you present
Agent	Ready
Signed in here	Nobody yet. Sign in as staff and owner in this browser once, then switch with the buttons at the top.
Demo date	Fixed at Fri 16 Oct 2026, so day counts stay the same in every run.
[…demo messages…]
Backups
Saved	Cases
18 Oct, 2:45 pm
nucleon-20261018-144501.sqlite3	4	Restore
[…7 more backups listed, from 18 Oct 2:44 pm back to 18 Oct 1:16 am…]

Restoring replaces the current cases with the backup. The current cases are saved first. Backups are kept in /Users/[REDACTED-USERNAME]/srv/nucleon/backups.
```
(Redaction: the original path contains the server account's home-folder username.)

Operator deep links:
```json
[["#/records","https://nucleon.dracooz.top/#/records","Sign in as staff\n\nPayment extension requests. Enter the staff, owner or demo console code for this demonstration.\n\nAccess code\n\nSign in\nOr continue as\nDemo console"],
 ["#/case/req_35c17a88570d5955","https://nucleon.dracooz.top/#/case/req_35c17a88570d5955","Sign in as staff\n[…same…]"],
 ["#/","Sign in as staff\n[…same…]"]]
```
The browser console recorded the B7 TypeError during/after these navigations (see the console log).
On the "Sign in as staff" screen there was no Sign out button and the operator cookie remained:
```json
{"before":"nucleon_operator","signOutVisible":0,"after":"nucleon_operator","signIn":1}
```
Returning to `#/console` and clicking the header Sign out cleared it:
```json
{"headerSignOut":1,"after":"","signIn":1,"url":"https://nucleon.dracooz.top/#/console"}
```

## X26 — Missing-date request on Manual B (extra check; B6, U10)
Approx. 04:50:50–04:51:40 UTC · Role: Staff · window resized to 1400×900. Message:
"Test CL1018T. Could we pay invoice CL1018T-001 a bit later?" → case req_366ba0f4763c2935, clarification
ready after ≈11 s, asking for the customer **and** "Payment date the customer wants" in one form.

Selecting Manual B with no date and sending:
```json
{"inputs":[["radio","invoiceId","CL1018T Manual A fictionalC-0004 · invoi",true],["radio","invoiceId","CL1018T Manual B fictionalC-0005 · invoi",true],["date","requestedDueDate","Payment date the customer wants",true]],"alerts":["Enter an answer."],"stillAsking":1}
```
The message sat under the date field. Entering 2026-10-12 programmatically (bypassing the picker's
`min="2026-10-17"`) and sending → server HTTP 422 (see console log line 7) and the form showed
"Enter a date after Fri 16 Oct 2026 (the as-of date)."; the Manual B selection was kept. Entering
2026-11-20 → case ready after ≈15 s:
```text
CL1018T Manual B fictional
Invoice CL1018T-001

Waiting for the owner's decision. Nothing to do yet.
[…]
+41 days
Due
Sat 10 Oct
Today
Fri 16 Oct
Asked for
Fri 20 Nov
Key facts
Outstanding
Not recorded
Due date now
Sat 10 Oct 2026
Asked to pay on
Fri 20 Nov 2026
Extension
41 days
Overdue today
Unknown

Calculated by the app from the invoice record. Days overdue aren't calculated: no amount still owed is recorded. Today is fixed at Fri 16 Oct 2026 for this demo.

What the customer wrote
Test CL1018T. Could we pay invoice CL1018T-001 a bit later
(another request)
?

Their words as received, not verified. Underlined: another request, as picked out by the agent.

Worth checking
Staff supplied the requested date in a clarification answer; it is not confirmed by the customer.
Invoice CL1018T-001 exists for more than one customer; staff chose the one for CL1018T Manual B fictional.
No amount still owed is recorded for this invoice, so the brief does not say how much is outstanding.
Not an exact amount, because: Whether the opening balance as at Wed 30 Sep 2026 includes credits or prepayments is not stated. A credit in it could settle this invoice: say it has none, or record its credits. Payment records for this customer have no confirmed completeness from Wed 30 Sep 2026.
Customer balance (the whole account, not this invoice): AUD 220.00, from an opening balance of AUD 0.00 owed as at Wed 30 Sep 2026 (CL1018T staff permission probe (fictional)) and the records after it. Records for this customer are not confirmed complete, so this balance only reflects what is recorded.
Whether the opening balance includes credits or prepayments is not stated. A credit could settle this invoice, so no amount for this customer is exact.
There are no confirmed owner notes for this customer.
Model note on the message: The customer asks to pay 'a bit later' but does not specify a new date.
```

## X27 — Activity and Technical details of case req_35c17a88570d5955 (B5)
Approx. 04:51:50 UTC · Role: Staff.
```text
Activity
18 Oct, 3:42 pm
Staff sent the customer's message
18 Oct, 3:42 pm
The agent started preparing the case
18 Oct, 3:42 pm
Asked staff for the invoice number
18 Oct, 3:42 pm
Staff answered: invoice_7058633933bfb4a7
18 Oct, 3:42 pm
The agent started preparing the case
18 Oct, 3:42 pm
The case was ready for the owner
18 Oct, 3:43 pm
The owner approved Sat 14 Nov 2026
18 Oct, 3:43 pm
Reply drafted. Not sent
```
```text
Technical details

Gemma 4 26B-A4B (local GGUF, LM Studio via home gateway), model gemma-4-26b-a4b-it-heretic-zh-rp, loaded as gemma4 Q4_K_M. Prompt extension-v0.3.

3:42:34 pm
Run 66d654: live, finished, 3 model calls, 2 tool calls, 6.5 s
3:42:46 pm
Run 416154: live, finished, 7 model calls, 6 tool calls, 9.6 s
3:42:38 pm
Model call extract_request, 3.5 s
3:42:39 pm
Model call handle_request, 1.1 s
3:42:39 pm
findCustomers, by the agent
3:42:41 pm
Model call handle_request, 1.8 s
3:42:41 pm
createClarification, by the agent
3:42:49 pm
Model call extract_request, 2.5 s
3:42:50 pm
Model call handle_request, 1.3 s
3:42:50 pm
findCustomers, returned NOT_FOUND, by the agent
3:42:51 pm
Model call handle_request, 0.8 s
3:42:51 pm
findCustomers, by the agent
3:42:52 pm
Model call handle_request, 1.4 s
3:42:52 pm
getInvoiceFacts, by the agent
3:42:53 pm
Model call handle_request, 1.0 s
3:42:53 pm
getConfirmedKnowledge, by the agent
3:42:54 pm
Model call handle_request, 0.9 s
3:42:54 pm
calculateExtension, by the agent
3:42:56 pm
Model call handle_request, 1.7 s
3:42:56 pm
prepareApprovalTask, by the agent
3:43:19 pm
saveResponseDraft, by the app
Raw event log
```

## X28 — Packaging-time capture (NOT test evidence)
Captured 2026-10-18T05:23:09.789Z, about 30 minutes after testing ended, from the automation browser
while preparing this package. It shows the browser had been restarted (about:blank, different window
size and pixel ratio from the test session); only the browser build is likely to carry over.
```json
{"capturedAtUTC":"2026-10-18T05:23:09.789Z","url":"about:blank","browserVersion":"155.0.8059.80","userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36","language":"zh-CN","languages":["zh-CN","zh","en"],"devicePixelRatio":1.5,"innerWidth":1250,"innerHeight":891,"role":"n/a","nucleonCookieNames":[]}
```
