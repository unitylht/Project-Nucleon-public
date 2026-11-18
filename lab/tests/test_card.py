"""The financial card (lab/card.py) from REAL customerOverview and invoices results of the records (fixtures/card/*.json, made by
make_card_fixtures.py from the prototype's own test scenarios; fictional data, business date Sun 18 Oct 2026). The card shows what the
records said and nothing else: every statement is checked against the result's own fields, never against a second calculation."""
import html
import inspect
import json
import re
import unittest
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

from lab import card

FIX = Path(__file__).resolve().parent / 'fixtures' / 'card'
NAMES = sorted(p.stem for p in FIX.glob('*.json'))
MONEY = re.compile(r'[A-Z]{3} [\d,]+\.\d\d')


def load(name):
    return json.loads((FIX / (name + '.json')).read_text())


class Page(HTMLParser):
    """What a reader sees (text outside script, style and title), and every tag with its attributes."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.visible, self.tags, self.scripts, self._skip = [], [], [], None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._skip = tag if tag in ('script', 'style', 'title') else self._skip

    def handle_endtag(self, tag):
        self._skip = None if tag == self._skip else self._skip

    def handle_data(self, data):
        (self.scripts if self._skip == 'script' else [] if self._skip else self.visible).append(data)

    @property
    def text(self):
        return ' '.join(' '.join(self.visible).split())


def shown(tool, result):
    return Page(card.card_html(tool, result)).text


class CardScenarios(unittest.TestCase):
    def both(self, name):
        d = load(name)
        return d, shown('customerOverview', d['overview']), shown('invoices', d['invoices'])

    def test_1_both_unconfirmed(self):
        d, ov, inv = self.both('both_unconfirmed')
        w = d['overview']['completeness']
        for text in (ov, inv):
            self.assertIn('Unconfirmed', text)
            self.assertNotIn('Confirmed records', text)
            self.assertIn(w['caveatText'], text)   # verbatim
            self.assertEqual(text.count('Not confirmed complete'), 2)
        self.assertIn(d['overview']['owedNow']['amount'], ov)
        self.assertIn('(' + d['overview']['owedNow']['mark'] + ')', ov)
        self.assertIn('Recorded amount ' + d['overview']['owedNow']['amount'], ov)
        self.assertIn('Current account balance not verified.', ov)
        self.assertNotIn('Owed now', ov)
        for r in d['overview']['invoices']:
            self.assertIn(r['reference'] + ' ' + r['amountText'], ov)   # each invoice's own amount text and mark

    def test_2_both_complete(self):
        d, ov, inv = self.both('both_complete')
        for text in (ov, inv):
            self.assertIn('Confirmed records', text)
            self.assertNotIn('Unconfirmed', text)
            self.assertEqual(text.count('Confirmed complete to Sun 18 Oct 2026'), 2)
            self.assertIn(d['overview']['completeness']['caveatText'], text)
        self.assertNotIn('Why unconfirmed', ov)
        self.assertIn('AUD 400.00 (worked out)', ov)   # a worked-out figure stays worked out however complete the records are

    def test_3_invoices_complete_only(self):
        d, ov, inv = self.both('invoices_only')
        for text in (ov, inv):
            self.assertIn('Unconfirmed', text)
            self.assertEqual((text.count('Confirmed complete to Sun 18 Oct 2026'), text.count('Not confirmed complete')), (1, 1))
        self.assertIn('Payment records not confirmed complete', ov)

    def test_4_payments_complete_only(self):
        d, ov, inv = self.both('payments_only')
        for text in (ov, inv):
            self.assertIn('Unconfirmed', text)
            self.assertEqual((text.count('Confirmed complete to Sun 18 Oct 2026'), text.count('Not confirmed complete')), (1, 1))
        self.assertIn('Invoice records not confirmed complete', ov)
        self.assertIn('Invoice records not confirmed complete', Page(card.card_html('invoices', d['invoices'])).text)

    def test_5_confirmed_only_to_an_earlier_date(self):
        d, ov, inv = self.both('earlier_date')
        for text in (ov, inv):
            self.assertEqual(text.count('Confirmed only to Sat 10 Oct 2026'), 2)
            self.assertNotIn('Confirmed complete', text)
            self.assertIn('Unconfirmed', text)
        self.assertIn('Invoice records confirmed only to an earlier date', ov)

    def test_6_contradicted(self):
        d, ov, inv = self.both('contradicted')
        w = d['overview']['completeness']
        self.assertEqual(w['payments']['contradicted'], 1)
        for text in (ov, inv):
            self.assertIn('A confirmation no longer holds (1)', text)
            self.assertIn(w['caveatText'], text)
            self.assertIn('Unconfirmed', text)
        self.assertIn('A payment completeness statement no longer holds', ov)

    def test_7_no_payments(self):
        d, ov, inv = self.both('no_payments')
        self.assertIn('No payments recorded', ov)
        self.assertIn(d['overview']['completeness']['caveatText'], ov)
        self.assertIn('0 recorded', ov)   # the records' own count

    def test_8_no_invoices(self):
        d, ov, inv = self.both('no_invoices')
        self.assertIn('No open invoices shown.', ov)
        self.assertIn('No invoices are recorded.', inv)
        self.assertNotIn('No invoices in this list', ov + inv)
        self.assertIn('No invoices recorded', ov)
        self.assertIn('Unconfirmed', ov)
        self.assertIn('which does not show that none were issued', ov)
        self.assertIn('which does not show that none were issued', inv)

    def test_9_unknown_outstanding_is_never_a_zero(self):
        d = load('unknown_outstanding')
        ov = shown('customerOverview', d['overview'])
        self.assertIn(d['overview']['unmatchedText'], ov)   # money received but not matched to the invoice
        self.assertIn('Unconfirmed', ov)
        self.assertIn('Current account balance not verified.', ov)
        self.assertIn('This does not show the account is settled.', ov)   # a recorded zero on unconfirmed records
        self.assertNotIn('Confirmed records', ov)
        # fields the records did not give: said so, never 0
        gone = deepcopy(load('both_unconfirmed')['overview'])
        gone.pop('owedNow')
        for row in gone['invoices']:
            row.pop('stillOwed'), row.pop('amountText'), row.pop('dueDateText', None), row.pop('dueDate', None)
        text = shown('customerOverview', gone)
        self.assertIn('Balance not established', text)
        self.assertNotIn('Owed now', text)
        self.assertNotIn('Recorded amount', text)
        self.assertEqual(text.count('Not recorded'), 2 * len(gone['invoices']))
        self.assertNotIn('0.00', text)
        self.assertNotIn('AUD', text)
        bare = shown('customerOverview', {'customerId': 'x'})
        self.assertIn('Unconfirmed', bare)
        self.assertIn('Unavailable', bare)
        self.assertNotIn('0.00', bare)

    def test_10_a_verified_zero_differs_from_an_unconfirmed_one(self):
        verified, unverified = load('verified_zero')['overview'], load('unverified_zero')['overview']
        self.assertEqual((verified['owedNow']['amount'], unverified['owedNow']['amount']), ('AUD 0.00', 'AUD 0.00'))   # the records say the same figure
        yes, no = shown('customerOverview', verified), shown('customerOverview', unverified)
        self.assertIn('Confirmed records', yes)
        self.assertNotIn('Unconfirmed', yes)
        self.assertIn('Owed now AUD 0.00 (worked out) Records confirmed complete to Sun 18 Oct 2026.', yes)
        self.assertNotIn('settled', yes)
        self.assertIn('Unconfirmed', no)
        self.assertNotIn('Confirmed records', no)
        self.assertNotIn('Records confirmed complete', no)
        self.assertNotIn('Owed now', no)
        self.assertIn('Recorded amount AUD 0.00 (worked out) Current account balance not verified. This does not show the account is settled.', no)
        self.assertNotEqual(card.card_html('customerOverview', verified), card.card_html('customerOverview', unverified))
        # anything but an explicit true is not confirmed
        for value in (None, 'true', 1, 'yes'):
            odd = deepcopy(verified)
            odd['completeness']['balanceEstablished'] = value
            self.assertIn('Unconfirmed', shown('customerOverview', odd))

    def test_12_filtered_invoices_say_what_they_list(self):
        d = load('filtered')['invoices']
        text = shown('invoices', d)
        self.assertIn(d['scopeText'], text)
        self.assertIn('Invoice list, not the account balance', text)
        self.assertIn('INV-2', text)
        self.assertNotIn('Owed now', text)   # a list has no account figure
        none = deepcopy(d)
        none['invoices'], none['invoiceCount'] = [], 0
        none['filter']['noneText'] = 'No invoice of X has Y as its due date.'
        self.assertIn('No invoice of X has Y as its due date.', shown('invoices', none))
        self.assertEqual(shown('invoices', none).count('No invoice of X has Y'), 1)

    def test_13_a_long_caveat_is_whole(self):
        d = load('long_caveat')
        caveat = d['overview']['completeness']['caveatText']
        self.assertGreater(len(caveat), 250)
        for tool, key in (('customerOverview', 'overview'), ('invoices', 'invoices')):
            self.assertIn(caveat, shown(tool, d[key]))

    def test_14_a_hostile_name_is_text_only(self):
        d = load('xss_name')
        for tool, key in (('customerOverview', 'overview'), ('invoices', 'invoices')):
            source = card.card_html(tool, d[key])
            page = Page(source)
            self.assertIn(d[key]['name'], page.text)
            self.assertNotIn('<script>alert', source)
            self.assertNotIn('<b>X</b>', source)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;Co&quot; &#x27;s', source)
            self.assertEqual([t for t, _ in page.tags if t == 'script'], ['script'])   # only the fixed one
            self.assertEqual(''.join(page.scripts), card.SCRIPT)
        # every string in a result is escaped, in any field
        evil = deepcopy(load('both_unconfirmed')['overview'])
        evil['invoices'][0].update(reference='<img src=x onerror=alert(1)>', amountText='"><svg onload=1>', status='</div><script>1</script>')
        evil['completeness']['caveatText'] = '<script>bad()</script>'
        evil['unmatchedText'] = '<a href="http://evil">x</a>'
        source = card.card_html('customerOverview', evil)
        self.assertEqual(Page(source).text.count('<img src=x onerror=alert(1)>'), 1)
        for bad in ('<img', '<svg', '<script>bad', '<script>1', '<a href'):
            self.assertNotIn(bad, source)


def with_owed(result, owed):
    d = deepcopy(result)
    d.pop('owedNow', None) if owed is ABSENT else d.update(owedNow=owed)
    return d


ABSENT = object()


class CardAmountStates(unittest.TestCase):
    """Zero is not unknown: the three states of the owed-now figure, and each row's own mark. Presentation of the records' fields only."""

    def test_confirmed_records_say_owed_now_and_keep_the_records_mark(self):
        d = load('both_complete')['overview']
        text = shown('customerOverview', d)
        self.assertIn('Owed now AUD 400.00 (worked out) Records confirmed complete to Sun 18 Oct 2026.', text)
        self.assertNotIn('Recorded amount', text)
        self.assertNotIn('Current account balance not verified', text)

    def test_an_amount_on_unconfirmed_records_is_a_recorded_amount_not_a_balance(self):
        for name in ('both_unconfirmed', 'contradicted', 'earlier_date', 'no_payments'):
            d = load(name)['overview']
            text = shown('customerOverview', d)
            o = d['owedNow']
            self.assertIn('Recorded amount ' + o['amount'] + ' (' + o['mark'] + ') Current account balance not verified.', text, name)
            self.assertNotIn('Owed now', text, name)
            self.assertNotIn('does not show the account is settled', text, name)   # only a zero says that

    def test_a_zero_on_unconfirmed_records_is_not_called_settled(self):
        for name in ('unverified_zero', 'unknown_outstanding', 'no_invoices'):
            text = shown('customerOverview', load(name)['overview'])
            self.assertIn('Recorded amount AUD 0.00 (worked out) Current account balance not verified. This does not show the account is settled.', text, name)
        # when the records give minorUnits, that is what is read (no arithmetic either way)
        d = load('both_unconfirmed')['overview']
        self.assertIn('does not show the account is settled', shown('customerOverview', with_owed(d, {**d['owedNow'], 'minorUnits': '0'})))
        zero = load('unverified_zero')['overview']
        self.assertNotIn('does not show the account is settled', shown('customerOverview', with_owed(zero, {**zero['owedNow'], 'minorUnits': '100'})))
        # the confirmed zero says neither
        self.assertNotIn('settled', shown('customerOverview', load('verified_zero')['overview']))

    def test_no_figure_is_balance_not_established_and_never_a_number(self):
        for name in ('both_complete', 'both_unconfirmed'):
            d = {**load(name)['overview'], 'invoices': []}   # no rows, so any amount on the page would be the owed-now figure
            for owed in (ABSENT, None, {}, {'amount': None}, {'amount': ''}, {'amount': 'n/a', 'mark': 'worked out'}, 'AUD 5.00', ['AUD 5.00']):
                text = shown('customerOverview', with_owed(d, owed))
                self.assertIn('Balance not established', text, (name, owed))
                for bad in ('Owed now', 'Recorded amount', 'AUD', '0.00', 'does not show the account is settled', 'worked out)'):
                    self.assertNotIn(bad, text, (name, owed, bad))

    def test_each_row_keeps_its_own_mark_and_a_missing_amount_is_not_recorded(self):
        d = load('both_unconfirmed')['overview']
        text = shown('customerOverview', d)
        for row in d['invoices']:
            self.assertIn(row['reference'] + ' ' + row['amountText'], text)
        self.assertIn('at most, from allocated payments', text)
        self.assertIn('exact as of Sun 18 Oct', shown('customerOverview', load('both_complete')['overview']))
        rows = [{'reference': 'INV-N', 'amountText': 'not recorded', 'mark': 'not recorded', 'status': 'open', 'dueDate': '2026-11-05'},
                {'reference': 'INV-M', 'status': 'open'},
                {'reference': 'INV-S', 'amountText': 'AUD 70.00', 'mark': 'stated', 'status': 'open'},
                {'reference': 'INV-Z', 'amountText': 'AUD 0.00 (worked out)', 'mark': 'worked out', 'status': 'open'}]
        text = shown('customerOverview', {**d, 'invoices': rows})
        self.assertIn('INV-N Not recorded', text)
        self.assertIn('INV-M Not recorded', text)
        self.assertIn('INV-S AUD 70.00 (stated)', text)   # the mark is never dropped
        self.assertIn('INV-Z AUD 0.00 (worked out)', text)   # a worked-out zero stays as the records worded it
        self.assertNotIn('INV-N AUD', text)
        self.assertNotIn('INV-M AUD', text)
        self.assertEqual(text.count('Not recorded'), 2 + 3)   # two amounts, and the missing due dates of the last three

    def test_an_empty_list_says_what_was_asked_not_that_there_are_no_invoices(self):
        d = load('both_unconfirmed')
        empty = lambda r, **k: {**deepcopy(r), 'invoices': [], 'invoiceCount': 0, **k}   # noqa: E731
        self.assertIn('No open invoices shown.', shown('customerOverview', empty(d['overview'])))
        inv = d['invoices']
        for which, said in (('open', 'No open invoices shown.'), ('overdue', 'No overdue invoices shown.'), ('all', 'No invoices are recorded.')):
            self.assertIn(said, shown('invoices', empty(inv, which=which)), which)
        # a filtered list: the backend's own sentence, else a plain one; never "no invoices are recorded"
        f = load('filtered')['invoices']
        text = shown('invoices', empty(f, filter={**f['filter'], 'noneText': 'No invoice of X has Y as its due date.'}))
        self.assertIn('No invoice of X has Y as its due date.', text)
        text = shown('invoices', empty(f))
        self.assertIn('No invoices match this filter.', text)
        self.assertNotIn('No invoices are recorded', text)
        self.assertNotIn('No invoices in this list', text)
        # with invoices there is no such sentence
        self.assertNotRegex(shown('invoices', inv), r'No (open |overdue )?invoices')

    def test_the_scope_text_is_the_backends_and_has_no_instruction_to_the_model(self):
        for name in NAMES:
            d = load(name)['invoices']
            self.assertNotIn('completeness says', d['scopeText'], name)
            self.assertIn(d['scopeText'], shown('invoices', d), name)


ANSWERS = ('Bayside Cafe owes AUD 1,100.00.', 'AUD 1,100.00 - that is the amount owed.')   # simulated final agent answers: the amount, no caveat


class CardOmissionSimulation(unittest.TestCase):
    """AUTOMATED SIMULATION, not a model run: a final answer that states the amount and drops the caveat leaves the card, which does not
    take the answer, showing the caveat. (Whether a real model omits it, and whether the host shows the card, is checked live.)"""

    CASES = ('both_unconfirmed', 'unverified_zero', 'contradicted', 'earlier_date', 'long_caveat', 'no_payments')

    def test_the_card_carries_the_caveat_whatever_the_answer_says(self):
        self.assertEqual(list(inspect.signature(card.card_html).parameters), ['tool', 'result', 'public_url'])   # no way to pass an answer in (public_url is the Lab's config, used by the action cards only)
        for name in self.CASES:
            d = load(name)['overview']
            w = d['completeness']
            self.assertFalse(w['balanceEstablished'])
            self.assertNotEqual(w['invoices']['state'] + w['payments']['state'], 'completecomplete')
            caveat = w['caveatText']
            self.assertTrue(caveat)
            for answer in ANSWERS:
                self.assertNotIn(caveat, answer)   # the simulated answer omits it
            cards = [card.card_html('customerOverview', deepcopy(d)) for _ in ANSWERS]   # made once per answer; nothing of the answer goes in
            self.assertEqual(cards[0], cards[1], name)
            for answer, source in zip(ANSWERS, cards):
                self.assertIn(html.escape(caveat, quote=True), source, name)   # (1) verbatim, in escaped form
                self.assertNotIn(html.escape(answer, quote=True), source)
                self.assertNotIn(answer, source)
                self.assertIn(caveat, Page(source).text, name)
            # (3) the amount and its mark, as the records gave them
            o = d['owedNow']
            self.assertIn(o['amount'] + ' (' + o['mark'] + ')', Page(cards[0]).text, name)
            self.assertIn('Current account balance not verified.', Page(cards[0]).text, name)

    def test_the_stored_resource_renders_the_same_bytes_after_a_round_trip(self):
        """(5) LibreChat stores the tool result's resource item as JSON; the simulated storage is dump and load of {uri, mimeType, text}."""
        for name in self.CASES:
            d = load(name)['overview']
            made = {'uri': card.card_uri('customerOverview', d), 'mimeType': 'text/html', 'text': card.card_html('customerOverview', d)}
            stored = json.loads(json.dumps(made, ensure_ascii=False))
            self.assertEqual(stored, made)
            self.assertEqual(stored['text'].encode(), card.card_html('customerOverview', deepcopy(d)).encode(), name)
            self.assertIn(html.escape(d['completeness']['caveatText'], quote=True), stored['text'])


class CardSafety(unittest.TestCase):
    def test_every_card_is_inert(self):
        for name in NAMES:
            d = load(name)
            for tool, key in (('customerOverview', 'overview'), ('invoices', 'invoices')):
                source = card.card_html(tool, d[key])
                page = Page(source)
                tags = {t for t, _ in page.tags}
                self.assertFalse(tags & {'form', 'button', 'a', 'input', 'img', 'iframe', 'link', 'object', 'embed', 'svg', 'textarea', 'select', 'base'}, (name, tags))
                for tag, attrs in page.tags:
                    self.assertFalse({a for a in attrs if a.startswith('on')} | {'href', 'src', 'action', 'srcset', 'style'} & set(attrs), (name, tag, attrs))
                self.assertNotRegex(source, r'(?i)<form|<button|href=|https?://|javascript:|localhost|127\.0\.0\.1|token|bearer')
                self.assertEqual(''.join(page.scripts), card.SCRIPT)   # the one script is the fixed one
                self.assertEqual(source, card.card_html(tool, deepcopy(d[key])))   # the same result, the same bytes

    def test_the_csp_allows_that_script_by_hash_and_nothing_else(self):
        source = card.card_html('invoices', load('both_unconfirmed')['invoices'])
        csp = next(a['content'] for t, a in Page(source).tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
        self.assertIn("default-src 'none'", csp)
        self.assertIn('script-src ' + card.SCRIPT_HASH, csp)
        self.assertNotIn('unsafe-eval', csp)
        self.assertNotRegex(csp, r"script-src[^;]*'unsafe-inline'")
        self.assertNotRegex(csp, r'connect-src|frame-src|img-src|https?:')

    def test_the_script_only_reports_the_height_as_ui_size_change(self):
        self.assertEqual(re.findall(r'postMessage\(', card.SCRIPT), ['postMessage('])
        self.assertEqual(re.findall(r"type:'([^']+)'", card.SCRIPT), ['ui-size-change'])   # no prompt, tool or link action
        self.assertIn('payload:{height:', card.SCRIPT)
        self.assertIn('width:0', card.SCRIPT)   # the host leaves the width at 100%
        self.assertIn('getBoundingClientRect', card.SCRIPT)   # the card's own height, not the frame's (which could never shrink)
        self.assertNotRegex(card.SCRIPT, r'fetch|XMLHttpRequest|WebSocket|eval\(|innerHTML|document\.write|localStorage|cookie|location')
        self.assertIn('display:flow-root', card.CSS)   # no margin collapses out of the measured box

    def test_nothing_is_added_up_or_made_up(self):
        for name in NAMES:
            d = load(name)
            for tool, key in (('customerOverview', 'overview'), ('invoices', 'invoices')):
                said = json.dumps(d[key], ensure_ascii=False)
                for money in MONEY.findall(shown(tool, d[key])):
                    self.assertIn(money, said, (name, tool))   # every amount on the card is one the records gave

    def test_overview_and_invoices_cards_show_the_same_completeness(self):
        for name in NAMES:
            d = load(name)
            if d['overview']['customerId'] != d['invoices']['customerId'] or 'completeness' not in d['invoices']:
                continue
            self.assertEqual(d['overview']['completeness'], d['invoices']['completeness'], name)
            block = card.completeness_html(d['overview']['completeness'])
            self.assertIn(block, card.card_html('customerOverview', d['overview']))
            self.assertIn(block, card.card_html('invoices', d['invoices']))

    def test_the_important_facts_come_first(self):
        d = load('both_unconfirmed')
        source = card.card_html('customerOverview', d['overview'])
        order = [source.index(x) for x in ('Unconfirmed', d['overview']['owedNow']['amount'], html.escape(d['overview']['completeness']['caveatText'], quote=True),
                                           'Invoice records', '<h2>Invoices</h2>')]
        self.assertEqual(order, sorted(order))

    def test_only_the_two_tools_get_a_card(self):
        for tool in ('findCustomers', 'cases', 'proposeImport'):
            with self.assertRaises(ValueError):
                card.card_html(tool, {})
        with self.assertRaises(ValueError):
            card.card_html('invoices', ['not', 'a', 'dict'])

    def test_a_long_list_is_cut_by_the_card_not_the_result(self):
        d = deepcopy(load('both_unconfirmed')['invoices'])
        d['invoices'] = d['invoices'] * 40
        text = shown('invoices', d)
        self.assertIn('Showing the first 30 of ' + str(len(d['invoices'])) + ' invoices.', text)

    def test_the_resource_uri_names_the_tool_and_customer(self):
        d = load('both_unconfirmed')
        self.assertEqual(card.card_uri('invoices', d['invoices']), 'ui://nucleon/card/invoices/' + d['invoices']['customerId'])
        self.assertEqual(card.card_uri('customerOverview', {}), 'ui://nucleon/card/customerOverview/unknown')



class ExtendedOverdueRow(unittest.TestCase):
    """An extended invoice still counts overdue from its original due date; the row says so in the records' words (Hoang's NTK round, 9 Nov 2026)."""
    def test_the_row_says_where_the_count_starts_and_the_new_date(self):
        inv = {'reference': 'DEMO-702', 'status': 'open', 'dueDate': '2026-11-13', 'daysOverdue': 23, 'amountText': 'AUD 10.00 (worked out)',
               'overdueText': '23 days past the original due date (Thu 1 Oct 2026). Extended to Fri 13 Nov 2026, which has not passed yet.'}
        out = html.unescape(card.invoice_rows_html([inv], 'none'))
        self.assertIn('23 days past the original due date (Thu 1 Oct 2026). Extended to Fri 13 Nov 2026, which has not passed yet.', out)
        self.assertNotIn('23 days overdue', out)

    def test_a_row_without_an_extension_is_unchanged(self):
        out = html.unescape(card.invoice_rows_html([{'reference': 'X', 'status': 'open', 'dueDate': '2026-10-01', 'daysOverdue': 3}], 'none'))
        self.assertIn('3 days overdue', out)

if __name__ == '__main__':
    unittest.main()
