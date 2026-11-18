# Owner test playbook

For the team member who runs a test session with a business owner. Updated on the evening of 12 November 2026 for the system as it is now (Get started, the three levels, the three display levels, shorter menu, "Decide" page, Quick setup, the Doctor, the reworded Control panel). All data in the session is **fictional**. Never put access codes, passwords or tokens in a chat message, a note or the repository.

## The one question this session should answer

At the session of 12 November the owners said the product works and the Staff side is easy, but that the Owner side is too much to take in at first: they needed someone to explain and to click for them. Since then the menu was shortened, the Control panel was reworded and Quick setup was added. Nobody has yet watched an owner try these **alone**.

So the main question is: **can the owner set the rules and decide a request without you explaining?** Everything else is secondary. The most useful thing you can do is stay quiet in Part 1 and write down where the owner stops.

| We are testing | We are not testing |
| --- | --- |
| Can the owner set up rules alone with Quick setup, and predict what the agent will then do? | Real credit policy (all values are fictional) |
| Does the owner understand each result: who decided, why, and how to reverse it? | Whether the decisions match the owner's own customers (the demo has six made-up ones) |
| Which words, pages or numbers make the owner stop or ask? | The speed of the AI model |
| After the guided part: what would the owner delegate, and what never? | Messages to customers (Nucleon sends none) |

## What to send the owner the day before

1. The one-page introduction to the demo data, **Nucleon Demo Data**: https://claude.ai/artifact/5cjXfWe67PBNsCjktNk8b2 (who the six fictional customers are and what each will ask).
2. [TESTER-GUIDE.md](TESTER-GUIDE.md) (how to get in) and [CONSENT.md](CONSENT.md).
3. The sign-in details, by a **different channel** from the guide. The access codes were changed on 12 November; ask Hanting for the current DEMO codes. Old codes no longer work.

The full reference, if the owner wants to read more, is the **Nucleon Operating Manual**: https://claude.ai/artifact/SnzMe62Q8jAAs5uXbanD44

## 30 minutes before

Ask Hanting (he runs the machine) to confirm three things. Each takes under a minute.

1. The health check passes and the public site shows the **fictional** data. The line under the menu must say "Practice workspace with fictional data."
2. The data is **clean**: no rules saved, nothing decided. A request that was already decided returns its stored result, so a used data set spoils the session.
3. For Part 2 only: whether you want the **demonstration rules loaded for you** between Part 1 and Part 2 (one minute), or you will type them yourself from the manual.

Then, yourself:

- Open https://nucleon.dracooz.top in Chrome or Edge on a **laptop** and sign in as Owner. Open a second browser (or a private window) and sign in as Staff. You play Staff unless a staff member joins.
- From the Staff window, open **Assistant** in the menu once, so the chat is signed in.
- Have a stopwatch and a place to write. Start recording only after the owner agrees.

Things to know before you start:

- "Today" in the demo is **Saturday 24 October 2026** and does not move. Amounts are in AUD.
- The decision **card** under the assistant's answer is the result. The assistant's own sentences may vary.
- A card usually appears in 10 to 20 seconds and the whole answer in up to a minute.

## Part 1: first use, alone (about 25 minutes)

**Your role: observer.** Give the task, then stay quiet. If the owner is stuck for more than a minute, ask "what would you try?" before helping, and write down that you helped. Do not explain a page before the owner has looked at it.

### Task 1. Set your rules (Owner)

Say only: *"You want the assistant to handle the easy requests for more time to pay, and send you the rest. Please set that up."*

On clean data the Home page opens with **Let's get started**: three steps (how strict: Strict, Balanced or Relaxed; customers to keep; how much the pages show: Simple, Standard or Detailed), saved by the last button. **Quick setup** asks each question one by one instead, and the Control panel has every setting. All three are right answers; note which one the owner takes.

Write down:

- Time from the first click to "Save these rules".
- Which way did the owner go: Get started, Quick setup or the Control panel? (On 12 November an owner went to the Control panel first.)
- Which level and which display level did they pick, and did the preview beside the levels help?
- Every question the owner asks you, word for word, and which label or number it was about.
- Before saving, ask one thing: *"What do you expect the assistant to do with a request now?"* Write the answer down; you will compare it with what happens.

### Task 2. A request comes in (Staff, then Owner)

In the Staff window open **Assistant**, start a new chat and paste:

> Bayview Gelato Co asks to move the due date of invoice DEMO-301 from 18 October 2026 to 10 November 2026.

Show the owner the card. Ask: *"What happened, and who decided?"* Then ask the owner to find this request in their own window, without telling them where. (It is on **Decide**: at the top if it waits for them, under "Autonomous decisions to review" if the agent decided.)

Write down: did the result match what the owner predicted in Task 1? Did they find it? Could they say why it was decided that way?

### Task 3. Decide one yourself (Staff, then Owner)

New chat, paste:

> Riverside Foods asks for 10 more days on invoice DEMO-505.

This one comes to the owner whatever rules were saved, because this customer's records are incomplete (one invoice has no amount, one payment has no date) and the agent does not decide on incomplete records. Ask the owner to deal with it. Approving or declining needs a short reason typed in; if the owner clicks and nothing happens, that is why. Note whether they noticed without help.

### Task 4. Change your mind (Owner)

Say: *"Suppose you now want every request from Bayview to come to you personally. Make that so."* (The Control panel has it at the top under "Quick settings"; Quick setup has "Customers the agent must never decide for"; the Control panel form has it under Advanced.) Note where the owner looks first and how long it takes.

### Three questions to close Part 1

1. "What on these pages did you not need?"
2. "What did you look for and not find?"
3. "If you had to do this alone tomorrow, what would stop you?"

## Part 2: guided scenarios (about 20 minutes)

**Your role: guide.** Now you may explain. The aim is to show every kind of result and to hear what the owner would delegate.

The six scenarios, with the exact sentence to paste and the expected result of each, are in the manual, section 6 "Scenarios to try". They assume the **demonstration rules** (the table "The starting rules" in the same section). Quick setup only covers payment extensions, so for the new-customer scenarios these rules must be in place: ask Hanting to load them, or enter them on the Control panel and press Save.

Loading the demonstration rules resets the data, so Bayview and Riverside can be asked again.

| Scenario | Customer | What it shows |
| --- | --- | --- |
| 1 | Bayview Gelato Co, then Northside Cafe | The agent approves inside the rules; the owner reviews afterwards with one click |
| 2 | Lakeside Kiosk | Facts are missing: Nucleon asks **Staff**, not the owner, then approves |
| 3 | Harbourline Catering | Over a money limit: it comes to the owner with the reason |
| 4 | (the Harbourline request) | The owner declines, with a reason |
| 5 | opt-in | The agent may say no by itself when a request is far over a limit |
| 6 | any | Change one setting, send the same kind of request, see a different result |

After the scenarios, open **Dashboard** and the **Doctor** (both are on the Owner's Home page) and ask what the owner would want to see there.

Closing questions:

- "Which of these decisions would you let the assistant make alone in your own business? Which never?"
- "For one request like these, after the customer has given a final answer: how long does it take you today, and who is involved?" (On 12 November the owners said about one working day.)
- "What would you need to see before you trusted it with real customers?"

## What to write down, always

- Clock time at the start and end of each task, and when each card appeared.
- Every time you helped, and with what.
- Direct quotes, with the time. "It is confusing" is less useful than the exact words and the thing on screen at that moment.
- For each stop or question: the page, the label or number, and what the owner expected instead.

Do not defend the product. Ask what they expected and why.

## After the session

1. Stop the recording and keep it private. Do not upload it to shared storage.
2. Take screenshots of the Decide page, one request page and the Dashboard.
3. Tell Hanting the session is over, so the data can be reset for the next one. A backup is kept.
4. Write the session up the same day using [SESSION-LOG-TEMPLATE.md](SESSION-LOG-TEMPLATE.md). Say plainly which tasks the owner did alone and which with help.
5. Add de-identified observations to [FEEDBACK-REGISTER.md](FEEDBACK-REGISTER.md).

## If something goes wrong

| What you see | What to do |
| --- | --- |
| The assistant asks "which invoice?" or "until what date?" | It is meant to: it never guesses. Give the invoice number and the date in one message. |
| The assistant repeats itself, loops or shows an error | Send the same message once more. If it fails again, note it and move on. |
| The card says the request was already handled | The data is not clean. Ask Hanting to reset it (one minute). |
| A button on the card opens a sign-in page | That browser is not signed in to Nucleon as Staff. Sign in and press again. |
| The old access code is refused | Codes were changed on 12 November. Ask Hanting for the current DEMO codes. |
| The owner clicks Approve and nothing happens | A reason is required. Type a few words. |
| The assistant says a customer was not found | Check the spelling against the Customers page. A new customer must be added there first. |
| An answer takes more than 100 seconds | The connection cuts silent requests at 100 seconds. Send once more and note it. |
| Everything is unreachable | Message Hanting. The machine is a laptop; a restart takes a few minutes. |

## Known limits to be honest about

Say these if the owner runs into them; do not hide them.

- The assistant is a small AI model running on one laptop. It is slow and sometimes words things badly. The rules and the card come from ordinary code, not from the AI.
- An ABN is only checked for typing mistakes. Nucleon does not look it up; the link opens the public register for a person to read.
- The demo has six customers and small amounts. It shows how Nucleon behaves, not whether it would agree with the owner about their own customers.
- The email code at the door is a temporary measure for the test, not part of the product.
