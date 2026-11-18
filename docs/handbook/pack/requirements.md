## What the report must contain (from the Week 8 and Week 9 slides)

**Core message.** The slides ask for proof of value, not a feature list: a baseline, an "after", who tested, what they said and what we changed because of it. The pack is strong on design, build and technical evidence. It cannot supply problem and discovery, go-to-market, or the owners' own numbers and quotes: those must come from the team.

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
| Friction before and after, and new friction avoided (another destination, double entry, bad timing, context switching, learning curve) | W8 p20 | The owner session is direct evidence of **learning-curve friction** (about an hour of setup), and Quick setup, the Doctor, the shorter menu and the reworded Control panel are the responses (section 5). |
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

### The gaps that matter most, in order

1. **Baseline and after, with the real owners.** The slides ask what the agent took off the owner's plate in time, steps, errors or money. We have the Owner-reported baseline and measured decision times, but not the owners' decisions on their scenarios compared with the agent's, nor a timed session. Without them the proof of value rests on team testers.
2. **Owner quotes.** None are recorded word for word.
3. **Problem, discovery and go-to-market.** Not in this pack.
4. **Individual portfolio.** Seven good entries out of nine are needed for Competent; this week's is due Friday 13 Nov, close of business, and the last one in Week 10 [W9 p3].

