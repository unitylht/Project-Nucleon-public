# Session log (one copy per session)

Copy this file to the team's private folder, **not** into the repository, and fill it in. Implements "Minimum evidence capture" and "Net-time measurement" in the [validation plan](../research/POV-VALIDATION-PLAN-20261030.md). Record only what happened; leave a field blank or write "not observed" rather than guessing. Use "Owner" / "Staff", never names.

## 1. Session

| Field | Entry |
| --- | --- |
| Session ID (e.g. S-01) | |
| Date / facilitator / note-taker | |
| Participant role (Owner / Staff) | |
| Consent signed (date) / recording allowed (Y/N) | |
| Remote or in person; browser | |

## 2. Environment and version

| Field | Entry |
| --- | --- |
| Git commit (Nucleon) | |
| Policy mode and version at start / at end | |
| Model and context (expect Qwen3.5-35B-A3B, 32768) | |
| `bin/pov-check` result (time) / `bin/demo-reset` done (time) | |
| Other notes (outage, slow model, retries) | |

## 3. Participant's current manual process (before the tasks)

Ask for a typical credit request, not a specific customer. No customer or bank details.

- How do you handle a request like this today? (steps, tools)
- How long does it take you, start to finish, for a typical one? For the unusual ones?
- Who is involved, and how many times does the Owner get interrupted? How often per week?
- What goes wrong today (late payments, forgotten follow-ups, rework)?
- Manual baseline for this role: ____ min per request; ____ requests per week; Owner share ____ min.

## 4. Tasks and timestamps

Use clock time (hh:mm:ss). Net time = end minus start minus interruptions. Time to backend card and time to the model's final text are separate (validation plan).

| # | Task / scenario | Prompt used | Start | Card shown | Model text done | End | Interruptions (min, why) | Outcome (success / partial / fail) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Owner sets fictional policy v1 | n/a | | n/a | n/a | | | |
| 1 | Northside trial credit | exact | | | | | | |
| 2 | Harbourline escalation | exact | | | | | | |
| 3 | Lakeside evidence, Staff form | exact | | | | | | |
| B | Owner review (agree / disagree / override) | n/a | | n/a | n/a | | | |
| C | Case timeline: can they say what happened and what is pending? | n/a | | n/a | n/a | | | |
| D | Dashboard: can they read it? | n/a | | n/a | n/a | | | |

Per task also note: number of prompts and clicks; retries of the message; any help the facilitator gave (what, when).

## 5. Observed decisions and control events

| Item | Count | Detail (case, policy version, reason) |
| --- | --- | --- |
| Autonomous decisions by the agent | | eligible cases: |
| Escalations to the Owner | | total requests: |
| Evidence requests; Staff confirmations | | |
| Owner overrides / disagrees / agrees | | decisions shown to Owner: |
| Pause used / policy changed | | |
| Wrong or ambiguous claims by the model text (card was right?) | | |
| Loops, errors, retries, tool-step limit | | |
| Source of evidence (recorded / Staff-checked) | | |

## 6. Owner / Staff understanding (questions 2 and 4)

- Could they say what the AI may act on, what was decided, what is pending? (Y / partly / N, with words used)
- Could Staff act on the result without asking the Owner? (Y / N)
- Did they know how to pause or override? (Y / N)
- Did they confuse Staff-checked with bank-verified, or pending with paid? (Y / N)

## 7. Feedback

- Direct quotes, with clock time (what they trusted, found confusing, not useful, or unacceptable, and why):
  1.
  2.
  3.
- Confusions and friction (page, step, what happened):
- What they trusted:
- What they would not accept, or would require before delegating (limits, checks):
- Would the Owner delegate any defined class? Which? (their words)

## 8. Net-time comparison

All in minutes; state the sample size and assumptions.

| Item | Manual (baseline) | Assisted |
| --- | --- | --- |
| Owner time per comparable request | | |
| Staff time per comparable request | | |
| Setup / onboarding (allocate across expected cases) | n/a | |
| Review, corrections, maintenance (allocate) | n/a | |
| **Net owner time saved** = manual owner time - (assisted owner time + allocated onboarding/review/maintenance) | | |

Assumptions and caveats (fictional data, N = 1 session, prompts pre-scripted):

## 9. Files to save (private folder `S-xx/`)

- [ ] Screen and voice recording (if allowed)
- [ ] Screenshots: each decision card, Review page, case timeline, Dashboard, any error
- [ ] Backend evidence per case (final_acceptance-style: decision status, policy version, evidence, actor)
- [ ] `GET /api/delegation/impact` snapshot taken after the session
- [ ] Case timelines for each case run
- [ ] Signed consent (or the agreement email)
- [ ] This log, completed within 24 h; quotes copied to the [feedback register](FEEDBACK-REGISTER.md) (de-identified)
