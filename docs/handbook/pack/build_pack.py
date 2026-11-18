"""Build the information pack page from INFO-PACK.md (+ the manual's screenshots, if present).
    python3 build_pack.py  ->  nucleon-report-pack.html
A small Markdown subset: #/##/### headings, tables, bullet and numbered lists (one nesting level), paragraphs, ---, **bold**, *italic*, `code`."""
import base64, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(os.path.dirname(HERE), 'manual', 'shots')
src = open(os.path.join(HERE, 'INFO-PACK.md'), encoding='utf-8').read()
src = src.replace('`~/Developer/Project-Nucleon`', 'the project repository')


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![*\w])\*([^*\n]+)\*(?![*\w])', r'<em>\1</em>', t)
    t = re.sub(r'\[([A-Z][A-Z0-9\- /,.a-z]{1,60})\]', r'<span class="src">[\1]</span>', t)
    return t


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:50]


out, toc, lines, i = [], [], src.split('\n'), 0
title_done = False
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1; continue
    m = re.match(r'(#{1,3}) (.*)', line)
    if m:
        level, text = len(m.group(1)), m.group(2).strip()
        if level == 1:
            i += 1; continue   # the page has its own header
        sid = slug(text)
        if level == 2:
            toc.append((sid, text))
        out.append('<h%d id="%s">%s</h%d>' % (level, sid, inline(text), level))
        i += 1; continue
    if line.strip() == '---':
        i += 1; continue
    if line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')]); i += 1
        head, body = rows[0], [r for r in rows[2:]]
        out.append('<div class="tw"><table><thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head) + '</tr></thead><tbody>' +
                   ''.join('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>' for r in body) + '</tbody></table></div>')
        continue
    if re.match(r'\s*([-*]|\d+\.) ', line):
        ordered = bool(re.match(r'\s*\d+\. ', line))
        items = []
        while i < len(lines) and (re.match(r'\s*([-*]|\d+\.) ', lines[i]) or (lines[i].startswith('  ') and lines[i].strip())):
            cur = lines[i]
            indent = len(cur) - len(cur.lstrip())
            text = re.sub(r'^\s*([-*]|\d+\.) ', '', cur)
            if indent >= 2 and items and re.match(r'\s*([-*]|\d+\.) ', cur):
                items[-1][1].append(text)
            elif indent >= 2 and items:
                if items[-1][1]: items[-1][1][-1] += ' ' + cur.strip()
                else: items[-1][0] += ' ' + cur.strip()
            else:
                items.append([text, []])
            i += 1
        tag = 'ol' if ordered else 'ul'
        out.append('<%s>' % tag + ''.join('<li>%s%s</li>' % (inline(t), ('<ul>' + ''.join('<li>%s</li>' % inline(s) for s in sub) + '</ul>') if sub else '') for t, sub in items) + '</%s>' % tag)
        continue
    para = [line]; i += 1
    while i < len(lines) and lines[i].strip() and not re.match(r'(#{1,3} |\||\s*([-*]|\d+\.) |---$)', lines[i]):
        para.append(lines[i]); i += 1
    text = inline(' '.join(para))
    out.append('<p class="core">%s</p>' % text if text.startswith('<strong>Core message.') else '<p>%s</p>' % text)

# ---- the screenshots already taken for the manual, with their captions (shots/captions.json: {file: caption}), as a section before the wish-list
gallery = ''
if os.path.isdir(SHOTS):
    caps = {}
    cj = os.path.join(SHOTS, 'captions.json')
    if os.path.exists(cj):
        caps = json.load(open(cj))
    files = sorted(f for f in os.listdir(SHOTS) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
    figs = []
    for f in files:
        data = base64.b64encode(open(os.path.join(SHOTS, f), 'rb').read()).decode()
        mime = 'image/png' if f.lower().endswith('.png') else 'image/jpeg'
        cap = caps.get(f) or re.sub(r'^\d+[-_]?', '', os.path.splitext(f)[0]).replace('-', ' ').replace('_', ' ')
        figs.append('<figure><img loading="lazy" alt="%s" src="data:%s;base64,%s"><figcaption><b>%s</b> %s</figcaption></figure>' % (html.escape(cap, quote=True), mime, data, html.escape(f), html.escape(cap)))
    if figs:
        toc.append(('screenshots-taken', 'Screenshots already taken (%d)' % len(figs)))
        gallery = ('<h2 id="screenshots-taken">Screenshots already taken (%d)</h2><p>Taken on 11 November 2026 from a scratch copy of Nucleon with the fictional demonstration data, after the Control panel wording was rewritten. '
                   'Right-click (or long-press) an image to copy or save it for a slide. The same images appear in the Operating Manual with step-by-step explanations.</p><div class="shots">%s</div>' % (len(figs), ''.join(figs)))

CSS = """
/* layout: one reading column for prose, tables and screenshots allowed wider; contents list on top */
:root{--bg:#f7f8fa;--surface:#ffffff;--fg:#1b2430;--muted:#5a6675;--line:#d9dee6;--accent:#1f5fa8;--accent-soft:#e6eef8;--core:#eef6f0;--core-line:#3a7d57;--code:#eef0f4;
  --display:"Space Grotesk","Helvetica Neue",Arial,sans-serif;--body:"Inter",system-ui,-apple-system,"Segoe UI",Arial,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#12161c;--surface:#1a2029;--fg:#e6eaf0;--muted:#9aa6b5;--line:#2f3945;--accent:#7fb2ee;--accent-soft:#1d2c40;--core:#182a20;--core-line:#6fbf92;--code:#232b36;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#12161c;--surface:#1a2029;--fg:#e6eaf0;--muted:#9aa6b5;--line:#2f3945;--accent:#7fb2ee;--accent-soft:#1d2c40;--core:#182a20;--core-line:#6fbf92;--code:#232b36;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.6}
.wrap{max-width:1040px;margin:0 auto;padding-block:32px 72px;padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}
header.top h1{font-family:var(--display);font-size:clamp(28px,5vw,40px);line-height:1.15;margin:0 0 8px;text-wrap:balance}
header.top p{color:var(--muted);margin:0;max-width:70ch}
nav.toc{margin:28px 0 8px;padding:16px 20px;background:var(--surface);border:1px solid var(--line);border-radius:6px}
nav.toc b{font-family:var(--display);font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
nav.toc ol{margin:8px 0 0;padding-left:22px;columns:2;column-gap:32px}
nav.toc li{break-inside:avoid;margin:2px 0}
@media (max-width:640px){nav.toc ol{columns:1}}
a{color:var(--accent)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
h2{font-family:var(--display);font-size:26px;line-height:1.2;margin:56px 0 12px;padding-top:20px;border-top:2px solid var(--fg);text-wrap:balance}
h3{font-family:var(--display);font-size:19px;margin:32px 0 8px;text-wrap:balance}
p,ul,ol{max-width:74ch}
p{margin:10px 0}
li{margin:4px 0}
p.core{background:var(--core);border-left:4px solid var(--core-line);padding:12px 16px;max-width:none;font-size:17px}
code{font-family:var(--mono);font-size:.88em;background:var(--code);padding:1px 5px;border-radius:3px;overflow-wrap:anywhere}
.src{color:var(--muted);font-size:.82em;white-space:normal}
.tw{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:6px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14.5px;font-variant-numeric:tabular-nums}
th,td{text-align:left;vertical-align:top;padding:8px 12px;border-bottom:1px solid var(--line);min-width:120px}
th{font-family:var(--display);font-size:13px;letter-spacing:.03em;background:var(--accent-soft)}
tr:last-child td{border-bottom:0}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:20px;margin-top:16px}
figure{margin:0;min-width:0}
figure img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:4px;background:#fff}
figcaption{font-size:13.5px;color:var(--muted);margin-top:6px}
figcaption b{font-family:var(--mono);font-weight:500;font-size:12px;color:var(--fg);display:block;overflow-wrap:anywhere}
"""

page = ('<title>Nucleon Report Pack</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap">\n'
        '<style>' + CSS + '</style>\n<div class="wrap"><header class="top"><h1>Nucleon: information pack for the final report</h1>'
        '<p>Facts, numbers, reasons and screenshots to lift into the 35-page deck. Every number names its source. Written 11 November 2026; the report is due Monday 16 November.</p></header>'
        '<nav class="toc" aria-label="Contents"><b>Contents</b><ol>' + ''.join('<li><a href="#%s">%s</a></li>' % (s, html.escape(re.sub(r'^\d+\.\s*', '', t))) for s, t in toc) + '</ol></nav>\n')
body = '\n'.join(out)
marker = '<h2 id="12-screenshot-wish-list">'
body = body.replace(marker, gallery + marker) if marker in body else body + gallery
page += body + '</div>\n'
dest = os.path.join(HERE, 'nucleon-report-pack.html')
open(dest, 'w', encoding='utf-8').write(page)
print(dest, round(len(page.encode()) / 1e6, 2), 'MB', len(toc), 'sections')
