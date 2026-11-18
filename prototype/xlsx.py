"""Read an .xlsx workbook's cell values with the standard library only (zipfile and xml.etree): shared and inline strings,
numbers, and Excel serial dates, which become YYYY-MM-DD when the cell's format is a date format. Formulas give their saved
values; formatting, merged cells and charts are ignored. Deterministic code only."""
from __future__ import annotations

import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from records import RecordsError, require

MAX_PART = 30_000_000   # bytes of one uncompressed XML part: a zip bomb stops here
MAX_ROWS, MAX_COLUMNS = 20_050, 120   # cells to the right of MAX_COLUMNS are not read
DATE_FORMATS = {14, 15, 16, 17, 22, *range(27, 37), *range(50, 59)}   # Excel's built-in date formats (not the time-only ones)
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
BAD = 'This is not an .xlsx workbook Nucleon can read. Save it as .xlsx or CSV and try again.'


def local(element):
    return element.tag.rsplit('}', 1)[-1]


def children(element, name):
    return [e for e in element.iter() if local(e) == name]


def text_of(element):
    """The text of a string item: its <t> runs joined, phonetic guides (<rPh>) left out."""
    if element is None:
        return ''
    return ''.join(t.text or '' for run in [element] + [r for r in element if local(r) == 'r'] for t in run if local(t) == 't')


def read_workbook(data):
    """{sheet name: rows} in the workbook's order; rows[i] is the sheet's row i + 1 as a list of text cells ([] for a blank row)."""
    try:
        book = zipfile.ZipFile(io.BytesIO(data))
        names = set(book.namelist())

        def part(name):
            info = book.getinfo(name)
            require(info.file_size <= MAX_PART, 400, 'INVALID_FILE', 'The workbook is too large to read.', 'fileBase64')
            raw = book.read(name)
            require(b'<!DOCTYPE' not in raw.upper(), 400, 'INVALID_FILE', BAD, 'fileBase64')   # workbook parts never declare one
            return ET.fromstring(raw)

        def links(name):
            """A part's relationships, {id: (type, path)}, with each target resolved against the part's folder."""
            folder, rels = posixpath.dirname(name), posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name) + '.rels')
            if rels not in names:
                return {}
            return {r.get('Id'): (r.get('Type', ''), r.get('Target', '').lstrip('/') if r.get('Target', '').startswith('/') else
                                  posixpath.normpath(posixpath.join(folder, r.get('Target', '')))) for r in children(part(rels), 'Relationship')}
        main = next((path for kind, path in links('').values() if kind.endswith('/officeDocument')), 'xl/workbook.xml')
        require(main in names, 400, 'INVALID_FILE', BAD, 'fileBase64')
        workbook, rels = part(main), links(main)
        by_type = {kind.rsplit('/', 1)[-1]: path for kind, path in rels.values()}
        strings = [text_of(si) for si in children(part(by_type['sharedStrings']), 'si')] if by_type.get('sharedStrings') in names else []
        dated = date_styles(part(by_type['styles'])) if by_type.get('styles') in names else set()
        start = date(1904, 1, 1) if any(p.get('date1904') in ('1', 'true') for p in children(workbook, 'workbookPr')) else date(1899, 12, 30)
        sheets = {}
        for sheet in children(workbook, 'sheet'):
            target = rels.get(sheet.get('{' + REL + '}id'), ('', ''))[1]
            if target in names:
                sheets[sheet.get('name') or target] = read_sheet(part(target), strings, dated, start)
    except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, ValueError, OverflowError, EOFError, OSError):
        raise RecordsError(400, 'INVALID_FILE', BAD, 'fileBase64') from None
    require(sheets, 400, 'INVALID_FILE', 'The workbook has no sheets.', 'fileBase64')
    return sheets


def date_styles(styles):
    """The cell style indexes (s="n") whose number format shows a date."""
    custom = {int(f.get('numFmtId')): f.get('formatCode', '') for f in children(styles, 'numFmt')}

    def is_date(code):
        bare = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', '', code)   # quoted text, [colours or locales] and escaped characters
        return bool(re.search(r'[dy]', bare, re.I))
    xfs = next((x for x in styles.iter() if local(x) == 'cellXfs'), None)
    found = set()
    for n, xf in enumerate([] if xfs is None else [x for x in xfs if local(x) == 'xf']):
        fmt = int(xf.get('numFmtId', '0'))
        if fmt in DATE_FORMATS or (fmt in custom and is_date(custom[fmt])):
            found.add(n)
    return found


def column_index(ref):
    letters = re.match(r'[A-Z]+', ref or '')
    if not letters:
        return None
    n = 0
    for ch in letters.group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(sheet, strings, dated, start):
    rows = []
    for row in children(sheet, 'row'):
        number = int(row.get('r') or len(rows) + 1)
        require(number <= MAX_ROWS, 400, 'INVALID_FILE', 'A sheet has more than 20,000 rows.', 'fileBase64')
        cells = []
        for c in (x for x in row if local(x) == 'c'):
            at = column_index(c.get('r'))
            at = len(cells) if at is None else at
            if at >= MAX_COLUMNS:
                continue
            cells += [''] * (at + 1 - len(cells))
            cells[at] = value(c, strings, dated, start)
        while cells and not cells[-1]:
            cells.pop()
        rows += [[] for _ in range(number - 1 - len(rows))]
        rows.append(cells)
    return rows


def value(cell, strings, dated, start):
    kind, v = cell.get('t', 'n'), next((x.text or '' for x in cell if local(x) == 'v'), '')
    if kind == 's':
        return strings[int(v)].strip() if v else ''
    if kind == 'inlineStr':
        return text_of(next((x for x in cell if local(x) == 'is'), None)).strip()
    if kind == 'b':
        return 'TRUE' if v == '1' else 'FALSE'
    if kind in ('str', 'e'):
        return v.strip()
    if kind == 'd':   # an ISO date-time written as text
        return v[:10]
    try:
        number = Decimal(v)
    except InvalidOperation:
        return v.strip()
    if int(cell.get('s') or 0) in dated and number >= 1:
        return (start + timedelta(days=int(number))).isoformat()   # the time of day is dropped
    return format(number.normalize(), 'f')
