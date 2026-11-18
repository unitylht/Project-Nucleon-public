# Making the Owner side easier to start with (proposals, 12 November 2026)

Status: **mostly built on the evening of 12 November** (see "What was built" at the end). Not yet tried by any owner. The text below is kept as it was written before building.

Original status: recorded, not built. Nothing here is scheduled. What to build is decided after Tony's session with an owner (12 November), whose Part 1 measures where an owner stops when nobody explains. The software freeze is Friday 13 November.

## The problem

At the session of 11–12 November the owners said the product works and the Staff side is easy, but the Owner side is too much to take in at first, hard to understand without explanation, and steep to learn. Hoang had to explain and click for them. Earlier evidence points the same way: owners changed about 6 of more than 30 settings, and setup took about an hour.

The many settings are also the value: they let an owner shape the agent's behaviour in depth. So the direction is **not to remove anything, but to layer it**: by default the owner sees only what is needed to decide; the rest appears when asked for.

## Decisions already taken by Hanting (12 November)

- **The Decide card keeps showing its evidence by default.** An owner needs the facts in front of them to decide. Do not fold the evidence away.
- **A typed reason stays required for approve and decline.** The reasons are information the business will want later, when it reviews or tunes its rules. Do not make the reason optional.

## Proposals

| # | Proposal | What changes | Size |
| --- | --- | --- | --- |
| 1 | Simple view by default | The Owner menu shows Home, Decide, Rules and Assistant. Dashboard, Doctor, Customers, Model and the full Control panel move under "More". One switch shows everything; the choice is remembered. | Small (menu and entry points) |
| 2 | Quick setup as the front door to rules | "Rules" in the menu opens Quick setup, with a link "All settings" to the Control panel at the bottom. Quick setup gains two or three questions on trial credit for new customers, so the common cases never need the Control panel. | Small to medium |
| 3 | Home as a one-line briefing | For example "3 requests are waiting for you" and one button. The other figures and cards are folded. | Small |
| 4 | Quicker reasons on Decide | The evidence stays visible and the reason stays required (see above). Offer a few one-click reasons that fill the box and can be edited, so a required reason costs one click. | Small |
| 5 | A three-step first run | Set rules, look at one request, decide one. The other pages are offered only after that. | Medium |
| 6 | Say it instead of finding it | The owner tells the assistant "let the agent handle extensions under 200 million"; the assistant opens Quick setup filled in, and the owner confirms. The Doctor's suggestions already work this way. | Medium |

## Order suggested

1 and 2 first: they change only what is shown first, not what the system does, so the risk is low. 4 next. 3, 5 and 6 go to the roadmap in the report.

## What the owner session of 12 November (afternoon) added

One owner, comfortable with software, on the fictional data. Details are in the feedback register (docs/pov/FEEDBACK-REGISTER.md); the full notes are kept privately.

- He set rules alone in 2 min 37 s and decided a request in 9 s. For him the Owner side is **usable but long and wordy** ("clunky"), not confusing. He would not remove any setting.
- His worry is **his staff**, who are not technical: the assistant's answers show too much working. He asked for a simple view and an advanced view.
- He asked, unprompted, for three things already on this list or close to it: **presets** (strict, balanced, relaxed), a **"Let's get started" path** from Home, and a **simple view**.
- He clicked Control panel before Quick setup, which supports proposal 2.

| # | Proposal from this session | Size |
| --- | --- | --- |
| 7 | Presets in Quick setup: strict, balanced, relaxed fill the answers; "custom" keeps today's questions | Small |
| 8 | Simple or detailed answers from the Staff assistant, chosen by the Owner | Small to medium |
| 9 | Outstanding amounts the way a statement shows them: overdue only when asked who to chase, with days overdue; Dashboard by age band | Medium |
| 10 | "When will they pay?": typical days late and an expected window, from the recorded history | Medium |
| 11 | Small fixes: "still owed" defaults to the invoice amount; the Quick setup preview says when a change alters nothing; the assistant shows the ABN on record | Small |

Not for the PoV, for the report's limits and roadmap: ABN register lookup and change alerts (needs an outside data service), connections to accounting and payment software, a daily unprompted "who to follow up" list.

**Order now suggested:** 7 with 2 (presets inside Quick setup, Quick setup as the door), then 5 (the get-started path), then 1 and 8 (simple views for Owner and Staff), then 11.

## What would change this order (written before the session)

Tony's notes from Part 1: where the owner stopped, which label or number they asked about, and whether they found Quick setup alone. If the owner stops somewhere else (for example on the request page, or on the words of a result), that comes first.

## What was built (evening of 12 November, commit 9c95cd8)

| # | Proposal | State |
| --- | --- | --- |
| 1 | Simple view by default | Built as a choice of three display levels (Simple, Standard, Detailed), kept per browser. The default is Standard, not Simple: one line of each explanation, a click shows the rest. Simple shortens the Owner's menu to Home, Assistant, Decide, Rules |
| 2 | Quick setup as the front door | Built for the Simple view ("Rules" opens Quick setup). Trial-credit questions were **not** added to Quick setup |
| 3 | Home as a one-line briefing | Built: one sentence and one button at the top of Home. The cards below stay; in the Simple view the recent decisions and counts are hidden |
| 4 | Quicker reasons on Decide | Built: one-click reasons that fill the box. A reason stays required and the evidence stays visible |
| 5 | A first run in steps | Built as Get started: how strict, customers to keep, how much the pages show |
| 6 | Say it instead of finding it | Not built |
| 7 | Presets | Built: Strict, Balanced, Relaxed, in Get started, Quick setup and the Control panel |
| 8 | Simple or detailed answers from the Staff assistant | **Not built.** It changes the assistant's instructions and the layer in front of the model; too risky the day before the freeze without a round of live tests |
| 9 | Outstanding amounts like a statement | Not built |
| 10 | "When will they pay?" | Not built |
| 11 | Small fixes | The preview note is built. "Still owed" is deliberately not prefilled (an invoice amount alone does not say what is still owed). The assistant cannot show an ABN because the customer record has no ABN field: an ABN is only entered as evidence on a request |

Also built, asked for by Hanting: the choices of Get started are all at the top of the Control panel ("Quick settings"), so changing one never means running Get started again; a level fills answers in Quick setup and saves nothing by itself; section icons and a row of links on the Control panel.
