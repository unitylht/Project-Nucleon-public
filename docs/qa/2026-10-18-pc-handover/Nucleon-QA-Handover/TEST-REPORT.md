# Project Nucleon — QA test report (tester tag `CL1018T`)

Exported from the Windows-PC test session for the developer. It replaces the chat-only report from that session
and keeps its finding IDs (**B1–B9, U1–U12, G1–G5**). Changes from the chat report are listed in
[§9](#9-corrections-to-the-in-session-chat-report).

**How to read this report**
- **Observed** = what the app showed or returned, backed by the evidence cited.
- **Suspected cause** = the tester's inference. It is not verified against code or logs.
- **Unknown** = not recorded during the session. It has not been reconstructed.
- Evidence references: `E##` = screenshot, `X##` = verbatim script output, `snapshot hh:mm:ss` = automation
  snapshot file, `console L#` = browser console log line. All are listed in
  [evidence/EVIDENCE-INDEX.md](evidence/EVIDENCE-INDEX.md). Excerpts are in
  [evidence/session-output-excerpts.md](evidence/session-output-excerpts.md).
- Severity is the tester's own assessment.

---

## 1. Scope and environment

| Item | Value |
|---|---|
| Site | https://nucleon.dracooz.top (shared practice instance) |
| Guide | *Nucleon Team Testing Guide*, revision 2, "practice release a9ce30d", 18 Oct 2026 ([test-pack/original/](test-pack/original/)) |
| Application revision | **Unknown.** The guide claims a9ce30d. It was not verified against the running site. |
| Actual test date/time | Sunday **2026-10-18**, 04:34:19 to ≈04:52 UTC (15:34 to ≈15:52 AEDT, UTC+11). The end time is approximate. |
| Simulated business date | **Fri 16 Oct 2026** ("Today is fixed at Fri 16 Oct 2026 for this demo"). Amounts in AUD. |
| Tester | An AI agent (Claude Code) driving the browser with Playwright, in the user's foreground window on a Windows 11 PC. Speeds and "help needed" are therefore not comparable with human testers. |
| Browser | Chromium-based browser controlled by Playwright MCP (headed). Build 155.0.8059.80 / UA "Chrome/155.0.0.0", read at packaging time (X28) and **assumed** to be the same install. Browser language zh-CN (native date pickers show 年/月/日). |
| Viewports | Desktop: 3840×1958 CSS px, inferred from screenshots at device pixel ratio 1. Narrow: window set to 390×844 (document width 375 px because of the scrollbar). Final extra check: 1400×900 (no screenshots). |
| Real phone | Not used. |
| Tester tag | **CL1018T**. The Hanting folder (HL1815A) was copied with HL1815A replaced by CL1018T in all four CSVs; see [test-pack/inputs-used/](test-pack/inputs-used/). |
| Roles used | Staff, Owner, Operator (Operator read-only; no console button pressed). |

## 2. Method and deviations from the guide

T1–T7 were followed in order. Expected results in the guide were treated as claims to verify. Additional checks:
role permissions, wrong-role codes, the operator console gate, a missing-date request, and a past requested date.

Things done that the guide did not ask for (all on CL1018T records or read-only):
1. Typed the Staff code at the Owner prompt, and the Owner code at the console prompt (U2).
2. Saved an opening balance **as Staff** on Manual B (C-0005), with source "CL1018T staff permission probe (fictional)" (B2).
3. Opened, without submitting, the Revert form of the 01-invoices.csv batch (B3). The guide forbids reverting 01; it was not reverted.
4. Signed in with the **Operator** code and read the Demo console. No Reset, Start empty, Restore or Copy was pressed.
5. Sent one extra request with no date ("…a bit later?") for Manual B. This created case req_366ba0f4763c2935, which was left with the owner and not decided.
6. Clicked **Apply 0 rows** on the repeat invoice import (the guide allows this). For the repeat payment import, **Close** was clicked instead.

## 3. Results by task, including successful checks

Elapsed times are approximate (from snapshot and screenshot times). No task was blocked.

| Task | Result | ≈Time (UTC) |
|---|---|---|
| T1 Manual records | Passed | 04:34:40–04:36:15 |
| T2 Note and decision | Passed | 04:36:25–04:38:46 |
| T3 / T3b CSV and errors | Passed. Guide mismatches G1, G2. | 04:38:58–04:40:25 |
| T4 Payments | Passed | 04:40:25–04:41:30 |
| T5 Exact amount | Passed | 04:41:47–04:43:23 |
| T6a/b/c Changes and revert | Passed | 04:43:30–04:45:25 |
| T7 Narrow screen | Layout passed. Sign-out bug B1 found. | 04:46:28–04:47:57 |
| Extra checks | See §4 | 04:45:30–≈04:52 |

### T1 — passed (E01, X02, snapshots 04:34:40–04:36:00)
- Records header: "Practice workspace: everything here is fictional. Today is Fri 16 Oct 2026. Amounts in AUD." That is inside the guide's 16 Oct–13 Nov window.
- At the start there were no other testers' tagged records. Customers were Harbour Demo Supplies (C-DEMO-01), Harbour Demo Logistics (C-DEMO-02) and Release check café (fictional) (C-0003).
- Created **CL1018T Manual A fictional = C-0004** and **CL1018T Manual B fictional = C-0005**.
- Manual A: CL1018T-001, Mon 5 Oct, AUD 1,000.00, due **Not on record**, still owed **Not recorded**.
- Manual B: CL1018T-001, Mon 5 Oct, AUD 200.00, due Sat 10 Oct, still owed Not recorded.
- The same invoice number for two customers was accepted.

### T2 — passed (E02, X04, snapshots 04:36:25–04:38:38)
- The note "CL1018T fictional test customer. Prefers a written payment date." (About: Manual A, Context to know) was saved as "draft by staff". Staff saw Retire but no Confirm.
- As Owner, Confirm on that note changed it to "confirmed by the owner". The other draft (Harbour Demo Supplies, "draft by fictional") stayed a draft.
- The request "Test CL1018T. Could we pay invoice CL1018T-001 on 14 November 2026 instead?" became **req_fcde410df1eff472**. The agent asked "Which customer's invoice is it?" and listed both CL1018T-001 holders. **No silent choice.**
- Sending with nothing selected was blocked ("Enter an answer.").
- After choosing Manual A, the prepared case showed:
  - Outstanding Not recorded, Due date now Not on record, Asked to pay on Sat 14 Nov 2026, Extension Not calculated, Overdue Unknown.
  - The confirmed note.
  - "Worth checking: … staff chose the one for CL1018T Manual A fictional."
- The Owner's decision button was disabled ("Choose an outcome") until an outcome was picked.
- Approved with the reason "Fictional test only" → "Approved. New payment date: Sat 14 Nov 2026."
- Reply: "Not sent." Staff's **Copy reply** put the exact reply text on the clipboard.
- Agent preparation: about 11–13 s for the initial step, and about 12–14 s after the answer (approximate; see the timing caveat in the evidence index).

### T3 / T3b — passed, with guide mismatches (E03, E04, X05–X08)
- The file was uploaded through the file input, as Invoices, with source "CL1018T Invoice test".
  - The mappings matched the guide. Amount still owed and Amount paid showed "— not in this file —". Dates: "Work it out".
  - Unknown customers blocked Apply ("Apply 0 rows" disabled) until both were set to "Create a new customer" and the preview updated.
  - The similar-name hints listed my Manual customers.
- Applied: **CL1018T Imported A fictional = C-0006** and **Imported B = C-0007**, each with CL1018T-CSV-001: AUD 1,000.00 / 200.00, Mon 5 Oct, due Sat 10 Oct, source "Import: CL1018T Invoice test".
- Repeat import with the same label: "This exact file was imported before … Already recorded: 2". Apply 0 rows created no new invoice; there was still one CL1018T-CSV-001 per Imported customer.
- T3b, source "CL1018T Invalid preview":
  - Row 2 rejected: `Invoice date "2026-02-31" is not a valid date.`
  - Row 3 rejected: `Invoice amount "1O0.00": Enter an amount using digits, for example 1200.50.`
  - Row 4 (CL1018T-VALID-PREVIEW) shown as New.
  - Clicked Close. No invoice was created (0 matches on the page).

### T4 — passed (E05, X09–X11)
- The payment mappings matched the guide. The preview showed "Allocate AUD 600.00 to CL1018T-CSV-001" for Imported A's row.
- After Apply:
  - A's invoice: **At most AUD 400.00**, "AUD 600.00 allocated".
  - B's CL1018T-PAY-002: 50.00, **Not allocated**.
  - No payment crossed to the other customer's same-numbered invoice.
- Repeat import with the same label: "Already recorded: 2". Closed without applying; payments unchanged, no second allocation.
- "Why not exact" gave two reasons: no opening balance, and payment completeness not confirmed.

### T5 — passed; calculations correct (E06, X13, X14)
- Owner opening balance on C-0006: as at 30 Sep 2026, 0.00 owed, "It includes none", source "Fictional test dataset starts from zero". Result: "Balance from it: AUD 400.00".
- The completeness form defaulted to "Only these customers". It was confirmed for Imported A only, Payments received only, 2026-10-01 to 2026-10-16.
- Imported A's invoice became **"AUD 400.00 exact, as of Fri 16 Oct"**. Imported B stayed "Not recorded" / not confirmed.
- Case **req_35c17a88570d5955** (customer chosen by Staff: Imported A) was checked independently:

  | Fact | Expected | Shown |
  |---|---|---|
  | Outstanding | 1,000.00 − 600.00 | AUD 400.00 exact |
  | Overdue | Sat 10 Oct → Fri 16 Oct | 6 days |
  | Extension | Sat 10 Oct → Sat 14 Nov (21 + 14 days) | 35 days |

  The Evidence table showed each formula. Approved with "Fictional test only".

### T6a — passed (E07, E08, E10, X15, X16)
- Staff recorded Money received for Imported A: 2026-10-14, 10.00, CL1018T-LATE-ENTRY, left unallocated. Result: "Payment recorded". Balance from it became AUD 390.00.
- The exact claim disappeared: "At most AUD 400.00".
- The completeness statement showed "No longer holds for CL1018T Imported A fictional: CL1018T-LATE-ENTRY changed inside the period afterwards." Payments complete to: Not confirmed.
- Reopening req_35c17a88570d5955 showed: "The records changed after this decision. Amount still owed: was exactly AUD 400.00 as of Fri 16 Oct 2026; now at most AUD 400.00. The decision stands; check it if it matters." The decision was unchanged.
- E12 (04:47) also shows a Records **Needs attention** section that explains the same cause with the word "added".

### T6b — passed (X17)
- Manual B's CL1018T-001 (the correction form rendered under the C-0005 row): amount 200.00 → 220.00, reason "Fictional correction test".
- Result: "Corrected"; the row shows "AUD 220.00 … Corrected by staff · version 2".
- Still owed stayed "Not recorded", although the form pre-filled an as-of date.
- Imported B's invoice was unchanged at 200.00.
- Not tested: whether the reason is mandatory.

### T6c — passed (X17, E12, snapshot 04:45:20)
- 04-revert-only.csv, source "CL1018T Revert test", with a new customer created: **CL1018T Revert Demo fictional = C-0008**, CL1018T-RV-001, 75.00.
- Revert on that row only, with the reason "Fictional reversal test" → "Import reverted". The batch status became "reverted".
- The customer and invoice disappeared from the lists and pickers. The page says "1 removed or reverted invoice is kept in the history and not used by the agent."
- The 01 and 02 batches and all other CL1018T records were unchanged.
- No impact review appeared. This batch had nothing depending on it.

### T7 — layout passed; B1 found (E09–E16, X20–X22)
- At a 390×844 window, on Home, the case and Records: document width = viewport width (375), so there was **no page-wide sideways scroll**.
- The top bar wraps to two rows. The three Records tables scroll inside their own containers, which the guide allows. Radio inputs are 13 px wide, but their labels are clickable.
- Role switching and the "All cases" navigation worked.
- Sign-out bug: see B1.

## 4. Additional checks (successful unless stated)

| Check | Observed | Evidence |
|---|---|---|
| Staff code at Owner prompt | Did **not** grant Owner; fell back to Staff (no message: U2) | X03 |
| Staff cannot confirm notes, completeness or decisions | No Confirm on notes; Completeness shows "The owner confirms completeness." with no form; case shows "Waiting for the owner's decision. Nothing to do yet." | snapshots 04:36:29, 04:37:51; E07/E08 |
| Console gate | A Staff-only session and an Owner session both get "Enter the demo console code" at `#/console` | X23 |
| Operator separation | The Operator cannot open `#/records` or `#/case/…` (asked for the Staff code). The Operator header has no Records link. | X25 |
| Missing information | For "…a bit later?" the agent asked for the customer **and** the payment date in one form | X26 |
| Past requested date | Server rejected 2026-10-12 with HTTP 422 and the message "Enter a date after Fri 16 Oct 2026 (the as-of date)." The selection was kept. (The date picker also has `min=2026-10-17`; automation bypassed it.) | X26, console L7 |
| Extension with a staff-supplied date | 10 Oct → 20 Nov = **41 days**: correct | X26 |
| No access code in any saved file | Searched all evidence and the automation output folder for the three codes: 0 matches | packaging check |

## 5. Findings summary

| ID | Category | Severity | One-line summary |
|---|---|---|---|
| B1 | Application bug — authentication | **High** | Sign out ends only the selected role's session. After Staff + Owner, signing out from Staff lands in Owner mode. |
| B2 | Permission / attribution question (policy unconfirmed) | Medium if Owner-only is intended, otherwise Low | Staff can save opening balances. No "entered by" is shown. |
| B3 | Unverified risk — revert safeguards | Medium (unverified) | The Revert form for a batch with dependants shows no dependency warning before submit. Server behaviour on submit is untested. |
| B4 | Application bug — import history | Low | Closed (unapplied) previews remain in Import history as "preview · Open". |
| B5 | Application bug — audit text | Low | Activity log mislabels the clarification and shows a raw invoice id. A later records change is not logged. |
| B6 | Application/agent bug — labelling | Low | The only request in a message was labelled "(another request)". |
| B7 | Application bug — client JS | Low | TypeError in renderConsole while navigating away from the console as Operator. |
| B8 | Application bug — copy | Low | "2 cases need you. Choose it from the list." |
| B9 | Information disclosure (operator-only) | Low | The console shows the backup folder path, including the server account's username. |
| U1 | Usability | Medium | Invoice and payment customer pickers default to the first sample customer, and the invoice picker resets to it after every save. |
| U2 | Usability | Low | A wrong-role code at a role prompt silently switches role, with no message. |
| U3 | Usability | Low | Copy reply gives no visible confirmation. |
| U4 | Usability | Low | The customer reply uses an ISO date (2026-11-14). |
| U5 | Usability / clarity | Low | Decision and confirmation stamps use the real clock (18 Oct) while "today" is fixed at 16 Oct. |
| U6 | Clarity / possible logic question | Low | Invoices with no allocation show "Not recorded", while allocated ones show "At most …". |
| U7 | Clarity | Low | After the late entry, "Why not exact" doesn't name the cause and says "from Wed 30 Sep". The completeness note says "changed" for an added entry. |
| U8 | Clarity | Low | The case brief says "Records for this customer are not confirmed complete" right after saying payment records are complete. |
| U9 | Usability (narrow screen) | Low | The Still owed column and summary lines are cut off, with no scroll cue. |
| U10 | Usability | Low | Generic "Enter an answer." validation message. |
| U11 | Usability | Low | An Operator who leaves the console cannot sign out from the page they land on. |
| U12 | Usability / accessibility | Low | Staff see a Demo console link, and its accessible name is "Demo c onsole". |
| G1 | Guide mismatch | Low | The guide refers to an import "completeness choice" that doesn't exist. |
| G2 | Guide mismatch + usability | Medium | The guide asks for amounts and dates to be checked in the preview, but the preview doesn't show them. |
| G3 | Guide mismatch | Low | "Leave the as-of date blank", but it is pre-filled with 2026-10-16. |
| G4 | Guide mismatch | Low | The guide mentions a mobile "back arrow"; the app shows an "All cases" link. |
| G5 | Guide ambiguity | Low | T5 does opening balances as Owner, but neither the guide nor the app says whether Staff may. |

## 6. Findings in detail

### B1 — Sign out ends only the currently selected role; can leave the browser in Owner mode
- **Category / severity:** application bug, authentication. High.
- **Role:** Staff (Owner unlocked earlier in the same browser). Mirror case: Owner (Staff also unlocked).
- **Starting conditions:** signed out; Staff and Owner codes available. Observed in a 390×844 window. Desktop width and other browsers were not tried.
- **Steps:**
  1. Open https://nucleon.dracooz.top and sign in with the Staff code.
  2. Click **Owner** and enter the Owner code → Owner mode.
  3. Click **Staff**.
  4. Click **Sign out**.
- **Expected:** the sign-in screen, with every Nucleon role session ended.
- **Actual (observed):**
  - Network after the click: `POST /api/demo/logout`, then `GET /api/session` ×2 and `GET /api/requests`.
  - Cookie names before → after: `nucleon_staff,nucleon_owner` → `nucleon_owner`.
  - `localStorage["nucleon.role"]` became `owner`.
  - No sign-in screen. Owner button pressed, "Needs your decision" shown.
  - `#/records` and `#/case/req_35c17a88570d5955` opened without a prompt.
  - A second Sign out (only the owner cookie present) did reach the sign-in screen and cleared all cookies.
  - **Mirror:** with both unlocked and Owner selected, Sign out left `nucleon_staff` and Staff mode.
- **Suspected cause (unverified):** the logout endpoint clears only the session of the active role. The client then reads `/api/session`, finds the remaining role and switches to it. Request bodies were not captured, so whether the client sends the role or the server picks it is unknown.
- **Impact:** on a shared or unattended browser, the next person gets Owner powers without the Owner code. Those powers include approving extensions and confirming completeness. In the mirror case, an Owner who thinks they signed out leaves a Staff session behind.
- **Reproduction confidence:** high. Staff→Owner observed 2/2 (04:47:40 and ≈04:48:20 UTC, the second from a clean signed-out state). Mirror observed 1/1 (≈04:49:40 UTC).
- **Evidence:** E15, E16 (byte-identical captures 17 s apart), X21, X22, X24.

### B2 — Staff can save opening balances; the record does not show who entered it
- **Category / severity:** permission or attribution question. The intended policy is **not known**. Medium if opening balances are meant to be Owner-only; otherwise Low (attribution only).
- **Role:** Staff.
- **Starting conditions:** a customer without an opening balance (C-0005).
- **Steps:**
  1. Records → Customers and invoices → CL1018T Manual B fictional → **Add an opening balance**.
  2. As at 2026-09-30; Amount 0.00; leave "Owed by the customer" and credits "Not stated".
  3. Set "Where this figure comes from" to any text.
  4. Click **Save opening balance**.
- **Expected:** not defined. Guide T5 performs this step after "Switch to Owner", but neither the guide nor the UI says Staff may not. Either outcome may be intended:
  - (a) Owner-only, so Staff would be refused; or
  - (b) Staff allowed, in which case the owner may need to see who entered it.
- **Actual (observed):**
  - "Opening balance saved". Header: "Opening balance AUD 0.00 owed as at Wed 30 Sep · CL1018T staff permission probe (fictional) · credits in it not stated". No "entered by" text appears.
  - The case brief for req_366ba0f4763c2935 cites this opening balance by its source text only. In req_35c17a88570d5955 (Owner-entered opening balance) the brief says "A person said the opening balance includes no credits or prepayments."
  - Staff also see **Correct** and **Remove** on existing opening balances, including another tester's (Release check café). These were not used.
- **Not tested:** Staff Correct/Remove on opening balances; whether a Staff-entered opening balance with "It includes none" plus Owner completeness produces an "exact" amount.
- **Impact:** opening balances and their credits statement feed "exact" amounts. If Staff entry isn't intended, or isn't visible to the Owner, the Owner may rely on a figure without knowing who entered it.
- **Reproduction confidence:** observed once. The save is a deterministic UI action, so high confidence it repeats.
- **Evidence:** X12, X19, X26, X14; E12 (Manual B header). No dedicated screenshot.

### B3 — Revert form on a batch with dependants shows no dependency warning before submit (server guard untested)
- **Category / severity:** unverified risk. Medium if no guard exists, otherwise Low.
- **Role:** Staff. Owner not tried.
- **Starting conditions:** the 01-invoices.csv "New 2" batch is applied, and other records depend on it:
  - 02 payment CL1018T-PAY-001 allocated to Imported A's CL1018T-CSV-001
  - the opening balance on C-0006
  - the completeness statement for C-0006 (already voided)
  - approved case req_35c17a88570d5955
- **Steps:**
  1. Records → Import history → row "01-invoices.csv · CL1018T Invoice test · New 2 · applied".
  2. Click that row's **Revert**.
  3. Read the form. **Do not submit.**
- **Expected (guide T6c):** "A disabled or blocked revert must explain its dependency", and "If an impact review appears, read it before confirming."
- **Actual (observed):**
  - The row button was enabled, with no tooltip.
  - The inline form showed only "Why revert this import?", "Nothing is deleted: records from this import are marked reverted, and values it replaced get their earlier version back." and a Revert button. No dependants were mentioned.
  - The form was closed without submitting.
  - The zero-row repeat batch ("Already recorded 2 · applied") also has an enabled Revert.
  - For the 04 batch (no dependants), submitting reverted immediately with no impact review.
- **What this does NOT show:** whether the server refuses, warns, or shows an impact review **after** submit. Because the form was not submitted, there is no evidence that a server-side guard is missing.
- **Suspected cause:** none asserted. Possibly the dependency check exists only at submit time.
- **Impact (conditional):** if there is no guard, reverting 01 could orphan the allocation and alter exact amounts and case evidence. If there is a guard, the only issue is that the warning comes late. It's also unclear what reverting a zero-row batch does.
- **How to confirm:** on a disposable database, submit Revert on a batch with dependants and on a zero-row batch, and check the server-side dependency handling.
- **Reproduction confidence:** UI state high (deterministic; observed once). Server behaviour unknown.
- **Evidence:** X18, X17, X07, E12.

### B4 — Closed previews stay in Import history as "preview · Open"
- **Category / severity:** application bug, import history. Low.
- **Role:** Staff.
- **Steps:**
  1. Import a CSV → choose a file and a source label → **Preview** → **Close** (no Apply).
  2. Do another import and Apply it.
  3. Look at Import history.
- **Expected:** the guide says "An unwanted preview can be closed; no records change until Apply". The tester expected a closed preview to be discarded, or shown as closed.
- **Actual (observed):**
  - Records did not change (CL1018T-VALID-PREVIEW was absent).
  - Right after Close, history did not list the preview (X08).
  - After the next applied import it listed "03-invalid-preview-only.csv · CL1018T Invalid preview · New 1, Rejected 2 · **preview** · **Open**" (X09).
  - The closed repeat-payment preview ("02-payments.csv · Already recorded 2 · preview · Open") appeared the same way (X17, E12).
  - **Open** was not clicked, so whether a reopened preview can still be applied is untested.
- **Suspected cause:** Close only hides the panel and the server keeps the preview batch. The history list isn't refreshed on Close.
- **Impact:** clutter. Someone could later reopen and apply a file the tester chose not to apply (unverified).
- **Reproduction confidence:** observed for 2 of 2 closed previews.
- **Evidence:** X08, X09, X10, X17, E12.

### B5 — Activity log mislabels the clarification, shows a raw id, and omits the later records change
- **Category / severity:** application bug, audit text. Low.
- **Role:** Staff (viewer). The case was created by Staff and decided by Owner.
- **Starting conditions:** a case where the agent asked which customer (here req_35c17a88570d5955), approved, then affected by a later records change.
- **Steps:** open the case → expand **Activity**.
- **Expected:** the question as asked ("which customer"), the answer in readable form (customer name/number or invoice number), and an entry for the post-decision records change shown in the banner.
- **Actual (observed):**
  - "Asked staff for the invoice number"; the question actually asked was "Which customer's invoice is it?".
  - "Staff answered: invoice_7058633933bfb4a7".
  - No entry for the records change.
- **Reproduction confidence:** observed in the one case inspected. The T2 case's Activity was not inspected.
- **Evidence:** X27; X14 (the question actually asked).

### B6 — The single request in a message was labelled "(another request)"
- **Category / severity:** application/agent bug, labelling. Low.
- **Role:** Staff.
- **Steps:**
  1. New request: "Test CL1018T. Could we pay invoice CL1018T-001 a bit later?" (two customers have CL1018T-001).
  2. Choose Manual B and the date 2026-11-20 → open the prepared case.
- **Expected:** "(the request)" and "Underlined: the request…", as in the other cases.
- **Actual (observed):** "(another request)" and "Underlined: another request, as picked out by the agent."
- **Suspected cause:** the label depends on the model's classification of the highlighted span. This message had no date.
- **Reproduction confidence:** observed once. Agent output may not be deterministic.
- **Evidence:** X26.

### B7 — TypeError in renderConsole when navigating away from the console
- **Category / severity:** application bug, client JavaScript. Low.
- **Role:** Operator.
- **Steps:**
  1. Sign in with the Operator code (lands on `#/console`).
  2. Navigate by URL to `#/records`, then `#/case/req_35c17a88570d5955`, then `#/` within a few seconds.
- **Expected:** no console errors.
- **Actual (observed):** at 04:50:11.7 and 04:50:19.7 UTC: `TypeError: Cannot set properties of null (setting 'innerHTML') at renderConsole (https://nucleon.dracooz.top/static/app.js:783:27) at loadConsole (…/static/app.js:769:3)`. The exact triggering navigation was not isolated.
- **Suspected cause:** `loadConsole` renders after an async load, when the console container is no longer in the DOM.
- **Impact:** probably cosmetic. Not investigated further.
- **Reproduction confidence:** observed twice in one sequence.
- **Evidence:** console L1–6, X25.

### B8 — "2 cases need you. Choose it from the list."
- **Category / severity:** copy bug. Low.
- **Role:** Owner.
- **Steps:** as Owner, with two or more cases waiting for the owner, open Home (`#/`) without selecting a case.
- **Expected:** plural wording, e.g. "Choose one from the list." (Staff with one case: "One case needs you. Choose it from the list.", which is fine.)
- **Actual (observed):** "2 cases need you. Choose it from the list."
- **Reproduction confidence:** observed twice (X20, X23).
- **Evidence:** X20, X23.

### B9 — Demo console reveals the server's backup path, including an account username
- **Category / severity:** information disclosure, visible only with the Operator code. Low.
- **Role:** Operator.
- **Steps:** sign in with the Operator code → Demo console → Backups section footer.
- **Expected:** no server filesystem paths or account names in the UI.
- **Actual (observed):** "Backups are kept in /Users/[REDACTED-USERNAME]/srv/nucleon/backups." The real text includes the server account's home-folder name.
- **Impact:** small. It discloses the host account name and directory layout to anyone with the operator code.
- **Reproduction confidence:** observed once (static text).
- **Evidence:** X25 (redacted). No screenshot.

### U1 — Customer pickers default to the first sample customer; the invoice picker resets after every save
- **Category / severity:** usability. Medium (risk of entering data against the wrong customer).
- **Role:** Staff.
- **Steps:**
  1. Records → **Add an invoice**: note the Customer default.
  2. Select another customer, fill in valid values, click Add invoice.
  3. Look at the picker again. Then check the **Record a payment or credit** Customer default.
- **Expected:** no pre-selected customer (as the notes "About" picker does with "Choose…"), or the last-used customer kept. This is the tester's expectation; the guide only warns that "Existing sample customers may be selected by default."
- **Actual (observed):**
  - Both pickers default to "Harbour Demo Supplies (C-DEMO-01)" (internal value `customer_demo_01`).
  - After each of 2 invoice saves, the invoice picker returned to Harbour Demo Supplies.
  - The payment picker also showed Harbour on later page states.
  - Not verified: that the payment picker specifically resets after "Record it". The page was re-rendered or reloaded in between.
- **Reproduction confidence:** invoice picker reset 2/2. Payment default observed.
- **Evidence:** snapshots 04:35:41 and 04:36:00; X01; E01, E05, E07, E12.

### U2 — A wrong-role code at a role prompt silently switches role
- **Category / severity:** usability. Low. No privilege escalation was observed.
- **Steps:**
  - (a) From Staff, click Owner and type the **Staff** code.
  - (b) From a Staff-only session, open `#/console` and type the **Owner** code.
- **Expected:** a message saying the code belongs to another role (tester suggestion).
- **Actual (observed):** (a) back in Staff with no message. (b) signed in as Owner and redirected to Home; no console.
- **Reproduction confidence:** each observed once.
- **Evidence:** X03, X23; snapshots 04:36:34 and 04:36:41.

### U3 — Copy reply gives no visible confirmation
- **Category / severity:** usability. Low.
- **Role:** Staff. **Steps:** on an approved case, click **Copy reply**.
- **Expected:** brief "Copied" feedback.
- **Actual (observed):** the button text stays "Copy reply" and no message appears. The clipboard did contain the reply text.
- **Reproduction confidence:** observed once.
- **Evidence:** X04, snapshot 04:38:38, E02.

### U4 — Customer-facing reply uses an ISO date
- **Category / severity:** usability. Low.
- **Actual (observed):** "…The new payment date is 2026-11-14." The rest of the UI says "Sat 14 Nov 2026".
- **Reproduction confidence:** observed in both decided cases.
- **Evidence:** X04, X14, E02, E06, E14.

### U5 — Real-clock timestamps alongside a fixed "today"
- **Category / severity:** clarity. Low.
- **Actual (observed):** "Decided 18 Oct, 3:38 pm", "confirmed by the owner 18 Oct, 3:42 pm" and case-list times of 18 Oct, while the app says "Today is fixed at Fri 16 Oct 2026". Decisions therefore appear dated after "today".
- **Expected:** a short note that stamps use real time, or consistent display (tester suggestion).
- **Evidence:** E02, E06, X13, X14.

### U6 — "Not recorded" for unallocated invoices vs "At most …" for allocated ones
- **Category / severity:** clarity or possible logic question. Low. May be intended.
- **Actual (observed):**
  - Invoices with no allocation and no stated amount show **Not recorded**: Manual A 1,000.00, and Imported B 200.00 even though B has an unallocated 50.00 payment.
  - An invoice with an allocation shows **At most AUD 400.00**.
- **Question:** the invoice total is also an upper bound, so should it show "At most AUD 1,000.00"? Guide T1 says "An invoice total alone does not establish the remaining debt", which is consistent with "Not recorded". The developer should confirm which is intended.
- **Evidence:** X02, X09, E05.

### U7 — After the late entry, the explanation wording is incomplete or inaccurate in two places
- **Category / severity:** clarity. Low. Narrowed from the chat report; see §9.
- **Actual (observed):**
  - The invoice's **Why not exact** says only "Payment records for this customer have no confirmed completeness from Wed 30 Sep 2026." It doesn't mention CL1018T-LATE-ENTRY. "From Wed 30 Sep" also differs from the Thu 1 Oct start that had made the amount exact (opening balance as at 30 Sep).
  - The **Completeness** note says "CL1018T-LATE-ENTRY **changed** inside the period afterwards", but the entry was added.
  - The Records **Needs attention** section (E12) does explain it correctly: "…because CL1018T-LATE-ENTRY was **added** inside its period afterwards."
- **Evidence:** X15, E07, E08, E12.

### U8 — Case brief seems to contradict itself about completeness
- **Category / severity:** clarity. Low.
- **Actual (observed):** "Payment records for this customer are confirmed complete from Thu 1 Oct 2026 to Fri 16 Oct 2026…", followed by "Records for this customer are not confirmed complete, so this balance only reflects what is recorded." The second sentence presumably means the invoice records.
- **Evidence:** X14, E06, E11.

### U9 — Narrow screen: key column and summary lines clipped with no scroll cue
- **Category / severity:** usability. Low. Inner table scrolling is allowed by the guide.
- **Steps:** a 390-px-wide window → Records → Customers and invoices.
- **Actual (observed):** the Still owed column (e.g. "At most AUD 400.00") and customer summary lines are cut at the right edge mid-word. The table scrolls inside its container (scrollWidth 528 vs 327 visible), but nothing indicates this.
- **Evidence:** E13, E12, X20.

### U10 — Generic "Enter an answer." validation
- **Category / severity:** usability. Low.
- **Actual (observed):** sending a clarification with no customer selected (T2), or with no date (extra check), shows "Enter an answer." In the date case the message is placed under the date field.
- **Expected:** a specific prompt such as "Choose a customer" or "Enter the payment date" (tester suggestion).
- **Evidence:** snapshot 04:37:33, X26.

### U11 — An Operator who leaves the console cannot sign out from the landing page
- **Category / severity:** usability. Low.
- **Steps:** sign in with the Operator code → navigate to `#/records` (or `#/`).
- **Actual (observed):** the "Sign in as staff" screen has no Sign out button, and the `nucleon_operator` cookie remains. Signing out required going back to `#/console`.
- **Evidence:** X25.

### U12 — Staff see a Demo console link; its accessible name is "Demo c onsole"
- **Category / severity:** usability / accessibility. Low.
- **Actual (observed):**
  - The Staff top bar shows "Demo console" (visible text, E01). The accessibility tree names the link **"Demo c onsole"** (snapshots 04:34:31 onward).
  - On narrow screens it is "Console".
  - The console itself is correctly gated (X23).
- **Suspected cause:** unknown, possibly markup splitting the word. Impact on screen readers is inferred, not tested with a screen reader.
- **Evidence:** snapshot 04:34:31, E01, X23.

### G1 — Guide refers to an import "completeness choice" that does not exist
- **Category / severity:** guide mismatch. Low.
- **Guide text:** T3 step 4 says "Leave the optional completeness choice at Not sure, or not saying." T4 step 1 says "Leave completeness unset."
- **Actual (observed):** the import preview has no such control. The word "complete" does not appear anywhere in the import section.
- **Evidence:** X05, E03, E04.

### G2 — Guide asks for amounts and dates to be checked in the preview, but the preview omits them
- **Category / severity:** guide mismatch and usability. Medium (removes a check before Apply).
- **Guide text:**
  - T3 step 4: "Check the two rows: Imported A has 1000.00, Imported B has 200.00 … dated 5 October and due 10 October".
  - T3b: "one valid row for 250.00".
  - T4 step 2: "Check the two rows before Apply".
- **Actual (observed):**
  - The preview tables show only Row / Customer / Invoice (or Reference) / Result.
  - For payments, an allocated row adds "Allocate AUD 600.00 to …". Unallocated rows show no amount or date.
  - Amounts and dates could only be checked after Apply.
- **Evidence:** X05, E03, E04, X09.

### G3 — "Leave … its as-of date blank", but the as-of date is pre-filled
- **Category / severity:** guide mismatch. Low.
- **Guide text:** T1 step 2.
- **Actual (observed):**
  - "…still owed as of" is pre-filled with 2026-10-16 and re-filled after each save. The tester cleared it manually in T1.
  - In the T6b correction form it stayed pre-filled. Saving with no amount owed changed nothing ("Not recorded" remained).
- **Evidence:** X01, X17, snapshot 04:34:40.

### G4 — Guide mentions a mobile "back arrow"; the app shows an "All cases" link
- **Category / severity:** guide mismatch. Low.
- **Guide text:** "A mobile back arrow may return to the case list."
- **Actual (observed):** an "All cases" text link at the top of the case.
- **Evidence:** E10, E14, X20.

### G5 — T5 assigns opening balances to Owner without saying whether Staff may enter them
- **Category / severity:** guide ambiguity. Low. Linked to B2.
- **Guide text:** T5 step 1 "Switch to Owner … click Add an opening balance".
- **Actual (observed):** Staff have the same button and can save (B2). The guide and the app should state the intended rule once it is decided.
- **Evidence:** X12, X19.

## 7. Other observations (not filed as findings)

1. **Preparing timer.** The "Preparing the case" step timer showed "5 s" in an inline snapshot taken about 12 s after the answer was sent. It may be a per-step timer. Not investigated.
2. **Overdue "Unknown" with a known due date.** Manual B's case (due Sat 10 Oct) shows "Overdue today: Unknown" with the explanation "Days overdue aren't calculated: no amount still owed is recorded." This looks intentional.
3. **Technical details panel.** It is visible to Staff and Owner and shows model and gateway details: "Gemma 4 26B-A4B (local GGUF, LM Studio via home gateway), model gemma-4-26b-a4b-it-heretic-zh-rp…". The run list is not in time order (a 3:42:46 run is listed before a 3:42:38 model call). Whether this panel should show these details is for the developer to decide.
4. **Browser language.** The browser was zh-CN, so native date and file controls appeared in Chinese. Dates were entered as ISO by automation, so this did not affect the tests.
5. **Starting state of the instance.** At the start, no other tester's tagged data existed. There was "Release check café (fictional)" with an approved RC-1 case at 18 Oct 2:33 pm AEDT, and the console listed backups from 1:16 am to 2:45 pm on 18 Oct. This suggests the instance was reset or restored earlier that day (inference).
6. **Off-screen elements.** On the narrow Home page, some case-list elements measured beyond the right edge (x 192–479), but nothing was visible off-screen (E09). Probably a hidden panel; not verified.

## 8. Limitations and not tested
- No real phone, no browser other than Chromium 155, no screen reader.
- B3 server behaviour: reverting a batch with dependants, and reverting a zero-row batch.
- Opening "Open" on a closed preview (B4).
- Staff Correct/Remove on opening balances, invoices and customers; the "Allocate" and "Not for an open invoice" actions; credits ("A credit held for the customer").
- Whether a correction reason is mandatory; whether an empty clarification answer fails server-side as well as client-side.
- Owner outcomes "Approve a different date" and "Decline".
- T8 (fresh database); concurrency with other testers.
- Network request/response bodies (not captured); server logs (not accessible).
- Console messages before 04:46:28 UTC.
- The application revision.

## 9. Corrections to the in-session chat report
1. **T6b:** the chat report said "the reason was required in the form". That was **not tested** and is withdrawn.
2. **U1:** the chat report said both pickers reset "after every save". Reset is verified only for **Add an invoice**; for payments only the default was observed.
3. **U7:** the chat report said the cause of the lost exact amount was not named. The full-page capture E12 shows a **Needs attention** section that names it correctly ("added"). U7 now covers only the "Why not exact" and Completeness wording.
4. **B2:** re-stated without assuming that Staff entry violates the intended policy.
5. **B3:** re-stated to make explicit that the unsubmitted form proves nothing about a server-side guard.
6. **During the session** the tester first said the clarification date picker had no minimum. It has `min="2026-10-17"`; automation bypassed it and the server rejected the past date. The chat report's final wording was already correct.
7. **Environment details** (desktop viewport, browser build, locale, timing caveats) were added from the evidence during packaging.
