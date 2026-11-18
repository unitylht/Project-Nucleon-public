### Open issues after the live test of 11 November (not fixed)

Found by 21 real conversations with both assistants on the real-data instance and by walking every page as the Owner and as Staff. The data was restored to its snapshot afterwards. None of these produces a wrong approval; the one that did (a vague "more time" request, guessed and approved) was fixed the same night.

| # | Where | What happens | What to do meanwhile |
| --- | --- | --- | --- |
| 1 | Owner's assistant, "What is waiting for my decision?" | The answer shows internal field names and lists only some of the waiting cases (it named 2 of 8). | Use the Decide page. The count on "Decide" in the menu is right. |
| 2 | Owner's assistant, "What are my current rules?" | It describes which rules sent requests to the Owner, not the values of the rules, and speaks of "the Owner" in the third person. | Read "Current policy" at the top of the Control panel. |
| 3 | Staff assistant, a customer who is not in the records yet | It asks Staff for a customer id. It should say: add the customer under Customers first. | Add the customer (and the invoice or order) under Customers, then ask again. |
| 4 | Staff assistant, a customer who "cannot promise a date" | It still recommends "approve once the information is confirmed", so the request comes to the Owner. The agent's own decline applies only when the assistant recommends declining. | The Owner decides it. Expect fewer agent declines than the decline lines suggest. |
| 5 | A vague "more time" request | The new safeguard looks at one message. A follow-up that gives the invoice but still no date was not tested. A request that gives a date but no invoice is asked about even when the customer has a single open invoice. | Give the invoice number and the date (or number of days) in the same message. |
| 6 | Policy, a customer with invoices but no payment recorded yet | Counted as "a customer with no earlier receipts". With trial credit off that limit is 0, so every such request comes to the Owner, and the reason reads "over the limit of VND 0". | Expected under the current policy; the wording is confusing. Turning trial credit on with a limit changes it. |
| 7 | Decide page | Approving a waiting request needs a reason typed in (it is labelled "required"). An owner may find this one step too many. | Type a few words. The reason is what the similar-cases list and the model learn from. |
| 8 | Wording to the Owner | Home notices and the request page still say "the Owner delegated" and "The Owner decided" to the Owner themselves. A Staff notice shows a date as 2026-12-25. | Cosmetic. |
| 9 | Records | Several customers have payments not matched to invoices (for one customer more than the total they owe), and no customer's records are confirmed complete. Amounts owed are therefore "worked out", and the cards say so. | The Owner confirms a customer's records on the Customers page; until then totals are what the records show. |
| 10 | Model page | It shows no agreement figure until cases are decided after a model is fitted. The Dashboard's agreement figure is a different measure (how often the Owner agreed with the agent). | Not a fault; say which figure you quote. |
| 11 | Business identity | An ABN is checked for typing mistakes only. Nucleon does not look it up in the register or fetch related businesses; the link opens the register for a person to read. | Staff look it up and say where they saw it. |
| 12 | Phone layout | Not re-tested after the menu change. The Home page's automated check has four expectations that still describe the old menu. | Test on a laptop for now. |
| 13 | Demo data | **Changed 12 Nov, about 13:10:** the public address now shows the fictional demonstration data again (clean: no policy saved, nothing decided), and both assistants work on it. The real-data instance is off the public address; a full backup of the owners' session was taken first. | The scenarios in the manual work on the public address. Real-data testing needs the instance switched back. |

**After the session with the owners (12 November).** Fixed and re-tested the same day: the requested date recorded wrongly (31 December became 1 December), the chat card headed "STATUS UNAVAILABLE" for an agent decline, and "15-day" not being read as a number of days (details in section 6.5). Still open from that session:

| # | Where | What happens | What to do meanwhile |
| --- | --- | --- | --- |
| 14 | Customer names | The real-data records hold "Customer 0010", not the business's real name, so the assistant cannot find a customer by its real name and asks. | Use the customer number, or import the real names. |
| 15 | Business date | The system's date can be one day behind the tester's own date just after midnight in Sydney. "15 days" then lands one day earlier than the tester expects, and the assistant asks which date is meant. | Give the date itself, not a number of days, when the exact day matters. |
| 16 | Owner's first use | The owners found the Owner side overwhelming and needed an interpreter; many elements were not clear without explanation. Quick setup and the reworded Control panel (11 Nov) were not tested with the owners alone. | Not solved. It is the main next step. |
| 17 | Test records | The three benchmark cases of the session (Customers 0010, 0011, 0014) are kept in the real-data instance and in its full backup, as evidence. The real-data instance is no longer public. | Nothing to do until the report is written. |

**Fixed on 12 November (afternoon), re-tested with nine real conversations on the fictional data.** From the tables above: 1 (the Owner's assistant now lists every waiting request in plain words), 2 (it now states the rules in force), 4 (a customer who cannot commit to a date is recommended for decline), 5 (a second message that still leaves out the date is asked about), 6 (the "limit of VND 0" sentence now says that credit for customers with no payment on record is off), 8 (the Owner's pages say "you"), 12 (the Home check follows the new menu, phone tab bar included, 61 of 61). Also after the owners' session: the wrong date, the "status unavailable" heading and "15-day".

**Still open, and why.**

| # | Issue | Why it is not fixed now |
| --- | --- | --- |
| 3 | For a customer who is not in the records the Staff assistant now asks "which customer?" and says it was not found, but does not always add "add it under Customers first". | The instruction is in the tool's answer; the local model does not always repeat it. |
| 7 | Approving a waiting request needs a typed reason. | A design choice: the reason feeds the similar-cases list and the model. Making it optional is a product decision. |
| 8b | A Staff notice shows a date as 2026-12-25. | That sentence is also read by the form-path parser; changing its format needs its own test round. |
| 9, 14 | Payments not matched to invoices; records not confirmed complete; real names replaced by numbers. | These are properties of the imported data, not of the program. |
| 10 | The Model page shows no agreement figure until cases are decided after a fit. | Working as designed. |
| 11 | The ABN is not looked up in the register. | Needs a registered access key and sends identifiers to an outside service. |
| 15 | The system's date can be a day behind the tester's own date. | The date follows the business's time zone setting, which is unconfirmed for NTK. |
| 16 | The Owner side is too much to take in at first. | The main open product problem; not a quick fix. |
| 18 | An invoice number that two customers share must be chosen by its id, and the assistant's question about it is confusing. | The rule is a deliberate safeguard; the wording of the question is the model's. |
