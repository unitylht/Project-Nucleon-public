# Demo script: the four-minute core demonstration (fictional data)

For the presenter and the backup recorder. Everything here runs on the Nucleon Lab with the local Gemma model and the AI Agent testing login (one code, Staff and Owner roles in one session). All names, invoices and amounts are fictional or anonymised. Replies to customers are drafts; nothing is sent. Recommendations come from the fixed calculation and the owner's policy checks; no approval predictor runs.

Timings below are observed on isolated rehearsal workspaces on 24 October 2026 (see "Observed timings"); they are not estimates presented as measurements. Final presentation recording and the final demonstration-state preparation are separate steps after independent review.

## Starting conditions

- A workspace in VND with the team ledger imported (the cleaned workbook, 21 customers, 137 invoices, 113 payments, 4 opening balances, 57 allocations) and the owner's limits set: staff may approve up to 14 days, only when nothing else is overdue, up to VND 500,000,000 outstanding, 2 concern rounds.
- No open request yet on invoice 00000087 (Customer 0011) or 00000079 (Customer 0001). The business date is Fri 23 Oct 2026 (the rehearsal date; adjust the dates below if the demonstration state is prepared on another business date).
- The browser is signed in with the AI Agent code, Lab in the General thread, Staff selected, zoom at 110%. The records page is open in a second tab. Do not spend demo time on login. Optional presenter panel: add `?presenter=1` to the Lab address (or press Ctrl+Shift+P) on a fictional workspace; it shows the current step, fills the exact message into the composer (you still press Send), opens the right case by invoice number, switches the role through the normal buttons, warms the model and shows the build and business date. It never presses Send, Act or Confirm. It sits in a right-hand column beside the Lab and does not cover the composer, so it can stay open while recording. Its **Keep warm** toggle asks the Lab server to keep the model loaded for the next 10 minutes (renewed every minute while ticked): the server sends one tiny model request 30 seconds after the previous one ended, never two at once and none while the Lab is answering, and writes nothing. The line under the buttons says whether the model is ready: "Model ready: last warm-up at 14:02:31 took 0.3 s" only after a warm-up succeeded within the last minute; "Warming the model…", "Not ready: the warm-up … failed" or "Paused while the Lab is answering" otherwise. A ticked box alone does not mean ready.
- The local model serves **one request at a time**, so nothing else may use it during the demo. Measured 24 October (evening): every slow Lab turn (30–220 s) and every slow one-word probe coincided, to the second, with a generation by another application on this network using the same model (a chat front-end; generations of 30–220 s every one to four minutes); with nothing else using the model a Lab turn took 4–19 s. Before the demo, stop that application or point it at another model, and check that the presenter panel's line reads "Model ready". The earlier explanation (the model paged out after about 90 s idle) was wrong: the afternoon's slow requests also coincided with that application's generations. Keep warm stays useful as a readiness signal: it reads "slow, not ready" while a warm-up has waited more than 5 s for the model, which is what a busy model looks like. Quit memory-heavy applications as well; the model holds about 17–20 GB of the machine's 32 GB.

## The timed script (target 3:45, ceiling 4:00)

Seven messages, one Act, one Confirm, one look at the saved calculation. Speak the *during* line while the Lab answers and the *after* line once the card is there; each after line is 3–8 s. The optional steps at the end are not part of the timed run.

Intro (5 s): "Two requests came in this morning. First, a routine one."

### Journey 1: a routine request

1. **Staff**, General thread. Paste exactly:
   > Customer 0011 just called about invoice 00000087. They said: "Could we pay it on 6 November instead of the 30th? Our transfer run is on Fridays." Please open the request.

   *During:* "Staff paste the customer's words; the agent finds the customer and the invoice and opens a case." Expected: "Request opened" card with 00000087 · Customer 0011 · Fri 6 Nov 2026 · With the owner; a new thread in the sidebar. *After (4 s):* "The case is open and in the queue. Nothing is decided."
2. Click the thread **00000087 · Customer 0011** (or the panel's Open case). Paste:
   > What do the numbers say? Is 6 November something I can agree to myself?

   *During:* "Every figure comes from code over the ledger; the model only explains it." Expected: the Assessment card: VND 15,369,999 owed, nothing overdue, due Fri 30 Oct; the owner's limits all Pass (7 ≤ 14 days; VND 15,369,999 ≤ VND 500,000,000); "Within the limits the owner set"; **Act within authority**. *After (6 s):* "Seven days, nothing else overdue, well under the limit: inside the owner's rules, so staff may act."
3. Press **Act within authority** → **Yes, record it**. Expected: "Approved to Fri 6 Nov 2026 · by AI Agent (as staff), within the limits the owner set"; "It followed the recommendation." Open **Calculation details** under the decision (the saved basis): point at the as-of date and `calc-v1`, the invoice row, and the policy checks with actual value and threshold; close it. *After (8 s):* "Staff decided within the owner's authority. This is the calculation the decision rested on, saved with it. The reply to the customer is a draft; nothing is sent."

### Journey 2: an exception

Click **General**. "Now an exception."

4. **Staff**, General thread. Paste:
   > Email from Customer 0001 about invoice 00000079: "Sorry this one is late. Could we pay invoice 00000079 on 2026-11-15? Our main client pays us on the 12th." Please open the request.

   *During:* "This customer is already late and wants five more weeks." Expected: the request-opened card for 00000079 · Customer 0001. *After (2 s):* "Opened."
5. Click **00000079 · Customer 0001**. Paste:
   > They've been with us a long time. Run the numbers: can I give them until 15 November, or does this one have to go up to the owner?

   *During:* "Same calculation, same rules." Expected: 34 days after the due date, beyond the 14-day limit; VND 57,240,000 overdue; "Escalate to the owner"; no Act button. *After (6 s):* "Thirty-four days is beyond the owner's fourteen, so it goes to the owner. Staff get no button to approve it."
6. Press **Owner** in the header (the case stays open). Paste:
   > Staff should ring them, confirm the exact date their client pays them, and come back to me with it before I decide.

   *During:* "The owner doesn't decide yet: they send it back with an instruction." Expected: header "Waiting on staff"; a card with the owner's words. *After (5 s):* "Now it waits on staff. The records track who acts next."
7. Press **Staff**. Paste:
   > Rang them just now. Their client pays them on 12 November, so they can pay us on the 13th. Please pass that back to the owner.

   *During:* "Staff ring the customer and report back." Expected: "The owner will see it on the case." Header back to "With the owner". *After (3 s):* "Back with the owner, as a reply."
8. Press **Owner**. Paste:
   > Approve it to 13 November. Reason: their client pays them on the 12th and they have paid every earlier invoice in full.

   *During:* "The owner approves to the 13th, with a reason." Expected: the prepared card "Approve to Fri 13 Nov 2026 · 00000079 · 32 days after the current due date … Reason to record: … · Nothing is decided until you press Confirm". *After (4 s):* "The agent only prepared it. Nothing is decided until a person presses Confirm." Press **Confirm**. Expected: "Approved to Fri 13 Nov 2026 · by AI Agent (as owner)"; the earlier answer's words fold under "What the Lab said at the time", with a line saying it was approved. *After (6 s):* "Approved by the owner, with the reason and the calculation saved. The reply is again a draft."

Close (4 s): "Routine cases stay with staff, exceptions reach the owner, and every decision is a person's."

### Optional, outside the timed run

- After step 5, staff raise a concern: "I'm uneasy about this one: the invoice is already 11 days late and they want another five weeks on top. Can you flag that to the owner for me?" (expected: "The owner will see it on the case. Nothing is decided."; the concern in the case header).
- Before step 6, the owner asks for information only: "Before I decide anything: how has this customer paid us over the year, and how do 8 November and 15 November compare for this invoice? Information only, don't prepare a decision." (four payments; 27 and 34 days; nothing prepared), or keeps the decision with guidance: "Guidance for staff on this case, not a decision yet: do not record their promised payment as received until the bank confirms it. I still have to decide this one myself." ("Still with the owner").
- At the end, as staff: "Why was this approved, and what exactly did the owner record?" (the reason quoted verbatim).

## Making the agent's work visible

Open the **Activity** group under any answer: the tool calls in order (finding the customer, opening the request, working out the numbers, checking the limits, preparing the decision). The **Records (n)** group shows what the agent read. The case header shows who holds the case now.

## Recovery path for a slow or failed model call

- A turn normally takes 4–20 s. If "The Lab is answering…" lasts more than 30 s, the model is almost certainly busy with another application's request (it serves one at a time); the presenter panel's line then reads "Not ready: the model has not answered …". Say: "the local model is busy; the records already hold the case" and open the records tab (Requests → the case): the request, its assessment and the Act/Confirm buttons are there without the model. The answer still arrives once the model is free; do not send the message again.
- If a turn fails, read the recovery card first: it lists what the records did during the turn (for example "Opened request 00000084 for Customer 0018" or "Saved the owner's guidance"), what failed and what is uncertain. Press **Refresh from the records** on that card. Do not send the same message again on the assumption that nothing happened: a request or guidance may already be saved. If the card shows that the write did not happen, send the message once more; the same message in the same thread is answered from the store and cannot write twice.
- If the model is down, the records page alone carries Journey 1 (the case page shows the assessment and the Act button) and the owner's Confirm on an already prepared decision. Say so plainly; do not pretend the model answered.
- If a backup recording has been made (checklist below), switch to it if two turns in a row fail; do not present it as a live answer. None exists at the time of writing.

## Backup-recording checklist

1. Record on an isolated rehearsal workspace prepared the same way (not the shared Lab), with the timing table filled from that run.
2. Full screen, 110% zoom, the Lab tab and the records tab only, no other windows; the agent code typed before recording starts.
3. Record Journey 1, the Calculation details expansion and Journey 2 in one take; keep the Activity group open once.
4. Check afterwards that no access code, no private workbook and no personal name appears in the frame.
5. Note the commit shown in the Lab footer or the records "Technical" tab and the business date in the recording's notes.

## Observed timings

The timed script above, five attempts on 24 October 2026 (evening), each on a fresh isolated workspace (start empty, settings, limits, the cleaned workbook imported through the Lab; not timed), Lab `a8ab624`/`0d54e9f`, local Gemma through LM Studio, Keep warm on. The browser was driven at operator pace: the presenter panel filled each message and Enter was pressed; each *during* line was spoken while the Lab answered and each *after* line once the card was shown, at 150 words a minute; the waits for each case to appear in the thread list, the role switches, Act, the saved-basis expansion and Confirm are all inside the time, from the first intro word to the last closing word.

| Attempt | Total | Lab turn times (s): open, numbers, open, numbers, send back, reply, approve | Result |
|---|---|---|---|
| 1 | stopped | 4.4, then the records' own preparation of the case timed out (128.8 s) and it ended "needs information" | failed |
| 2 | 6:50 | 4.4, **221.1**, 10.4, 15.4, 15.4, 13.9, 15.9 | failed |
| 3 | 5:57 | 4.9, 12.9, **156.2**, 14.9, 14.9, 13.9, 19.0 | failed |
| 4 | **3:22** | 4.4, 14.0, 10.4, 16.4, 15.0, 13.9, 17.0 | **within 3:45** |
| 5 | **3:29** | 6.4, 12.9, 10.9, 16.4, 15.9, 13.9, 19.0 | **within 3:45** |

Every slow request (attempts 1–3) was queued behind a generation by another application on this network that uses the same model (a chat front-end; its proxy log shows generations of 30–220 s every one to four minutes that evening, each matching a stall to within seconds). Attempts 4 and 5 were started after five quiet minutes and no such generation overlapped them. Without that contention the script takes about three and a half minutes; with it, any single turn can take two to four minutes. Waiting for each new case to appear in the thread list (the records prepare it with the same model) took 8–23 s per case and is included.

Earlier figures (24 October, afternoon): two rehearsals of the longer script, 4:23 and 4:29. The "first request after about 90 s idle costs 50–200 s" explanation given then is withdrawn: the afternoon's slow probes also coincided with that application's generations, and a probe after 120 s idle was fast.

## What not to claim

- No approval predictor runs; the trained classifiers are not part of the product. Recommendations come from the calculation and the owner's limits.
- No validated approval-confidence percentage exists.
- Replies are drafts; nothing is sent to customers.
- The raw accounting export is not importable as exported (no credit terms, grouped rows); the cleaned workbook is. Netting and adjustment rows are left out, so two customers do not reconcile to the ledger (documented).
- Technical tests do not measure business time savings.
