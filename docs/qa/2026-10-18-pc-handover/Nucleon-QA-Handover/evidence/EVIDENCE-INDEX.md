# Evidence index

All evidence comes from the single test session on **2026-10-18, 04:34–≈04:52 UTC (15:34–≈15:52 AEDT)**,
unless it is marked as a packaging-time capture. Nothing in this folder was re-captured after testing
except where explicitly labelled. Paths are relative to this `evidence/` folder.

Time conventions: UTC is authoritative. The app displays Sydney time (AEDT, UTC+11). Screenshot times are
the original file modification times. Automation-snapshot times come from the file names, which the
browser-automation tool assigns. Those names can lag or lead the page state by a few seconds (see the note
under *Automation snapshots*).

## Screenshots (`screenshots/`)

All were captured with Playwright `page.screenshot` in a headed Chromium 155 window. Device pixel ratio was 1
during testing (the 390-px-wide window produced 390-px-wide images). Desktop images are therefore
3840×1958 CSS px. None show the browser address bar, the access codes or any cookie.

| ID | File | Original session file name | Captured (UTC / AEDT) | Pixels | Shows | Used for |
|---|---|---|---|---|---|---|
| E01 | [E01-T1-records-manual-A-B-invoices-desktop.png](screenshots/E01-T1-records-manual-A-B-invoices-desktop.png) | T1-manual-invoices.png | 04:36:15 / 15:36:15 | 3840×1958 | Records (Staff): Manual A C-0004 and Manual B C-0005, each with CL1018T-001; A due "Not on record"; Add an invoice picker back on Harbour Demo Supplies | T1, U1, U12 (visible text "Demo console") |
| E02 | [E02-T2-case-req_fcde410d-approved-staff-view-desktop.png](screenshots/E02-T2-case-req_fcde410d-approved-staff-view-desktop.png) | T2-case-approved-staff.png | 04:38:46 / 15:38:46 | 3840×1958 | Case req_fcde410df1eff472 (Staff): Approved to Sat 14 Nov; reply with ISO date; Copy reply; "Decided 18 Oct, 3:38 pm" | T2, U3, U4, U5 |
| E03 | [E03-T3-invoice-import-preview-before-apply.png](screenshots/E03-T3-invoice-import-preview-before-apply.png) | T3-preview-before-apply.png | 04:39:33 / 15:39:33 | 1250×1185 (element) | 01-invoices.csv preview: mappings, "Create a new customer" ×2, New: 2, table Row/Customer/Invoice/Result only, Apply 2 rows | T3, G1, G2 |
| E04 | [E04-T3b-invalid-file-preview-closed-not-applied.png](screenshots/E04-T3b-invalid-file-preview-closed-not-applied.png) | T3b-invalid-preview.png | 04:40:24 / 15:40:24 | 1250×1107 (element) | 03 preview: 2 rejected with reasons, 1 New; Apply 1 row enabled (Close was clicked next) | T3b, G2 |
| E05 | [E05-T4-records-after-payment-import-staff-desktop.png](screenshots/E05-T4-records-after-payment-import-staff-desktop.png) | T4-after-payments.png | 04:41:28 / 15:41:28 | 3840×1958 | Records (Staff) after payments: A "At most AUD 400.00" + Why not exact; B "Not recorded"; Add an invoice picker on Harbour | T4, U1, U6 |
| E06 | [E06-T5-case-req_35c17a88-approved-owner-view-desktop.png](screenshots/E06-T5-case-req_35c17a88-approved-owner-view-desktop.png) | T5-case-approved-owner.png | 04:43:23 / 15:43:23 | 3840×1958 | Case req_35c17a88570d5955 (Owner) just approved: AUD 400.00 exact, 35 days, 6 days overdue, brief text | T5, U4, U5, U8 |
| E07 | [E07-T6a-records-after-late-entry-why-not-exact.png](screenshots/E07-T6a-records-after-late-entry-why-not-exact.png) | T6a-records-after-late-entry.png | 04:43:56 / 15:43:56 | 3840×1958 | Records (Staff) after CL1018T-LATE-ENTRY: A back to "At most AUD 400.00", Why not exact text, balance 390.00 | T6a, U7, U1 |
| E08 | [E08-T6a-completeness-statement-no-longer-holds.png](screenshots/E08-T6a-completeness-statement-no-longer-holds.png) | T6a-completeness-no-longer-holds.png | 04:43:56 / 15:43:56 | 3840×1958 | Completeness section: A statement "No longer holds … CL1018T-LATE-ENTRY changed inside the period afterwards." | T6a, U7 |
| E09 | [E09-T7-phone390-home-staff.png](screenshots/E09-T7-phone390-home-staff.png) | T7-phone-home.png | 04:46:30 / 15:46:30 | 390×844 | Home at 390-px window (Staff): wrapped top bar, case list | T7 |
| E10 | [E10-T7-phone390-case-req_35c17a88-top.png](screenshots/E10-T7-phone390-case-req_35c17a88-top.png) | T7-phone-case-top.png | 04:46:45 / 15:46:45 | 390×844 | T5 case on narrow screen: "All cases" link, evidence-change banner | T7, G4, T6a |
| E11 | [E11-T7-phone390-case-req_35c17a88-fullpage.png](screenshots/E11-T7-phone390-case-req_35c17a88-fullpage.png) | T7-phone-case-full.png | 04:46:45 / 15:46:45 | 375×2326 (full page) | Same case, whole page | T7, U8, T6a |
| E12 | [E12-T7-phone390-records-fullpage.png](screenshots/E12-T7-phone390-records-fullpage.png) | T7-phone-records-full.png | 04:47:00 / 15:47:00 | 375×10922 (full page) | Whole Records page (Staff): **Needs attention** section, "1 removed or reverted invoice is kept in the history…", Import history incl. two `preview · Open` rows and Revert buttons, Manual B staff-entered opening balance, both pickers on Harbour | T6c, B3, B4, B2, U1, U7, U9 |
| E13 | [E13-T7-phone390-records-invoice-table-clipped.png](screenshots/E13-T7-phone390-records-invoice-table-clipped.png) | T7-phone-records-invoices.png | 04:47:07 / 15:47:07 | 390×844 | Invoice table on narrow screen: Still owed column and summary lines cut at right edge | U9 |
| E14 | [E14-T7-phone390-owner-case-req_fcde410d.png](screenshots/E14-T7-phone390-owner-case-req_fcde410d.png) | T7-phone-owner-case.png | 04:47:27 / 15:47:27 | 390×844 | T2 case as Owner on narrow screen: "All cases" link, reply with ISO date | T7, G4, U4 |
| E15 | [E15-B1-after-staff-signout-lands-in-owner-mode.png](screenshots/E15-B1-after-staff-signout-lands-in-owner-mode.png) | T7-phone-signed-out.png | 04:47:40 / 15:47:40 | 390×844 | Immediately after clicking Sign out from **Staff**: Owner pressed, "Needs your decision" | B1 |
| E16 | [E16-B1-after-staff-signout-reloaded-still-owner.png](screenshots/E16-B1-after-staff-signout-reloaded-still-owner.png) | T7-after-signout-still-in.png | 04:47:57 / 15:47:57 | 390×844 | After reloading `#/` (17 s later): still Owner. **Byte-identical to E15** (same SHA-256) — two captures of the same rendered state | B1 |

### Derived (made during packaging, not original evidence)

| File | Made | Purpose |
|---|---|---|
| [derived/E12-contact-sheet-made-during-packaging.png](derived/E12-contact-sheet-made-during-packaging.png) | 2026-10-18 05:22:49 UTC, from E12 only | E12 cut into four columns so the 10,922-px-tall page can be read on one screen. No new capture. |

## Browser console log (`browser-console/`)

[browser-console/console-2026-10-18T04-46-28-860Z.log](browser-console/console-2026-10-18T04-46-28-860Z.log). The Playwright console
log starts when the tab navigated at 04:46:28.860 UTC (start of T7). The bracketed numbers are milliseconds
from that start. The third entry's computed time matches the file's modification time to the millisecond,
which confirms the reference point.

| Line(s) | Offset | Computed UTC | Message | Context | Finding |
|---|---|---|---|---|---|
| 1–3 | 222875 ms | 04:50:11.7 | `TypeError: Cannot set properties of null (setting 'innerHTML') at renderConsole (app.js:783:27) at loadConsole (app.js:769:3)` | Operator session; a script navigated from `#/console` to `#/records`, `#/case/req_35c17a88570d5955` and `#/` in about 5 s (X25) | B7 |
| 4–6 | 230871 ms | 04:50:19.7 | same TypeError | Same script / immediately after; exact triggering navigation **not isolated** | B7 |
| 7 | 291222 ms | 04:51:20.1 | `Failed to load resource: the server responded with a status of 422 () @ …/api/requests/req_366ba0f4763c2935/clarifications/clarify_3ed5da8f4a0e90fe/answers:0` | **Expected** validation: Staff deliberately answered a clarification with a past date (2026-10-12). The UI then said "Enter a date after Fri 16 Oct 2026 (the as-of date)." | Successful check (not a defect) |

No console messages were recorded before T7 because console capture to file began with the T7 navigation.
Errors before 04:46:28 UTC, if any, are **unknown**.

## Session output excerpts (`session-output-excerpts.md`)

[session-output-excerpts.md](session-output-excerpts.md) holds verbatim outputs of browser-automation
scripts (redacted). They are the primary evidence for findings without screenshots.

| Excerpt | Topic | Findings / tasks |
|---|---|---|
| X01 | Add-an-invoice field defaults (as-of 2026-10-16, first sample customer) | G3, U1 |
| X02 | T1 result rows | T1, U1 |
| X03 | Staff code typed at the Owner prompt | U2 |
| X04 | Copy reply clipboard contents | U3, U4, T2 |
| X05 | Import preview HTML; no completeness control | G1, G2 |
| X06–X07 | T3 apply and repeat import | T3, B3 (zero-row batch) |
| X08 | T3b after Close | T3b, B4 |
| X09–X10 | T4 apply, repeat, history | T4, U6, B4 |
| X11 | Why not exact (before T5) | T4 |
| X12 | Staff sees active opening-balance form | B2, G5 |
| X13–X14 | T5 opening balance, completeness, case, evidence, decision | T5, U8, U5 |
| X15–X16 | T6a late entry; T5 case flag | T6a, U7 |
| X17 | T6b correction, invoice ids, T6c import and revert | T6b, T6c, B4 |
| X18 | 01 batch Revert form opened, **not submitted** | B3 |
| X19 | Staff saves opening balance on Manual B | B2, G5 |
| X20 | Narrow-window measurements, navigation, "2 cases need you" | T7, U9, B8, G4 |
| X21–X22 | Sign out from Staff → Owner mode; clean reproduction; network calls | B1 |
| X23 | Console gate checks; Owner code at console prompt | U2, U12, B8 |
| X24 | Mirror: Sign out from Owner → Staff remains | B1 |
| X25 | Operator console (read-only), deep links, sign-out | B9, U11, B7 |
| X26 | Missing-date request, validation, 422, final case | B6, U10, extra check |
| X27 | Activity and Technical details of case req_35c17a88570d5955 | B5 |
| X28 | **Packaging-time** browser capture (05:23 UTC) — browser build only | Environment |

## Automation snapshots (`automation-snapshots/`)

These are accessibility-tree snapshots (YAML) that the Playwright MCP tool saved automatically after some
actions. Only this session's 44 files (`page-2026-10-18T*.yml`) are included. Older, unrelated files in the
same tool folder were left out. Times in the file names are UTC.

**Timing caveat:** the files for 04:37:24 and 04:37:51 already show the next state (clarification / prepared
case). Inline snapshots taken moments *after* those same waits still showed "The agent is preparing this
case". So treat these file times as approximate (± a few seconds), and do not use them to measure agent latency.
Pairs 04:37:24/04:37:26 and 04:37:51/04:37:53 are byte-identical.

| File time (UTC) | Role | State captured (from file content) | Related |
|---|---|---|---|
| 04:34:19.732 | — | Sign-in screen (password field, empty) | — |
| 04:34:31.302 | Staff | Home after Staff sign-in; link name "Demo c onsole" | U12 |
| 04:34:40.446 | Staff | Records initial: Today is Fri 16 Oct 2026, AUD; 3 customers; pickers default Harbour; as-of 2026-10-16 | Env, G3, U1 |
| 04:34:54.028 | Staff | After adding Manual A (C-0004) | T1 |
| 04:35:11.018 | Staff | After adding Manual B (C-0005) | T1 |
| 04:35:29.884 | Staff | Add an invoice picker set to Manual A | T1 |
| 04:35:41.248 | Staff | After Add invoice (Manual A): picker **back on Harbour Demo Supplies** | U1 |
| 04:35:54.497 | Staff | Picker set to Manual B | T1 |
| 04:36:00.104 | Staff | After Add invoice (Manual B): picker **back on Harbour** | U1 |
| 04:36:25.981 | Staff | Note "About" set to Manual A | T2 |
| 04:36:29.104 | Staff | Note saved: "draft by staff" | T2 |
| 04:36:34.444 | — | "Sign in as owner" prompt | U2 |
| 04:36:41.059 | Staff | After typing the Staff code at the Owner prompt: back in Staff, no message | U2 |
| 04:36:48.481 | — | Owner prompt again | — |
| 04:36:52.036 | Owner | Owner unlocked; notes show Confirm | T2 |
| 04:36:56.944 | Owner | CL1018T note "confirmed by the owner"; Harbour draft still draft | T2 |
| 04:37:07.287 | Staff | Back to Staff | — |
| 04:37:08.677 | Staff | Home | — |
| 04:37:13.550 | Staff | Case req_fcde410df1eff472 preparing ("2 s") | T2 |
| 04:37:24.591 | Staff | Clarification "Which customer's invoice is it?" (see timing caveat) | T2 |
| 04:37:26.766 | Staff | identical to 04:37:24 | T2 |
| 04:37:33.623 | Staff | "Enter an answer." after sending with nothing selected | U10 |
| 04:37:38.030 | Staff | Manual A selected | T2 |
| 04:37:39.373 | Staff | Preparing after answer ("2 s") | T2 |
| 04:37:51.552 | Staff | Prepared case: Waiting for the owner (see timing caveat) | T2 |
| 04:37:53.714 | Staff | identical to 04:37:51 | T2 |
| 04:38:02.217 | Owner | Ready for your decision | T2 |
| 04:38:07.305 | Owner | Evidence and sources expanded | T2 |
| 04:38:18.782 | Owner | Approve Sat 14 Nov chosen | T2 |
| 04:38:24.185 | Owner | Approved | T2, U5 |
| 04:38:32.810 | Staff | Staff view with Copy reply | T2 |
| 04:38:38.914 | Staff | After clicking Copy reply (button text unchanged) | U3 |
| 04:38:58.136 | Staff | Records | — |
| 04:39:08.022 | Staff | 01 preview: Unknown customer: 2, Apply 0 rows disabled | T3 |
| 04:39:15.496 / .817 | Staff | Customer decisions being set | T3 |
| 04:39:19.665 | Staff | New: 2, Apply 2 rows | T3, G1, G2 |
| 04:39:35.011 | Staff | Import applied | T3 |
| 04:40:00.418 | Staff | After Apply 0 rows on repeat import | T3 |
| 04:40:43.439 | Staff | After payment import applied | T4 |
| 04:41:47.932 | Owner | Records as Owner with opening-balance form open | T5 |
| 04:44:05.424 | Staff | Page shell while T5 case loads (no case content) | — |
| 04:45:20.257 | Staff | After 04 revert: history shows "reverted" | T6c |
| 04:46:28.871 | Staff | Narrow window, page shell (link name "Console") | T7 |

## Missing or never-captured evidence

| What | Status |
|---|---|
| Dedicated screenshots for B2 (partly visible in E12), B3, B5–B9, U2, U10, U11, U12 (accessible name) | Never captured. Text evidence only (excerpts and snapshots). B4 is visible in E12; U3 in E02 (taken after Copy reply was clicked); U6 in E05. |
| Screenshot of the Demo console (B9) | Never captured, on purpose (read-only visit). Text only, with the username redacted. |
| Screenshot of the 01 Revert form (B3) | Never captured. Text only (X18). |
| Network HAR, request/response bodies and headers | Not captured. Only method + path lists were recorded (X21, X22). |
| Cookie values, session tokens | Deliberately never read or stored. |
| Browser console messages before 04:46:28 UTC | Not captured to file. Unknown. |
| Server-side logs | Not available from this PC. |
| Application revision / build id | Not verified. The guide states "a9ce30d", but this was not confirmed against the running site. |
| Exact desktop viewport | Not logged. Inferred as 3840×1958 from screenshot sizes at device pixel ratio 1. |
| Internal ids for payments, notes, opening balances, completeness statements, import batches, customers | Not recorded. Only invoice ids, case ids and one clarification id are known. |
| Timestamps for individual script outputs | Not printed by the scripts. Approximate times are given in the excerpts. |
