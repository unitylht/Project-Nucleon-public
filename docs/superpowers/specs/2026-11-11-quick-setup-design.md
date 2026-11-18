# Quick setup: an onboarding helper for the Owner's Control panel

Date: 11 November 2026. Status: approved by the user on 11 November 2026. No code is written yet.

## Why

On 10 November 2026 Hoang ran a session with the NTK owners. Setting up the Control panel took about one hour, with Hoang explaining. The owners said the product is very helpful if it works, but they fear the learning curve will send staff back to asking them. They asked for minimalism.

What the records of that session show:

- The owners changed about six settings out of more than thirty. The rest stayed at their defaults.
- Six scenarios were run afterwards. The agent approved none on its own: three went to the Owner, two were held, one was declined by the agent.
- A trial on a copy of that night's data (the copy was deleted afterwards) applied the owners' saved policy to all 20 open invoices, as if each customer asked for 14 more days from today. The agent could approve 0 of 20. Seventeen failed the day limit, because the invoices were already long overdue and days are counted from the due date. Sixteen failed "nothing else overdue", a default the owners never touched. Eight belong to the two held customers. Allowing other overdue invoices gave 2 of 20; also raising the day limit to 60 gave 9 of 20.

So the hour did not go on clicking. It went on understanding, and at the end the owners still could not see what their settings would do.

## Goal

An Owner who has never seen Nucleon can set a working first policy alone in about ten minutes, and sees what it will do to their own invoices before saving it.

The helper sits beside the Control panel. It does not replace it, hide it or remove any setting.

## Decisions already made with the user

- Scope: Owner setup first (this spec). Staff onboarding is a separate, later project.
- No LLM guesses the Owner's preferences. Every answer maps to settings by fixed code.
- For testing and the PoV the helper's default is that the agent decides from the first day, so the effect is visible at once. "Watch first" is offered as the second choice.
- Day limits: state clearly how each is counted, and offer limits for both readings.

## What the Owner sees

A new page, "Quick setup" (`#/quick-setup`), Owner only. It is linked from step 1 of "Where to start" on Home and from the top of the Control panel. It can be run again at any time.

One page, five parts, in order:

1. **Three assurances.** Nucleon never contacts your customer. You can undo any decision the agent makes. You can pause the agent with one button.
2. **How to start.** Three choices:
   - The agent decides from today, inside the limits below (default).
   - The agent decides after you have reviewed some of its recommendations and agreed with most of them.
   - The agent only recommends; you decide everything.
3. **The questions.** Each uses the Owner's own figures as a guide.
   - The largest invoice the agent may extend on its own. Shown with clickable amounts taken from the Owner's open invoices (for example the median and the largest), so nobody types ten zeros.
   - The most one customer may owe in total for the agent to decide.
   - The latest new payment date, counted from the day the request is received.
   - How late an invoice may become in total, counted from its original due date.
   - May the agent decide when the customer has other overdue invoices?
   - May the agent decide for a customer who paid late before? Three choices: yes; only when at most a quarter of their earlier payments were late; no. (Added while planning: the default for this setting is "no", which would block most customers without the Owner ever being asked.)
   - Customers the agent must never decide for, picked by name.
   - May the agent decline on its own a request that is beyond these limits, when the assistant recommends declining?
4. **The preview.** For every open invoice, what would happen if the customer asked today for N more days (N is a small choice, 14 by default):
   - how many the agent would decide, how many come to the Owner, how many are held;
   - the reasons, most common first, each with a link back to the question that controls it;
   - a few named examples of each group.

   The preview updates when an answer changes. It says plainly that it is an estimate: it assumes the assistant recommends approval and the customer asks for exactly N days.
5. **The summary and Save.** A short text in plain sentences: what the agent will decide alone, and what always comes to the Owner. Saving stores a normal policy version with the note "Saved from Quick setup". The page then links to the assistant ("try a request now"), to Review and to the Control panel for fine tuning.

Settings the helper does not ask about keep the value they have in the current policy, or the default when no policy was saved yet. The summary lists the ones that send requests to the Owner, so nothing is silent.

## Day limits

Today there is one limit, `extensions.maxDays`: the days between the invoice's current due date and the date asked for. Two problems were found.

- An Owner reads "30 days" as 30 days from today. An invoice already 29 days late that asks for 14 more days counts as 43.
- Because the current due date moves after each approval, a customer can ask again and again. A test on fictional data had the agent approve four 20-day extensions in a row on one invoice under a 30-day limit: 80 days in total.

Design:

- `extensions.maxDays` stays as it is. Its label and hint say how it is counted and give a worked example.
- New, optional `extensions.maxDaysFromRequest`: the new date may be at most this many days after the day the request was received. "Today" in the helper's question means that day. When a request is checked again later (for example after Staff adds information), the count still starts from the day it was received, so waiting never changes the answer.
- New, optional `extensions.maxDaysPastOriginalDue`: the new date may be at most this many days after the invoice's original due date. This closes the repeat-request gap.
- A request must pass every limit that is set. An empty limit is not used. A policy saved before this change has neither new limit and behaves exactly as before (same digest).
- The helper asks for the two new limits and sets `maxDays` to the same number as the total-lateness limit, so it never blocks anything the other two allow.
- The Control panel form shows all three, each with its counting rule.
- The agent-decline lines keep counting days from the current due date. The helper turns on at most that one line, with the same number as the total-lateness limit.

## How it is built

- **Preview: `POST /api/delegation/preview`**, Owner only, read-only. Body: a candidate policy and the days. The server validates the candidate with `delegation.validate_policy`, then for each open invoice builds the request with `dg_request` and calls `delegation.evaluate` with the candidate policy and an "approve" recommendation. It returns counts by handling, reasons with counts, and examples. It writes nothing: no case, no version, no event. Because it calls the same `evaluate` as a real request, the preview cannot drift from the real rules. Measured cost: 20 invoices in 0.1 seconds. The response is capped at 200 invoices, and says so when it cuts.
- **Guide figures: `GET /api/delegation/quick-setup`**, Owner only. Returns the current policy, the customers (id and name), and the amounts used as clickable choices, from the existing helpers `_amounts` and `_base_amount`.
- **Saving** uses the existing `PUT /api/delegation/policy` with `expectedVersion`. No new write path.
- **The mapping** from answers to a policy lives in one pure function in `delegation.py`, `quick_setup_policy(answers, current)`, used by both new endpoints so the preview and the save agree.
  - "Decides from today": mode delegated, track-record minimums empty.
  - "Decides after reviews": mode delegated, track record on live cases with the default minimums (5 reviewed, 80% agreement).
  - "Only recommends": mode advisory.
- **The page** is a new file `prototype/web/quicksetup.js`. `delegation.js` and `home.js` gain one link each.
- **The new limits** touch `default_policy`, `validate_policy`, `features_of`, `risk_checks`, `dg_request`, the policy summary and the form.

## What can go wrong

- The candidate policy is invalid: the preview returns the same field error the form would, shown beside the question.
- The policy changed in another tab: the save returns the existing version conflict; the page reloads the current policy and keeps the Owner's answers.
- No open invoices: the preview says so and the helper still saves.
- Records that cannot be read for a customer: those invoices are counted under "come to you", with the reason the engine gives.

## Tests

- Unit tests for `quick_setup_policy` (each start choice, empty answers keep current values) and for each new day limit (pass, fail, empty, old policy keeps its digest, the four-in-a-row case is now stopped).
- Unit tests that the preview writes nothing and matches `evaluate` on the same invoice.
- A page check, `deploy/quick_setup_page_check.py`, on fictional data: open the helper, answer, see the preview change, save, and find the new version on the Control panel.
- The full suite and the existing page checks stay green.

## Not in this spec

- Prompts on Review when a pattern appears ("the last five cases came to you for this reason and you approved four"). Second phase; it extends the existing Suggestions.
- Staff onboarding.
- Vietnamese text.
- Trial credit questions. The helper leaves trial credit as it is; the NTK owners turned it off.

## Open questions for the owners (through Hoang)

- Where did the hour go: concepts, language, the form, or sign-in and Setup?
- When they say "30 days", do they mean from today or from the due date?
- Were they surprised that the agent approved nothing?
