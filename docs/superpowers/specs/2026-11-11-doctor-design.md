# Doctor: answers to the Owner's questions about how the setup is working

Date: 11 November 2026. Status: design agreed with the user in conversation the same day. No code is written yet.

## Why

Quick setup helps an Owner set the rules once. Afterwards the Owner has questions the Control panel does not answer: "Why am I still getting so many requests? Which setting is unreasonable?" and "Why do I keep correcting the agent? What is going wrong?" Today the only way to find out is to read cases one by one.

## Goal

The Owner picks a question and gets, in plain words: what is happening, with the counts behind it; what change would help; and what that change would cost. Every number is worked out by code from the Owner's own cases.

## Decisions made with the user

- Six preset questions answered by code. These are the main feature.
- No model inside Nucleon for this. A trial on 11 Nov showed the local model explains a facts sheet well but makes mistakes too often to stand alone: of 24 answers, 1 was empty, 2 compared against the wrong starting number, 1 left out the cost of a change, and 1 guessed a figure the sheet did not have. Each answer took one to three minutes.
- As an experiment, the Owner's existing assistant (the "Nucleon ADA Owner" agent in the chat) gets one new read-only tool that hands it the same facts. This is to see how much it helps for questions nobody predicted. It needs no new model plumbing.
- The Doctor suggests; it never changes a setting. A suggestion opens Quick setup with the answers filled in, where the Owner sees the preview and saves.

## The six questions

Each looks at the live cases of a window: 30 days by default; 90 days or everything on request.

1. **Why do so many requests still come to me?**
   - The cases that came to the Owner, grouped by the rule that sent them, each group with what the Owner then did (approved, declined, still waiting).
   - What-ifs on those same cases: for each rule that could be relaxed, how many the agent would have decided, and how many of those the Owner had in fact declined (the cost).
   - Rules are also tried together. On the NTK data of 10 Nov, allowing other overdue invoices gave 2 of 22, a 90-day limit gave 3, and both together gave 11: single changes hide the answer.
   - A look ahead on today's open invoices for the best combination, from the same preview Quick setup uses.
2. **Why do I keep correcting the agent?**
   - The agent's decisions the Owner reviewed: how many agreed, how many corrected (overridden, or marked "disagree").
   - What the corrected ones have in common, found by trying tighter limits: for each limit, the value that would have sent the most corrected cases to the Owner while sending back the fewest the Owner agreed with. Both counts are shown.
   - Agent declines the Owner reversed are counted apart.
3. **How much is the agent helping?** Requests in the window; how many the agent decided (approved, declined); how many came to the Owner; how many of the agent's decisions were reviewed and agreed with.
4. **Did the extensions the agent approved get paid?** The agent's approvals by what happened next: paid on time, paid late, part paid, not due yet, past due, unknown.
5. **Which customers come to me most?** The five customers with the most requests that came to the Owner, each with the main reason.
6. **Which rules never matter, and which block everything?** For each rule: how often it sent a real request to the Owner, and how many of today's open invoices it would block. A rule that blocks nine in ten is named; so is one that never fired.

## Honesty rules

- Every suggestion states its starting number, what it gains and what it costs, in one sentence. (The trial's mistakes were exactly these three.)
- With fewer than five cases behind a finding, the Doctor says there are too few to see a pattern, and still shows the counts.
- What-ifs on past cases judge the rules' bounds only, on the facts recorded when the case was decided. The page says so. Cases recorded before a limit existed are not judged on that limit.
- The Doctor never calls a setting "wrong". It says what the setting did and what the Owner did with the cases it sent.

## What the Owner sees

A page, "Doctor" (`#/doctor`), Owner only, linked from Home, the Control panel and the Decide page.

- Six question buttons and a window choice (30 days, 90 days, all).
- The answer: one headline sentence, the findings as a short list with their counts, then suggestions. Each suggestion has a button, "Try this in Quick setup", which opens Quick setup with those answers filled in and nothing saved.
- At the bottom: "Something else? Ask the assistant", linking to the chat, with one line saying the assistant explains the same figures, takes a minute or two, and that the numbers on this page are the ones to trust.

## The assistant's tool

`doctor`, Owner only, read-only, on by default like the Owner's other read tools. Arguments: `question` (one of the six ids, optional) and `days` (optional). With a question it returns that answer's facts as plain lines written by code; without one, each question's headline. The Owner agent's instructions gain one paragraph: use the tool for these questions, report only its numbers with their starting point, gain and cost, never compute its own, and point to Quick setup for changes.

## How it is built

- `prototype/doctor.py`, a new module of pure functions over case dicts and a policy. No database, no server. It reuses `delegation.would_approve`, `delegation.risk_checks`, `delegation.quick_setup_policy` and the helpers in `impact.py`.
- `GET /api/delegation/doctor[?question=<id>][&days=30|90|all]`, Owner only, read-only.
- The look-ahead reuses the Quick setup preview. Its loop moves into one helper both callers use.
- `prototype/web/doctor.js`, and a `try` parameter on Quick setup that fills the form.
- The tool follows `impactSummary` through `coordinator.py`, `server.py`, `agent_views.py` and `lab/mcp_server.py`. A script updates the agent in LibreChat.

## Tests

- Unit tests of each question on handwritten fictional cases with known answers, including the too-few-cases path and the combination search.
- API tests: Owner only, read-only (nothing written), the window.
- Tool tests beside the existing Owner tool tests.
- A page check on fictional data: each question answers, a suggestion opens Quick setup filled in.
- After deployment, a real conversation with the Owner agent on the two questions the user named, and a faithful report of how its answers compare with the page.

## Not in this spec

- Free-text questions inside Nucleon.
- Changing settings from the Doctor.
- Vietnamese text.
- Alerts that tell the Owner about a pattern before they ask.
