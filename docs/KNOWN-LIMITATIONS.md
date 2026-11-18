# Known limitations: the ADA demo agent

Limitations we found while testing the Adaptive Decision Authority demo with real users. Each entry gives what happened, why, what we changed and what is still open. All data is fictional.

**Where these were seen:** the normal local M3 environment.
- **Chat:** LibreChat 3080, image `librechat:nucleon-card-v0.8.8-rc4-tailnet`, agent "Nucleon ADA Staff (Qwen)".
- **Model:** Qwen3.5-35B-A3B in LM Studio.
- **Nucleon:** Lab `83b3efb`.
- **Access:** group members reached it through a Tailscale share.

**What did not go wrong:** in every case below, the **backend behaved correctly**.
- It refused invalid arguments, and approved only what the Owner's policy allowed.
- It never sent anything to a customer, and the decision card was right.
- The failures are in the model's tool use and in what it wrote back.

## L-001: a mixed or incomplete request makes the agent guess and retry

**Seen:** 27 Oct 2026, a group member's rehearsal. The policy was version 0 (advisory). The prompt was:

> NorthSide Cafe wants an approved credit of 1500 AUD within 30 days extension what is your decision on this?

**What happened:**
- **Two kinds in one sentence:** the sentence mixes a new-customer **trial credit** (an amount and terms) with a payment **extension**, which applies to one existing invoice.
- **Qwen alternated between the two kinds:**
  - it called `assessDecision` for an extension with no invoice and got `INVALID_ARGUMENT`;
  - it sent arguments that failed schema validation, four times;
  - it invented the invoice number `1500AUDEXTENSIONREQUEST` and got `NOT_FOUND`.
- **Turn limit reached:** the two turns used 13 and 12 tool calls and hit LibreChat's agent step limit.
- **The reply:** it ended with *"No tool-calling budget remains"* and no clear answer.
- **What the backend did:** it stored one trial-credit case for Northside as **with the Owner for review**, which is correct under advisory policy v0. Nothing was approved. The demo data was reset afterwards.

**Why:**
- **The extension needs an invoice:** the request named none, and the instructions didn't tell the model to ask instead of guessing.
- **The step budget ran out:** the re-check loop in L-002 used up the rest of it.

**What we changed:** the agent's instructions now say:
- a request is exactly one kind;
- if the message mixes the two kinds, or an extension names no invoice, ask Staff one short question and stop;
- never invent an invoice number or any other argument;
- after `INVALID_ARGUMENT` or a schema error, ask for the missing detail instead of retrying with made-up values.

**Result:** the same prompt, run 3 times with real Qwen, used 1–3 tool calls and 21–24 s each time. Every run asked whether this is a trial credit or an extension of a specific invoice. No case was created.

**Still open:**
- **The model is still the weak point:** this rule lives in the instructions, so how well it works depends on the model. The backend stays the guard; a guessed invoice is still refused.
- **Possible backend improvement:** `assessDecision` could return a structured "which kind / which invoice?" hint, instead of a bare `INVALID_ARGUMENT`.
- **Update 31 Oct (S1b, S3):** the backend now returns the structured `hint` (S1b) and the Lab passes it to the model (S3); `integrations/librechat/agents/update_ada_agent_hints.js` (not yet run live) tells the agent to ask `hint.question` and stop. The mixed prompt is one of the five prompts of the model bench (`docs/research/MODEL-BENCH-20261031.md`), judged by the backend: no case may be created.

## L-002: the model's context window fell back to 8,192 tokens, so the agent forgot its own results and looped

**Seen:** 27 Oct 2026, while checking L-001. Even the standard demo prompts now looped.

| Request | Tool calls | Reply finished | Backend result | Qwen's final text |
|---|---|---|---|---|
| Northside trial credit, AUD 800 | 12 (step limit) | 56 s | approved by the agent ✔ | "I cannot call assessDecision…" ✘ |
| Bayview extension, DEMO-301 | 12 (step limit) | 53 s | approved, due date moved ✔ | "Staff needs to provide the invoice details" ✘ |
| Harbourline trial credit, AUD 5,000 | 12 (step limit) | 63 s | with the Owner ✔ | "the deposit amount … unclear" ✘ |
| Lakeside trial credit, AUD 600 | 12 (step limit) | 56 s | information needed from Staff ✔ | "blocked by the system constraint" ✘ |

**Why:**
- **The model had been reloaded with a smaller window:** Qwen is normally loaded with a **32,768-token** context, and every acceptance run and recording used that. LM Studio unloads a model it loaded on demand after 1 hour idle. When it was next needed, LM Studio loaded it again with its **default 8,192 tokens**.
- **The decision results don't fit:** the `assessDecision` and `resolveDecision` results are about 8.7k and 10k characters, so one request overflows 8,192 tokens.
- **The model loses its own history:** the oldest messages are dropped, so right after a successful `resolveDecision` Qwen's reasoning starts again from "Let me start by finding the customer". It also reported results it had never seen, such as "the search returned no matches".
- **It loops to the limit:** it repeats `findCustomers` and `assessDecision` until the step limit, then writes a confused summary.
- **The member's case too:** this also made L-001 worse.

**What we changed:**
- **Loaded at the right size:** Qwen is loaded with `lms load qwen3.5-35b-a3b --context-length 32768 --identifier qwen3.5-35b-a3b -y`. A manual load has no idle unload.
- **Saved as the default:** 32,768 is now LM Studio's saved default for this model, in `~/.lmstudio/.internal/user-concrete-model-default-config/mlx-community/Qwen3.5-35B-A3B-4bit.json`. Verified: an on-demand load after an unload came up at 32,768.
- **Checked before the demo:** `~/Developer/nucleon-local/bin/demo-reset` checks the loaded context and prints a warning with the fix command if it is not 32,768.
- **Clearer instructions:** the agent's instructions were rewritten as explicit steps that end with "stop calling tools; repeat the statusText".

**Result at 32,768 tokens, same prompts, fresh demo data, real Qwen:**

| Request | Tool calls | Reply finished | Backend result | Qwen's final text |
|---|---|---|---|---|
| The mixed L-001 prompt | 1 | 21 s | nothing stored | asks which kind ✔ |
| Northside trial credit, AUD 800 | 3 | 26 s | approved, exposure AUD 600 ✔ | repeats the statusText ✔ |
| Bayview extension, DEMO-301 | 3 | 26 s | approved, moved to 10 Nov ✔ | repeats the statusText ✔ |
| Harbourline trial credit, AUD 5,000 | 3 | 32 s | with the Owner ✔ | "escalated to the Owner" ✔ |
| Lakeside trial credit, AUD 600 | 3 | 32 s | information needed ✔ | asks for deposit and identity ✔ |

This is faster than the earlier measured runs, which took 33–60 s with up to 12 tool calls.

**Still open:**
- **The large results:** the decision tool results are still large, at about 2.5–3k tokens each, so a long conversation can still fill the window. A smaller result for the model (with the full detail kept in the card) would make the agent less sensitive to context size.
- **The setting can be lost:** if LM Studio's settings are reset, or someone loads the model from the LM Studio window, it may come back at 8,192. Run `demo-reset`, or `lms ps`, before a demo.
- **Model wording:** Qwen's wording can still be loose, and the card is the source of truth.

## Maintainer note: LibreChat bans clients that aren't browsers

LibreChat scores a non-browser HTTP client (a script using urllib or curl with a login) as a violation. With this configuration, one violation reaches the ban threshold, so it **bans that user, and the Docker gateway address `172.18.0.1`, for 2 hours**. Every login from the host Mac then fails, including the admin's. Test LibreChat in a real browser, for example with Playwright, using `fetch` from inside the page.
- **To clear a ban:** delete the `ban:*` and `BANS:*` documents in the Mongo `logs` collection, then restart the LibreChat app container.

## Where the agent instructions live

- **Storage:** the instructions are kept in LibreChat's Mongo database, in the `agents` collection, not in this repository.
- **Scripts:** the changes were made by these scripts, in this order:
  - `update_ada_agent_instructions.js`: resolve once.
  - `update_ada_agent_clarify.js`: L-001.
  - `update_ada_agent_steps.js`: the step rewrite, now in force.
  - They are all in `~/Developer/LibreChat-card-visibility-dev/nucleon-test/deploy-3080/`.
- **Backup:** the version before L-001 is in `~/Developer/nucleon-local/backup/ada-agent-instructions-before-clarify.json`.

## L-003: Quick setup's preview is an estimate

**Seen:** while building Quick setup, 11 Nov 2026 (fictional data in the checks).

- **What it shows:** what the agent would do if each customer asked today for N more days (7, 14 or 30) on each open invoice.
- **Why it can differ from real requests:**
  - It assumes the assistant recommends approving. A real assistant may recommend otherwise, and then the request comes to the Owner.
  - A real customer may ask for another number of days.
  - It tries at most 200 open invoices, and says so when it stops.
- **Still open:**
  - The agent's own decline line still counts days from the invoice's current due date, not from the request or the original due date.
  - The helper's text is in English only; the NTK owners read Vietnamese.
  - Prompts on the Decide page when a pattern appears (the second phase in the spec) are not built.

## L-004: what the Doctor's what-ifs do not judge

**Seen:** while building the Doctor, 11 Nov 2026 (fictional data in the tests).

- **What a what-if is:** the policy's limits (`delegation.would_approve`) applied to the facts recorded when each past case was decided.
- **What it leaves out:**
  - the assistant's recommendation, the track-record gate, advisory mode and a pause: a case that came to the Owner for one of these is counted, but no limit change would have let the agent decide it;
  - first credits for new customers: counted in the questions, never tried, because Quick setup does not cover them;
  - cases recorded before Nucleon kept their facts, or before a limit existed: left out of that what-if, and the answer says how many.
- **The local model as a doctor (trial of 11 Nov):** of 24 answers from a code-written facts sheet, 19 were right; 1 was empty, 2 used the wrong starting number, 1 left out a cost and 1 guessed a figure. Each took one to three minutes, because its thinking cannot be switched off. So Nucleon answers the preset questions itself, and the assistant's `doctor` tool only hands it the same lines.

## L-005: open after the live test of 11 November 2026 (real-data instance, real assistants)

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

**Fixed that night, for the record:** the Staff message "Customer 0010 wants more time to pay." (no invoice, no date) became the customer's latest open invoice plus exactly the 30 days the policy allows, and the agent approved it. The proxy in deploy/m3-local/bin/title-proxy now attaches a note to such messages (function vague_extension); three vague messages then each got one question and created no case. How the test was run: the scripts in deploy/m3-local/tests/bosstest/ (snapshot, conversations, restore).

## L-006: the session with the owners, night of 11-12 November 2026

Source: Hoang's write-up (docs/handbook/pack/sources/), checked against the case events. Timing and feedback are in the report pack, section 6.5.

**Fixed and re-tested on 12 November (commit "Owners' session (12 Nov)"):**

- Staff asked for 31 December; the model sent `days=78` (1 December) while its reasoning said 31 December, and the agent declined on the wrong date. `check_extension_dates` in `prototype/server.py` now refuses with `DATE_MISMATCH` when the reasoning names a later date that is not the requested one (tests in `prototype/test_auto_decline.py`).
- The chat card headed an agent decline "STATUS UNAVAILABLE" (`decision_badge` in `lab/card.py` had no branch for it).
- The vague-request note in `title-proxy` read "a 15-day extension" as no days given.
- Re-test with the real Staff assistant (`deploy/m3-local/tests/bosstest/live_chat3.py`, data restored afterwards): 31 December recorded as 31 December, 108 days; the card heading is right.

**Still open:**

| # | Where | What happens | What to do meanwhile |
| --- | --- | --- | --- |
| 14 | Customer names | The real-data records hold "Customer 0010", not the real business name, so the assistant cannot find a customer by its real name and asks. | Use the customer number, or import the real names. |
| 15 | Business date | Just after midnight in Sydney the system's date can be a day behind the tester's. "15 days" then lands a day earlier than expected and the assistant asks which date is meant. | Give the date itself when the exact day matters. |
| 16 | Owner's first use | The owners found the Owner side overwhelming and needed an interpreter. Quick setup and the reworded Control panel were not tested with the owners alone. | Not solved. |
| 17 | Test records | The three benchmark cases of the session (Customers 0010, 0011, 0014) are kept in the real-data instance and in its full backup, as evidence. The real-data instance is no longer public. | Nothing to do until the report is written. |
| 18 | Re-test, wrong invoice for a customer | Asked about an invoice that belongs to another customer, the assistant's question to Staff was confusing (it offered the same invoice number as an option). | Check the invoice number on the Customers page. |

## L-007: known issues fixed on 12 November 2026 (afternoon) and what stays open

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

Re-test script: `deploy/m3-local/tests/bosstest/live_chat4.py` (fictional data with the demo policy; the demo data was reset afterwards).
