# Team test pack, revision 3

For the redesigned interface on branch `feat/ux-redesign-20261018`. It replaces the 18 October revision 2 pack for that interface only. Since 18 October at 23:24 the shared practice site runs this interface (`f95f50f`), so revision 3 is the guide to use there; revision 2 belongs to the earlier interface.

| File | What it is |
| --- | --- |
| [Nucleon-Team-Test-Pack-v3.zip](Nucleon-Team-Test-Pack-v3.zip) | What testers receive: the guide, README.txt, one folder per tester (new tags `HL1018U`, `HN1018U`, `PD1018U`, `CC1018U`, `TT1018U`) and templates |
| [Nucleon-Team-Test-Pack-v3/](Nucleon-Team-Test-Pack-v3/) | The same files, unzipped |
| [GUIDE-v3.md](GUIDE-v3.md) | The guide's text, for review. Generated; the Word file is what testers use. |
| [DEVELOPER-SETUP.md](DEVELOPER-SETUP.md) | Local preview, isolated servers and checks. Kept out of the testers' guide. |
| [build/](build/) | `guide-content.js` (the one source of the guide), `build_guide.js` and `make_pack.py` |

**What changed from revision 2.** The guide follows the new navigation and its exact labels. It also:
- starts with sign-in, role switching and the one-step sign-out;
- checks import values in the preview;
- keeps import drafts, then discards them;
- separates the safe, blocked and review-required reverts;
- explains the certainty marks and the dates;
- states the open rule on opening balances;
- tightens the rules that protect other testers' records.

Every claim and on-screen text in it was checked against the running interface with the live model: `deploy/guide_check.js`, 58/58 on 18 October, after the review of `810a4cc` (T1 now checks that signing out removes unsent text; T5 to T7 use the shorter tab labels and the attention box). That covers T1 to T8. T9, phone and keyboard, is covered by `ui_check.js` and `layout_check.js`. No teammate has used revision 3 yet.

**On branch `explore/agent-coordinator-20261019` (20 October, not deployed).** Requests opens the desk there. The guide's Requests steps describe the old pages, which on that branch are at `#/cases` (list view) and `#/cases/new` (the form). `guide_check.js` opens those addresses directly. Revision 4 of the guide, for the Requests area, is pending.

**Preview of that branch (20 October).** It runs at https://nucleon.dracooz.top/preview/ (E019; [DEPLOYMENT.md](../../DEPLOYMENT.md), "Preview instance"). This guide's Requests steps still describe the old pages there, at `#/cases`, not the desk. Since the evening of 20 October the preview runs the conversational desk (E020), which this guide does not cover either; revision 4 is still pending.

**Where the original is.** The PC handover and the revision 2 pack it used are kept unchanged in [../2026-10-18-pc-handover/](../2026-10-18-pc-handover/).
