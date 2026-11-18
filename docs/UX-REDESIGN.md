# Interface redesign (18 October 2026)

Branch: `feat/ux-redesign-20261018`. Not merged, and not deployed to the shared practice instance. The disposition of every QA finding is in [qa/FINDINGS-DISPOSITION.md](qa/FINDINGS-DISPOSITION.md).

## Why

The earlier interface had grown one feature at a time:
- **One page for everything.** The Records page was about 7,000 px long on a desktop and 10,000 px on a phone. It mixed setup, open questions, tables, entry forms, notes, completeness and import history.
- **No clear next step.** The starting point and the next action were often unclear.
- **No way back to work.** Records offered no route back to a request.
- **The wrong customer, by default.** Selectors defaulted to a sample customer, inviting entries against the wrong one.
- **Hidden figures on phones.** Tables hid amounts behind a sideways scroll.

The aim is an operational tool a teammate can use without a guided tour. The agent-prepared request remains the centre of the app, with the records that support it one step away.

## Tasks it serves

| Who | Task | Where |
| --- | --- | --- |
| Staff | Paste a customer's message and send it to the agent | Requests → New request |
| Staff | Answer the agent's question (which customer, which date, which invoice) | Requests → the case |
| Staff | Copy the owner's unsent reply | Requests → the case |
| Staff | Keep invoices and payments current: by hand, by CSV, corrections, removal, allocation | Customers → the customer; Imports |
| Staff | Answer questions about the opening balance; mark money not for an open invoice | Customers → the customer (its Needs attention box and tab, Payments) |
| Staff | Write knowledge drafts | Knowledge, or the customer's Notes |
| Owner | Decide requests, with the facts, their sources and their certainty | Requests → the case |
| Owner | Confirm knowledge drafts | Knowledge |
| Owner | Opening balances and completeness statements, which make amounts exact | Customers → the customer's Opening balance tab; Completeness statements |
| Owner | First-run setup and the checklist | Setup |
| Operator | Reset, start empty, restore; practice messages | Demo console (own code, own header) |

## Navigation: two options compared, one chosen

| | A. Requests + Records with sub-tabs | **B. Task areas (chosen)** |
| --- | --- | --- |
| Top level | Requests, Records | Requests, Customers, Imports, Knowledge, Setup |
| Records | One area with tabs: customers, payments, completeness, knowledge, imports, setup | Each a page, one tap from anywhere |
| Strengths | Keeps the "single Records area" from the 17 October P002 review; small header | Each area is named for the job done there; the customer is the anchor for every financial record; one level of navigation |
| Weaknesses | "Records" stays vague; two levels of navigation; it was the source of the "no route back" complaint | Five items: needs a bottom bar on phones; departs from the review's wording |

**Chosen: B.**
- It maps one-to-one to the tasks above.
- It keeps **Requests first**, as the Week 7 demo requires: "start the demo with the agentic feature".
- It makes the customer the place for invoices, payments, credits, opening balances, completeness and their requests, which removes the wrong-customer defaults by construction (QA U1).
- The P002 review's point was that onboarding and maintenance share one set of capabilities. B keeps that: Setup links into the same Customers, Imports and Knowledge pages, and there is no separate onboarding wizard.

**Structure:**
- Header bar on wide screens (navigation, agent status, Staff/Owner, Sign out). On phones a bottom bar carries the five areas.
- Every page has a header: back link, title, one line about the page, and its main actions on the right (stacked on phones).
- `#/requests`, `#/requests/new`, `#/case/<id>[?from=<customer>]`
- `#/customers`, `#/customers/<id>/<invoices|payments|balance|notes|requests>[?from=<case>]`, `#/completeness`
- `#/imports`, `#/imports/new`, `#/imports/<id>` (a draft to check, or an applied or reverted import)
- `#/knowledge`, `#/setup`, `#/console` (operator). Old `#/records` links open Customers.

**Context travels with you.**
- From a case, "Customer records" opens the customer with `?from=<case>`. Every tab keeps "← Back to the request about …", and the case links back to the customer.
- Filters (requests, notes, the customer search and "Needs attention only") are kept for the browser session.
- Dialog drafts are kept when a dialog closes (see below). The new-request draft is kept in the browser until it is sent.

## The design system

**Brief:** a restrained operational tool for financial records; Arial throughout; colour only where it carries meaning. The frontend-design skill's process was used: plan the tokens, check them against generic defaults, build, then critique screenshots.

**Tokens** (in `web/app.css`, `:root`):
- **Type:** Arial (falling back to Helvetica). 16 px body; 26/22 px page titles; 18 px section titles; 13–14 px secondary text.
- **Colour:** ink `#18222c`; slate `#3f4c58` and `#5b6874` for secondary text; paper `#f3f5f7`; surface white; `#d5dce2` for separators and `#7a8692` for control borders.
- **Accent:** ledger blue `#1d5c8c`, for actions, links and the focus ring.
- **Status colours:** green `#1b6a45`, amber `#855000` text with a `#c4851a` line, red `#b3261e`, and blue-grey for "preparing".
- **Spacing:** 4, 8, 12, 16, 24, 32, 48. **Radius:** 4 px on controls, 6 px on panels.
- **Touch targets:** 40 px; 44 px on phones and coarse pointers. Bottom-bar items are 56 px tall.

**The one bold element: certainty marks.** Every amount is shown with how certain it is, and the line style carries the meaning without colour:

| Mark | Line | Meaning |
| --- | --- | --- |
| Exact | solid, green | From complete records, as of a date |
| At most | dashed, amber | The invoice less allocated payments; some may be missing |
| Stated | dotted | A source's figure as of a date |
| Not recorded | none, muted | No amount stated and no payment allocated, with that reason |
| As recorded | none, muted | A customer balance worked out from the records entered |
| Settled | solid, green | Covered by allocated payments, or exactly zero from complete records |

The due-date timeline on a case stays as it was.

**Components:**
- **Buttons:** primary (one per area of the screen), secondary, danger (outlined), solid danger only in the confirming dialog, and link.
- **Status chips:** need (amber), wait (grey), busy (blue), done (green), fail (red).
- **Callouts:** ok, warn, bad.
- **Forms:** label above the field, help text under the label, the error under the field (announced, and the field gets focus), and "(optional)" marked.
- **Tables:** full tables on wide screens; stacked rows with labels on phones, so no figure is hidden behind a sideways scroll.
- **Dialogs:** native `<dialog>`, which keeps focus inside and returns it on close, with Esc.
- **Tabs:** arrow keys move between them, and the selected tab is the one in the tab order.
- **Feedback:** a toast for every success. Copy confirms on its own button.
- **Page states:** "Loading …", "This page didn't load" with "Try again", empty states that say what to do next, and "not found" pages.

**Avoided:** content chopped into identical shadowed cards; all-caps labels; joining facts with middle dots; decorative colour. Only the action panel and dialogs are raised.

## Screens

**Requests.**
- **The queue:** For you, In progress and Done, with filters and counts. Staff get "New request"; the owner's starting point counts the requests waiting for a decision.
- **The case:** the next step (answer, decide, copy the reply, prepare again, or waiting) sits beside the key facts on wide screens and comes first on phones.
- Below that: the customer's words, "Worth checking" and the owner's notes.
- Evidence, Activity and Technical are tabs, not a long scroll.

**Customers.**
- **The list:** search, "Needs attention only", open invoices, money not allocated, the opening balance, payments complete to, and what needs attention.
- **Each customer** (revised after the review of `810a4cc`, so the records and routine actions come first on a phone):
  1. The name and the routine actions: Add invoice, Record payment or credit.
  2. Only when something needs attention, a short box: the count, then one line per kind of issue, blocking ones first and in red, each naming up to three records ("Payment records are no longer confirmed complete: LATE-1 was added"; "2 questions about the opening balance: DEMO-952, EARLY"), and "Review all".
  3. Three key figures, uncertain ones marked: not allocated, payments complete to, customer balance "as recorded".
  4. Tabs: Invoices, Payments, Opening balance, Notes, Requests. The section headings keep the full names ("Payments and credits", "Opening balance and completeness"). Needs attention is its own tab, opened from the box or from the list's count, with every explanation and question answered in place. It is listed with the tabs while it is open.
  5. The selected tab's records, then the recorded totals.
- Opening another page or record starts at its top; the same page drawn again after a change, or another tab, keeps its place.
- Correct name and Remove customer sit at the bottom, away from the routine actions.
- Records are browsed in tables. Every create, correct, remove, allocate and mark happens in a dialog that names the customer and says what it affects.

**Imports.**
- **The list:** drafts not applied (resume or discard), history (view or revert), and discarded drafts listed.
- **A new import:** choose the file.
- **A draft:**
  1. Columns.
  2. Customers not in the records (nothing is matched for you).
  3. Completeness (owner only, explained to staff).
  4. Check the rows, with every value shown.
  Then **Apply**, **Keep as a draft and close**, or **Discard draft**.
- **An applied import:** its rows, and "Revert this import" with what reverting would do, worked out before anyone types a reason.

**Knowledge:** drafts waiting for the owner, confirmed notes, all notes; confirm and retire.

**Setup:**
- The checklist, each item linked to where it is done, with skip for the owner.
- The workspace facts, and how business dates and recorded times differ.
- First run: the owner chooses the workspace type, then the basics; staff see that the owner has to set it up.

**Demo console** (operator): reset, start empty and restore, each confirmed in a dialog with Undo afterwards; practice messages; backups by name only.

## Lifecycle of unsaved work

| Thing | Close or leave | Save | Discard | Resume |
| --- | --- | --- | --- | --- |
| New request | Kept in this browser while signed in, across navigation and reloads | "Send to the agent" clears it | Clear the box | Open New request |
| A dialog (invoice, payment, opening balance, note, …) | Kept for this session; the toast says "Draft kept" | Saving clears it | "Start again" in the restored dialog | Open the same dialog: "Restored what you typed before" |
| An import | "Keep as a draft and close" lists it under Drafts not applied | "Apply" | "Discard draft" (it can never be applied) | "Resume" |
| A case answer or decision | Not kept; the case keeps its state on the server | "Send to the agent" / "Record decision" | — | Open the case again |

The 8-second refresh of the request list pauses while you type or while a dialog is open.

**Signing out** (revised after the review of `810a4cc`):
1. Every role this browser holds ends at once in this view. The page stops all signed-in work, and responses that arrive later are dropped.
2. Unsent drafts, kept filters and searches, and the loaded records are removed from this browser. Other open tabs follow straight away.
3. The page says "Signed out" only after the server, asked again, holds no session for this browser. Other browsers keep their sessions.
4. If that cannot be confirmed, the page says "Sign-out not confirmed". It says only what is known: whether the server answered (when no answer arrives, "The app did not receive confirmation"), and which roles the server still holds, and offers "Try signing out again". A reload keeps trying; nothing signed-in is shown meanwhile.

## Responsibilities by role

- **Staff:**
  - send requests and answer the agent;
  - keep records by hand and by import;
  - answer opening-balance questions;
  - write knowledge drafts;
  - prepare a failed case again.
- **Owner:**
  - decide requests;
  - confirm knowledge;
  - confirm or retire completeness, including the optional completeness of an import;
  - set up the workspace and skip checklist items.
- **Both:** enter opening balances. Who should is open business question B6, so the page shows who entered each one. Who may confirm completeness and answer inclusion questions is open question B7; completeness stays owner-only, as before.
- **Where the rules are enforced:** on the server. The interface explains them where an action is not available, for example "The owner confirms completeness."

## Accessibility

- Landmarks; a skip link; one `h1` per page.
- Visible 3 px focus.
- Every control labelled; errors linked to their fields and announced.
- Keyboard: dialogs, tabs, decisions and filters all work without a mouse.
- Contrast, measured: text 4.95:1 or more on every background used (secondary text on paper 5.23:1; chips 5.58–6.79:1). Control borders 3.72:1 on white and 3.40:1 on paper (WCAG 1.4.11). The first draft had 1.99:1 field borders; this check caught them.
- 44 px touch targets on phones.
- Reduced motion respected.
- Not tested with a screen reader (VoiceOver or NVDA).

## Skills that informed this work

- **`frontend-design`** (Anthropic's official plugin). Its two-pass method (plan the tokens, review them against generic defaults, build, critique screenshots) shaped the token set and the single bold element, the certainty marks. The brief's Arial and restraint took precedence over its push for distinctiveness.
- **`design-critique`**, **`ux-copy`**, **`accessibility-review`** and **`design-system`** (Anthropic's `knowledge-work-plugins/design`, installed as personal skills without the plugin's unrelated connectors). Used for:
  - the screenshot critiques, which found the wrapped filters, the clipped table cells, the misleading "Stated" on balances and destructive actions placed next to routine ones;
  - error messages that say what is missing;
  - verbs on buttons, and a button that names the decision it records;
  - the WCAG 2.1 AA checks on keyboard use, focus, labels, contrast and targets;
  - the component and token inventory.
- **`webapp-testing`** (Anthropic's `anthropics/skills`). The reconnaissance-then-action pattern and console capture behind `deploy/ui_check.js` and `deploy/guide_check.js`.
- **`docx`** (Anthropic's `anthropics/skills`). Built the Arial testing guide with docx-js, rendered it through LibreOffice to check the layout, and caught the missing answer lines and a non-Arial bullet.

## Screens before and after

In [screenshots/ux-2026-10-18/](screenshots/ux-2026-10-18/). None shows an access code.

- **Before** (the unchanged code with the same fictional data): `before-desktop-staff-requests`, `before-desktop-owner-case`, `before-desktop-records-top`, `before-390-records-customers` (the clipped table), `before-390-case`, `before-375-staff-requests`.
- **After:**
  - Desktop: `after-desktop-requests`, `-owner-decided`, `-customers`, `-customer-invoices`, `-customer-balance`, `-import-draft`, `-imports`, `-flagged-case`, `-preparation-failed`, `-knowledge`, `-setup`.
  - Phones: `after-390-customer-invoices`, `-case`, `-customers`, `-imports`, `after-375-case`, `-requests`, `-signin`.
  - The customer page at 375 and 390 px, revised: `after-375-customer-routine` and `after-390-customer-routine` (nothing needs attention), `after-375-customer-invoices` and `after-390-customer-invoices` (three unresolved issues, the first screen), `after-390-customer-attention` (after "Review all").

## The desk (branch `explore/agent-coordinator-20261019`, 19–20 October 2026; preview only, at `/preview/`)

Added for the first slice of P003 ([AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), E018). The shared site still runs the interface described above (`f95f50f`).

- **Where.** Requests (`#/requests`) is now a desk: a thread list beside the open thread, in the queue's grid. **Nucleon**, the general thread, is pinned first. Every case follows as its own thread, with the queue's row styles and status chips.
  - The old queue is still there, unchanged, as **List view** (`#/cases`), with its form at `#/cases/new`.
  - The case page `#/case/<id>` and the navigation labels are unchanged.
- **Cards.** A case thread shows its turns, then **Facts**, **What you have said** (staff: **What the owner shared**), **What I need** (the owner's questions, each with "Why I ask"; staff: **What the agent needs from you**, only the questions asked of staff, with Answer only), **Decision**, and **Reply draft**.
  - Owner context on the desk gives one **What I understood** card, with Confirm, Correct and Discard.
  - A question gets an **Answer** card. Its title is the code-written note; amounts are shown with their certainty marks.
  - Every card has **Sources**. Case cards also link to the full case and to the customer's records.
  - The cards reuse the case page's parts (facts, flags, the decision panel, status words, certainty marks) and use only the existing tokens.
- **The input.** One text box with **Send** (Ctrl or Cmd+Enter also sends). While the model reads, it shows "Nucleon is reading your message…". The unsent text is kept per thread for the browser session, and sign-out clears it.
  - The 8 s refresh keeps running while the box has focus, and pauses while a card's form or a dialog has focus.
  - The input is outside the redrawn area, so a refresh never clears what is being typed.
- **Phone layout.** The list is one page and a thread is another, with "← Requests" to go back. Up to 760 px wide, the input sits fixed directly above the tab bar, and the page gains bottom padding so the last card clears it. From 761 to 899 px it is sticky at the bottom. `desk_check.js` checks 375 and 390 px for no horizontal overflow, cards that fit, an input that can be reached, and answer tables that stack without overlap.
- **What staff see and what the owner sees.**

  | | Owner | Staff |
  | --- | --- | --- |
  | The owner's own turns, and the agent's replies to them | yes | no |
  | Context lines | everything confirmed | only statements the owner shared, under "What the owner shared"; no card when nothing is shared |
  | Questions ("What I need") | yes | no; they quote the owner's words |
  | Suggestion block, and the decision's record of it | yes | no trace |
  | The decision form | yes | no; staff see where the case stands ("With the owner for a decision.") and, once it is decided, the reply draft |

  The owner's intro on the desk says that staff enter requests.
- **Not known:** whether people find the desk easier than the list view, beyond the counted effort comparison ([qa/EFFORT-COMPARISON.md](qa/EFFORT-COMPARISON.md); mock agent, fictional data; its Reading section is unfilled). No teammate has used it yet, and nobody has looked at the list view's two-button header at phone width beyond `layout_check.js`.

### Second slice (20 October): the conversational desk

The desk agent loop of E020 ([AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 3"). Where this list differs from the one above, this one is current: answers and case threads no longer carry their own Sources or links.

- **The answer card.** One card per answer:
  - the agent's words first, split into paragraphs on blank lines only. When code withholds them, a muted sentence says so, and the blocks below carry the answer;
  - then only the blocks the agent asked for, each written by code with the records' amounts, marks and dates: "What X owes, as the records show it on …", "Open/Overdue/All invoices for X", "What you have said about X" (staff: "What the owner shared about X"), "Requests for X", "Where to do it" (numbered steps) and "New customer: <name>". Up to three blocks are all open; from four, only the first;
  - then at most one next step: a link button (for example "Add customer" to Customers, "Open Harbour Demo Supplies"), or a hint line.
  - A prepared customer's card has one control, **Create customer**, which opens the existing Add customer dialog with the name filled in. Nothing is added until the person saves it; the thread then notes "Customer <name> added.".
- **The focus chip.** Above the input, "About <name> ×" names the customer the conversation is about for this person. Pressing it clears it, and the next question that names nobody asks which customer. The owner and staff each have their own.
- **The case thread hierarchy.**
  - **Owner:** one card first, with the request line ("Bayside Café asks to pay invoice DEMO-501 on Tue 10 Nov 2026 instead of Tue 20 Oct 2026, an extension of 21 days."), the customer's own words quoted under it, the amount still owed with its mark, the suggestion when on, and the decision controls. Then folded sections, each with a count: **What the agent needs** (open while a question is open, because the suggestion waits for it), **What you have said**, **Facts and sources**, and after deciding **Reply draft**. The decision form starts within the first 900 px at 1366 px wide (`layout_check`, `desk_check` D6). The header shows the chip alone while the case waits for the owner and once it is completed.
  - **Staff:** one status line, "With the owner since <time>; nothing for you to do." (or "Decided: …"), or the question addressed to staff in its place. Then the request line with the customer's words, folded **Facts**, **What the owner shared** when something is shared, and **Reply draft** once decided.
  - The turns follow the case block, next to the input.
- **The footer.** One per thread: "Open the full case", "Customer records" and **Sources** (what the suggestion cites, where each context line came from, who asked each question, how the reply is written). In the general thread, "Customer records" follows the latest answer's customer. Each link appears once per thread (`desk_check` D4, `layout_check`).
- **Checks:** `desk_check.js` 60/60 and `layout_check.js --seed` 217/217, including 375 and 390 px, on scratch servers with the mock agent. No browser check covers an answer with two or three blocks, or a reply with paragraphs.
- **Not known:** whether people find it easier. The conversation review's reader is a model reading transcripts, not a person using the page ([qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md)), and the effort comparison has not been re-run on this slice.

### Third slice (21 October): situation, capabilities and prepared actions

The changes of E021 ([AGENT-COORDINATOR-PROPOSAL.md](AGENT-COORDINATOR-PROPOSAL.md), "Revision 4"). Where this list differs from the ones above, this one is current. Built for the preview; not yet deployed there at the time of writing.

- **The case block comes from the situation.** The request line, "Still owed on this invoice" with its mark, the suggestion, the questions with their answers ("Already known", skipped), the context groups and the Sources lines are drawn from the same role-filtered structure the agent reads. The status line, the decision form and the reply panel come from the case, as before.
- **The limit line.** Under the amount, for the owner: "Asked for 21 days; you allowed up to 14 days (beyond the limit; latest Tue 3 Nov 2026)." With no extension asked: "You allowed up to 14 days (latest …)." Staff see no limit line.
- **The prepared decision.** When the owner says a decision in words ("approve 14 days, then"), the answer card ("Prepared decision on invoice DEMO-501") and the case block ("Prepared decision") show "Approve to Tue 3 Nov 2026", "14 days after the current due date, Tue 20 Oct 2026.", the days asked against the limit, "Reason to record: …", "Nothing is decided until you press Confirm decision." and one **Confirm decision** button. It records the decision through the decision form's own call; nothing is committed before. A replaced or decided one reads "No longer current: a later one replaced it, or the case was decided." and has no button; a new suggestion withdraws it.
- **Details and summary lines.** The reply says how its blocks are shown:
  - a short answer: the words, then one closed **Details** expander holding the blocks;
  - summary: one line per block under the words, from the block's own fields, never computed by the page ("<name>: N open invoices, N overdue, N open requests. <balance line>", "<invoices title>: N.", "<requests title>: N.", the context title or "<title>: nothing on file.", "Where to do it: <label>."), then the same expander;
  - full: the blocks open, as before.

  A prepared customer and a prepared decision are never folded, so their buttons stay in view. An invoice appears once: with an invoices block, the overview leaves out the invoices it shows. The same context block appears once.
- **The chip** above the input reads "About <name> ×" for a customer, with a **Customer records** link; "About <name> (not yet a customer) ×" for a customer prepared but not yet created; and "About <name> (not found) ×" for a name the records do not hold. The last two have no link. Pressing the chip clears it.
- **A withheld reply** is asked again once. If it is still withheld, the card says "Here is what the records show about <name>." (or "Here is what the records show.") with the blocks open, and the thread's Sources list "Wording withheld <time>: <code's sentence>".
- **Setup → Agent tools** (owner only; staff see nothing of it and send no request). A table with Tool, What it does, Kind (Read, Prepare, Act), Roles, Needs confirmation (on phones "Confirmation") and Enabled, with an "On" checkbox per tool, the sentence "In this fictional preview every implemented tool is on by default. Nothing here sends anything outside Nucleon." and the hint "Turning a tool off or on takes effect from the next message to the agent." A tool turned off is neither offered to the agent nor run.
- **Checks:** `desk_check.js` 73/73 on scratch servers with the mock agent, including the expander, the summary lines, the merging, the three chips, the Agent tools table and switch, and prepare-then-confirm (D8, D10, D11, D12); `layout_check.js --seed` 217/217 and `ui_check.js` 150/150 at `d5d165a`. Screenshots of the summary lines, the chips and the Agent tools table were checked by eye at desktop width and at 375 px; the prepared block at desktop width only, not at 375 or 390 px.
- **Not known:** whether people find it easier. The reader of the conversation review is a model reading transcripts ([qa/CONVERSATION-REVIEW.md](qa/CONVERSATION-REVIEW.md)), and the effort comparison has not been re-run.

## Not done, or not known

- **Not tested:** a real phone, browsers other than Chromium, and a screen reader. No teammate has used the new interface yet.
- **Deployed** to the shared practice instance on 18 October at 23:24 as `f95f50f` (the reviewed `33272b7` plus a fix for 502s on page load; [DEPLOYMENT.md](DEPLOYMENT.md)). Not merged into main.
- **Check scripts:** `browser_check.js` and `layout_check.js` on this branch target the new interface. To check the deployed `a9ce30d`, use them from `1f5a21d`.
- **Remaining defects:** see [qa/FINDINGS-DISPOSITION.md](qa/FINDINGS-DISPOSITION.md), "Found during this work".
