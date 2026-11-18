"""Quick setup (11 Nov 2026): the helper's answers become a full policy by fixed code (no model), a policy reads back as answers, and the plain summary says what
the agent will decide and what comes to the Owner. Fictional demonstration policy (delegation_demo.DEMO_POLICY)."""
import unittest

import delegation
import delegation_demo
from records import RecordsError

S = {'currency': 'AUD', 'scale': 2}
CUR = delegation.validate_policy(delegation_demo.DEMO_POLICY, S)
ANS = {'start': 'now', 'maxInvoice': '2,000.00', 'maxCustomer': ' 5000 ', 'daysFromRequest': 14, 'daysPastOriginalDue': 45, 'allowOtherOverdue': True,
       'lateHistory': 'some', 'holdCustomers': ['c9'], 'agentDeclines': True}


def policy(answers, current=CUR):
    return delegation.validate_policy(delegation.quick_setup_policy(answers, current), S)


class QuickSetupPolicyTests(unittest.TestCase):
    def test_every_answer_lands_on_its_setting(self):
        p = policy(ANS)
        self.assertEqual((p['mode'], p['trackRecord']['minReviewedCases'], p['trackRecord']['minAgreement']), ('delegated', None, None))
        self.assertEqual((p['limits']['maxDecisionExposure']['minorUnits'], p['limits']['maxCustomerExposure']['minorUnits']), ('200000', '500000'))
        e = p['extensions']
        self.assertEqual((e['enabled'], e['maxDays'], e['maxDaysFromRequest'], e['maxDaysPastOriginalDue'], e['requireNothingElseOverdue'], e['maxPriorLateShare']),
                         (True, 45, 14, 45, False, '0.25'))
        self.assertEqual(p['restrictions']['holdCustomers'], ['c9'])
        self.assertEqual(p['autoDecline'], {'enabled': True, 'maxExtensionDays': 45, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None})

    def test_the_three_starts(self):
        after = policy({**ANS, 'start': 'after_reviews'}, policy(ANS))   # from a policy that decides from today: the helper sets its own track record
        self.assertEqual((after['mode'], after['trackRecord']['minReviewedCases'], after['trackRecord']['minAgreement'], after['trackRecord']['sources']),
                         ('delegated', 5, '0.8', 'live'))
        rec = policy({**ANS, 'start': 'recommend'})
        self.assertEqual((rec['mode'], rec['trackRecord']), ('advisory', CUR['trackRecord']))

    def test_a_change_keeps_extensions_off_when_the_owner_turned_them_off(self):
        off = {**CUR, 'extensions': {**CUR['extensions'], 'enabled': False}}
        p = policy({**delegation.quick_setup_answers(off), 'maxInvoice': '700.00'}, off)
        self.assertFalse(p['extensions']['enabled'])
        self.assertTrue(policy({**delegation.quick_setup_answers(off), 'start': 'now'}, {**off, 'mode': 'advisory'})['extensions']['enabled'])

    def test_late_history_choices_and_no_decline(self):
        self.assertIsNone(policy({**ANS, 'lateHistory': 'any'})['extensions']['maxPriorLateShare'])
        self.assertEqual(policy({**ANS, 'lateHistory': 'none'})['extensions']['maxPriorLateShare'], '0')
        self.assertEqual(policy({**ANS, 'agentDeclines': False})['autoDecline'], delegation.AUTO_DECLINE_DEFAULT)

    def test_what_was_not_asked_is_kept(self):
        p = policy(ANS)
        for key in ('newCustomers', 'exceptions', 'smallOverage', 'evidence', 'customers', 'paused', 'feedback'):
            self.assertEqual(p[key], CUR[key], key)
        self.assertEqual(p['limits']['maxAutonomousExposure30d'], CUR['limits']['maxAutonomousExposure30d'])
        self.assertEqual(p['restrictions']['unusualSizeMultiple'], CUR['restrictions']['unusualSizeMultiple'])

    def test_missing_answers_keep_the_current_values(self):
        self.assertEqual(delegation.policy_digest(policy({})), delegation.policy_digest(CUR))

    def test_a_stored_policy_with_version_and_digest_is_accepted_as_current(self):
        self.assertEqual(policy(ANS, {**CUR, 'version': 4, 'digest': 'x', 'createdAt': 'y'})['mode'], 'delegated')

    def test_answers_round_trip(self):
        self.assertEqual(delegation.quick_setup_answers(policy(ANS)), {**ANS, 'maxInvoice': '2000.00', 'maxCustomer': '5000.00', 'newCustomers': 'trial'})   # the demo policy keeps trial credit on

    def test_bad_money_is_a_field_error_from_validate(self):
        for bad in ('-5', 'abc'):
            with self.assertRaises(RecordsError) as e:
                policy({**ANS, 'maxInvoice': bad})
            self.assertEqual(e.exception.field, 'limits.maxDecisionExposure')

    def test_field_names_map_back_to_questions(self):
        self.assertEqual(delegation.QUICK_FIELD['limits.maxDecisionExposure'], 'maxInvoice')
        self.assertEqual(delegation.QUICK_CHECK['nothing_else_overdue'], 'allowOtherOverdue')


class QuickSetupSummaryTests(unittest.TestCase):
    def summary(self, answers, current=CUR, names=None):
        return delegation.quick_setup_summary(policy(answers, current), S, names or {'c9': 'Cityside Foods'})

    def test_summary_says_what_the_agent_decides_and_what_comes_to_you(self):
        s = self.summary(ANS)
        decides, comes = ' '.join(s['decides']), ' '.join(s['comesToYou'])
        self.assertIn('A later payment date on an invoice of up to AUD 2,000.00, when the customer would owe at most AUD 5,000.00 in total.', decides)
        self.assertIn('up to 14 days after the day the customer asks, and up to 45 days after the invoice\'s original due date', decides)
        self.assertIn('Also when the customer has other overdue invoices.', decides)
        self.assertIn('It may decline a request for more than 45 days when the assistant recommends declining.', decides)
        self.assertIn('Every request from: Cityside Foods.', comes)
        self.assertIn('Anything over those limits.', comes)
        self.assertNotIn('first credit', comes)   # the demo policy has trial credit on
        off = {**CUR, 'newCustomers': {**CUR['newCustomers'], 'trialCredit': 'off'}}
        self.assertIn('Every first credit for a new customer.', self.summary(ANS, off)['comesToYou'])

    def test_other_overdue_and_late_history_come_to_you_when_not_allowed(self):
        comes = ' '.join(self.summary({**ANS, 'allowOtherOverdue': False, 'lateHistory': 'none'})['comesToYou'])
        self.assertIn('Any request from a customer with another overdue invoice.', comes)
        self.assertIn('Any request from a customer who has paid late before.', comes)
        self.assertIn('more than a quarter of their earlier payments were late', ' '.join(self.summary(ANS)['comesToYou']))

    def test_the_starts_change_the_first_sentence(self):
        self.assertEqual(self.summary({**ANS, 'start': 'recommend'})['decides'], ['Nothing yet: the agent only recommends, and you decide everything.'])
        self.assertTrue(self.summary({**ANS, 'start': 'after_reviews'})['decides'][0].startswith('Nothing until you have reviewed 5 of its recommendations'))

    def test_unasked_settings_that_send_requests_to_you_are_named(self):
        comes = ' '.join(self.summary(ANS)['comesToYou'])   # the demo policy sets a 30-day total of AUD 5,000.00 and an unusual size of 3 times
        self.assertIn('(set on the Control panel)', comes)
        self.assertIn('3 times', comes)


class QuickSetupLevelTests(unittest.TestCase):
    """The three ready-made levels (12 Nov 2026): six answers each, worked out from the business's own open invoices."""
    plain = staticmethod(lambda units: '%d.%02d' % divmod(units, 100))

    def levels(self, units={'median': 48000, 'largest': 90000}):
        return {l['name']: l for l in delegation.quick_setup_levels(units, self.plain)}

    def test_three_levels_in_order_each_stricter_than_the_next(self):
        out = delegation.quick_setup_levels({'median': 48000, 'largest': 90000}, self.plain)
        self.assertEqual([l['name'] for l in out], ['strict', 'balanced', 'relaxed'])
        days = [(l['answers']['daysFromRequest'], l['answers']['daysPastOriginalDue']) for l in out]
        self.assertEqual(days, [(7, 30), (14, 60), (30, 90)])
        self.assertEqual([l['answers']['lateHistory'] for l in out], ['none', 'some', 'any'])
        self.assertEqual(out[2]['answers']['maxInvoice'], '900.00')
        self.assertEqual(out[2]['answers']['maxCustomer'], '1800.00')
        self.assertEqual(out[0]['answers']['maxInvoice'], '480.00')

    def test_a_level_never_touches_the_start_the_kept_customers_or_declining(self):
        for l in self.levels().values():
            self.assertEqual(set(l['answers']), {'maxInvoice', 'maxCustomer', 'daysFromRequest', 'daysPastOriginalDue', 'allowOtherOverdue', 'lateHistory'})

    def test_without_open_invoices_a_level_leaves_the_money_answers_alone(self):
        for l in delegation.quick_setup_levels(None, self.plain):
            self.assertNotIn('maxInvoice', l['answers'])
            self.assertNotIn('maxCustomer', l['answers'])

    def test_a_level_makes_a_valid_policy_and_reads_back_as_itself(self):
        for name, l in self.levels().items():
            answers = {**delegation.quick_setup_answers(CUR), **l['answers']}
            p = policy(answers)
            back = delegation.quick_setup_answers(p)
            for k, v in l['answers'].items():
                self.assertEqual(back[k], v, (name, k))
            self.assertEqual(p['newCustomers'], CUR['newCustomers'], name)   # what a level does not ask about is kept
            self.assertEqual(p['restrictions'], CUR['restrictions'], name)


if __name__ == '__main__':
    unittest.main()


TUNED = delegation.validate_policy({**delegation_demo.DEMO_POLICY,
    'extensions': {**delegation_demo.DEMO_POLICY['extensions'], 'maxDays': 14, 'maxPriorLateShare': '0.1'},
    'trackRecord': {'minReviewedCases': 20, 'minAgreement': '0.9', 'sources': 'both'},
    'autoDecline': {'enabled': True, 'maxExtensionDays': 60, 'maxDecisionExposure': '800.00', 'maxCustomerExposure': None, 'maxPriorLateShare': '0.5'}}, S)


class QuickSetupFixTests(unittest.TestCase):
    """The final review of 11 Nov 2026: what the helper writes when it is run again, the first-run answers, and the summary's honesty."""

    def test_an_untouched_rerun_on_a_tuned_policy_changes_only_the_total_limit_it_adds(self):
        p = policy(delegation.quick_setup_answers(TUNED), TUNED)
        self.assertEqual(p['extensions']['maxDaysPastOriginalDue'], 14)   # the helper's question shows the 14 and keeps it as the total
        p_without = {**p, 'extensions': {**p['extensions'], 'maxDaysPastOriginalDue': None}}
        self.assertEqual(delegation.policy_digest(p_without), delegation.policy_digest(TUNED))

    def test_ticking_a_held_customer_changes_nothing_else(self):
        p = policy({**delegation.quick_setup_answers(TUNED), 'holdCustomers': ['c9']}, TUNED)
        self.assertEqual(p['restrictions']['holdCustomers'], ['c9'])
        for key in ('trackRecord', 'autoDecline', 'limits'):
            self.assertEqual(p[key], TUNED[key], key)
        self.assertEqual((p['extensions']['maxDays'], p['extensions']['maxPriorLateShare']), (14, '0.1'))

    def test_changing_the_total_moves_a_linked_decline_line_but_not_a_separately_tuned_max_days(self):
        linked = delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'extensions': {**delegation_demo.DEMO_POLICY['extensions'], 'maxDays': 30, 'maxDaysPastOriginalDue': 30},
                                             'autoDecline': {'enabled': True, 'maxExtensionDays': 30, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None}}, S)
        p = policy({**delegation.quick_setup_answers(linked), 'daysPastOriginalDue': 50}, linked)
        self.assertEqual((p['extensions']['maxDays'], p['extensions']['maxDaysPastOriginalDue'], p['autoDecline']['maxExtensionDays']), (50, 50, 50))
        p = policy({**delegation.quick_setup_answers(TUNED), 'daysPastOriginalDue': 45}, {**TUNED, 'extensions': {**TUNED['extensions'], 'maxDaysPastOriginalDue': 30}})
        self.assertEqual((p['extensions']['maxDays'], p['extensions']['maxDaysPastOriginalDue'], p['autoDecline']['maxExtensionDays']), (14, 45, 60))

    def test_first_run_answers_are_the_helpers_defaults_and_validate(self):
        a = delegation.quick_setup_first_answers({'median': {'plain': '480.00'}, 'largest': {'plain': '900.00'}})
        self.assertEqual((a['start'], a['maxInvoice'], a['maxCustomer'], a['lateHistory']), ('now', '480.00', '900.00', 'some'))
        self.assertGreater(a['daysPastOriginalDue'], 0)
        p = policy(a, delegation.default_policy(S))
        self.assertEqual(p['mode'], 'delegated')
        self.assertEqual(delegation.quick_setup_first_answers(None)['maxInvoice'], '')

    def test_the_summary_names_what_lets_the_agent_go_over_a_limit(self):
        on = {**CUR, 'smallOverage': {**CUR['smallOverage'], 'enabled': True}, 'exceptions': {**CUR['exceptions'], 'enabled': True},
              'customers': {'c9': {'maxExtensionDays': 10}}}
        s = delegation.quick_setup_summary(policy(ANS, on), S, {})
        decides, comes = ' '.join(s['decides']), ' '.join(s['comesToYou'])
        self.assertIn('A little over a money limit', decides)
        self.assertIn("the team's model says you would approve", decides)
        self.assertIn('1 customer with its own rules', decides)
        self.assertIn('Anything over those limits, except as above.', comes)
        self.assertIn('Anything over those limits.', ' '.join(delegation.quick_setup_summary(policy(ANS), S, {})['comesToYou']))


class QuickSetupNewCustomerTests(unittest.TestCase):
    """New customers in Get started and Quick setup (13 Nov 2026): from a clean start trial credit stayed off, so every first order went to the Owner."""
    V0 = delegation.default_policy(S)

    def first(self, **more):
        return {**delegation.quick_setup_first_answers({'median': {'plain': '480.00'}, 'largest': {'plain': '900.00'}}), **more}

    def test_first_run_keeps_new_customers_with_the_owner(self):
        self.assertEqual(self.first()['newCustomers'], 'owner')
        p = policy(self.first(), self.V0)
        self.assertEqual(p['newCustomers']['trialCredit'], 'off')
        self.assertIn('Every first credit for a new customer.', delegation.quick_setup_summary(p, S, {})['comesToYou'])

    def test_a_small_first_order_follows_the_one_request_limit(self):
        p = policy(self.first(newCustomers='trial'), self.V0)
        n = p['newCustomers']
        self.assertEqual((n['trialCredit'], n['maxExposure']['minorUnits'], n['staffCheckedDepositUpTo']['minorUnits'], n['minDepositShare'], n['maxTermsDays']),
                         ('limited', '48000', '48000', '0.25', 30))
        self.assertEqual(p['limits']['maxDecisionExposure']['minorUnits'], '48000')
        self.assertEqual(delegation.quick_setup_answers(p)['newCustomers'], 'trial')
        decides = ' '.join(delegation.quick_setup_summary(p, S, {})['decides'])
        self.assertIn('A first order on credit for a new customer, with up to AUD 480.00 at risk after a deposit of at least a quarter', decides)

    def test_raising_the_invoice_limit_later_moves_a_linked_trial_limit_only(self):
        linked = policy(self.first(newCustomers='trial'), self.V0)
        p = policy({**delegation.quick_setup_answers(linked), 'maxInvoice': '900.00'}, linked)
        self.assertEqual((p['newCustomers']['maxExposure']['minorUnits'], p['newCustomers']['staffCheckedDepositUpTo']['minorUnits']), ('90000', '90000'))
        p = policy({**delegation.quick_setup_answers(CUR), 'maxInvoice': '900.00'}, CUR)   # the demo policy tuned its trial limit apart (600 vs 1000)
        self.assertEqual(p['newCustomers']['maxExposure'], CUR['newCustomers']['maxExposure'])

    def test_an_owner_choice_switches_trial_credit_off_and_keeps_its_numbers(self):
        p = policy({**delegation.quick_setup_answers(CUR), 'newCustomers': 'owner'}, CUR)
        self.assertEqual(p['newCustomers'], {**CUR['newCustomers'], 'trialCredit': 'off'})

    def test_an_untouched_answer_changes_nothing_and_a_bad_one_is_refused(self):
        p = policy(delegation.quick_setup_answers(CUR), CUR)
        self.assertEqual(p['newCustomers'], CUR['newCustomers'])
        with self.assertRaises(RecordsError):
            policy({**delegation.quick_setup_answers(CUR), 'newCustomers': 'maybe'})
