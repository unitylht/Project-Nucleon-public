// Build the team testing guide from guide-content.js: a Word document in Arial and a Markdown copy for review.
//   cd docs/qa/test-pack-v3/build && npm install docx@9.5.1 && node build_guide.js
// Output: ../Nucleon-Team-Test-Pack-v3/Nucleon-Team-Testing-Guide-v3.docx and ../GUIDE-v3.md
'use strict';
const fs = require('fs');
const path = require('path');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, AlignmentType, LevelFormat,
        HeadingLevel, Footer, PageNumber, TabStopType } = require('docx');
const guide = require('./guide-content');

const FONT = 'Arial';
const OUT = path.join(__dirname, '..');
const PACK = path.join(OUT, 'Nucleon-Team-Test-Pack-v3');
const INK = '18222C', MUTED = '4D5B67', RULE = 'C9D1D8', WARN = 'C4851A', WARN_BG = 'FCF1DC', NOTE_BG = 'EEF2F5';
const TEXT_W = 9026;   // A4 width less 2.5 cm margins, in twentieths of a point

const run = (text, opts = {}) => new TextRun({ text, font: FONT, ...opts });
// Text with "quoted on-screen labels" kept as written; plain runs otherwise.
const runs = (text, opts = {}) => [run(text, opts)];
let listInstance = 0;

function paragraphs(block) {
  if (block.h1) return [new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(block.h1), pageBreakBefore: /^T[2-9]\b/.test(block.h1) && false })];
  if (block.h2) return [new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(block.h2) })];
  if (block.p) return [new Paragraph({ children: runs(block.p), spacing: { after: 120 } })];
  if (block.start) return [new Paragraph({ children: [run('Starting point: ', { bold: true }), run(block.start)], spacing: { before: 60, after: 120 }, keepNext: true })];
  if (block.steps) { listInstance += 1; const inst = listInstance;
    return [new Paragraph({ children: [run('Steps', { bold: true })], spacing: { before: 60, after: 60 }, keepNext: true }),
            ...block.steps.map(s => new Paragraph({ numbering: { reference: 'steps', level: 0, instance: inst }, children: runs(s), spacing: { after: 80 } }))]; }
  if (block.checks) return [new Paragraph({ children: [run('Check', { bold: true })], spacing: { before: 120, after: 60 }, keepNext: true }),
    ...block.checks.map(s => new Paragraph({ numbering: { reference: 'checks', level: 0 }, children: runs(s), spacing: { after: 80 } }))];
  if (block.list) return block.list.map(s => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: runs(s), spacing: { after: 80 } }));
  if (block.note) return [new Paragraph({ children: [run('Note: ', { bold: true }), run(block.note)], shading: { type: ShadingType.CLEAR, color: 'auto', fill: NOTE_BG },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: '7D8B96', space: 6 } }, spacing: { before: 120, after: 160 }, indent: { left: 120, right: 120 } })];
  const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  if (block.box) return [new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [TEXT_W],
      borders: { top: none, bottom: none, right: none, insideHorizontal: none, insideVertical: none, left: { style: BorderStyle.SINGLE, size: 24, color: WARN } },
      rows: [new TableRow({ cantSplit: true, children: [new TableCell({ width: { size: TEXT_W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: 'auto', fill: WARN_BG },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph({ children: [run(block.title, { bold: true })], spacing: { after: 60 } }),
                   ...block.items.map(s => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: runs(s), spacing: { after: 40 } }))] })] })] }),
    new Paragraph({ children: [run('')], spacing: { after: 60 } })];
  // Answer lines: ruled table rows (consecutive bordered paragraphs would merge into one box).
  if (block.lines) return [new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [TEXT_W],
      borders: { top: none, left: none, right: none, insideVertical: none, bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE }, insideHorizontal: { style: BorderStyle.SINGLE, size: 6, color: RULE } },
      rows: Array.from({ length: block.lines }, () => new TableRow({ height: { value: 440, rule: 'atLeast' }, children: [new TableCell({ width: { size: TEXT_W, type: WidthType.DXA }, children: [new Paragraph({ children: [run('')] })] })] })) }),
    new Paragraph({ children: [run('')], spacing: { after: 120 } })];
  if (block.table) {
    const t = block.table;
    const cell = (text, head, w) => new TableCell({ width: { size: w, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
      shading: head ? { type: ShadingType.CLEAR, color: 'auto', fill: 'E6EBEF' } : undefined,
      children: [new Paragraph({ children: [run(text, { bold: head, size: 19 })] })] });
    return [new Table({ width: { size: t.widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: t.widths,
      borders: { top: { style: BorderStyle.SINGLE, size: 4, color: RULE }, bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE }, left: { style: BorderStyle.SINGLE, size: 4, color: RULE },
                 right: { style: BorderStyle.SINGLE, size: 4, color: RULE }, insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: RULE }, insideVertical: { style: BorderStyle.SINGLE, size: 4, color: RULE } },
      rows: [new TableRow({ tableHeader: true, children: t.cols.map((c, i) => cell(c, true, t.widths[i])) }), ...t.rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, false, t.widths[i])) }))] }),
      new Paragraph({ children: [run('')], spacing: { after: 60 } })];
  }
  throw new Error('Unknown block ' + JSON.stringify(block).slice(0, 80));
}

const widths = guide.blocks.filter(b => b.table).map(b => b.table.widths.reduce((a, c) => a + c, 0));
if (widths.some(w => w > TEXT_W)) throw new Error('A table is wider than the text area: ' + widths);

const doc = new Document({
  creator: 'Project Nucleon team', title: guide.title, description: guide.subtitle,
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: INK }, paragraph: { spacing: { line: 276 } } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: FONT, size: 36, bold: true, color: INK }, paragraph: { spacing: { after: 80 } } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 28, bold: true, color: INK },
        paragraph: { spacing: { before: 360, after: 120 }, keepNext: true, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 4 } } } },
      { id: 'Footer', name: 'Footer', basedOn: 'Normal', run: { font: FONT, size: 16, color: MUTED } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 23, bold: true, color: INK },
        paragraph: { spacing: { before: 240, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START, style: { run: { font: FONT, bold: true }, paragraph: { indent: { left: 440, hanging: 360 } } } }] },
    { reference: 'checks', levels: [{ level: 0, format: LevelFormat.BULLET, text: '□', alignment: AlignmentType.START, style: { run: { font: FONT }, paragraph: { indent: { left: 440, hanging: 360 } } } }] },
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.START, style: { run: { font: FONT }, paragraph: { indent: { left: 440, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ style: 'Footer', tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
      children: [run('Nucleon team testing guide, revision 3. Fictional data only. Never include access codes.', { size: 16, color: MUTED }),
                 new TextRun({ children: ['\tPage ', PageNumber.CURRENT, ' of ', PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: MUTED })] })] }) },
    children: [
      new Paragraph({ style: 'Title', children: runs(guide.title) }),
      new Paragraph({ children: runs(guide.subtitle, { color: MUTED }), spacing: { after: 240 } }),
      ...guide.blocks.flatMap(paragraphs),
    ],
  }],
});

// The Markdown copy: the same content, for review in a pull request.
function markdown() {
  const out = ['# ' + guide.title, '', '_' + guide.subtitle + '_', ''];
  let n = 0;
  for (const b of guide.blocks) {
    if (b.h1) out.push('## ' + b.h1, '');
    else if (b.h2) out.push('### ' + b.h2, '');
    else if (b.p) out.push(b.p, '');
    else if (b.start) out.push('**Starting point:** ' + b.start, '');
    else if (b.steps) { n = 0; out.push('**Steps**', '', ...b.steps.map(s => `${++n}. ${s}`), ''); }
    else if (b.checks) out.push('**Check**', '', ...b.checks.map(s => '- [ ] ' + s), '');
    else if (b.list) out.push(...b.list.map(s => '- ' + s), '');
    else if (b.note) out.push('> **Note:** ' + b.note, '');
    else if (b.box) out.push('> **' + b.title + '**', '>', ...b.items.map(s => '> - ' + s), '');
    else if (b.lines) out.push('_' + '\\_'.repeat(40) + '_', '');
    else if (b.table) out.push('| ' + b.table.cols.join(' | ') + ' |', '|' + b.table.cols.map(() => ' --- |').join(''), ...b.table.rows.map(r => '| ' + r.map(c => c || ' ').join(' | ') + ' |'), '');
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n');
}

fs.mkdirSync(PACK, { recursive: true });
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(path.join(PACK, 'Nucleon-Team-Testing-Guide-v3.docx'), buffer);
  fs.writeFileSync(path.join(OUT, 'GUIDE-v3.md'), '<!-- Generated by build/build_guide.js from build/guide-content.js. Edit the content file, not this copy. -->\n\n' + markdown());
  console.log('written', path.join(PACK, 'Nucleon-Team-Testing-Guide-v3.docx'));
});
