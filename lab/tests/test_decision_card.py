"""The decision card (lab/card.py: assessDecision, resolveDecision, decisionStatus) from REAL results of the records (fixtures/decision_card/*.json, made by
make_decision_card_fixtures.py; fictional data, business date Sat 24 Oct 2026). The badge is chosen from the backend's status and handling only; an assessment is a
preview and never claims a decision; the dates are exactly the backend's; the one button exists only for a case gathering evidence with a valid action id on a
contract URL; comparables are labelled as analogies; nothing is escaped wrongly and no token is in the HTML. Also the MCP annotations of the three tools."""
import html
import json
import re
import unittest
from copy import deepcopy
from pathlib import Path

from lab import card
from lab.mcp_server import ACTS, NON_DESTRUCTIVE, READ_ONLY, annotations_for, exposed
from test_card import Page

FIX = Path(__file__).resolve().parent / 'fixtures' / 'decision_card'
ISOLATED = 'http://127.0.0.1:18631'
SENT = 'Nucleon sent nothing to the customer. Staff informs the customer.'


def fixture(name):
    return json.loads((FIX / (name + '.json')).read_text())


def page(result, tool='resolveDecision', url=ISOLATED):
    return Page(card.card_html(tool, result, url))


class BadgeTests(unittest.TestCase):
    def badge(self, result, tool='resolveDecision'):
        p = Page(card.card_html(tool, result, ISOLATED))
        return card.decision_badge(result)[1], p.text

    def test_each_backend_state_has_its_own_badge_and_nothing_else_is_claimed(self):
        cases = [('decided_extension', 'resolve', 'APPROVED UNDER OWNER POLICY v1 — DECIDED BY AGENT'), ('decided_trial', 'resolve', 'APPROVED UNDER OWNER POLICY v1 — DECIDED BY AGENT'),
                 ('gathering', 'resolve', 'INFORMATION NEEDED FROM STAFF'), ('owner_review_trial', 'resolve', 'WITH THE OWNER FOR REVIEW'),
                 ('owner_review_extension', 'resolve', 'WITH THE OWNER FOR REVIEW'), ('incomplete', 'resolve', 'WITH THE OWNER FOR REVIEW'),
                 ('overridden', 'status', 'APPROVAL OVERRIDDEN BY THE OWNER')]
        for name, key, want in cases:
            badge, text = self.badge(fixture(name)[key], 'decisionStatus' if key == 'status' else 'resolveDecision')
            self.assertEqual(badge, want, name)
            self.assertIn(want, text)

    def test_the_status_tool_shows_the_same_badge_as_the_resolve_that_made_the_case(self):
        d = fixture('decided_extension')
        self.assertEqual(card.decision_badge(d['status'])[1], card.decision_badge(d['resolve'])[1])
        g = fixture('gathering')
        self.assertEqual(card.decision_badge(g['status'])[1], card.decision_badge(g['resolve'])[1])

    def test_on_hold_and_closed_and_the_owner_decided_and_an_unknown_state(self):
        base = fixture('owner_review_trial')['resolve']
        self.assertEqual(card.decision_badge({**base, 'status': 'on_hold'})[1], 'ON HOLD BY POLICY')
        self.assertEqual(card.decision_badge({**base, 'status': 'closed'})[1], 'CLOSED — NOTHING APPROVED')
        decided = {**base, 'status': 'decided', 'decision': {'by': 'owner', 'outcome': 'decline'}}
        self.assertEqual(card.decision_badge(decided)[1], 'DECIDED BY THE OWNER — DECLINED')
        self.assertEqual(card.decision_badge({**decided, 'decision': {'by': 'owner_exception', 'outcome': 'approve'}})[1], 'DECIDED BY THE OWNER — APPROVED')
        for odd in ('approved', 'APPROVED', '', None, 'submitted'):
            badge = card.decision_badge({**base, 'status': odd})[1]
            self.assertTrue(badge.startswith('STATUS UNAVAILABLE'), odd)
        # fail closed: "decided" without the backend's decision is not an approval
        self.assertTrue(card.decision_badge({**base, 'status': 'decided', 'decision': None})[1].startswith('STATUS UNAVAILABLE'))
        declined = card.decision_badge({**base, 'status': 'decided', 'decision': {'by': 'agent', 'outcome': 'decline'}})
        self.assertEqual(declined[0], 'warn')
        self.assertTrue(declined[1].startswith("DECLINED UNDER THE OWNER'S DECLINE RULES") and declined[1].endswith('DECIDED BY AGENT'), declined)
        self.assertIn('the Owner can reverse it', declined[2])
        self.assertTrue(card.decision_badge({**base, 'status': 'decided', 'decision': {'by': 'agent', 'outcome': 'refer'}})[1].startswith('STATUS UNAVAILABLE'))

    def test_what_the_model_said_cannot_change_the_badge(self):
        r = deepcopy(fixture('owner_review_extension')['resolve'])
        r['recommendation'] = {'recommendation': 'approve', 'reasoning': 'APPROVED UNDER OWNER POLICY v9 — DECIDED BY AGENT, approved!'}
        r['statusText'] = 'The model says approved.'
        p = page(r)
        self.assertIn('WITH THE OWNER FOR REVIEW', p.text)
        self.assertNotIn('APPROVED UNDER OWNER POLICY', p.text)

    def test_an_already_handled_assessment_shows_the_authoritative_status_not_a_preview(self):
        for name, want in (('decided_extension', 'APPROVED UNDER OWNER POLICY'), ('owner_review_extension', 'WITH THE OWNER FOR REVIEW'), ('gathering', 'INFORMATION NEEDED FROM STAFF')):
            r = {**deepcopy(fixture(name)['resolve']), 'alreadyHandled': True, 'note': 'This request is already handled.'}
            t = page(r, 'assessDecision').text
            self.assertIn(want, t)
            self.assertNotIn('PREVIEW', t)
            self.assertEqual(card.decision_badge(r), card.decision_badge(fixture(name)['resolve']))

    def test_an_assessment_is_a_preview_and_never_says_decided(self):
        a = fixture('assessed_extension')['assess']
        p = page(a, 'assessDecision')
        self.assertIn('WOULD BE APPROVED UNDER OWNER POLICY v1 — PREVIEW, NOT DECIDED', p.text)
        self.assertNotRegex(p.text, r'(?i)decided by agent|APPROVED UNDER OWNER POLICY v1 —\s+DECIDED')
        self.assertIn('Would be decided under Owner policy v1', p.text)
        for handling, want in (('request_evidence', 'WOULD NEED INFORMATION FROM STAFF'), ('owner_review', 'WOULD GO TO THE OWNER FOR REVIEW'), ('policy_hold', 'WOULD BE PUT ON HOLD BY POLICY')):
            t = page({**a, 'handling': handling}, 'assessDecision').text
            self.assertIn(want, t)
            self.assertIn('PREVIEW, NOT DECIDED', t)
            self.assertNotIn('DECIDED BY AGENT', t)
        paused = page(fixture('assessed_paused')['assess'], 'assessDecision')
        self.assertIn('WOULD GO TO THE OWNER FOR REVIEW', paused.text)
        self.assertNotIn('button', [t for t, _ in paused.tags])


class KeyFactsTests(unittest.TestCase):
    def test_extension_dates_are_the_backends_in_chronological_order_with_the_derived_lines(self):
        r = fixture('decided_extension')['resolve']
        facts = r['keyFacts']
        p = page(r)
        for label, key in (('Original due date', 'originalDueDate'), ('As-of date', 'asOfDate'), ('Requested due date', 'requestedDueDate')):
            self.assertIn(label + ' ' + facts[key + 'Text'], p.text)
        self.assertNotIn('Current due date', p.text)   # the same as the original: not repeated
        rows = re.findall(r'<span class="v">([^<]*)</span>', card.card_html('resolveDecision', r, ISOLATED))
        self.assertEqual(rows, [facts[k + 'Text'] for k in ('originalDueDate', 'asOfDate', 'requestedDueDate')])   # the backend's own words, oldest first
        self.assertIn('+23 days past the current due date', p.text)
        self.assertIn('6 days overdue as of ' + facts['asOfDateText'], p.text)
        self.assertIn('Amount owed: ' + facts['amountText'], p.text)
        self.assertIn('AUD 480.00 (stated as of', p.text)

    def test_a_current_due_date_that_differs_is_listed_and_the_rows_stay_in_date_order(self):
        r = deepcopy(fixture('decided_extension')['resolve'])
        f = r['keyFacts']
        f['currentDueDate'], f['currentDueDateText'] = '2026-10-30', 'Fri 30 Oct 2026'
        rows = card.date_rows(f)
        self.assertEqual([x[2] for x in rows], ['2026-10-18', '2026-10-24', '2026-10-30', '2026-11-10'])
        self.assertIn('Current due date Fri 30 Oct 2026', page(r).text)

    def test_the_timeline_has_pins_in_proportion_dates_on_the_marks_and_the_extension_and_overdue_spans(self):
        r = fixture('decided_extension')['resolve']
        html_ = card.card_html('resolveDecision', r, ISOLATED)
        tl = re.search(r'<div class="tl"[^>]*>(.*?)</div>\s*(?:<div class="facts">|$)', html_, re.S).group(1)
        lefts = [int(x) for x in re.findall(r'class="pin m\d" style="left:(\d+)%"', tl)]
        self.assertEqual(lefts, sorted(lefts))
        self.assertEqual((lefts[0], lefts[-1]), (0, 100))
        self.assertEqual(lefts[1], round(100 * 6 / 23))   # 18 Oct, 24 Oct, 10 Nov: day 0, day 6, day 23
        self.assertEqual(re.findall(r'<b>([^<]*)</b>', tl), ['18 Oct', '24 Oct', '10 Nov'])   # the dates are written on the marks
        self.assertEqual(re.findall(r'<span>([^<]*)</span>', tl), ['Original due', 'As of', 'Requested'])
        self.assertIn('class="mark above edge-l"', tl)   # the first mark hugs the left edge, the second sits below the axis, the last hugs the right edge
        self.assertIn('class="mark below"', tl)
        self.assertIn('class="mark above edge-r"', tl)
        self.assertIn('class="span ext approved" style="left:0%;width:100%"', tl)   # due date to requested due date, green: this fixture is decided and approved
        assessed = {**r, 'status': 'assessed', 'decision': None}
        self.assertIn('class="span ext pending"', card.card_html('assessDecision', assessed, ISOLATED))   # nothing decided yet: orange
        over = {**r, 'decision': {**(r.get('decision') or {}), 'overridden': True}}
        self.assertIn('class="span ext declined"', card.card_html('resolveDecision', over, ISOLATED))   # overridden: hollow
        self.assertIn('class="span late" style="left:0%;width:26%"', tl)   # due date to the as-of date: overdue
        self.assertIn('aria-hidden="true"', html_)
        self.assertEqual(len(re.findall(r'class="r"', html_)), 3)   # one text row per date
        one = {'kind': 'extension', 'asOfDate': '2026-10-24', 'asOfDateText': 'Sat 24 Oct 2026'}
        self.assertNotIn('class="tl"', card.date_bar(card.date_rows(one)))   # a single date has no timeline
        same = card.date_bar([('A', 'x', '2026-10-24'), ('B', 'y', '2026-10-24')])
        self.assertEqual(re.findall(r'pin m\d" style="left:(\d+)%', same), ['50', '50'])
        self.assertNotIn('class="span', same)   # no due or requested date: nothing to fill

    def test_trial_credit_facts_and_how_the_deposit_was_verified(self):
        p = page(fixture('decided_trial')['resolve'])
        for want in ('Order amount: AUD 800.00', 'Verified deposit: AUD 200.00',
                     'Deposit source: AUD 200.00 — a recorded payment in Nucleon Records; reference DEP-NS-01, received Fri 23 Oct 2026', 'Deposit share: 0.25',
                     'Exposure (order less verified deposit): AUD 600.00', 'Terms: 14 days', 'Due date if approved: Sat 7 Nov 2026 (as-of date + terms)'):
            self.assertIn(want, p.text)
        g = page(fixture('gathering')['resolve'])
        self.assertIn('Verified deposit: AUD 0.00 — none verified', g.text)

    def test_each_deposit_level_is_shown_in_words_and_a_staff_check_is_never_called_a_recorded_payment(self):
        checked = page(fixture('decided_staff_checked')['resolve'])
        self.assertIn('Deposit source: AUD 150.00 — checked by Staff in the bank account (not a recorded payment); reference DEP-LK-02', checked.text)
        self.assertIn('Deposit source: AUD 150.00 — reported by the customer, not verified; reference DEP-LK-01', checked.text)
        self.assertIn('does not count towards the deposit', checked.text)
        self.assertNotIn('a recorded payment in Nucleon Records; reference DEP-LK', checked.text)
        said = page(fixture('gathering_customer_said')['resolve'])   # the customer's word alone: shown, never verified
        self.assertIn('Verified deposit: AUD 0.00 Deposit source: AUD 150.00 — reported by the customer, not verified', said.text)
        self.assertIn('reported by the customer, not verified', said.text)
        self.assertIn('INFORMATION NEEDED FROM STAFF', said.text)
        self.assertNotIn('DECIDED BY AGENT', said.text)
        r = deepcopy(fixture('decided_staff_checked')['resolve'])
        r['keyFacts']['depositSources'][0]['text'] = 'AUD 150.00 — <b>x</b> & "y"'
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', card.decision_card_html('resolveDecision', r, ISOLATED))   # the backend's words are escaped like every other text

    def test_an_overridden_case_says_what_the_override_does_not_undo(self):
        for name in ('overridden', 'overridden_trial'):
            r = fixture(name)['status']
            p = page(r, 'decisionStatus')
            self.assertIn('APPROVAL OVERRIDDEN BY THE OWNER', p.text)
            self.assertIn("This reverses Nucleon's internal decision only. Nucleon sent nothing to the customer; if Staff already told the customer or acted on it outside Nucleon, "
                          "that is not undone — Staff must follow up.", p.text)
            self.assertEqual('Amounts already invoiced under this credit remain owed.' in p.text, name == 'overridden_trial')
        # an overridden result without the backend's sentence still says it; a case that is not overridden carries no such box
        bare = deepcopy(fixture('overridden')['status'])
        del bare['externalEffects']
        self.assertIn('Staff must follow up', page(bare, 'decisionStatus').text)
        self.assertNotIn('does not undo', page(fixture('decided_extension')['resolve']).text)

    def test_warnings_and_unknown_amounts_are_shown_never_as_zero(self):
        r = fixture('incomplete')['resolve']
        p = page(r)
        self.assertIn('Warnings', p.text)
        for w in r['warnings']:
            self.assertIn(w, p.text)
        r2 = deepcopy(r)
        r2['keyFacts']['amountOwed'] = None
        r2['keyFacts']['amountText'] = None
        r2['keyFacts']['amountMark'] = None
        self.assertIn('Amount owed: Not recorded', page(r2).text)
        self.assertNotIn('AUD 0.00', page(r2).text)
        r3 = deepcopy(r)
        r3['keyFacts']['daysOverdueAsOf'], r3['keyFacts']['daysOverdueNote'] = None, 'needs the current due date'
        self.assertIn('Days overdue: needs the current due date', page(r3).text)


class DimensionTests(unittest.TestCase):
    def test_three_dimensions_with_the_simulation_label_and_the_sample_size(self):
        r = fixture('decided_extension')['resolve']
        p = page(r)
        self.assertIn('Evidence — sufficient', p.text)
        self.assertIn('Business risk — within', p.text)
        self.assertIn('Track record — established', p.text)
        self.assertIn('Dataset: fictional evaluation set (simulation).', p.text)
        e = r['reliability']['evaluation']
        self.assertIn('Sample: the policy would approve %d of %d reviewed cases; the Owner approved %d of them.' % (e['wouldApprove'], e['reviewed'], e['ownerApproved']), p.text)
        self.assertIn('Another customer\'s reviewed case', p.text)

    def test_up_to_three_comparables_each_an_analogy_and_fictional_ones_say_so(self):
        r = deepcopy(fixture('decided_extension')['resolve'])
        self.assertGreaterEqual(len(r['comparables']), 4)
        p = page(r)
        self.assertEqual(p.text.count("Another customer's reviewed case — analogy, not this customer's history"), 3)
        self.assertEqual(p.text.count("analogy, not this customer's history — fictional"), 3)
        r['comparables'][0].update(sameCustomer=True, fictional=False)
        t = page(r).text
        self.assertIn("This customer's earlier case", t)
        self.assertEqual(t.count("analogy, not this customer's history"), 2)
        self.assertNotIn('Comparable cases', page({**r, 'comparables': []}).text)
        self.assertNotIn('ownerReason', json.dumps(r['comparables']))   # a staff result never carries the Owner's reasons, so the card cannot show them

    def test_the_authority_line_and_nothing_sent(self):
        self.assertIn('Decided under Owner policy v1', page(fixture('decided_extension')['resolve']).text)
        for name in ('owner_review_trial', 'incomplete'):
            self.assertIn('The Owner decides', page(fixture(name)['resolve']).text)
        only_if = 'Approved under Owner policy v1 only if the information confirms it; otherwise the Owner decides'
        self.assertIn(only_if, page(fixture('gathering')['resolve']).text)
        self.assertIn(only_if, page({**fixture('gathering')['resolve'], 'status': 'assessed', 'stored': False}, 'assessDecision').text)

    def test_the_recommendation_is_labelled_in_the_assistants_own_terms(self):
        r = deepcopy(fixture('gathering')['resolve'])
        r['recommendation'] = {'recommendation': 'approve_if_verified', 'reasoning': 'x', 'text': 'The assistant recommended approval once the information is confirmed'}
        self.assertIn('The assistant recommended approval once the information is confirmed', page(r).text)

    def test_the_first_reason_is_shown_under_the_badge_unless_decided(self):
        r = fixture('owner_review_trial')['resolve']
        self.assertIn('Why: ' + r['reasons'][0], page(r).text)
        self.assertIn(r['statusText'], page(r).text)
        self.assertNotIn('Why:', page(fixture('decided_trial')['resolve']).text)
        for name, key in (('decided_extension', 'resolve'), ('assessed_extension', 'assess'), ('overridden', 'status')):
            self.assertIn(SENT, page(fixture(name)[key], 'decisionStatus').text)


class ButtonTests(unittest.TestCase):
    def test_the_button_exists_only_for_a_case_gathering_evidence_with_a_valid_action_id_on_a_contract_url(self):
        g = fixture('gathering')['resolve']
        act = g['actionId']
        p = page(g)
        buttons = [a for t, a in p.tags if t == 'button']
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]['data-url'], ISOLATED + '/#/actions/' + act)
        self.assertIn('Provide information in Nucleon', p.text)
        self.assertEqual(len(p.scripts), 2)   # the fixed size script and the fixed click script: the url is in a data attribute only
        self.assertNotIn(act, ''.join(p.scripts))
        for url in (None, '', 'https://evil.example', 'http://127.0.0.1:8632', ISOLATED + '/x', 'http://127.0.0.1:18631@evil.example', ISOLATED + '?q=1', 'javascript:alert(1)'):
            self.assertNotIn('button', [t for t, _ in page(g, url=url).tags], url)
        for bad in ('act_xyz', 'act_' + 'g' * 16, 'ACT_' + '0' * 16, act + 'x', '', None, 'act_0123456789abcdef"><script>', '../' + act):
            self.assertNotIn('button', [t for t, _ in page({**g, 'actionId': bad}).tags], bad)
        self.assertEqual(len([t for t, _ in page(g, url='http://127.0.0.1:8631').tags if t == 'button']), 1)

    def test_no_button_for_any_other_state_nor_for_an_assessment(self):
        g = fixture('gathering')['resolve']
        for name, key in (('decided_extension', 'resolve'), ('decided_trial', 'resolve'), ('owner_review_trial', 'resolve'), ('owner_review_extension', 'resolve'),
                          ('incomplete', 'resolve'), ('assessed_extension', 'assess'), ('assessed_paused', 'assess'), ('overridden', 'status')):
            self.assertNotIn('button', [t for t, _ in page(fixture(name)[key]).tags], name)
        for change in ({'status': 'awaiting_owner'}, {'status': 'decided'}, {'status': 'on_hold'}, {'handling': 'owner_review'}, {'evidenceLink': False}, {'evidenceLink': None}, {'stored': False}):
            self.assertNotIn('button', [t for t, _ in page({**g, **change}).tags], change)
        self.assertNotIn('button', [t for t, _ in page(g, tool='assessDecision', url=None).tags])

    def test_the_button_text_is_fixed_and_no_token_is_in_the_page(self):
        g = fixture('gathering')['resolve']
        raw = card.card_html('resolveDecision', {**g, 'token': 'secret-token-123', 'csrf': 'abc'}, ISOLATED)
        self.assertNotIn('secret-token-123', raw)
        self.assertNotRegex(raw, r'(?i)bearer|csrf|cookie|idempotency')
        self.assertIn(html.escape(card.CLICK_HASH), raw)
        self.assertIn(html.escape(card.SCRIPT_HASH), raw)
        self.assertNotIn('<form', raw)


class EscapingTests(unittest.TestCase):
    def test_every_string_from_the_result_is_escaped(self):
        evil = '<script>alert(1)</script><img src=x onerror=alert(2)>"\''
        r = deepcopy(fixture('gathering')['resolve'])
        r['customer']['name'] = evil
        r['statusText'] = evil
        r['warnings'] = [evil]
        r['needs'] = [evil]
        r['keyFacts']['orderAmount']['text'] = evil
        r['evidence']['items'][0]['detail'] = evil
        r['risk']['checks'][0]['sentence'] = evil
        r['comparables'] = [{'summary': evil, 'ownerDecision': 'approve', 'outcome': evil, 'fictional': True}]
        raw = card.card_html('resolveDecision', r, ISOLATED)
        self.assertNotIn('<script>alert', raw)
        self.assertNotIn('<img', raw)
        self.assertEqual(raw.count('<script>'), 2)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', raw)

    def test_a_result_without_key_facts_has_no_card(self):
        for bad in (None, [], {}, {'keyFacts': 'x'}):
            with self.assertRaises(ValueError):
                card.card_html('assessDecision', bad, ISOLATED)

    def test_the_same_result_gives_the_same_bytes_and_a_stable_uri(self):
        r = fixture('decided_trial')['resolve']
        self.assertEqual(card.card_html('resolveDecision', r, ISOLATED), card.card_html('resolveDecision', r, ISOLATED))
        self.assertEqual(card.card_uri('resolveDecision', r), 'ui://nucleon/card/resolveDecision/' + r['caseId'])
        self.assertEqual(card.card_uri('assessDecision', fixture('assessed_extension')['assess']), 'ui://nucleon/card/assessDecision/customer_demo_bayview')

    def test_financial_and_action_cards_are_unchanged(self):
        self.assertEqual(card.FINANCIAL_CARDS, ('customerOverview', 'invoices'))
        self.assertEqual(card.ACTION_CARDS, ('prepareRequest', 'actionStatus'))
        self.assertEqual(card.CARD_TOOLS, card.FINANCIAL_CARDS + card.ACTION_CARDS + card.DECISION_CARDS)


class ForModelTests(unittest.TestCase):
    """S1b adds `forModel` (the compact result the model reads) and, on a refused call, `hint` beside the full result: the card renders the same page with or without them."""
    FOR_MODEL = {'status': 'decided', 'handling': 'autonomous_approve', 'statusText': 'x', 'why': '', 'nextStep': 'Tell the customer yourself; Nucleon sent nothing.', 'keyFacts': {'customer': 'C'}}

    def test_every_fixture_renders_identically_with_a_forModel_beside_the_full_result(self):
        for path in sorted(FIX.glob('*.json')):
            for key, result in json.loads(path.read_text()).items():
                tool = 'decisionStatus' if key == 'status' else 'assessDecision' if key == 'assess' else 'resolveDecision'
                plain = card.card_html(tool, deepcopy(result), ISOLATED)
                self.assertEqual(plain, card.card_html(tool, {**deepcopy(result), 'forModel': self.FOR_MODEL}, ISOLATED), path.name + ' ' + key)


class AnnotationTests(unittest.TestCase):
    def test_assess_and_status_are_read_only_resolve_is_neither_read_only_nor_destructive_hinted(self):
        self.assertTrue({'assessDecision', 'decisionStatus'} <= READ_ONLY)
        self.assertNotIn('resolveDecision', READ_ONLY)
        self.assertNotIn('resolveDecision', NON_DESTRUCTIVE)
        for name in ('assessDecision', 'decisionStatus'):
            a = annotations_for(name)
            self.assertEqual((a.read_only_hint, a.open_world_hint), (True, False))
        a = annotations_for('resolveDecision')
        self.assertEqual((a.read_only_hint, a.open_world_hint, a.destructive_hint), (False, False, None))

    def test_the_registry_decides_what_is_exposed_resolve_is_an_allowed_act_and_nothing_else_new_is(self):
        self.assertIn('resolveDecision', ACTS)
        registry = {'tools': [{'name': n, 'kind': k} for n, k in (('assessDecision', 'read'), ('decisionStatus', 'read'), ('resolveDecision', 'act'), ('openRequest', 'act'),
                                                                   ('actWithinAuthority', 'act'), ('setPolicy', 'act'))]}
        self.assertEqual([t['name'] for t in exposed(registry)], ['assessDecision', 'decisionStatus', 'resolveDecision'])
        self.assertEqual(exposed({'tools': []}), [])


if __name__ == '__main__':
    unittest.main()
