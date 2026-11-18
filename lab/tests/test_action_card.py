"""The action cards (lab/card.py: prepareRequest, actionStatus) from REAL results of the records (fixtures/action_card/*.json, made by
make_action_card_fixtures.py; fictional data). A proposal is never called submitted; "submitted" is said only for an executed action; the one button
exists only when the Lab's recordsPublicUrl and the result's actionId make a URL that fits the contract exactly; the HTML carries no token; the
financial cards are byte for byte what they were."""
import hashlib
import html
import json
import re
import unittest
from copy import deepcopy
from pathlib import Path

from lab import card
from lab.config import load
from test_card import FIX, NAMES, Page, load as load_financial

ACTIONS = Path(__file__).resolve().parent / 'fixtures' / 'action_card'
LOCAL, ISOLATED = 'http://127.0.0.1:8631', 'http://127.0.0.1:18631'
TAILNET = 'https://nucleon.tail492813.ts.net:8443'   # the local runtime over Tailscale Serve
CLOUDFLARE = 'https://nucleon.dracooz.top'   # the PoV's public origin (Cloudflare Tunnel, behind Cloudflare Access)


def fixture(name):
    return json.loads((ACTIONS / (name + '.json')).read_text())


def page(tool, result, url=ISOLATED):
    return Page(card.card_html(tool, result, url))


class ProposedCard(unittest.TestCase):
    def test_a_proposal_says_proposed_not_submitted_and_shows_what_the_records_gave(self):
        d = fixture('proposed')
        for tool, result in (('prepareRequest', d['prepare']), ('actionStatus', d['status'])):
            p = page(tool, result)
            text, preview = p.text, result['preview']
            self.assertIn('PROPOSED — NOT SUBMITTED.', text)
            self.assertIn('A person must confirm it in Nucleon.', text)
            self.assertNotIn('SUBMITTED FOR OWNER REVIEW', text)
            self.assertNotRegex(text, r'(?i)\b(approved|created|opened|submitted for)\b')
            self.assertIn(preview['fromRecords']['customer']['name'], text)
            self.assertIn('Invoice ' + preview['fromRecords']['invoice']['reference'], text)
            self.assertIn(preview['fromRecords']['invoice']['amountText'], text)
            self.assertIn(preview['proposedChange']['currentDueDateText'] + ' → ' + preview['proposedChange']['requestedDueDateText'] + ' (14 days)', text)
            self.assertIn('Reason drafted by the assistant: ' + preview['draftedByAssistant']['reason'], text)
            self.assertIn('Confirming submits this request to the owner for review. It does not approve the extension.', text)
            self.assertIn('Expires ' + 'Tue 27 Oct 2026, 00:10 UTC', text)

    def test_the_completeness_caveat_is_shown_verbatim_unless_the_records_are_confirmed_complete(self):
        d = fixture('proposed')['prepare']
        caveat = d['preview']['completeness']['caveatText']
        self.assertIs(d['preview']['completeness']['balanceEstablished'], False)
        self.assertIn(caveat, page('prepareRequest', d).text)
        self.assertIn('Unconfirmed', page('prepareRequest', d).text)
        for broken in (None, 'true', 1, 'yes'):   # fail closed: only an explicit true is "confirmed"
            r = deepcopy(d)
            r['preview']['completeness']['balanceEstablished'] = broken
            self.assertIn(caveat, page('prepareRequest', r).text)
        r = deepcopy(d)
        del r['preview']['completeness']
        self.assertIn('The records are not confirmed complete.', page('prepareRequest', r).text)
        r = deepcopy(d)
        r['preview']['completeness']['balanceEstablished'] = True
        self.assertNotIn(caveat, page('prepareRequest', r).text)

    def test_no_drafted_reason_shows_no_reason_line_and_a_date_request_has_its_own_days(self):
        d = fixture('proposed_no_reason')['prepare']
        text = page('prepareRequest', d).text
        self.assertNotIn('Reason drafted', text)
        self.assertIn('(16 days)', text)


class StateCards(unittest.TestCase):
    def test_an_executed_action_says_submitted_for_owner_review_with_the_request_and_that_the_owner_has_not_decided(self):
        d = fixture('executed')['status']
        text = page('actionStatus', d).text
        self.assertIn('SUBMITTED FOR OWNER REVIEW — request ' + d['request']['id'] + '; the owner has not decided.', text)
        self.assertNotIn('PROPOSED', text)
        self.assertNotIn('NOT SUBMITTED', text)
        self.assertNotIn('Review and confirm', text)
        self.assertNotIn('Confirming submits', text)   # nothing left to confirm

    def test_once_the_owner_has_decided_the_card_does_not_say_he_has_not(self):
        d = fixture('executed_decided')['status']
        text = page('actionStatus', d).text
        self.assertIn('SUBMITTED FOR OWNER REVIEW — request ' + d['request']['id'] + ': ' + d['request']['label'] + '.', text)
        self.assertNotIn('has not decided', text)

    def test_the_other_states_are_plain_and_never_say_submitted(self):
        for name, headline in (('expired', 'EXPIRED — NOT SUBMITTED.'), ('superseded', 'REPLACED — NOT SUBMITTED.'), ('cancelled', 'CANCELLED — NOT SUBMITTED.'),
                               ('invalidated', 'NOT SUBMITTED — THE RECORDS CHANGED.')):
            d = fixture(name)['status']
            text = page('actionStatus', d).text
            self.assertIn(headline, text, name)
            self.assertNotIn('SUBMITTED FOR OWNER REVIEW', text, name)
            self.assertNotIn('Confirming submits', text, name)
            self.assertNotIn('Review and confirm', text, name)
            if (d.get('outcome') or {}).get('message'):
                self.assertIn(d['outcome']['message'], text, name)   # the records' own words
        self.assertIn('Prepare it again from the current records.', page('actionStatus', fixture('invalidated')['status']).text)

    def test_a_status_the_card_does_not_know_is_never_read_as_submitted(self):
        for status in ('mystery', None, 5):
            d = deepcopy(fixture('proposed')['status'])
            d['status'] = status
            text = page('actionStatus', d).text
            self.assertIn('STATUS UNAVAILABLE — nothing here shows it was submitted.', text)
            self.assertNotIn('SUBMITTED FOR OWNER', text)
        d = deepcopy(fixture('executed')['status'])
        d['request'] = None   # an executed action whose request the view could not give
        self.assertIn('SUBMITTED FOR OWNER REVIEW — request ' + d['requestId'], page('actionStatus', d).text)

    def test_a_result_without_a_preview_has_no_card(self):
        for result in ({}, {'actionId': 'act_0123456789abcdef'}, {'preview': 'x'}, [], None):
            with self.assertRaises(ValueError):
                card.card_html('actionStatus', result)


class Button(unittest.TestCase):
    def button(self, tool, result, url):
        buttons = [(tag, attrs) for tag, attrs in page(tool, result, url).tags if tag == 'button']
        return buttons

    def test_the_button_opens_exactly_the_contract_url_for_the_actions_own_id(self):
        d = fixture('proposed')
        for origin in (LOCAL, ISOLATED, LOCAL + '/'):
            [(tag, attrs)] = self.button('prepareRequest', d['prepare'], origin)
            self.assertEqual(attrs, {'type': 'button', 'id': 'open', 'data-url': origin.rstrip('/') + '/#/actions/' + d['prepare']['actionId']})
            self.assertRegex(attrs['data-url'], r'^(http://127\.0\.0\.1:(8631|18631)|https://nucleon\.tail492813\.ts\.net:8443|https://nucleon\.dracooz\.top)/#/actions/act_[0-9a-f]{16}$')
        [(tag, attrs)] = self.button('actionStatus', d['status'], LOCAL)   # actionStatus names it `id`
        self.assertEqual(attrs['data-url'], LOCAL + '/#/actions/' + d['status']['id'])
        self.assertIn('Review and confirm in Nucleon', page('prepareRequest', d['prepare']).text)
        for name in ('executed', 'cancelled', 'expired'):   # an action that cannot be confirmed: a button to view it, never to confirm
            [(tag, attrs)] = self.button('actionStatus', fixture(name)['status'], LOCAL)
            self.assertIn('View in Nucleon', page('actionStatus', fixture(name)['status'], LOCAL).text)
            self.assertNotIn('Review and confirm', page('actionStatus', fixture(name)['status'], LOCAL).text)

    def test_no_url_configured_or_one_off_the_contract_means_no_button_and_a_sentence_instead(self):
        d = fixture('proposed')['prepare']
        for url in (None, '', 'https://nucleon.example.org', 'http://127.0.0.1:8630', 'http://localhost:8631', 'http://127.0.0.1:8631/x', 'http://127.0.0.1:8631?a=1',
                    'http://u:p@127.0.0.1:8631', 'http://127.0.0.1:86310', 'http://127.0.0.1:8631/#/', 5, ['http://127.0.0.1:8631']):
            p = page('prepareRequest', d, url)
            self.assertEqual(self.button('prepareRequest', d, url), [], url)
            self.assertNotIn('data-url', card.card_html('prepareRequest', d, url))
            self.assertIn('Open this action in Nucleon to review and confirm it: ' + d['actionId'] + '.', p.text)
            self.assertEqual(''.join(p.scripts), card.SCRIPT)   # no click handler either
            csp = next(a['content'] for t, a in p.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
            self.assertEqual(csp, card.CSP)

    def test_an_action_id_that_does_not_fit_the_contract_is_never_put_in_the_html(self):
        d = fixture('proposed')['prepare']
        for bad in ('act_0123456789ABCDEF', 'act_0123456789abcde', 'act_0123456789abcdef0', 'act_../../x', 'x', '', 'act_0123456789abcdef?x=1',
                    'act_0123456789abcdef#', '<script>', 'act_0123456789abcdef/../../', 7, None, 'ACT_0123456789abcdef', 'act_0123456789abcdeg'):
            r = {**deepcopy(d), 'actionId': bad}
            source = card.card_html('prepareRequest', r, LOCAL)
            self.assertNotIn('data-url', source, bad)
            self.assertNotIn('<button', source, bad)
            if isinstance(bad, str) and len(bad) > 6:
                self.assertNotIn(html.escape(bad, quote=True), source, bad)
        self.assertEqual(card.card_uri('prepareRequest', {**d, 'actionId': '<script>'}), 'ui://nucleon/card/prepareRequest/unknown')

    def test_the_click_handler_is_a_second_fixed_script_allowed_by_its_own_hash_and_runs_only_on_a_click(self):
        d = fixture('proposed')['prepare']
        p = page('prepareRequest', d, LOCAL)
        self.assertEqual(p.scripts, [card.SCRIPT, card.CLICK_SCRIPT])
        csp = next(a['content'] for t, a in p.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
        self.assertEqual(csp, "default-src 'none'; style-src 'unsafe-inline'; script-src " + card.SCRIPT_HASH + ' ' + card.CLICK_HASH + "; base-uri 'none'; form-action 'none'")
        self.assertEqual(csp, card.CSP_WITH_BUTTON)
        self.assertEqual(card.CLICK_HASH, "'sha256-" + __import__('base64').b64encode(hashlib.sha256(card.CLICK_SCRIPT.encode()).digest()).decode() + "'")
        self.assertNotRegex(csp, r"unsafe-eval|script-src[^;]*'unsafe-inline'|connect-src|frame-src|img-src|https?:")
        # the handler: nothing at load; one listener on the button; the url comes from its data attribute; the message is the contract's
        self.assertEqual(re.findall(r'addEventListener\(\'(\w+)\'', card.CLICK_SCRIPT), ['click'])
        self.assertEqual(re.findall(r'postMessage\(', card.CLICK_SCRIPT), ['postMessage('])
        self.assertIn("parent.postMessage({type:'link',payload:{url:u}},'*')", card.CLICK_SCRIPT)
        self.assertNotRegex(card.CLICK_SCRIPT, r'setTimeout|setInterval|fetch|XMLHttp|location|open\(|eval|import|document\.cookie|localStorage')
        self.assertNotIn('127.0.0.1', card.CLICK_SCRIPT + card.SCRIPT)   # no data in any script
        self.assertNotRegex(card.card_html('prepareRequest', d, LOCAL), r'(?i)<form|href=|<a |onclick|javascript:|<iframe|<img|<link')

    def test_the_html_carries_no_token_cookie_or_session(self):
        for name in ('proposed', 'executed', 'invalidated'):
            d = fixture(name)
            for tool, result in (('actionStatus', d['status']),) + ((('prepareRequest', d['prepare']),) if 'prepare' in d else ()):
                source = card.card_html(tool, result, LOCAL)
                self.assertNotRegex(source, r'(?i)bearer|token|cookie|nucleon_staff|nucleon_owner|csrf|session|authorization|idempotency')

    def test_every_value_from_the_result_is_escaped(self):
        d = deepcopy(fixture('executed')['status'])
        evil = '<script>alert(1)</script> & "x" \''
        d['preview']['fromRecords']['customer']['name'] = evil
        d['preview']['fromRecords']['invoice']['reference'] = evil
        d['preview']['draftedByAssistant']['reason'] = evil
        d['request']['label'], d['request']['id'] = evil, evil
        d['status'] = 'executed'
        source = card.card_html('actionStatus', d, LOCAL)
        self.assertNotIn('<script>alert', source)
        self.assertIn(html.escape(evil, quote=True), source)
        p = Page(source)
        self.assertEqual(p.scripts, [card.SCRIPT, card.CLICK_SCRIPT] if 'data-url' in source else [card.SCRIPT])

    def test_the_same_result_gives_the_same_bytes_and_resource_id_after_a_round_trip(self):
        for name in ('proposed', 'executed'):
            d = fixture(name)
            tool, result = ('prepareRequest', d['prepare']) if 'prepare' in d else ('actionStatus', d['status'])
            made = {'uri': card.card_uri(tool, result), 'mimeType': 'text/html', 'text': card.card_html(tool, result, LOCAL)}
            stored = json.loads(json.dumps(made, ensure_ascii=False))
            self.assertEqual(stored, made)
            self.assertEqual(stored['text'], card.card_html(tool, deepcopy(result), LOCAL))
            self.assertRegex(made['uri'], r'^ui://nucleon/card/(prepareRequest|actionStatus)/act_[0-9a-f]{16}$')


class FinancialCardsUnchanged(unittest.TestCase):
    """The customerOverview and invoices cards for the existing fixtures are byte for byte what they were before Phase B (digests made from the
    Phase A code), with or without a public URL in the Lab's config."""
    DIGESTS = {
        'both_complete': '50d733b75980664b', 'both_unconfirmed': '13f03651b000d40c', 'both_unconfirmed_open': 'e5fb5eeb7b44980f', 'contradicted': '7fe8abde3e618a21',
        'earlier_date': 'b3396c0621018ca8', 'filtered': '6cc217db29cd6100', 'invoices_only': 'f2a7620f033c5607', 'long_caveat': '40675c76721c0954',
        'no_invoices': '8ba7c23d7b7bd645', 'no_payments': '7f325f1fd12c89e3', 'payments_only': 'd1196b4dc4196d43', 'unknown_outstanding': 'acb879e4d54854a6',
        'unverified_zero': '49c9991044274645', 'verified_zero': '17f4e0e3e32b088b', 'xss_name': 'aa7867889eb09b8e'}

    def test_digests(self):
        self.assertEqual(set(NAMES), set(self.DIGESTS))
        for name in NAMES:
            d = load_financial(name)
            for url in (None, LOCAL):
                made = card.card_html('customerOverview', d['overview'], url) + '\x00' + card.card_html('invoices', d['invoices'], url)
                self.assertEqual(hashlib.sha256(made.encode()).hexdigest()[:16], self.DIGESTS[name], (name, url))

    def test_the_csp_of_the_financial_cards_is_the_one_it_was(self):
        self.assertEqual(card.CSP, "default-src 'none'; style-src 'unsafe-inline'; script-src " + card.SCRIPT_HASH + "; base-uri 'none'; form-action 'none'")
        self.assertEqual(card.CARD_TOOLS, ('customerOverview', 'invoices', 'prepareRequest', 'actionStatus', 'assessDecision', 'resolveDecision', 'decisionStatus'))   # the decision card is separate (test_decision_card)


class ConfigPublicUrl(unittest.TestCase):
    def test_recordsPublicUrl_is_one_of_the_contract_origins_or_unset(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'lab.json'
            for url, ok in ((None, True), (LOCAL, True), (ISOLATED, True), (LOCAL + '/', True), ('http://127.0.0.1:8630', False), ('https://nucleon.example.org', False), (TAILNET, True),
                            (CLOUDFLARE, True), (CLOUDFLARE + '/', True), ('http://nucleon.dracooz.top', False), ('https://nucleon.dracooz.top:8443', False),
                            ('https://creditease.dracooz.top', False), ('https://dracooz.top', False), ('https://nucleon.dracooz.top.evil.example', False),
                            ('http://nucleon.tail492813.ts.net:8443', False), ('https://nucleon.tail492813.ts.net', False),
                            (5, False), ('http://localhost:8631', False), ('', False)):
                path.write_text(json.dumps({} if url is None else {'recordsPublicUrl': url}))
                if ok:
                    self.assertEqual(load(path)['recordsPublicUrl'], url)
                else:
                    with self.assertRaisesRegex(ValueError, 'recordsPublicUrl'):
                        load(path)


    def test_tailnet_origin_gets_a_button_and_lookalikes_do_not(self):
        result = {'actionId': 'act_0123456789abcdef'}
        self.assertEqual(card.confirm_url(TAILNET, result), TAILNET + '/#/actions/act_0123456789abcdef')
        for url in ('http://nucleon.tail492813.ts.net:8443', 'https://nucleon.tail492813.ts.net', 'https://nucleon.tail492813.ts.net.evil.com:8443',
                    'https://other.tail492813.ts.net:8443', 'https://nucleonXtail492813.ts.net:8443'):
            self.assertIsNone(card.confirm_url(url, result), url)

    def test_cloudflare_origin_gets_a_button_and_other_https_origins_do_not(self):
        result = {'actionId': 'act_0123456789abcdef'}
        self.assertEqual(card.confirm_url(CLOUDFLARE, result), CLOUDFLARE + '/#/actions/act_0123456789abcdef')
        self.assertEqual(card.confirm_url(CLOUDFLARE + '/', result), CLOUDFLARE + '/#/actions/act_0123456789abcdef')
        for url in ('http://nucleon.dracooz.top', 'https://nucleon.dracooz.top:8443', 'https://creditease.dracooz.top', 'https://dracooz.top',
                    'https://evil.dracooz.top', 'https://nucleon.dracooz.top.evil.example', 'https://nucleonXdracooz.top', 'https://user@nucleon.dracooz.top',
                    'https://nucleon.dracooz.top/x', 'https://nucleon.dracooz.top?a=1', 'https://nucleon.example.org', 'https://evil.example'):
            self.assertIsNone(card.confirm_url(url, result), url)

    def test_the_button_of_the_cloudflare_origin_opens_exactly_the_contract_url(self):
        d = fixture('proposed')
        def buttons(url):
            return [attrs for tag, attrs in page('prepareRequest', d['prepare'], url).tags if tag == 'button']
        [attrs] = buttons(CLOUDFLARE)
        self.assertEqual(attrs['data-url'], CLOUDFLARE + '/#/actions/' + d['prepare']['actionId'])
        self.assertEqual(buttons('https://evil.example'), [])   # an unlisted https origin: no button


if __name__ == '__main__':
    unittest.main()
