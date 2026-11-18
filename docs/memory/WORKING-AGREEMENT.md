# Memory operations — ChatGPT, Claude Code and team
Updated: 2026-10-26

## Aim
Shared evidence-based project state rather than any AI's private conversation history. GitHub is the record, not an automatically synchronised memory stream.

## When starting work
1. Read [START-HERE](START-HERE.md), charter, decision authority, engineering snapshot and decision register. Also read repo `AGENTS.md`, `CLAUDE.md`, course constraints and current source files relevant to the requested change.
2. Check whether local branches/worktrees are ahead of GitHub. Documentation snapshot is not direct proof of current code.
3. State what is **confirmed / proposed / disputed / deprecated / implemented / tested / deployed**.
4. Resolve conflicts in this order: newest explicit user confirmation, verified code/runtime facts for implementation, documented decisions and evidence. Team/Owner facts must retain proper attribution.
5. Before write actions: check exact repo/branch/path; prefer isolated documentation branch, no surprise pushes/merges. Preserve existing historical documents and local unpublished changes.

## After major work
Update product principles only when actually decided. Record decision changes with reasons and supersession; update engineering status with commit, tests and environment; attach evidence and open limitations; update handoff. Distinguish code **committed locally** from **pushed**, **tested in isolation** from **deployed**.

## Existing generated project brief
`docs/project-state.json` drives `docs/PROJECT-STATE.md`. Do not hand-edit the generated Markdown. Reconcile local newer version before updating source JSON and regenerate via `tools/build_brief.py`. Existing old files remain historical snapshots until reconciled.

## Branch approach (updated 30 October)
The original product-memory notes were created on `docs/product-memory-20261026`. Further ADA status was recorded on `docs/ada-status-demo-plan-20261027`. The 30 October PoV documentation consolidation builds on the latter branch and is intended for a reviewable PR to `main`. Documentation Git branches are **not** M3 application code branches. Inspect local work and reconcile concurrent edits before merge; no automatic deployment from documentation.

## Security and privacy
Store no tokens, personal passwords, test signing keys, actual customer details or unreviewed private transcripts in memory documents. Use fictionalized examples and references. Describe privileged tool limitations accurately.

## Drift prevention checklist
- Did we mistake a POC guard for the long-term product goal?
- Did we mistake a proposed AI delegation policy for actual authorisation?
- Did we mistake a teammate's report for verified Owner input?
- Did we overstate financial completeness, accuracy, benchmarks or sample validity?
- Did we confuse M3, M6 and isolated demo deployment?
- Did we assume this GitHub branch contains unpublished local commits?
