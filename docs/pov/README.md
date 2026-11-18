# PoV sessions: preparation pack

Preparation for slice S5 (Weeks 8-10 of the plan in [POV-IMPLEMENTATION-PLAN-20261030.md](../product/POV-IMPLEMENTATION-PLAN-20261030.md)). The protocol itself is the [validation plan](../research/POV-VALIDATION-PLAN-20261030.md); these files make it runnable. All data in every session is **fictional**. Nothing here contains codes, passwords or real customer data.

## Files

| File | For | Use |
| --- | --- | --- |
| [TESTER-GUIDE.md](TESTER-GUIDE.md) | Owner and Staff testers (not technical) | Sent the day before. Addresses, sign-in, the three practice journeys, the Owner steps. |
| [CONSENT.md](CONSENT.md) | Testers | Sent with the guide; signed (name and date) before a recorded session. |
| [FACILITATOR-RUNBOOK.md](FACILITATOR-RUNBOOK.md) | Team member running a session | The owner test playbook (rewritten 12 Nov 2026): Part 1 the owner alone, Part 2 guided scenarios, what to write down. `python3 docs/pov/build_playbook.py` builds the page published as "Owner Test Playbook". |
| [SESSION-LOG-TEMPLATE.md](SESSION-LOG-TEMPLATE.md) | Team member running a session | One copy per session. Minimum evidence capture and net-time measurement. |
| [FEEDBACK-REGISTER.md](FEEDBACK-REGISTER.md) | Whole team | Running table of observations and the product change each one motivates. |

## Where completed material goes

- Filled session logs, recordings and exports stay on the team's machine (see the facilitator runbook). Do not commit recordings, names or quotes that identify a person.
- De-identified quotes and observations go into the feedback register, which is committed.
- The final report follows the validation plan's six-part reporting format.

## Calendar (Weeks 8-10)

Dates set by the product lead on 31 Oct 2026 (Week 10 submission: Monday 16 Nov 2026).

| Week | Planned | Date |
| --- | --- | --- |
| 8 | Prepare: send guide and consent, add tester emails, create accounts, dry run; a version the Owner (the boss) can use is handed over | Mon 2 - Fri 6 Nov 2026; hand-over by Wed 4 Nov |
| 9 | Owner and Staff sessions (about 45-60 min each); fix blockers for the three journeys only | Mon 9 - Fri 13 Nov 2026 |
| 10 | Remaining sessions, impact report from real session data, final demo rehearsal on the actual audio path | Mon 16 Nov 2026 (submission) |

## Owner baseline (reported 31 Oct 2026)

Relayed by a team member who asked the business owner on 31 Oct 2026 (not measured by us; label it "reported by the Owner" wherever it is used):

- **Volume:** about **one request for additional credit per week**.
- **Turnaround:** typically **about 5 days** from request to approval, **never under 3 days**.
- **What "processing" means:** the Owner personally phones the customer to negotiate; there is no delegated path today.

How this feeds the plan: the "Time saved" row of the impact report (plan section 5) uses this as its manual baseline, labelled as an interview figure. At one request a week, Week 9 and 10 sessions cannot produce enough live cases for a measured comparison, so the impact report compares the **fictional session scenarios** (time to decision, Owner intervention time, escalation rate) against this reported baseline and says so. The PoV claim to test is therefore "a delegated request is decided in minutes instead of days, and the Owner is involved only for the cases the policy sends to review", not a volume claim.

## Related

[DEPLOYMENT.md](../DEPLOYMENT.md) (public access) · [KNOWN-LIMITATIONS.md](../KNOWN-LIMITATIONS.md) (model behaviour) · [demo runbook](../../deploy/m3-local/demo-runbook.html) (the same journeys, team-facing)
