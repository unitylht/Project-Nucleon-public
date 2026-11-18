# Effort comparison: the old request pages and the desk

**Fictional data; mock agent; not a measure of real-world value.**

- Date: 2026-10-20
- Commit: `2b628ab`
- Script: `deploy/effort_compare.js`, on a fresh `deploy/ui_check_server.py` scratch server (mock agent, fictional sample, business date Fri 16 Oct 2026), in Chromium at 1366 × 900.

## Method

- Three scenarios, each run twice: on the old pages (the list view `#/cases` with its form, the case page `#/case/<id>`, Customers) and on the desk (`#/requests`).
- Each interface has its own fictional customer with the same invoices, so neither run sees the other's records: Rockpool Café (old pages) and Tidewater Café (desk). Each has two invoices of AUD 1,200.00 (DEMO-601 and DEMO-602; DEMO-701 and DEMO-702), due Tue 20 Oct 2026, still owed AUD 1,150.00 and AUD 800.00 as of Fri 16 Oct 2026.
- Each person starts signed in on their interface's starting page (`#/cases` or `#/requests`). Setup through the API is not counted: the customers, the invoices, the owner's paragraph and turning suggestions on.
- The path is the shortest a person would take on a desktop screen. On the old list view, staff find the form already open beside the list.
- Counted per person: messages typed (the customer's message in the form or the desk's message box, and a question typed into the desk), taps or clicks, fields filled (every other typed field: dates, reasons, answers), pages opened (hash changes, including those the app makes after a send), and elapsed ms from the first action to the result on screen, including the mock agent's work. People involved: the roles that acted.
- **S1**, a complete request with no owner judgement needed: staff enter the customer's message (DEMO-601 or DEMO-701, asked for Fri 30 Oct 2026); the owner approves the date asked for.
- **S2**, a request needing one owner judgement, with context already given: the owner's paragraph ("…I would consider a small extension…"), confirmed beforehand in each interface's own place: a confirmed Knowledge note for the old pages, which the case page shows under "What you've noted", and a confirmed statement on the desk. Staff enter the message (DEMO-602 or DEMO-702, asked for Tue 10 Nov 2026, 21 days). Intended outcome: approve Tue 3 Nov 2026 (14 days). On the old pages the owner sets that date. On the desk the owner answers the agent's question with "Up to 14 days this time", uses the suggested date and approves.
- **S3**, staff ask what a customer owes. Old pages: Customers, then the customer, then read the "Still owed" cells. Desk: type the question, then read the answer card's "Still owed" cells.
- Correctness: the decision stored is the intended outcome and date (S1, S2); each invoice's "Still owed" cell shows the amount `/api/records` gives for that invoice (S3).
- Understanding: the final screen contains, as written, a sentence that states what was done and one that states what was not. The old customer page in S3 has no agent turn, so this does not apply to it. Whether a person understands the screen is for the Reading section.

## Results

| Scenario | Interface | Role | Messages typed | Taps/clicks | Fields filled | Pages opened | Elapsed ms |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| S1 | Old pages | Staff | 1 | 1 | 0 | 1 | 83 |
| S1 | Old pages | Owner | 0 | 3 | 1 | 1 | 155 |
| S1 | Desk | Staff | 1 | 1 | 0 | 1 | 70 |
| S1 | Desk | Owner | 0 | 3 | 1 | 1 | 222 |
| S2 | Old pages | Staff | 1 | 1 | 0 | 1 | 80 |
| S2 | Old pages | Owner | 0 | 3 | 2 | 1 | 183 |
| S2 | Desk | Staff | 1 | 1 | 0 | 1 | 67 |
| S2 | Desk | Owner | 0 | 4 | 2 | 1 | 247 |
| S3 | Old pages | Staff | 0 | 2 | 0 | 2 | 121 |
| S3 | Desk | Staff | 1 | 1 | 0 | 0 | 74 |

| Scenario | Interface | People involved | Correct | Intended | Stored or shown |
| --- | --- | ---: | --- | --- | --- |
| S1 | Old pages | 2 | yes | approve 2026-10-30 | approve 2026-10-30 |
| S1 | Desk | 2 | yes | approve 2026-10-30 | approve 2026-10-30 |
| S2 | Old pages | 2 | yes | approve 2026-11-03 | approve 2026-11-03 (suggestion: none) |
| S2 | Desk | 2 | yes | approve 2026-11-03 | approve 2026-11-03 (suggestion: accepted) |
| S3 | Old pages | 1 | yes | DEMO-601 AUD 1,150.00, DEMO-602 AUD 800.00 | DEMO-601 "AUD 1,150.00 Stated as of Fri 16 Oct", DEMO-602 "AUD 800.00 Stated as of Fri 16 Oct" |
| S3 | Desk | 1 | yes | DEMO-701 AUD 1,150.00, DEMO-702 AUD 800.00 | DEMO-701 "AUD 1,150.00 Stated as of Fri 16 Oct", DEMO-702 "AUD 800.00 Stated as of Fri 16 Oct" |

## Work shifted

Actions are messages typed + taps/clicks + fields filled.

| Scenario | Staff actions, old pages | Staff actions, desk | Owner actions, old pages | Owner actions, desk |
| --- | ---: | ---: | ---: | ---: |
| S1 | 2 | 2 | 4 | 4 |
| S2 | 2 | 2 | 5 | 6 |
| S3 | 2 | 2 | – | – |

## Understanding

| Scenario | Interface | Role | Says what was done | Says what was not |
| --- | --- | --- | --- | --- |
| S1 | Old pages | Staff | "With the owner for a decision." | "Nothing for you to do yet." |
| S1 | Old pages | Owner | "Approved. New payment date: Fri 30 Oct 2026." | "Not sent." |
| S1 | Desk | Staff | "With the owner for a decision." | "Nothing for you to do yet." |
| S1 | Desk | Owner | "Approved. New payment date: Fri 30 Oct 2026." | "Not sent." |
| S2 | Old pages | Staff | "With the owner for a decision." | "Nothing for you to do yet." |
| S2 | Old pages | Owner | "Approved. New payment date: Tue 3 Nov 2026." | "Not sent." |
| S2 | Desk | Staff | "With the owner for a decision." | "Nothing for you to do yet." |
| S2 | Desk | Owner | "Approved. New payment date: Tue 3 Nov 2026." | "Not sent." |
| S3 | Old pages | Staff | not applicable: no agent turn | – |
| S3 | Desk | Staff | "What Tidewater Café owes, as the records show it on" | "The agent only chose the question and the customer." |

## Reading

_For a person to fill in after reading the final screens (the screenshots in the script's output directory): does each screen make clear what was done and what was not, and who did the work? Not filled in by the script._
