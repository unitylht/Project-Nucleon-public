# Evidence keys: bookkeeping, wording and a migration

Assessment and design, 18 October 2026, for item 4 of the review of `810a4cc`. Written before any implementation. The implementation follows in separate commits, and its verification is added at the end of this document.

## Summary

- **Bookkeeping can be told apart safely.** One field is pure import bookkeeping: `confirmedBy` on invoices and payments. One thing recorded in that field is evidence, not bookkeeping: a later import that disagreed with a record, where a person kept the recorded value. That gets its own field and stays in the keys.
- **The keys also hash wording.** Explanations ("why not exact", conflicts) and record descriptions are part of the keys. This branch changed that wording (U7), so it would flag decided cases whose records have not changed. Reproduced on a read-only copy of the production database. That is a deployment blocker for this branch, and it is fixed by the same change.
- **A migration is needed.** Existing keys are re-baselined only when the records are shown to be unchanged under the format that stored them. Anything else is flagged (decided cases) or prepared again (pending cases). Existing flags are never touched.

## What the keys are now

- **A decided case** stores `evidenceSeen.key`. This is a SHA-256 over:
  - the customer record;
  - the invoice as the evidence view shows it, including its derived `position`;
  - the customer's opening balances;
  - the completeness statements that apply to the customer, including the derived `contradictedFor`.

  After every records change, `records_changed` recomputes the key. If it differs, the case gets the flag "The records changed after this decision", naming the change and who made it, and the baseline moves to the new key. The decision itself never changes.
- **A pending case** (awaiting the owner) stores `task.evidenceVersion`. It covers:
  - the settings and business date;
  - the customer and all its invoices, with positions;
  - its payments, allocations, opening balances, completeness statements and notes;
  - the effective due date.

  If the version differs at startup or after a records change, the case is prepared again.

## Reproduced

Branch code, scratch databases (`ImportTests` harness). The production check used a read-only copy taken with SQLite's backup API.

| Change | Recorded values changed | Decided case | Pending case |
| --- | --- | --- | --- |
| Re-import of an unchanged file | None; the invoice's `confirmedBy` gains the import | Flagged "records changed" | Prepared again |
| Revert of that import (it changed no rows) | None; `confirmedBy` loses the import | Flagged again | |
| A conflicting row, recorded value kept | None; `confirmedBy` gains the import | Flagged | |
| This branch's U7 wording, on the production copy | None | `req_35c17a88…` is flagged at the first unrelated change. The flag reads "Customer Unrelated fictional customer added by staff", with "at most AUD 400.00" before and after. `a9ce30d` adds no flag. | All three still match |

Stored keys on the production copy: all six (three decided, three pending) match what `a9ce30d` computes now. Under this branch's code, the decided case `req_35c17a88…` no longer matches. Its position has a not-exact reason whose wording U7 changed.

Also found: after a kept conflict, reverting the original import keeps the invoice with the original values, but attributes it to the later import ("confirmed by a later import"), whose file disagreed with those values. Tracked separately below; this change does not alter revert behaviour.

## What is bookkeeping and what is evidence

**Bookkeeping: `confirmedBy` on invoices and payments.**
- **Written** only by the importer:
  - apply adds the import for unchanged rows, and for conflicting rows where the recorded value is kept;
  - revert removes the reverted import, and its keep path moves the latest one into `setBy`.
- **Read** only by `revert_impact` and `payment_revert_impact`, to see whether a later import still lists the record.
- It never holds a value, the source of the current values, or a person's answer.

**Evidence recorded in the same list: a kept conflict.** A later source said something different, and a person kept the recorded value. The amount is unchanged, but the evidence is not. Today such a case is flagged only because `confirmedBy` changed. To keep that signal once `confirmedBy` leaves the key:
- the importer also records the import in a new list, `disputedBy`, which stays in the keys;
- revert removes it from `disputedBy` as it does from `confirmedBy`. Withdrawing the disagreement is also a change.

`confirmedBy` and the revert rules are not changed.

**Everything else stays in the keys**, including:
- `setBy`: who, or which import, the current values come from. A revert that re-attributes a record to a later import is still flagged.
- `history`, `version`, `origin`, the status fields, and `removed` or `reverted`.
- Every person's answer: whether a payment was reflected in a stated amount, opening-balance inclusion, "not for an open invoice", and the credits in an opening balance.
- Customer aliases.
- `confirmedBy` on notes and completeness statements. It has the same name but a different meaning: the person who confirmed them.

**Derived values keep their content and lose their wording.**
- **Position:**
  - Every number, date, record id and status stays as now.
  - Conflicts, checks and not-exact reasons become codes, each carrying the values the sentence states: amounts in minor units, ISO dates, record ids and counts.
  - Exact-amount steps are kept by amount. Their labels are fixed text built from the basis and dates, which are already in the key.
- **Contradictions** become the record id and whether it was added to, or taken out of, the confirmed period. The record's description is dropped.

**So:**
- A change of wording no longer moves a key.
- A change to anything an explanation states still does. For example, a new reason why an amount is not exact is flagged even when the "at most" amount stays the same.

**Not chosen:**
- **Comparing amounts only** would miss new conflicts, new open questions and broken completeness, all of which leave the amount unchanged.
- **Hashing all of the customer's records instead of the derived values** would flag decided cases for changes that do not affect their invoice, such as a payment for another invoice after the confirmed period. Today only changes to what the decided invoice shows are flagged.

## Format 2

- **Decision key:** a SHA-256 over:
  - the customer;
  - the invoice without `confirmedBy`, with its position in the form above;
  - the opening balances;
  - the applicable completeness statements, with contradictions as ids.

  `evidenceSeen` gains `"format": 2`.
- **Pending version:** as now, with the same projection for invoices, payments (without `confirmedBy`) and completeness statements.

## The migration

It runs during startup recovery: once per database, and again after a restore, because a restore brings back the database's own meta. It runs after the document migration and before stale cases are prepared.

1. **Backfill `disputedBy`.** For each applied import and each conflicting row it did not take, add the import to that record's `disputedBy`, if the import is in the record's `confirmedBy`. No key is compared yet, and no case changes.
2. **Pending cases:**
   - Version already in format 2: nothing.
   - Version equal to the `a9ce30d` version computed now: re-stamped to format 2, with the existing event `evidence.version_updated` and its reason. The case is not prepared again.
   - Otherwise: the existing path. The case is prepared again. The earlier whole-document re-stamp stays.
3. **Decided cases with a stored key:**
   - Key already in format 2: nothing.
   - Key equal to the `a9ce30d` key computed now: the records are unchanged since that baseline. Re-baselined to format 2, with the event `evidence.key_format_updated` holding the old and new keys. No flag.
   - Otherwise: the records no longer match the last comparison, and when they changed was not recorded.
     - A flag is added now: `records_changed_after_decision`, cause `startup comparison`. Its description says the change was found when this version started, and that when and by whom it was made was not recorded. It also gives the amount still owed before and now.
     - The baseline then moves to format 2, as after any flag.
4. **Decided cases without a stored key:** the existing baseline path, now in format 2.
5. **Existing flags are never changed, removed or re-dated.** A decision, its stored snapshot and the due date it set are never changed.
6. **A marker** `evidenceKeys` is written in meta, with the format, the time and the counts. Later starts skip the `a9ce30d` comparison.

**"The `a9ce30d` key computed now"** means `a9ce30d`'s formulas applied to the current records, with the derived values written as `a9ce30d` wrote them:
- contradictions as record descriptions;
- its one completeness sentence in its earlier wording, rebuilt from the reason's code;
- no "The statement that they were complete … no longer holds" sentences;
- no codes.

This is a frozen module used only by the migration. Before use, it is checked against `a9ce30d`'s own code on every database available: the production copy, the isolated test databases and the backups. It must give identical keys for every case.

**Not recognised:** keys written by this branch before the change. The branch was never deployed, so these exist only in local test databases. They are treated as unverifiable: decided cases are flagged, and pending cases are prepared again.

## Rollback

After the migration, the earlier release would read format-2 keys as changes:
- at its first records change, it would flag every decided case;
- at startup, it would prepare every pending case again.

So roll back by restoring the backup `nucleonctl deploy` takes before the deploy, not by running earlier code on a migrated database.

## Verification plan

- **Unit tests:**
  - After a decision, nothing is flagged by an unchanged re-import, by the revert of that zero-row import, or by a change of explanation wording alone.
  - A pending case is not prepared again after an unchanged re-import.
  - A kept conflict is flagged, and so is its revert. A taken conflict is flagged.
  - A new not-exact reason with an unchanged "at most" amount is flagged.
- **Migration tests on a database written by `a9ce30d`'s code:**
  - unchanged records are re-baselined with no flag;
  - a change made behind the comparison is flagged at startup;
  - existing flags are kept as they were;
  - pending cases are re-stamped, not prepared again;
  - kept conflicts are backfilled;
  - a second start changes nothing.
- **The frozen keys** checked against `a9ce30d`'s code on every available database.
- **On a copy of the production database:** the new release starts.
  - The three pending cases are re-stamped and the three decided cases re-baselined.
  - No flag is added, and the existing flag on `req_35c17a88…` is unchanged.
  - An unrelated change then flags nothing, while a real change to that invoice is flagged.
- **The full unit suite and the release checks.**

## Revert attribution after a kept conflict (resolved)

Found during this assessment, and fixed separately in `f95bbc0` at Hanting's instruction. A kept conflict never supports the values it disagreed with. A revert that would leave a record with no import supporting its values is blocked, and the block says how to proceed. See [qa/FINDINGS-DISPOSITION.md](qa/FINDINGS-DISPOSITION.md), R5.

## Verification (after implementation, `83c602e`)

- **Unit tests:** `test_evidence_keys.py` 12/12, and the whole suite 237/237.
  - **Bookkeeping:**
    - an unchanged re-import and its zero-row revert leave a decided case alone;
    - an unchanged re-import leaves a pending case awaiting the owner, and it is not prepared again.
  - **Evidence:**
    - a kept conflict is flagged, with the amount the same before and after, and so is its revert;
    - a taken conflict is flagged;
    - a new reason with the same "at most" amount is flagged;
    - another record added inside a confirmed period moves the key.
  - **Wording:** with every date and record description rendered differently, both keys stay the same while the explanations change.
- **Migration, on a database written by `a9ce30d`'s own code** (`prototype/testdata/a9ce30d-evidence.sql`, made by `make_a9ce30d_evidence.py` from an export of that release):
  - **Carried over:**
    - all three decided cases are re-baselined. This includes the one whose completeness explanation changed wording, and one that already carried two flags.
    - the pending case is re-stamped, keeping its version and analysis.
  - **Flags:** existing flags stay byte-identical. A change written directly into the database before startup is flagged at startup ("cause: startup comparison"); the pending case it affects is prepared again.
  - **Backfill:** the kept conflict is recorded in `disputedBy`.
  - **Afterwards:** an unrelated change flags nothing, a real correction flags, and a second start changes nothing.
- **The frozen keys against `a9ce30d`'s own code**, computed on read-only copies of every database on the home server:
  - **Equal on every case that has keys of this kind:** 26 cases in 9 databases. These are production (6), the five Stage 3 test databases, and three backups.
  - **Skipped:** databases older than Stage 3, which have no record tables or no records.
  - **One pending case** in a pre-reset backup no longer matches its stored version under `a9ce30d` itself. That release would prepare it again, and so does the migration.
- **On a copy of the production database:**
  - The first start re-baselined 3 decided cases and re-stamped 3 pending ones. It flagged nothing and prepared nothing again, and all flags are byte-identical.
  - The same unrelated change that flagged `req_35c17a88…` before the fix now flags nothing.
  - A real change to that invoice (CL1018T-CSV-001) flags it.
