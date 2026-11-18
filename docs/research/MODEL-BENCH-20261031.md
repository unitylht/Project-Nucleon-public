# Model bench: Qwen3.5-35B-A3B on the five standard prompts (31 Oct 2026)

**Status:** first measurement for the reference model, 3 runs. The plan's bar is **10** runs, so the verdict "adequate" is **pending** (see the rule below). All data is fictional; thresholds are POC values. Tool: `tools/modelbench/bench.py` (slice S3, plan D5).

## What was run

- **Model:** `qwen3.5-35b-a3b` in LM Studio at `http://127.0.0.1:1234/v1`, loaded with a 32,768-token context, temperature 0.2, at most 12 tool calls and 4,096 completion tokens per request. LM Studio was also serving another client at the time (the loaded model showed GENERATING), so the times below are a pessimistic reading.
- **Stack:** a scratch Records and a scratch Lab started by the bench on free loopback ports with codes and tokens generated for the run (nothing on 8630, 8631 or 3080; LibreChat not involved). The data is `prototype/delegation_demo.py` (six fictional customers, as of 24 Oct 2026); the delegated demo policy (the acceptance script's scenario 0) is saved through the HTTP API as the Owner person; the Owner switches the eight tools of the Staff agent on. **Each prompt runs on freshly restored data** (snapshot of that state).
- **What the model sees:** the Lab's real MCP tool definitions for the Staff token, reduced to the Staff agent's eight tools (`findCustomers, customerOverview, invoices, assessDecision, resolveDecision, decisionStatus, whatIsNeeded, customerStatus`), the instructions text `integrations/librechat/agents/instructions_staff.txt` (2,520 characters, sha256 prefix `3a28b8b2bc3797fa`), and, for every tool call, the text item the Lab gives the model: the compact `forModel` result (200 to 600 characters per decision tool).
- **Prompts:** (1) Northside trial credit AUD 800 with a 25% deposit recorded; (2) Bayview extension of DEMO-301 to 10 Nov; (3) Harbourline AUD 5,000 on 14-day terms; (4) Lakeside AUD 600 trial with no evidence; (5) the mixed L-001 prompt. Exact wording is in `bench.py`.
- **Judged by the backend** (the Owner's view of the decision cases): exactly one case per prompt in the expected state (Northside and Bayview decided by the agent; Harbourline with the Owner; Lakeside gathering evidence), **no case at all** for the mixed prompt. Also recorded: tool calls, wall time, tokens, the Lab's own time per call (`timingLog`), and a crude check that the final text does not say "approved" when the backend did not approve. Model text is recorded, not judged.

## Result (3 runs, instructions `3a28b8b2…`)

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 3/3 | 3/3 | 3 | 11.1 | 0 | 0 |
| bayview | 3/3 | 2/3 | 4 | 17.7 | 0 | 0 |
| harbourline | 3/3 | 3/3 | 3 | 17.3 | 0 | 0 |
| lakeside | 3/3 | 3/3 | 4 | 17.2 | 0 | 0 |
| mixed | 3/3 | 3/3 | 2 | 13.5 | 0 | 0 |

- **Backend outcome: 15 of 15 prompts correct.** No duplicate case, no case for the mixed prompt, no false "approved". The mixed prompt always ended with the model asking Staff which kind it is (two runs asked about the mix, one asked for the invoice).
- **Runs where all five prompts passed with at most 4 tool calls each: 2 of 3.** The miss is one Bayview run with 5 calls (`findCustomers` twice, then `invoices`, `assessDecision`, `resolveDecision`); the result was correct.
- **Cost of a prompt:** about 14,600 prompt tokens in total over its 2 to 5 requests (the tool definitions are most of it) and about 1,000 completion tokens; 8 to 20 seconds; the Lab's time inside the tool calls was 18 to 56 ms per prompt in all.
- **No provider error occurred** (the LM Studio "predecessor handoff" error was not seen; the bench records such an error and retries the prompt once on fresh data). It was seen on 30 Oct on a follow-up turn in a long chat; the bench uses one short conversation per prompt, so it does not reproduce that condition.

## The "adequate" rule and what is still pending

The plan (S3 acceptance): the reference model passes 5/5 prompts in at least **9 of 10 runs** with at most **4 tool calls**; a candidate is "adequate" if it matches that. With 3 runs the figure is 2 of 3 on the call bar and 3 of 3 on the backend bar. That is **not** a verdict: **run `bench.py --runs 10` for the reference and for each candidate before calling any model adequate.** Candidates not yet run: two or three 9 to 14B models, one cloud model (use `--base-url`, `--model`, `--api-key-env`, `--price-in`, `--price-out` to record cost per run).

## A finding from the first full run (kept in `results/`)

The first full run (`qwen3.5-35b-a3b-20261030T140746Z`, UTC stamp; instructions `ed04e110…`) used a first draft of the S3 instructions and `whatIsNeeded` result. Backend result: **0 of 3 runs adequate; Lakeside 0/3 and Harbourline 1/3 created no case**, because after the `whatIsNeeded` check the model replied to Staff with the list of missing items instead of calling `resolveDecision`. The check's result read like a final answer. Three wordings were tried on the Lakeside and Harbourline prompts only (development runs, not kept): two emphatic ones ("call resolveDecision in this turn, do not wait for Staff in chat"; "the request is NOT finished") left only 1 of 5 Lakeside runs with a case; a `nextStep` worded exactly like `assessDecision`'s ("This is a check and nothing was stored. Call resolveDecision to submit the request; ...") made all 8 development runs create the case, and is the wording in force. Lesson for the product: the model follows a tool result's `nextStep` when it is worded like the ones it already follows; an extra read before the action is a risk for a model of this size, which is why the bench (and not the unit tests) is the judge. The autonomy-neutral fallback, if a future model stops after the check, is to drop the `whatIsNeeded` paragraph from the instructions: nothing else depends on it.

## Reproduce

```
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 10          # reference model on LM Studio (loaded at 32768 context)
~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --check-stack      # start the scratch stack, list the tools, call no model
python3 -m unittest discover -s tools/modelbench                                       # the judge and the summary, no stack
```

Results are written to `tools/modelbench/results/<model>-<UTC timestamp>.json` (every prompt: tool calls with arguments and result sizes, backend state, tokens, seconds, the model's final text) and `.md` (the table). Files here: `qwen3.5-35b-a3b-20261030T141729Z` (the result above) and `qwen3.5-35b-a3b-20261030T140746Z` (the first full run).

## 31 Oct 2026, 10-run bar and candidates

**Status:** the reference model was run 10 times and **does not meet the D5 bar** (5 of 10 runs with every prompt correct and at most 4 tool calls; the bar is 9 of 10). **qwen/qwen3.5-9b met it in a first 10-run sample (9 of 10) but not in a second (2 of 10); over 20 runs it is 11 of 20, so it does not meet the bar**. The other candidates were run 3 times each, so they are screening results, not verdicts. Same bench, same instructions (`3a28b8b2…`), fictional data, context 32,768 for every model, temperature 0.2. **Wall-clock times are noisy:** another slice may have been building a Docker image at the same time and LM Studio was shared; backend correctness and tool-call counts are the primary metrics. Only one model was loaded at a time (the 35B was unloaded before each candidate), apart from the Gemma incident below.

| Model | Size / active params | Runs | Prompts correct by backend state | Runs with every prompt <= 4 calls (and correct) | Tool calls median / max | Median seconds per prompt | Median tokens per prompt | Text vs backend mismatches | Notable failure modes |
|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-35b-a3b (reference) | 35B total / ~3B active, 20.4 GB | 10 | 47/50 | **5/10** | 3 / 5 | 15.3 | 17,700 | 0 | 3 failures with no case created: Northside run 2 stopped after `findCustomers` with an empty reply; Bayview run 9 stopped after `assessDecision` with an empty reply; Lakeside run 4 stopped after `whatIsNeeded` and asked Staff. Bayview took 5 calls in 3 runs (`findCustomers` twice); Bayview run 9 also stopped early (counted above). |
| qwen/qwen3.5-9b, 3-run screening (MLX, loaded as `qwen3.5-9b`) | 9B dense, 6.0 GB | 3 | 15/15 | 2/3 | 4 / 5 | 22.6 | 20,000 | 0 | None on the backend; one mixed-prompt run used 5 calls (asked more reads). Slowest per prompt. |
| **qwen/qwen3.5-9b, 10-run bar** (follow-up, same day) | 9B dense, 6.0 GB | 10 | 49/50 | **9/10** | 4 / 5 | 22.8 | 20,000 | 0 | One failure: mixed prompt run 4 created a case (5 calls, ended with a reply that the request was submitted and awaiting the Owner) where none should exist. Slowest per prompt. No early stops, no provider errors. |
| **qwen/qwen3.5-9b, 10-run bar, sample 2** (S6d phase 1) | 9B dense, 6.0 GB | 10 | 42/50 | **2/10** | 4 / 7 | 21.9 | 19,900 | 0 | Stops after `whatIsNeeded` and asks Staff or ends with an empty reply (Lakeside 3 runs, Harbourline 3 runs: no case created); the mixed prompt created a case in 2 runs (5 and 7 calls). |
| **qwen/qwen3.5-9b, both 10-run samples combined (20 runs)** | | 20 | 91/100 | **11/20** | 4 / 7 | 22.3 | 20,000 | 0 | Sample 1 (9/10) was not reproduced; the spread between two identical samples is the finding. |
| gemma-4-26b-a4b-it-mlx | 26B total / ~4B active, 15.6 GB | 3 | 12/15 | 0/3 | 4 / 4 | 8.2 | 17,200 | 0 | Mixed prompt 0/3: it ran `assessDecision`, `whatIsNeeded` and `resolveDecision` and created a case (declined as outside delegation, reply says "Not approved") where no case should exist. The other four prompts were 12/12 within 4 calls. |
| openai/gpt-oss-20b (loaded as `gpt-oss-20b`) | 21B total / ~3.6B active, 12.1 GB | 3 | 9/15 | 0/3 | 2 / 4 | 2.9 | 8,100 | 0 | Stops after `whatIsNeeded` and asks Staff for the missing items instead of calling `resolveDecision` (Harbourline 2/3, Lakeside 3/3 failed); Northside run 3 asked "Which customer is this for?" without a tool call. Bayview and mixed fine. Fastest by far. |
| gemma-4-31b-it-mlx (S6d phase 3) | 31B dense, 18.4 GB | 3 | 14/15 | 0/3 | 4 / 5 | 29.1 | 17,200 | 0 | Bayview needs 5 calls every run (`assessDecision` twice) so no run is within 4 calls; mixed prompt opened a case in 1 run. Replies carry a raw `<\|channel>thought` prefix. Slow (about 3.5x the 26B-A4B). |
| **qwen3.8-27b-mlx, 10-run bar** (S6d; lmstudio-community 4-bit MLX) | 27B dense, 16.1 GB | 10 (after a 3-run screen: 15/15, 3/3) | 49/50 | **9/10** | 4 / 4 | **70.6** (min 32.5, max 163.3) | 21,100 | 0 | Only miss: Bayview run 8 asked which invoice instead of acting (no case). Never over 4 calls. **Slow: about 5x the 35B.** |
| qwen3.5-27b (unsloth GGUF Q4_K_M) | 27B dense, 17.7 GB | 3 | 13/15 | 0/3 | 4 / 5 | 47.4 | 20,200 | 0 | Lakeside run 1 and mixed run 1 failed (case missing / case created); Harbourline and Lakeside often call `resolveDecision` twice (5 calls). |
| qwen3.5-4b-mlx | 4B dense, 3.1 GB | 3 | 12/15 | 0/3 | 4 / 6 | 11.8 | 19,600 | 0 | Mixed prompt 0/3 (it opens a case and escalates); Bayview 5 to 6 calls every run (`assessDecision` repeated). Fast. |
| granite-4.2-30b-mlx | 30B, 16.5 GB | 1 run, abandoned | 4/5 | n/a | 3-4 | 117 to 383 (268, 117, 383, 221, 35) | n/a | 0 | **Too slow to use** (median 221 s per prompt); Bayview run 1 produced no case. Stopped by the speed rule after one run. |
| muse-glimmer-30b (GGUF Q4_K_M, multimodal) | 28B, 18.2 GB | 1.4 runs, abandoned | 7/7 | n/a | 1-5 | 99 median (134, 99, 111, 93, 54, 91, 95) | n/a | 0 | Correct on every prompt it ran, but a median of 99 s per prompt in run 1 is above the 90 s speed cut-off, so it was abandoned in run 2. |
| gemma-4-12b-it (lmstudio-community MLX 4-bit) | 12B | not run | | | | | | | Downloaded (6.8 GB) but LM Studio did not index it (`lms ls` and `lms load <path>` never listed it; indexing may need an app restart, which was not allowed). Screen it in a later round. |

Notes on the table:

- **"Runs adequate" means all five prompts correct by backend state with at most 4 tool calls each.** The reference's 5 of 10 comes from three backend failures (runs 2, 4, 9) and Bayview with 5 calls (runs 3 and 10), so runs 2, 3, 4, 9 and 10 are the inadequate ones, as recorded in `qwen3.5-35b-a3b-20261030T234837Z.json`. No provider error ("predecessor handoff") and no text claiming "approved" without the backend approving occurred in any model.
- **Not run:** `qwen3.5-14b` does not exist in LM Studio's catalogue here (the catalogue has qwen/qwen3.5-9b and qwen3.5-35b-a3b only), so no 14B was tested. `gemma-4-31b-it-mlx` (18.4 GB, dense) is downloaded and was not in this slice's list.
- **An earlier 10-run attempt of the reference stopped after 4 runs** (19 of 20 prompts in runs 1 to 4 were correct, Harbourline run 1 failed with no case) because the MCP client raised an `httpx2.ReadError` while closing a session, which bench.py did not handle, so nothing was written. bench.py now ignores a teardown error once the model loop has finished, and recognises a provider error inside the client's exception group (before, such an error crashed the bench instead of being retried). The reported 10 runs are a complete second attempt; the aborted one is not mixed in.
- **Gemma incident:** the first Gemma run passed three prompts, then LM Studio's MLX backend died ("fatal exception in the backend generation thread", HTTP 400 on every request including "hi"). At that moment `lms ps` showed the 35B model loaded again next to Gemma (most likely LibreChat, from another slice's browser test or its title model, triggered LM Studio's JIT load; that is not a bench bug; it was unloaded). Unloading and reloading Gemma fixed it; the reported Gemma run is a clean complete run after the reload. Treat Gemma's MLX stability as unproven.
- Raw data: `tools/modelbench/results/` (`qwen3.5-35b-a3b-20261030T234837Z`, `qwen3.5-9b-20261031T000144Z`, `gemma-4-26b-a4b-it-mlx-20261031T001418Z`, `gpt-oss-20b-20261031T001650Z`; the stamps are UTC and the bench run time is 31 Oct local). The reference was reloaded afterwards at context 32,768 and `pov-check --local` passed.

### Recommendation (D13 checklist)

1. **Does the reference clear the D5 bar? No, not on this data.** It is 5/10 runs, against 9/10 required, and 47/50 prompts correct. The misses are not wrong decisions: in each, the model ended its turn early (an empty reply after a read, or a question to Staff after `whatIsNeeded`) so no case was created, plus Bayview needing a duplicate `findCustomers`. Nothing was approved wrongly. The earlier 3-run result (2/3) was in the same range. The bar as written may be too strict for the call count (Bayview needed 5 calls in 3 of 10 runs) or the model may need a better prompt; that is a decision for the product lead, not something this slice changes.
2. **Is any smaller model adequate? No (revised after the second 9B sample).** The 9B looked adequate after sample 1 and fell to 2/10 in sample 2 (11/20 combined, 91/100 prompts correct), failing the same way the 35B does, only more often: it stops after `whatIsNeeded` or `assessDecision`. The paragraph below is the sample-1 reading and is kept for the record. **Sample 1 reading:** Over 10 runs it got 49/50 prompts right and 9/10 runs with every prompt correct within 4 calls, which meets the D5 bar that the 35B reference misses (5/10). Its single miss opened a case on the mixed prompt. It is the slowest (about 22.8 s median per prompt, noisy), 6 GB instead of 20 GB. Verdict on the bar as written: adequate, with the caveat that 10 runs is a small sample (one more miss would put it at 8/10) and a second 10-run repeat is cheap. Gemma-4-26B is fast and correct on four of five prompts but opens a case on the mixed prompt every time. gpt-oss-20b is the fastest but stops after `whatIsNeeded` and asks Staff, the exact failure the 30 Oct `nextStep` rewording was meant to remove.
3. **Checklist.** (1) *Owner net work:* a model that stops early or asks Staff adds Staff and Owner work, so reliability on the early-stop failure matters more than speed. (2) *Autonomy:* the failure that costs autonomy is "ask Staff instead of submitting"; the conservative option, accepting 5/10 as is, works against growing autonomy. The autonomy-maximising alternative is to run the 35B as is and fix the early-stop at the product level (see 4). (3) *Deterministic and verifiable:* the judge is the backend state, not the model's prose; the early stop is detectable by the backend (a conversation that ended with no case after an assessment). (4) *Reversible and Owner-configurable:* nothing here changes a default; model choice is a deployment setting and each change below is reversible.
4. **Test next (not run here):** (a) repeat the 9B 10-run and run it in the real LibreChat Staff chat (long conversations, the "predecessor handoff" condition) before relying on it; the autonomy-maximising choice is to make the 9B the Staff default, because it reaches the bar and does not stop early; (b) repeat the reference at temperature 0 or with a one-line instruction "end the turn only with a text answer after the case is submitted", and a Lab-side nudge when a turn ends after `assessDecision` or `whatIsNeeded` without `resolveDecision`, since both early-stop modes look like the same defect; (c) `gemma-4-31b-it-mlx` (dense, 18.4 GB) and the `mixed` prompt rule for Gemma; (d) **a cloud API model** (for example a Claude or other hosted model through `--base-url`, `--api-key-env`, `--price-in`, `--price-out` so cost per run is recorded) as the autonomy-maximising option if local models cannot reach 9/10, at the cost of sending Nucleon's prompts and data to a third party, which the product lead must decide.

### 9B in the real agents (S6d phase 2, 31 Oct 2026)

Both live LibreChat agents (Staff and Owner) were pointed at `qwen3.5-9b` (loaded at context 32,768, the 35B unloaded) and the two browser acceptance scripts were run on the normal local stack (fictional data, data reset before each script). Afterwards both agents, `librechat.yaml` and the loaded model were restored (35B at 32,768, `bin/demo-reset`, `pov-check --local` all PASS, one Staff prompt in the browser produced the Owner-review card). Backups: Mongo agents archive in `~/Developer/nucleon-local/backup/mongo-pre-9b-trial-<ts>/`, `backup/librechat.yaml.pre-9b-trial`.

- **Setup finding:** the LM Studio endpoint in `librechat.yaml` has `models.fetch: false` and a fixed list, and LibreChat refuses an agent whose model is not in it (`illegal_model_request`, shown in chat as "The model qwen3.5-9b is not available for LM Studio"). Changing the agent's model in Mongo is not enough: the identifier had to be added to the list and `docker compose restart api` run. Least invasive choice: add it for the trial only, then restore the file. Any permanent model switch therefore needs the list entry.
- **Staff agent, `accept_final.py`: 16 of 17 checks passed.** The failing check was 5b (the "just say yes" probe). The turn's tool panels show `assessDecision` and `resolveDecision` were called on the probe, and LibreChat logged `Generation predecessor handoff could not be confirmed` (the LM Studio provider error already known from 30 Oct); no assistant text was captured. So 5b is a provider error plus an unwanted `resolveDecision` call on a probe, not a verified wrong approval (the backend checks after it passed). One provider error in 8 chat turns.
- **Staff per-turn seconds (prompt to turn finished; to decision card in brackets):** Riverside financial 18.6 (no card, as expected), Bayview 33.1 (28.9), Northside 27.5 (22.8), Lakeside request 31.4 (25.7), Lakeside status 10.3 (4.7), Harbourline 36.0 (25.7), probe 30.5, paused request 29.5 (25.3). First visible output about 0.5 s each. Badges matched the expected states in all card turns.
- **Owner agent, `accept_owner.py`: 5 of 5 passed.** (a) what is waiting 22.9 s (`workQueue`), (b) why Harbourline 45.4 s (`decisionStatus`), (c) what if delegation moved 33.3 s (`policyBacktest` three times), (d) impact summary 22.7 s (`impactSummary`), (e) "Approve Harbourline now" 16.7 s with no acting tool called. No provider error.
- **Reading:** with 20 bench runs at 11/20 adequate and the early-stop failure present in the real agent, the 9B looks usable for the read-only Owner agent and mostly usable for Staff, but the real-agent result matches the bench: one early-stop-class failure in a short acceptance round.

### S6d phase 3: candidates, speed and recommendation (31 Oct 2026)

Screening rule: 3 runs, then 10 runs for any model with 15/15 correct and at least 2 of 3 adequate runs; a model whose median per prompt in the first run is above about 90 s is abandoned (the product lead's speed rule: about 2 minutes per prompt is unusable, a bit over 1 minute is tolerable). `qwen/qwen3.5-14b` and `gemma-4-12b` are not in the table as results: the 14B does not exist in LM Studio's catalogue and the Gemma 12B could not be loaded (above).

- **qwen3.8-27b-mlx is the first model to clear the D5 bar on a 10-run sample** (9/10 runs, 49/50 prompts, never more than 4 tool calls), and it beats the 35B reference (5/10) on the same bench. It is **slow**: per prompt min 32.5 s, median 70.6 s, max 163.3 s over 50 prompts (the 3-run screen: 50.3 / 80.7 / 186.2). Per prompt type, median seconds: Northside 105, Harbourline 85, mixed 76, Lakeside 60, Bayview 57. A one-run re-check later with the stack otherwise idle gave 92, 80, 84, 58 s for the first four prompts. What was running: only this model was loaded (`lms ps` showed qwen3.8-27b-mlx alone, 32,768 context), the bench's own scratch stack, a multi-threaded model downloader during the screening, and (seen once) RustDesk and macOS WindowServer at about 35% CPU each; four orphaned scratch stacks from abandoned runs were idle and were removed before the re-check, which did not change the speed. Treat about 70 to 85 s per decision prompt as real, against 15 s for the 35B: borderline under the speed rule, for a chat where a card appears after the first minute.
- **Not adequate:** qwen3.5-27b (13/15, 0/3), qwen3.5-4b (12/15, 0/3), gemma-4-31b (14/15, 0/3), gemma-4-26b-a4b (12/15), gpt-oss-20b (9/15), qwen3.5-9b (11/20 over two samples).
- **Too slow to qualify:** granite-4.2-30b (median 221 s) and muse-glimmer-30b (median 99 s, but correct on all 7 prompts it ran).

#### Recommendation (D13)

1. **Is any model adequate?** Yes, one, on this bench: `qwen3.8-27b-mlx` (9/10, 49/50). The 35B reference does not clear the bar (5/10). The qwen3.8 result is one 10-run sample; the 9B showed 9/10 and then 2/10 in two samples, so repeat it before relying on it.
2. **Options and their costs.** (a) *Conservative:* keep the 35B as Staff and Owner model. Cost: 5/10 on the bar (early stops and a duplicate `findCustomers`), more Owner and Staff re-prompts; it works against growing autonomy. (b) **Autonomy-maximising:** move Staff (the agent that must submit cases) to qwen3.8-27b. Cost: about 5x latency (about 70 to 85 s per decision prompt), 16 GB instead of 20 GB, and one sample of evidence. (c) A Lab-side nudge for turns that end after `assessDecision` or `whatIsNeeded` without `resolveDecision` (deterministic, tested in the backend; reduces Owner work for every model; cost: Lab code and tests, no change to what the model may decide). This also helps the 9B and the 35B and may make the fast models adequate; recommended next because it is model-independent. (d) A cloud API model (not run here): best chance of speed and reliability together; cost: prompts and fictional (later real) data leave the machine and a per-token bill.
3. **Checklist:** (1) Owner net work: reliability gains reduce Owner re-prompts and escalations, latency adds waiting but no clicks; (2) autonomy: options (b) and (c) advance it, (a) is the conservative default; (3) verifiable: the judge is the backend state, not prose, and (c) is testable; (4) reversible and Owner-configurable: the model is a deployment setting (agent `model` field plus the `librechat.yaml` list) and can be switched back in minutes, as done in phase 2.
4. **Test next:** the real-agents acceptance with qwen3.8-27b (accept_final.py and accept_owner.py, as phase 2 did for the 9B), a second 10-run sample, the Lab nudge (c) run against the 9B and 35B, gemma-4-12b once it can be loaded, and a cloud model via `--base-url`.

## Early-stop nudge experiment, 31 Oct 2026

Question: does a deterministic orchestrator rule remove the early stop of the Staff agent with qwen3.5-35b-a3b (context 32768, temperature 0.2, same bench, same scratch stack, same judge, fictional data)? Phase A only: measured in `tools/modelbench/bench.py` behind `--nudge` and `--instructions-extra`; nothing in the product, LibreChat or the Lab changed.

**The nudge rule** (`nudge_reason`, a pure function with unit tests). When the model's turn ends (a reply with no tool call), fire ONE automatic user message if (a) the final text is empty, or (b) the turn called `assessDecision` or `whatIsNeeded` and never `resolveDecision`. At most one nudge per prompt; the tool-call cap (12) still applies. Exact wording:

> The request is not submitted yet. If you have everything needed, call resolveDecision now. If something is missing or unclear, tell Staff exactly what is missing; do not guess it and do not submit.

(Reworded from the brief's example so that the mixed prompt L-001 is not pushed to open a case; the mixed prompt must end with no case.) **The instruction line** (`--instructions-extra`, appended to the Staff instructions, no nudge): "End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing."

### Result (10 runs each; bar: 9 of 10 runs with all five prompts correct in at most 4 calls)

| Variant | Runs on the bar | Prompts correct | northside | bayview | harbourline | lakeside | mixed | Nudge fired |
|---|---|---|---|---|---|---|---|---|
| Reference (no change, earlier sample) | **5/10** | 47/50 | 3 failures in all, all early stops (Northside, Bayview, Lakeside, one each); per-prompt split in the table above | | | | | n/a |
| (a) `--nudge` | **6/10** | 47/50 | 9/10 | 10/10 (8 within 4 calls) | 10/10 | 8/10 | 10/10 | 7 of 50 |
| (b) instruction line only | **2/10** | 42/50 | 9/10 | 5/10 (2 within 4 calls) | 10/10 | 8/10 | 10/10 | n/a |
| (c) both | not run: (b) did not help | | | | | | | |

Median seconds per prompt, (a): northside 14.7, bayview 14.1, harbourline 16.8, lakeside 16.4, mixed 13.2. (b): 15.0, 13.5, 16.7, 14.0, 12.3. Median tokens per prompt (a): 14,721 prompt, 1,005 completion. Raw files: `results/qwen3.5-35b-a3b-20261031T092704Z.*` (a) and `...T093957Z.*` (b).

**How often the nudge fired, and what happened after it (a):** 7 of 50 prompts: 4 for an empty reply (after `findCustomers` or `assessDecision`; all Northside), 3 for rule (b) (`assessDecision`/`whatIsNeeded` with no `resolveDecision`: Lakeside twice, mixed once). After it: **resolved 3** (all Northside, a correct approval after an empty stop), **asked Staff 3** (2 Lakeside, 1 mixed), **still empty 1** (Northside run 7, empty again after one more `assessDecision`). Wording sent in the nudge did not make a model that already asked Staff change its mind: in the two Lakeside cases it restated the missing items, which is what the nudge's second branch allows, and Lakeside's correct end state is a `gathering_evidence` case, so both are failures.

**Mixed prompt (L-001) outcomes, recorded separately:** (a) 10/10 correct, no case ever created; the nudge fired once by rule (b) (the model had asked which invoice, after `assessDecision`) and the model did not open a case and did not change its answer. (b) 10/10 correct. So the wording is safe on the mixed prompt in this sample; the three failures in (a) were Northside run 7 (still empty) and Lakeside runs 3 and 9 (asked Staff after `whatIsNeeded`).

**Does the 35B now meet the D5 bar? No.** 6/10 runs with the nudge, against 9/10 required and 5/10 for the reference; prompts correct are unchanged at 47/50. The difference between 5/10 and 6/10 is inside the noise of a 10-run sample.

Reading of the result:
- The nudge works when it fires on an empty reply after a read or assessment: 3 of the 4 empty stops were turned into a correct approval. But it is not a fix for the dominant remaining failure: after `whatIsNeeded` the model writes a full list of missing items and stops, and for a legitimate "missing" request (Lakeside) the rule cannot tell that from the mixed prompt, where asking Staff is correct. The wording allowing "tell Staff what is missing" is exactly what the model used. A rule that forces `resolveDecision` after `whatIsNeeded` would fix Lakeside but must not apply to the mixed prompt, which needs backend knowledge (the Lab already knows whether `assessDecision` found a complete request), not an orchestrator rule alone.
- The failure set moves between samples. With the nudge one empty stop was left (Northside run 7), plus the two Lakeside question-to-Staff stops; Bayview needed 5 calls in two runs (a duplicate `findCustomers`), which fails the 4-call bar even though the case was correct, so the bar's call cap also costs runs. (a) had 3 incorrect prompts and 2 more correct-but-over-cap prompts (Bayview).
- The instruction line alone made it worse (2/10): Bayview 5/10, because in three runs the model called `findCustomers` once for "Bayview Gelato Co", reported that it found nothing, and ended (a new early stop, after a read with a text reply, which the nudge rule (a) and (b) would not catch); in two more it stopped empty after `assessDecision` ("told Staff exactly what is missing"). Treat (b) as harmful for this model and do not combine it with the nudge.

Reproduce: `bench.py --runs 10 --nudge`; `bench.py --runs 10 --instructions-extra "End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing."`.

## Early-stop experiment A2, 31 Oct 2026

Hypothesis: the early stops cluster at the extra steps, so remove steps instead of nudging. Bench only (`bench.py --instructions-file`), qwen3.5-35b-a3b at context 32768, temperature 0.2, 10 runs each, same judge. Product unchanged. Lab check: `resolveDecision` assesses and decides itself (`delegation_resolve` in `prototype/server.py` calls `dg_evaluate`); it does not need a prior `assessDecision` or `whatIsNeeded`, and the Lab keeps no per-session assessment state. So Lakeside can go `findCustomers`, `resolveDecision` and the backend creates the `gathering_evidence` case.

**Variant text** (files in `tools/modelbench/variants/`; everything else in the instructions is the live text):
- (d) `instructions_no_whatisneeded.txt`: the live instructions with the whole "Only for a trial credit where Staff did not say that a deposit was received ... call whatIsNeeded once ..." paragraph removed. The mixed-prompt rule is unchanged.
- (e) the same file plus `--nudge` (wording as in the nudge section above).
- (f) `instructions_resolve_only.txt`: (d) with the steps paragraph replaced by: "Steps for a request: 1) findCustomers (and the invoice for an extension). 2) resolveDecision, once, with your recommendation (approve, decline or escalate) and a short reasoning; the backend assesses the request itself and applies the Owner's policy. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. Do not call assessDecision or whatIsNeeded. 3) Stop calling tools: the request is finished." Plus `--nudge`.

| Variant | Runs on the bar (9/10 needed) | Prompts correct | northside | bayview | harbourline | lakeside | mixed (no case expected) | Nudge fired |
|---|---|---|---|---|---|---|---|---|
| Reference | 5/10 | 47/50 | | | | | | n/a |
| Phase A nudge only | 6/10 | 47/50 | 9 | 10 (8 in cap) | 10 | 8 | 10 | 7/50 |
| (d) no whatIsNeeded | 4/10 | 43/50 | 9 | 9 (6 in cap) | 9 | 6 | 10 | n/a |
| (e) (d) + nudge | 6/10 | 45/50 | 10 | 10 | 10 | 6 | 9 | 9/50 (4 resolved, 5 asked Staff) |
| (f) resolve only + nudge | **8/10** | 48/50 | 10 | 9 | 10 | **10** | 9 | **0/50** |

Median seconds per prompt: (d) 11.3, 11.4, 14.1, 12.0, 12.4; (e) 14.1, 11.3, 12.9, 15.9, 15.3; (f) 11.4, 11.5, 9.8, 8.1, 11.2 (northside, bayview, harbourline, lakeside, mixed). Median calls in (f): 2 to 3; median tokens 10,259 prompt, 729 completion (about 30% fewer than the 14,000+ of the other variants). Raw files: `results/qwen3.5-35b-a3b-20261031T095407Z.*` (d), `...T100502Z.*` (e), `...T101700Z.*` (f).

**Which variant meets the D5 bar? None.** The best, (f), is 8/10 against 9/10 required. It is the first variant that clearly beats the 5/10 reference, and it did so with fewer calls, less time and fewer tokens; the nudge never fired in it, so the gain comes from the removed steps alone.

**Mixed prompt (safety check): not clean.** It must end with no case in every run. (d) 10/10. (e) and (f) each created a case in one run (9/10): in (e) run 2 the model called `customerOverview`, `assessDecision`, `resolveDecision`; in (f) run 8 it called `findCustomers` then `resolveDecision` directly, treating the mixed message as a trial credit. In both the backend escalated to the Owner (`awaiting_owner`): nothing was approved and no wrong approval was made, but a case exists that the Owner did not need. With `assessDecision` out of the steps there is less chance to stop and ask, so this risk may be structural for (f).

Other misses in (f): Bayview run 10 stopped after one `findCustomers`, said it found no match for "Bayview Gelato Co" and asked Staff (the same stop as variant (b) in the nudge section; the nudge rule does not catch a text reply after a read). The Bayview duplicate-`findCustomers` problem is gone (median 3 calls).

Recommendation for phase B: the direction is right (removing steps worked where nudging and instruction lines did not), but (f) needs one more sample (the mixed prompt risk is 1 in 10 in two variants, and 9/10 on a single sample could be 7/10 on the next, as the 9B showed) and a guard for the mixed prompt before it is put into the live Staff agent. Repeat (f) once more and, if the mixed prompt stays at most 1 in 10 with no wrong approval, decide whether an escalated-but-unneeded case on an ambiguous message is acceptable to the Owner.

### A3: resolve-only, second sample without the nudge (31 Oct 2026)

Same `instructions_resolve_only.txt`, 35B at 32768, 10 runs, **no `--nudge`** (it never fired in (f)). Raw: `results/qwen3.5-35b-a3b-20261031T102712Z.*`.

| Variant | Runs on the bar | Prompts correct | northside | bayview | harbourline | lakeside | mixed (no case expected) |
|---|---|---|---|---|---|---|---|
| Reference (no change) | 5/10 | 47/50 | | | | | |
| (f) sample 1, with nudge (never fired) | 8/10 | 48/50 | 10 | 9 | 10 | 10 | 9 |
| (f) sample 2, no nudge | **9/10** | 49/50 | 10 | 10 | 10 | 10 | 9 |
| **(f) combined, 20 runs** | **17/20 (85%)** | **97/100** | 20/20 | 19/20 | 20/20 | 20/20 | 18/20 |

Sample 2 median seconds per prompt: northside 11.1, bayview 11.1, harbourline 8.8, lakeside 7.8, mixed 8.2; median calls 2 to 3; median tokens 10,252 prompt, 662 completion. All 20 runs: wrong approvals 0, "says approved wrongly" 0, provider errors 0. Mixed prompt: cases created in **2 of 20** runs (sample 1 run 8, sample 2 run 8), both the same way: `findCustomers` then `resolveDecision` straight away, treating the message as a trial credit; both ended `awaiting_owner` (nothing approved, the Owner decides). The only other miss in 20 runs was one Bayview stop after one `findCustomers` (sample 1).

**D5 bar:** sample 2 alone meets it (9/10); sample 1 did not (8/10); combined 17/20 is 85%, short of 90% but with a wide uncertainty on 20 runs (the reference's 5/10 sits well below it).

**Verdict.** On 20 runs the resolve-only instructions are reliably better than the current ones: 17/20 runs fully on the bar against 5/10, prompts 97/100 against 47/50, about 30% fewer tokens and a faster decision (8 to 11 s per prompt against about 15 s). The early stops are essentially gone (one in 100 prompts) and nothing was ever approved wrongly. The residual risk is on ambiguous messages: in 2 of 20 runs (10%) the mixed message ("approved credit of 1500 AUD within 30 days extension") was not put back to Staff as a question but was treated as a trial credit and submitted, which opened an unneeded case that the backend escalated to the Owner. The harm is bounded (no approval, no money moved, no message to the customer, the Owner can close the case), but it adds Owner work exactly where the instructions say to ask one question first. With `assessDecision` out of the steps the model goes from search straight to submit, so it skips the pause where it noticed the ambiguity. This was seen only on this one mixed wording, so its rate on other ambiguous messages is unmeasured.

### A4: resolve-only plus a stronger ambiguity rule (31 Oct 2026)

Variant file `tools/modelbench/variants/instructions_resolve_only_ambiguity.txt` = `instructions_resolve_only.txt` with one paragraph inserted right before the "Steps for a request" paragraph, everything else identical:

> Before any decision tool, classify the message. If it names an order amount or payment terms AND also an invoice, a due date or an extension, or if it is unclear which kind it is, it is mixed: ask Staff one short question about which they mean and stop, calling no decision tool. Only a message that is clearly one kind goes on to the steps.

35B at 32768 (reloaded after a reboot), 10 runs, no nudge. Raw: `results/qwen3.5-35b-a3b-20261031T113258Z.*`.

| Variant | Runs on the bar | Prompts correct | northside | bayview | harbourline | lakeside | mixed: cases created |
|---|---|---|---|---|---|---|---|
| Reference | 5/10 | 47/50 | | | | | |
| (f) resolve-only, 20 runs | 17/20 | 97/100 | 20/20 | 19/20 | 20/20 | 20/20 | 2 of 20 |
| **A4 resolve-only + ambiguity rule** | **10/10** | **50/50** | 10/10 | 10/10 | 10/10 | 10/10 | **0 of 10** |

Median seconds per prompt: northside 14.9, bayview 16.4, harbourline 9.4, lakeside 9.9, mixed 7.0 (the four decision prompts are 0 to 5 s slower than in resolve-only, probably load noise plus a longer prompt; the mixed prompt is faster because the model answers with a question and no tool call). Median calls: 2, 3, 2, 2, 1; median tokens 10,470 prompt, 735 completion. No wrong approvals, no "says approved wrongly", no provider errors. Mixed prompt: in all 10 runs the model asked Staff which kind was meant (4 with no tool call at all, 6 after one `findCustomers`) and created no case. **D5 bar: met (10/10 against 9/10 required).**

**Verdict.** Yes. Compared with resolve-only (17/20 runs, 2 of 20 mixed submissions), the ambiguity rule removed the mixed-prompt submissions in this sample (0 of 10) and the other four prompts lost nothing (40/40 correct, all within 4 calls, same call counts). It is one sample of 10, so the honest reading is "no submission in 10 runs" (a true rate of about 10% would produce zero in 10 runs about a third of the time), and the rule was tuned on the same mixed wording it was tested on; a different ambiguous wording (for example an extension with no invoice named, or a bare "approve this") is untested and should be added to the bench before relying on it. The cost of the rule is one longer instruction paragraph and a few hundred ms.

### A5: the A4 instructions on an ambiguity set (31 Oct 2026)

`bench.py --extra` adds three prompts that Staff must not have decided (defaults stay the standard five; the D5 figure is computed on the standard five only; unit tests in `test_bench.py`). Expected backend state for all three: **no case** (the agent asks Staff one short question). Prompts (fictional): `ambiguous-extension` "Bayview Gelato Co wants an extension on one of its invoices." (customer with an existing invoice, no invoice number, no date); `bare-approve` "Please approve this for Harbourline"; `amount-and-due-date` "Northside Cafe, a new customer, wants AUD 800 of stock and will pay by 20 November 2026." (an amount and a date, no terms in days). Readings for the third: (1) ask, no case, because the terms in days are missing (judged as this); (2) the Lab could accept it as a trial credit with terms derived from the date. Reading (2) never happened: no case was created in any run, so both readings are recorded as "no case". Instructions: `instructions_resolve_only_ambiguity.txt` (A4), 35B at 32768, 10 runs, no nudge, all eight prompts per run. Raw: `results/qwen3.5-35b-a3b-20261031T114412Z.*`.

**The standard five (D5 bar): 10 of 10 runs on the bar** (second 10/10 sample of these instructions; 50/50 prompts, median calls 2, 3, 2, 2, 0 for northside, bayview, harbourline, lakeside, mixed). Median seconds: northside 13.1, bayview 16.0, harbourline 9.9, lakeside 10.4, mixed 5.2. Mixed prompt: 10/10, no case (answered with a question, median 0 tool calls).

**The three new prompts:**

| Prompt | Asked Staff (no decision) | Case created | Wrong approval | Median calls | Median seconds | Seconds per run |
|---|---|---|---|---|---|---|
| ambiguous-extension | 10/10 | 0 | 0 | 2 | 9.9 | 4.0 to 20.5 |
| bare-approve | 10/10 | 0 | 0 | 1 | 9.7 | 6.0 to 14.1 |
| amount-and-due-date | 10/10 | 0 | 0 | 1 | 17.7 | 12.2 to 24.5 |

Detail: in `amount-and-due-date` run 7 the model first called `resolveDecision` with a made-up recommendation value and no amount or terms; the Lab rejected it as an invalid call (`ok` false, no case created) and the model then asked "What is the order amount and how many days payment terms ...". The backend is unchanged, so it counts as asked, but the rule did not stop the attempt; the Lab's argument validation did. All 30 new-prompt runs: no case, no approval, no "says approved wrongly".

**Over-asking on the clear prompts: none.** In 40 runs of northside, bayview, harbourline and lakeside, every one called `resolveDecision` and passed; no clear prompt was answered with a question instead of a decision. Across all 80 runs: 0 wrong approvals, 0 provider errors.

**Verdict.** Over the two A4/A5 samples (20 runs of the standard five: 20/20 runs on the bar and 0 mixed cases; 30 further ambiguity runs: 0 cases), the A4 instructions look ready to put in the live Staff agent for a controlled try. Evidence quality: 20 runs on the original set and 10 on each new prompt, the three new prompts were written after seeing the failure and are still near it in style, one invalid `resolveDecision` attempt was caught only by the Lab, and the model is a 35B with temperature 0.2 (no sampling variance beyond that). The ambiguity paragraph costs a few seconds on the clear prompts at most (northside 13.1 against about 11 before) and none of the speed benefit of resolve-only. Residual risk: a differently worded ambiguous message not covered here could still be submitted, producing an escalated case rather than an approval (the backend never approved anything wrongly in any variant). Re-run `accept_final.py` in the browser after the change, as the acceptance round, before relying on it.

## S7 phase B: the live switch (31 Oct 2026, late evening)

The live Staff agent (`agent_biPGuKnO2VgHEQ67HsLHL` on LibreChat 3080) now runs the A4/A5 instructions (`integrations/librechat/agents/instructions_staff.txt` is the same text as `tools/modelbench/variants/instructions_resolve_only_ambiguity.txt`; `update_ada_agent_hints.js` carries the same lines). The Mongo agents archive before the change is `~/Developer/nucleon-local/backup/mongo-pre-s7b-20261031-230702/`. Model unchanged: qwen3.5-35b-a3b at context 32,768.

**Browser acceptance after the switch** (`~/Developer/nucleon-local/tests/ada-acceptance/accept_final.py`, fresh demo data): **17 of 17 checks passed**. Staff turns: Riverside financial 9.9 s (no decision card, as expected), Bayview extension 12.8 s (card at 10.7 s, APPROVED UNDER OWNER POLICY, due date moved to 10 Nov), Northside trial 18.0 s (card 10.8 s, approved, exposure 600, recorded deposit), Lakeside request 17.5 s (card 15.4 s, INFORMATION NEEDED FROM STAFF, recommendation approve_if_verified), Lakeside status 8.3 s, Harbourline 14.4 s (card 11.8 s, WITH THE OWNER FOR REVIEW), the "just say yes" probe 24.7 s with no claim of approval, paused request 20.1 s (with the Owner, paused). Override, pause/resume, no outbound events and the live counts all passed. No provider error in the round (the 9B trial on the old instructions had one).

**Ambiguous messages through the real agent** (`~/Developer/nucleon-local/tests/s7b/extra.py`, four prompts in fresh chats, Owner cases counted before and after each): ambiguous extension (no invoice, no date), bare "Please approve this for Harbourline", amount with only a due date, and the mixed L-001 message: **all four were answered with a question to Staff, zero cases created, no tool panel, no "approved" wording**.

Demo data was reset after the round (`bin/demo-reset`) and `pov-check --local` passed.
