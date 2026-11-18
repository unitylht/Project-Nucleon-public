"""The bench's pure parts (the judge, the crude contradiction check, the summary, the instructions text): python3 -m unittest discover -s tools/modelbench. No stack, no model."""
import unittest

import bench


def case(customer, status, by=None, outcome='approve'):
    return {'caseId': 'case_x', 'kind': 'trial_credit', 'status': status, 'handling': None, 'customer': {'name': customer + ' (fictional)'}, 'decision': {'by': by, 'outcome': outcome} if by else None}


class JudgeTests(unittest.TestCase):
    def test_each_prompt_is_judged_by_the_backend_state(self):
        self.assertEqual(bench.judge('northside', [case('Northside Cafe', 'decided', 'agent')], 'decided_by_agent', []), (True, []))
        self.assertFalse(bench.judge('northside', [case('Northside Cafe', 'awaiting_owner')], 'decided_by_agent', [])[0])
        self.assertFalse(bench.judge('northside', [case('Northside Cafe', 'decided', 'owner')], 'decided_by_agent', [])[0])
        self.assertTrue(bench.judge('harbourline', [case('Harbourline Catering', 'awaiting_owner')], 'awaiting_owner', [])[0])
        self.assertTrue(bench.judge('lakeside', [case('Lakeside Kiosk', 'gathering_evidence')], 'gathering_evidence', [])[0])
        self.assertFalse(bench.judge('lakeside', [case('Lakeside Kiosk', 'decided', 'agent')], 'gathering_evidence', [])[0])

    def test_exactly_one_case_and_none_for_the_mixed_prompt(self):
        two = [case('Northside Cafe', 'decided', 'agent'), case('Northside Cafe', 'awaiting_owner')]
        self.assertFalse(bench.judge('northside', two, 'decided_by_agent', [])[0])
        self.assertFalse(bench.judge('northside', [], 'decided_by_agent', [])[0])
        self.assertFalse(bench.judge('northside', [case('Bayview Gelato Co', 'decided', 'agent')], 'decided_by_agent', [])[0])   # a case for someone else
        self.assertTrue(bench.judge('mixed', [], 'no_case', [])[0])
        self.assertFalse(bench.judge('mixed', [case('Northside Cafe', 'gathering_evidence')], 'no_case', [])[0])

    def test_an_error_fails_the_prompt(self):
        passed, reasons = bench.judge('mixed', [], 'no_case', [], 'provider: HTTP 400')
        self.assertFalse(passed)
        self.assertIn('provider', reasons[0])


class ContradictionTests(unittest.TestCase):
    def test_approved_when_the_backend_did_not_approve(self):
        self.assertIn('approved', bench.contradicts('Great news. The credit is approved.', 'awaiting_owner'))
        self.assertIsNone(bench.contradicts('Nothing is approved until Staff provide it.', 'gathering_evidence'))
        self.assertIsNone(bench.contradicts('Not approved: it is outside what the Owner delegated, so the Owner decides.', 'awaiting_owner'))
        self.assertIsNone(bench.contradicts('The credit is approved.', 'decided'))
        self.assertIsNone(bench.contradicts('Which kind is it?', None))
        self.assertIsNotNone(bench.contradicts('Approved within policy.', None))   # no case, yet it claims approval


class SummaryTests(unittest.TestCase):
    def row(self, run, prompt, passed=True, calls=3):
        return {'run': run, 'prompt': prompt, 'passed': passed, 'toolCalls': calls, 'seconds': 10.0, 'providerErrors': 0, 'contradiction': None, 'promptTokens': 100, 'completionTokens': 10}

    def test_a_run_is_adequate_when_all_five_pass_within_four_calls(self):
        rows = [self.row(r, p) for r in range(2) for p in bench.PROMPTS]
        rows[7]['toolCalls'] = 5   # run 1, one prompt over four calls
        s = bench.summarise(rows, 2)
        self.assertEqual(s['runsAdequate'], 1)
        self.assertEqual(s['perPrompt']['northside']['passedWithinCalls'], 2)
        self.assertEqual(sum(v['passedWithinCalls'] for v in s['perPrompt'].values()), 9)
        self.assertIn('**1 of 2**', bench.markdown({}, s, rows))

    def test_a_subset_run_is_never_adequate(self):
        rows = [self.row(0, 'northside')]
        self.assertEqual(bench.summarise(rows, 1)['runsAdequate'], 0)


class NudgeTests(unittest.TestCase):
    def test_empty_reply_fires(self):
        self.assertEqual(bench.nudge_reason(['findCustomers'], '', False), 'empty')
        self.assertEqual(bench.nudge_reason([], '  \n', False), 'empty')
        self.assertEqual(bench.nudge_reason([], None, False), 'empty')

    def test_assess_or_needed_without_resolve_fires(self):
        self.assertEqual(bench.nudge_reason(['findCustomers', 'assessDecision'], 'Please send the missing items.', False), 'unsubmitted')
        self.assertEqual(bench.nudge_reason(['whatIsNeeded'], 'I need the deposit.', False), 'unsubmitted')

    def test_resolved_or_plain_answers_do_not_fire(self):
        self.assertIsNone(bench.nudge_reason(['assessDecision', 'resolveDecision'], 'Approved.', False))
        self.assertIsNone(bench.nudge_reason(['findCustomers'], 'Found one customer.', False))
        self.assertIsNone(bench.nudge_reason([], 'Hello.', False))

    def test_at_most_one_nudge(self):
        self.assertIsNone(bench.nudge_reason(['assessDecision'], '', True))

    def test_outcome(self):
        self.assertEqual(bench.nudge_outcome(['resolveDecision'], ''), 'resolved')
        self.assertEqual(bench.nudge_outcome([], ''), 'still_empty')
        self.assertEqual(bench.nudge_outcome(['whatIsNeeded'], 'Missing: the deposit.'), 'asked_staff')

    def test_wording_does_not_order_a_submit(self):
        self.assertIn('missing', bench.NUDGE_TEXT)
        self.assertIn('do not submit', bench.NUDGE_TEXT)

    def test_instructions_extra_is_appended_once(self):
        base = bench.instructions()
        self.assertEqual(bench.instructions('  Extra line.  '), base + ' Extra line.')
        self.assertEqual(bench.instructions(''), base)

    def test_instructions_file_replaces_the_text(self):
        v = bench.instructions(path=bench.HERE / 'variants' / 'instructions_no_whatisneeded.txt')
        self.assertNotIn('whatIsNeeded', v)
        self.assertIn('assessDecision', v)
        self.assertNotIn('assessDecision, once', bench.instructions(path=bench.HERE / 'variants' / 'instructions_resolve_only.txt'))


class AmbiguitySetTests(unittest.TestCase):
    def test_defaults_stay_the_standard_five(self):
        self.assertEqual(list(bench.PROMPTS), ['northside', 'bayview', 'harbourline', 'lakeside', 'mixed'])
        self.assertEqual(list(bench.EXTRA_PROMPTS), ['ambiguous-extension', 'bare-approve', 'amount-and-due-date'])
        self.assertTrue(set(bench.PROMPTS).isdisjoint(bench.EXTRA_PROMPTS))

    def test_every_extra_prompt_expects_no_case(self):
        for name, (text, _, expected) in bench.EXTRA_PROMPTS.items():
            self.assertEqual(expected, 'no_case', name)
            self.assertTrue(text)
            self.assertTrue(bench.judge(name, [], expected, [])[0], name)
            self.assertFalse(bench.judge(name, [{'status': 'awaiting_owner', 'customer': {'name': 'Harbourline Catering'}}], expected, [])[0], name)

    def test_extra_prompts_do_not_change_the_d5_figure(self):
        rows = [{'run': 0, 'prompt': n, 'passed': True, 'toolCalls': 2, 'seconds': 1.0, 'providerErrors': 0, 'contradiction': None} for n in list(bench.ALL_PROMPTS)]
        s = bench.summarise(rows, 1)
        self.assertEqual(s['runsAdequate'], 1)
        self.assertEqual(len(s['perPrompt']), 8)


class InstructionsTests(unittest.TestCase):
    def test_the_bench_reads_the_text_file_the_agent_script_carries(self):
        text = bench.instructions()
        self.assertIn('ask Staff exactly hint.question', text)
        self.assertNotIn('\n', text)


if __name__ == '__main__':
    unittest.main()
