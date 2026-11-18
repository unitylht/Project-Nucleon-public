# Fictional sample files

All names, numbers and amounts are made up for demonstrations and tests. None comes from a real business.

| File | Shape | What it shows |
| --- | --- | --- |
| `invoices-list.csv` | Invoice list (day/month dates, balances as of a date you confirm) | Two customers share invoice number INV-1001; one row has an impossible date (31/02) and is rejected |
| `payments-list.csv` | Payments received | A partial payment (600.00 on a 1,000.00 invoice); an overpayment (500.00 on a 400.00 invoice, so 100.00 stays unallocated); an unreferenced payment; a reference to an invoice that belongs to a *different* customer (never allocated across customers); a rejected row |
| `decision_memory_fictional.json` | Fictional decision memory for the Adaptive Decision Authority demonstration (`python3 prototype/delegation_demo.py --db PATH [--with-policy]`) | Reviewed credit cases, each `fictional: true`, in `fictional_example` (retrieval) and `fictional_evaluation` (held out; a policy is back-tested on it, a SIMULATION) |
| `payments-overlap.csv` | Payments received, a later export | Overlaps `payments-list.csv` (two rows already imported, one unreferenced) and adds one new payment |

Typical order: import `invoices-list.csv` (create the customers it doesn't know), then `payments-list.csv`, then `payments-overlap.csv`.

## Complete records (typed in after the imports)

Opening balances and completeness statements are entered on the Records page; there is no file for them. With the three files imported (invoice amounts as of 9 October 2026):

1. **Opening balance for Bayside Café:** AUD 1,400.00 owed as at 9 Oct 2026, from "Accountant's balance list". Under credits, choose "It includes none".
2. **Confirm what it is made of.** Bayside's two invoices were still owed 1,000.00 + 400.00 on 9 Oct. **Needs attention** therefore suggests them, but only as a suggestion: a missing invoice and a missing credit would add up just as well. Choose **Yes, all of them are part of it**.
3. *(Optional)* **Coastline Foods:** AUD 1,500.00 as at 9 Oct. Its invoices add up to 1,250.50, so **Needs attention** asks about each one; leave them unanswered.
4. **Bayside's unreferenced 250.00 (14 Oct):** allocate it to Bayside's INV-1001. That is a person's choice; nothing allocates it automatically.
5. **The 100.00 left from EFT 7790:** choose **Not for an open invoice**, with a reason such as "Credit kept for the next order".
6. **As the owner, under Completeness:** Bayside Café, payments received, from 10 Oct 2026 to today, "Checked against the bank statements", and tick the confirmation.

Bayside's INV-1001 then shows **AUD 150.00, exact**. Leave out step 1's credits answer, or step 2's confirmation, and it stays "at most", with the reason. Here the amount is 1,000.00 still owed on 9 Oct, less 600.00 and 250.00 allocated after it. INV-1002 is settled. Any Bayside payment dated in that period and recorded afterwards ends the statement, and the amount goes back to "at most".
