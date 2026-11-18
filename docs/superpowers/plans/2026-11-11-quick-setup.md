# Quick Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An Owner who has never seen Nucleon sets a working first delegation policy alone in about ten minutes, and sees what it does to their own open invoices before saving.

**Architecture:** Two new optional day limits join the policy engine. A pure mapping turns the helper's answers into a full policy. A read-only preview endpoint runs the existing `delegation.evaluate` with that unsaved policy over every open invoice. A new page shows the questions, the preview and a plain summary, and saves through the existing policy PUT.

**Tech Stack:** Python 3 standard library (`prototype/server.py`, `prototype/delegation.py`, `unittest`), plain JavaScript pages in `prototype/web/`, headless-Chrome page checks in `deploy/`.

**Spec:** `docs/superpowers/specs/2026-11-11-quick-setup-design.md`

## Global Constraints

- The helper sits beside the Control panel. No existing setting, page or endpoint is removed or renamed.
- No LLM is involved anywhere in this feature.
- A policy saved before this change behaves exactly as before and keeps its digest.
- The preview writes nothing: no case, no policy version, no event, no notice.
- The preview must call `delegation.evaluate`; it must not re-implement any rule.
- Fictional data only in tests and page checks (`delegation_demo.py`). Never read or write `~/Developer/nucleon-local/data/`.
- Do not deploy, restart or touch the running NTK instance (ports 8631/8630). The owners are using it. Deployment is a separate step the user decides.
- UI text is plain English, short sentences, no jargon ("exposure" is explained wherever it appears).
- Run Python tests with `~/Developer/nucleon-local/venv/bin/python` from `prototype/` (the system Python 3.9 can spin).
- Page checks need `CHROME_HEADLESS=/Users/unitylht/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
- Git has no identity configured in this repo. Commit with `git -c user.name="$(git log -1 --format=%an)" -c user.email="$(git log -1 --format=%ae)" commit ...`. End each message with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Never push.

## Review Focus

1. A stored policy version without the new keys is evaluated, shown and digested without error, and its digest is unchanged. (Task 1)
2. An invoice with no original due date, with `maxDaysPastOriginalDue` set: the check is `unknown` and the request goes to the Owner; it is never approved and never crashes. (Task 1)
3. Money answers typed with separators or spaces ("2,000,000,000", " 500000 "), an empty answer, a negative number: accepted where the Control panel accepts them, otherwise a field error naming the question. (Task 3)
4. Preview on a workspace with no open invoices, or before currency and time zone are set: a clear empty result or the existing `NO_RECORDS` error, not a crash. (Task 4)
5. The policy is saved in another tab between preview and save: the page shows the conflict, reloads the current policy and keeps the Owner's answers. (Task 5)

---

### Task 1: Two new day limits in the policy engine

**Files:**
- Modify: `prototype/delegation.py` (`default_policy` ~l.89, `policy_digest` ~l.112, `validate_policy` ~l.246, `risk_checks` ~l.510, `features_of` ~l.1015)
- Modify: `prototype/server.py` (`dg_request` l.2088; its callers for stored cases at l.2560 and l.2849; where a new case dict is first built after the call at l.2440)
- Test: `prototype/test_day_limits.py` (new; base class `DelegationCase` from `test_delegation.py`, helpers as in `test_auto_decline.py`)

**Interfaces:**
- Produces: policy keys `extensions.maxDaysFromRequest` and `extensions.maxDaysPastOriginalDue` (int 1–365 or `None`; default `None`).
- Produces: request keys `daysFromRequest` (int) and `daysPastOriginalDue` (int or `None`), feature keys of the same names, risk check keys `days_from_request` and `days_past_original_due`.
- Produces: `App.dg_request(self, kind, ev, doc, c, invoice, params, received=None)`; `received` is an ISO date string, default `ev.as_of`. Case key `receivedDate` (ISO date), set when a case is created.

- [ ] **Step 1: Write the failing tests** in `prototype/test_day_limits.py`. Demo facts: as of 2026-10-24, Bayview's DEMO-301 is due 2026-10-18.

```python
class DayLimitTests(DelegationCase):
    def limits(self, **ext):  # saves a new policy version with these extension keys changed
        self.change_policy(extensions={**self.policy()['extensions'], **ext})

    def test_from_request_limit_sends_a_later_date_to_the_owner(self):
        self.limits(maxDaysFromRequest=10)
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # 17 days from 24 Oct
        self.assertEqual(out['handling'], 'owner_review')
        self.assertIn('17 days after the day the request was received is over the limit of 10 days', ' '.join(out['reasons']))

    def test_from_request_limit_passes_inside(self):
        self.limits(maxDaysFromRequest=20)
        self.assertEqual(self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))['handling'], 'autonomous_approve')

    def test_total_lateness_limit_stops_repeated_extensions(self):
        self.limits(maxDaysPastOriginalDue=30)
        first = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-07', reasoning='Fictional: first ask.'))    # 20 days past 18 Oct
        second = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-27', reasoning='Fictional: asks again.'))  # 40 days past 18 Oct
        self.assertEqual((first['handling'], second['handling']), ('autonomous_approve', 'owner_review'))
        self.assertIn('40 days after the original due date', ' '.join(second['reasons']))
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-07')

    def test_without_the_new_limits_nothing_changes(self):
        p = delegation.validate_policy(delegation_demo.DEMO_POLICY, {'currency': 'AUD', 'scale': 2})
        self.assertIsNone(p['extensions']['maxDaysFromRequest']); self.assertIsNone(p['extensions']['maxDaysPastOriginalDue'])
        old = {**p, 'extensions': {k: v for k, v in p['extensions'].items() if not k.startswith('maxDaysFrom') and k != 'maxDaysPastOriginalDue'}}
        self.assertEqual(delegation.policy_digest(p), delegation.policy_digest(old))
        checks = delegation.risk_checks({**old, 'version': 1}, 'extension', {'exposure': 1, 'customerExposure': 1, 'extensionDays': 5}, {'currency': 'AUD', 'scale': 2})
        self.assertNotIn('days_from_request', [c['key'] for c in checks])

    def test_no_original_due_date_is_unknown_never_approved(self):
        f = {'exposure': 1, 'customerExposure': 1, 'extensionDays': 5, 'daysFromRequest': 5, 'daysPastOriginalDue': None, 'nothingElseOverdue': True}
        p = {**delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'extensions': {**delegation_demo.DEMO_POLICY['extensions'], 'maxDaysPastOriginalDue': 30}}, {'currency': 'AUD', 'scale': 2})}
        row = [c for c in delegation.risk_checks(p, 'extension', f, {'currency': 'AUD', 'scale': 2}) if c['key'] == 'days_past_original_due'][0]
        self.assertEqual(row['status'], 'unknown'); self.assertFalse(delegation.would_approve(p, 'extension', f))

    def test_a_recheck_counts_from_the_day_the_request_was_received(self):
        req, _ = self.request_for('bayview', 'DEMO-301', '2026-11-10', received='2026-10-20')   # helper below
        self.assertEqual(req['daysFromRequest'], 21)

    def test_out_of_range_is_a_field_error(self):
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'extensions': {**delegation_demo.DEMO_POLICY['extensions'], 'maxDaysFromRequest': 0}, 'expectedVersion': self.policy()['version']})
        self.assertEqual((status, body['error'], body.get('field')), (400, 'INVALID_INPUT', 'extensions.maxDaysFromRequest'))
```

`request_for(who, reference, date, received)` is a small helper in the test class that calls `self.app.dg_request('extension', ev, doc, customer, invoice, {'requestedDueDate': date}, received=received)` under `self.app.lock`.

- [ ] **Step 2: Run** `~/Developer/nucleon-local/venv/bin/python -m unittest test_day_limits -v` from `prototype/`. Expected: FAIL (unknown policy key / missing `received`).

- [ ] **Step 3: Implement.**
  - `default_policy`: both keys `None` under `extensions`.
  - `validate_policy`: `_int(..., 1, 365, nullable=True)` with labels "Latest new date, in days after the request" and "Most days after the original due date".
  - `policy_digest`: drop each of the two keys from `rules['extensions']` when it is `None` or absent (copy the dict; do not mutate the policy).
  - `dg_request`: add `received=None`; set `daysFromRequest = (requested − (received or ev.as_of)).days` and `daysPastOriginalDue = (requested − originalDueDate).days` or `None`. Callers at l.2560 and l.2849 pass `case.get('receivedDate')`. Set `case['receivedDate'] = ev.as_of.isoformat()` where a new case is built.
  - `features_of`: copy both request keys with `request.get(...)`.
  - `risk_checks`: after `extension_days`, for each limit that is not `None` (read with `ext.get`), `at_most('days_from_request', 'Days after the day the request was received', ...)` and `at_most('days_past_original_due', 'Days after the original due date', ...)`. A limit that is `None` adds no row.

- [ ] **Step 4: Run** the new tests, then the whole suite: `~/Developer/nucleon-local/venv/bin/python -m unittest discover -p 'test_*.py'`. Expected: all pass (1157 existing + the new ones; `test_import_proposal` is occasionally flaky, rerun it alone if it fails).

- [ ] **Step 5: Commit** "Extension limits counted from the request day and from the original due date".

---

### Task 2: The three day limits on the Control panel

**Files:**
- Modify: `prototype/web/delegation.js` (`policySummary` ~l.58, `policyForm` ~l.90, the form-to-body code that reads `extensions.maxDays`)
- Modify: `deploy/delegation_page_check.py` (add checks)

**Interfaces:**
- Consumes: policy keys from Task 1.
- Produces: form fields `name="extensions.maxDaysFromRequest"` (`id="dg-ext-from-request"`) and `name="extensions.maxDaysPastOriginalDue"` (`id="dg-ext-total"`); empty means `null`.

- [ ] **Step 1: Add failing checks** to `deploy/delegation_page_check.py`: fill `#dg-ext-from-request` with `14` and `#dg-ext-total` with `45`, save, reload; both fields show the values; `[data-testid=policy-summary]` contains "14 days after the request" and "45 days after the original due date"; clearing both and saving stores `null` for both (read with `S.api('/api/delegation/policy', None, S.cookie['owner'])`).

- [ ] **Step 2: Run** `python3 deploy/delegation_page_check.py`. Expected: the new checks FAIL, the old ones pass.

- [ ] **Step 3: Implement.** Exact copy for the three fields:
  - `extensions.maxDays` label: "Longest single extension (days after the invoice's current due date)". Hint: "Counted from the date the invoice is due now, not from today. An invoice already 29 days late that asks for 14 more days counts as 43."
  - New field label: "Latest new payment date (days after the day the request is received)". Hint: "Counted from the day the customer asks. Leave empty to not use this limit."
  - New field label: "Most an invoice may be late in total (days after its original due date)". Hint: "Counted from the first due date, so asking again and again cannot go past it. Leave empty to not use this limit."
  - Summary rows only when the value is set.

- [ ] **Step 4: Run** the page check. Expected: all PASS.

- [ ] **Step 5: Commit** "Control panel: three extension day limits, each with how it is counted".

---

### Task 3: Answers to policy, policy to answers, and the plain summary

**Files:**
- Modify: `prototype/delegation.py` (new section at the end, "Quick setup")
- Test: `prototype/test_quick_setup.py` (new, plain `unittest.TestCase`; no server)

**Interfaces:**
- Produces: `quick_setup_policy(answers: dict, current: dict) -> dict` — a policy body ready for `validate_policy` (no `version`, no `digest`). It raises nothing itself: a bad answer is caught by `validate_policy`.
- Produces: `quick_setup_answers(policy: dict) -> dict` — the answers that describe an existing policy, used to prefill the page.
- Produces: `quick_setup_summary(policy: dict, template: dict, names: dict) -> {'decides': [str], 'comesToYou': [str]}`; `names` maps customer id to name.
- Produces: `QUICK_FIELD = {'limits.maxDecisionExposure': 'maxInvoice', 'limits.maxCustomerExposure': 'maxCustomer', 'extensions.maxDaysFromRequest': 'daysFromRequest', 'extensions.maxDaysPastOriginalDue': 'daysPastOriginalDue', 'extensions.maxDays': 'daysPastOriginalDue', 'restrictions.holdCustomers': 'holdCustomers'}` and `QUICK_CHECK = {'decision_exposure': 'maxInvoice', 'customer_exposure': 'maxCustomer', 'days_from_request': 'daysFromRequest', 'days_past_original_due': 'daysPastOriginalDue', 'extension_days': 'daysPastOriginalDue', 'nothing_else_overdue': 'allowOtherOverdue', 'late_history': 'lateHistory'}`.

Answers (all keys required by the page; a missing key keeps the current policy's value):

| key | type | maps to |
|---|---|---|
| `start` | `'now'` \| `'after_reviews'` \| `'recommend'` | `now`: mode `delegated`, `trackRecord.minReviewedCases` and `minAgreement` `None`. `after_reviews`: mode `delegated`, `minReviewedCases` 5, `minAgreement` `'0.8'`, `sources` `'live'`. `recommend`: mode `advisory`, track record unchanged. |
| `maxInvoice` | money text | `limits.maxDecisionExposure` |
| `maxCustomer` | money text | `limits.maxCustomerExposure` |
| `daysFromRequest` | int | `extensions.maxDaysFromRequest` |
| `daysPastOriginalDue` | int | `extensions.maxDaysPastOriginalDue` and `extensions.maxDays` |
| `allowOtherOverdue` | bool | `extensions.requireNothingElseOverdue = not value` |
| `lateHistory` | `'any'` \| `'some'` \| `'none'` | `extensions.maxPriorLateShare`: `None`, `'0.25'`, `'0'` |
| `holdCustomers` | list of customer ids | `restrictions.holdCustomers` |
| `agentDeclines` | bool | `autoDecline`: on with `maxExtensionDays = daysPastOriginalDue` and the other three lines `None`; or `{**AUTO_DECLINE_DEFAULT}` |

Always: `extensions.enabled = True`. Everything else (trial credit, exceptions, small overage, evidence, customers, feedback, paused, 30-day limit, unusual size) is copied from `current` unchanged.

- [ ] **Step 1: Write the failing tests.**

```python
CUR = delegation.validate_policy(delegation_demo.DEMO_POLICY, {'currency': 'AUD', 'scale': 2})
ANS = {'start': 'now', 'maxInvoice': '2,000.00', 'maxCustomer': ' 5000 ', 'daysFromRequest': 14, 'daysPastOriginalDue': 45, 'allowOtherOverdue': True,
       'lateHistory': 'some', 'holdCustomers': ['c9'], 'agentDeclines': True}
S = {'currency': 'AUD', 'scale': 2}

def test_every_answer_lands_on_its_setting(self):
    p = delegation.validate_policy(delegation.quick_setup_policy(ANS, CUR), S)
    self.assertEqual((p['mode'], p['trackRecord']['minReviewedCases'], p['trackRecord']['minAgreement']), ('delegated', None, None))
    self.assertEqual((p['limits']['maxDecisionExposure']['minorUnits'], p['limits']['maxCustomerExposure']['minorUnits']), ('200000', '500000'))
    e = p['extensions']
    self.assertEqual((e['enabled'], e['maxDays'], e['maxDaysFromRequest'], e['maxDaysPastOriginalDue'], e['requireNothingElseOverdue'], e['maxPriorLateShare']), (True, 45, 14, 45, False, '0.25'))
    self.assertEqual(p['restrictions']['holdCustomers'], ['c9'])
    self.assertEqual(p['autoDecline'], {'enabled': True, 'maxExtensionDays': 45, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None})

def test_the_three_starts(self):        # after_reviews -> (delegated, 5, '0.8', 'live'); recommend -> advisory with CUR's track record
def test_what_was_not_asked_is_kept(self):   # newCustomers, exceptions, smallOverage, evidence, customers, paused equal CUR's
def test_missing_answers_keep_the_current_values(self):   # quick_setup_policy({}, CUR) validates to the same digest as CUR
def test_answers_round_trip(self):      # quick_setup_answers(validated policy from ANS) == ANS with money as plain text '2000.00' / '5000.00'
def test_bad_money_is_a_field_error_from_validate(self):   # maxInvoice='-5' and 'abc' -> validate_policy raises with field 'limits.maxDecisionExposure'
def test_summary_says_what_the_agent_decides_and_what_comes_to_you(self):
    s = delegation.quick_setup_summary(delegation.validate_policy(delegation.quick_setup_policy(ANS, CUR), S), S, {'c9': 'Cityside Foods'})
    self.assertIn('A later payment date on an invoice of up to AUD 2,000.00', ' '.join(s['decides']))
    self.assertIn('up to 14 days after the day the customer asks', ' '.join(s['decides']))
    self.assertIn('Cityside Foods', ' '.join(s['comesToYou']))
    self.assertNotIn('first credit', ' '.join(s['comesToYou']))    # the demo policy has trial credit on
    off = {**CUR, 'newCustomers': {**CUR['newCustomers'], 'trialCredit': 'off'}}
    self.assertIn('Every first credit for a new customer.', delegation.quick_setup_summary(off, S, {})['comesToYou'])
```

Fill the one-line tests with assertions on the exact values named in their comments.

- [ ] **Step 2: Run** `... -m unittest test_quick_setup -v`. Expected: FAIL, functions not defined.

- [ ] **Step 3: Implement** the three functions and two maps. Money answers: strip spaces and thousands commas before handing to the policy body (the Control panel form does the same in the browser; do it here so the server accepts what the helper sends). `quick_setup_summary` sentences, in this order, each only when it applies:
  - decides: "A later payment date on an invoice of up to {maxInvoice}, when the customer would owe at most {maxCustomer} in total."; "The new date may be up to {n} days after the day the customer asks, and up to {m} days after the invoice's original due date."; "Also when the customer has other overdue invoices." / (else in comesToYou) "Any request from a customer with another overdue invoice."; "It may decline a request for more than {m} days when the assistant recommends declining."; with `advisory`: decides is the single sentence "Nothing yet: the agent only recommends, and you decide everything."; with `after_reviews`: first sentence is "Nothing until you have reviewed 5 of its recommendations and agreed with at least 80% of them. After that:".
  - comesToYou: "Anything over those limits."; late-history sentence for `'0'` and `'0.25'`; "Every request from: {names}." for held customers; "Every first credit for a new customer." when trial credit is off; one sentence per unasked setting that can send requests to the Owner and is set (30-day total, unusual size multiple, records confirmed complete above an amount), naming it and ending "(set on the Control panel)".

- [ ] **Step 4: Run** the tests. Expected: PASS.

- [ ] **Step 5: Commit** "Quick setup: answers to a policy, back again, and the plain summary".

---

### Task 4: The two endpoints

**Files:**
- Modify: `prototype/server.py` (two `App` methods next to `policy_presets` ~l.3086; two routes next to `/api/delegation/preferences/next` ~l.7802)
- Test: `prototype/test_quick_setup_api.py` (new; `DelegationCase`)

**Interfaces:**
- Consumes: Task 3 functions; `App.dg_request(..., received=None)`; `delegation.evaluate`.
- Produces: `GET /api/delegation/quick-setup` → `{'policy': <policy view as GET /api/delegation/policy gives>, 'answers': quick_setup_answers(current), 'customers': [{'id', 'name'}], 'amounts': {'median': <money view or None>, 'largest': <money view or None>}, 'openInvoices': int}`. `amounts` are over open invoices (amount owed > 0).
- Produces: `POST /api/delegation/quick-setup/preview` body `{'answers': {...}, 'days': int 1–365 (default 14)}` → `{'policy': <validated policy body, ready to PUT>, 'summary': {'decides', 'comesToYou'}, 'days': int, 'total': int, 'skipped': int, 'truncated': bool, 'counts': {'agent': int, 'owner': int, 'held': int}, 'reasons': [{'key', 'label', 'count', 'question' or None}], 'examples': {'agent': [...], 'owner': [...], 'held': [...]}}`. Each example: `{'customer': name, 'invoice': reference, 'amountText': str, 'reason': str or None}`; at most 3 per group.
- Both: Owner role only (403 `FORBIDDEN` otherwise). The POST also needs `person_required` and the CSRF header, like the other delegation POSTs. A validation error returns 400 `INVALID_INPUT` with `field` translated through `QUICK_FIELD` (the original field when it has no entry).

Preview rules:
- For each customer, each active invoice with an original due date: build the request for `requestedDueDate = as_of + days` with `received = as_of`. Leave out (count in `skipped`) an invoice with nothing owed, or whose current due date is on or after that date.
- Evaluate with the candidate policy `{**validated, 'version': current['version'] + 1, 'digest': policy_digest(validated)}`, recommendation `{'recommendation': 'approve', 'reasoning': 'Quick setup preview.'}`, `scorer=None`, `policy_seen=None`.
- Group: `autonomous_approve` → `agent`; `policy_hold` → `held`; everything else → `owner`.
- Reasons: every risk check with status `fail` or `unknown` (key and label from the check, `question` from `QUICK_CHECK`); a held customer adds key `held_customer`, label "The customer is on your never-decide list", question `holdCustomers`; a case with no failing check adds key `other` with label = the evaluation's `why`. Sort by count, largest first.
- Stop after 200 evaluated invoices and set `truncated`.

- [ ] **Step 1: Write the failing tests.**

```python
class QuickSetupApi(DelegationCase):
    def preview(self, answers, days=14, role='owner'):
        return self.call('/api/delegation/quick-setup/preview', {'answers': answers, 'days': days}, role, 'qs-' + hashlib.sha1(json.dumps([answers, days], sort_keys=True).encode()).hexdigest()[:12])[:2]

    def test_preview_counts_add_up_and_name_reasons(self):
        status, out = self.preview({**OPEN, 'daysPastOriginalDue': 1})          # OPEN: generous answers; 1 day total blocks every invoice
        self.assertEqual(status, 200); self.assertEqual(out['counts']['agent'], 0)
        self.assertEqual(sum(out['counts'].values()), out['total'])
        self.assertEqual((out['reasons'][0]['key'], out['reasons'][0]['question']), ('days_past_original_due', 'daysPastOriginalDue'))

    def test_generous_answers_let_the_agent_decide_some(self):
        self.assertGreater(self.preview(OPEN)[1]['counts']['agent'], 0)

    def test_preview_matches_a_real_request(self):
        out = self.preview(OPEN)[1]
        status, saved = self.put_policy({**out['policy'], 'expectedVersion': self.policy()['version']}); self.assertEqual(status, 200)
        ex = out['examples']['agent'][0]
        real = self.resolved(kind='extension', customerId=self.customer_id_of(ex['customer']), invoiceReference=ex['invoice'], days=None, requestedDueDate=(AS_OF + timedelta(days=14)).isoformat(), **APPROVE)
        self.assertEqual(real['handling'], 'autonomous_approve')

    def test_preview_writes_nothing(self):
        before = (self.counts(), self.policy()['version'], self.table_count('events'), self.table_count('notices'))
        self.preview(OPEN); self.preview({**OPEN, 'maxInvoice': 'abc'})
        self.assertEqual(before, (self.counts(), self.policy()['version'], self.table_count('events'), self.table_count('notices')))

    def test_a_bad_answer_names_the_question(self):
        status, body = self.preview({**OPEN, 'maxInvoice': 'abc'})
        self.assertEqual((status, body['error'], body['field']), (400, 'INVALID_INPUT', 'maxInvoice'))

    def test_held_customers_are_counted_as_held(self):   # holdCustomers=[bayview id] -> counts['held'] >= 1 and a reason with key 'held_customer'
    def test_staff_and_service_sessions_are_refused(self):   # role='staff' -> 403 FORBIDDEN on both endpoints
    def test_days_out_of_range(self):                    # days=0 and days=400 -> 400 INVALID_INPUT, field 'days'
    def test_get_gives_answers_customers_and_amounts(self):   # customers lists the six demo customers; amounts.largest['text'] is the largest open demo invoice; answers == quick_setup_answers(current)
    def test_no_open_invoices(self):                     # a workspace started with sample_data=False and no seed: total 0, counts all 0, reasons [], amounts None
```

`OPEN` = `{'start': 'now', 'maxInvoice': '100000', 'maxCustomer': '100000', 'daysFromRequest': 365, 'daysPastOriginalDue': 365, 'allowOtherOverdue': True, 'lateHistory': 'any', 'holdCustomers': [], 'agentDeclines': False}`. `table_count(name)` and `customer_id_of(name)` are small helpers in the test class (one SQL count; a lookup in `self.cust` / the records). `AS_OF` is the demo date 2026-10-24.

- [ ] **Step 2: Run** `... -m unittest test_quick_setup_api -v`. Expected: FAIL with 404.

- [ ] **Step 3: Implement** `App.quick_setup(self, actor)` and `App.quick_setup_preview(self, actor, body)` and the two routes. Take the lock the way `preference_next` does. Do not open a transaction.

- [ ] **Step 4: Run** the new tests and the whole suite. Expected: all pass.

- [ ] **Step 5: Commit** "Quick setup: figures endpoint and a read-only preview of an unsaved policy".

---

### Task 5: The Quick setup page

**Files:**
- Create: `prototype/web/quicksetup.js`
- Modify: `prototype/web/index.html` (script tag after `delegation.js`), `prototype/web/core.js` (route name for `#/quick-setup`; it is not added to `NAV`), `prototype/web/home.js` (`whereToStartHtml`, Owner step 1), `prototype/web/delegation.js` (one link above the presets), `prototype/web/app.css` (only if an existing class does not fit)
- Create: `deploy/quick_setup_page_check.py` (model: `deploy/review_decline_page_check.py`)

**Interfaces:**
- Consumes: both endpoints from Task 4; `PUT /api/delegation/policy` with `{...preview.policy, expectedVersion, note: 'Saved from Quick setup'}`.
- Produces: `PAGES['quick-setup']`; test ids `quick-setup-page`, `qs-assurances`, `qs-start`, `qs-q-<answer key>` (one per question), `qs-amount-choice`, `qs-preview`, `qs-count-agent`, `qs-count-owner`, `qs-count-held`, `qs-reason` (with `data-question`), `qs-summary`, `qs-save`, `qs-saved`, `qs-conflict`.

Page behaviour:
- Owner only; Staff see the same "Only the Owner…" message the Control panel shows.
- Prefilled from `answers`. Amount questions show two buttons (`qs-amount-choice`) with the median and the largest open invoice; clicking fills the field. No buttons when `amounts` are `None`.
- Held customers: a list of checkboxes by customer name.
- Any change calls the preview after 400 ms without typing. A field error shows under its question (`data-testid="qs-q-<key>"`) and keeps the last good preview, greyed.
- Preview heading: "If each customer asked today for {N} more days on each open invoice". N is a select: 7, 14, 30. Under it the line "An estimate: it assumes the assistant recommends approving."
- Each reason row is a button; clicking scrolls to and focuses its question. A reason with no question links to `#/delegation`.
- When `counts.agent` is 0 and `total` > 0, a callout: "With these answers the agent would decide none of these. Every request would come to you." 
- Assurances, exact copy: "Nucleon never contacts your customer." / "You can undo any decision the agent makes, on the Decide page." / "You can pause the agent at any time with one button on the Control panel."
- Save: PUT, then show `qs-saved` with links to the assistant (when `assistantHref()` gives one), `#/review` and `#/delegation`. On 409 `POLICY_CHANGED`: show `qs-conflict` ("The rules were changed somewhere else. Your answers are kept; check the preview and save again."), reload `expectedVersion`, keep the answers, run the preview again.
- Home step 1 becomes: "**Set the limits once.** Answer a few questions in [Quick setup](#/quick-setup) and see what the agent would do with your open invoices. The [Control panel](#/delegation) has every setting."
- Control panel link, above the presets: "New here? [Quick setup](#/quick-setup) asks a few questions and shows what they would do."

- [ ] **Step 1: Write the page check** `deploy/quick_setup_page_check.py` on the fictional scratch server, with these checks:
  - A1 the page loads for the Owner with the three assurances, and Staff get the owner-only message;
  - A2 the preview appears with three counts that add up to the total;
  - A3 setting `daysPastOriginalDue` to 1 makes `qs-count-agent` 0, shows the "decide none" callout, and the first `qs-reason` has `data-question="daysPastOriginalDue"`; clicking it focuses that field;
  - A4 clicking an amount choice fills the field and the preview changes;
  - A5 typing `abc` in the invoice amount shows an error under that question and no crash;
  - B1 Save stores a new version whose note is "Saved from Quick setup" (read through the API) and shows `qs-saved`;
  - B2 the Control panel then shows the same day limits in its form;
  - B3 conflict: save a policy through `S.owner(...)` behind the page's back, click Save: `qs-conflict` appears, the answers are still in the fields, a second Save succeeds;
  - C1 Home's first step links to `#/quick-setup`; the Control panel has the link;
  - C2 at phone width there is no horizontal scroll (`p.phone()`, `p.no_hscroll()`).

- [ ] **Step 2: Run** it. Expected: FAIL at A1 (page not found).

- [ ] **Step 3: Implement** the page and the links, following the patterns of `setup.js` and `delegation.js` (`pageHead`, `field`, `radios`, `formError`, `showErrors`, `api`, `busy`, `toast`).

- [ ] **Step 4: Run** `quick_setup_page_check.py`, `delegation_page_check.py`, `review_decline_page_check.py` and `home_page_check.py`. Expected: the first three all PASS; `home_page_check.py` has the same 3 old failures (A4, D3) and no new one.

- [ ] **Step 5: Commit** "Quick setup page: questions, live preview on the Owner's own invoices, plain summary".

---

### Task 6: Records of the change, and the final check

**Files:**
- Modify: `docs/KNOWN-LIMITATIONS.md` (the preview is an estimate; the agent-decline line still counts from the current due date; no Vietnamese text), `docs/DECISIONS.md` (one entry: Quick setup beside the Control panel; day limits counted three ways; no LLM in setup)

- [ ] **Step 1:** Add the entries, in the style of the entries already there.
- [ ] **Step 2:** Run the whole unit suite, the lab tests (`~/Developer/nucleon-local/venv/bin/python -m unittest discover -s lab/tests -q` from the repo root) and the four page checks of Task 5. Expected: as in Task 5, nothing new failing.
- [ ] **Step 3:** Commit "Docs: Quick setup and the day limits".
- [ ] **Step 4:** Stop. Report what passed. Deployment to NTK waits for the user's word.
