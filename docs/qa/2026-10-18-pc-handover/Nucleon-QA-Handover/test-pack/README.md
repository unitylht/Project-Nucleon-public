# Test pack

This folder separates the **original supplied materials** from what the tester **used** or **added**.

| Folder | Content | Status |
|---|---|---|
| [original/](original/) | The supplied pack, unchanged | **Original** |
| [inputs-used/](inputs-used/) | The CSVs actually uploaded, plus every manual entry and message typed | Tester's copies |
| [derived/](derived/) | Text extraction of the guide, and the tester's corrections and observations | **Not original** — tester-authored |

## original/
- `Nucleon-Team-Test-Pack.zip`: the supplied ZIP, byte-for-byte as received (53,735 bytes).
- `Nucleon-Team-Test-Pack/`: that ZIP extracted during packaging. It is identical to the copy extracted and used
  during testing (checked with a recursive diff). It contains:
  - `README.txt`: pack instructions (revision 2, 18 October 2026, practice release a9ce30d).
  - `Nucleon-Team-Testing-Guide.docx`: the testing guide (T1–T7, optional T8).
  - `templates/`: the four CSVs with the `TESTTAG` placeholder.
  - `testers/<Name>-<TAG>/`: five tester folders (Chris-CC1815A, Hanting-HL1815A, Hoang-HN1815A, Phu-PD1815A,
    Tony-TT1815A), each with four CSVs and `YOUR-TAG.txt`.
- `Nucleon-Team-Testing-Guide (1).docx`: a separately supplied copy of the guide that sat next to the ZIP on the
  test PC. It is **byte-identical** to the guide inside the ZIP (same SHA-256).

The pack's README says access codes are supplied privately. **No codes are included anywhere in this package.**

## inputs-used/
- `CL1018T/01-invoices.csv` … `04-revert-only.csv`: copies of `original/Nucleon-Team-Test-Pack/testers/Hanting-HL1815A/`
  with every `HL1815A` replaced by `CL1018T` (plain text substitution, `sed s/HL1815A/CL1018T/g`). There is no other
  change: same header rows, values and line structure; ASCII/UTF-8 without BOM, as in the originals.
  - These four files were uploaded through the file input in this order: 01 (twice), 03 (preview only), 02 (twice),
    04.
- [MANUAL-ENTRIES-AND-MESSAGES.md](inputs-used/MANUAL-ENTRIES-AND-MESSAGES.md): every value typed by hand
  (customers, invoices, note, requests, opening balances, completeness, late payment, correction, reasons).

No other input files were used.

## derived/
- [guide-text-extract.md](derived/guide-text-extract.md): a plain-text/Markdown rendering of the .docx, made
  during packaging so the guide can be searched. The .docx is authoritative.
- [GUIDE-CORRECTIONS-AND-OBSERVATIONS.md](derived/GUIDE-CORRECTIONS-AND-OBSERVATIONS.md): where the app differed
  from the guide's claims, and the tester's suggested wording. These are suggestions, not part of the original guide.
