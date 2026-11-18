"""Agent-assisted import (plan 2026-10-21, Task 1): the stdlib .xlsx reader, the ledger splitter, and proposeImport and
applyImportProposal on the tool surface. The fixtures are built here from fictional rows in the shape of a Vietnamese
accounting ledger (title rows above the table, invoice and VAT lines per invoice number, credit rows that are payments, credit
terms, Excel serial dates, customer codes); no real file is used. No real model is called."""
import base64
import io
import json
import unittest
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import importer
import records
import xlsx
from coordinator import CAPABILITIES, tools_for
from model_adapter import AdapterResult
from records import RecordsError
from agent import money_text
import server
from server import DeskTools, IMPORT_PROPOSALS
from test_records import RecordsCase

TODAY = date(2026, 10, 18)
VND = {'currency': 'VND', 'scale': 0, 'timezone': 'Asia/Ho_Chi_Minh', 'businessName': None}


def serial(day):
    return (day - date(1899, 12, 30)).days


class Styled:
    """A number cell with an explicit style index (0: none, 1: the built-in date format 14)."""

    def __init__(self, value, style):
        self.value, self.style = value, style


def column_letter(index):
    letters = ''
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def make_xlsx(sheets, inline=False):
    """A minimal workbook. Text cells are shared strings (inline strings when inline), numbers are numbers, a date is a serial
    styled with a custom day/month/year format, Styled is a number with that style; None leaves the cell out and a row of
    nothing is left out of the sheet."""
    strings, parts = [], {}
    for n, rows in enumerate(sheets.values(), start=1):
        out = []
        for r, row in enumerate(rows, start=1):
            cells = []
            for c, value in enumerate(row):
                ref = column_letter(c) + str(r)
                if value is None:
                    continue
                if isinstance(value, str) and inline:
                    cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(value)))
                elif isinstance(value, str):
                    strings.append(value)
                    cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, len(strings) - 1))
                elif isinstance(value, date):
                    cells.append('<c r="%s" s="2"><v>%d</v></c>' % (ref, serial(value)))
                elif isinstance(value, Styled):
                    cells.append('<c r="%s" s="%d"><v>%s</v></c>' % (ref, value.style, value.value))
                else:
                    cells.append('<c r="%s"><v>%s</v></c>' % (ref, value))
            if cells:
                out.append('<row r="%d">%s</row>' % (r, ''.join(cells)))
        parts['xl/worksheets/sheet%d.xml' % n] = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/'
                                                  'spreadsheetml/2006/main"><sheetData>' + ''.join(out) + '</sheetData></worksheet>')
    main, rel = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    parts['xl/workbook.xml'] = ('<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (main, rel) + ''.join(
        '<sheet name=%s sheetId="%d" r:id="rId%d"/>' % (quoteattr(name), n, n) for n, name in enumerate(sheets, start=1)) + '</sheets></workbook>')
    links = [('rId%d' % n, rel + '/worksheet', 'worksheets/sheet%d.xml' % n) for n in range(1, len(sheets) + 1)]
    links += [('rIdS', rel + '/sharedStrings', 'sharedStrings.xml'), ('rIdT', rel + '/styles', 'styles.xml')]
    parts['xl/_rels/workbook.xml.rels'] = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(
        '<Relationship Id="%s" Type="%s" Target="%s"/>' % x for x in links) + '</Relationships>')
    parts['xl/sharedStrings.xml'] = '<sst xmlns="%s">' % main + ''.join('<si><t>%s</t></si>' % escape(s) for s in strings) + '</sst>'
    parts['xl/styles.xml'] = ('<styleSheet xmlns="%s"><numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy;@"/></numFmts>'
                              '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="164"/></cellXfs></styleSheet>' % main)
    parts['_rels/.rels'] = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" '
                            'Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>' % rel)
    parts['[Content_Types].xml'] = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            z.writestr(name, text)
    return buffer.getvalue()


HEADER = ['Customer_ID', 'Credit Term Days', 'Posting Date', 'Document Date', 'Document Number', 'Invoice Date', 'Invoice Number', 'Description',
          'Debit (Dr)', 'Credit (Cr)']
D = date


def ledger_rows():
    """A fictional receivables ledger in the NTK shape: title rows in Vietnamese, then the table (row 6). Invoice and VAT lines
    share an invoice number; credit rows are payments (one names the invoice it pays); an opening balance, a debit with no
    invoice number, a totals row and a totals label in the customer column are doubtful rows."""
    return [
        ['CÔNG TY TNHH MẪU HƯNG THỊNH (hư cấu)'],
        ['SỔ CHI TIẾT CÔNG NỢ PHẢI THU KHÁCH HÀNG'],
        ['Từ ngày 01/01/2026 đến ngày 30/09/2026'],
        ['Đơn vị tính: VND'],
        [],
        HEADER,
        [None, None, None, None, None, None, None, 'Số dư đầu kỳ', 5000000, None],                                                     # 7
        ['0001', 30, D(2026, 1, 15), D(2026, 1, 15), 'BH0001', D(2026, 1, 15), 'HD0000101', 'Bán hàng hóa', 10000000, None],           # 8
        ['0001', 30, D(2026, 1, 15), D(2026, 1, 15), 'BH0001', D(2026, 1, 15), 'HD0000101', 'Thuế GTGT đầu ra', 1000000, None],        # 9
        ['0002', 45, D(2026, 1, 18), D(2026, 1, 18), 'BH0002', D(2026, 1, 18), 'HD0000102', 'Bán hàng hóa', 4000000, None],            # 10
        ['0002', 45, D(2026, 1, 18), D(2026, 1, 18), 'BH0002', D(2026, 1, 18), 'HD0000102', 'Thuế GTGT đầu ra', 400000, None],         # 11
        ['0001', 30, D(2026, 1, 29), D(2026, 1, 28), 'NH0001', None, 'HD0000101', 'Thu tiền hàng', None, 11000000],                    # 12
        ['0002', 45, D(2026, 2, 2), D(2026, 2, 2), 'NH0002', None, None, 'Thu tiền hàng', None, 2000000],                              # 13
        ['0003', 30, D(2026, 2, 7), D(2026, 2, 7), 'BH0003', D(2026, 2, 7), 'HD0000103', 'Bán hàng', 2500000, None],                   # 14
        ['0003', 30, D(2026, 2, 7), D(2026, 2, 7), 'BH0003', D(2026, 2, 7), 'HD0000103', 'Thuế GTGT đầu ra', 250000, None],            # 15
        ['0003', None, D(2026, 2, 8), D(2026, 2, 8), 'BH0004', D(2026, 2, 8), None, 'Điều chỉnh', 100000, None],                       # 16
        [None, None, None, None, None, None, None, 'Cộng phát sinh', 18250000, 13000000],                                              # 17
        ['Cộng', None, None, None, None, None, None, None, 18350000, 13000000],                                                        # 18
    ]


def ledger_xlsx():
    return make_xlsx({'Hướng dẫn': [['Sổ này là dữ liệu hư cấu.']], 'Sổ chi tiết': ledger_rows()})


INVOICES_CSV = """Customer,Invoice No,Invoice Date,Amount,Due Date
Bayside Café,DEMO-701,01/10/2026,"1,200,000",31/10/2026
Bayside Café,DEMO-702,05/10/2026,800000,
Coastline Foods,DEMO-701,03/10/2026,450000,02/11/2026
Coastline Foods,DEMO-703,06/10/2026,300000,
Coastline Foods,DEMO-703,07/10/2026,300000,
"""

# Vietnamese headings, text dates (day/month) in one date column and Excel serials in two others, as a CSV saved from Excel shows them
VIETNAMESE_CSV = ('Mã khách hàng,Số ngày nợ,Ngày hạch toán,Ngày chứng từ,Số chứng từ,Ngày hóa đơn,Số hóa đơn,Diễn giải,Phát sinh Nợ,Phát sinh Có\n'
                  'KH01,30,46037,46037,BH01,15/01/2026,HD01,Bán hàng,"1,000,000",\n'
                  'KH01,30,46037,46037,BH01,15/01/2026,HD01,Thuế GTGT,"100,000",\n'
                  'KH02,,46055,46055,NH01,,,Thu tiền,,"500,000"\n')


def rows_of(cells):
    return [(n, row) for n, row in enumerate(cells, start=1) if any(str(c).strip() for c in row)]


def no_model(header, samples, fields):
    raise AssertionError('the model is not asked when the headings are known')


class XlsxReaderTests(unittest.TestCase):
    def test_shared_and_inline_strings_numbers_and_dates_by_style(self):
        data = make_xlsx({'Sổ cái': [['Mã', 'Số tiền', 'Ngày'], ['0001', 1250000, D(2026, 1, 15)], [],
                                     [Styled(serial(D(2026, 2, 2)), 1), Styled(46037, 0), 12.5, Styled('1.25E+7', 0)]]})
        book = xlsx.read_workbook(data)
        self.assertEqual(list(book), ['Sổ cái'])
        self.assertEqual(book['Sổ cái'], [['Mã', 'Số tiền', 'Ngày'], ['0001', '1250000', '2026-01-15'], [],
                                          ['2026-02-02', '46037', '12.5', '12500000']])   # an unstyled serial stays a number here
        inline = xlsx.read_workbook(make_xlsx({'A': [['Khách', None, 'x'], [None, 'B2']]}, inline=True))
        self.assertEqual(inline, {'A': [['Khách', '', 'x'], ['', 'B2']]})

    def test_what_is_not_a_workbook_is_refused(self):
        for data in (b'not a zip file', make_xlsx({'A': [['x']]})[:200]):
            with self.assertRaises(RecordsError) as caught:
                xlsx.read_workbook(data)
            self.assertEqual(caught.exception.code, 'INVALID_FILE')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('hello.txt', 'a zip, not a workbook')
        with self.assertRaises(RecordsError):
            xlsx.read_workbook(buffer.getvalue())

    def test_a_doctype_anywhere_in_a_part_is_refused(self):
        src = zipfile.ZipFile(io.BytesIO(make_xlsx({'A': [['x']]})))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            for n in src.namelist():
                data = src.read(n)
                z.writestr(n, data.replace(b'<sheetData>', b'<!-- ' + b'x' * 3000 + b' --><!DOCTYPE a [<!ENTITY b "c">]><sheetData>') if n.endswith('sheet1.xml') else data)
        with self.assertRaises(RecordsError) as caught:
            xlsx.read_workbook(buffer.getvalue())
        self.assertEqual(caught.exception.code, 'INVALID_FILE')


RAW_HEADER = ['CUSTOMER', 'CUSTOMER NAME', 'Ngày hạch toán', 'Ngày chứng từ', 'Số chứng từ', 'Ngày hóa đơn', 'Số hóa đơn', 'DESCRIPTION',
              'TK công nợ', 'TK đối ứng', 'Nợ', 'Có', 'Cong no', 'Thanh toan truoc']
CLEAN_HEADER = ['Source Row', 'Customer_ID', 'Customer_ID Status', 'Credit Term Days', 'Posting Date', 'Document Date', 'Document Number', 'Invoice Date',
                'Invoice Number', 'Description (English)', 'Description Category', 'Invoice Reference Mentioned', 'Contra Account', 'Debit (Dr)',
                'Credit (Cr)', 'Outstanding Debt', 'Advance Payment', 'Net Position After', 'Net Balance Change', 'Record Type', 'Transaction Type']


def raw_rows():
    """A fictional raw export: two title rows, the table at row 3, a group subtotal row in the first column per customer."""
    d = lambda *a: D(*a)
    return [
        ['CÔNG TY MẪU (hư cấu)'], ['SỔ CÔNG NỢ'], RAW_HEADER,
        ['Tên khách hàng : Công ty A'],
        ['0001', 'Công ty A', d(2026, 1, 15), d(2026, 1, 15), 'BH1', d(2026, 1, 15), 'HD1', 'Bán hàng', '131', '511', 1000000, None, None, None],
        ['0001', 'Công ty A', d(2026, 1, 29), d(2026, 1, 28), 'NH1', None, None, 'Thu tiền', '131', '112', None, 400000, None, None],
        [None, None, None, None, None, None, None, 'Cộng Tên khách hàng : Công ty A', None, None, 1000000, 400000, 600000, None],
        ['Tên khách hàng : Công ty B'],
        ['0002', 'Công ty B', d(2026, 2, 3), d(2026, 2, 3), 'BH2', d(2026, 2, 3), 'HD2', 'Bán hàng', '131', '511', 500000, None, None, None],
        [None, 'Công ty B', None, None, None, None, None, 'Cộng', None, None, 500000, None, 500000, None],
    ]


def clean_rows():
    rows = [CLEAN_HEADER]
    for i, (c, inv, debit, credit) in enumerate([('0001', 'HD1', 1000000, None), ('0001', None, None, 400000), ('0002', 'HD2', 500000, None)], start=1):
        row = [None] * len(CLEAN_HEADER)
        row[:] = [i, c, 'known', 30, D(2026, 1, 15), D(2026, 1, 15), 'BH%d' % i, D(2026, 1, 15) if inv else None, inv, 'Sales', 'Sale', None, '511',
                  debit, credit, None, None, None, None, 'Sale', 'Sale']
        rows.append(row)
    return rows


def three_sheets():
    return make_xlsx({'Raw Data': raw_rows(), 'Cleaned Data': clean_rows(), 'Dictionary': [['Column', 'Meaning'], ['CUSTOMER', 'The customer code']]})


class SheetChoiceTests(unittest.TestCase):
    def sheets(self, data):
        return importer.sheets_of({'fileBase64': base64.b64encode(data).decode()})

    def test_the_best_scoring_sheet_is_chosen_not_the_first(self):
        sheets = self.sheets(three_sheets())
        scores = importer.sheet_scores(sheets)
        self.assertEqual([s['name'] for s in scores], ['Raw Data', 'Cleaned Data', 'Dictionary'])
        self.assertEqual([s['headerRow'] for s in scores], [3, 1, None])
        self.assertGreater(scores[1]['score'], scores[0]['score'])
        self.assertEqual(importer.pick_sheet(sheets, None), 'Cleaned Data')
        self.assertEqual(importer.pick_sheet(sheets, 'Raw Data'), 'Raw Data')

    def test_a_workbook_with_data_only_on_the_first_sheet_reads_the_first(self):
        sheets = self.sheets(make_xlsx({'Raw Data': raw_rows(), 'Dictionary': [['Column', 'Meaning']]}))
        self.assertEqual(importer.pick_sheet(sheets, None), 'Raw Data')

    def test_a_tie_goes_to_the_earliest_sheet(self):
        sheets = self.sheets(make_xlsx({'One': clean_rows(), 'Two': clean_rows()}))
        self.assertEqual(importer.pick_sheet(sheets, None), 'One')

    def test_the_raw_vietnamese_ledger_maps_as_a_ledger_and_subtotals_are_left_out(self):
        p = importer.propose(self.sheets(three_sheets())['Raw Data'], {}, no_model, VND, TODAY)
        self.assertEqual((p['shape'], p['headerRow']), ('ledger', 3))
        mapped = {m['field']: m['header'] for m in p['mapping'] if m['column'] is not None}
        self.assertEqual({k: mapped[k] for k in ('customer', 'invoiceNumber', 'issueDate', 'debit', 'credit', 'reference')},
                         {'customer': 'CUSTOMER', 'invoiceNumber': 'Số hóa đơn', 'issueDate': 'Ngày hóa đơn', 'debit': 'Nợ', 'credit': 'Có', 'reference': 'Số chứng từ'})
        self.assertEqual(mapped['paymentDate'], 'Ngày chứng từ')
        self.assertEqual((p['counts']['customers'], p['counts']['invoices'], p['counts']['payments']), (2, 2, 1))
        self.assertEqual({f['row'] for f in p['flaggedRows']}, {4, 7, 8, 10})


class ProposeTests(unittest.TestCase):
    def propose(self, cells, hints=None, classify=no_model):
        return importer.propose(rows_of(cells), hints or {}, classify, VND, TODAY)

    def test_the_ledger_is_split_into_invoices_by_number_and_payments_from_credit_rows(self):
        """Review Focus 2: an invoice's amount is the sum of its debit lines once (VAT lines included, never twice); credit rows
        are payments, never invoices, even when they name the invoice they pay."""
        p = self.propose(xlsx.read_workbook(ledger_xlsx())['Sổ chi tiết'])
        self.assertEqual((p['shape'], p['headerRow'], p['columns']), ('ledger', 6, HEADER))
        self.assertEqual({m['field']: (m['column'], m['by']) for m in p['mapping'] if m['column'] is not None},
                         {'customer': (0, 'header'), 'creditDays': (1, 'header'), 'paymentDate': (3, 'header'), 'reference': (4, 'header'),
                          'issueDate': (5, 'header'), 'invoiceNumber': (6, 'header'), 'description': (7, 'header'), 'debit': (8, 'header'),
                          'credit': (9, 'header')})
        invoices = {i['invoiceNumber']: i for i in p['entries']['invoices']}
        self.assertEqual({k: (i['customer'], i['issueDate'], i['dueDate'], i['amount']['minorUnits'], i['rows']) for k, i in invoices.items()}, {
            'HD0000101': ('Customer 0001', '2026-01-15', '2026-02-14', '11000000', [8, 9]),
            'HD0000102': ('Customer 0002', '2026-01-18', '2026-03-04', '4400000', [10, 11]),
            'HD0000103': ('Customer 0003', '2026-02-07', '2026-03-09', '2750000', [14, 15])})
        debit_lines = [8, 9, 10, 11, 14, 15]
        self.assertEqual(sum(int(i['amount']['minorUnits']) for i in invoices.values()),
                         sum(int(ledger_rows()[n - 1][8]) for n in debit_lines))   # each debit line counted once
        self.assertEqual([(x['customer'], x['date'], x['amount']['minorUnits'], x['reference'], x['invoiceNumber'], x['row']) for x in p['entries']['payments']],
                         [('Customer 0001', '2026-01-28', '11000000', 'NH0001', 'HD0000101', 12), ('Customer 0002', '2026-02-02', '2000000', 'NH0002', None, 13)])
        self.assertEqual({f['row']: f['reason'] for f in p['flags']}, {
            7: 'No customer on this row (an opening balance, a total or a heading?); left out.',
            16: 'A debit with no invoice number; left out.',
            17: 'No customer on this row (an opening balance, a total or a heading?); left out.',
            18: 'Not a customer code like the others (a total or a heading?); left out.'})
        self.assertEqual(p['flaggedRows'][0], {'row': 7, 'reason': p['flags'][0]['reason'], 'cells': ['', '', '', '', '', '', '', 'Số dư đầu kỳ', '5000000', '']})
        self.assertEqual(p['counts'], {'rows': 12, 'customers': 3, 'invoices': 3, 'invoiceLines': 6, 'payments': 2, 'openingBalances': 0, 'flagged': 4})
        self.assertEqual(p['naming'], {'rule': 'code', 'prefix': 'Customer', 'example': 'Customer 0001'})
        self.assertEqual(p['dueDates'], {'rule': 'creditTerm', 'column': 1, 'days': None})
        self.assertEqual((p['needs'], p['samples']), ([], [['', '', '', '', '', '', '', 'Số dư đầu kỳ', '5000000', ''],
                                                          ['0001', '30', '2026-01-15', '2026-01-15', 'BH0001', '2026-01-15', 'HD0000101', 'Bán hàng hóa', '10000000', ''],
                                                          ['0001', '30', '2026-01-15', '2026-01-15', 'BH0001', '2026-01-15', 'HD0000101', 'Thuế GTGT đầu ra', '1000000', '']]))

    def test_a_person_names_the_prefix_the_due_days_and_columns(self):
        rows = xlsx.read_workbook(ledger_xlsx())['Sổ chi tiết']
        p = self.propose(rows, {'customerPrefix': 'NTK', 'mapping': {'creditDays': None, 'paymentDate': 2}, 'creditDays': 10})
        self.assertEqual(sorted({i['customer'] for i in p['entries']['invoices']}), ['NTK 0001', 'NTK 0002', 'NTK 0003'])
        self.assertEqual([i['dueDate'] for i in p['entries']['invoices']], ['2026-01-25', '2026-01-28', '2026-02-17'])
        self.assertEqual(p['dueDates'], {'rule': 'days', 'column': None, 'days': 10})
        self.assertEqual(p['entries']['payments'][0]['date'], '2026-01-29')   # the posting date, as the person chose
        self.assertEqual({m['field']: m['by'] for m in p['mapping'] if m['field'] in ('creditDays', 'paymentDate')}, {'creditDays': 'person', 'paymentDate': 'person'})

    def test_text_dates_and_excel_serials_both_parse_under_vietnamese_headings(self):
        """Review Focus 1: day/month text dates, and serial numbers in a column whose heading names a date."""
        import csv
        p = self.propose(list(csv.reader(io.StringIO(VIETNAMESE_CSV))))
        self.assertEqual((p['shape'], p['needs']), ('ledger', []))
        [invoice] = p['entries']['invoices']
        self.assertEqual((invoice['customer'], invoice['issueDate'], invoice['dueDate'], invoice['amount']['minorUnits']),
                         ('Customer KH01', '2026-01-15', '2026-02-14', '1100000'))
        [payment] = p['entries']['payments']
        self.assertEqual((payment['customer'], payment['date'], payment['amount']['minorUnits'], payment['reference']), ('Customer KH02', '2026-02-02', '500000', 'NH01'))

    def test_a_column_with_mixed_content_is_not_a_date_column(self):
        """Review Focus 1: serial numbers become dates only in a column whose every value is a date."""
        p = self.propose([['Customer', 'Invoice No', 'Invoice Date', 'Amount'], ['Bayside', 'A-1', '46037', '100'], ['Bayside', 'A-2', 'see note', '100'],
                          ['Bayside', 'A-3', '15/01/2026', '100']])
        self.assertEqual(p['shape'], 'invoices')
        self.assertEqual([i['invoiceNumber'] for i in p['entries']['invoices']], ['A-3'])   # a text date still parses
        self.assertEqual({f['row']: f['reason'] for f in p['flags']}, {2: 'The invoice date is not a date; left out.', 3: 'The invoice date is not a date; left out.'})

    def test_a_plain_invoice_list_maps_by_its_headings_and_flags_repeated_numbers(self):
        import csv
        p = self.propose(list(csv.reader(io.StringIO(INVOICES_CSV))))
        self.assertEqual((p['shape'], p['headerRow'], p['needs']), ('invoices', 1, []))
        self.assertEqual([(i['customer'], i['invoiceNumber'], i['issueDate'], i['dueDate'], i['amount']['minorUnits']) for i in p['entries']['invoices']],
                         [('Bayside Café', 'DEMO-701', '2026-10-01', '2026-10-31', '1200000'), ('Bayside Café', 'DEMO-702', '2026-10-05', None, '800000'),
                          ('Coastline Foods', 'DEMO-701', '2026-10-03', '2026-11-02', '450000')])
        self.assertEqual({f['row']: f['reason'] for f in p['flags']}, {5: 'The same invoice number of the same customer is on more than one row; left out.',
                                                                       6: 'The same invoice number of the same customer is on more than one row; left out.'})
        self.assertEqual((p['naming']['rule'], p['entries']['payments'], p['dateOrder']), ('name', [], 'dmy'))

    def test_a_payment_list_is_told_from_an_invoice_list_by_the_columns_it_names(self):
        rows = importer.read_rows((Path(__file__).parent / 'samples' / 'payments-list.csv').read_text())   # names an invoice column too
        p = importer.propose(rows, {}, no_model, {**VND, 'currency': 'AUD', 'scale': 2}, TODAY)
        self.assertEqual((p['shape'], p['needs']), ('payments', []))
        self.assertEqual([(x['customer'], x['date'], x['amount']['minorUnits'], x['reference'], x['invoiceNumber']) for x in p['entries']['payments']][:3],
                         [('Bayside Café', '2026-10-12', '60000', 'EFT 7781', 'INV-1001'), ('Bayside Café', '2026-10-13', '50000', 'EFT 7790', 'INV-1002'),
                          ('Bayside Café', '2026-10-14', '25000', None, None)])
        self.assertEqual(p['flags'], [{'row': 6, 'reason': 'The payment date is not a date; left out.'}])
        self.assertEqual(importer.propose(rows, {'shape': 'invoices'}, no_model, {**VND, 'currency': 'AUD', 'scale': 2}, TODAY)['shape'], 'invoices')

    def test_the_model_classifies_only_unknown_columns_and_its_answers_are_checked_against_the_data(self):
        """Review Focus 4: the model sees the headings and three sample rows only; an answer the data contradicts is not used."""
        cells = [['Buyer', 'Bill #', 'Raised', 'Value', 'Notes'], ['Bayside', 'B-1', '13/09/2026', '1,000', 'x'], ['Bayside', 'B-2', '14/09/2026', '2,000', 'y'],
                 ['Coastline', 'B-3', '15/09/2026', '3,000', ''], ['Coastline', 'B-4', '16/09/2026', '4,000', 'z']]
        asked = []

        def model(answers):
            def classify(header, samples, fields):
                asked.append((header, samples, fields))
                return {'columns': [{'column': c, 'field': f} for c, f in answers]}
            return classify
        wrong = self.propose(cells, classify=model([(0, 'customer'), (1, 'invoiceNumber'), (2, 'amount'), (3, 'issueDate'), (4, 'dueDate'), (0, 'reference')]))
        self.assertEqual(asked[0][:2], (cells[0], cells[1:4]))   # headings and three sample rows, nothing more
        self.assertEqual({m['field']: (m['column'], m['by']) for m in wrong['mapping'] if m['column'] is not None},
                         {'customer': (0, 'model'), 'invoiceNumber': (1, 'model')})
        self.assertEqual(wrong['notes'], ['The model read "Raised" as Invoice amount, but its values are not amounts; it is not used.',
                                          'The model read "Value" as Invoice date, but its values are not dates; it is not used.',
                                          'The model read "Notes" as Due date, but its values are not dates; it is not used.'])
        self.assertEqual(wrong['needs'], ['Choose a column for: Invoice date, Invoice amount.'])
        right = self.propose(cells, classify=model([(0, 'customer'), (1, 'invoiceNumber'), (2, 'issueDate'), (3, 'amount'), (9, 'dueDate')]))
        self.assertEqual((right['needs'], right['counts']['invoices'], right['notes']), ([], 4, []))
        self.assertEqual([m['by'] for m in right['mapping'] if m['column'] is not None], ['model'] * 4)
        mixed = self.propose([['Buyer', 'Bill #', 'Raised', 'Value'], ['Bayside', 'B-1', '46037', '1,000'], ['Bayside', 'B-2', 'soon', '2,000']],
                             classify=model([(0, 'customer'), (1, 'invoiceNumber'), (2, 'issueDate'), (3, 'amount')]))
        self.assertIn('The model read "Raised" as Invoice date, but its values are not dates; it is not used.', mixed['notes'])
        self.propose(xlsx.read_workbook(ledger_xlsx())['Sổ chi tiết'])   # every heading known: the model is not asked (no_model)


class ProposalHelpers(RecordsCase):
    def ready(self, role='owner'):
        self.start()
        self.practice_ready(currency='VND', scale=0, timezone='Asia/Ho_Chi_Minh')

    def tool(self, name, role='staff', key=None, message=None, **args):
        body = {'args': args, **({'message': message} if message is not None else {})}
        status, out, _ = self.call('/api/tools/' + name, body, role, key or name + '-' + json.dumps(args, sort_keys=True)[:120] + str(len(json.dumps(args))))
        self.assertEqual(status, 200, out)
        return out

    def propose(self, role='staff', key=None, **args):
        out = self.tool('proposeImport', role, key, **args)
        self.assertTrue(out['ok'], out)
        return out['result']

    def apply(self, proposal, role='staff', key=None, **args):
        return self.tool('applyImportProposal', role, key, proposalId=proposal['proposalId'], version=proposal['version'], **args)

    def ledger(self, role='staff', key=None):
        return self.propose(role, key, fileBase64=base64.b64encode(ledger_xlsx()).decode(), fileName='so-chi-tiet-cong-no.xlsx')

    def active(self, kind):
        return [r for r in self.app.fixture().get(kind, []) if r.get('status', 'active') == 'active']


class ProposalApiTests(ProposalHelpers):
    def test_staff_propose_and_apply_two_batches_with_exactly_the_previewed_rows_and_revert(self):
        """Review Focus 3 and 4: staff propose and apply; the batches hold exactly the previewed rows; each can be reverted."""
        self.ready()
        p = self.ledger()
        self.assertEqual((p['version'], p['shape'], p['sheet'], [x['name'] for x in p['sheets']], p['ready'], p['counts']['invoices'], p['counts']['payments']),
                         (1, 'ledger', 'Sổ chi tiết', ['Hướng dẫn', 'Sổ chi tiết'], True, 3, 2))
        self.assertEqual((p['preview']['invoices']['new'], p['preview']['payments']['new'], p['counts']['newCustomers']), (3, 2, 3))
        self.assertEqual([f['row'] for f in p['flaggedRows']], [7, 16, 17, 18])
        self.assertNotIn('entries', p)
        model = json.dumps({k: v for k, v in p.items() if k not in ('flaggedRows', 'customers')}, ensure_ascii=False)   # the card's keys aside
        for value in ('HD0000102', 'HD0000103', 'NH0001', 'NH0002', '"0002"', 'Customer 0002', 'Thu tiền hàng', 'Cộng phát sinh', '4400000', '18250000'):
            self.assertNotIn(value, model)   # beyond the headings and three sample rows, only the code's counts and words
        self.assertEqual(self.active('invoices'), [])   # nothing is written by a proposal
        out = self.apply(p)
        self.assertTrue(out['ok'], out)
        batches = out['result']['batches']
        self.assertEqual([(b['shape'], b['counts']['new'], b['revertLink']) for b in batches],
                         [('invoices', 3, '#/imports/' + batches[0]['id']), ('payments', 2, '#/imports/' + batches[1]['id'])])
        self.assertEqual((out['result']['proposalId'], out['result']['version']), (p['proposalId'], 1))
        names = {c['id']: c['name'] for c in self.active('customers')}
        self.assertEqual(sorted(names.values()), ['Customer 0001', 'Customer 0002', 'Customer 0003'])
        self.assertEqual(sorted((names[i['customerId']], i['reference'], i['issueDate'], i['originalDueDate'], i['total']['minorUnits'])
                                for i in self.active('invoices')),
                         [('Customer 0001', 'HD0000101', '2026-01-15', '2026-02-14', '11000000'), ('Customer 0002', 'HD0000102', '2026-01-18', '2026-03-04', '4400000'),
                          ('Customer 0003', 'HD0000103', '2026-02-07', '2026-03-09', '2750000')])
        self.assertEqual(sorted((names[x['customerId']], x['receivedDate'], x['amount']['minorUnits'], x['reference']) for x in self.active('payments')),
                         [('Customer 0001', '2026-01-28', '11000000', 'NH0001'), ('Customer 0002', '2026-02-02', '2000000', 'NH0002')])
        [allocation] = self.active('allocations')   # the credit row named the invoice it pays
        self.assertEqual(allocation['amount']['minorUnits'], '11000000')
        for b, shape in zip(batches, ('invoices', 'payments')):
            stored = self.call('/api/imports/' + b['id'], role='staff')[1]
            self.assertEqual((stored['status'], stored['shape'], stored['sourceLabel']), ('applied', shape, 'Spreadsheet import'))
        again = self.apply(p, key='again')
        self.assertEqual((again['ok'], [b['id'] for b in again['result']['batches']]), (True, [b['id'] for b in batches]))   # idempotent
        for b in reversed(batches):   # the payments first: their allocations hold the invoices
            status, body, _ = self.call('/api/imports/' + b['id'] + '/revert', {'reason': 'Fictional test'}, 'staff', 'rv-' + b['id'])
            self.assertEqual((status, body['status']), (200, 'reverted'), body)
        self.assertEqual((self.active('invoices'), self.active('payments'), self.active('customers')), ([], [], []))

    OPENING_LEDGER = (
        'Customer,Invoice No,Invoice Date,Document Date,Debit,Credit,Record Type,Transaction Type,Outstanding Debt\n'
        'Bayside Café,A1,2026-09-05,2026-09-05,1200000,0,Transaction,Invoice revenue,\n'
        'Bayside Café,,,,0,0,Opening Balance,Opening balance,3500000\n'
        'Bayside Café,,2026-09-20,2026-09-20,0,400000,Transaction,Debt netting,\n')

    def test_an_opening_balance_row_is_written_as_a_third_batch_as_at_the_day_before_the_first_entry_and_reverts(self):
        self.ready()
        p = self.propose(csvText=self.OPENING_LEDGER, fileName='ledger.csv')
        self.assertEqual((p['counts']['openingBalances'], p['preview']['openings']['new']), (1, 1))
        self.assertEqual(p['openingsText'], "1 opening balance as at Fri 4 Sep 2026, the day before the ledger's first entry (the file states no date)")
        reasons = {f['row']: f['reason'] for f in p['flaggedRows']}
        self.assertIn('as at 2026-09-04, the day before the ledger\'s first entry (the file states no date)', reasons[3])
        self.assertIn("debt-netting row of VND 400,000; not imported, so this customer's balance excludes it", reasons[4])
        out = self.apply(p)
        self.assertTrue(out['ok'], out)
        batches = out['result']['batches']
        self.assertEqual([b['shape'] for b in batches], ['invoices', 'openings'])
        [opening] = self.active('openingBalances')
        self.assertEqual((opening['asOf'], opening['amount']['minorUnits'], opening['setBy']['batchId']), ('2026-09-04', '3500000', batches[1]['id']))
        self.assertEqual(self.active('payments'), [])
        doc = self.app.fixture()
        customer = next(c for c in doc['customers'] if c['name'] == 'Bayside Café' and c['status'] == 'active')
        self.assertEqual(records.opening_view(doc, customer['id'])['balance']['minorUnits'], '4700000')   # 3,500,000 opening + the invoice dated after it
        status, body, _ = self.call('/api/imports/' + batches[1]['id'] + '/revert', {'reason': 'Fictional test'}, 'staff', 'rv-open')
        self.assertEqual((status, body['status']), (200, 'reverted'), body)
        self.assertEqual(self.active('openingBalances'), [])
        self.assertEqual(len(self.active('invoices')), 1)

    def test_a_three_sheet_workbook_reads_the_best_sheet_and_the_hint_chooses_another(self):
        self.ready()
        p = self.propose(fileBase64=base64.b64encode(three_sheets()).decode(), fileName='export.xlsx')
        self.assertEqual((p['sheet'], p['headerRow'], p['shape'], [(x['name'], x['headerRow']) for x in p['sheets']]),
                         ('Cleaned Data', 1, 'ledger', [('Raw Data', 3), ('Cleaned Data', 1), ('Dictionary', None)]))
        q = self.propose(proposalId=p['proposalId'], hints={'sheet': 'Raw Data'})
        self.assertEqual((q['version'], q['sheet'], q['headerRow'], q['counts']['invoices'], q['counts']['payments']), (2, 'Raw Data', 3, 2, 1))

    def test_the_file_proposed_again_with_changed_due_dates_previews_updates_without_failing(self):
        """Dry-running an update (an invoice already imported, now with due dates) once failed for want of a time in the author."""
        self.ready()
        first = self.ledger()
        first = self.propose(proposalId=first['proposalId'], hints={'mapping': {'creditDays': None}})
        self.apply(first)
        again = self.ledger(key='again')
        self.assertEqual((again['preview']['invoices']['new'], again['preview']['invoices']['updated']), (0, 3))

    def test_the_owner_too_and_a_stale_version_is_refused(self):
        """Review Focus 3 and 4: a correction makes a new version; the older one is never applied."""
        self.ready()
        p = self.ledger('owner')
        newer = self.propose('owner', proposalId=p['proposalId'], hints={'customerPrefix': 'NTK'})
        self.assertEqual((newer['proposalId'], newer['version'], newer['naming']['example']), (p['proposalId'], 2, 'NTK 0001'))
        stale = self.apply(p, 'owner')
        self.assertEqual((stale['ok'], stale['error'], stale['version']), (False, 'STALE_VERSION', 2))
        self.assertEqual(self.call('/api/imports', role='owner')[1], [])
        out = self.apply(newer, 'owner')
        self.assertTrue(out['ok'], out)
        self.assertEqual(sorted(c['name'] for c in self.active('customers')), ['NTK 0001', 'NTK 0002', 'NTK 0003'])

    def test_corrections_with_the_import_press_make_and_apply_a_new_version(self):
        self.ready()
        p = self.ledger()
        out = self.apply(p, corrections={'mapping': {'paymentDate': 2}})   # the posting date, not the document date
        self.assertTrue(out['ok'], out)
        self.assertEqual(out['result']['version'], 2)
        self.assertEqual(sorted(x['receivedDate'] for x in self.active('payments')), ['2026-01-29', '2026-02-02'])

    def test_records_changed_since_the_proposal_are_refused_until_it_is_proposed_again(self):
        self.ready()
        p = self.ledger()
        self.add_customer('Customer 0001')
        changed = self.apply(p)
        self.assertEqual((changed['ok'], changed['error']), (False, 'RECORDS_CHANGED'))
        self.assertEqual(self.call('/api/imports', role='staff')[1], [])
        again = self.propose(proposalId=p['proposalId'])
        self.assertEqual((again['version'], again['counts']['newCustomers']), (2, 2))
        self.assertTrue(self.apply(again)['ok'])
        self.assertEqual(sorted(c['name'] for c in self.active('customers')), ['Customer 0001', 'Customer 0002', 'Customer 0003'])

    def test_a_plain_invoice_csv_is_one_batch_and_unknown_customers_follow_the_choices(self):
        self.ready()
        bayside = self.add_customer('Bayside Café')
        p = self.propose(csvText=INVOICES_CSV, fileName='invoices.csv', hints={'customers': {'coastline foods': 'skip'}})
        self.assertEqual((p['shape'], p['preview']['invoices']['new'], p['preview']['invoices']['leftOut'], p['preview']['payments']), ('invoices', 2, 1, None))
        out = self.apply(p)
        self.assertEqual([b['shape'] for b in out['result']['batches']], ['invoices'])
        self.assertEqual(sorted((i['customerId'], i['reference']) for i in self.active('invoices')), [(bayside['id'], 'DEMO-701'), (bayside['id'], 'DEMO-702')])
        self.assertEqual([c['name'] for c in self.active('customers')], ['Bayside Café'])

    def test_apply_is_offered_to_no_agent_and_propose_to_both_roles(self):
        self.ready()
        caps = {c['name']: c for c in CAPABILITIES}
        self.assertEqual((caps['proposeImport']['kind'], caps['proposeImport']['roles'], caps['proposeImport']['needsConfirmation']), ('prepare', ['staff', 'owner'], True))
        self.assertEqual((caps['applyImportProposal']['kind'], caps['applyImportProposal']['roles'], caps['applyImportProposal']['pressedBy'],
                          caps['applyImportProposal']['needsConfirmation']), ('act', [], ['staff', 'owner'], True))
        for role in ('staff', 'owner'):
            offered = [t['function']['name'] for t in tools_for(role, None)]
            listed = [t['name'] for t in self.call('/api/tools', role=role)[1]['tools']]
            self.assertIn('proposeImport', offered)
            self.assertNotIn('applyImportProposal', offered + listed)
            self.assertIn('proposeImport', listed)
        self.assertNotIn('applyImportProposal', [t['name'] for t in self.call('/api/agent-tools', role='owner')[1]['tools']])
        p = self.ledger()
        with self.app.lock:   # as the desk agent runs its tools: the apply is refused and nothing is written
            desk = DeskTools(self.app, {'role': 'staff', 'id': 'staff_demo'}, 'import it', TODAY, None, 10)
            outcome = desk.execute('applyImportProposal', {'proposalId': p['proposalId'], 'version': 1})
        self.assertEqual((outcome.ok, outcome.error), (False, 'FORBIDDEN'))
        self.assertEqual(self.active('invoices'), [])

    def test_the_model_is_sent_headings_and_three_rows_and_when_unreachable_nothing_is_proposed(self):
        """Review Focus 4: only the headings and three sample rows go to the model; counts are the code's."""
        sent = []

        class Classifier:
            def respond(self, task, messages, tools=None, schema=None, timeout=None):
                sent.append((task, messages))
                return AdapterResult('structured_output', value={'columns': [{'column': 0, 'field': 'customer'}, {'column': 1, 'field': 'invoiceNumber'},
                                                                             {'column': 2, 'field': 'issueDate'}, {'column': 3, 'field': 'amount'}]})
        self.start(adapter=Classifier(), mode='live')
        self.practice_ready(currency='VND', scale=0, timezone='Asia/Ho_Chi_Minh')
        text = 'Buyer,Bill #,Raised,Value\n' + ''.join('Buyer %d,B-%d,1%d/10/2026,%d000\n' % (n, n, n, n) for n in range(1, 6))
        p = self.propose(csvText=text, fileName='odd.csv')
        [(task, messages)] = sent
        self.assertEqual(task, 'classify_columns')
        said = json.dumps(messages, ensure_ascii=False)
        self.assertIn('Buyer 3', said)
        self.assertNotIn('Buyer 4', said)
        self.assertNotIn('B-5', said)
        self.assertEqual(({m['field']: m['by'] for m in p['mapping'] if m['column'] is not None}, p['counts']['invoices']),
                         ({'customer': 'model', 'invoiceNumber': 'model', 'issueDate': 'model', 'amount': 'model'}, 5))
        self.restart(mode='unavailable')
        out = self.tool('proposeImport', csvText=text, fileName='odd.csv', key='down')
        self.assertEqual((out['ok'], out['error']), (False, 'MODEL_UNAVAILABLE'))
        self.assertTrue(self.ledger(key='known-headings')['ready'])   # every heading known: no model call is needed

    def test_rows_pasted_in_the_person_s_message_are_proposed_from_and_nothing_is_imported(self):
        self.ready()
        out = self.tool('proposeImport', message='Import this ledger:\n' + VIETNAMESE_CSV, key='msg-1')
        self.assertTrue(out['ok'], out)
        p = out['result']
        self.assertEqual((p['counts']['invoices'], p['counts']['payments'], p['counts']['customers']), (1, 1, 2))
        self.assertEqual((self.active('invoices'), self.call('/api/imports', role='staff')[1]), ([], []))   # a person presses Import
        out = self.tool('proposeImport', message='Import my spreadsheet please', key='msg-2')
        self.assertEqual(out['ok'], False)   # no attachment and no rows in the message: nothing to read

    def test_files_are_checked_before_they_are_read(self):
        self.ready()
        for n, args in enumerate(({'fileBase64': 'not base64!'}, {'fileBase64': base64.b64encode(b'PK\x03\x04broken').decode()},
                                  {'csvText': 'only a heading'}, {'proposalId': 'proposal_unknown'}, {'csvText': INVOICES_CSV, 'hints': {'shape': 'recipes'}})):
            out = self.tool('proposeImport', key='bad' + str(n), **args)
            self.assertEqual((out['ok'], out['error']), (False, ('INVALID_FILE', 'INVALID_FILE', 'INVALID_FILE', 'NOT_FOUND', 'INVALID_ARGUMENT')[n]), args)
        big = base64.b64encode(b'a,b\n' * 700_000).decode()
        status, out, _ = self.call('/api/tools/proposeImport', {'args': {'fileBase64': big}}, 'staff', 'big')
        self.assertEqual((status, out.get('error')), (200, 'INVALID_FILE'), out)

    def test_five_proposals_are_kept_and_a_new_one_supersedes_the_others_files(self):
        self.ready()
        first = self.propose(key='k0', csvText=INVOICES_CSV)
        ids = [first['proposalId']] + [self.propose(key='k%d' % n, csvText=INVOICES_CSV)['proposalId'] for n in range(1, 6)]
        with self.app.lock:
            kept = {k: self.app.meta(k) for k in [IMPORT_PROPOSALS + i for i in ids]}
        self.assertEqual([bool(kept[IMPORT_PROPOSALS + i]) for i in ids], [False] + [True] * 5)   # the oldest of six is gone
        self.assertEqual([bool(kept[IMPORT_PROPOSALS + i]['file']) for i in ids[1:]], [False] * 4 + [True])   # only the newest keeps its file
        self.assertEqual(kept[IMPORT_PROPOSALS + ids[1]]['view']['counts']['invoices'], first['counts']['invoices'])   # the summary stays
        out = self.tool('proposeImport', key='again', proposalId=ids[1])
        self.assertEqual((out['ok'], out['error']), (False, 'NOT_FOUND'))
        self.assertTrue(self.propose(key='again2', proposalId=ids[5], hints={'creditDays': 10})['version'] == 2)


# ---------------------------------------------------------------- import correctness (week 7 core flow, task 2)

VI_HEADER = ['Mã khách hàng', 'Số ngày nợ', 'Ngày hạch toán', 'Số chứng từ', 'Số hóa đơn', 'Diễn giải', 'Nợ', 'Có']
CUSTOMER_OF = {11: 1, 12: 1, 13: 1, 14: 2, 15: 2, 16: 3, 17: 3, 18: 4, 19: 4, 20: 4, 21: 5, 22: 5, 23: 6, 24: 6, 25: 6}
# (customer, description, amount): n * 110000 is invoice n's total (goods n * 100000 and VAT n * 10000)
VI_PAYMENTS = [(1, 'Thu tiền hàng HĐ 11', 1210000), (1, 'Thu tiền hàng HĐ 12, 13', 2000000), (2, 'Công ty X thanh toán hóa đơn số 14', 1540000),
               (2, 'Thu tiền hàng HĐ 15', 5000000), (3, 'Thu tiền', 500000), (3, 'Thu tiền hàng HD16', 1760000), (4, 'Thu tiền hàng inv 18', 1980000),
               (5, 'Thu tiền hàng HĐ 99', 300000), (6, 'Thu tiền theo số HĐ 23', 2530000), (6, '', 100000)]


def vi_rows():
    """A fictional Vietnamese ledger: 15 invoices with a goods and a VAT line, ten payments whose descriptions name an invoice
    (HĐ 11, hóa đơn số 14, HD16, inv 18, số HĐ 23), two (HĐ 12, 13), one that does not exist (HĐ 99), one larger than its invoice
    (HĐ 15) and two that name nothing."""
    rows = [['SỔ CHI TIẾT CÔNG NỢ (hư cấu)'], [], VI_HEADER]
    for n, c in CUSTOMER_OF.items():
        for text, amount in (('Bán hàng hóa', n * 100000), ('Thuế GTGT', n * 10000)):
            rows.append(['%04d' % c, 30, D(2026, 1, n), 'BH%d' % n, str(n), text, amount, None])
    for k, (c, text, amount) in enumerate(VI_PAYMENTS):
        rows.append(['%04d' % c, 30, D(2026, 3, 1 + k), 'NH%d' % k, None, text, None, amount])
    return rows


def vi_xlsx():
    return make_xlsx({'Sổ': vi_rows()})


class UnitAndReferenceTests(unittest.TestCase):
    def test_the_unit_is_read_from_a_token_a_currency_column_or_vietnamese_headings(self):
        self.assertEqual(importer.detect_unit(VI_HEADER, []), {'detected': 'VND', 'basis': 'the headings are in Vietnamese'})
        self.assertEqual(importer.detect_unit(['Customer', 'Amount (VND)'], [])['detected'], 'VND')
        self.assertEqual(importer.detect_unit(['Customer', 'Số tiền (đ)'], [])['detected'], 'VND')
        self.assertEqual(importer.detect_unit(['Customer', 'Amount ($)'], []), {'detected': 'dollar', 'basis': 'a dollar sign in the headings'})
        self.assertEqual(importer.detect_unit(['Customer', 'Amount', 'Currency'], [['a', '5', 'vnd'], ['b', '6', 'VND']])['detected'], 'VND')
        self.assertEqual(importer.detect_unit(['Customer', 'Amount', 'Currency'], [['a', '5', 'AUD'], ['b', '6', 'VND']])['detected'], None)
        none = importer.detect_unit(['Customer', 'Invoice', 'Amount'], [['a', '1', '5']])
        self.assertEqual(none['detected'], None)
        self.assertIn('names a currency', none['basis'])

    def test_the_unit_is_read_from_the_headings_of_any_sheet_of_the_workbook(self):   # live test L11a
        sheets = importer.sheets_of({'fileBase64': base64.b64encode(three_sheets()).decode()})
        AUD = {**VND, 'currency': 'AUD', 'scale': 2}
        alone = importer.propose(sheets['Cleaned Data'], {}, no_model, AUD, TODAY)
        self.assertIsNone(alone['unit']['detected'])
        whole = importer.propose(sheets['Cleaned Data'], {}, no_model, AUD, TODAY, {k: v for k, v in sheets.items() if k != 'Cleaned Data'})
        self.assertEqual(whole['unit']['detected'], 'VND')
        self.assertIn('Raw Data', whole['unit']['basis'])

    def test_whole_amounts_in_the_millions_are_a_doubtful_unit_where_cents_are_kept(self):   # live test L11b
        AUD = {**VND, 'currency': 'AUD', 'scale': 2}
        head = ['Customer', 'Invoice No', 'Invoice Date', 'Amount']
        big = importer.propose(rows_of([head, ['Bayside Café', 'A1', '15/10/2026', '1,200,000'], ['Bayside Café', 'A2', '16/10/2026', '800000']]), {}, no_model, AUD, TODAY)
        self.assertEqual(big['unit'], {'detected': None, 'doubtful': True, 'basis': 'whole numbers in the millions, no decimals'})
        for rows in ([head, ['Bayside Café', 'A1', '15/10/2026', '1,200.50']], [head, ['Bayside Café', 'A1', '15/10/2026', '1,200']],
                     [head, ['Bayside Café', 'A1', '15/10/2026', '12,000.50']]):
            self.assertFalse(importer.propose(rows_of(rows), {}, no_model, AUD, TODAY)['unit'].get('doubtful'))
        self.assertFalse(importer.propose(rows_of([head, ['Bayside Café', 'A1', '15/10/2026', '1,200,000']]), {}, no_model, VND, TODAY)['unit'].get('doubtful'))

    def test_a_reference_is_read_from_the_description_or_the_reference_cell(self):
        ref = importer.invoice_reference_from
        for text in ('Thu tiền hàng HĐ 73', 'Công ty X thanh toán hóa đơn số 73', 'HD73', 'invoice 73', 'Inv 73', 'Thu theo số HĐ 73', 'Invoice No. 73 paid'):
            self.assertEqual(ref(text, ''), ['73'], text)
        self.assertEqual(ref('Thu tiền hàng HĐ 12, 13', ''), ['12', '13'])
        self.assertEqual(ref('Thu HĐ 12 và 13', ''), ['12', '13'])
        for text in ('Thu tiền', '', 'Investment 5', 'Công ty X thanh toán'):
            self.assertEqual(ref(text, ''), [], text)
        self.assertEqual(ref('Thu tiền', '73'), ['73'])   # an explicit column wins
        self.assertEqual(ref('Thu HĐ 5', 'HĐ 73'), ['73'])
        self.assertEqual(ref('', 'HD73'), ['73'])   # a spaceless cell is read too
        self.assertEqual(ref('', '12,13'), ['12', '13'])
        self.assertEqual(ref('', 'A/2026/5'), ['A/2026/5'])   # nothing named: the raw cell


class ImportCorrectnessTests(ProposalHelpers):
    def vi(self, role='staff', key=None, **extra):
        return self.propose(role, key, fileBase64=base64.b64encode(vi_xlsx()).decode(), fileName='so-cong-no.xlsx', **extra)

    def position(self, name):
        doc = self.app.fixture()
        c = next(c for c in doc['customers'] if c['name'] == name and c['status'] == 'active')
        return records.customer_position(doc, c['id'], records.settings_of(doc))

    def stored(self, proposal):
        with self.app.lock:
            return self.app.meta(IMPORT_PROPOSALS + proposal['proposalId'])

    def live(self, proposal, role='staff'):
        status, body, _ = self.call('/api/records/imports/proposals/' + proposal['proposalId'], role=role)
        self.assertEqual(status, 200, body)
        return body

    def test_a_vietnamese_ledger_into_an_aud_workspace_is_refused_and_nothing_is_written(self):
        """Review Focus 2."""
        self.start()
        self.practice_ready()   # AUD, 2 decimal places
        p = self.vi()
        self.assertEqual((p['unit'], p['workspace']), ({'detected': 'VND', 'basis': 'the headings are in Vietnamese'}, {'currency': 'AUD', 'scale': 2}))
        out = self.apply(p)
        self.assertEqual((out['ok'], out['error']), (False, 'UNIT_MISMATCH'))
        self.assertEqual(out['message'], 'The file\'s amounts look like VND; these records are kept in AUD. Nothing was imported. Start a workspace in VND, or convert the file.')
        doc = self.app.fixture()
        self.assertEqual([len(doc.get(k, [])) for k in ('customers', 'invoices', 'payments', 'allocations')], [0, 0, 0, 0])
        self.assertEqual(self.call('/api/imports', role='staff')[1], [])
        body = self.live(p)['proposal']
        self.assertEqual((body['status'], body['lastError']), ('refused', out['message']))
        self.assertEqual(body['batches'], [])

    def old_shape(self, p, keep_file=True):   # a proposal stored by the build before the unit rules
        s = self.stored(p)
        s.pop('unitRules', None)
        s['view']['unit'] = {'detected': None, 'basis': 'no heading or column in the file names a currency'}
        s['view']['unitProblem'] = None
        if not keep_file:
            s['file'] = None
        with self.app.lock, self.app.db:
            self.app.set_meta(IMPORT_PROPOSALS + p['proposalId'], s)

    def test_a_proposal_made_before_the_unit_rules_is_checked_again_from_its_file(self):
        self.start()
        self.practice_ready()
        p = self.vi()
        self.assertEqual(self.stored(p)['unitRules'], server.UNIT_RULES)
        self.old_shape(p)
        body = self.live(p)
        self.assertEqual(body['proposal']['unit']['detected'], 'VND')
        self.assertIn('look like VND', body['view']['unitProblem'])
        out = self.apply(p)
        self.assertEqual((out['ok'], out['error']), (False, 'UNIT_MISMATCH'))
        self.assertEqual(len(self.app.fixture().get('invoices', [])), 0)

    def test_a_proposal_made_before_the_unit_rules_without_its_file_is_stale(self):
        self.start()
        self.practice_ready()
        p = self.vi()
        self.old_shape(p, keep_file=False)
        body = self.live(p)['proposal']
        self.assertEqual((body['status'], body['message']), ('stale', server.STALE_PROPOSAL))
        out = self.apply(p)
        self.assertEqual((out['ok'], out['error'], out['message']), (False, 'STALE_PROPOSAL', server.STALE_PROPOSAL))
        self.assertEqual(self.live(p)['proposal']['status'], 'stale')

    def test_a_mismatch_is_on_the_proposal_before_anyone_presses_import(self):
        self.start()
        self.practice_ready()
        body = self.live(self.vi())
        self.assertEqual(body['proposal']['status'], 'proposed')
        self.assertIn('look like VND', body['view']['unitProblem'])

    def test_a_doubtful_unit_is_on_the_proposal_and_apply_refuses_it(self):   # live test L11b
        self.start()
        self.practice_ready()
        p = self.propose(csvText='Customer,Invoice No,Invoice Date,Amount\nBayside Café,A1,15/10/2026,"1,200,000"\n')
        self.assertTrue(p['unit']['doubtful'])
        self.assertNotIn('does not say its currency', ' '.join(p['notes']))
        out = self.apply(p)
        self.assertEqual((out['ok'], out['error']), (False, 'UNIT_MISMATCH'))
        self.assertEqual(out['message'], 'The file\'s amounts look like a zero-decimal currency; these records are kept in AUD with cents. Nothing was imported. '
                         'Start a workspace in that currency, or convert the file.')
        self.assertEqual(self.active('invoices'), [])

    def test_an_unlabelled_file_imports_as_the_workspace_currency_and_says_so(self):
        self.start()
        self.practice_ready()
        p = self.propose(csvText='Customer,Invoice No,Invoice Date,Amount\nBayside Café,A1,15/10/2026,"1,200.00"\n')
        self.assertEqual(p['unit']['detected'], None)
        self.assertIn('The file does not say its currency; amounts are taken as AUD.', p['notes'])
        self.assertTrue(self.apply(p)['ok'])
        [invoice] = self.active('invoices')
        self.assertEqual((invoice['total']['currency'], invoice['total']['minorUnits']), ('AUD', '120000'))

    def test_a_dollar_invoice_csv_fits_an_aud_workspace(self):
        csv_text = 'Customer,Invoice No,Invoice Date,Amount ($)\nBayside Café,A1,15/10/2026,"1,200.00"\n'
        self.start()
        self.practice_ready()
        self.assertTrue(self.apply(self.propose(csvText=csv_text))['ok'])
        self.assertEqual(self.active('invoices')[0]['total']['currency'], 'AUD')

    def test_a_dollar_invoice_csv_fits_a_usd_workspace(self):
        csv_text = 'Customer,Invoice No,Invoice Date,Amount ($)\nBayside Café,A1,15/10/2026,"1,200.00"\n'
        self.start()
        self.practice_ready(currency='USD')
        p = self.propose(csvText=csv_text)
        self.assertEqual(p['unit']['detected'], 'dollar')
        self.assertTrue(self.apply(p)['ok'])
        self.assertEqual(self.active('invoices')[0]['total']['currency'], 'USD')

    def test_a_dollar_invoice_csv_is_refused_by_a_vnd_workspace(self):
        self.start()
        self.practice_ready(currency='VND', scale=0, timezone='Asia/Ho_Chi_Minh')
        out = self.apply(self.propose(csvText='Customer,Invoice No,Invoice Date,Amount ($)\nBayside Café,A1,15/10/2026,1200\n'))
        self.assertEqual((out['error'], out['message'][:37]), ('UNIT_MISMATCH', "The file's amounts look like dollars;"))

    def test_the_same_ledger_into_a_vnd_workspace_writes_whole_units_and_shows_no_decimals(self):
        """Review Focus 2."""
        self.ready()
        p = self.vi()
        self.assertEqual(p['workspace'], {'currency': 'VND', 'scale': 0})
        self.assertTrue(self.apply(p)['ok'])
        invoices = {i['reference']: i for i in self.active('invoices')}
        self.assertEqual(len(invoices), 15)
        self.assertEqual(invoices['11']['total'], {'currency': 'VND', 'scale': 0, 'minorUnits': '1210000'})
        self.assertEqual(money_text(invoices['11']['total']), 'VND 1,210,000')
        status, body, _ = self.call('/api/tools/invoices', {'args': {'customerId': invoices['11']['customerId'], 'which': 'all'}}, 'staff', 'inv-text')
        [row] = [r for r in body['result']['invoices'] if r['invoiceId'] == invoices['11']['id']]
        self.assertEqual(row['amountText'], 'VND 0 (at most, from allocated payments)')   # HĐ 11 was paid in full: whole units, no decimals
        self.assertNotIn('.', row['amountText'])
        for payment in self.active('payments'):
            self.assertRegex(payment['amount']['minorUnits'], r'^\d+$')

    def test_payments_naming_an_invoice_are_matched_and_the_rest_counted_and_the_balance_is_unchanged(self):
        """Review Focus 3."""
        self.ready()
        p = self.vi()
        self.assertEqual(p['references'], {'payments': 10, 'named': 7, 'matched': 6, 'unmatched': 4, 'multiple': 1,
                                       'unmatchedReasons': {'noReference': 2, 'notInFile': 1, 'otherCustomer': 0, 'ambiguous': 0, 'multiple': 1, 'issuedAfter': 0}})
        self.assertIn('6 of them match an invoice in this file and will be matched; 1 name an invoice not in this file; 3 stay without a reference', p['referencesText'])
        self.assertIn('This payment names several invoices; left unmatched.', [f['reason'] for f in p['flags']])
        self.assertTrue(self.apply(p)['ok'])
        allocations = self.active('allocations')
        self.assertEqual(len(allocations), 6)
        by_invoice = {a['invoiceId']: int(a['amount']['minorUnits']) for a in allocations}
        invoices = {i['id']: i['reference'] for i in self.active('invoices')}
        self.assertEqual(sorted((invoices[k], v) for k, v in by_invoice.items()),
                         [('11', 1210000), ('14', 1540000), ('15', 1650000), ('16', 1760000), ('18', 1980000), ('23', 2530000)])   # HĐ 15: only what it owed
        first, second = self.position('Customer 0001'), self.position('Customer 0002')
        self.assertEqual(first['recordedNet']['minorUnits'], str(11 * 110000 + 12 * 110000 + 13 * 110000 - 1210000 - 2000000))
        self.assertEqual(first['unallocated']['minorUnits'], '2000000')   # HĐ 12, 13: flagged, not allocated
        self.assertEqual((second['unallocated']['minorUnits'], second['recordedNet']['minorUnits']), ('3350000', '-3350000'))   # the part above HĐ 15
        self.assertEqual(self.position('Customer 0005')['unallocated']['minorUnits'], '300000')   # HĐ 99 does not exist

    def test_the_wording_names_the_basis_and_the_unmatched_amount(self):
        self.ready()
        self.assertTrue(self.apply(self.vi())['ok'])
        doc = self.app.fixture()
        two = next(c for c in doc['customers'] if c['name'] == 'Customer 0002')
        out = self.tool('customerOverview', customerId=two['id'])
        self.assertIn('VND 3,350,000', out['result']['notAllocated']['amountText'])
        self.assertIn('received, not matched to an invoice', out['result']['notAllocated']['amountText'])
        six = next(c for c in doc['customers'] if c['name'] == 'Customer 0006')
        rows = self.tool('invoices', customerId=six['id'], which='all')['result']['invoices']
        self.assertIn('from allocated payments', next(r for r in rows if r['reference'] == '23')['amountText'])

    def test_the_same_file_twice_is_a_duplicate_and_not_applicable(self):
        """Review Focus 5."""
        self.ready()
        first, second = self.vi(), self.vi(key='again')
        self.assertTrue(self.apply(first)['ok'])
        self.assertEqual(self.live(second)['proposal']['status'], 'duplicate')   # proposed before the first was applied
        out = self.apply(second, key='second')
        self.assertEqual((out['ok'], out['error']), (False, 'DUPLICATE'))
        self.assertEqual(len(self.active('invoices')), 15)
        third = self.vi(key='third')
        state = self.live(third)
        live = state['proposal']
        self.assertEqual(live['status'], 'duplicate')
        self.assertIn('This file was imported on', live['message'])
        self.assertIn('15 invoices, 10 payments', live['message'])
        # the real clock with its time zone, apart from the business date the records were on (the sample's fixed date here)
        self.assertRegex(live['message'], r'^This file was imported on \d{1,2} \w{3} 2\d{3}, \d{2}:\d{2} (?:[A-Z]{2,5}|UTC[+-]\d{2}:\d{2}) \(business date \w{3} \d{1,2} \w{3} 2\d{3}\): ')
        self.assertIn('(business date ' + server.display_date(self.stored(first)['appliedOn']) + ')', live['message'])
        # its references were matched when it was imported: never "0 of them match … name an invoice not in this file"
        self.assertEqual((third['referencesText'], state['view']['referencesText']), (server.ALREADY_MATCHED, server.ALREADY_MATCHED))
        self.assertEqual(self.live(first)['proposal']['appliedAtText'], server.imported_text(self.stored(first), 'Asia/Ho_Chi_Minh'))
        self.assertEqual(server.clock_text('2026-10-23T15:04:00+00:00', 'Australia/Sydney'), '24 Oct 2026, 02:04 AEDT')
        self.assertEqual(server.clock_text('2026-10-23T15:04:00+00:00', 'Asia/Ho_Chi_Minh'), '23 Oct 2026, 22:04 UTC+07:00')
        self.assertTrue(self.stored(first)['sha256'])   # kept after the file is cleared
        self.assertIsNone(self.stored(first)['file'])

    def test_a_reverted_import_reads_reverted_and_the_same_file_proposed_again_can_be_applied(self):
        self.ready()
        first = self.vi()
        batches = self.apply(first)['result']['batches']
        for b in reversed(batches):   # the payments first
            self.assertEqual(self.call('/api/imports/' + b['id'] + '/revert', {'reason': 'Fictional test'}, 'staff', 'rv-' + b['id'])[0], 200)
        live = self.live(first)['proposal']
        self.assertEqual((live['status'], live['batches'], bool(live['appliedAt']), bool(live['revertedAt'])), ('reverted', batches, True, True))
        again = self.vi(key='again')
        self.assertEqual(self.live(again)['proposal']['status'], 'proposed')   # not a duplicate: nothing of it is imported now
        self.assertTrue(self.apply(again, key='apply-again')['ok'])
        self.assertEqual(len(self.active('invoices')), 15)
        self.assertEqual(self.live(first)['proposal']['status'], 'reverted')

    def test_import_pressed_twice_returns_the_same_batches(self):
        """Review Focus 5."""
        self.ready()
        p = self.vi()
        one, two = self.apply(p), self.apply(p, key='twice')
        self.assertTrue(two['ok'], two)
        self.assertEqual(one['result']['batches'], two['result']['batches'])
        self.assertEqual(len(self.active('invoices')), 15)
        self.assertEqual(len(self.call('/api/imports', role='staff')[1]), 2)

    def test_a_failing_second_batch_reverts_the_first_and_leaves_the_proposal_proposed(self):
        self.ready()
        p = self.vi()
        real, calls = self.app.apply_import, []

        def failing(actor, batch):
            calls.append(batch['id'])
            if len(calls) == 2:
                raise RecordsError(409, 'NOT_READY', 'The preview still needs something.')
            return real(actor, batch)
        self.app.apply_import = failing
        out = self.apply(p)
        self.app.apply_import = real
        self.assertEqual((out['ok'], out['error']), (False, 'APPLY_FAILED'))
        self.assertEqual([len(self.active(k)) for k in ('customers', 'invoices', 'payments')], [0, 0, 0])
        proposal = self.live(p)['proposal']
        self.assertEqual((proposal['status'], proposal['batches']), ('proposed', []))
        self.assertIn('The preview still needs something.', proposal['lastError'])
        self.assertTrue(self.apply(p, key='retry')['ok'])   # a retry works
        self.assertEqual(len(self.active('invoices')), 15)

    def test_the_live_route_gives_the_proposal_to_staff_and_owner(self):
        self.ready()
        p = self.vi()
        for role in ('staff', 'owner'):
            body = self.live(p, role)
            self.assertEqual(sorted(body['proposal']), ['batches', 'counts', 'fileName', 'id', 'lastError', 'message', 'references', 'status', 'unit', 'version', 'workspace'])
            self.assertEqual((body['proposal']['status'], body['proposal']['counts']['invoices']), ('proposed', 15))
            self.assertEqual(body['view']['proposalId'], p['proposalId'])
        applied = self.apply(p)['result']['batches']
        body = self.live(p)['proposal']
        self.assertEqual((body['status'], body['batches'], bool(body['appliedAt'])), ('applied', applied, True))
        self.assertEqual(self.call('/api/records/imports/proposals/proposal_nope', role='staff')[0], 404)

    def test_a_proposal_stored_before_the_upgrade_still_reads(self):
        """Old shape: no sha256, and a view without unit, workspace or references."""
        self.ready()
        p = self.vi()
        for applied in (False, True):
            if applied:
                self.assertTrue(self.apply(p)['ok'])
            with self.app.lock:
                old = self.app.meta(IMPORT_PROPOSALS + p['proposalId'])
                old.pop('sha256', None)
                for k in ('unit', 'workspace', 'references'):
                    old['view'].pop(k, None)
                with self.app.db:
                    self.app.set_meta(IMPORT_PROPOSALS + p['proposalId'], old)
            body = self.live(p)['proposal']
            self.assertEqual(body['status'], 'applied' if applied else 'proposed')
            self.assertEqual((body['unit'], body['workspace'], body['references']), (None, None, None))

    def test_customers_from_a_code_keep_the_code_as_an_alias_and_a_name_column_is_the_name(self):
        self.ready()
        self.assertTrue(self.apply(self.vi())['ok'])
        names = {c['name']: c for c in self.active('customers')}
        self.assertEqual(names['Customer 0001']['aliases'], ['0001'])
        found = self.tool('findCustomers', query='0001', key='f1')['result']
        self.assertEqual([m['name'] for m in found['matches']], ['Customer 0001'])
        csv_text = ('Customer ID,Customer Name,Posting Date,Document Number,Invoice Number,Debit,Credit\n'
                    '0014,Bayside Café,15/01/2026,BH1,A7,"1,000",\n')
        self.assertTrue(self.apply(self.propose(key='n', csvText=csv_text))['ok'])
        bayside = next(c for c in self.active('customers') if c['name'] == 'Bayside Café')
        self.assertEqual(bayside['aliases'], ['0014'])
        found = self.tool('findCustomers', query='0014', key='f2')['result']
        self.assertEqual([m['name'] for m in found['matches']], ['Bayside Café'])


class ReferenceMatchingTests(unittest.TestCase):
    """Fictional ledger rows: payments name invoices in another number format than the invoice row; opening, netting and zero rows."""
    HEAD = ['Customer', 'Invoice No', 'Invoice Date', 'Document Date', 'Debit', 'Credit', 'Record Type', 'Transaction Type', 'Outstanding Debt']

    def run_rows(self, lines):
        p = importer.propose(rows_of([self.HEAD] + [list(x) + [''] * (9 - len(x)) for x in lines]), {'dateOrder': 'dmy'}, no_model, VND, TODAY)
        batches = importer.derived(p['entries'], {})
        previews = importer.dry_run(records.empty_document(VND, False), batches, VND, TODAY, 'test')
        return p, importer.reference_summary(p['entries']['payments'], batches, previews)

    def invoice(self, customer, number, amount='1000000'):
        return [customer, number, '01/10/2026', '01/10/2026', amount, '0', 'Transaction', 'Invoice revenue']

    def payment(self, customer, number, amount='1000000'):
        return [customer, number, '10/10/2026', '10/10/2026', '0', amount, 'Transaction', 'Payment']

    def test_padded_and_short_numbers_match_in_both_directions_and_keep_the_stored_reference(self):
        p, (refs, text) = self.run_rows([self.invoice('Customer 0001', '35'), self.invoice('Customer 0001', '00000036'),
                                         self.payment('Customer 0001', '00000035'), self.payment('Customer 0001', '36')])
        self.assertEqual((refs['named'], refs['matched']), (2, 2))
        self.assertEqual([i['invoiceNumber'] for i in p['entries']['invoices']], ['35', '00000036'])   # as written in the file
        self.assertIn('2 of them match an invoice in this file and will be matched', text)
        self.assertEqual(importer.invoice_key(' hd-007 '), importer.invoice_key('HD-7'))

    def test_a_prefix_the_invoice_lacks_does_not_match_and_the_reasons_add_up(self):
        _, (refs, text) = self.run_rows([self.invoice('Customer 0001', '73'), self.invoice('Customer 0002', '74'),
                                         self.payment('Customer 0001', 'HD73'), self.payment('Customer 0001', '74'),
                                         self.payment('Customer 0001', '99'), self.payment('Customer 0001', '')])
        self.assertEqual(refs['matched'], 0)
        self.assertEqual(refs['unmatchedReasons'], {'noReference': 1, 'notInFile': 2, 'otherCustomer': 1, 'ambiguous': 0, 'multiple': 0, 'issuedAfter': 0})
        self.assertEqual(refs['matched'] + sum(refs['unmatchedReasons'].values()), refs['payments'])
        self.assertTrue(text.endswith('3 name an invoice not in this file; 1 stay without a reference'), text)

    def test_a_number_that_reads_as_two_invoices_of_the_customer_is_ambiguous_unless_written_exactly(self):
        _, (refs, text) = self.run_rows([self.invoice('Customer 0001', '7'), self.invoice('Customer 0001', '007'),
                                         self.payment('Customer 0001', '0007'), self.payment('Customer 0001', '7')])
        self.assertEqual((refs['matched'], refs['unmatchedReasons']['ambiguous']), (1, 1))   # '7' names invoice 7 exactly
        self.assertIn('1 could be more than one invoice', text)

    def test_opening_balance_netting_and_negative_rows_are_counted_or_flagged_with_what_they_are(self):
        p, _ = self.run_rows([self.invoice('Customer 0001', '1'),
                              ['Customer 0001', '', '', '', '0', '0', 'Opening Balance', 'Opening balance', '5500000'],
                              ['Customer 0001', '', '09/10/2026', '09/10/2026', '0', '1234000', 'Transaction', 'Debt netting'],
                              ['Customer 0001', '', '09/10/2026', '09/10/2026', '0', '0', 'Transaction', 'Debt netting'],
                              ['Customer 0001', '1', '09/10/2026', '09/10/2026', '-300000', '0', 'Transaction', 'Invoice revenue']])
        reasons = {f['row']: f['reason'] for f in p['flags']}
        self.assertEqual((p['counts']['openingBalances'], p['counts']['payments'], p['counts']['invoices']), (1, 0, 1))
        self.assertEqual(p['entries']['openings'][0]['direction'], 'owed')
        self.assertTrue(reasons[3].startswith('An opening balance of VND 5,500,000 owed by this customer'), reasons[3])
        self.assertEqual(reasons[4], "A debt-netting row of VND 1,234,000; not imported, so this customer's balance excludes it.")
        self.assertEqual(reasons[5], 'No amount (zero or blank) on a debt-netting row; left out.')
        self.assertTrue(reasons[6].startswith('A negative amount of VND 300,000'), reasons[6])


if __name__ == '__main__':
    unittest.main()
