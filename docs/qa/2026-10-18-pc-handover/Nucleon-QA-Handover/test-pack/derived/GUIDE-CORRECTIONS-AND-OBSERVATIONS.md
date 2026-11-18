# Guide corrections and observations (tester-authored, NOT part of the original guide)

The original guide is `../original/Nucleon-Team-Test-Pack/Nucleon-Team-Testing-Guide.docx` (unchanged).
This file lists where the running app differed from what the guide says. Each entry gives the guide text,
what was observed on 2026-10-18 (tag CL1018T), and a **suggested** change. Suggestions are the tester's
opinion. Whether to change the app or the guide is the developer's decision.

| Guide location | Guide says (quoted) | Observed | Suggested change | Finding |
|---|---|---|---|---|
| Sign in and navigate | "A mobile back arrow may return to the case list." | An "All cases" link at the top of the case | "On narrow screens, use **All cases** at the top of a case to return to the list." | G4 |
| Sign in and navigate | "Clicking Owner asks for its code the first time." | True. Entering the Staff code there silently returns to Staff | Add: "If you enter the wrong role's code you are returned to that role without a message." | U2 |
| T1 step 2 | "Leave Amount still owed and its as-of date blank." | The as-of date is pre-filled with 2026-10-16 and re-filled after each save | "Leave Amount still owed blank and clear the pre-filled as-of date" (or make the field empty by default) | G3 |
| T1 step 2 | "Existing sample customers may be selected by default." | Accurate. The picker also returns to Harbour Demo Supplies after every Add invoice | "…and the picker resets to the first sample customer after every save — reselect each time." | U1 |
| T3 step 4 | "Leave the optional completeness choice at Not sure, or not saying." | No completeness control exists in the import preview | Remove the sentence, or restore the control | G1 |
| T3 step 4 | "Check the two rows: Imported A has 1000.00, Imported B has 200.00 … dated 5 October and due 10 October. Click Apply 2 rows." | The preview shows only Row / Customer / Invoice / Result | Either show amounts and dates in the preview, or say "After Apply, check in Customers and invoices that …" | G2 |
| T3 step 5 | "It should show Already recorded, with zero new rows. If Apply 0 rows is offered, you may use it" | Accurate. Using it adds a zero-row batch to Import history, with its own Revert button | Mention that the zero-row batch appears in history | B3 (context) |
| T3b | "Expect … one valid row for 250.00 … click Close." | Rows and reasons accurate, but the 250.00 amount is not shown. After Close the preview later appears in Import history as "preview · Open" | Note that closed previews remain listed | G2, B4 |
| If an import will not proceed | "An unwanted preview can be closed; no records change until Apply." | No records changed, but the closed preview stays in history and can be reopened | As above | B4 |
| T4 step 1 | "Leave completeness unset" | No such control | Remove | G1 |
| T4 step 2 | "Check the two rows before Apply 2 rows: … 600.00 on 12 October … 50.00 with a blank invoice reference" | The preview shows "Allocate AUD 600.00 to …" for A only. B's amount and both dates are not shown | As G2 | G2 |
| T5 step 1 | "Switch to Owner. … click Add an opening balance" | Staff have the same button and can save | State whether Staff may enter opening balances | G5, B2 |
| T5 step 3 | "Check A's invoice is exactly AUD 400.00 as of 16 October." | Accurate | — | — |
| T6a check | "A's exact claim should disappear and its completeness statement should show why it no longer holds." | Accurate. The note says the entry "changed" (it was added); "Why not exact" doesn't name the entry; the Needs attention section explains it correctly | Optional: point testers to the Needs attention section | U7 |
| T6b check | "The row shows 220.00, a correction source and a higher version." | Accurate ("Corrected by staff · version 2") | — | — |
| T6c check | "A disabled or blocked revert must explain its dependency." | The 01 batch's Revert form shows no dependency information before submit (not submitted; server behaviour unknown) | Clarify whether the warning appears only after submit | B3 |
| T7 | "If using only a narrow desktop browser, say so." | The tester used a 390×844 desktop window, not a phone | — | — |
| T7 / general | (not covered) | Sign out from one role can leave the other role signed in | Add: "Sign out, then confirm the sign-in screen appears; repeat if it does not." | B1 |
| Feedback form | "Copy reply" (T2 step 4) | Works, but gives no visual confirmation | — | U3 |
