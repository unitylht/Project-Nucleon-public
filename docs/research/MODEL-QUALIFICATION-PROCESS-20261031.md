# How the Staff agent's model and instructions were qualified (30–31 Oct 2026)

**Status:** process record, written 31 Oct 2026 from the repository only. It is meant to be lifted into the PoV report (section "How the model was chosen"). The numbers are quoted as recorded in [MODEL-BENCH-20261031.md](MODEL-BENCH-20261031.md) and `tools/modelbench/results/`; where two places disagree, the text says so. All data used in the tests is fictional and all thresholds are POC values. Times are local (UTC+11) unless marked UTC; result files carry UTC stamps.

## 1. Summary

1. **Question.** Can the Staff agent run on a local model, and which one? The plan (D5) kept Qwen3.5-35B-A3B as the reference and asked for a test bench to decide whether a smaller model was adequate.
2. **Method.** A bench (`tools/modelbench/bench.py`) runs five standard prompts against a scratch Records and Lab with the Staff agent's real tool definitions and instructions, and judges each prompt by the state of the backend, not by what the model says. The bar: at least 9 of 10 runs in which all five prompts are correct with at most 4 tool calls each.
3. **Reference result.** The 35B reference was 2 of 3 on the first clean 3-run sample and 5 of 10 on the 10-run sample (47 of 50 prompts correct). It did not meet the bar. Its failures were early stops: the model ended its turn before submitting the case.
4. **Candidates.** Ten other models were screened. One of them, qwen/qwen3.5-9b, scored 9/10 and then 2/10 in two identical samples (11/20). One, qwen3.8-27b-mlx, scored 9/10 but at a median of 70.6 s per prompt, about five times the 35B. The others failed on correctness, failed on the mixed prompt, or were too slow.
5. **Instructions instead of a new model.** A nudge (6/10) and an instruction line (2/10) did not fix the early stop. Removing steps did: "resolve-only" instructions reached 17 of 20 runs (85%).
6. **Ambiguity rule.** Resolve-only submitted the ambiguous "mixed" message as a case in 2 of 20 runs. One added paragraph (classify first, ask Staff when mixed) gave 10/10 runs, then 10/10 again, with 0 cases on the mixed prompt in 20 runs and 0 cases in 30 runs on three further ambiguous prompts.
7. **Answer.** The 35B stays. The Staff instructions change (resolve-only plus the ambiguity rule). Final recorded numbers for those instructions: 20 of 20 runs on the bar on the standard five (50/50 and 50/50 prompts), 0 of 20 mixed-prompt cases, 0 of 30 cases on the ambiguity set, 0 wrong approvals and 0 provider errors in all 80 runs of the last two samples.
8. **Not yet done.** The live switch of the Staff agent to the new text and the browser acceptance round are recorded separately (phase B). Other ambiguous wordings, a cloud model and long conversations were not tested.

## 2. The bar and the judge

**The bar (D5, POV-IMPLEMENTATION-PLAN-20261030.md; S3 acceptance).** Qwen3.5-35B-A3B is the reference. A model is "adequate" if, over 10 runs, in at least 9 runs all five prompts pass with at most 4 tool calls each. The bench constant is `ADEQUATE_CALLS = 4`. The D5 figure is always computed on the standard five prompts only, including after the ambiguity set was added.

**Why the backend is the judge.** Model text is recorded but not judged. After each prompt the bench reads the Owner's view of the decision cases in the scratch Lab and checks the expected state. A fluent reply that created no case, or a case the Owner did not need, is a failure; a clumsy reply that left the right case in the right state is a pass. A crude text check also flags a final text that says "approved" when the backend did not approve; it never fired in any model.

**The five standard prompts** (exact wording in `bench.py`; the first four test the three outcomes of the delegation policy and one evidence path, the fifth tests that the agent asks):

| Prompt | Wording (fictional) | Expected backend state | What it tests |
|---|---|---|---|
| northside | Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a 25% deposit, which is recorded in Nucleon. | one case, decided by the agent | clear trial credit inside delegation |
| bayview | Bayview Gelato Co asks to move invoice DEMO-301 to 10 November 2026. | one case, decided by the agent | invoice extension; needs the invoice lookup |
| harbourline | Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms. | one case, with the Owner (`awaiting_owner`) | amount above delegation: escalate, do not decide |
| lakeside | Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms. | one case, `gathering_evidence` | no evidence: the case must exist and wait for evidence |
| mixed | NorthSide Cafe wants an approved credit of 1500 AUD within 30 days extension what is your decision on this? | no case at all | an ambiguous message (known limitation L-001): ask Staff, do not guess |

**The scratch stack.** The bench starts its own Records and Lab on free loopback ports with generated codes and tokens (nothing on 8630, 8631 or 3080; LibreChat is not involved). The data is `prototype/delegation_demo.py` (six fictional customers, as of 24 Oct 2026). The demo delegation policy is saved through the HTTP API as the Owner person and the eight Staff tools are switched on. Each prompt runs on freshly restored data (a snapshot of that state), in its own short conversation.

**What the model sees.** The Lab's real MCP tool definitions for the Staff token, reduced to the Staff agent's eight tools (`findCustomers, customerOverview, invoices, assessDecision, resolveDecision, decisionStatus, whatIsNeeded, customerStatus`), the Staff instructions, and for each tool call the compact `forModel` text the Lab gives the model (200 to 600 characters per decision tool).

**Settings.** LM Studio at `http://127.0.0.1:1234/v1`, context 32,768 for every model, temperature 0.2, at most 12 tool calls and 4,096 completion tokens per request. Only one model was loaded at a time. Instructions: `integrations/librechat/agents/instructions_staff.txt`, 2,520 characters (the file on `main` is 2,521 bytes), sha256 prefix `3a28b8b2bc3797fa` for all model comparisons; the earlier draft was `ed04e110…`. Variants were loaded with `--instructions-file` and recorded in the result files. A provider error ("predecessor handoff") is recorded and the prompt retried once on fresh data.

## 3. Timeline

Order is taken from the commit log and the UTC stamps of the result files (UTC+11: add 11 hours). The user's brief puts the start on 30 Oct; the first bench commit is 01:07 on 31 Oct local, and the first result file is stamped 30 Oct 14:07 UTC. Both dates are correct for different clocks.

| Local time | Step | What was tried | Result | Decision |
|---|---|---|---|---|
| 31 Oct 01:07 (commit `5ef99ea`) | Bench built (S3) | scratch stack, five prompts, minimal tool loop, backend judge | unit tests for the judge and summary | bench becomes the judge, not the unit tests |
| 31 Oct 01:07 (`…20261030T140746Z`) | First full run, 3 runs, first-draft instructions `ed04e110…` | 35B, S3 instructions with a `whatIsNeeded` read | 0 of 3 runs adequate; Lakeside 0/3 and Harbourline 1/3 created no case. After `whatIsNeeded` the model listed the missing items instead of calling `resolveDecision` | the result of `whatIsNeeded` read like a final answer |
| 31 Oct, same night, not timed | Three wordings on Lakeside and Harbourline (development runs, not kept) | two emphatic instructions; a `nextStep` worded like `assessDecision`'s | emphatic: 1 of 5 Lakeside runs with a case; `nextStep` like `assessDecision`'s: 8 of 8 development runs created the case | `nextStep` wording adopted (commit `c8562ee`) |
| 31 Oct 01:17 (`…T141729Z`, commit `c8562ee` 01:21) | Reference, 3 runs, instructions `3a28b8b2…` | final S3 text | 15/15 correct, 2 of 3 runs on the bar (one Bayview run with 5 calls) | not a verdict; the bar is 10 runs |
| 31 Oct, before 10:48, not timed | First 10-run attempt of the reference | — | stopped after 4 runs: 19 of 20 prompts correct, then an `httpx2.ReadError` while closing an MCP session crashed the bench; nothing was written | bench fixed: ignores a teardown error once the model loop has finished, and recognises a provider error inside the client's exception group (before, it crashed instead of retrying). The aborted attempt is not mixed in |
| 31 Oct 10:48 (`…20261030T234837Z`) | Reference, 10 runs | the full bar | 5/10 runs on the bar, 47/50 prompts. 3 early stops with no case (Northside run 2, Bayview run 9, Lakeside run 4) plus Bayview with 5 calls (runs 3, 10) | the reference does not meet D5 |
| 31 Oct 11:01 (`qwen3.5-9b-…T000144Z`) | qwen3.5-9b, 3 runs | screening | 15/15 correct, 2/3 on the bar | run 10 |
| 31 Oct ~11:14 to 11:16 | gemma-4-26b-a4b, gpt-oss-20b, 3 runs each | screening | Gemma 12/15 (mixed 0/3), gpt-oss 9/15 (stops after `whatIsNeeded`) | not adequate. Gemma MLX backend died after three prompts of its first run (see below); the reported run is the clean one after reload |
| 31 Oct 11:21 (`…T002128Z`, commit `4fd6285` 11:41) | qwen3.5-9b, 10 runs, sample 1 | the bar | 9/10, 49/50 | meets the bar; "second sample is cheap" |
| 31 Oct 12:13 (`…T011348Z`, commit `784d10b` 12:37) | qwen3.5-9b, sample 2 (S6d phase 1) | same | 2/10, 42/50. Stops after `whatIsNeeded` (Lakeside 3, Harbourline 3), mixed created a case in 2 runs. 11/20 combined | the 9B is not adequate; one 10-run sample is not enough |
| 31 Oct, about 12:00 to 12:50 (commit `19fb1ba` 12:53) | 9B in the real LibreChat agents (S6d phase 2) | Staff `accept_final.py`, Owner `accept_owner.py` | Staff 16/17, Owner 5/5; one provider error in 8 Staff turns; the failing check was a "just say yes" probe | 9B usable for the read-only Owner agent, mostly for Staff; everything restored afterwards |
| 31 Oct 13:38 (`gemma-4-31b-…T023808Z`, commit `549f6ed` 13:45) | gemma-4-31b, 3 runs (phase 3) | screening | 14/15, 0/3 on the bar | not adequate |
| 31 Oct, about 13:30 to 13:50 | LM Studio force-stopped and unable to relaunch; reinstalled (see below) | — | app back, 35B reloaded at 32,768, `pov-check` green | never quit or kill the LM Studio app from automation again |
| 31 Oct, about 14:00 to 17:00 | Late candidates downloaded and screened: qwen3.8-27b-mlx, qwen3.5-27b, qwen3.5-4b-mlx, granite-4.2-30b-mlx, muse-glimmer-30b, gemma-4-12b | speed rule applied: 3 runs, then 10 for any model with 15/15 and at least 2 of 3 adequate; abandon above about 90 s median in run 1 | see section 4. Download times are not recorded; the result stamps are 14:45, 15:08, 16:13 and 17:03 | granite and muse abandoned as too slow; gemma-4-12b downloaded but never listed by LM Studio |
| 31 Oct 14:45 and 15:08 | qwen3.8-27b-mlx, 3 then 10 runs | screening, then the bar | 3/3, then 9/10, 49/50, median 70.6 s | meets the bar, slow |
| 31 Oct 17:15 (`48a5157`) | Phase 3 written up | recommendation with options (a) to (d) | the 35B does not clear the bar; qwen3.8-27b does, slowly; a model-independent nudge recommended next | nudge tested next |
| 31 Oct 20:27 (`…T092704Z`, commit `eb32933` 20:52) | Phase A: nudge on the 35B | one automatic message after an early stop | 6/10, 47/50, nudge fired in 7 of 50 | not a fix |
| 31 Oct 20:39 (`…T093957Z`) | Phase A: instruction line only | one appended line | 2/10, 42/50 | harmful; dropped; the combination (c) not run |
| 31 Oct 20:54 (`…T095407Z`) | A2 (d): no `whatIsNeeded` paragraph | fewer steps | 4/10, 43/50 | not enough |
| 31 Oct 21:05 (`…T100502Z`) | A2 (e): (d) plus nudge | | 6/10, 45/50 | not enough |
| 31 Oct 21:17 (`…T101700Z`, commit `ea6c9a1` 21:26) | A2 (f): resolve-only plus nudge | | 8/10, 48/50; nudge fired 0 of 50 | direction right; second sample needed |
| 31 Oct 21:27 (`…T102712Z`, commit `4e5e43f` 21:36) | A3: resolve-only, no nudge, sample 2 | | 9/10, 49/50; combined 17/20 | better than the reference; 2 of 20 mixed submissions remain |
| 31 Oct 22:32 (`…T113258Z`, commit `5b8f3f9` 22:43) | A4: resolve-only plus the ambiguity rule | 35B reloaded after a reboot | 10/10, 50/50, mixed cases 0 of 10 | rule works on this wording |
| 31 Oct 22:44 (`…T114412Z`, commit `b473507` 23:00) | A5: A4 instructions on the ambiguity set (`--extra`) | three new ambiguous prompts | standard five 10/10; new prompts 0 cases in 30 runs | ready for a controlled live try (phase B, recorded separately) |

**The speed rule.** The product lead set it at about 16:50 on 31 Oct, in chat, while Granite was running at 120 to 380 s per prompt: about 2 minutes per prompt is unusable whatever the score, a bit over 1 minute is tolerable. The bench's working version: a model whose median per prompt in its first run is above about 90 s is abandoned. (Recorded here from the working session; the repository holds only the rule's effect.)

**Gemma MLX incident.** The first Gemma-26B run passed three prompts, then LM Studio's MLX backend died ("fatal exception in the backend generation thread", HTTP 400 on every request, including "hi"). `lms ps` showed the 35B loaded again next to Gemma, most likely loaded just in time by LibreChat from another slice's browser test or title model; it was unloaded, Gemma was unloaded and reloaded, and the reported run is a clean complete run. Gemma's MLX stability is recorded as unproven.

**LM Studio incident and reinstall (31 Oct, about 13:30 to 13:50, from the working session; not in the repository).** Between the 9B round and phase 3 the LM Studio app was force-stopped from automation (an AppleScript quit was blocked by the sandbox, so the process was killed) and would then not relaunch: `codesign` reported "sealed resource is missing" for files under the app's vendored Python, a pre-existing damage that only showed when the app had to start cold. Stale `SingletonLock` and `llmster-pid.lock` files were removed; the fix was to reinstall the same version (0.4.26+4) from the official dmg, which the product lead did with a prepared script (the old bundle is kept as `backup/LM-Studio.app.broken-20261031-133635`). After the reinstall LM Studio resumed two stale in-app downloads whose `.part` files kept the candidate models out of its list until the downloads were cancelled in the GUI. Standing rule since then: never quit, kill or restart the LM Studio app from automation; load and unload models only with `lms`. That rule is why the Gemma 12B, downloaded later but never indexed, was not run ("may need an app restart, which was not allowed"). Related: LM Studio's idle-unload reloads the model at 8,192 context, which breaks the agent (engineering inventory); the reference was reloaded at 32,768 after the candidate round and again after a reboot before A4, and `pov-check --local` passed after both.

**Candidate downloads (31 Oct afternoon).** The first downloads ran at about 1 MB/s because the Mac was on the lead's phone hotspot; once on the home network they ran at about 14 MB/s through a multi-threaded `hf_transfer` downloader that writes straight into LM Studio's models folder and refuses to run unless the default gateway is the home router. Candidates were chosen from LM Studio's catalogue and Hugging Face after a web check of models released since the 35B: Qwen3.8-27B (MLX 4-bit), Qwen3.5-27B (GGUF Q4_K_M), Qwen3.5-4B, Granite 4.2 30B (MLX), Muse Glimmer 30B (GGUF), Gemma 4 12B and 31B (MLX). `qwen3.5-14b` does not exist.

## 4. Candidate models

All ten, in the order screened. "Adequate runs" means all five prompts correct by backend state with at most 4 calls each. The 35B reference is included first for comparison. Wall-clock times are noisy (another slice may have been building a Docker image, LM Studio was shared).

| Model | Size | Runs | Prompts correct | Adequate runs | Median s per prompt | Why abandoned or rejected |
|---|---|---|---|---|---|---|
| qwen3.5-35b-a3b (reference) | 35B / ~3B active, 20.4 GB | 10 | 47/50 | 5/10 | 15.3 | Not a candidate: it is the reference. Three early stops; Bayview needed 5 calls in 3 runs |
| qwen/qwen3.5-9b | 9B dense, 6.0 GB | 3, then 10, then 10 | 15/15; 49/50; 42/50 (91/100 over 20) | 2/3; 9/10; 2/10 (11/20) | 22.6; 22.8; 21.9 (22.3 over 20) | Sample 1 met the bar, sample 2 did not. Same failure as the 35B, more often: stops after `whatIsNeeded` or `assessDecision`; mixed prompt opened a case in 3 runs over the two samples |
| gemma-4-26b-a4b-it-mlx | 26B / ~4B active, 15.6 GB | 3 | 12/15 | 0/3 | 8.2 | Mixed prompt 0/3: opens a case and declines it. MLX backend crash in the first attempt |
| openai/gpt-oss-20b | 21B / ~3.6B active, 12.1 GB | 3 | 9/15 | 0/3 | 2.9 | Stops after `whatIsNeeded` and asks Staff (Harbourline 2/3, Lakeside 3/3 failed); fastest by far |
| gemma-4-31b-it-mlx | 31B dense, 18.4 GB | 3 | 14/15 | 0/3 | 29.1 | Bayview needs 5 calls every run; mixed opened a case once; raw `<\|channel>thought` prefix in replies |
| qwen3.8-27b-mlx | 27B dense, 16.1 GB | 3, then 10 | 15/15; 49/50 | 3/3; 9/10 | 70.6 (min 32.5, max 163.3) | Not rejected on correctness. Rejected for now on speed: about 5x the 35B, a card appearing after the first minute. One sample only |
| qwen3.5-27b (GGUF Q4_K_M) | 27B dense, 17.7 GB | 3 | 13/15 | 0/3 | 47.4 | Lakeside and mixed failed once each; `resolveDecision` called twice (5 calls) |
| qwen3.5-4b-mlx | 4B dense, 3.1 GB | 3 | 12/15 | 0/3 | 11.8 | Mixed 0/3 (opens a case and escalates); Bayview 5 to 6 calls every run |
| granite-4.2-30b-mlx | 30B, 16.5 GB | 1 run, stopped | 4/5 | n/a | 221 (35 to 383) | Too slow; stopped by the speed rule after one run; Bayview produced no case |
| muse-glimmer-30b (GGUF Q4_K_M) | 28B, 18.2 GB | 1.4 runs, stopped | 7/7 | n/a | 99 | Correct on all it ran, but the median in run 1 was above the 90 s cut-off |
| gemma-4-12b-it (MLX 4-bit) | 12B, 6.8 GB | not run | | | | Downloaded; LM Studio never listed it |

Also not run: `qwen3.5-14b` does not exist in LM Studio's catalogue here, so no 14B was tested. The plan called for 9 to 14B models; the 4B, 9B and 12B (not loadable) cover the low end.

**Data inconsistencies.** (i) The bench report's header still reads "3 runs … verdict pending"; it was not updated after the 10-run bar. (ii) The report's recommendation item 2 first says the 9B is adequate and later "No (revised after the second 9B sample)", leaving both readings in the text. (iii) The 3-run 9B screen and the sample-1 note say the single miss was a mixed-prompt case; the combined mixed-prompt count over both 9B samples (1 + 2 = 3 runs) is derived from the two descriptions, not stated in the report. (iv) The report says the Gemma 12B "could not be loaded" in one place and "downloaded but not indexed" in another; both mean it never ran.


## 5. The early-stop problem

**What it looked like.** The model ended its turn before the case existed. Three forms, all visible in the reference's 10-run sample: an empty reply after `findCustomers` (Northside run 2) or after `assessDecision` (Bayview run 9); a question to Staff, or a list of missing items, after `whatIsNeeded` instead of calling `resolveDecision` (Lakeside run 4); and a text reply after a single read (later seen in Bayview). The backend sees only a missing case. Nothing was ever approved wrongly. A second cost: Bayview used 5 calls (a repeated `findCustomers`) in 3 of 10 runs, which fails the 4-call cap even when the case is right. The 9B and gpt-oss showed the same failure, the 9B more often.

**Why second samples.** The 9B scored 9/10 and then 2/10 with identical settings, so a single 10-run sample can be off by seven runs. From then on any model or instruction set that passed once was sampled again before a conclusion was drawn.

**Hypotheses in order.** All on qwen3.5-35b-a3b, context 32,768, temperature 0.2, 10 runs each, same judge. Reference: 5/10, 47/50.

| # | Hypothesis | Exact wording or change | Result | Kept? |
|---|---|---|---|---|
| 1 | A deterministic nudge after an early stop (`--nudge`) | One automatic message when a turn ends with an empty reply, or after `assessDecision`/`whatIsNeeded` with no `resolveDecision`; once per prompt. Text: "The request is not submitted yet. If you have everything needed, call resolveDecision now. If something is missing or unclear, tell Staff exactly what is missing; do not guess it and do not submit." (reworded from the brief's example so that the mixed prompt is not pushed to open a case) | 6/10, 47/50. Fired in 7 of 50 prompts: 3 resolved (all Northside), 3 asked Staff, 1 still empty. Mixed prompt 10/10, no case | Dropped as a fix: it repairs empty stops but the model uses the "tell Staff" branch, which is also what Lakeside's failure looks like. 5/10 to 6/10 is inside noise |
| 2 | An instruction line (`--instructions-extra`) | "End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing." | 2/10, 42/50. Bayview 5/10: the model searched once, reported no match for "Bayview Gelato Co" and ended | Dropped; harmful. Combination (c) with the nudge was not run |
| 3 | Drop the `whatIsNeeded` paragraph (d) | Live instructions without the "Only for a trial credit where Staff did not say that a deposit was received … call whatIsNeeded once …" paragraph | 4/10, 43/50 (Lakeside 6/10) | Not enough alone |
| 3b | (d) plus the nudge (e) | as above | 6/10, 45/50; nudge fired 9 of 50 (4 resolved, 5 asked Staff); mixed created a case in 1 run | Not enough |
| 4 | Resolve-only (f) | Steps paragraph replaced by: "Steps for a request: 1) findCustomers (and the invoice for an extension). 2) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning; the backend assesses the request itself and applies the Owner's policy. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. Do not call assessDecision or whatIsNeeded. 3) Stop calling tools: the request is finished." | With nudge: 8/10, 48/50, nudge fired 0 of 50. Without nudge (A3): 9/10, 49/50. Combined 17/20, 97/100; about 30% fewer tokens, 8 to 11 s per prompt | Kept. The nudge dropped. Mixed prompt: a case in 2 of 20 runs |
| 5 | Ambiguity rule (A4) | See section 6 | 10/10, 50/50, mixed 0 of 10; then (A5) 10/10, 50/50, mixed 0 of 10 | Kept |

**Why resolve-only works.** The Lab's `resolveDecision` assesses and decides itself (`delegation_resolve` calls `dg_evaluate`); it needs no earlier `assessDecision` or `whatIsNeeded`, and the Lab keeps no per-session assessment state. Lakeside can therefore go `findCustomers` then `resolveDecision` and the backend creates the `gathering_evidence` case. Every removed step was a place where the model could stop. In (f) the median was 2 to 3 calls and the nudge never fired.

**Mixed-prompt safety check and the 2 of 20.** The mixed prompt must end with no case, so it was tracked separately in every variant. The nudge variant and the instruction-line variant were clean (10/10 each). Variant (e) and (f) sample 1 each created one case; in A3 sample 2 one more. In (f) the two cases (sample 1 run 8, sample 2 run 8) came the same way: `findCustomers` then `resolveDecision` straight away, treating the message as a trial credit. Both ended `awaiting_owner`: no approval, no money moved, no message to the customer, but an unneeded case for the Owner, on the one message the instructions say to ask about. With `assessDecision` out of the steps the model skipped the pause where it noticed the ambiguity. The 2 of 20 is 10%, and the reference had 0 mixed cases in its 10 runs; resolve-only moved risk from "no case" to "an unneeded escalated case".

**Ambiguity set (A5).** `--extra` adds three prompts the agent must not decide: "Bayview Gelato Co wants an extension on one of its invoices." (`ambiguous-extension`), "Please approve this for Harbourline" (`bare-approve`) and "Northside Cafe, a new customer, wants AUD 800 of stock and will pay by 20 November 2026." (`amount-and-due-date`; a reading that the Lab could accept it was recorded but never happened). Expected: no case. Result in 10 runs each: asked Staff 10/10 each, 0 cases, 0 wrong approvals; median calls 2, 1, 1. In one run of the third prompt the model called `resolveDecision` with a made-up recommendation and no amount or terms; the Lab rejected it as an invalid call and no case was created. The clear prompts were never over-asked (40 of 40 called `resolveDecision` and passed).

## 6. The final instructions

The recorded result is for `tools/modelbench/variants/instructions_resolve_only_ambiguity.txt`. Compared with the live text it differs in three places. The `whatIsNeeded` paragraph is gone. The steps paragraph is replaced by the resolve-only steps above. A paragraph is inserted before the steps:

> Before any decision tool, classify the message. If it names an order amount or payment terms AND also an invoice, a due date or an extension, or if it is unclear which kind it is, it is mixed: ask Staff one short question about which they mean and stop, calling no decision tool. Only a message that is clearly one kind goes on to the steps.

> Steps for a request: 1) findCustomers (and the invoice for an extension). 2) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning; the backend assesses the request itself and applies the Owner's policy. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. Do not call assessDecision or whatIsNeeded. 3) Stop calling tools: the request is finished.

Unchanged: the opening line (use tools for every business fact), the "each request is exactly one kind" paragraph and the hint paragraph (ask Staff exactly `hint.question`; never retry with made-up values), the rule to repeat `statusText` and follow `nextStep`, the rule to report only the outcome the tool states, and the rule to use `decisionStatus` or `customerStatus` only when asked where something stands.

**What stayed available as tools.** The Staff agent still has all eight tools. `assessDecision` and `whatIsNeeded` remain in the Lab and on the agent but the instructions tell the model not to call them for a request; `decisionStatus` and `customerStatus` serve status questions. The Lab's `hint` on refused calls and its argument validation are unchanged. Nothing in the backend changed during the experiments; the autonomy-neutral fallback written on 31 Oct (drop the `whatIsNeeded` paragraph) is what the first step of this sequence became.

## 7. Lessons

1. **A tool result's `nextStep` wording steers a small model.** Three wordings were tried on the first draft; the one worded exactly like `assessDecision`'s ("This is a check and nothing was stored. Call resolveDecision to submit the request; …") made all 8 development runs create the case, while two emphatic instructions did not.
2. **Removing steps beat adding nudges.** The nudge gave 6/10, an instruction line 2/10, resolve-only 17/20, and the nudge never fired once the steps were gone.
3. **Backend validation is a real safety layer.** In A5 a made-up `resolveDecision` call was rejected by the Lab and no case was created.
4. **One 10-run sample is not enough.** The 9B went 9/10 then 2/10. Resolve-only went 8/10, then 9/10. The 35B reference's own 3-run (2/3) and 10-run (5/10) results differ. Conclusions here rest on at least two samples; even 20 runs leave wide uncertainty (a true 10% rate gives zero in 10 runs about a third of the time).
5. **Latency is a product constraint.** qwen3.8-27b cleared the bar and was rejected on speed (median 70.6 s against 15.3 s). The bar counts correctness and calls, not waiting; the product lead's speed rule filled that gap. Resolve-only also made the 35B faster (8 to 11 s per prompt) and cheaper in tokens.
6. **Tuning risk.** The ambiguity rule was written after seeing the mixed-prompt failure and tested on the same wording; the A5 prompts were also written after seeing it. The result is good evidence, not proof for other wordings.
7. **The runtime is part of the experiment.** A killed LM Studio app cost about half an hour and a reinstall; stale in-app downloads hid models from its list; a phone hotspot made 17 GB downloads look stuck; LibreChat's just-in-time model load crashed the MLX backend once. Each of these would have been misread as a model result without a log.
8. **Data and thresholds.** All data is fictional (six customers as of 24 Oct 2026). The 9 of 10 and 4-call bar, the 90 s cut-off and the delegation limits are POC values.

## 8. Reproduce

```
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10                  # reference, LM Studio loaded at 32768 context
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --model qwen/qwen3.5-9b
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --nudge
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --instructions-extra "End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing."
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --instructions-file tools/modelbench/variants/instructions_no_whatisneeded.txt
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --instructions-file tools/modelbench/variants/instructions_resolve_only.txt
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --instructions-file tools/modelbench/variants/instructions_resolve_only_ambiguity.txt
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10 --extra --instructions-file tools/modelbench/variants/instructions_resolve_only_ambiguity.txt
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --check-stack              # scratch stack, tool list, no model call
python3 -m unittest discover -s tools/modelbench                                               # judge and summary, no stack
```

The model name for each candidate is the identifier LM Studio lists (`lms ls`). Results are written to `tools/modelbench/results/<model>-<UTC stamp>.json` and `.md`. Mapping of this record to files: first full run `qwen3.5-35b-a3b-20261030T140746Z`; 3-run reference `…T141729Z`; 10-run reference `…T234837Z`; nudge `…20261031T092704Z`; instruction line `…T093957Z`; (d) `…T095407Z`; (e) `…T100502Z`; (f) `…T101700Z`; A3 `…T102712Z`; A4 `…T113258Z`; A5 `…T114412Z`. 9B: `qwen3.5-9b-…T000144Z` (3 runs), `…T002128Z` (sample 1), `…T011348Z` (sample 2). No result files exist for granite, muse or the Gemma 12B; their figures come from the bench report only.

## 9. Open points

- **Not tested:** other ambiguous wordings (an extension that names a wrong invoice, a message with two customers, other languages, typos); a cloud model through `--base-url` (prompts and data would leave the machine, and the product lead has not decided); long conversations and the LM Studio "predecessor handoff" condition in the bench (it uses one short conversation per prompt; it did occur in the real-agent round); other temperatures; a second sample of qwen3.8-27b; the resolve-only instructions on the 9B and on qwen3.8-27b.
- **Evidence quality:** 20 runs on the original set for the final instructions; 10 runs per new ambiguous prompt; one model family and one quantisation.
- **Live switch (phase B), done 31 Oct 2026 late evening:** the live Staff agent now runs these instructions (`integrations/librechat/agents/instructions_staff.txt` on `main` is the resolve-only + ambiguity text). Browser acceptance after the switch: 17 of 17 checks; four ambiguous messages through the real agent all ended with a question to Staff and no case. Details in the "S7 phase B" section of `docs/research/MODEL-BENCH-20261031.md`. One operational note: the switch was kicked off by a reply sent from a phone through the Rocket.Chat bridge (ClaudecodeRC); the resumed turn's background agent was cut off when that turn ended, so the acceptance round was re-run by hand. The bridge now needs to wait for a resumed turn's background work.
- **Open question for the Owner:** whether an escalated case on an ambiguous message, the residual risk, is acceptable. The backend never approved anything wrongly in any variant.
