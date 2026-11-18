# Handbook sources

Two published pages are built from this folder (11 Nov 2026):

- **Nucleon Operating Manual** (for an Owner and for whoever demonstrates the product): `manual/`. Screenshots are taken from a scratch server on the fictional demonstration data:
  `capture.py` (needs Playwright; on the M3: `~/Developer/nucleon-local/pwvenv/bin/python`) → `convert.py` → `build.py` → `nucleon-manual.html`.
  Text lives in `part1.html`, `part3.html` and `settings.py` (one row per Control panel setting; labels are quoted from `prototype/web/delegation.js`).
  **Retake the screenshots whenever a page changes**: the manual must show the system as it is.
- **Nucleon Report Pack** (facts, reasons, change history, proof of value and course requirements for the team's final report): `pack/INFO-PACK.md` → `python3 pack/build_pack.py` → `nucleon-report-pack.html` (it embeds `manual/shots/`).

The built HTML files are not kept here (about 9 MB each); rebuild them. `deploy/m3-local/tests/bosstest/` holds the scripts that walk a copy of a live database as the Owner and Staff would (`copy_server.py`, `tour.py`, `act.py`, `act2.py`) and the real-assistant conversation run (`live_chat.py`, only between a snapshot and its restore).
