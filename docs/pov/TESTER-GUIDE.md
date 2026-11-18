# Nucleon tester guide

Thank you for helping us test. This guide is for the **Owner** and **Staff** testers. You do not need any technical knowledge. Please read the whole guide once before your session. Updated 12 November 2026.

New to the demo? Read the one-page introduction to the fictional customers first: **Nucleon Demo Data**, https://claude.ai/artifact/5cjXfWe67PBNsCjktNk8b2

## What Nucleon is

Nucleon is an assistant for a small business that sells to customers on credit. Staff tell the assistant what a customer is asking for (for example, a new customer who wants stock on 14-day terms). The assistant checks the request against the limits the Owner has set, then either approves it within those limits, asks Staff for missing information, or passes it to the Owner. Nothing is ever sent to a customer: Staff and the Owner stay in charge.

## Please remember

- **All data is fictional.** The customers, amounts and references in this test are made up. Please do not enter anything real.
- **Nothing is sent to any customer** and no real credit is approved.
- **The assistant can be slow.** The decision card usually appears in 10-20 seconds and the full reply in 30-60 seconds. Please wait.
- **The assistant can word things badly or wrongly.** It is an AI. The **green or amber status card** under its message is the truth: it comes from Nucleon's own records and rules. If the text and the card disagree, believe the card.
- You are testing the product, not being tested. Tell us when something is confusing.

## Getting in

Use **Chrome or Edge** on a laptop or desktop. Please do not use a phone.

| What | Address |
| --- | --- |
| The assistant (chat) | https://creditease.dracooz.top |
| The Nucleon pages (policy, review, dashboard, records) | https://nucleon.dracooz.top |

Signing in has **two steps**, and each address asks for both:

1. **Email code (the gate; a temporary PoV measure, not part of the product).** Enter the email address we invited. You receive a one-time code by email, usually within a minute (check spam). Type the code in. This step is the same for both addresses.
2. **The app itself.**
   - On the **assistant** you sign in with the LibreChat account we created for you.
   - On the **Nucleon pages** you choose your role (Owner or Staff) and enter your access code.

You will receive your login details separately, in a different message from this guide. If a step does not work, tell the facilitator straight away.

## Which journeys are yours

- **Staff:** Journeys 1, 2 and 3 (you talk to the assistant).
- **Owner:** Step A (set the limits) first, then watch or do Journeys 1-3 if you wish, then Steps B, C and D.

In your session the facilitator will tell you which ones to do. If you do both roles, do Step A before Journey 1.

## Step A (Owner): set the limits

Open the Nucleon pages. The Home page offers **Quick setup**: a few plain questions about requests for more time to pay, with a preview of what the assistant would do with the open invoices before anything is saved. Answer them as you would for your own business and press **Save these rules**. Three things are always true: Nucleon never contacts your customer, you can reverse any decision the assistant makes on the **Decide** page, and you can pause the assistant at any time on the **Control panel**.

Quick setup covers payment extensions only. The three journeys below also use credit for new customers, so for them the facilitator will load the demonstration rules, or you can enter them yourself on the **Control panel**: the full table ("The starting rules") is in the Nucleon Operating Manual, section 6, https://claude.ai/artifact/SnzMe62Q8jAAs5uXbanD44. Each save makes a new version, so nothing is lost.

## The three practice journeys (Staff)

Open the assistant from the **Assistant** link in the Nucleon menu (it opens the right assistant for your role) and start a **new chat for each journey**. Copy each message exactly. Each journey can be run once; asking again returns the stored result.

### Journey 1: Northside Cafe, a new customer with a deposit

Type:

> Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit.

Wait for the decision card and read it from the top. **You should see:** *Approved* under policy version 1. The order of $800 less a verified deposit of $200 (reference DEP-NS-01) leaves $600 exposure, which is within the $600 limit for a new customer. Every limit it was checked against is listed. Nothing is sent to the customer: you would tell them yourself.

If you see an early card saying "Would be decided ... preview, not decided", wait: that is not the decision.

### Journey 2: Harbourline Catering, too big for the agent

Start a new chat and type:

> Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms with a deposit.

**You should see:** the request is **sent to the Owner** and nothing is approved. The order of $5,000 less a $1,000 deposit leaves $4,000 exposure, over the $1,000 limit for a single decision. The card shows which limit was not met.

### Journey 3: Lakeside Kiosk, information is missing

Start a new chat and type:

> Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.

**You should see:** an amber card asking Staff for information, because Nucleon has no record of a deposit or of the business's identity. It does **not** go to the Owner. Scroll down the card and press **Provide information in Nucleon**. A form opens in a new tab. Fill it in:

| Field | Value |
| --- | --- |
| Amount received | 150.00 |
| Date received | 23/10/2026 (type it or use the date picker) |
| Payment reference | DEP-LK-FICT-01 |
| How you know | I saw it arrive in the bank account |
| Business registration number | ABN 51 824 753 556 (fictional) |
| Trading name | Lakeside Kiosk Pty Ltd (fictional) |
| How you know | On a document |

Press **Submit information** and scroll to the top. **You should see:** Nucleon checks again: $600 less $150 = $450 exposure, within the limits, so it is approved. Staff only confirm what they saw themselves; that record is labelled as Staff-checked, not as a bank receipt.

## Owner steps after the journeys

**Step B: Decide page.** Open **Decide**. You see the decisions the assistant made on its own (Northside, Lakeside) and the cases waiting for you (Harbourline), each with a one-line reason. For each decision made by the assistant choose **Agree**, **Disagree** or **Override**, and give a reason. For Harbourline, choose **Approve** or **Decline** and write a reason. Try the Pause switch on the Control panel afterwards, then switch it back.

**Step C: Case timeline.** Open any case from the Decide page. You see its history in order: request, evidence asked and given, the check against the policy version, the decision and who made it, your feedback, and the repayment outcome. The outcome reads **pending** until a real repayment is seen; pending is not the same as paid on time or late.

**Step D: Dashboard.** Open **Dashboard**. You see how many requests the assistant handled within your limits, how many came to you, how many you overrode, and how long things took. Each tile says where its number comes from. Tell us what you would want it to show.

## If something goes wrong

- **The assistant repeats itself, loops or shows an error:** send the same message again once. If it still fails, tell the facilitator and we will move on. This is a known weakness of the AI model, not something you did wrong.
- **The assistant asks a question instead of deciding:** it never guesses an invoice or a date. Answer it, giving the invoice number and the date in one message, or send the exact message above again.
- **You press Approve or Decline and nothing happens:** a short reason is required. Type a few words.
- **A card button opens a login page:** sign in to the Nucleon pages as Staff, then press the button again.
- **A case says it was already handled:** it was run before. Tell us and we will reset the data.
- **Anything else:** tell the facilitator what you were trying to do and what you saw. Screenshots are welcome.

Please say out loud what you are thinking, especially when something surprises you or you are unsure whether to trust it.
