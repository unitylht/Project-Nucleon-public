# UI references and reset scope
Updated 2026-10-26. Captures **user-preferred patterns**, not implementation instructions or screenshots as product truth.

## Reset decision
User explicitly wants to **discard the previous console UI** and redesign it from scratch. The new owner console has not started. Do not discard verified data models, credit workflows, authentication, idempotency or financial completeness just because the old UI is retired.

## Reuse: Key Facts timeline
Old screenshot (shown privately in chat, not checked into repository) was liked for its readability:
- Original due date: Sun 18 Oct.
- Historical 'today/as-of': Sat 24 Oct.
- Requested new due: Tue 10 Nov.
- Extension: **+23 days from original due date**. As-of 24 Oct implies **6 days overdue**, distinct from requested extension.
In screenshot labels crowded/overlapped, so rebuild responsively with clear spaced date labels; exact backend dates; derived durations; clear timezone, currency and as-of provenance. Screenshot dates are historical **illustrative**, not live test fixtures or today's date. When dates are incomplete/uncertain, display caveats rather than fabricating them.

## Add later: Decision Handling owner console
Visual example: 60% autonomous, 25% gathering evidence, 15% Owner review out of 100 hypothetical requests. All figures are illustrative and **not measured Nucleon outcomes**.
- Show count, denominator, status, timeframe and source; distinguish in-progress information-gathering from completed resolutions.
- Measure autonomous resolution and Owner review workload, but do not optimise volume at expense of credit losses/false approvals.
- Include overrides, exceptions, credit exposure, outcome quality and confidence limitations over time.
- Simple Owner policy controls: authority level, automatic exposure cap, new customer trial policy, with transparent advanced restrictions. UI is conceptual, not adopted detailed contract.

## User experience principles
- Conversational first. The assistant searches, reasons, requests evidence and, when authorised, acts; not a dashboard-centric manual workflow.
- Real owner permissions and business effects enforced in backend.
- Financial caveats and policy explanations come from structured tools, not confident model prose.
- A model's statement 'submitted/approved' does not constitute business-state proof.
- Separate **internal credit decision** from **external communication/action**. Staff may be notified or complete outgoing mail; this is not a second credit approval.
- Keep desktop MVP clear, minimal and stable. Do not rebuild broad console functionality as a prerequisite for current demo.
