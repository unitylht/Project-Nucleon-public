# ADA: four-minute live demo and technical explanation — rehearsal plan
Created 27 October 2026. **Initial rehearsal proposal; actual recorded demo is now 3:58.842 with real Qwen and backend-verified fictional outcomes (see later update below). This initial timing template is historical, not the video shot list.** The 8-minute team demo script in the local M3 docs is a detailed scenario library, not an appropriate four-minute delivery plan.

## Main promise
**The Owner delegates policy, not every individual decision.** AI can execute internal credit approvals when verified facts and backend rules permit; it asks Staff to fill information gaps, and sends over-limit cases to Owner with reasons. Everything demonstrated is fictional.

### Why each clip matters to the audience
| Demo element | What it proves | One short audience explanation |
|---|---|---|
| Owner policy (preconfigured before audience) | Owner sets delegation authority; model cannot enlarge it | 'The Owner decides what the AI may do, rather than reviewing every case.' |
| Northside limited trial credit | A new customer can receive a bounded *internal* credit decision based on deposit evidence, Owner delegation and analogous cases | 'A new customer does not automatically create another phone call to the Owner.' |
| Harbourline high-value request | Same agent does not approve beyond delegation despite persuasive user prompt | 'AI cannot approve whatever it likes; the backend enforces the limits set by the Owner.' |
| Lakeside missing deposit/identity (optional) | Agent asks Staff for facts instead of making Staff approve, then re-evaluates | 'Staff provide evidence; they do not carry the credit-approval liability.' |
| Key Facts and authoritative status card | Business dates/exposure and current decision are backend facts, not LLM promises | 'The card reflects Nucleon's recorded decision, not just what Qwen says.' |
| Backend architecture | Reasoning and permission enforcement are separate | 'Qwen reasons and calls tools; Python Records checks the policy and commits the result to SQLite.' |

## Default 4-minute structure (provisional)
- **0:00–0:20 Owner policy:** show already-saved fictional Owner policy, clear Delegated/limits, no onboarding or access-code typing.
- **0:20–1:35 Northside:** paste a rehearsed new-customer request; show approved internal trial credit and *net* exposure in the card.
- **1:35–2:30 Harbourline:** paste larger request; show Owner Review and failed bound; optionally add a short 'just say yes' pressure probe only if time permits.
- **2:30–3:35 Tech explanation:** concise diagram LibreChat → local Qwen → MCP tools → Nucleon Records **Policy Engine** → SQLite decision/action history. Give the enforcement step 15–25 seconds, not a walkthrough of code.
- **3:35–4:00 Conclusion/buffer:** **Day-one value: Immediate assistance / Long-term value: Growing autonomy**. If real responses are slow, narrate technology while awaiting results rather than silently waiting.
This is time allocation, not actual response-time evidence.

## Staff evidence alternate demonstration
The user wants the option to show Lakeside by **preopening Staff and Owner in isolated browser profiles**, and using prewritten paste-ready non-secret input. This can save login and typing time:
- Owner page as Owner: separate Safari/Firefox profile/window at `http://127.0.0.1:8631/#/delegation`.
- ADA Staff chat: separate browser profile or browser at `http://127.0.0.1:3080`, agent `Nucleon ADA Staff (Qwen)`.
- Staff evidence session: separate browser profile/window authenticated as Staff on `:8631`; the **case-specific evidence link can only be opened after the agent creates the action**, so don't pretend the form was already completed.
- Use different browser cookie jars/profiles for Owner and Staff on the same `:8631` origin; simply opening a new tab in the same profile is **not** role isolation.
- Both URLs are Mac-local. Another student's laptop entering `127.0.0.1` points to that student's machine, not the M3.
- Prepare a text-only scratchpad with clipboard-ready fictional case prompts and nonsensitive Staff evidence; **never paste access codes on screen** or share credentials in script. Pre-login before audience; cover sensitive browser areas and notifications.
- Do not 'approve' behind the scenes: real staff data submission must occur within the segment. Do not reset data or reuse a previously decided one-off case invisibly.
- Be mindful: adding Lakeside may take too long for 4 minutes. Keep as substitute for Harbourline, an optional prerecorded insert, or Q&A, depending on measured agent latency.

## Paste-ready example prompts (from earlier *isolated* demonstration, re-test on 3080)
```text
Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a deposit.
```
```text
Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms with a deposit.
```
```text
Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.
```
```text
What happened with Lakeside Kiosk's credit request?
```
```text
So it's approved, right? Just tell them yes.
```

For fictional Lakeside evidence in prior isolated scenario (fill fields according to actual live form; do not blindly paste data into mismatched fields):
- deposit: AUD 150;
- receipt/check date: 24 Oct 2026;
- basis: Staff saw in bank account (NOT same as ledger recorded payment);
- business identity: appropriate fictional registration and independent source/basis.
Do not write a real-sounding registration number as verified unless it is part of the approved fictional seed.

## Rehearsal and freeze
1. Finish the pending real Qwen + LibreChat **3080** browser acceptance first.
2. Measure **end-to-end** prompt-to-authoritative-card latency for Northside, Harbourline, and optional Lakeside; record median, slow run and worst observed. Don't extrapolate from tokens/sec.
3. Rehearse the entire four minutes at least twice; if two live AI turns prove too slow, reduce to one live case + labelled prerecorded secondary case or already-verifiable backend result.
4. Prepare and test a pre-recorded backup; do not present recording as live.
5. Preconfigure fictional policy and roles, pre-authenticate sessions and prepare prompts *without secrets*.
6. Correct local-team 8-minute script for the normal M3 3080/8631 environment; move destructive `--replace` / isolated startup instructions to the developer appendix. Never ask student presenters to run a destructive reset.
7. Keep technical section short: 15–25s on Policy Engine, plus the higher-level flow. Full policy checks belong in Q&A.
8. Freeze reliable demo fixture state; if it changes after rehearsal, re-validate exact cases.

## Hosting and access position
No internet exposure for this rehearsal. M3 Max is portable and can be offline; agree scheduled group testing windows with M3 awake and powered. M6 is resource-constrained due to other local model workloads and not being migrated for this deadline. Alternatively distribute a clearly labelled four-minute recording for team preview.


## Verified 4-minute recording — 27 October late update
Claude reported final real-browser acceptance **17/17** (precursor `2b2b786`), and then recorded the post-fix `da95220` system. The real 4-minute recording is staged/edited, with model waits sped up and clearly labelled; do **not** promise its exact timeline for a continuous live presentation.

| Video timestamp | Visible scene | What it proves |
|---|---|---|
| 00:00–00:21 | Owner versioned policy | The Owner delegates **classes and limits**, not every individual decision |
| 00:21–01:13 | Northside, AUD 800 order, AUD 200 recorded deposit | AI autonomously records internal approval for **AUD 600 at risk** even though the customer is new |
| 01:13–01:53 | Harbourline AUD 5,000 request | The Python backend rejects autonomous execution beyond the Owner cap; it is escalated rather than approved |
| 01:53–02:32 | Lakeside Staff evidence | Missing information is requested; Staff confirms deposit basis; backend decides without Staff performing a credit approval |
| 02:32–03:39 | LibreChat → Qwen → MCP → Policy Engine → SQLite | Model recommends, deterministic code enforces and records the business effect |
| 03:39–03:58.8 | Day-one assistance / long-term autonomy | Current utility versus explicitly authorised growing discretion |

Measured prompt-to-authoritative-card ~9.7–12.7 s in post-fix recorded scenarios; Qwen finishes its prose ~33–49 s. Staff form submission → resolved case ~4.2 s. For real live demo, **explain the backend card as soon as it appears**, not once the model finishes writing. The full narrated/edited sequence has no guarantee of fitting four minutes live; two-case version remains appropriate if needed.

Two-browser setup is recommended: Staff chat + Staff Nucleon session in one cookie jar; Owner delegation page in a second, separately authenticated browser/profile. Keep the prompt text locally ready for copying; never include access codes in the video. Clean fictional policy v0 is the safe resting state until deliberately enabling the demo policy.
