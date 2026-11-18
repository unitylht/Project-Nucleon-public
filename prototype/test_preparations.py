"""The decision a case has prepared as a versioned proposal with a status (current, superseded, withdrawn, confirmed): a revision keeps
what it does not change, a stale version is never confirmed, and the history is the owner's alone. Also the case's due dates (due now,
originally due), the ordinal and the duplicate flag of a second open request on one invoice, staff concerns, and the needs step's own
"still holds?" check of what the owner said earlier. All data is fictional; no real model is called."""
import json
import re
import unittest
from datetime import timedelta

from agent import calendar_date, display_date
from coordinator import known_text, said_reason
from server import NO_REASON, queue_why, waiting_on
from test_agent import ISO_MESSAGE
from test_demo import DemoCase
from test_helpers import NAMED, SHARED, Recording
from test_situation import SituationCase
import test_tool_surface   # its helpers only: the module, so its tests are not collected here again

EVENT = 'they have an event next month'
WORRY = "I'm worried about this one: they sounded unsure on the phone."
EXPECTS = 'They have an event next month and should recover'   # the expectation line of NAMED


class AsksAboutTheEvent(Recording):
    """The mock, whose needs step also asks about the owner's expectation, quoting it: the case cites that line."""
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        out = super().respond(task, messages, tools, schema, timeout)
        if task == 'plan_needs':
            out.value['needs'].append({'need': 'Whether the event bears on this', 'why': 'It bears on whether a later date suits them.', 'from': 'owner',
                                       'kind': 'recommend', 'answeredBy': None, 'question': 'You said "' + EXPECTS + '". Does it bear on this request?'})
        return out


class PreparationTests(SituationCase):
    T = test_tool_surface.ToolSurfaceTests
    case, bayside_subject = T.case, T.bayside_subject

    def prepare(self, message, key, **args):
        return self.ok('prepareDecision', key=key, message=message, requestId=self.r['id'], **args)

    def confirm(self, p, key):
        """The Confirm decision button for preparation p: the case as it stands now, with p's values and version."""
        c = self.case()
        shown = (c.get('preparedDecision') or {}).get('suggestionShown')
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': p['outcome'], 'approvedDueDate': p['approvedDueDate'], 'reason': p['reason'], 'preparedVersion': p['version'],
                **({'suggestionShown': shown} if shown else {})}
        return self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', key)

    def statuses(self, role='owner'):
        return [(x['version'], x['status'], x.get('replacedBy')) for x in self.case(role)['preparations']]

    def test_a_revision_keeps_what_it_does_not_change(self):   # Review Focus 1
        first = self.prepare('approve 14 days, ' + EVENT, 'p1', outcome='approve', days=14, reason=EVENT)
        self.assertEqual((first['prepared']['version'], first['prepared']['reason'], first['revisionOf'], first['retained']), (1, EVENT, None, []))
        # only the days: the outcome and the reason are kept; the days are in the message
        second = self.prepare('make that ten days instead, keep the same reason', 'p2', days=10)
        p = second['prepared']
        self.assertEqual((p['version'], p['outcome'], p['approvedDueDate'], p['days'], p['reason']), (2, 'approve', '2026-10-30', 10, EVENT))
        self.assertEqual((second['revisionOf'], second['retained']), (1, ['outcome', 'reason']))
        # the current reason passed through: kept, though the message does not say it
        third = self.prepare('keep the same reason, but make it a week', 'p3', outcome='approve', days=7, reason=EVENT)
        self.assertEqual((third['prepared']['reason'], third['prepared']['days'], third['retained']), (EVENT, 7, ['reason']))
        # only a reason: the days are kept, and a new reason in the owner's words replaces the old one
        fourth = self.prepare('the reason is that they paid early last time', 'p4', reason='they paid early last time')
        p = fourth['prepared']
        self.assertEqual((p['approvedDueDate'], p['days'], p['reason'], fourth['retained']), ('2026-10-27', 7, 'they paid early last time', ['outcome', 'days']))
        # a reason in the message that says nothing more than the decision is no new reason: the current one is kept
        fifth = self.prepare('approve ten days', 'p5', days=10, reason='approve ten days')
        self.assertEqual((fifth['prepared']['reason'], fifth['prepared']['days'], fifth['retained']), ('they paid early last time', 10, ['outcome', 'reason']))
        # a reason in neither place is no reason, as before
        sixth = self.prepare('approve a week', 'p6', outcome='approve', days=7, reason='they are a good customer')
        self.assertEqual((sixth['prepared']['reason'], sixth['retained']), (NO_REASON, []))
        # a supplied day count is still grounded in the message: nothing is prepared, and the current one stays
        missing = self.prepare('keep it as it is but longer', 'p7', days=21)
        self.assertEqual((missing['missing'], 'prepared' in missing), ('days', False))
        self.assertEqual(self.statuses(), [(n, 'superseded', n + 1) for n in range(1, 6)] + [(6, 'current', None)])
        c = self.case()
        self.assertEqual([e['data']['version'] for e in c['history'] if e['kind'] == 'decision.superseded'], [1, 2, 3, 4, 5])
        self.assertEqual((c['preparedDecision']['version'], c['preparations'][-1]['approvedDueDateText']), (6, 'Tue 27 Oct 2026'))

    def test_a_date_said_implies_approve_a_decline_must_be_said_and_a_revision_keeps_the_outcome(self):
        days = {'requestId': self.r['id'], 'missing': 'days', 'ask': 'How many days, or until which date?', 'subject': self.bayside_subject()}
        # nothing prepared and no days or date: asked for them, whether or not the model passed approve
        self.assertEqual([self.prepare('yes, go ahead', 'y' + str(n), **args) for n, args in enumerate(({}, {'outcome': 'approve'}))], [days, days])
        # a decline is never inferred: not said, it is asked; with a date it is refused
        self.assertEqual(self.prepare('make it so', 'd0', outcome='decline'),
                         {'requestId': self.r['id'], 'missing': 'outcome', 'ask': 'Approve or decline?', 'subject': self.bayside_subject()})
        self.assertEqual(self.refused('prepareDecision', key='d1', message='decline 10 days', outcome='decline', days=10, requestId=self.r['id']), 'INVALID_ARGUMENT')
        self.assertNotIn('preparedDecision', self.case())
        # a grounded day count is an approval (the only outcome with a date), with or without approve words or an outcome passed
        said = 'Go with the fortnight, reason: they are a steady customer and a fortnight is harmless. Leave it for me to confirm.'
        first = self.prepare(said, 'p1', outcome='approve', days=14, reason='they are a steady customer and a fortnight is harmless')
        p = first['prepared']
        self.assertEqual((p['version'], p['outcome'], p['approvedDueDate'], p['reason'], first['revisionOf']),
                         (1, 'approve', '2026-11-03', 'they are a steady customer and a fortnight is harmless', None))
        second = self.prepare('make that ten days', 'p2', days=10)   # a revision keeps the outcome
        self.assertEqual((second['prepared']['outcome'], second['prepared']['days'], second['retained']), ('approve', 10, ['outcome', 'reason']))
        third = self.prepare('decline it', 'p3', outcome='decline')
        self.assertEqual((third['prepared']['outcome'], third['prepared']['approvedDueDate'], third['retained']), ('decline', None, ['reason']))
        self.assertEqual(self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])['withdrawn'], True)
        fourth = self.prepare('two weeks then', 'p4', days=14)   # nothing current, no outcome passed: the days say approve
        self.assertEqual((fourth['prepared']['outcome'], fourth['prepared']['approvedDueDate'], fourth['retained']), ('approve', '2026-11-03', []))

    def test_a_reason_said_for_an_earlier_preparation_is_kept_when_passed_again(self):
        self.prepare('approve 14 days, ' + EVENT, 'p1', outcome='approve', days=14, reason=EVENT)
        self.assertEqual(self.prepare('make that ten days', 'p2', days=10)['reasonFrom'], 1)   # kept from the current one
        self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])
        # nothing current: the earlier reason, passed again in other case and spacing, is the owner's, from the latest version that had it
        said = "Right, prepare the fortnight once more, same reason, and I'll confirm it."
        again = self.prepare(said, 'p3', outcome='approve', days=14, reason='They have an  event next month')
        p = again['prepared']
        self.assertEqual((p['version'], p['approvedDueDate'], p['reason'], again['revisionOf'], again['retained'], again['reasonFrom']),
                         (3, '2026-11-03', EVENT, None, ['reason'], 2))
        # a reason never said in a message nor for any preparation of this case is no reason
        self.ok('withdrawPreparation', key='w2', requestId=self.r['id'])
        never = self.prepare(said, 'p4', outcome='approve', days=14, reason='they always pay in the end')
        self.assertEqual((never['prepared']['reason'], never['retained'], never['reasonFrom']), (NO_REASON, [], None))

    def test_figures_said_for_an_earlier_preparation_are_the_owner_s_when_passed_again(self):
        first = self.prepare('approve to 20 November, ' + EVENT, 'p1', outcome='approve', date='2026-11-20', reason=EVENT)
        self.assertEqual((first['prepared']['approvedDueDate'], first['prepared']['days'], first['figuresFrom']), ('2026-11-20', 31, None))   # said now
        self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])
        said = 'Fine, put it back as it was: same date, same reason.'
        again = self.prepare(said, 'p2', outcome='approve', date='2026-11-20', reason=EVENT)
        p = again['prepared']
        self.assertEqual((p['version'], p['outcome'], p['approvedDueDate'], p['reason'], again['retained'], again['figuresFrom'], again['reasonFrom']),
                         (2, 'approve', '2026-11-20', EVENT, ['date', 'reason'], 1, 1))
        self.assertEqual(self.prepare('make it as before', 'p3', days=31)['figuresFrom'], 2)   # an earlier day count too, the latest version with it
        # a revision keeping the date names the current version
        self.assertEqual(self.prepare('the reason is that they paid early last time', 'p4', reason='they paid early last time')['figuresFrom'], 3)
        # a figure never said in a message nor for any preparation of this case is still asked for
        self.ok('withdrawPreparation', key='w2', requestId=self.r['id'])
        for n, args in enumerate(({'date': '2026-11-21'}, {'days': 30})):
            missing = self.prepare(said, 'm' + str(n), outcome='approve', reason=EVENT, **args)
            self.assertEqual((missing['missing'], 'prepared' in missing), (list(args)[0], False), args)
        # nor is an earlier figure when the message states one of its own, in any words: the owner's words now win
        for n, (text, args) in enumerate((('approve to 10 December', {'date': '2026-11-20'}), ('approve 2 weeks', {'days': 31}),
                                          ('Make it the 30th instead, same reason.', {'date': '2026-11-20'}), ('till next Friday', {'date': '2026-11-20'}),
                                          ('a month this time', {'days': 31}), ('make it the twentieth, as before', {'date': '2026-11-20'}))):
            self.assertEqual(self.prepare(text, 'f' + str(n), outcome='approve', **args)['missing'], list(args)[0], text)
        back = self.prepare(said, 'f9', outcome='approve', date='2026-11-20', reason=EVENT)   # no figure of its own: the history still counts
        self.assertEqual((back['prepared']['approvedDueDate'], back['figuresFrom']), ('2026-11-20', 4))

    def test_a_decline_word_blocks_the_implied_approve_unless_it_is_negated(self):
        ask = {'requestId': self.r['id'], 'missing': 'outcome', 'ask': 'Approve or decline?', 'subject': self.bayside_subject()}
        self.assertEqual(self.prepare('Decline it; they already had 30 days last time.', 'd1', days=30), ask)   # no outcome passed: not approve
        self.assertEqual(self.prepare("Don't decline it.", 'd2', outcome='decline'), ask)   # a negated decline is no decline
        self.assertNotIn('preparedDecision', self.case())
        p = self.prepare("Don't decline it, go with the fortnight.", 'd3', days=14)['prepared']
        self.assertEqual((p['outcome'], p['approvedDueDate']), ('approve', '2026-11-03'))

    def test_a_reason_clause_in_the_message_is_the_reason_when_none_or_another_is_passed(self):   # fix wave 2, finding 1
        none = self.prepare('Approve 14 days.', 'n1', days=14)
        self.assertEqual((none['prepared']['reason'], none['reasonFrom']), (NO_REASON, None))
        for n, (said, reason, passed) in enumerate((
                ("Let's go with 14 days then, because that gives them a little breathing room.", 'that gives them a little breathing room', None),
                ('Approve 14 days, reason: they called ahead.', 'they called ahead', None),
                ('Approve 14 days since they paid the last one early. Thanks.', 'they paid the last one early', None),
                ('Approve 14 days, as they have always paid in the end.', 'they have always paid in the end', None),
                ('Approve 14 days so that they can finish the event.', 'they can finish the event', None),
                ('Because they paid early last time, give them 14 days.', 'they paid early last time', None),
                ('Approve 14 days because the event ran late.', 'the event ran late', 'events run late sometimes'),   # not in the message
                ('Go with 14 days because the season is slow.', 'the season is slow', 'the season is slow'))):   # the clause, as the Lab passes it
            out = self.prepare(said, 'c' + str(n), days=14, **({'reason': passed} if passed else {}))
            self.assertEqual((out['prepared']['reason'], out['reasonFrom'], 'reason' in out['retained']), (reason, 'message', False), said)
        # no clause: as before ("as it was" and "as before" are no reason)
        for n, said in enumerate(('Make it 14 days, as before.', 'Put it back as it was, 14 days.')):
            self.assertEqual(self.prepare(said, 'k' + str(n), days=14)['reasonFrom'], self.statuses()[-2][0], said)   # kept from the current one
        # a reason kept beats a clause: asked for in words, or passed as an earlier preparation's (round 2)
        kept = self.prepare('Keep the same reason, since nothing changed; 14 days.', 'r1', days=14)
        self.assertEqual((kept['prepared']['reason'], kept['reasonFrom'], 'reason' in kept['retained']), ('the season is slow', self.statuses()[-2][0], True))
        earlier = self.prepare('Go with 14 days, because it is fair.', 'r2', days=14, reason='they called ahead')
        first = [x['version'] for x in self.case()['preparations'] if x['reason'] == 'they called ahead'][0]
        self.assertEqual((earlier['prepared']['reason'], earlier['reasonFrom']), ('they called ahead', first))

    def test_a_weak_reason_word_needs_a_clause_of_three_words_with_no_digits(self):   # round 2
        for said in ('Approve 14 days since the 6th.', 'Fine, approve 14 days since you asked.', "Approve 14 days, so that's settled.",
                     'Approve 14 days, as they said 3 times.', 'Keep my reason, because nothing changed.', 'Same date, the reason as before, because why not.'):
            self.assertIsNone(said_reason(said), said)
        self.assertEqual([said_reason(x) for x in ('Approve 14 days because fair.', 'Approve it, reason: 2 late invoices.', 'Since the 6th they paid, because the event ran late.')],
                         ['fair', '2 late invoices', 'the event ran late'])

    def test_a_limit_said_with_nothing_prepared_is_asked_about_not_prepared(self):   # fix wave 2, finding 2
        ask = {'requestId': self.r['id'], 'missing': 'outcome', 'ask': 'Is that a decision to approve, or guidance to keep?', 'subject': self.bayside_subject()}
        for n, (said, days) in enumerate((('Up to 14 days this time', 14), ('No more than 10 days for this customer.', 10), ('At most a fortnight.', 14),
                                          ('Maximum 14 days.', 14))):
            self.assertEqual(self.prepare(said, 'h' + str(n), days=days), ask, said)
        self.assertNotIn('preparedDecision', self.case())
        # a decision verb makes it a decision; with something prepared, a limit said is a revision
        for n, (said, args) in enumerate((('Go with the fortnight', {'days': 14}), ('Give them till the 20th of November', {'date': '2026-11-20'}),
                                          ('Give them up to 14 days.', {'days': 14}), ('Approve up to 10 days.', {'days': 10}), ('Up to 7 days instead.', {'days': 7}))):
            self.assertIn('prepared', self.prepare(said, 'd' + str(n), **args), said)

    def test_an_explicit_outcome_and_a_remember_text_are_never_asked_about(self):   # live test L6
        said = ('approve on 30 Nov, they have paid everything in the end and their client is late this month, and from now on give them '
                'up to two weeks on any invoice until the end of December')
        got = self.prepare(said, 'L6', outcome='approve', date='2026-11-30', reason='they have paid everything in the end and their client is late this month',
                           remember={'text': 'up to two weeks on any invoice until the end of December', 'keepForCustomer': True, 'until': '2026-12-31'})
        self.assertEqual((got['prepared']['version'], got['prepared']['remember']['until'], 'missing' in got), (1, '2026-12-31', False))
        self.assertIn('their client is late', got['prepared']['reason'])

    def test_a_kept_date_is_named_as_it_was_given(self):
        dated = self.prepare('approve to 3 November', 'p1', outcome='approve', date='2026-11-03')['prepared']
        self.assertEqual((dated['approvedDueDate'], dated['days']), ('2026-11-03', 14))
        kept = self.prepare('the reason is that they paid early last time', 'p2', reason='they paid early last time')
        self.assertEqual((kept['prepared']['approvedDueDate'], kept['retained']), ('2026-11-03', ['outcome', 'date']))

    def test_a_revision_to_decline_keeps_the_reason_and_drops_the_date(self):
        self.prepare('approve 14 days, ' + EVENT, 'p1', outcome='approve', days=14, reason=EVENT)
        declined = self.prepare('decline it instead', 'p2', outcome='decline')
        p = declined['prepared']
        self.assertEqual((p['outcome'], p['approvedDueDate'], p['days'], p['reason'], declined['retained']), ('decline', None, None, EVENT, ['reason']))
        self.assertEqual(self.refused('prepareDecision', key='p3', message='approve 10 days', days=10, requestId=self.r['id']), 'INVALID_ARGUMENT')   # decline takes no days
        self.assertEqual(self.prepare('approve it', 'p4', outcome='approve')['missing'], 'days')   # a decline has no date to keep
        back = self.prepare('ten days then', 'p5', outcome='approve', days=10)   # back to approve: the days say it
        self.assertEqual((back['prepared']['outcome'], back['prepared']['days'], back['prepared']['reason'], back['retained']), ('approve', 10, EVENT, ['reason']))

    def test_superseded_and_withdrawn_preparations_are_never_confirmed_and_the_history_says_which(self):   # Review Focus 2
        v1 = self.prepare('approve 14 days', 'p1', outcome='approve', days=14)['prepared']
        v2 = self.prepare('approve ten days', 'p2', outcome='approve', days=10)['prepared']
        self.assertTrue(self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])['withdrawn'])
        for n, p in enumerate((v1, v2)):
            status, body, _ = self.confirm(p, 'c' + str(n))
            self.assertEqual((status, body['error']), (409, 'STALE_PREPARATION'), p['version'])
        c = self.case()
        self.assertEqual((c['status'], c['decision'], 'preparedDecision' in c), ('awaiting_owner', None, False))
        self.assertEqual(self.statuses(), [(1, 'superseded', 2), (2, 'withdrawn', None)])
        self.assertEqual([(e['data']['version'], e['data']['by']) for e in c['history'] if e['kind'] == 'decision.withdrawn'], [(2, 'owner_demo')])
        details = self.ok('caseDetails', requestId=self.r['id'])['case']
        self.assertEqual((details['activePreparation'], [(x['version'], x['status']) for x in details['preparations']]), (None, [(1, 'superseded'), (2, 'withdrawn')]))
        self.assertEqual(details['preparations'][0]['approvedDueDateText'], 'Tue 3 Nov 2026')
        # prepared again with nothing current: a new proposal, not a revision; confirmed, it is marked with the decision's time
        third = self.prepare('approve 14 days', 'p3', outcome='approve', days=14)
        self.assertEqual((third['prepared']['version'], third['revisionOf'], third['retained']), (3, None, []))
        self.assertEqual(self.ok('caseDetails', requestId=self.r['id'])['case']['activePreparation'], 3)
        status, decision, _ = self.confirm(third['prepared'], 'c3')
        self.assertEqual(status, 201, decision)
        c = self.case()
        self.assertEqual(self.statuses(), [(1, 'superseded', 2), (2, 'withdrawn', None), (3, 'confirmed', None)])
        self.assertEqual((c['preparations'][-1]['decidedAt'], 'preparedDecision' in c), (decision['decidedAt'], False))
        self.assertEqual([e['data']['version'] for e in c['history'] if e['kind'] == 'decision.confirmed'], [3])

    def test_a_case_prepared_again_or_decided_through_the_form_leaves_nothing_current(self):
        self.prepare('approve 14 days', 'p1', outcome='approve', days=14)
        c = self.case()
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/reanalyse', {'expectedRequestVersion': c['version']}, 'owner', 'ra')[0], 202)
        self.wait_status(self.r, ('awaiting_owner',))
        self.assertEqual(self.statuses(), [(1, 'withdrawn', None)])
        self.prepare('approve ten days', 'p2', outcome='approve', days=10)
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'd1')[0], 201)
        self.assertEqual(self.statuses(), [(1, 'withdrawn', None), (2, 'withdrawn', None)])
        self.assertEqual([(e['data']['version'], e['data']['by']) for e in self.case()['history'] if e['kind'] == 'decision.withdrawn'],
                         [(1, None), (2, 'owner_demo')])   # the app, when the case was prepared again; the owner, deciding through the form

    def test_what_the_model_reads_of_the_history_and_the_concerns_has_no_times(self):   # Important 1: a time's digits are no figure
        self.ok('raiseConcern', 'staff', key='k1', message=WORRY, requestId=self.r['id'], text=WORRY)
        self.prepare('approve 14 days', 'p1', outcome='approve', days=14)
        v2 = self.prepare('approve ten days', 'p2', outcome='approve', days=10)['prepared']
        self.assertEqual(self.confirm(v2, 'c1')[0], 201)
        details = self.ok('caseDetails', requestId=self.r['id'])
        self.assertIsNone(re.search(r'\d{4}-\d{2}-\d{2}T\d', known_text([details])))
        self.assertEqual([{k for k in x if k not in ('replacedBy',)} for x in details['case']['preparations']],
                         [{'version', 'status', 'outcome', 'approvedDueDate', 'approvedDueDateText', 'days', 'reason'},
                          {'version', 'status', 'outcome', 'approvedDueDate', 'approvedDueDateText', 'days', 'reason', 'decidedOn', 'decidedOnText'}])
        [concern] = details['case']['concerns']
        self.assertEqual((set(concern) - {'saidOnText'}, concern['saidOn']), ({'id', 'quote', 'kind', 'by', 'saidOn'}, self.case()['concerns'][0]['saidOn']))

    def test_staff_never_see_the_preparations_and_see_the_due_date_the_decision_gives(self):   # Review Focus 3
        self.prepare('approve 14 days', 'p1', outcome='approve', days=14)
        self.prepare('approve ten days', 'p2', outcome='approve', days=10)
        self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])
        v3 = self.prepare('approve 14 days', 'p3', outcome='approve', days=14)['prepared']
        staff = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']
        self.assertEqual((staff['preparations'], staff['activePreparation'], staff['preparedDecision']), (None, None, None))
        for words in ('preparations', 'preparedDecision', 'decision.prepared', 'decision.superseded', 'decision.withdrawn'):
            self.assertNotIn(words, json.dumps(self.case('staff')))
        self.assertEqual(self.confirm(v3, 'c1')[0], 201)
        self.wait_status(self.r, ('completed',))
        for words in ('preparations', 'decision.confirmed'):
            self.assertNotIn(words, json.dumps(self.case('staff')))
        staff = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']
        self.assertEqual((staff['dueNow'], staff['dueNowFrom'], staff['originalDue'], staff['preparations']), ('2026-11-03', 'decision', '2026-10-20', None))

    def test_due_now_is_the_invoice_s_until_a_decision_moves_it(self):
        def row():
            return next(x for x in self.call('/api/requests', role='staff')[1] if x['id'] == self.r['id'])
        before = row()
        self.assertEqual({k: before[k] for k in ('originalDue', 'originalDueText', 'dueNow', 'dueNowText', 'dueNowFrom')},
                         {'originalDue': '2026-10-20', 'originalDueText': 'Tue 20 Oct 2026', 'dueNow': '2026-10-20', 'dueNowText': 'Tue 20 Oct 2026', 'dueNowFrom': 'invoice'})
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'd1')[0], 201)
        self.wait_status(self.r, ('completed',))
        after = row()
        self.assertEqual((after['originalDue'], after['dueNow'], after['dueNowText'], after['dueNowFrom']), ('2026-10-20', '2026-11-03', 'Tue 3 Nov 2026', 'decision'))
        case = self.ok('caseDetails', requestId=self.r['id'])['case']
        self.assertEqual((case['dueNow'], case['dueNowText'], case['originalDueText'], case['dueNowFrom']), ('2026-11-03', 'Tue 3 Nov 2026', 'Tue 20 Oct 2026', 'decision'))

    def test_the_invoice_rows_tell_the_original_due_date_apart_from_the_one_a_decision_moved_it_to(self):
        def row():
            return next(x for x in self.ok('invoices', customerId=self.r['customerId'], which='all')['invoices'] if x['invoiceId'] == self.r['invoiceId'])
        self.assertEqual((row()['originalDueText'], 'dueNowText' in row()), ('Tue 20 Oct 2026', False))
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'd1')[0], 201)
        self.wait_status(self.r, ('completed',))
        moved = row()
        self.assertEqual((moved['originalDueText'], moved['dueNowText'], moved['dueNowSource'].startswith('approved to Tue 3 Nov 2026 on ')), ('Tue 20 Oct 2026', 'Tue 3 Nov 2026', True))

    def test_staff_raise_a_concern_both_roles_see_it_and_the_owner_s_queue_says_why(self):
        result = self.ok('raiseConcern', 'staff', key='k1', message=WORRY, requestId='current', current={'requestId': self.r['id']}, text=WORRY)
        line = result['line']
        self.assertEqual((set(line) - {'saidOnText'}, line['quote'], line['kind'], line['by']), ({'id', 'quote', 'kind', 'by', 'saidOn'}, WORRY, 'concern', 'staff'))
        self.assertEqual((result['requestId'], result['invoiceReference'], result['subject']), (self.r['id'], 'DEMO-501', self.bayside_subject()))
        status, body, _ = self.tool('raiseConcern', 'owner', 'k2', message=WORRY, requestId=self.r['id'], text=WORRY)   # staff only
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertEqual(self.refused('raiseConcern', 'staff', 'k3', message='Please look at it.', requestId=self.r['id'], text=WORRY), 'INVALID_ARGUMENT')   # not their words
        [mine] = [x for x in self.ok('workQueue')['forYou'] if x['requestId'] == self.r['id']]
        self.assertEqual(mine['why'], 'staff raised a concern')
        [theirs] = [x for x in self.ok('workQueue', 'staff')['waitingOnOthers'] if x['requestId'] == self.r['id']]
        self.assertEqual(theirs['why'], 'the owner decides; nothing to enter')
        for role in ('owner', 'staff'):   # listed where what was said is read: the case's lines and ownerContext for the case
            case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
            self.assertEqual([x['quote'] for x in case['concerns']], [WORRY], role)
            [said] = [x for x in case['contextLines'] if x['kind'] == 'concern']
            self.assertEqual((said['quote'], said['scope'], said['by'], said['source']), (WORRY, 'case', 'staff', 'concern'), role)
            context = self.ok('ownerContext', role, customerId=self.bayside['id'], requestId=self.r['id'])
            self.assertEqual([x['quote'] for x in context['lines'] if x['kind'] == 'concern'], [WORRY], role)
            self.assertIn('concern.raised', [e['kind'] for e in self.case(role)['history']], role)

    def test_a_concern_on_a_case_being_prepared_waits_on_no_one_until_it_is_prepared(self):
        r = {'status': 'analysing', 'concerns': [{'quote': WORRY}], 'analysis': None}
        for role in ('owner', 'staff'):
            self.assertEqual((waiting_on(r, role), queue_why(r, waiting_on(r, role), role)), ('none', 'the agent is preparing it'), role)
        r['status'] = 'needs_information'
        self.assertEqual([(waiting_on(r, x), queue_why(r, waiting_on(r, x), x)) for x in ('owner', 'staff')],
                         [('owner', 'staff raised a concern'), ('staff', 'the agent needs your answer to prepare it')])

    def said_earlier(self, text, days):
        """The statement said in these words, as said `days` before the business date."""
        with self.app.lock, self.app.db:
            s = next(x for x in self.app.statements() if x['text'] == text)
            s['saidOn'] = (calendar_date(s['saidOn']) - timedelta(days=days)).isoformat()
            self.app.save_statement(s)
        return s

    def reanalysed(self, key):
        c = self.case()
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/reanalyse', {'expectedRequestVersion': c['version']}, 'owner', key)[0], 202)
        self.wait_status(self.r, ('awaiting_owner',))
        return [q for q in self.case()['analysis']['brief']['questions'] if q['from'] == 'code']

    def code_questions(self):
        return [q for q in self.case()['analysis']['brief']['questions'] if q['from'] == 'code']

    def line(self, quote):
        return next(x for s in self.app.statements() for x in s['lines'] if x['quote'] == quote)

    def test_a_cited_line_said_earlier_that_expects_something_is_checked_and_an_uncited_or_ended_one_is_not(self):
        self.assertEqual(self.code_questions(), [])   # all said today
        self.app.model_adapter = AsksAboutTheEvent()   # the case's questions cite the expectation, and the guidance (the mock's own)
        named = self.said_earlier(NAMED, 10)
        self.said_earlier(SHARED, 31)   # long ago, but no question or limit of the case cites it
        expects = self.line(EXPECTS)
        # said 10 days ago: the cited expectation is checked; the cited guidance is not (not an expectation, not 30 days old)
        [q] = self.reanalysed('r1')
        self.assertEqual({k: q[k] for k in ('from', 'kind', 'lineId', 'status', 'answeredBy', 'createdBy')},
                         {'from': 'code', 'kind': 'check', 'lineId': expects['id'], 'status': 'open', 'answeredBy': None, 'createdBy': 'application_code'})
        self.assertEqual(q['question'], 'On ' + display_date(named['saidOn']) + " you said '" + EXPECTS + "'. Does that still hold for this request?")
        # said more than 30 days ago: every cited line, once each
        self.said_earlier(NAMED, 25)
        guidance = self.line('I would consider a small extension')
        self.assertEqual(sorted(q['lineId'] for q in self.reanalysed('r2')), sorted([expects['id'], guidance['id']]))
        staff = json.dumps(self.case('staff'), ensure_ascii=False) + json.dumps(self.situation('staff'), ensure_ascii=False)
        self.assertNotIn('Does that still hold', staff)
        self.assertEqual([(q['from'], q['createdBy']) for q in self.situation('owner')['case']['questions'] if q['from'] == 'code'],   # asked of the owner, by the app
                         [('code', 'application_code')] * 2)
        # an expectation that has ended is not asked about
        with self.app.lock, self.app.db:
            s = next(x for x in self.app.statements() if x['text'] == NAMED)
            next(x for x in s['lines'] if x['id'] == expects['id'])['until'] = (calendar_date(named['saidOn']) - timedelta(days=1)).isoformat()
            self.app.save_statement(s)
        self.assertEqual([q['lineId'] for q in self.reanalysed('r3')], [guidance['id']])

    def test_an_open_check_holds_back_the_suggestion_and_once_answered_stays_answered(self):   # Important 2
        self.said_earlier(NAMED, 31)   # the mock's question quotes the guidance, and is answered by the owner's answer
        [q] = self.reanalysed('r1')
        guidance = self.line('I would consider a small extension')
        self.assertEqual((q['lineId'], q['status']), (guidance['id'], 'open'))
        s = self.situation('owner')['case']['suggestion']
        self.assertEqual((s['status'], s['withheldBecause']), ('withheld', [q['question']]))
        status, view, _ = self.call('/api/requests/' + self.r['id'] + '/questions/' + q['id'] + '/answer', {'text': 'Yes, that still stands'}, 'owner', 'a2')
        self.assertEqual(status, 200, view)
        [said] = [x for x in self.app.statements() if x['text'] == 'Yes, that still stands']
        self.assertEqual((said['scope'], said['source']), ({'kind': 'case', 'requestId': self.r['id']},
                                                           {'kind': 'answer', 'questionId': q['id'], 'lineId': guidance['id']}))
        self.assertEqual(self.situation('owner')['case']['suggestion']['status'], 'given')
        # prepared again: the line is still cited and still old, and the check is answered by the owner's words, not asked again
        [again] = self.reanalysed('r2')
        self.assertEqual((again['lineId'], again['status'], again['answeredBy']), (guidance['id'], 'answered', said['lines'][0]['id']))
        self.assertEqual(self.situation('owner')['case']['suggestion']['status'], 'given')


class IntakeTests(DemoCase):
    def test_a_second_open_request_on_one_invoice_is_numbered_and_flagged_and_neither_is_refused_or_merged(self):   # Review Focus 5
        self.start()
        first = self.wait_status(self.create(ISO_MESSAGE, 'k1'), ('awaiting_owner',))
        second = self.wait_status(self.create(ISO_MESSAGE, 'k2'), ('awaiting_owner',))
        later = self.wait_status(self.create('Could we pay invoice DEMO-101 on 2026-11-06 instead?', 'k3'), ('awaiting_owner',))
        rows = {x['id']: x for x in self.call('/api/requests', role='staff')[1]}
        self.assertEqual([(rows[x['id']]['ordinal'], rows[x['id']]['flags']) for x in (first, second, later)],
                         [(1, []), (2, [{'kind': 'duplicateIntake', 'requestId': first['id']}]), (3, [])])
        queue = self.call('/api/tools/workQueue', {'args': {}}, 'owner')[1]['result']
        self.assertEqual(sorted(x['requestId'] for x in queue['forYou']), sorted(x['id'] for x in (first, second, later)))
        self.assertEqual({x['requestId']: x['ordinal'] for x in queue['forYou']}, {first['id']: 1, second['id']: 2, later['id']: 3})
        self.assertEqual((queue['summaryText'], {x['waitingOn'] for x in queue['forYou']}),
                         ('3 cases need your decision: DEMO-101 (Harbour Demo Supplies, 3 requests). Nothing is waiting on others.', {'you'}))
        staff = self.call('/api/tools/workQueue', {'args': {}}, 'staff')[1]['result']
        self.assertEqual((staff['summaryText'], {x['waitingOn'] for x in staff['waitingOnOthers']}),
                         ('Nothing is waiting for you. 3 cases are with the owner: DEMO-101 (Harbour Demo Supplies, 3 requests).', {'owner'}))
        details = self.call('/api/tools/caseDetails', {'args': {'requestId': second['id']}}, 'staff')[1]['result']['case']
        self.assertEqual((details['ordinal'], details['flags']), (2, [{'kind': 'duplicateIntake', 'requestId': first['id']}]))
        # once the first is decided, the second is the first open request on the invoice, and no longer a likely duplicate
        self.assertEqual(self.decide(first)[0], 201)
        self.wait_status(first, ('completed',))
        rows = {x['id']: x for x in self.call('/api/requests', role='staff')[1]}
        self.assertEqual([(rows[x['id']]['ordinal'], rows[x['id']]['flags']) for x in (second, later)], [(1, []), (2, [])])


if __name__ == '__main__':
    unittest.main()
