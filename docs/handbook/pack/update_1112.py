"""Adds the timed session with the owners (12 Nov 2026) to INFO-PACK.md and open_issues.md. Run once."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, 'INFO-PACK.md')
s = open(p, encoding='utf-8').read()


def sub(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


SESSION = """### 6.5 The timed session with the owners (night of 11-12 Nov)

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

**What this adds to the proof of value, and what it still does not.** It is the first timing with the real owners in the room and their own baseline for the same step. It is still one facilitated session with fictional requests; it does not show an owner working alone, a week of real traffic, or any repayment outcome. The strongest honest sentence about onboarding: "The owners said the product works and the Staff side is easy, and that the Owner side is too much to take in at first. Setup took about an hour on 10 November, and on 12 November the Owner still needed an interpreter."

"""

sub("---\n\n## 7. Cost", SESSION + "---\n\n## 7. Cost")

sub("| Owner's 5 (or 6) scenario decisions vs the agent's outcomes. | **Pending on 11 Nov** (to be compared by the product lead). Not known / to confirm with Hanting and Hoang. |",
    "| After negotiation, the internal decision takes about 42 s (agent) or under 2 min (Owner) instead of about one working day. | **Measured** in one facilitated session with the owners (6.5) against a baseline **reported by the Owner**. Say both halves. |\n"
    "| Owner's 5 (or 6) scenario decisions vs the agent's outcomes. | **Still not compared one by one.** The session of 12 Nov tested fresh requests instead (6.5). Not known / to confirm with Hoang: whether the earlier five answers were written down. |")
sub("| Timed workflow session with the owners. | **Pending**: Hoang planned a short second session on the night of 11 Nov. [DIARY] |",
    "| Timed workflow session with the owners. | **Done on the night of 11-12 Nov**: see 6.5. [NTK-SESSION] |")

sub("1. **Baseline and after, with the real owners.** The slides ask what the agent took off the owner's plate in time, steps, errors or money. We have the Owner-reported baseline and measured decision times, but not the owners' decisions on their scenarios compared with the agent's, nor a timed session. Without them the proof of value rests on team testers.",
    "1. **Baseline and after, with the real owners.** Partly closed on 12 Nov: one timed session with the owners gives 42 s (agent) and under 116 s (Owner) against \"about one working day\" reported by the Owner (section 6.5). Still missing: an owner working without an interpreter, more than one request of each kind, and the owners' earlier scenario answers compared with the agent's one by one.")
sub("2. **Owner quotes.** None are recorded word for word.",
    "2. **Owner quotes.** None are recorded word for word. Section 6.5 has what the owners said as reported by Hoang; present it as reported feedback, not as quotations.")

ISSUES = """
**After the session with the owners (12 November).** Fixed and re-tested the same day: the requested date recorded wrongly (31 December became 1 December), the chat card headed "STATUS UNAVAILABLE" for an agent decline, and "15-day" not being read as a number of days (details in section 6.5). Still open from that session:

| # | Where | What happens | What to do meanwhile |
| --- | --- | --- | --- |
| 14 | Customer names | The real-data records hold "Customer 0010", not the business's real name, so the assistant cannot find a customer by its real name and asks. | Use the customer number, or import the real names. |
| 15 | Business date | The system's date can be one day behind the tester's own date just after midnight in Sydney. "15 days" then lands one day earlier than the tester expects, and the assistant asks which date is meant. | Give the date itself, not a number of days, when the exact day matters. |
| 16 | Owner's first use | The owners found the Owner side overwhelming and needed an interpreter; many elements were not clear without explanation. Quick setup and the reworded Control panel (11 Nov) were not tested with the owners alone. | Not solved. It is the main next step. |
| 17 | Test records | The three benchmark cases of the session (Customers 0010, 0011, 0014) are still in the real-data instance. | Kept as evidence until the report is written; then removed or the data restored from a snapshot. |
"""
marker = "| 13 | Demo data |"
i = s.index(marker)
j = s.index("\n", i) + 1
assert s.count(marker) == 1
s = s[:j] + ISSUES + s[j:]
open(p, 'w', encoding='utf-8').write(s)

q = os.path.join(HERE, 'open_issues.md')
t = open(q, encoding='utf-8').read()
assert 'After the session with the owners' not in t
open(q, 'w', encoding='utf-8').write(t.rstrip('\n') + '\n' + ISSUES)
print('pack updated')
