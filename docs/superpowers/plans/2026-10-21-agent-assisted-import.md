# Agent-Assisted Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A person attaches a spreadsheet on the Lab, the agent proposes the whole import (sheet, shape, mapping, customer naming, ledger splitting, due dates, counts, doubtful rows), the person corrects and presses Import once, and the existing importer writes the batches.

**Architecture:** records side (stdlib): an `.xlsx` reader, a ledger splitter, `proposeImport` and `applyImportProposal` operations exposed on the tool surface; the model classifies only columns the heuristics cannot, through the existing adapter, and code verifies. Lab side: a `prepareImport` tool, file attachment on the composer (sent to the Lab, forwarded to the records), an import-proposal card with editable mappings and an Import button that calls the records' apply.

**Tech Stack:** as the Lab plans (Python 3.12 stdlib records; Lab venv; assistant-ui UI; Playwright checks).

**Spec:** `docs/superpowers/specs/2026-10-21-agent-assisted-import-design.md`.

## Global Constraints

- Records server stdlib-only; fictional fixtures only in tests; data files never committed; no secrets.
- Existing tests and checks keep passing (records 463, Lab 115, desk 76/76, lab_check 99/99, conversation mock 319/319).
- The agent never applies an import: the card's button does, through the records with the proposal version; a stale version is refused.
- Nothing but headers and three sample rows goes to the model; counts are computed by code.
- Commit per task; implementers never push or deploy; never touch ~/srv, the public URL or ports 8620–8623 (a demo is running).

## Review Focus

1. Excel serial dates and text dates both parse; a column with mixed content is not a date column. (Task 1.)
2. The ledger splitter never double-counts VAT lines: an invoice's amount is the sum of its debit lines once; credit rows are payments, never invoices. (Task 1.)
3. Apply writes exactly the previewed rows, as two batches with revert, and refuses a stale proposal version. (Task 1 test; Task 2 check.)
4. A staff member can propose and apply; the owner too; the model's column answers are verified against the data before use. (Task 1.)
5. The card never shows the file's rows beyond the three samples and the flagged rows, and attachments are size-limited (2.5 MB, like `/api/imports`). (Task 2.)

---

### Task 1: Records: xlsx reader, ledger splitter, proposal and apply
**Files:** `prototype/xlsx.py` (new: `read_workbook(bytes) -> {sheet: [rows]}` with shared strings, inline strings, numbers, serial dates → ISO when the cell style is a date or the header says date), `prototype/importer.py` (`propose(rows, header_hints, classify) -> proposal` with shape detection: `invoices`, `payments`, `ledger`; mapping by synonyms then `classify(header, samples)` for unknowns; ledger split; customer naming `<prefix> <id>` when the customer column holds codes; due dates from a credit-term column; counts; flags), `prototype/server.py` (`DeskTools._proposeImport(fileBase64|csvText, fileName, sheet?, hints?)` storing `importProposals` on meta with versions; `_applyImportProposal(proposalId, version, corrections?)` → upload batches with the mapping → apply → `{batches: [{id, shape, counts, revertLink}]}`; registry entries: `proposeImport` prepare (staff, owner), `applyImportProposal` act with confirmation (human-only through the surface: offered to no agent role; the card calls it)), `prototype/coordinator.py` (registry + tool schema; desk mock rule "import|spreadsheet|ledger" → proposeImport), tests `prototype/test_import_proposal.py` with a fictional ledger fixture in the NTK shape (Vietnamese headers, debit/credit, VAT lines, credit terms) and a plain invoice CSV.
- [ ] Tests first (Review Focus 1–4); implement; records suite; commit.

### Task 2: Lab: attachment, tool, card, Import button
**Files:** `lab/tools.py` (`prepareImport` passing the attachment and hints), `lab/app.py` (attachment upload on the chat route: multipart or base64 field, size-limited, forwarded to the records call), `lab/prompts.py` (one rule: a spreadsheet means proposeImport; describe the proposal in two sentences; never list rows), `lab/agent.py` (card kind `import` as an action card), `lab/web/src` (composer attachment button; `ImportProposal` card: sheet, shape, mapping table with dropdowns prefilled from the proposal and the records' field list, naming rule, due-date rule, counts, flagged rows, Import button → `records/api/tools/applyImportProposal` with the version; after apply the card shows the batches and revert links), `deploy/lab_check.js` (a fictional xlsx fixture generated in the check: drop it, see the card, change one mapping, Import, assert two batches on the records and the invoice count), tests in `lab/tests`.
- [ ] Tests/check first; implement; build; run lab_check; commit.

### Task 3: Records and docs
**Files:** PROMPTS.md (the new tool text; version bumps), docs/DECISIONS.md (E024), lab/README.md, prototype/README.md, docs/DEPLOYMENT.md (placeholders for the controller).
- [ ] Write; commit.
