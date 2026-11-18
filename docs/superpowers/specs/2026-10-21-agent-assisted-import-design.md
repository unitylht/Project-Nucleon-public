# Agent-assisted import (design, 21 October 2026)

## Intent

Importing a spreadsheet today means choosing a shape, mapping each column by hand, and repeating that for invoices and for payments. The team wants the agent to read the file, work out what is in it, fill the import in, and leave the person to check and correct a few things before one confirmation. Nothing changes in what gets written: the deterministic importer still applies the rows, keeps the batch, and can revert it.

## What the person experiences

1. On the Lab, the person attaches a file (`.xlsx` or `.csv`) or pastes its content, with or without a sentence ("this is NTK's ledger for the year").
2. The agent reads it and shows **one import proposal card**: what the file seems to be (an invoice list, a payment list, or a ledger with both), which sheet, the column mapping it proposes for each field with a confidence mark, how it names customers, how it groups ledger lines into invoices, how due dates are derived (credit terms), the counts (customers, invoices, payments), the money unit it detected, and the rows it is unsure about (missing dates, zero amounts, duplicate invoice numbers).
3. The person corrects a mapping or a rule in the card (dropdowns prefilled), or says it in words ("the customer is column B, due dates are 30 days"), and presses **Import**. The card then shows the applied batches with their revert links. Nothing is written before the press.

## Decisions

1. **Parsing is code.** The records server gains a stdlib `.xlsx` reader (zip + XML, shared strings, Excel serial dates) and a ledger splitter: rows with a debit and an invoice number become invoice lines grouped by invoice number; rows with a credit become payments; the customer column is the one the mapping names; a credit-term column yields due dates. Headers are matched by the existing synonym lists (English and Vietnamese), extended by whatever the model proposes.
2. **The model proposes, code verifies.** A new records operation `proposeImport(fileText|xlsx, sheet?, hints?)` builds the proposal with heuristics first; the model is asked only to classify columns the heuristics cannot (through the existing adapter, with the header and three sample rows), and its answer is checked against the data (a date column must parse as dates, an amount column as money). Every count in the card is computed by code.
3. **Apply reuses the importer.** `applyImportProposal(proposalId, corrections?)` turns the proposal into one or two import batches (`invoices`, `payments`) through the existing upload → mapping → apply path, so previews, idempotency, source labels and revert stay as they are. The proposal is stored on the records with a version; a correction makes a new version; apply refuses a stale version.
4. **Roles.** Staff and the owner may propose and apply (imports are staff work today). The agent never applies: the button does.
5. **Privacy and data.** The file stays on the records instance; nothing is sent anywhere but the local model gateway (headers and three sample rows). Data files are never committed.

## Non-goals

Editing individual rows in the card (fix the file or the mapping instead); PDF or scanned statements; automatic apply.

## Validation

Unit tests for the xlsx reader (shared strings, serial dates, blank rows), the ledger splitter (the NTK-shaped fixture rebuilt from fictional rows), the proposal's counts and flags, stale-version refusal, and that the apply writes exactly what the preview showed; a Lab check that drops a fictional `.xlsx` and sees the card, corrects one mapping, imports, and finds the batches on the records page; the builder's own run with the team's file on the Lab after the demo.
