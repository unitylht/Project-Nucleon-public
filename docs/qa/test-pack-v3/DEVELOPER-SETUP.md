# Developer setup for testing the redesigned interface

For whoever runs the app or prepares a test session. Testers need only the guide in the pack. All data is fictional. Never reset, restore or reconfigure the shared practice instance for testing. Use a local server or an isolated database.

## A local preview

From the repository root, on branch `feat/ux-redesign-20261018`, with Python 3.10 or later.

**Quickest (test agent, no AI model).** A fresh practice workspace with the fictional sample, a fixed business date of Fri 16 Oct 2026, and the demo console:

```bash
python3 deploy/ui_check_server.py /tmp/nucleon-preview.sqlite3 8765
```

- Open http://127.0.0.1:8765.
- The terminal prints `STAFF access code: …`, `OWNER access code: …` and `OPERATOR access code: …`. Use those; they change on every start. Keep them out of screenshots and documents.
- The test agent reads only invoice numbers like `DEMO-101` and ISO dates (2026-10-30). Use the sample messages under New request → Practice messages, or `DEMO-` numbers on your own customers.
- Starting it again deletes that database.

**With the real model** (the local Gemma gateway must be running). Copy `prototype/config.example.json` to a private path outside the repository and edit it:
- `"db"`: a new file, for example `/tmp/nucleon-live.sqlite3`;
- `"port"`: for example `8766`;
- `"publicOrigins"`: `[]`;
- `"demo"`: `{"enabled": true, "backupDir": "/tmp/nucleon-live-backups"}`.

Keep `"sampleData": true` for the fixed practice date. Then:

```bash
python3 prototype/server.py --config /path/to/your-copy.json
```

This is what the team test pack needs: its tagged invoice numbers (for example `HL1018U-CSV-001`) are read by the model, not by the test agent.

**First-run setup** (the old optional T8): start with no sample. The owner then sees the workspace choice:

```bash
python3 prototype/server.py --db /tmp/nucleon-first-run.sqlite3 --port 8767
```

## On the home server

Use `nucleonctl isolate <name>` and `nucleonctl production`, as described in [../../DEPLOYMENT.md](../../DEPLOYMENT.md). The shared practice instance runs this branch (`f95f50f`) since 18 October at 23:24: give testers guide revision 3 for it. Revision 2 was for the earlier interface (`a9ce30d`).

## Checks

Playwright is needed for the browser checks. Set `NODE_PATH` to a folder whose `node_modules` contains `playwright`.

```bash
cd prototype && python3 -m unittest discover -q          # unit tests
python3 deploy/ui_check_server.py /tmp/uic.sqlite3 8881 &
python3 deploy/ui_check_server.py /tmp/uicf.sqlite3 8882 --fault-fallback &
node deploy/ui_check.js http://127.0.0.1:8881 <log of 8881> http://127.0.0.1:8882 <log of 8882> /tmp/ui-check   # the whole interface
node deploy/guide_check.js http://127.0.0.1:8766 <log> /tmp/guide-check   # guide revision 3, on a live-model server with the sample
NUCLEON_LOG=<log> node deploy/layout_check.js http://127.0.0.1:8881     # 375, 390, 820 and 1366 px, measured
```

- **What each needs:** `ui_check.js` and `layout_check.js` read the access codes from the server's output. Redirect it to a file and pass that file. `guide_check.js` creates, applies and reverts its own tagged records.
- **Never on the shared instance:** neither `ui_check.js` nor `guide_check.js`.
- **The older checks:** `browser_check.js` (`--fallback`, `--legacy`, `--records`, live), `e2e_records_check.py`, `e2e_https_check.py` and `e2e_stage3_check.py` run against isolated databases as in DEPLOYMENT.md.

## Building the pack

```bash
cd docs/qa/test-pack-v3/build
npm install docx@9.5.1          # node_modules is ignored by Git
node build_guide.js             # the Word guide (Arial) and GUIDE-v3.md, from guide-content.js
python3 make_pack.py            # tester folders, templates, README.txt and Nucleon-Team-Test-Pack-v3.zip
```

Edit `guide-content.js`, not the generated files. For a new round, change the tags in `make_pack.py`, so earlier records never collide. To check the layout, convert the Word file to PDF, for example with LibreOffice (`soffice --headless --convert-to pdf`), and look at every page.
