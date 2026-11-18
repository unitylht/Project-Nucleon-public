PROJECT NUCLEON TEAM TEST PACK
Revision 3 | 18 October 2026 | for the redesigned interface (branch feat/ux-redesign-20261018)

1. Extract this ZIP before opening any file.
2. Open Nucleon-Team-Testing-Guide-v3.docx and follow it from "Before you start".
3. Use the folder with your name under testers. In a pair, use one folder for both roles.
4. Your tag is in YOUR-TAG.txt. The CSV files already contain it: do not edit them on a first run.
5. Work through T1 to T9 in order. TAG in the guide means your tag.

Files in each tester folder
01-invoices.csv: two invoices with the same number for two new customers. Import first; later import it again with the SAME source label.
02-payments.csv: one payment allocated to its own customer's invoice, and one not allocated. Import after 01.
03-invalid-preview-only.csv: two rows the app must reject and one valid row. Check it, then discard the draft. Never apply it.
04-revert-only.csv: one invoice for a separate customer, used only for the safe revert in T8.

The templates folder holds TESTTAG versions for repeat runs: replace TESTTAG with a new unique tag in a plain-text editor, keep UTF-8 and .csv.

Shared instance rules
Use only records with your tag. Never edit, answer, revert or remove anyone else's records.
Do not use the demo console, Reset, Start empty or Restore. Do not change Setup.
Never choose "All customers" when confirming completeness.
Read what a revert or removal will affect before confirming it; stop if it names anything without your tag.
Access codes are given privately by Hanting. None are in this pack. Never put a code in a screenshot or document.
Leave your tagged records in place for review.

Developers: setting up a local or isolated server is described in DEVELOPER-SETUP.md in the repository (docs/qa/test-pack-v3), not here.
