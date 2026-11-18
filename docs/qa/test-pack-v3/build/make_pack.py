"""Make the team test pack, revision 3: one folder per tester with their tag in four CSV files, templates, the README, and the ZIP.
    python3 make_pack.py            (run build_guide.js first; it writes the guide into the pack folder)
Every value is fictional. Tags are new for revision 3, so records from earlier runs (HL1815A, CL1018T, …) never collide."""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / 'Nucleon-Team-Test-Pack-v3'
TESTERS = {'Hanting': 'HL1018U', 'Hoang': 'HN1018U', 'Phu': 'PD1018U', 'Chris': 'CC1018U', 'Tony': 'TT1018U'}

FILES = {
    '01-invoices.csv': 'Customer,Invoice number,Invoice date,Invoice amount,Due date\n'
                       'TAG Imported A fictional,TAG-CSV-001,2026-10-05,1000.00,2026-10-10\n'
                       'TAG Imported B fictional,TAG-CSV-001,2026-10-05,200.00,2026-10-10\n',
    '02-payments.csv': 'Customer,Payment date,Amount received,Payment reference,Invoice number\n'
                       'TAG Imported A fictional,2026-10-12,600.00,TAG-PAY-001,TAG-CSV-001\n'
                       'TAG Imported B fictional,2026-10-12,50.00,TAG-PAY-002,\n',
    '03-invalid-preview-only.csv': 'Customer,Invoice number,Invoice date,Invoice amount,Due date\n'
                                   'TAG Imported A fictional,TAG-BAD-001,2026-02-31,100.00,2026-10-10\n'
                                   'TAG Imported A fictional,TAG-BAD-002,2026-10-05,1O0.00,2026-10-10\n'
                                   'TAG Imported A fictional,TAG-VALID-PREVIEW,2026-10-05,250.00,2026-10-10\n',
    '04-revert-only.csv': 'Customer,Invoice number,Invoice date,Invoice amount,Due date\n'
                          'TAG Revert Demo fictional,TAG-RV-001,2026-10-05,75.00,2026-10-10\n',
}

README = """PROJECT NUCLEON TEAM TEST PACK
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
"""

YOUR_TAG = """Your tag is {tag}

Use this exact tag in the guide's names, invoice numbers, messages and source labels.
Your CSV files already use it. No editing is needed on your first run.
In a pair, use one person's folder and tag for both roles.
Use a new tag throughout if you repeat the run.

Source labels
{tag} Invoice test
{tag} Invalid preview
{tag} Payment test
{tag} Revert test
"""


def main():
    (PACK / 'templates').mkdir(parents=True, exist_ok=True)
    (PACK / 'README.txt').write_text(README, encoding='utf-8')
    for name, text in FILES.items():
        (PACK / 'templates' / name).write_text(text.replace('TAG', 'TESTTAG'), encoding='utf-8')
    for person, tag in TESTERS.items():
        folder = PACK / 'testers' / f'{person}-{tag}'
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in FILES.items():
            (folder / name).write_text(text.replace('TAG', tag), encoding='utf-8')
        (folder / 'YOUR-TAG.txt').write_text(YOUR_TAG.format(tag=tag), encoding='utf-8')
    guide = PACK / 'Nucleon-Team-Testing-Guide-v3.docx'
    if not guide.exists():
        raise SystemExit('Run build_guide.js first: the guide is missing.')
    archive = HERE.parent / 'Nucleon-Team-Test-Pack-v3.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PACK.rglob('*')):
            if f.is_file():
                z.write(f, Path('Nucleon-Team-Test-Pack-v3') / f.relative_to(PACK))
    print('written', archive)


if __name__ == '__main__':
    main()
