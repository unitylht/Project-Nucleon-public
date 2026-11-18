# Nucleon: master document and information pack for the final report

Written 11 November 2026 for Tony, Hoang and Phu/Chris; updated the same night after the deployment and after checking the Week 8 and Week 9 slides. Report due Monday 16 November 2026, 5 pm. **13 November: this is now the team's master document.** The four members' compendiums are merged in as sections 13 to 17 (discovery and problem definition, research, data and model, team and delivery, open points).

## How to use this pack

- Each section starts with a **core message** you can put on a slide, then the detail.
- Every number has its source in square brackets. If two sources disagree, both are given and flagged "SOURCES DISAGREE".
- Three labels matter more than any others. Use them on slides.
  - **Measured**: a computer counted or timed it (tests, benchmark runs, timestamps).
  - **Reported by a person**: someone told us (the Owner's baseline, a tester's opinion). Say "reported by the Owner", never "we measured".
  - **Not measured yet**: say so plainly. Hiding gaps costs more marks than showing them.
- "Not known / to confirm with X" means we did not find the answer in the project records.
- All demo and most test data is **fictional**. Only the "NTK" rounds (8-11 Nov) used the real business's imported records.
- **Who does what (agreed 12 Nov [MEETING-1112]).** Hoang, Phu and Chris write the 35-slide report deck; Tony and Hanting make the 10-minute and 2-minute videos. Each member posts one text-only summary of everything they did under Hoang's Teams post; Hoang merges them into one master document and builds a new slide structure from it. Chris: Scrum review (1-2 slides), methodology, personas, overviews, slide allocation against the rubric. Hoang: the software, business and technical parts. Phu: unit economics, market and delivery, and styling Hoang's raw slides. Slide content due Saturday 14 Nov; deck and video due Monday 16 Nov, 5 pm. This pack's link does not change; refresh it to see updates. The summaries members post will be merged into it.

Source key (all in the repository `~/Developer/Project-Nucleon` unless stated):

| Tag | File |
| --- | --- |
| [ADA] | docs/ADAPTIVE-DECISION-AUTHORITY.md |
| [PLAN] | docs/product/POV-IMPLEMENTATION-PLAN-20261030.md (decisions D1 to D15) |
| [ROADMAP] | docs/product/POV-ROADMAP-20261030.md |
| [BENCH] | docs/research/MODEL-BENCH-20261031.md |
| [QUAL] | docs/research/MODEL-QUALIFICATION-PROCESS-20261031.md |
| [SHADOW] | docs/research/SHADOW-MODEL-20261102.md |
| [LIMITS] | docs/KNOWN-LIMITATIONS.md |
| [POV-README] | docs/pov/README.md |
| [TESTER-GUIDE] | docs/pov/TESTER-GUIDE.md |
| [FEEDBACK-W7] | docs/team/WEEK07-PRESENTATION-FEEDBACK-20261030.md |
| [REGISTER] | docs/memory/DECISION-REGISTER.md |
| [QS-SPEC] / [DOCTOR-SPEC] | docs/superpowers/specs/2026-11-11-quick-setup-design.md / ...-doctor-design.md |
| [GIT] | `git log` of the repository (524 commits, 15 Oct to 11 Nov 2026) |
| [DIARY] | engineering diary kept by the product lead (dated entries) |
| [NTK-SESSION] | "Nucleon Owner Testing Session Summary for NTK", written by Hoang after the session with the owners on the night of 11-12 Nov 2026 |
| [SESSION-1112PM] | Tony's session with a second owner on the afternoon of 12 Nov 2026: audio transcript, handwritten notes and the system's records. Kept privately; de-identified observations are in docs/pov/FEEDBACK-REGISTER.md |
| [MEETING-1112] | Team meeting on the evening of 12 Nov 2026 (Teams transcript, 60 min): work split, deadlines, Tony's report on the Staff-side test and the second owner's extra comments, Hoang's account of the first owner session's set-up hour |
| [HOANG-6NOV] | Hoang's "Nucleon App Test Assessment" report, tested 6 Nov |
| [HOANG-8NOV] | Hoang's "NTK Nucleon Workflow Examination" report, 8 Nov |
| [HOANG-9NOV] | Hoang's "NTK Final Core Workflow Test Report", 9 Nov |
| [TONY-6NOV] | Tony's notes file "TESTING" from his 6 Nov round |
| [C-HOANG] | "NTK Term Work Evidence Compendium", Hoang, 13 Nov 2026: discovery with the NTK owner, research document, ledger cleaning, exploratory models, all test reports |
| [C-TONY] | "Tony Tran: Term Work Evidence Compendium", 13 Nov 2026: interviews with the gelato manufacturer, Teams posts and minutes, trust research, questionnaire, sessions |
| [C-CHRIS] | "Chris Cheng: Term Work Evidence Compendium", 13 Nov 2026: charter, café research and interviews, problem statements, Solution Design Document, BPMN, slide plan |
| [C-PHU] | "Individual Term Work Evidence Compendium" (author not named in the file; taken to be Phu's), 13 Nov 2026: café owner interview, post-pivot credit examples, presentation and value analysis |

---

## What the report must contain (from the Week 8 and Week 9 slides)

**Core message.** The slides ask for proof of value, not a feature list: a baseline, an "after", who tested, what they said and what we changed because of it. The pack is strong on design, build and technical evidence. Since 13 November it also holds problem and discovery (section 13), the team's research (14), the data work (15) and team practice (16). It still cannot supply unit economics and go-to-market: nobody has written them (section 17).

Checked on 11 November against the two decks "INFS3605 W8 Seminar Slides" [W8] and "INFS3605 Week 09 Refinement" [W9]. Page numbers are the PDF pages. Where the slides differ from what was said aloud in the Week 9 seminar, the slides are given and the difference is flagged.

### The three deliverables

| Item | What the slides say |
| --- | --- |
| Report deck | PDF, **max 35 pages at 16:9**, appendices extra, one submission per team, **due Monday of Week 10 at 5 pm on Moodle** [W8 p4, W9 p4]. It must make sense to a reader who never met the team. The seminar recording mentions Turnitin; the slides say Moodle: check the submission page. |
| Demo video | **Max 10 minutes, at least 3 distinct use cases, realistic data, on the working app.** Show the agent act and the owner approve, told through the owner's day; cut the waiting time on AI steps [W8 p4, W9 p4, p12]. Storyboard on the slide: 0:00-0:30 hook and problem; 0:30-3:00 use case 1; 3:00-5:30 use case 2; 5:30-8:00 use case 3; 8:00-9:00 proof-of-value evidence (user quotes, what changed); 9:00-10:00 lessons and close. |
| Week 10 showcase | Wed 18 Nov, 2-5 pm. **7-minute pitch including a recorded demo, stopped at 7:00, then 5 minutes of questions.** At least 3 members present. Not assessed [W9 p3, p13]. Pitch outline: 0:30 hook; 1 min discovery evidence; 1 min solution and the agent's role; 2:30 recorded demo of the strongest use case; 1 min proof of value (before, after, quotes); 1 min go-to-market, lessons, close. |
| Microsoft showcase | Tue 24 Nov, 9 am-2 pm, North Sydney, top six teams across the three seminars, 10 minutes including about 5 minutes of demo [W9 p3, p13]. |

### How it is judged

Three levels: Not yet, Competent, With Merit, judged "from this submission and your Week 07 PoC". No weights are on the slides; the rubric is on Moodle [W8 p4-5]. For Competent the slides list: a working PoC (core features end to end with realistic data, without the team's help); a defensible problem statement grounded in stakeholder analysis and evidence; design decisions each justified by user research, partner input and course concepts; proof of value tested with target users, where the learning shaped refinements; team practice (Scrum-style cadences, shared accountability); professional deck and video; lessons learned stated explicitly. With Merit adds depth beyond the core and **several test rounds traced to decisions**.

### Suggested page budget [W9 p11]

| Pages | Part | Where the content comes from |
| --- | --- | --- |
| 1 | Team: a photo and the Scrum role of every member, GitHub link, live app link, any login needed | **Team.** Links and logins from Hanting. The repository is private: decide how the marker gets access. |
| 2-5 | Problem and evidence | **Team** (interviews, stakeholder analysis). This pack has only section 1's short background. |
| 6-9 | Discovery | **Team** (weeks 1 to 6 are not in the project records). |
| 10-15 | Design decisions and why | This pack, section 4, plus the glossary. |
| 16-22 | Build: the PoC and its agent | This pack, sections 1, 3, 5 and 8, and the screenshots. |
| 23-29 | Evaluation: proof of value | This pack, section 6, **plus the owners' numbers and quotes from Hoang and Tony** (see the gaps below). |
| 30-32 | Go-to-market | **Team.** Nothing in this pack. |
| 33-35 | Lessons and next steps | This pack, sections 9 and 10. |
| Appendix | Test notes and extras | This pack's tables; the testers' reports. |

Each part needs one key message, a page budget, an owner, and a name and date. The Week 9 seminar said "about equal space for problem, PoC and PoV"; the slide's outline is uneven as above and is called "a starting outline".

### Checklist of things the slides ask the deck to show

| The deck should show | Slide | Status |
| --- | --- | --- |
| Photo and Scrum role of every member; GitHub link; live link; logins | W9 p4 | Team to do. |
| Problem statement grounded in stakeholder analysis and evidence | W8 p5 | Team. |
| The owner persona and the owner's day (journey) | W8 p18, W9 p4 | Team; the three use cases in section 8 can be told as the owner's day. |
| Design decisions tied to user research, partner input and course concepts | W8 p5 | Section 4 gives the decisions and reasons. **Add the course concepts** (below). |
| The agent's goal, authority and escalation rules; which steps are human, tool or agent | W8 p19 | Sections 1 and 2: goal = decide routine credit requests; authority = the Owner's policy; escalation = anything outside a rule comes to the Owner. |
| "Tool or agent" test: if a human must notice, start, check and act, it is a tool; an agent owns the outcome within guardrails | W8 p19 | Nucleon's answer: inside the policy the agent decides and the Owner only reviews afterwards; outside it, the Owner decides. Say this explicitly. |
| Friction before and after, and new friction avoided (another destination, double entry, bad timing, context switching, learning curve) | W8 p20 | The owner session is direct evidence of **learning-curve friction** (about an hour of setup on 10 Nov, most of it importing and cleaning the owners' data, the rest the settings; see 6.3), and Quick setup, the Doctor, the shorter menu and the reworded Control panel are the responses (section 5). |
| From dashboard to briefing: few items, one action each, detail on demand | W8 p21 | The Owner's Home and Decide pages: what waits, one decision each, the full request one click away. The count "N need you" sits on Decide. |
| Three use cases, the same in the deck, the test plan and the video | W8 p13 | Section 8. |
| Test plan: tester, use case, baseline, after, evidence, decision | W8 p13 | Section 5's "feedback to change" table has tester, finding and change. **Baseline and after per use case are missing.** |
| Who tested and how close they are to the real user; stand-ins named honestly | W8 p13, W9 p5-6 | Section 6: Tony and Hoang are team members acting as users (say so); the owners of the real business took part on 10-11 Nov through Hoang. The slides say **"simulated users aren't evidence"**. |
| A before and after measure: time, steps, errors, money or confidence; estimates labelled | W8 p12, W9 p6 | Before: reported by the Owner (about one request a week, 3 to 5 days, phone calls). After: measured seconds per decision. **The comparison on the owners' own scenarios and the timed session are still to come from Hoang.** |
| User quotes and dated test notes | W8 p24 | **Missing: no verbatim owner quotes are recorded.** Hoang and Tony to supply, with permission. |
| Test results that changed the design, traced to decisions | W8 p5, W9 p16 | Section 5, including the 11 Nov additions. This is the pack's strongest part. |
| What changed since Week 7 | W9 p6, p12 | Section 5 by week. |
| Go-to-market card: one customer type, channel, why switch, 90-day pilot, biggest barrier | W9 p10 | Team. Pricing and unit economics are **not required** ("value to users is assessed, not pricing"). Section 7's costs are optional background. |
| Lessons learned and next steps | W8 p5 | Sections 9 and 10. |
| Team practice: Scrum cadence, shared accountability | W8 p5 | Team (meeting rhythm, roles, how work was split). The change history in section 5 can illustrate iterations. |
| SPEC.md and PROMPTS.md kept current in the repository | W9 p17 | PROMPTS.md exists in the repository. **SPEC.md does not exist yet** (checked 11 Nov): Hanting to add it. |

### Notes on the draft slide plan (33 slides, 12 Nov)

Chris's plan follows the double diamond and already covers most of what the slides ask for. These notes only compare it with the Week 8 and Week 9 slides; the plan is the team's call.

| Draft slides | Note |
| --- | --- |
| 1 Title | The slides require more on page 1: a photo and the Scrum role of every member, the GitHub link, the live app link and any login the marker needs [W9 p4]. |
| 3-9 Discover and Define (7 slides) | The suggested budget is about 8 pages for problem and discovery together [W9 p11], so this fits. Make slide 9 ("Validating the problem space") carry real evidence: who was interviewed, when, what they said. |
| 10-12 Ideation, scope, agentic feature | The plan's own note says these can be combined. Keep slide 12 separate: the slides ask explicitly for the agent's goal, its authority, its escalation rules and which steps are human, tool or agent [W8 p19]. Pack sections 1 and 2 have the wording. |
| 13 Methodology; "Project Delivery and Team Collaboration" (unnumbered) | Team practice is a marked criterion (Scrum-style cadence, shared accountability) [W8 p5]. Give it a numbered slide. |
| 14-21 Architecture, data, rules, walkthroughs (8 slides) | Matches the suggested 7 pages for the build. Pack sections 3, 4 and 8 and the screenshots feed these. Tell the walkthroughs through the three use cases that the video uses [W8 p13]. Slide 18 "Onboarding" is new since Week 7: Quick setup and the Doctor exist because the owners needed about an hour to set up. |
| 22-25 Proof of value (4 slides) | **Too few.** The slides suggest about 7 pages and judge "With Merit" on several test rounds traced to decisions [W8 p5, W9 p11]. Suggested split: (a) test plan: who tested, how close they are to the real user, which use cases; (b) baseline today, reported by the owner; (c) what was measured after; (d) the owners' session and what they said, in their words; (e) the finding that the owners' first policy let the agent decide 0 of about 20 open invoices, and why; (f) feedback → change table (pack section 5); (g) what is still not measured. "Simulated users aren't evidence" [W9 p6]: name Tony and Hoang as team members acting as users, and the owners as the real users. |
| 23 Feedback and limitations; "Keep, Cut and Defer" | Good fit for the open-issues table above and pack section 9. |
| 26 "What does the solution solve?" | Could be the before/after slide: steps and time for one request today versus with Nucleon. Label the baseline as reported by the owner. |
| 27-30 Market, demand, go-to-market, unit economics (4 slides) | The slides ask for one go-to-market card: customer (one business type, size, place), channel, why switch, a 90-day pilot, the biggest barrier, in about 3 pages [W9 p10-11]. **Unit economics and pricing are not required** ("value to users is assessed, not pricing") [W8 p7, W9 p10]. Slides 28 and 30 could be dropped or folded into 29, freeing two pages for proof of value. Pack section 7 has the cost facts if a cost line is still wanted. |
| 31-32 Roadmap, learnings | Pack section 10. One lesson with fresh evidence: a rule written in the prompt did not stop the assistant guessing; a check outside the model did (pack section 5, live test row). |
| 33 Conclusion and video link | Fine. The video itself: max 10 minutes, at least 3 use cases, the agent acts and the owner approves [W9 p4]. |
| Missing | "What changed since Week 7" is asked for in both the deck and the video [W9 p6, p12]: pack section 5 by week. Friction before and after, and "dashboard to briefing" [W8 p20-21], are course concepts the design slides can name. |

### The gaps that matter most, in order

1. **Baseline and after, with the real owners.** Partly closed on 12 Nov: one timed session with the owners gives 42 s (agent) and under 116 s (Owner) against "about one working day" reported by the Owner (section 6.5). Still missing: an owner working without an interpreter, more than one request of each kind, and the owners' earlier scenario answers compared with the agent's one by one.
2. **Owner quotes.** None are recorded word for word. Section 6.5 has what the owners said as reported by Hoang; present it as reported feedback, not as quotations.
3. **Unit economics and go-to-market.** Not written by anyone as of 13 Nov (section 17). Problem and discovery are now in section 13.
4. **Individual portfolio.** Seven good entries out of nine are needed for Competent; this week's is due Friday 13 Nov, close of business, and the last one in Week 10 [W9 p3].

---

## 1. Nucleon in one page

**Core message.** Nucleon lets a small-business Owner hand a defined kind of credit decision to an AI assistant, inside limits the Owner sets and can change or pause at any time. The assistant does the fact-finding and, when the Owner's rules allow, makes the internal decision itself. The Owner only sees the genuine exceptions.

### What it is

Nucleon is a working prototype of a "Founder's Second Brain" (the course stream) for one narrow, painful job: **credit requests**. A small business sells to customers on credit. Customers ask for exceptions: a new customer wants stock now and pay later; an existing customer asks for more days to pay an invoice. Today each request ends with the Owner, who phones the customer to negotiate [POV-README].

The product line from the project's charter: the Owner delegates a **category of decisions and risk limits**, not an approval click for every case [ROADMAP]. Moving the click from the Owner to Staff does not help, because Staff do not want personal responsibility for credit decisions [docs/team/PRODUCT-ARCHITECTURE-BRIEF.md].

### Who uses it

| Role | What they do |
| --- | --- |
| **Staff** | Type the customer's request into a chat with the assistant ("Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit."). Confirm facts they personally saw (a deposit arrived, a business registration document) on a Nucleon page when asked. They do **not** approve credit. |
| **Owner** | Sets the limits (the "policy") once, on the Control panel. Looks at the cases that need them (the Decide page), agrees or disagrees with what the assistant decided, can override or pause. Can ask a read-only Owner assistant questions. |

Only two roles exist in the prototype. A full many-person account system was deliberately left out [REGISTER, PM-002].

### The problem it addresses (evidence to cite)

- Owner-reported baseline (31 Oct 2026, relayed by a team member who asked the business owner): about **one request for extra credit per week**, typically **about 5 days** from request to approval, **never under 3 days**; the Owner personally phones the customer; there is no delegated path today [POV-README]. SOURCES DISAGREE slightly: the plan writes "3 to 5 days each" [PLAN section 5]. Use "3 to 5 days, reported by the Owner".
- This is **reported by a person, not measured by us**, and the diary says it must be re-confirmed with the Owner before it is shown on the dashboard [DIARY, 4 Nov].
- Owner context from the 15 Oct team meeting (Hoang's reports, not a new interview): the owner weighs amount, duration, customer promises and relationship; some experienced managers would answer like the owner but hesitate over responsibility; rejected requests are generally not recorded by the business [docs/meetings/2026-10-15.md].
- External feedback, Week 7 (28 Oct): the Microsoft speaker called it "one of the best clear Founder Second Brain problems" (approximate, from an automated transcript) and placed it in the most advanced of three AI maturity stages; she asked for an "AI impact report" [FEEDBACK-W7].

### How a request flows, end to end

1. **Request.** Staff paste the customer's request into the Staff assistant chat.
2. **Evidence.** The assistant looks up the customer and invoice in Nucleon Records (the ledger of customers, invoices and payments). If a fact is missing that Staff can supply (a deposit, the business identity), the assistant says so, and a button opens a Nucleon page where Staff confirm what they saw.
3. **Evaluation against the Owner's policy.** Plain code, not the AI, checks the request against the Owner's current policy version: limits on money and days, evidence, history, track record. The AI only recommends (approve, decline or escalate) and explains [ADA section 1].
4. **Decision.** One of four outcomes [docs/team/PRODUCT-ARCHITECTURE-BRIEF.md]:
   - *Approved by the agent* (inside every limit, evidence verified, assistant recommends approval). It takes effect inside Nucleon at once (the invoice's due date moves).
   - *Information needed from Staff*.
   - *With the Owner for review* (outside the policy, records incomplete, policy paused or in advisory mode, or the assistant did not recommend approval).
   - *On hold by policy* (a customer the Owner excluded, or evidence that contradicts the records).
   Since 8 Nov the Owner may also switch on an **autonomous decline** for extensions that are clearly over a line the Owner set [DIARY, 8 Nov].
5. **Owner feedback.** For decisions the agent made, the Owner can Agree, Disagree or Override, with a reason. An override reverses it (due date restored, credit line revoked) [ADA section 7].
6. **Outcome.** Later, the records show whether the invoice was paid on time, late, part-paid, or is still open. "Pending" is a valid answer and is not the same as "paid" [TESTER-GUIDE].

### What the agent may and may not do (human in the loop)

May:
- Read records, ask Staff for missing facts, recommend.
- Make an **internal** decision (move a due date inside Nucleon, record a trial credit line) **only** when the Owner's saved policy allows it and every check passes.

May not:
- Send anything to a customer. Nucleon sends nothing outside itself; Staff tell the customer [TESTER-GUIDE, ADA section 3].
- Change or widen the policy. Only the Owner, through a person session, can save a new policy version. No chat tool can write the policy [ADA section 3].
- Treat an unknown as zero, or treat a customer's own statement ("I paid") as proof [ADA sections 5 and 6].
- Approve without a policy: with no saved policy (version 0) it is advisory and nothing executes [ADA section 3].
- Decline on its own, unless the Owner has switched on the opt-in decline (off by default) [DIARY, 8 Nov].

Safety nets the Owner always has: a pause switch (while paused, nothing is decided), versioned policies (every change is a new version, nothing lost), override with reason, and a case timeline showing who did what.

---

## 2. Glossary

**Core message.** Nucleon uses a handful of precise terms. Using them consistently in the report avoids the two biggest misunderstandings: "the AI approves credit" (it does not; the Owner's rules do) and "a model learns" (it does not retrain; it consults reviewed cases).

| Term | Plain meaning |
| --- | --- |
| **Owner / Staff** | The two roles. The Owner owns the risk and sets the limits; Staff talk to customers and run requests. |
| **Records** | The Nucleon web app that holds customers, invoices, payments, cases and policies, and enforces the rules. "The backend" in this pack. |
| **Lab / MCP** | The Lab is a small go-between service. It offers the Records' functions to the AI chat as named "tools" using a standard called MCP (Model Context Protocol, a standard way for an AI chat to call outside tools). It also turns results into the coloured decision card. |
| **LibreChat** | An open-source chat web app. Nucleon uses it as the chat window for the Staff assistant and the Owner assistant instead of building its own (decision D1, section 4). |
| **Agent / assistant** | The AI (a language model plus written instructions plus the tools). One "Staff" agent, one read-only "Owner" agent. |
| **Policy (and version)** | The Owner's rulebook: modes, limits, switches. Every save creates a new numbered version (v1, v2...). Version 0 means "nothing saved: advisory only". Each decision records which version applied. |
| **Advisory vs delegated** | Advisory: the agent only recommends; the Owner decides everything. Delegated: the agent may decide inside the policy. |
| **Exposure** | Money the business is at risk of not getting back. **Decision exposure** = what this one decision adds or extends (for a trial credit: order amount minus the verified deposit; for an extension: the unpaid amount of the invoice). **Customer total exposure** = everything the customer would owe after this decision. The policy has a separate limit for each, plus a limit on all autonomous approvals in the last 30 days [ADA section 3]. Tony's question in his 6 Nov round was exactly the difference between these two [TONY-6NOV]. On the Dashboard the customer total is shown as "Total at risk" (since 13 Nov). |
| **Trial credit** | A small first line of credit for a new customer, approved only with a verified deposit and identity, up to a small exposure the Owner sets. |
| **Extension** | A later due date for one existing open invoice. |
| **Evidence levels** | A deposit can be: *recorded payment* (in the ledger, always counts); *checked by Staff* in the bank or on a document (counts only up to an Owner-set amount); *reported by the customer* (never counts) [ADA section 5]. |
| **Escalation** | Sending a case to the Owner because it is outside the policy or unclear. |
| **Policy hold** | A case frozen for the Owner because the customer is on the Owner's "never decide" list or evidence contradicts the records. |
| **Track record** | Evidence the policy deserves autonomy: "of the past cases this policy would have approved, how many did the Owner also approve?" The Owner can require a minimum (for example 5 reviewed cases and 80% agreement) before the agent decides alone. Counts real reviewed cases and, optionally, a fictional starter set; the two are always labelled separately [PLAN D7]. |
| **Tacit agreement** | If the Owner never reviews an agent decision, after X days (an Owner setting) it is counted as "treated as agreed", recorded separately from an explicit "agree" [PLAN D8]. |
| **Comparable cases** | The closest earlier reviewed cases (other customers too), shown as "analogy, not this customer's history". Used as context and for one escalation rule, never as permission [ADA section 7]. |
| **Exception band** | Optional Owner setting (off by default, added 3 Nov): the agent may approve a request that breaches a money or day limit by a small bounded margin, if the team's model gives a high chance the Owner would approve and the Owner approved most of the closest similar cases [SHADOW]. |
| **Small overage** | Optional Owner setting (off by default, added 5 Nov): if the only failing checks are money limits missed by at most a set share or amount (the demo preset: 10% or AUD 50), the agent approves. No model needed [GIT 2026-11-05]. |
| **Autonomous decline** | Optional Owner setting (off by default, added 8 Nov, extensions only): the agent declines on its own when the assistant recommends declining and the request is over a decline line the Owner set (Hoang tested "over 30 days"). The Owner can reverse it [DIARY, 8 Nov]. |
| **Advisory "practice" mode** | A switch for Staff testers: the request runs as a preview, nothing is stored, so people can play without filling the Owner's queue (4 Nov) [GIT]. |
| **Decision card** | The coloured summary under the assistant's message. It is drawn from the Records, not written by the AI. If the chat text and the card disagree, believe the card [TESTER-GUIDE]. |
| **Quick setup** | A guided page (built and deployed 11 Nov) where the Owner answers 8 questions, sees a live preview of what those answers would do to their own open invoices, and saves a normal policy version. |
| **Doctor** | A page (built and deployed 11 Nov) answering six preset questions for the Owner, such as "Why do so many requests still come to me?" It is computed by program code from the Owner's own cases. It suggests changes with their gain and cost; it never changes a setting. |
| **The team's model / research or shadow model** | Hoang's classifier idea, plugged in as a "shadow": it scores each case (chance the Owner declines) for the Owner's eyes only and is never used for the decision unless the Owner switches on a promotion bar. It can only escalate or, inside the exception band, support an approval of a small breach [SHADOW]. |
| **Training table** | An Owner-only CSV of decided cases with their features and the Owner's actual decision, for fitting that model. |
| **Local model** | The AI runs on the team's own computer (Qwen3.5-35B-A3B in the app LM Studio), not on a cloud service. |
| **NTK** | The real business (Nutek) whose receivables ledger the team obtained; used for the real-data rounds 8-11 Nov [docs/FACTS-AND-OPEN-QUESTIONS.md]. |
| **Fictional vs live data** | Fictional: invented customers (Northside Cafe...). Live: real NTK records. Never mixed in one number [PLAN section 5]. |
| **PoC / PoV** | Proof of concept (does it work technically; Week 7) and proof of value (would people use it and does it save net work; Weeks 8 to 10). |

---

## 3. Architecture in plain words

**Core message.** Three simple pieces: a chat window, a go-between, and a records system that holds all the rules. The AI model runs on one computer under the team's control, so no per-request fee is paid and the business records are not sent to an AI company. The AI can be wrong in its wording, so the records system, not the AI, makes and enforces every decision.

### Components

1. **Chat window (LibreChat).** Staff and Owner talk to their assistants here. Open-source software run in Docker (a tool for running packaged programs) on the same computer.
2. **The AI model.** Qwen3.5-35B-A3B (a 35-billion-parameter open model that uses about 3 billion at a time, which makes it fast), served by LM Studio on the computer. The model file is 20.4 GB, run with a 32,768-token context [BENCH].
3. **The Lab (go-between, MCP server).** Offers the Staff and Owner a short list of tools. Staff tools: find customers, customer overview, invoices, assess a decision, resolve a decision, decision status, what is needed, customer status (eight). The Owner agent is read-only [BENCH, PLAN D9]. The Owner chooses which tools are switched on.
4. **Records (backend and web pages).** The business brain: ledger, policy versions, decision cases, evidence, events, outcomes. A SQLite database file (a single-file database). Pages: Home, Requests, Customers, Imports, Setup, Control panel, Decide, Dashboard, Model, Quick setup, Doctor [prototype/web/core.js].
5. **Safe public door.** For testers outside the computer: a Cloudflare Tunnel (an outbound-only secure link, no open port on the router) plus Cloudflare Access (an email one-time-code login in front of both web addresses) [PLAN D6].

### What runs where

Everything runs on **one MacBook Pro** (the "M3": model identifier Mac15,9, 48 GB memory, read from the machine on 11 Nov) that stays on. A previous second machine (called M6) was retired on 31 Oct [DIARY, 31 Oct]. Two web addresses point at the one machine: one for the chat, one for the Nucleon pages [TESTER-GUIDE]. For the real-data rounds a second pair of services (the "NTK pair") serves the imported records; the fictional demo pair runs separately and is not reachable publicly [DIARY, 7 Nov].

### Why a local model, and no cloud model

- Decision D1 of the project (15 Oct): build locally first, defer cloud hosting [docs/DECISIONS.md D001].
- Decision D5: "local first, test smaller models, cloud API as an option... positioned as the choice for businesses without hardware." Product story: fully offline is possible [PLAN D5].
- Reasons that follow from the records: no per-request fee; the business's ledger does not go to a third-party AI provider; the course requirements say the build does not need a cloud host or model training [docs/COURSE-REQUIREMENTS.md].
- A cloud model was **never tested**; it is listed as a future option because prompts and data would leave the machine and a per-token bill would apply [BENCH, recommendation].

### What data stays where (careful wording)

- Business records live in a database file on the computer. The AI model reads only what the tools return, on the same computer.
- Do **not** claim "data never leaves the computer". For remote testers, pages and chat travel through Cloudflare's tunnel, and screen sharing (Teams) is another path. The project's own notes say to confirm the exact configuration before claiming this [FEEDBACK-W7].
- Access protection: Cloudflare email one-time code first; then the app's own sign-in (chat account; Nucleon role + access code). Codes are not in this pack. Only an Owner person session can write policy; the AI and Staff cannot [ADA section 3]. Cross-site protections (CSRF and Origin checks) guard writes.
- Access codes change when the app restarts; the 6 Nov tester notes found conflicting instructions about this [HOANG-6NOV].

### Diagram to redraw (text description)

Draw five boxes left to right, with arrows labelled by what travels.

```
[Staff person]--types request-->[LibreChat chat window]--asks-->[AI model on the same computer]
                                       |  (model asks to use a tool)
                                       v
                                [Lab / MCP: tool list, builds the decision card]
                                       |
                                       v
                       [Records: ledger + Owner's POLICY (versioned) + rules in code
                                 + decision cases + evidence + outcomes]
                                       ^
[Owner person]--sets limits, decides, overrides--> Records web pages
[Owner person]--read-only questions--> LibreChat (Owner assistant)
```

Annotate: (1) "AI recommends; code decides" on the Records box. (2) A padlock between the internet and the computer labelled "Cloudflare Access". (3) A note "Nothing is sent to customers". (4) A dashed box "Team's model: scores cases, Owner's eyes only" attached to Records.

---

## 4. Design decisions and why

**Core message.** Most big decisions were made to answer one worry: "can we trust an AI with money decisions?" The answer built into the design is: rules in code decide, the AI reads and recommends, the Owner stays in charge, and every choice was tested against evidence rather than taste.

Decision dates and numbers come from [PLAN], [BENCH], [QUAL], [ADA], [SHADOW], [REGISTER], [DOCTOR-SPEC], [QS-SPEC] and [DIARY].

### Decision table

| # | Decision | Alternatives considered | Why chosen | Evidence and date |
| --- | --- | --- | --- | --- |
| 1 | **Rules decide; the model only reads and recommends.** | Let the model give a confidence score that triggers approval. | "Model-written confidence is not authority." A server-enforced policy decides what executes; the model cannot change or bypass a check. Three separate questions (is the evidence enough, is the risk inside the limits, has this policy been shown to match the Owner) instead of one score. | Charter and ADA, 26 Oct [ADA sections 1, 2]. On 30 Oct a recommendation framed as a risk parameter was caught as contradicting the Owner's goals; this led to the written four-question checklist (D13) [PLAN D13]. |
| 2 | **Local model: Qwen3.5-35B-A3B, chosen by a bench.** | Smaller models (4B, 9B), other 20-31B models, a cloud model. | Only a measured test could decide. The bench runs five standard prompts and judges by what the backend stored, not by what the model says. Bar: at least 9 of 10 runs with all five correct in at most 4 tool calls. | 31 Oct: ten other models screened. The 35B started at 5/10 runs on the bar (47/50 prompts); the best other model (qwen3.8-27b) reached 9/10 but needed a median 70.6 s per prompt, about 5x slower; the 9B scored 9/10 then 2/10 on an identical repeat (11/20). Conclusion: keep the 35B and fix the instructions instead. [BENCH, QUAL] |
| 3 | **Resolve-only instructions plus an ambiguity rule.** | A nudge message after an early stop; an extra instruction line; asking the model to check first. | The failure was the model stopping early, e.g. listing missing items instead of submitting. Removing steps worked where nagging did not. | Nudge: 6/10 runs; instruction line alone: 2/10; resolve-only: 17/20 runs (85%), 97/100 prompts, about 30% fewer tokens, 8-11 s per prompt instead of about 15 s; plus the ambiguity rule: 10/10 then 10/10 runs, 0 wrongly created cases in 20 runs on the mixed prompt, 0 of 30 on three further ambiguous prompts; 0 wrong approvals in 80 runs. Live switch 31 Oct late evening, browser acceptance 17/17. [BENCH, PLAN D15] |
| 4 | **Policy is versioned and Owner-only.** | One editable settings page; AI-suggested automatic changes. | Every decision must be traceable to the exact rules in force; a mistake can be rolled back; no silent growth of authority. Suggestions are only suggestions. | Design 26 Oct [ADA section 3]; version 0 = nothing executes. Later fix 3 Nov: old saved versions still read back after new keys were added. [GIT] |
| 5 | **Agent never declines by default; decline is opt-in.** | Let the agent decline anything outside limits. | A permanent "no" to a customer is a relationship decision; unknown whether the Owner wants it. A failed request goes to the Owner or a hold, not a refusal. | 26 Oct: "no permanent denial by the agent" [ADA section 6]. 8 Nov: Hoang's NTK test said full autonomy was incomplete without decline [HOANG-8NOV, finding "No autonomous decline: High"]; opt-in decline built the same day for extensions only, off until the Owner saves it, Owner can reverse [DIARY, 8 Nov]. Hoang's 9 Nov retest: a 60-day request was declined by the agent under a 30-day decline line; exactly 30 days was not declined; the Owner reversed the decline [HOANG-9NOV]. |
| 6 | **Evidence from Staff must be confirmed by a person on a Nucleon page, with a stated basis.** | Accept what the AI relays from chat; accept "the customer said so". | Anything the model passes along is "reported in chat" and never counts as verification. Staff confirm only what they personally saw, with how they know. A deposit Staff only checked is labelled and capped; it never creates a ledger payment. | ADA sections 5, 6 (26 Oct). Demo: Lakeside gets approved only after Staff confirm a 150.00 deposit and the business identity [TESTER-GUIDE]. |
| 7 | **Fictional and live data kept apart.** | Mixed demo and real figures. | A made-up past cannot prove real accuracy. Every figure carries a dataset label; the impact report reads only live cases; "unknown" is never shown as 0. | Plan section 5; impact module header [prototype/impact.py]; ADA section 7. A fictional "evaluation set" gives the demo a track record and is described as a simulation. |
| 8 | **Exception band and small overage.** | Keep strict limits where the Owner's real calls are almost all breaches. | Hoang's point (3 Nov): the cases that overwhelm the Owner are the ones that breach the policy, and a model that can only escalate reduces nothing. | PM-025 [REGISTER], 3 Nov. Band is off by default and only money/day checks can be inside it. Small overage added 5 Nov [GIT]. |
| 9 | **Quick setup (onboarding helper).** | Longer manual, training video, more explanatory text on the Control panel. | At the 10 Nov owner session, setup took about an hour with Hoang explaining (most of it importing and cleaning a new copy of the owners' data, then adjusting settings; see 6.3). The owners changed about 6 of more than 30 settings. Owners asked for minimalism. A helper that shows the effect on their own invoices before saving addresses the real problem: not clicking, but understanding. | [QS-SPEC]. Built and deployed 11 Nov. Answers map to settings by fixed code; no AI guesses the Owner's preferences. |
| 10 | **Doctor built by code, not by the local model.** | Let the local model read a facts sheet and answer the Owner's questions. | Trial on 11 Nov: of 24 answers from a code-written facts sheet, **19 were right and 5 wrong** (1 empty, 2 used the wrong starting number, 1 left out a cost, 1 guessed a figure not on the sheet), and each took 1 to 3 minutes. Code answers the six preset questions instantly and exactly. | [DOCTOR-SPEC, LIMITS L-004]. Live trial of the Owner assistant's doctor tool the same day: right question every time, 18-27 s each, core numbers all correct, but it dropped one figure, added judgement words and once muddled an explanation. Verdict: keep the tool as a pointer; the page is the source of truth [DIARY, 11 Nov]. |
| 11 | **Stitch LibreChat and Records, do not rebuild.** | A new custom front end; embedding one inside the other. | Two weeks to deliver; the chat to tool to backend path was already verified (17/17). The "disconnected" feeling came from two logins, no links and two visual languages, which stitching fixes. | PLAN D1 (30 Oct). Follow-up S6b (31 Oct): one entry point, link in the chat's left rail. |
| 12 | **Remove three overlapping agent runtimes down to one.** | Keep all three. | Three runtimes cost investigation time and tests. History kept in git under tag `poc-week7`. | PLAN D2. Lab tests went from 384 to 121 after the first removal [GIT 30 Oct]. |
| 13 | **Fresh fictional database for the new version.** | Migrate old data. | No legacy burden. Old databases kept in backups. | PLAN D4. |
| 14 | **Reliability gate counts real Owner-reviewed cases, with fictional starter set switchable off.** | Count only fictional or only live. | "Growing autonomy": advisory mode is shadow mode, agreement accumulates, autonomy unlocks. Small samples handled by Owner-set thresholds and labels. | PLAN D7. |
| 15 | **"Silent Owner" setting.** | Ignore decisions the Owner never clicks on. | Metrics should not ignore agent decisions just because the Owner did not click. Recorded as a separate "tacit agree". | PLAN D8. |
| 16 | **Owner assistant is read-only.** | Let the Owner decide inside chat. | Any decision, feedback or policy change stays on a Records page so there is no second write path. In testing the Owner assistant refused to approve a case and pointed to the Decide page [HOANG-6NOV]. | PLAN D9. |
| 17 | **Telemetry stored locally** (page visits, key clicks, decision durations). | Estimate Owner time. | Owner intervention time becomes measured, not guessed. | PLAN D11. |
| 18 | **Public access by Cloudflare Tunnel + Access; Tailscale retired.** | VPN for testers. | Owner opens a URL in their own browser; no software install; a login gate the app need not provide. | PLAN D6, 30 Oct. |
| 19 | **Decision checklist (D13).** | Informal judgement. | Every product recommendation answers: does it reduce Owner net work; does it advance autonomy or add a permanent human gate; is it deterministic and verifiable; is it reversible and Owner-configurable. | PLAN D13. Used in the shadow-model and model-bench write-ups. |
| 20 | **Count extension days three ways** (11 Nov): from the invoice's current due date, from the day the request is received, and from the original due date. | One day limit. | The Owner session showed 17 of 20 open invoices failed a 30-day limit because days were counted from an already-passed due date. Four 20-day extensions in a row under a 30-day limit had also been approved; counting from the original due date closes that chain. | [QS-SPEC, DIARY 11 Nov, GIT]. |

### Solution design for the three demo use cases

The policy engine treats every request in the same order of checks (the "ladder"). It is useful to show this ladder as a slide because it makes the three demo outcomes (approve, ask Staff, escalate) obvious. From `evaluate()` in prototype/delegation.py (checked against the code on 11 Nov):

1. Customer on the Owner's hold list, or evidence contradicts the records: **policy hold**.
2. Risk outside the policy (a limit fails): **Owner review**.
3. Evidence Staff can supply is missing: **request evidence** (even in advisory mode, to save the Owner a round trip).
4. Evidence insufficient and Staff cannot supply it (a data defect): Owner review.
5. A risk value cannot be established: Owner review (unknown is never zero).
6. Most of the closest comparable cases were declined by the Owner: Owner review.
7. Track record required but not established: Owner review.
8. Advisory mode, paused, or the category switched off: Owner review. (Since 31 Oct this is checked before 6 and 7, so an explicit Owner setting is always the stated reason.)
9. The assistant did not recommend approval: Owner review.
10. Otherwise: **agent approves**.

A later addition (8 Nov): over an Owner-set decline line, the agent never approves; it may decline on its own only if the switch is on and none of the Owner's own stops applies [prototype/delegation.py comment, 8 Nov].

---

## 5. Build timeline and change history

**Core message.** In 4 weeks the project went from a shared notes repository to a working, tested, publicly reachable agent product with real-business test rounds. 524 commits. The most important change pattern: each testing round produced concrete findings, and most were fixed within a day. That is the story of "design by evidence".

### Course weeks (as labelled in the repository)

Week 7 presentation: **Wednesday 28 Oct 2026**. An earlier note in the repository said 21 Oct; that was wrong: the narrated video shown at the presentation was made on 28 Oct, the team's 25 Oct post schedules the rehearsal for 28 Oct, and the seminar calendar puts Week 7 on 28 Oct [C-CHRIS, C-TONY, DIARY]. Week 8: 2-6 Nov. Week 9: 9-13 Nov. Week 10 / submission: Mon 16 Nov [POV-README]. Weeks 1 to 6 are not documented in the repository (the project record starts 15 Oct); they are in section 13. SOURCES DISAGREE about week labels in one way: the calendar in [POV-README] places Week 8 on 2-6 Nov, which leaves 26-30 Oct unlabelled (probably a break week; Not known / to confirm with Hanting).

### Activity by week (commit counts from [GIT])

| Dates | Commits | What happened |
| --- | --- | --- |
| 15-18 Oct | 86 | Repository started (15 Oct, team meeting 15 Oct). First build: a local AI case-preparation workflow with a Gemma model on a home server (16 Oct: 8/8 real-model scenarios, deployed checks, 39 unit tests). Course requirements recorded 16 Oct. Redesign, then records foundation: manual records, imports, opening balances, payments, completeness (17-18 Oct). |
| 19-25 Oct | 225 | Coordinator / "desk" agent (19-20 Oct); the "Lab" chat experiment and agent-assisted import (21 Oct); core flow with honest numbers (21-24 Oct); replay of balances; live demo fixes; presenter panel (24 Oct). Team meeting and Tony's questionnaire 21 Oct [docs/reviews]. |
| 26 Oct - 1 Nov | 164 | **Adaptive Decision Authority** (26-27 Oct): versioned policy, trial credit, extensions, Staff evidence, Owner override and pause, decision memory, comparable cases, track record. Moved from the Mac "M6" / Lab chat to LibreChat + local Qwen + MCP. 27 Oct: 17/17 browser acceptance. Demo video v2 recorded 28 Oct and shown at the **Week 7 presentation the same day** [DIARY]. 30 Oct: Week 7 feedback analysed; PoV plan D1-D15 written; unused agent runtimes removed; decision-loop backend merged. 31 Oct: Owner surfaces (Control panel, Decide page, Dashboard with impact report), Owner assistant, one entry point, model bench and qualification (see section 6), live Staff instruction switch (17/17), public access via Cloudflare, tester accounts. |
| 2-8 Nov | 21 | 2 Nov: research hook (training table, shadow score) and research loop (versions, refit, promotion bar), Owner-facing batch (notices, counter-offers, customer rules, exposure view). 3 Nov: exception band. 4 Nov: week 8 seminar follow-ups (Staff practice mode, Owner what-ifs). 5 Nov: one page per request, Decide, two policy presets, small overage. **6 Nov: first tester rounds (Tony, Hoang).** 7 Nov: real NTK records instance made the public pair (the business's owner consented that day [DIARY]). 8 Nov: **Hoang's NTK test**; code now works out extension dates; opt-in autonomous decline. |
| 9-11 Nov | 28 | 9 Nov: **Hoang's final NTK round: PASS on all 8 acceptance criteria**; Review crash fixed; invoice tool fixed. 10 Nov: **owner session** (Hoang with the NTK owners). 11 Nov: Quick setup built and deployed 14:31; Doctor built and deployed 16:21; extension-day limits (three ways) added. |

Total: 86 + 225 + 164 + 21 + 28 = 524 [GIT].

### Version and milestone tags

- Tag `poc-week7` (Week 7 code, commit 83b3efb). Tag `baseline-records-ui-20261019`. Rollback tags `ntk-before-quick-setup-20261111` and `ntk-before-doctor-20261111` [GIT tags].
- Test size: 955 test functions in the Records prototype on 30 Oct [docs/ENGINEERING-INVENTORY-20261030.md]; 1,125 records tests pass on 6 Nov, plus 131 Lab tests [GIT 6 Nov commit messages]. The number of tests is a measure of effort and care, not proof the product creates value.

### Feedback to change table

| Who, when | Finding | Change made |
| --- | --- | --- |
| Microsoft guest speaker + teaching team, 28 Oct (Week 7) | Wants measurable impact and a visible decision-feedback loop; the loop was not shown. | Impact report and Dashboard, case timeline showing request, evidence, evaluation, decision, Owner feedback, outcome; two loops kept distinct (decision learning vs commercial outcome) [FEEDBACK-W7, PLAN section 4]. |
| Week 7 presentation (28 Oct) | Audio echo broke the narrated video. | Plan for one verified audio path and captioned fallback [FEEDBACK-W7, ROADMAP]. |
| Rehearsal, 27 Oct (L-001) | A mixed message ("approved credit of 1500 AUD within 30 days extension") sent the agent into 13 and 12 tool calls and no clear answer. | Instructions: a request is one kind; if mixed or no invoice named, ask Staff and stop; never invent an invoice number. Same prompt then used 1-3 calls, 21-24 s, asked a question, created no case [LIMITS L-001]. |
| 27 Oct (L-002) | Model silently reloaded with an 8,192-token window; agent forgot its results and looped to the step limit. | Always load at 32,768; demo reset checks the setting; clearer step instructions. Results at 32,768: 3 calls, 26-32 s [LIMITS L-002]. |
| Hoang, 15 Oct meeting | Cannot treat late payment as proof of approval. | Policy keeps "unknown", never infers approvals from lateness [docs/meetings/2026-10-15.md, REGISTER PM-006]. |
| Hoang, 3 Nov | Owner's real calls are policy breaches; an escalate-only model reduces nothing. | Exception band (3 Nov) [REGISTER PM-025]. |
| Week 8 seminar testing session, 4 Nov | Testers' "zeros" in the policy (limits of 0) gave useless results; wanted to play without clutter. | Staff practice switch; deposit defaults to 0 with the label "0 = none asked"; Owner "what-ifs" (Teach it your limits); unsaved-changes warning; two policy presets (5 Nov) [GIT 4-5 Nov, DIARY]. |
| Tony, 6 Nov | Northside Cafe (Step A) escalated instead of approving; a card showed AUD 3.00. Cause: his hand-filled policy had "records must be confirmed complete above" set to AUD 3.00, and nothing said why in words. | The card now names the coverage setting as the Owner's own and says Staff cannot supply it; the Control panel explains the field and the two money limits [GIT dd6a6b2]. |
| Tony, 6 Nov | "If I accidentally approved instead of declined, could I change it?" | Owner can withdraw their own approval on the Decide page through the override path [GIT dd6a6b2]. |
| Tony, 6 Nov | "Teach it your limits" box kept deleting what he wrote. | The Model page no longer redraws while a reason box is in use [GIT dd6a6b2]. |
| Tony, 6 Nov | Could not download the training table. | Links carry the role (`?role=`); fixed 6 Nov [DIARY]. |
| Tony, 6 Nov | Wanted to open the information card himself; asked what the difference is between "most one decision may add" and "owe after the decision". | Control panel explains both limits; Staff can add information to a trial-credit case the Owner has (commit bb3d9ba) [GIT]. |
| Tony, 6 Nov (reply) | Suggested an onboarding walkthrough (optional, a video would do). | Home page "Where to start" steps (6 Nov); deeper tutorial deferred; raised in priority after the owner session [DIARY]. |
| Hoang, 6 Nov [HOANG-6NOV] | **Critical:** after Staff picked one of two requests, the assistant submitted both. | Instructions: handle only the named request; code refuses a second new case for another customer within 20 s (ONE_AT_A_TIME) (commit 94e6a39). Soft guard only (see section 9). |
| Hoang, 6 Nov | Owner pages linked to the Staff assistant. | Owner gets their own assistant link [GIT 94e6a39]. |
| Hoang, 6 Nov | Owner assistant reported 1 of 2 waiting cases. | The work-queue sentence now names every waiting decision case [GIT 94e6a39]. |
| Hoang, 6 Nov | "Evidence sufficient" and "Records complete verified" shown while the same case warned records not confirmed complete. | Label changed to "Records readable"; "readable" and "confirmed complete" are kept separate [GIT 94e6a39, delegation.py comment]. |
| Hoang, 6 Nov | Queue count in the header stayed stale until reload. | Review and case page refresh the count after a decision [GIT 94e6a39]. |
| Hoang, 6 Nov night (retest) | Form path ("Send one without the assistant") ignored written dates ("14 November 2026") and reasons. | Parser v0.3 reads written dates and a "because" reason; form requests are listed on Review [GIT 50995ac]. |
| Hoang, 8 Nov (NTK) [HOANG-8NOV] | No autonomous decline (High); two "15 day" scenarios became 46 and 66 day requests (High); pending Owner cases called "declines" (Medium); one request per message (Medium). | Code works out extension dates and asks Staff when days land in the past on an overdue invoice; opt-in autonomous decline; decline vs approval counted separately (commit 8b06697, 8 Nov; 5090507, 9 Nov). Still open: marking test cases as tests, completeness warning, production limits. |
| Hoang, 9 Nov (NTK) [HOANG-9NOV] | Assistant looped on previews without submitting; invoice-list tool returned only part of a customer's invoices; Decide page crashed on an agent decline; declines counted as approvals; hidden policy gates blocked approvals. | Staff tool profile changed on NTK (assessDecision off, invoices tool off); crash and counting fixed (5090507); invoices tool rewritten so code finds named invoices (2f4c411) — the "partial list" was the model missing invoices in a 19-28k-character result while Records returned all of them; whose-invoice and due-date-in-force fixes (bfadd21, 4093886). |
| NTK owners via Hoang, 10 Nov | About 1 hour of set-up (mostly data import and cleaning, then the Control panel, which was hard to follow); they like it if it works but fear staff learning curve; "emphasise minimalism". | Quick setup (11 Nov); fields marked Required/Optional; Doctor (11 Nov); extension limits counted three ways [DIARY, QS-SPEC]. |
| Tony, 11 Nov afternoon | Explored the NTK instance (added a customer and invoice, decided cases, fitted a model; 739 interface events recorded). | Not a finding list; data restored to the owner-session state for Hoang's timing session; his state kept [DIARY, 11 Nov]. Fixed that day: refit on an empty training table says NOT_ENOUGH_DATA. |

---

### Added on the evening of 11 November (after the week-9 session with Tony and Hoang)

Built, tested and **deployed to the shared instance on 11 November at about 23:00** (the data was left as it was; a snapshot and a rollback tag were taken first).

| Who asked | Finding | Change |
| --- | --- | --- |
| Tony (for an owner who extends credit on "a valid ABN, how long they have traded, and supplier referrals") | The Owner had no view of a new customer's business background. | When Staff confirm a new customer's business identity they may add "Registered since". An 11-digit number is checked with the ABN's own arithmetic (it catches a typing mistake; it is **not** a lookup of the government register). The Owner sees the result, how long the business has been registered, and a link to look the ABN up on abr.business.gov.au. |
| Tony ("it shouldn't affect the current decision making") | Risk of the feature changing outcomes. | It is information only. A failed check or a business registered last week changes neither the evidence status nor the outcome; three automated tests pin this. Supplier referrals already exist as "trade reference" (who vouched, what they said), asked above an exposure the Owner sets. |
| Tony and Hoang ("even I don't know what this is"; the owners' setup took about an hour) | Control panel labels and hints were hard to follow. | 49 labels and hints rewritten in plain words, each with a worked example in numbers (exposure, extensions, trial credit, unreviewed approvals, track record, exceptions, small overage, decline lines, advanced settings, scheduled changes, the model). |
| Owners (10 Nov: "emphasise minimalism"), Hoang ("fewer tabs"), Tony (merge tabs) | Eleven tabs in the bar were overwhelming. | The Owner now sees Home, Assistant, Decide, Control panel, Dashboard, Customers; Staff see Home, Assistant, Requests, Customers. The other pages sit under "More". No page was removed. |
| Hoang ("how do we close the loop" with the five answers the owners gave outside the system) | The owners' decisions on outside scenarios could not be fed back. | Model page, "Add a decision you made yourself": customer, what was asked, the decision, why. Stored like an answered what-if: it appears among the similar cases beside later requests and in the model's training table. It never counts in the track record and changes no rule. |
| Walk-through of a copy of the real-data instance as the Owner would use it (developer, 11 Nov) | The work list was called "Review" in notices but "Decide" in the bar; rows hid the invoice and amount until opened; held customers were typed as internal ids; a mistyped name was saved silently; the "Schedule" and "Save model settings" buttons did nothing; a scheduled change listed internal field names; the "N need you" count did not show on the Owner's Home. | All fixed the same night; each has a check. |
| Live test with the real assistants on the real-data instance (developer, 11 Nov, 21 conversations; data restored to its snapshot afterwards) | The Staff message "Customer 0010 wants more time to pay." named no invoice and no date. The model chose the customer's latest open invoice and exactly the 30 days the policy allows, and the request, now complete and inside the policy, was approved by the agent. The written instruction "ask, do not guess" did not hold. | A note is now attached to any Staff message that asks for more time without an invoice, or without a date or number of days: ask, and call no decision tool. Re-tested live: three vague messages each got one question and created no case; a clear request, a status question and the Owner's assistant were unaffected. Good material for "lessons": a rule in the prompt was not enough, a check outside the model was. |
| Same live test | Still open: the Owner's assistant answered "What is waiting for my decision?" with internal field names and listed only some cases; asked for "my current rules" it described which rules send requests to the Owner rather than the rules' values. The Staff assistant asked for a customer id for a customer not yet in the records instead of saying "add the customer first". | Not fixed. Use the Decide page and the Control panel for these; the pages are the source of truth. |

Checks after the changes (measured): 1,248 automated tests pass; Lab tests 133 of 133; page checks: Control panel 78 of 78, Staff information page 42 of 42, Decide 88 of 88, agent decline 12 of 12, Dashboard 34 of 34, Doctor 16 of 16, Quick setup 17 of 17. The Home page check passes 57 of 61: its four navigation-order expectations still describe the old bar and need rewriting. A walk through 59 page states of a copy of the real data as Owner and Staff produced no page error.

Why the ABN is not looked up automatically: the official register (ABN Lookup) offers a web service, but it needs a registered access key and would send customer identifiers to an outside service. For the proof of concept the person who saw the register stays the source, and Nucleon says so. A live lookup is a next step, not a claim.

---

## 6. Proof of value

**Core message.** We have strong proof that the agent decides **correctly and safely** (rule-checked, repeatable, no wrong approvals in any measured run) and that **real testers and owners can run the workflow**. We have **not yet measured** time or money saved against the old way; the only baseline is the Owner's own rough figure. Be explicit about this. The honest framing: "technical correctness proven, workflow acceptance proven with a team tester on real records, owner trust early and conditional, savings still to be measured."

### 6.1 What was measured by computers

**A. Model bench (31 Oct 2026, fictional data, 5 standard prompts)** [BENCH, QUAL]

| Test | Result |
| --- | --- |
| Reference model, original instructions, 3 runs | 15 of 15 prompts correct by backend; 2 of 3 runs on the bar. |
| Reference, 10 runs | **5 of 10 runs** on the bar (need 9); 47 of 50 prompts; 0 wrong approvals; the misses were the model stopping early. |
| Ten other models screened, plus instruction variants | None cleared the bar reliably except one 27B model (9/10 runs) at a median of 70.6 s per prompt vs 15.3 s for the reference. |
| Resolve-only instructions, 20 runs | 17/20 runs (85%), 97/100 prompts. |
| Resolve-only + ambiguity rule, 2 samples of 10 | **20/20 runs on the bar**, 100/100 standard prompts; mixed prompt created 0 cases in 20 runs; 3 new ambiguous prompts: 0 cases in 30 runs. 0 wrong approvals and 0 provider errors across the 80 runs of the last two samples. |
| Time per decision (instruction change) | About 8-11 s median per prompt (resolve-only) vs about 15 s before; median tokens about 10,300 vs 14,000+. |

Evidence quality caveats the project itself wrote: the ambiguity paragraph was tuned on the same wording it was tested on; the three extra prompts were written after seeing the failure; a differently worded ambiguous message could still be submitted, producing an Owner case but never a wrong approval [BENCH, A5].

**B. Browser acceptance with the real model and chat** (fictional data)

- 27 Oct: 17 of 17 checks (extension +23 days, Northside trial credit, Lakeside after Staff evidence, Harbourline to the Owner, "just say yes" probe answered correctly, override, pause/resume, no outbound actions, no ledger payment created from Staff evidence) [docs/team/PRODUCT-ARCHITECTURE-BRIEF.md].
- 31 Oct, after the live instruction switch: 17 of 17 again. Decision card appeared 10.7 to 15.4 s after the prompt; full turns 8.3 to 24.7 s. Owner assistant acceptance 5 of 5 (22.9 s to 45.4 s per answer) in the 9B model trial [BENCH, S7 phase B and S6d phase 2].
- Response times for testers: [TESTER-GUIDE] says the decision card usually appears in 10-20 s and the full reply in 30-60 s. Earlier (before the instruction change, 27 Oct, 32,768 window) the same prompts took 26-32 s, and earlier still 33-60 s with up to 12 tool calls [LIMITS L-002].
- Week 7 demo timing (24 Oct, older Gemma-model version): 3:22 and 3:29 on two clean rehearsals; three earlier attempts failed or ran long (6:50, 5:57, stopped) because another application on the network was using the same model at the same time [docs/DEMO-SCRIPT.md]. This is useful as a lesson on shared hardware, not as a current performance figure.

### 6.2 What testers did and found

| Round | Who | Data | Outcome |
| --- | --- | --- | --- |
| 6 Nov | **Tony** (as a test user following the tester guide, both roles) | Fictional | Steps B and D worked and Step C went through to Owner review; Step A escalated unexpectedly because of a 3.00 setting; several usability findings (section 5). All fixed or answered 6 Nov. Re-test not yet scheduled [DIARY]. |
| 6 Nov | **Hoang** (Staff, Owner and mobile) | Fictional | Verified: role access, ambiguous request produced a clarification and no case, a valid extension created an Owner work item with comparable cases, Owner approval moved the due date (18 Oct to 10 Nov 2026), notices to Staff, Review queue cleared, Owner assistant refused to approve, mobile layout readable, no browser errors. One critical, three high, three medium, one low finding, all handled the same day [HOANG-6NOV]. |
| 8 Nov | Hoang, real NTK records (20 customers, 137 invoices, 113 payments imported) | **Real** | 5 targeted scenarios: 2 autonomous approvals, 3 Owner cases; no customer message sent. "Core workflow is operational." Main gaps: no autonomous decline; date arithmetic [HOANG-8NOV]. |
| 9 Nov | Hoang, final round | **Real** | **All 8 acceptance criteria PASS** (below). Final counts: 2 agent approvals, 0 active agent declines, 1 Owner override, 3 live test cases [HOANG-9NOV]. |

The 8 criteria Hoang passed on 9 Nov [HOANG-9NOV]:
1. Autonomous approval of appropriate requests.
2. Autonomous decline only when the recommendation and configured line permit it.
3. Requests over the decline line are not autonomously approved.
4. Ambiguous overdue extensions require clarification before a case is created.
5. Dates and day counts remain consistent.
6. Owner escalation and reversal work end to end.
7. Staff, Review, Home, Control and case timelines show consistent statuses.
8. No customer communication is sent.

Scenario evidence (9 Nov): invoices 00000085 and 00000086 approved by the agent, each moved by exactly 15 days to 12 Nov; invoice 00000079 asked a date question and created no case; invoice 00000077 (a 60-day request) declined by the agent and then reversed by the Owner (due date 8 Dec); exactly 30 days did not trigger the decline; a 90-day request went to the Owner.

Important qualification: Hoang tested with **very broad, test-only limits** (365-day maximum, extremely high money limits, removed gates). Those limits show the machine works, not that the business's real limits are safe or sensible. Hoang's own report says production limits must be confirmed by the Owner [HOANG-8NOV, HOANG-9NOV, DIARY 9 Nov].

### 6.3 What the owners said (10-11 Nov)

Reported by Hoang from the session with the NTK owners [DIARY 10-11 Nov, QS-SPEC]:
- Setting up took **about one hour**, with Hoang explaining.
- They find the product "very helpful if it works".
- They fear the staff learning curve would push staff back to asking the owners. Their suggestion: **emphasise minimalism**.
- They changed about 6 of more than 30 settings.
- Hoang's answers on 11 Nov: the hour went on understanding the Control panel; the owners mean "30 days after the due date", so the existing counting matches them; predictability was not tested yet.
- **Correction, 12 Nov [MEETING-1112].** Hoang explained that he did not use the copy of the owners' data that had been imported for him beforehand: he uploaded and cleaned a new copy during the session, then adjusted many settings. So most of the hour went on **importing and cleaning data**, and the rest on settings whose wording was hard to follow (rewritten on 11 Nov). SOURCES DISAGREE with his 11 Nov answer above ("the hour went on understanding the Control panel"); the later, more detailed account is the better one. On a slide, say "about an hour of set-up, mostly importing the business's data", not "an hour on the Control panel". Nobody timed the two parts separately.

Use these as qualitative owner testimony. Get Hoang to confirm exact wording and ask the owners' permission before quoting them by name or role. "Not known / to confirm with Hoang": whether any direct quotations were recorded.

**The finding that matters most.** On the data of the owner session, the owners' own saved policy let the agent decide **0 of 20 open invoices** (in the check done during the session analysis [QS-SPEC]) and **0 of 22** on the live Quick setup that afternoon [DIARY 11 Nov]. SOURCES DISAGREE on the count (20 vs 22): they were taken at different moments; give both. Why 0: 17 of the 20 failed the 30-day limit because the invoices were already long overdue and days were counted from the due date; 16 failed "nothing else overdue", a default the owners never touched; 8 belonged to the two customers the owners had put on hold. Allowing other overdue invoices would give 2 of 20; also raising the day limit to 60 would give 9 of 20 [QS-SPEC]. The Doctor's combination test gave 2 of 22 (other overdue allowed), 3 of 22 (90-day limit), 11 of 22 (both together) [DOCTOR-SPEC]. 

How to tell this story on a slide: "The product worked as designed, but the owners' first policy made the agent safe and useless. That is why we built Quick setup and the Doctor." It shows the cost of caution and the importance of onboarding. It is not a failure of the rules: the rules did exactly what the owners said.

During that session, six scenarios were run afterwards: the agent approved none on its own; three went to the Owner, two were held, one was declined by the agent [QS-SPEC]. SOURCES DISAGREE: the diary says Hoang collected the owners' decisions on **5** scenarios. Not known / to confirm with Hoang: whether it was five or six, and the owners' actual answers.

### 6.4 Savings: what we can and cannot say

| Claim | Status |
| --- | --- |
| Baseline: about 1 credit request per week, 3-5 days each, Owner phones the customer. | **Reported by the Owner** (31 Oct); relayed second-hand; must be re-confirmed with the Owner. Not a measurement. [POV-README, DIARY] |
| A delegated request is decided in seconds to a minute or two (card 10-20 s; whole turn up to 60 s). | **Measured** on fictional and NTK test data, by the team's testers. |
| Therefore decisions can take minutes instead of days. | A **reasoned comparison** between a measured figure and a reported baseline. Say exactly that. It says nothing about how often the policy lets the agent decide on the owners' real traffic (the 0 of 22 result shows it can be none). |
| Owner time saved per week. | **Not measured.** The dashboard's "Time saved" tile intentionally shows "unknown" with the note "manual baseline not measured; set from PoV interviews" [prototype/impact.py]. At about 1 request a week, a few sessions cannot give a statistically meaningful number [POV-README]. |
| Dollar savings. | **Not measured; do not invent.** |
| After negotiation, the internal decision takes about 42 s (agent) or under 2 min (Owner) instead of about one working day. | **Measured** in one facilitated session with the owners (6.5) against a baseline **reported by the Owner**. Say both halves. |
| Owner's 5 (or 6) scenario decisions vs the agent's outcomes. | **Still not compared one by one.** The session of 12 Nov tested fresh requests instead (6.5). Not known / to confirm with Hoang: whether the earlier five answers were written down. |
| Timed workflow session with the owners. | **Done on the night of 11-12 Nov**: see 6.5. [NTK-SESSION] |
| Real repayment outcomes after agent decisions. | **Not available**: no real decision has had time to be repaid; the outcome shows "pending". [TESTER-GUIDE, ROADMAP] |

What the Dashboard can show (so you can screenshot and describe): cases, share decided by the agent, share sent to the Owner, overrides and disagreements, the Owner's agreement (explicit and tacit), information requests to Staff and time to answer, median time to decision, Owner time per case, and a "Time saved" tile marked as an assumption. Every tile says whether its number is measured, derived or assumed [prototype/web/dashboard.js, impact.py].

### 6.5 The timed session with the owners (night of 11-12 Nov)

Source: Hoang's write-up "Nucleon Owner Testing Session Summary for NTK" [NTK-SESSION], checked against the server's own event times. Hoang ran the session with the NTK owners on the real-data instance (20 customers, 137 invoices, 113 payments; policy version 1: up to VND 2 billion per decision, VND 10 billion total exposure, 30 days past the current due date; Customers 0012 and 0018 always go to the Owner; autonomous decline on). The requests were fictional. Nothing was sent to any customer and no invoice date changed.

**Timing (measured by Hoang with a stopwatch; "negotiation finished" means the customer's final position is known, so only the internal decision is timed).**

| Run | Staff typing | Assistant and system | Owner | Result |
| --- | --- | --- | --- | --- |
| First use: Customer 0010, invoice 00000080 | 9.7 s | 77.3 s over 3 replies | not decided in this run | **87.0 s** until it was in the Owner's list |
| Decided by the agent: Customer 0014, invoice 00000066 | about 7 s | about 35 s | none | agent decline recorded in **about 42 s** |
| Decided by the Owner: Customer 0011, invoice 00000087 | 12.5 s | 43.6 s | under 60 s (the final click took 7.9 s) | **under 116.1 s** of internal work; the Owner declined |

Five assistant answers were timed: 24.5, 25.6, 27.2, about 35 and 43.6 seconds (median 27.2 s). They are different kinds of request, so this describes one session and is not a service level.

**The baseline the owners gave.** For the same internal step (after the customer's final position is known), the Owner said it normally takes **about one working day**. This is reported by the Owner, not measured. It is a narrower figure than the "3 to 5 days per request" reported on 31 October, which included phoning the customer. Use "about one working day" against the 42 s and 116 s figures; use "3 to 5 days" only for the whole request including negotiation.

**How to state the comparison honestly.** "After negotiation, the internal decision took about 42 seconds when the agent decided and under 2 minutes when the Owner decided, against about one working day reported by the Owner." Add the three caveats that Hoang wrote down himself:
1. **Hoang acted as the interpreter**: he clicked for the Owner and asked aloud the questions the screen showed. The Owner timing is that of an owner who already knows the screen, not of an owner alone on first use.
2. One request of each kind was timed. It is one session.
3. Login, access codes and waiting for the customer were left out.

**What the tests showed about decisions.** Requests went to the Owner where the policy says so; one was declined by the Owner; one was declined by the agent under the owners' decline rule. The agent approved nothing on its own in this session, which is consistent with the "0 of 20" finding in 6.3 (the owners' policy is strict and most invoices are long overdue).

**What the owners said (as reported by Hoang; not word-for-word quotes).**
- The product worked well, and the Staff workflow worked well.
- The interface could be overwhelming.
- Many elements were hard to understand without someone explaining.
- Onboarding was hard because of the amount to learn at the start.

**Two faults found in the session, both fixed and re-tested on 12 November.**

| Fault | Cause (checked in the records) | Fix | Re-test |
| --- | --- | --- | --- |
| Staff asked for **31 December**; the case was recorded as **1 December** (78 days). | The model turned the date into a number of days itself and got it wrong (31 December is 108 days after 14 September, not 78), while its written reasoning still said 31 December. The backend trusted the number. | The backend now compares the date in the assistant's reasoning with the date that would be recorded and refuses the call when they differ ("DATE_MISMATCH"); the assistant must send the date Staff gave. Same principle as before: the model proposes, code checks. | The same sentence on the live instance: recorded 31 December, 108 days, declined by the agent in 32 s. A second request with a date (20 December) was also recorded correctly. |
| The chat card for the agent's decline was headed "STATUS UNAVAILABLE" although its text said the agent declined. | The card had no heading for "declined by the agent" (the feature is one week old). | The heading now reads "DECLINED UNDER THE OWNER'S DECLINE RULES — DECIDED BY AGENT". | Seen on the live instance in the same re-test. |

The wrong date did not change the outcome of that case: 108 days is over the 30-day decline line just as 78 days is. It would have mattered for a request near a limit, which is why it was fixed the same day.

**Why the first-use run lost about 52 seconds** (Hoang's count: extra assistant time plus one more Staff reply):
- The customer was named by its real business name, but the imported records hold only "Customer 0010" (the names were replaced with numbers before import). The assistant could not match it and asked. With real names in the records this step disappears.
- The assistant said no number of days had been given although the message said "15-day". That was a fault in the safeguard added on 11 November (it did not read "15-day" with a hyphen as days). Fixed on 12 November.
- Staff then gave 27 November as "15 days". The system's business date was still 11 November (it was just after midnight in Sydney), so 15 days gave 26 November, and the assistant asked which was meant. This is the intended behaviour (it never picks between two readings), but it cost one more round.

**What this adds to the proof of value, and what it still does not.** It is the first timing with the real owners in the room and their own baseline for the same step. It is still one facilitated session with fictional requests; it does not show an owner working alone, a week of real traffic, or any repayment outcome. The strongest honest sentence about onboarding: "The owners said the product works and the Staff side is easy, and that the Owner side is too much to take in at first. Setup took about an hour on 10 November, mostly importing the data, and on 12 November the Owner still needed an interpreter."

### 6.6 A second owner, alone at the screen (afternoon of 12 Nov), and what was built from it

Source: the audio transcript of the session, the facilitator's handwritten notes, and the system's own records (page log, policy versions, cases, the assistant's conversations) [SESSION-1112PM]. Tony ran it in person with the owner of a food wholesale business, on the fictional demo data (six customers, AUD). This owner uses computers every day and says his staff do not. The session did not follow the playbook step by step: two tasks were done by the owner alone, the rest was a guided demonstration with his own questions, then an interview.

**What the owner did alone (times from the system's records).**

| Task | Result | Time |
| --- | --- | --- |
| Set the rules for the agent | Done without help, with Quick setup. He clicked "Control panel" first and reached Quick setup 56 seconds later | **2 min 37 s** from the first click to the saved rules (the facilitator's stopwatch: 2 min 33 s) |
| A request arrives (Bayview, 23 more days) | The card came after 14 s and said it goes to the Owner, because 23 days is more than the 14 he had just allowed. He went to the Decide page without being told and approved | **9 s** from starting to decide to done; about 2 minutes in all with reading |

Three decisions were recorded in the session: one by the Owner, two by the agent (Northside Cafe in 13 s; Lakeside Kiosk after Staff supplied a deposit and a business identity). No override, no decline.

**How this differs from 6.5.** In 6.5 the owners needed an interpreter. This owner did not: for him the Owner side is usable but long and wordy. Together the two sessions say: the difficulty depends on the person, and the product needs a short path for the first use and a way to show less. One comfortable owner is not evidence that owners in general can start alone.

**What he said (quotes from the transcript).**
- On the Control panel: "It's not confusing, it's probably more that the interface maybe is a little bit clunky or a bit wordy." He would not remove any setting.
- On presets: "Maybe what would make this easier is to have some presets, so you might have harsh, relaxed, medium." His reason is safety: a non-technical owner could put the wrong number in the wrong place.
- On the first use: "This should just be like a let's get started button... it's about minimizing the journey to get to the answer."
- On what staff see: "It's like trying to get fruit from a pomegranate: it's a lot of work for a little bit of fruit." And: "There's got to be a simplified view for the person who's literally just looking for the conclusion... They're just driving the AI, they're not programming the AI."
- On value: "It would minimize the amount of technical training I'd need to do with new staff around when to contact people about their outstanding accounts."
- On the idea as a whole: "It does make sense. It's not an invalidated concept... it just needs more alignment to reflect what day to day practices look like and the tech capacity people have in entry-level positions."
- He has not decided to use AI at all: "I still don't know that I want to go into AI."

**What he asked for that Nucleon does not do** (use these as limits and roadmap, not as faults):
- Tell him when a customer will probably pay, from their history ("usually pays 25 days overdue; this invoice is 20 days overdue").
- List who is overdue and by how many days, the way a statement does (0 to 30, 30 to 45, 45 to 90 days), not every balance.
- Look up a business's ABN and warn when it changes or closes. Nucleon only checks that an ABN is well formed; a lookup needs an outside data service. In his words, if the tool sends him back to do that work "it's kind of just making the steps look prettier".
- Connect to the accounting and payment software (he named Xero and Stripe) and to the bank, and work every morning without being asked.

**Where the system fell short in the session (checked in the records).** The assistant said it had no access to ABN information, and could not say when a payment is likely: both true, neither exists. It wrongly said an invoice due 19 November had passed its due date (a wrong sentence by the model; the demo's "today" is fixed at 24 October and he had entered an invoice dated 12 November). When he changed a limit in Quick setup the preview showed the same numbers and gave no sign that it had been worked out again.

**What was built the same evening (12 Nov), from this session and from 6.5.**

| Change | Asked for by | What it is |
| --- | --- | --- |
| Get started | This owner ("let's get started button") | One path of three steps from Home: how strict, customers to keep, how much the pages show. Nothing is saved until the last button |
| New customers in Get started and Quick setup (13 Nov) | Found while rehearsing the video: from a clean start trial credit stayed off, so every first order went to the Owner | Step 2 asks whether a new customer's first order always comes to the Owner or may be decided by the agent: up to the level's one-request limit at risk, a deposit of at least a quarter, 30 days, identity confirmed by Staff. Unchanged answers write nothing. 5 unit tests and a page check |
| Three levels: Strict, Balanced, Relaxed | This owner ("harsh, relaxed, medium") | Each fills six answers, worked out from the business's own open invoices, and shows what the agent would then decide. Settings a level does not cover are left as they are |
| Three display levels: Simple, Standard, Detailed | Both sessions ("overwhelming"; "a simplified view and an advanced view") | Simple hides the explanations, shortens the Owner's menu to Home, Assistant, Decide and Rules, and folds the occasional sections. Standard shows one line of each explanation. Detailed shows everything. It changes only what one browser shows, never a rule |
| Quick settings on the Control panel | Hanting (so nobody has to run Get started twice) | The same three choices at the top of the Control panel, with icons and a row of links to each section |
| One-line briefing on Home | 6.5 | "3 requests are waiting for your decision" and one button |
| One-click reasons on Decide | 6.5 (a reason is required and was easy to miss) | Common reasons fill the box and can be edited. A reason stays required: the reasons are what the business will learn from |
| A note when a change alters nothing | This session | Quick setup now says "worked out again: the same result" |

Checked by 1,254 unit tests and nine browser check suites (28 new checks for these pages), all passing. **Not yet tested with any owner**: the claim that these changes make the first use easier is a hypothesis until someone watches an owner use them.

**Later the same evening: a Staff-side look and the owner's extra comments [MEETING-1112].** Reported by Tony at the team meeting; informal, not timed, and not checked against the system's records.
- A Staff-side tester (a relative of a team member, shown the new pages and the chat late in the evening) found the interface intuitive and quick to pick up: "very standard procedure" for staff who know where to find things. She liked the new interface. She **could not judge the answers**, because she did not know the fictional data and could not make up a realistic request on the spot. Lesson for any further Staff test: give a short briefing on the demo customers and invoices, or test with the tester's own records.
- Tony expected Get started to be a guided tour through every page, as new apps have, and thinks onboarding still needs more. The team did not build a tour: owners use different parts of the product, so one long tour would be slow for most of them. Tony agreed that building every owner's wish would add too much. It is on the roadmap (section 10).
- The owner also found the Dashboard's "Exposure now" table confusing: for one customer three columns showed the same AUD 480 (what is owed, what is overdue, and exposure). He wants financial-statement words such as "outstanding balance". Tony rated it low priority. The figures match because that customer has one open invoice, all of it overdue, and no trial credit. **Changed on 13 Nov (wording only, no calculation changed):** the table is now headed "What customers owe now", with the columns Outstanding balance, Of which overdue, Trial credit in force, Total at risk and Limit, and a line under it saying total at risk = outstanding balance + trial credit, and why the columns can match.
- Tony's reading of the interview: the owner was confident with the controls himself and worried mainly whether his staff could use the system; he said it would save time if it means fewer phone calls, and that it is reliable for the way his business works. He would like an assistant that warns him on its own (for example, a customer about to close who has not paid), and one that does not flag a customer who is always about seven days late. Nucleon's track-record settings can learn the second over time from the Owner's decisions; the first needs outside data and is roadmap.

**Decided against, with the reason.** Folding the evidence on the Decide page (the Owner needs the facts in front of them to decide). Making the reason optional (the reasons are data for later). Filling "still owed" with the invoice amount when an invoice is typed in (an invoice amount alone does not say what is still owed; the records keep "stated" and "worked out" apart on purpose).

---

## 7. Cost

**Core message.** The prototype costs almost nothing to run per request because the AI model runs on hardware the team already owns and uses free open-source parts. The cash spent was about USD 2,500 of AI coding assistance for the whole project and about USD 50 a year for the domain and public access. What Nucleon would cost to sell or support is unknown, so pricing is the team's decision.

### What the proof of concept cost (figures from Hanting, 11 Nov 2026)

| Item | What it is | Cost |
| --- | --- | --- |
| Main computer | One MacBook Pro, M3 Max with 48 GB memory and 1 TB storage. It runs the whole product: the records app, the chat app and the AI model. It stays switched on. | Existing machine. Valued at **A$5,919**: Apple Australia's certified-refurbished price for this exact model (16-inch, M3 Max 16-core CPU and 40-core GPU, 48 GB, 1 TB), looked up 11 Nov 2026. |
| Second computer | One Mac mini (the "M6"), 32 GB memory and 1 TB storage. It hosted the first shared deployment until 31 Oct, then was retired when everything moved to the MacBook Pro [DIARY]. | Existing machine. Valued at about **A$2,799**: the price Australian retailers list for a new Mac mini M6 with 32 GB and 1 TB, looked up 11 Nov 2026. Apple's own page for this configuration could not be read, so check apple.com/au before quoting it as Apple's price. |
| AI coding assistant | Claude Code usage (tokens) over the whole project. | **About USD 2,500.** This covers more than the prototype: it also includes preparing and processing the interviews and preparing the presentations. Say "about USD 2,500 for the whole project, not only the build". |
| Domain and public access | The domain and Cloudflare (tunnel and access control) that put the product online for testers. | **About USD 50 a year** (Hanting's estimate). |
| AI model | Qwen3.5-35B-A3B, 20.4 GB on disk, runs on the MacBook Pro. | **No fee per request.** Licence terms of the model for commercial use not checked: to confirm before any sale. |
| Other software | LM Studio (runs the model), LibreChat (the chat window, open source), Docker, SQLite. | No charge in the proof of concept. LM Studio's terms for commercial use: to confirm. |
| Electricity | The MacBook Pro runs continuously. | Not measured. |
| People's time | Development, testing rounds (Tony, Hoang), the owner session (about one hour of setup). | Hours not recorded. |

How to say it on a slide: "Running cost per decision is close to zero because the model runs on a computer we already own. The project's cash cost was about USD 2,500 of AI coding assistance (shared with interview and presentation work) and about USD 50 a year for the domain and public access. Hardware was existing equipment, worth about A$8,700 at today's prices (A$5,919 + A$2,799)."

Mind the currencies: the hardware is in Australian dollars, the AI assistance and the domain in US dollars. Do not add them without converting.

What this does **not** tell you: what a customer would need to buy. A business adopting Nucleon as built needs a computer able to run a 20 GB model (see the next table) or a cloud model, which was not tested.

### Performance data useful for a cost argument (measured)

- The model needs a machine with enough memory: 20.4 GB for the model plus its working memory; a smaller 9B model (6 GB) was tried and was not reliable enough on the bench (11 of 20 runs) [BENCH].
- Tokens per decision: about 10,300 prompt and 660-735 completion tokens for the final instructions [BENCH]. This number would matter only if a cloud model were used. **Do not convert it to dollars**: the bench's cloud-price option was never run.
- Time per decision on this hardware: 8 to 11 s median for the model's part [BENCH].

### What we do not know (the unknowns to state on a slide)

- What price the Owner would pay and for what (per month, per decision, installation).
- Whether a business without suitable hardware would need the cloud-model option (not tested; prompts and data would leave the computer and per-token fees would apply) [BENCH].
- Support and maintenance cost per business (for example the "context reset to 8,192" problem shows operations need care [LIMITS L-002]).
- Setup cost per customer. The only data point: about 1 hour of guided setup before Quick setup existed, most of it importing and cleaning data (6.3); the settings alone took 2 min 37 s for the second owner with Quick setup on fictional, already-imported data (6.6). Quick setup's aim is about 10 minutes [QS-SPEC] (a design target, **not measured**).
- The cost of a wrong approval. The system reduces the chance by design, but the Owner's acceptable loss is **not ratified**; no thresholds were adopted [ROADMAP].

### Decisions the team must make (pricing is the team's call)

1. Pricing model (subscription, per case, setup fee) and how it compares with the Owner's current phone-and-wait cost, once the Owner's time cost is known.
2. Whether to sell as "bring your own computer" (local) or a hosted option.
3. Whether to present any cost figure at all without a measured baseline. Recommended: show the cost structure (low running cost, one-off hardware, people time) and mark any price as a proposal.

---

## 8. Three demo use cases

**Core message.** Three requests, same assistant, three different correct outcomes: approved by the agent, held for missing facts then approved after Staff confirm them, and escalated to the Owner. Change one setting and the outcome changes. The point to land: the AI does the legwork, the Owner's rules decide, and the card on screen is the truth.

All names and amounts are fictional (AUD). Source: [TESTER-GUIDE], the demo runbook (deploy/m3-local/demo-runbook.html), and the demo data module (prototype/delegation_demo.py, six customers, as of 24 Oct 2026). Note: docs/DEMO-SCRIPT.md is the **old Week 7 script** (Gemma model, a different desk-style interface and VND data); do not use it for the final demo.

### Setup: the Owner sets the limits (about 1 minute)

Owner, Control panel, enter and press "Save as version 1" [TESTER-GUIDE Step A]:

| Setting | Value |
| --- | --- |
| Mode | Delegated |
| Most one decision may add | 1000.00 |
| Most one customer may owe you in total | 1500.00 |
| Extensions | Agent may decide, longest 30 days |
| Trial credit for new customers | On; most exposure 600.00; smallest deposit 25% |
| Advanced | max agent-approved in 30 days 5000.00; trial terms 30 days; trade reference needed above exposure 1000.00; a Staff-checked deposit counts up to 600.00; unusual size 3 times the customer's usual; track record 5 reviewed cases and 80% agreement; "an extension needs nothing else overdue" ticked |

Expected: page shows "policy version 1, Delegated". The track-record check uses made-up past cases for this demo, so it is a simulation, say so [runbook].

**The video uses Get started instead (13 Nov).** Home → Let's get started → **Relaxed** → step 2 "The agent may give a small first order on credit" → Save. That gives one request up to AUD 900, trial credit up to AUD 900 at risk, deposit at least 25%, 30-day terms, and the same three outcomes with the same amounts (rehearsed with the real model, 8 of 8). Balanced would cap a first order at AUD 480 and send Northside and Lakeside to the Owner. With this set-up Harbourline's AUD 4,000 is over a AUD 900 limit, not AUD 1,000.

### Use case 1: Northside Cafe, approved by the agent

Staff, new chat with "Nucleon ADA Staff (Qwen)", type exactly:
> Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit.

Expected (card in 10-20 s, full reply up to 60 s): **Approved under policy version 1.** Order AUD 800 minus a verified deposit of AUD 200 (reference DEP-NS-01) leaves AUD 600 exposure, within the AUD 600 new-customer limit. Every limit checked is listed. Nothing is sent to the customer; Staff tell them.
Point to make: a new customer is no longer another phone call to the Owner. An early "Would be decided... preview" card is not the decision; wait for the final one.

### Use case 2: Lakeside Kiosk, missing facts, then approved

Staff, new chat:
> Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.

Expected: an amber card, **Information needed from Staff** (no record of a deposit or the business identity). It does not go to the Owner. Press "Provide information in Nucleon" (needs the Staff session) and fill in: amount received 150.00; date 24 Oct 2026; reference DEP-LK-FICT-01; how you know "I saw it arrive in the bank account"; business registration number 000 111 222 (fictional); trading name Lakeside Kiosk Pty Ltd (fictional); basis "On a document". Submit and scroll to the top.
Expected: Nucleon checks again. AUD 600 minus AUD 150 = AUD 450 exposure, inside the limits, so the agent approves. The deposit is labelled "checked by Staff", not a ledger payment.
Point to make: Staff confirm only what they saw; this answers "who verified it?".

### Use case 3: Harbourline Catering, over the limit, escalated

Staff, new chat:
> Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms with a deposit.

Expected: **Sent to the Owner, nothing approved.** AUD 5,000 minus a AUD 1,000 deposit = AUD 4,000 exposure, over the AUD 1,000 limit for one decision. The card names the limit that failed.
Then Owner, Decide page: Harbourline waits under "Needs your decision" with a reason box and Approve / Decline. Northside and Lakeside appear under "Decided by the agent" with Agree / Disagree / Override.
Point to make: the system holds the agent to the limit whatever the AI says.

### Bonus: an extension inside the limits (Bayview Gelato Co)

Bench-tested prompt: "Bayview Gelato Co asks to move invoice DEMO-301 to 10 November 2026." Invoice DEMO-301 is AUD 480.00, due 18 Oct 2026; moving it to 10 Nov is +23 days, inside the 30-day limit. Expected: **Approved under owner policy**, due date moves to 10 Nov. Seen in the 31 Oct acceptance: card at 10.7 s, whole turn 12.8 s [prototype/delegation_demo.py, BENCH]. Two other fictional cases are handy: Cityside Desserts (DEMO-410, +14 days) goes to the Owner for **unusual size**; Riverside Foods (DEMO-505, +10 days) goes to the Owner because **records are incomplete** (not a decline) [delegation_demo.py].

### Change one setting and see a different outcome

Pick one:
- **Pause.** Owner presses Pause on the Control panel; Staff repeat a request for a new customer; the result is "With the Owner, paused" and nothing is decided (seen in acceptance, 20.1 s). Resume restores it [BENCH S7 phase B].
- **Raise the limit.** Save version 2 with "Most money one request may involve" at 5000.00 and the trial exposure limit raised accordingly; a Harbourline-style request now passes the money check. The policy version on the card changes to v2. (The recorded demo runs each case once per reset; a second run returns the stored result. Use a fresh reset or a new customer.) The exact values to reach approval were not tested in the records: Not known / to confirm with Hanting before filming.
- **Quick setup.** On the real NTK data, show the 0 of 22 open invoices, then answer the questions differently and show the preview rise (section 6.3).

Reset between takes: the runbook's `demo-reset` command restores clean data (policy v0). Do not run it on the NTK instance.

---

## 9. Known limitations and honest caveats

**Core message.** Be upfront. The strongest reports say what was proven, what was not, and why.

From [LIMITS] and other project records:

1. **The model is the weak point, the backend is the guard.** In every logged failure the backend refused invalid input and approved only what the policy allowed. The failures were in the model's tool use and wording [LIMITS]. Rule: believe the card, not the chat text.
2. **Early-stop and looping behaviour.** The reference model sometimes stops before submitting; the final instructions reduce but do not remove this. A 20-run sample is small. Different ambiguous wordings are untested [BENCH].
3. **Model setting fragility.** If the model is reloaded with an 8,192-token window, the agent loops. The demo reset checks this. The cause was unattended reload after 1 hour idle [LIMITS L-002].
4. **One request per Staff message is a soft guard.** It is a 20-second rule that also refuses a colleague's request within 20 s of someone else's; a hard rule needs per-user identity through the chat [DIARY, pending #2].
5. **Single computer, single model at a time.** The model serves one request at a time; another application on the same model slowed Week 7 rehearsals from about 4-19 s to 30-220 s per turn [docs/DEMO-SCRIPT.md].
6. **Numbers are fictional unless stated.** The track record in the demo is back-tested on a made-up evaluation set. "No NTK accuracy has been substantiated" [REGISTER, charter].
7. **No real repayment outcomes yet.** Outcomes read "pending" until a payment is seen. The "learning" is case memory, comparisons and policy suggestions. It is not model retraining [FEEDBACK-W7, charter].
8. **The team's model is a shadow.** It is trained on the fictional decision memory until real decisions exist; Hoang's earlier notebook used lateness proxies (85 rows, 8 denials) and the project does not treat proxies as Owner decisions [SHADOW, REGISTER PM-014, DIARY]. Agreement is one number; no per-class precision and recall at scale.
9. **Test limits are not production limits.** Hoang's NTK limits (365 days, very high money limits) are test-only [HOANG-9NOV].
10. **Overdue days count from the ORIGINAL due date, even after an approved extension** (by design so far). The model once rewrote a day count in its reply [DIARY 9 Nov]. Quick setup adds limits counted from the request day and from the original due date (11 Nov).
11. **Quick setup preview is an estimate**: it assumes the assistant would recommend approval, tests 7, 14 or 30 more days, and covers at most 200 open invoices [LIMITS L-003].
12. **Doctor what-ifs leave out** the assistant's recommendation, the track-record gate, advisory mode and pause; first credits for new customers are counted but never tried [LIMITS L-004].
13. **Language.** Helper text is English only; the NTK owners read Vietnamese [LIMITS L-003]. Vietnamese text is a not-built second phase [DIARY].
14. **No outbound communication.** Staff must tell customers. This is a deliberate safety limit and also a gap versus "meet the user in their channel" [COURSE-REQUIREMENTS].
15. **Data completeness.** NTK balances are stated only to 30 Sep 2026 for some customers; several customers lack a confirmed completeness date; exposure may be understated [HOANG-8NOV].
16. **Recordings and demo.** Week 7 audio failed; the edited recording must never be presented as continuous live performance [FEEDBACK-W7].
17. **Staff onboarding, prompts on the Decide page when a pattern appears, and a notification channel to the Owner (webhook)** are not built [DIARY, LIMITS].
18. **Still open from Hoang's 9 Nov list:** assessDecision preview looping (tool switched off on NTK), decisionStatus cannot look up by invoice number, Owner-side wording of hidden policy gates, a hard refresh needed after a fix, and the wording of one clarification ("15 days from 24 November") [DIARY].
19. **Source conflict about data size.** Hoang reports 20 customers, 137 invoices, 113 payments [HOANG-9NOV]; the 24 Oct demo notes list 21 customers, 137 invoices, 113 payments [docs/DEMO-SCRIPT.md]. Use 20 for the current NTK import and check.
20. **Docs out of date.** Several early documents (ADA section 3 "no autonomous decline", the 24 Oct demo script, the INDEX) describe earlier states; the current rule is the opt-in decline of 8 Nov.

---

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

---

## 10. Lessons learned and next steps

**Core message.** The biggest lessons were not about AI cleverness. They were about trust boundaries, testing with a measuring tool, and onboarding. The next steps follow directly from the owners' feedback: make setup minimal, make the effect of settings visible, then measure real savings.

### Lessons learned

1. **Measure the model, do not trust it.** The reference model failed the project's own bar at 5/10 runs. Changing the instructions (fewer steps plus an ambiguity rule) moved it to 20/20 on the same bar. Cheaper than switching models [QUAL].
2. **A small sample lies.** The 9B model scored 9/10, then 2/10 on an identical repeat. Always repeat [BENCH].
3. **Judge by what was stored, not by what the AI said.** A fluent reply that created no case is a failure [BENCH].
4. **Onboarding was the real bottleneck.** After four weeks of safety design, the owners' first policy let the agent decide 0 of 22 invoices, and setup took about an hour (mostly importing data, then settings that were hard to follow). Safety without usability gives no value [DIARY, QS-SPEC].
5. **Code beats the model for exact questions.** The Doctor by model got 5 of 24 wrong; by code, none [LIMITS L-004].
6. **A system-prompt rule is weaker than a per-turn note for this model.** A repeated message was answered from chat memory despite an instruction; a note appended to the message worked [DIARY 4 Nov].
7. **Real users change the product within a day.** Tony's and Hoang's 6 Nov findings were answered by commits the same day (section 5).
8. **Test the exact environment.** Week 7's audio failure; the model silently reloading at the wrong size; one more application on the same model [FEEDBACK-W7, LIMITS, DEMO-SCRIPT].
9. **Keep real and made-up data apart**, and label every number.
10. **Ask who carries liability.** Moving the approval click from Owner to Staff does not remove the bottleneck [charter].

### Next steps (roadmap, in the order the evidence supports)

| Step | Status |
| --- | --- |
| Complete the Owner comparison: the owners' decisions on the scenarios vs the agent's outcomes | Still not compared one by one (6.4) |
| Timed workflow session with the owners (Hoang) to produce a measured time per request | Done, night of 11-12 Nov (6.5) |
| Watch an owner use Get started, the levels and the display levels (built 12 Nov) | Not tested with any owner yet (6.6) |
| A Staff test with a briefing on the demo data, or on the tester's own records | Proposed after the 12 Nov Staff-side look (6.6) |
| A guided tour of the pages for first use | Declined for the PoV: owners use different parts, one tour would be slow for most (6.6) |
| A simpler answer style for the Staff assistant (conclusion and next step only) | Proposed by the second owner, not built (6.6) |
| Statement-style overdue list (who, how much, days overdue by age band) and a payment-habit forecast | Proposed by the second owner, not built (6.6) |
| ABN lookup and change or closure alerts; accounting and payment software links (Xero, Stripe) | Need outside services; outside the PoV (6.6) |
| Confirm the Owner baseline (frequency, days, phone effort) in writing | To do; re-confirm before display [DIARY 4 Nov] |
| Replace test limits with the Owners' approved production limits (Quick setup) | Open |
| Staff onboarding (a walkthrough or short video) | Not built; Tony called it optional [DIARY] |
| Prompts on the Decide page when a pattern appears | Not built (phase 2 of Quick setup) |
| Vietnamese text for the helper pages | Not built |
| Owner notification channel (webhook) | Deferred |
| Per-user identity through the chat to enforce one-request-per-message properly | Deferred |
| Real repayment outcomes feeding back into suggestions | Waits for real decisions to age |
| Letting the team's model approve (not only escalate) with a bar on real cases | A product decision, not built [SHADOW] |
| Test a cloud-model option for businesses without hardware | Never run [BENCH] |
| Outbound customer messages, other request types, forecasting | Explicitly deferred (P2) [ROADMAP] |
| Go-to-market: pricing, packaging, target segment | Team's decision; see section 7 |

Go-to-market evidence available from the records (for the GTM slide): the problem is small-business credit exceptions with an Owner bottleneck; two-horizon value proposition ("Day-one immediate assistance" vs "Long-term growing autonomy") [charter]; the model runs offline on one computer so a low running cost; the Owner asked for minimalism. Market size, competitors and pricing are **not in the records**.

---

## 11. Where each fact goes (report part to pack sections)

| Report part | Feed from | Slide idea |
| --- | --- | --- |
| Team and links | Section 1 (roles); repository and testers named in section 5 | One slide: roles, repo, demo addresses (ask Hanting; do not paste access codes). |
| Problem and evidence | Section 13 (who we spoke to, how the problem narrowed, problem statement and HMW); Section 14 (research); Section 1 (problem, baseline, Week 7 feedback); Section 6.4 (what the baseline is and is not); Section 9 item 6 | "One request a week, 3 to 5 days, phone calls" with the label "reported by the Owner". |
| Discovery (double diamond) | Section 13 (sectors explored, interviews, the two narrowings, Solution Design Document); Section 1 (15 Oct meeting findings); Section 5 (Weeks 1 to 4: Gemma first build, then desk, then ADA); decision table rows 1, 5, 6 | Show the diverge to converge: many ideas (desk chat, Lab, import) then the narrowed decision-authority model. Note: Weeks 1 to 6 not in the records. |
| Design decisions | Section 4 (all), the check ladder, use cases from section 8 | Table of 5 key decisions with "why"; the ladder; the three outcomes. |
| The build (POC and agent) | Section 3 (architecture); Section 5 (timeline); Section 2 | Diagram; weekly timeline; "524 commits, 1,125 tests". |
| Evaluation (proof of value) | Section 6 (all); Section 5 (feedback to change); Section 8 | Three evidence tiers: measured, tester, owner. A "not yet measured" box. |
| Cost | Section 7 | Cost structure and unknowns; no invented prices. |
| Go-to-market | Section 7 (decisions for the team), Section 10 (GTM facts), Section 2 (two-horizon value) | Positioning slide; honest note that pricing/market sizing is the team's work. |
| Data and model | Section 15 | "A method, not a model": 8 denial examples, proxy labels, shadow only. |
| Team practice | Section 16; Section 5 | Charter roles, cadence, who did what, iterations after each test round. |
| Lessons and next steps | Section 10; Section 9; Section 17 | Five lessons and a pending-items roadmap. |
| Appendix | Section 2 glossary; Section 4 full table; Section 6 tables; Section 12 | Full tables as appendix. |

---

## 12. Screenshot wish-list

Another step will take these. All on the fictional demo instance unless marked NTK. Hide access codes, emails and real customer names in every frame. For NTK frames use anonymised customer numbers only and get Hoang's and the Owner's approval first.

| # | Page and state | Caption idea |
| --- | --- | --- |
| 1 | Home as Owner after sign-in, "Where to start" steps visible | "The Owner starts here: three steps." |
| 2 | Quick setup, top of page: three assurances and the three "How to start" choices | "Nucleon never contacts your customer. You can undo any decision. You can pause." |
| 3 | Quick setup with the questions answered and the live preview table (on NTK, anonymised, showing "0 of 22" before) | "See what your rules do to your own invoices before saving." |
| 4 | Quick setup after changing answers, preview showing a higher count | "One answer changed: the agent can now decide 11 of 22." (use real numbers from the screen) |
| 5 | Control panel with limits filled in (Mode Delegated, 1000 / 1500 / 600 / 25%) and "Required / Optional" tags | "The Owner's rulebook, every field marked Required or Optional." |
| 6 | Control panel history of policy versions (v0, v1) | "Every change is a new version; nothing is lost." |
| 7 | Control panel Pause switch on, banner visible | "One button stops all agent decisions." |
| 8 | LibreChat with the Staff agent selected, the Northside prompt typed | "Staff type the request in plain words." |
| 9 | Northside final decision card, whole card with limits listed | "Approved under policy version 1. AUD 800 less AUD 200 deposit = AUD 600." |
| 10 | The early "Would be decided... preview" card next to the final card (optional) | "A preview is not a decision: the card is the truth." |
| 11 | Lakeside amber card "Information needed from Staff" with the button | "Missing facts go to Staff, not the Owner." |
| 12 | Staff evidence form filled in (150.00, bank account, document, fictional ID) | "Staff confirm only what they saw, and say how they know." |
| 13 | Lakeside card or page after submission, now approved, deposit labelled "checked by Staff" | "Re-checked at once: AUD 450 exposure, approved." |
| 14 | Harbourline card "With the Owner for review", failed limit highlighted | "Over the limit: the agent cannot approve it, whatever the AI says." |
| 15 | Decide page (Owner): waiting case with Approve/Decline and reason box; decided-by-agent list with Agree/Disagree/Override | "The Owner sees exceptions, plus what the agent did." |
| 16 | Override confirmation dialog with the stated date and "No customer communication has been sent" | "Reversible: the Owner can undo an agent decision." |
| 17 | Request page timeline for one case (request, evidence, check, decision, feedback, outcome "pending") | "The full story of one decision." |
| 18 | Decision card key-facts timeline axis (dates and extension span, green when approved) | "Dates and days added, drawn from the records." |
| 19 | Dashboard top: tiles (cases, decided by the agent, sent to you, overrides, agreement) | "Every tile says whether it is measured or assumed." |
| 20 | Dashboard "Time saved" tile showing unknown with its note | "We show what we have not measured." |
| 21 | Dashboard loop strip and outcomes bars | "Decision loop and later outcomes." |
| 22 | Doctor page, question 1 answer ("Why do so many requests still come to me?") with counts and suggestion | "Plain answers worked out by code from your own cases." |
| 23 | Doctor suggestion opening Quick setup with the answers filled in | "A suggestion states where it starts, what it gains, what it costs." |
| 24 | Model page: model in force, versions, agreement | "The team's model scores cases for the Owner's eyes only." |
| 25 | Review/Decide row with "Research score, not used in this decision" line | "The model never decides; it is shown beside the case." |
| 26 | Exception band section of the Control panel (off by default) | "Optional: a bounded margin the Owner can allow." |
| 27 | Owner assistant answering "what is waiting?" in LibreChat | "Read-only assistant: it can tell, not decide." |
| 28 | Owner assistant refusing "Approve Harbourline now" | "It refuses and points to the Decide page." |
| 29 | NTK: Hoang's decline-and-reversal sequence on the timeline (anonymised) | "Agent declined a 60-day request; the Owner reversed it." |
| 30 | Model bench table or the A4/A5 result summary rendered as a chart, not a screenshot | "5 of 10 runs became 20 of 20 with better instructions." (draw from section 6.1) |

Existing older screenshots in `docs/screenshots/` (20 files from 18 Oct, older interface) exist; do not use them for the final deck because the interface has changed.

---

## 13. Discovery and problem definition (Weeks 1 to 5)

**Core message.** The team did not start with credit. Five members explored six kinds of small business, ruled most out on evidence, and narrowed twice: first from "any small business" to small manufacturers where staff wait on the owner, then (8 October) to one decision that owners keep to themselves: credit exceptions. The credit focus rests on one business's survey, interview and ledger, and is supported by a second owner's written answers. Say that plainly.

Merged on 13 November from the four members' compendiums [C-HOANG, C-TONY, C-CHRIS, C-PHU]. Businesses and people are described by role here; their names are in the members' own documents. Everything in this section is **reported by a person** unless marked otherwise.

### Course calendar

Seminars were on Wednesdays [C-CHRIS]: Week 1 16 Sep, Week 2 23 Sep, Week 3 30 Sep, Week 4 7 Oct, Week 5 14 Oct, Week 6 21 Oct, Week 7 28 Oct (proof-of-concept presentation), Week 8 4 Nov, Week 9 11 Nov, Week 10 18 Nov (showcase). Report and video due Monday 16 Nov, 5 pm.

### Who we spoke to

| When | Team member | Business (role of the person) | What it showed | How it is used |
| --- | --- | --- | --- | --- |
| Week 3 | Chris | Café inside a play centre, 10 to 15 staff (an employee) | Staff run the day; rostering, payments, stock and technology wait on the owner. The owner already uses AI for ideas and marketing, and would be least willing to hand over financial information. "AI adoption alone does not necessarily eliminate founder or owner bottlenecks." | First evidence of owner dependence; context only |
| Week 3 | Chris | Tutoring centre (a mathematics tutor) | Work is pen and paper; AI would add steps. | Sector ruled out |
| Week 3 | Phu | Family-owned café and takeaway, same processes for about ten years (the owner; interview partly in Vietnamese) | About 90% regular customers, Excel for the books, no wish to grow. A new system means cost, training and disruption. | An inefficient process does not create demand: the adoption barrier. Not credit evidence |
| Week 3 | Tony | Gelato wholesale manufacturer, under 20 staff (a senior employee) | Admin handles routine requests; high-value clients and executive decisions wait for the owner, who also covers production and deliveries. | Owner dependence in a manufacturer |
| 6 to 7 Oct | Hoang | Pet nutrition manufacturer and distributor, "NTK" (the founder: a survey, then an interview) | Dependence rated 2 of 5: staff handle routine work from procedures, but **credit control and payment clearance before stock release is the single largest bottleneck**. Approvals are often verbal. The founder decides exceptions on "my personal evaluation on the transaction, the level of the risk, customer's credibility or working history". A buyer with several shops can fail as a chain. | The business the product was built with; source of the ledger |
| 7 Oct | Tony and Hanting | The gelato manufacturer (the owner; about two hours, three recordings, factory tour) | The owner covers a driver, trains staff and adopts technology in stages after checking the cost. On credit: an admin mistake "could mean that … an account gets set up with a hundred thousand dollar credit limit and they never pay their bill". Tools are often "misaligned … to where my staff's working capacity is". | Second manufacturer; staged adoption; staff capability |
| Late Oct | Tony | The gelato manufacturer (the owner, in writing) | Grants credit on how long the business has traded, a valid ABN or ACN, and three supplier referrals. Hard cases are new venues with no history. Records are a printed folder, email and Xero. Would need correct, real-time information and his clients' acceptance to adopt AI. | Led to the business-identity step (section 5, 11 Nov) |
| After the pivot | Phu (authorship to confirm) | A restaurant overseas (mainly consumers) and a garment manufacturer overseas (business customers) | The restaurant gives occasional credit to long-standing customers on personal relationship and would not use AI without formal criteria. The manufacturer thought an agent supporting credit-extension decisions could save decision time. | Relationship-driven credit is common; business-to-business is the better fit |
| 15 to 31 Oct | Hoang | NTK (the owner, follow-ups) | Declined requests are not recorded; two late payments confirmed as not approved (21 Oct); baseline of about one request a week taking 3 to 5 days (31 Oct, section 1). | Labels for the data work; the baseline |
| 10 to 12 Nov | Hoang; Tony | NTK owners; the gelato owner | Sections 6.3, 6.5 and 6.6. | Proof of value |

Limits to state on a slide: one interview per business in Weeks 3 and 4; the two café interviews and the tutor interview are context for choosing a sector, not evidence about credit; only NTK supplied records.

### How the problem narrowed

1. **Weeks 1 to 2: sectors.** Each member researched a different sector so they could be compared: cafés and hospitality, bubble tea, tutoring, laundries, a pig farm lead, manufacturing [C-TONY Teams posts; C-CHRIS]. Chris wrote the team charter and the Week 2 café report; Tony collected sector statistics.
2. **Week 3: interviews with a shared question set.** Chris wrote ten general questions (background, how work is organised, technology and AI, trust and delegation) that members adapted. Tony called the cut-off: stop interviewing after Thursday and write the problem versions.
3. **6 Oct: the team leans to Stream 1, Founder's Second Brain.** Tutoring is dropped; the café owner's reluctance is kept as a warning about adoption.
4. **7 Oct: manufacturing.** Problem statement V0, V0.1 and V1 for manufacturers (Chris and Tony): employees depend on the founder for exceptions because procedures do not hold the knowledge needed. A delivery-preparation concept was worked up from the gelato interview as one candidate.
5. **8 Oct: credit.** With NTK's survey, interview and about a year of ledger (500+ transactions) in hand, the team agreed unanimously to focus on credit decisions in small, family-owned business-to-business manufacturers. The stated main risk: capturing the owner's relationship-based judgement as data [C-TONY, 8 Oct summary].
6. **15 Oct: a product for many businesses.** Configurable thresholds and escalation instead of one owner's rules; known approvals used only as a first experiment; unfamiliar cases escalate and are not treated as declines [docs/meetings/2026-10-15.md].
7. **26 Oct onward:** the owner-sets-limits design (section 4).

### Problem statement and How Might We (final wording, Week 5)

Small manufacturing businesses struggle to manage their credit policy and sales approval, which overwhelms owners. It affects owners and employees when customers want changes to existing credit terms. Employees lack the information, clear decision boundaries and confidence to handle these requests on their own, so routine and non-routine approvals keep returning to management, which adds to its workload, limits delegation and constrains growth.

**How might we** help owners enable employees in small manufacturing businesses to make informed credit and sales approval decisions independently, while maintaining appropriate oversight of credit risk and commercial outcomes? [C-CHRIS; C-TONY "Finalised Problem statement"]

| Why | Answer |
| --- | --- |
| 1 Why does this overwhelm management? | Employees need the founder to review requests outside existing terms. |
| 2 Why can't employees handle them? | Procedures do not cover unusual cases, and employees are reluctant to carry credit risk without guidance. |
| 3 Why do they struggle? | The decision needs context (payment history, relationship, balances, commercial risk) and they are unsure of their authority. |
| 4 Why is this not in the process? | The owner's decision knowledge is not documented or consistently communicated. |
| 5 Why does it persist? | Without boundaries and access to that knowledge, employees keep escalating. |

Reframes: zoom in (help employees assess credit-term requests and prepare a recommendation); shift category (give employees the information, the owner's knowledge and clear boundaries); **challenge the goal (delegate more decisions while keeping control of risk)**. Nucleon follows the third.

### Solution Design Document v1 (Week 4, written by Chris)

| Part | Content |
| --- | --- |
| Concepts compared | AI-assisted credit decision support (scored 9, selected); digital approval workflow (9, kept as a supporting part); credit rules guide (8, rejected as the main concept). Working name: CreditEase |
| Persona and stories | A sales and accounts employee; four epics, 13 user stories with acceptance criteria and sizes |
| Flow | Request entered, checks run, missing information asked for, recommendation, then accept, challenge or escalate to the owner |
| Features and rules | Ten features ranked Must, Should, Could; five rules including escalation when evidence is too weak |
| Platform | Custom Python application preferred |
| Peer check | Strength: the plan connects the problem to features and keeps the owner involved. Question: "how will we validate the AI's recommendations?" |

What changed between this document and the product: the SDD has the AI recommend and Staff accept. From 26 October the Owner's rules decide and the model only reads and proposes (section 4, decision 1), because a recommendation that Staff click through moves the approval without removing the owner's risk. Chris also drew two BPMN models in Week 6 (onboarding; handling a credit request); the images are in his compendium.

## 14. Research the team did

**Core message.** Three pieces of desk research shaped the design: late payment and credit exceptions are a real cost for small suppliers; existing tools hold or release an order but do not handle the exception; and small businesses distrust AI decisions unless they keep control. A check against the original sources on 13 November found two figures wrong and one only partly confirmed (marked in the table); the National AI Centre, UK data survey, UTS, NAFCO, FCA and ABS manufacturing figures matched their sources. "Up to 14 hours a week" was not checked. Cite the original source, not the team document, and do not present any of these as a measurement of NTK. Wording to keep: the 54% for content generation and data analytics is among adopters and planners; NAFCO's 38% is of approvals (24% of all applications) and is the vendor's own figure.

| Topic | Figure as recorded | Recorded source | From |
| --- | --- | --- | --- |
| Small business share | **Corrected 13 Nov:** 97.4% of actively trading businesses have 0 to 19 employees (2,741,087 of 2,814,778 at 30 June 2026). The team's note said 97.2% | ABS, Counts of Australian Businesses (released 18 Aug 2026); checked | Tony |
| AI use by small business | 43% of Australian SMEs reported some AI adoption, Dec 2025 to Feb 2026 | National AI Centre | Tony, Chris |
| Why non-adopters hold back | 65% cite distrust of AI decisions or a wish to keep human control; 54% not relevant; 19% do not know how | National AI Centre | Chris, Hoang |
| Manufacturing | About 9% of manufacturing businesses use AI | ABS, 2024-25 | Tony |
| Late payment, Australia | Small businesses were paid 6.0 days late on average (June 2026 quarter); checked. **Do not use "41% of invoices more than 14 days late":** that number is from a GoCardless survey of 800 decision-makers (a self-reported average delay), not Xero data and not a share of invoices | Xero Small Business Insights (25 Aug 2026) | Hoang |
| Business-to-business payment | 37% paid on time, 52% overdue, 11% bad debt (Australia, 2025). **Partly checked:** confirmed through a trade press report; Atradius's own page says "more than half" overdue and "more than 10%" bad debts. Read the Atradius PDF before quoting 37% | Atradius Payment Practices Barometer, Australia 2025 | Hoang |
| Owner workload | Up to 14 hours a week on collection and credit administration | Benchmark cited in Hoang's research document | Hoang |
| Data and AI | 73% of businesses uncomfortable with their data training external AI models | UK Business Data Survey 2026 | Tony |
| Staged autonomy | A lender automated approvals only for a limited group after testing recommendations on live applications; 38% of approvals automated in the first month (vendor-reported) | NAFCO Finance case study | Tony |
| Explanations | The kind of explanation changes whether people can spot an error in a credit decision | UK Financial Conduct Authority | Tony |
| How small firms manage AI risk | 133 Australian SMEs: accuracy and data are the main concerns; human review is the common safeguard | UTS Human Technology Institute | Tony |

**The gap in existing tools** [C-HOANG research document, 25 Oct]: accounting and ERP systems apply a credit hold as on or off; receivables tools work after the invoice; none carries the owner's reasons for an exception or controls release at the moment of dispatch. The research positioned the opportunity as a workflow inside order-to-cash, not a credit score.

**Trust research to design** [C-TONY, 24 Oct]. Tony's ten trust factors and where each appears in Nucleon: owner-defined limits (the policy); evidence beside each recommendation (the Decide page); saying when information is missing ("information needed from Staff"); an audit trail and the right to challenge (decisions carry who and why; the Owner can override); proof on the business's own cases before any authority (the research model runs in shadow only); demonstration without sensitive data (the fictional practice business). His five-stage path (fictional cases, past decisions, shadow mode, support staff, limited automation) is the adoption story for the roadmap slide.

## 15. Data work and the exploratory model (Hoang)

**Core message.** NTK's ledger was cleaned and reconciled to its source, and eight classifiers were compared on it. The honest result is a method, not a model: the ledger records payments, not requests or decisions, so the labels are proxies, there are only 8 denial examples from 3 customers, and no accuracy claim can be made. This is why the product decides with the Owner's rules and keeps the model in shadow [C-HOANG; SHADOW].

- **Data.** One year of ledger from one business. 511 rows kept after cleaning; invoice balances rebuilt by first-in-first-out allocation and reconciled to the source with zero differences on the checked rows (**measured**). For the workflow tests, 20 customers, 137 invoices and 113 payments were imported into Nucleon.
- **Labels.** 77 approval proxies, 8 denial proxies, 426 unlabelled. A late payment does not prove an extension was asked for or agreed. The Owner confirmed two receipts as unapproved late payments (21 Oct). Unlabelled rows were not turned into denials.
- **Split.** Trained on 50 rows (44 approvals, 6 denials); tested on the last quarter, 35 rows (33 approvals, 2 denials, both from one customer).

| Model | Accuracy | Balanced accuracy | Denials found (of 2) | False denials |
| --- | --- | --- | --- | --- |
| Always approve (baseline) | 94.3% | 50.0% | 0 | 0 |
| Logistic regression | 94.3% | 97.0% | 2 | 2 |
| SVM, linear | 88.6% | 93.9% | 2 | 4 |
| SVM, RBF | 85.7% | 92.4% | 2 | 5 |
| XGBoost, decision tree, random forest, k-nearest neighbours | 88.6% to 94.3% | 47.0% to 50.0% | 0 | not recorded |

False-denial counts for the two SVMs are worked out from the recorded precision (33.3% and 28.6%); the others are as recorded. The baseline reaches 94.3% accuracy by always saying yes, which is why accuracy alone is not used. The strongest signals in the logistic model were the customer's longest past delay, time since their last payment and their share of late payments: associations in a proxy experiment, not business rules.

**How it entered the product (2 Nov).** Nucleon's research hook stores, for every decided case, the same twelve features as of the request date, and can score a case with the team's model "in shadow": the score is shown to the Owner as "research score, not used in this decision". The training table is Nucleon's own decided cases with the Owner's decision as the label, never the proxy labels. Promotion is off by default and, if ever switched on, can only send a case to the Owner; it cannot approve or decline [SHADOW].

## 16. Team and delivery

**Core message.** Five people, a charter from Week 1, a Wednesday seminar and a Thursday meeting every week, and work split by what each person could reach: owners and data (Hoang), a second business and research (Tony), process and planning (Chris), communication and value (Phu), the build (Hanting).

- **Charter (16 Sep, written by Chris, initialled by all five).** Roles as assigned in Week 1: Chris, Scrum Master; Tony, Product Owner; Hanting, UX designer; Hoang, business analyst; Phu, developer. In practice the roles moved with the work (table below); say so on the team slide. Ways of working: in person Wednesday afternoon and evening, online Thursday, WhatsApp for daily contact and Teams for the record, replies within 24 hours on weekdays, ask early when stuck.
- **Cadence.** Agenda before each meeting and a written summary with action items after it, posted on Teams by Tony (Weeks 2 to 7); minutes for 8, 15 and 29 Oct and 12 Nov. From 15 Oct the build has its own record: decision register, engineering diary and commit history (section 5).
- **Iterations.** Week 7 proof of concept (28 Oct), then test rounds on 6, 8, 9, 11 and 12 Nov, each followed by changes within a day (section 5). A group retrospective was held in Weeks 8 to 9 (notes not supplied).

| Member | Main contributions | Evidence |
| --- | --- | --- |
| Chris | Scrum Master all term (task tracking, scope, distribution); team charter; café report; first interview secured; shared question set; problem statements V0 to V1 with Tony; Solution Design Document v1; BPMN models; Week 7 slides; plan for the final deck | [C-CHRIS] |
| Hoang | Access to the NTK business and its owners; survey and interview; ledger cleaning and reconciliation; exploratory models; research on credit exceptions; tests of 6, 8, 9 and 11 Nov on the real records; the owners' sessions of 10 to 12 Nov and the timing benchmark | [C-HOANG, HOANG-6NOV, HOANG-8NOV, HOANG-9NOV, NTK-SESSION] |
| Tony | Access to the gelato manufacturer (employee, owner interview, written answers, session of 12 Nov); meeting agendas and summaries; trust and adoption research; questionnaire mock-up; narration of the Week 7 and final videos; tester round of 6 Nov | [C-TONY, TONY-6NOV, SESSION-1112PM] |
| Phu | Café owner interview (bilingual); post-pivot credit examples; slide design and presenting at Week 7; analysis of feedback and time savings; final slide design. Unit economics and go-to-market were **not started by 13 Nov** | [C-PHU] |
| Hanting | Co-interviewer on 7 Oct; architecture and the whole build (sections 3 to 5); test infrastructure and model qualification; the practice and real-records instances; manual, this pack and the videos' production | [GIT, DIARY] |

## 17. Open points after the merge (13 November)

| # | Point | Who can settle it |
| --- | --- | --- |
| 1 | **Unit economics and go-to-market are not written.** The slides ask for both (pack section 7 has the cost facts and the decisions to make). | Phu, with the team |
| 2 | NTK's credit rules are recorded three ways: "$25,000 and 15 calendar days" in the interview synthesis; "30 days for established customers, 7 days for newer ones" at the 8 Oct meeting; "VND 500 million" as informal guidance in the November tests. SOURCES DISAGREE; do not merge them into one rule. | Hoang, with the owner |
| 3 | The third compendium does not name its author; it is taken to be Phu's. It also leaves open who interviewed the two overseas businesses. | Phu |
| 4 | Permission to name the businesses and people outside the team. This pack uses roles only. | Hoang, Tony, Phu |
| 5 | Secondary figures checked on 13 Nov (section 14). Still to read in full before quoting: the Atradius PDF, and the journal articles that need a UNSW Library login. | Hanting |
| 6 | Artefacts mentioned but not supplied: the Week 7 slide deck, the retrospective notes, the task board or backlog, the time-savings analysis file. Useful for the team-practice slide. | Chris, Phu |
| 7 | The 8, 15 and 29 Oct minutes were written with an AI summariser and checked by a member; cite them as such. | Noted |

---

*End of pack.*
