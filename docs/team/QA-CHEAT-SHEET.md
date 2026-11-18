# Nucleon Q&A Cheat Sheet: Adaptive Decision Authority

For presenters. Short, true answers. "Isolated test stack" means a separate copy on the developer's Mac, with fictional data. It isn't the normal demo services and it isn't M6.

**Is the AI actually approving credit?**
Yes, for internal credit decisions inside limits the Owner set, and it is built and tested on the isolated stack.
- **What decides:** the AI recommends approval; Nucleon's backend code checks every limit and records the decision as effective.
- **What it doesn't do:** it never sends anything to the customer.

**What stops the AI approving something risky?**
- **Code, not the model:** the backend checks each bound against the records.
- **The bounds:** the amount per decision, the customer's total, all autonomous approvals in 30 days, days, overdue, late history and unusual size.
- **Unknown values:** an amount the records can't establish counts as *unknown*, never zero.
- **Owner controls:** the Owner can pause the agent with one click.

**Can the AI change its own limits?**
No.
- **Who can change them:** only the Owner, signed in as a person in the browser.
- **Who can't:** AI connections, Staff and service sessions are refused, and no tool can change the policy.
- **Suggestions:** Nucleon may *suggest* a change, but the Owner has to save it as a new version.

**Why not just let Staff approve?**
- **It moves the queue:** the bottleneck would move from the Owner to Staff.
- **Staff reluctance:** Staff don't want personal liability for credit decisions.
- **What Staff do instead:** they supply missing facts. They don't re-approve the AI's decisions.

**What about a brand-new customer with no history?**
- **Not automatically escalated:** with the Owner's limited trial credit turned on, a small exposure with a verified deposit can be approved by the agent.
- **No history isn't negative:** a missing history is not held against the customer.
- **Other customers' cases are analogies:** similar cases inform the decision, but they are never presented as this customer's history.
- **Larger exposure goes to the Owner.**

**Can a deposit Staff mention count as paid?**
Only as far as the Owner allows, and only if Staff say how they know.
- **Seen in the bank account or on a document:** labelled "checked by Staff", not a recorded payment. It counts only up to the Owner's limit for Staff-checked deposits.
- **"The customer said they paid":** kept, but never counts.
- **The ledger:** nothing Staff confirm is turned into a ledger payment.

**What does "verified" mean?**
- **Records:** for example, a deposit receipt recorded in Nucleon.
- **Staff confirmation:** Staff confirming on a Nucleon page, signed in.
- **What doesn't count:** the AI saying "they paid" is stored only as reported context, never as verification.

**Does it decline requests automatically?**
No. That's an open product decision. Anything that doesn't qualify goes to the Owner, or onto a policy hold for the Owner.

**How accurate is it?**
We don't claim real-world accuracy.
- **The track-record figure:** it shows how the current policy compares with a **fictional** Owner on a held-out **fictional evaluation set**. It's a simulation.
- **NTK data:** the NTK ledger has no record of Owner approval decisions, so no real accuracy can be calculated from it.

**Did you use Hoang's ML models?**
Not in this slice.
- **The scripts:** they predict proxy labels built from payment timing. Those are not real Owner decisions.
- **Possible future use:** they may be useful later for features or research, after an evaluation.
- **What the decision uses now:** deterministic financial calculations plus decision memory.

**What does "learning" mean here?**
- **Decision memory:** each case keeps its evidence, recommendation, decision, Owner feedback or override, and outcome.
- **Comparable-case retrieval.**
- **Owner-approved policy versions.**
- No model fine-tuning.

**Can the Owner undo an AI decision?**
Yes.
- **Override:** the Owner can override from the Owner page. For an extension, the due date goes back.
- **Audit:** the original decision and the override are both kept in the history.

**Does the AI email customers?**
No. Internal decisions are separate from external communication. Staff tell the customer. Every card says "Nucleon sent nothing to the customer."

**How long does a decision take?**
These are measured on this Mac, not estimated:
- **The card:** the authoritative decision card appears after about **10–21 seconds**.
- **The text:** Qwen's written reply finishes after about 30–60 seconds, because it double-checks.
- **Evidence:** after Staff submit evidence, the decision follows in about **4–5 seconds**.

**What if the chatbot says something wrong?**
- **The card shows the truth:** it shows the backend's own status, and the chat text doesn't change it.
- **Tested:** in testing, Qwen refused to claim approval when the backend said "with the Owner".
- **Not a guarantee:** its wording can still be loose (for example, the order amount instead of the exposure), so **trust the card**.

**Can an order be split into small requests to stay under the limit?**
No.
- **Trial credit:** a second trial credit for a customer whose first is in force goes to the Owner.
- **Customer total:** the cap counts the customer's whole recorded debt plus any credit lines in force.
- **30-day total:** a separate limit covers all autonomous approvals in 30 days.
- **Deposits:** a deposit can't be counted twice, or reused for a second trial.

**What about duplicate clicks or repeated requests?**
- **One decision only:** a repeat returns the stored decision, and parallel calls create one decision.
- **Trial credit:** a different trial for a customer who already has one in force goes to the Owner.

**Is it deployed?**
Locally, yes. Since 27 Oct the normal local M3 environment (`127.0.0.1:3080` and `:8631`) runs this version with fictional data.
- **Starting state:** advisory mode, so nothing is approved until the Owner saves a delegated policy.
- **Verified:** a real Qwen + LibreChat browser acceptance passed there (17/17 checks).
- **M6:** not deployed.

**Who is accountable?**
- **The Owner** sets and owns the policy.
- **Each decision** records whether it was the agent under policy vN or the Owner.
- **Logins are shared:** Staff and Owner use shared access codes, so the audit identifies roles, not individual people.

**What's next (roadmap)?**
- the Owner Console's Decision Handling overview;
- real Owner-reviewed cases (shadow mode) before widening limits;
- explicit permissions for outbound actions;
- possibly agent declines, once the Owner decides on them.
