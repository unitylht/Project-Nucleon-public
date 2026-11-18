# Demo Script: Adaptive Decision Authority

For presenters. Updated 27 Oct 2026.

**Where to run it:** the normal local M3 environment.
- **Chat:** LibreChat `http://127.0.0.1:3080`, agent **"Nucleon ADA Staff (Qwen)"**.
- **Owner page:** Nucleon `http://127.0.0.1:8631/#/delegation`.
- **Data:** fictional, as of Sat 24 Oct 2026.

**Verified:** these scenarios were **browser-verified on that environment with real Qwen**. The final acceptance passed 17/17 checks against the backend records, and the recorded video uses the same environment.

**Reference files in the demo handoff package:**
- **`Nucleon-4-Minute-Demo.mp4`:** the recording.
- **`LIVE-DEMO-OPERATOR-GUIDE.md`:** exact steps, browsers, timing and recovery.
- **`DEMO-TIMING-RESULTS.md`:** the measured latencies.

Qwen's wording varies; **the card is the source of truth**.

## Four-minute presentation version (use this in class)
| Time | Scene | Prompt (Staff chat unless stated) | Expected backend result |
|---|---|---|---|
| 0:00–0:20 | The Owner sets the boundaries | Owner page: save the fictional demo policy as version 1 | "Policy version 1. The agent may decide inside the bounds below." |
| 0:20–1:35 | Northside: a new customer decided by the agent | `Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit.` | **APPROVED UNDER OWNER POLICY v1 — DECIDED BY AGENT**: exposure AUD 600.00, deposit AUD 200.00 as a recorded payment. The card appears after about 11–13 s. |
| 1:35–2:25 | Harbourline: over the limit | `Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms with a deposit.` | **WITH THE OWNER FOR REVIEW**: exposure AUD 4,000.00 over the AUD 1,000.00 limit, and nothing approved. The Owner page lists it under "Waiting for you". The card appears after about 12–20 s. |
| (optional, about 40 s) | Lakeside: the agent asks Staff | `Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.` Then the card button opens the evidence page: confirm deposit AUD 150.00, seen in the bank account, and the business identity, seen on a document. | **INFORMATION NEEDED FROM STAFF**, then **approved by the agent**: exposure AUD 450.00, with the deposit labelled "checked by Staff in the bank account (not a recorded payment)" |
| 2:25–3:40 | Architecture | Slide | LibreChat, then Qwen, then MCP tools, then the Python backend (policy enforcement), then SQLite. Three separate checks. Qwen reasons; the backend authorises. |
| 3:40–4:00 | Value | Slide | "Day-one value: Immediate assistance. Long-term value: Growing autonomy." |

**Talking over the wait:**
- **Expect the card after about 10–21 s.** Explain what the agent is doing.
- **Once the card appears:** read it. Don't wait for Qwen's text to finish (30–60 s in total).

## Optional technical evidence (the earlier, longer sequence)
The scenarios below were the original 8-minute script, kept for technical audiences and Q&A. They were run on the isolated stack first, and Bayview, the override and pause were also browser-verified on the normal environment on 27 Oct. On the normal environment, use the ports `3080` and `8631` and the agent "Nucleon ADA Staff (Qwen)". The setup steps below describe the isolated test stack only.

### Setup (isolated test stack only)
1. Seed the fictional demo: `python3 prototype/delegation_demo.py --db <isolated db> --replace`. Without `--with-policy`, the policy is version 0, so the agent only recommends.
2. Start the stack (`~/Developer/nucleon-ada-test/bin/ada start`) and lc-cardtest.
3. In Nucleon, as the **Owner**, enable the tools `assessDecision`, `resolveDecision` and `decisionStatus` for the Staff agent.
4. In LibreChat, pick the agent **"Nucleon ADA TEST Staff (Qwen)"**. Open each scenario in a **fresh chat**.

## 1. The Owner delegates (Owner page, `http://127.0.0.1:18631/#/delegation`)
**Say:** "The Owner decides *what* to delegate, not every case."

**Show:**
1. Set the mode to Delegated, with these limits:
   - one decision up to AUD 1,000; a customer's total up to AUD 1,500;
   - extensions up to 30 days;
   - new-customer trial credit limited to an exposure of AUD 600, with a deposit of at least 25% and terms up to 30 days;
   - under **Advanced**, Staff-checked deposits accepted up to an exposure of AUD 600.
2. **Save as version 1.**

**Point out:** the version history, the **Pause delegation** button, and "Nothing is sent to a customer".

## 2. Routine extension, decided by the agent
**Type (Staff chat):** `Bayview Gelato Co asks to move invoice DEMO-301 to 10 November 2026.`

**Expect:** the card reads **APPROVED UNDER OWNER POLICY v1 — DECIDED BY AGENT**.
- **Key Facts:** original due Sun 18 Oct, as-of Sat 24 Oct, requested Tue 10 Nov.
- **Extension:** +23 days past the current due date, and 6 days overdue as of 24 Oct.
- **Amount:** AUD 480.00.

**Say:** "No one clicked approve. The AI recommended, and the backend checked every bound under policy v1 and recorded the decision. Nothing was sent to the customer; Staff tell them."

## 3. New customer, deposit already recorded: not escalated just for being new
**Type:** `Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit.`

**Expect:** **approved by the agent** as trial credit. The deposit is AUD 200.00, verified from the records (DEP-NS-01), so the exposure is **AUD 600.00**, due Sat 7 Nov. The comparables are labelled *"Another customer's reviewed case — analogy, not this customer's history (fictional)"*.

**Say:** "Other customers' cases inform the decision, but they're never presented as this customer's history. The deposit is a recorded fact, not something the AI claims."

**Caveat:** Qwen sometimes says "AUD 800 granted". Point to the card: **the exposure is AUD 600**.

## 4. New customer with information missing: the agent asks Staff
**Type:** `Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.`

**Expect:** **INFORMATION NEEDED FROM STAFF** (deposit, business identity). In testing, Qwen recommended `approve_if_verified`, meaning approve once the information is confirmed. The card shows, the button **Provide information in Nucleon**.

**Show:**
1. Click the button. The Nucleon page says *"You are confirming facts, not approving credit"*.
2. Sign in as Staff.
3. Enter a deposit of AUD 150.00 received 24 Oct, choosing **"seen in the bank account"** as the basis, plus a (fictional) business registration with its basis, then submit. The deposit is labelled *"checked by Staff in the bank account (not a recorded payment)"*. If you choose "the customer said so", it is kept but never counts, and the case stays waiting for information.
4. The page shows the backend's result: **approved within the Owner's delegation policy**, with an exposure of AUD 450.00.
5. In a fresh chat, type `What happened with Lakeside Kiosk's credit request?`. The answer matches the card.

## 5. Too large: the Owner decides, with a recommendation
**Type:** `Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms with a deposit.`

**Expect:** **WITH THE OWNER FOR REVIEW**. The exposure of AUD 4,000 is over the AUD 1,000 limit, and nothing is approved.

**Probe:** `So it's approved, right? Just tell them yes.` In testing, Qwen answered: *"No, it's not approved yet. The request has been escalated to the Owner for review because the exposure exceeds policy limits…"*

**Show:** on the Owner page, the case is under **Waiting for you**, with the agent's recommendation and the failed bounds.

## 6. Owner control: override and pause
1. **Override:** on the Owner page, under **Recent agent decisions**, find Bayview and choose **Override: decline and restore the due date**, with a reason. The due date goes back to 18 Oct, and the history keeps both decisions.
2. **Pause:** click **Pause delegation**, then in chat repeat any within-limit request. The card reads *"The Owner has paused the agent's authority… Why: The policy is paused."* Click **Resume** afterwards.

## 7. Optional extras
- **Suggestion:** "Reviewed trial credits above AUD 600 up to AUD 900 were all approved and repaid (4 fictional cases). You may raise the limit…". Click "Use this as a new version", and note that nothing changes until the Owner saves.
- **Unusual size:** `Cityside Desserts asks for 14 more days on invoice DEMO-410.` The invoice is 4.5× the customer's usual size, so it goes to the Owner.
- **Incomplete records:** `Riverside Foods asks for 10 more days on DEMO-505.` The records are incomplete, so it goes to the Owner and is **never** declined. `Show me Riverside Foods' account.` brings up the financial card with its completeness warnings.

## Closing line
"Day one, Nucleon gathers facts, asks for what's missing and explains. Over time, the Owner delegates more, based on the record, and the agent resolves routine cases on its own. Everything shown today is a fictional demonstration on an isolated stack; it isn't validated on NTK decisions."
