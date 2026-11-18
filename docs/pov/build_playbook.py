"""Build the Owner test playbook page from FACILITATOR-RUNBOOK.md.
    python3 docs/pov/build_playbook.py [out.html]   (default: docs/pov/owner-test-playbook.html, not kept in the repository)"""
import html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'FACILITATOR-RUNBOOK.md'), encoding='utf-8').read()
GITHUB = {'TESTER-GUIDE.md': 'the tester guide', 'CONSENT.md': 'the consent form', 'SESSION-LOG-TEMPLATE.md': 'the session log template', 'FEEDBACK-REGISTER.md': 'the feedback register'}


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', lambda m: '<span class="doc">' + GITHUB.get(m.group(2), m.group(1)) + ' (docs/pov/' + m.group(2) + ' in the repository)</span>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return re.sub(r'(https://[^\s<)]+[^\s<).,])', r'<a href="\1">\1</a>', t)


out, lines, i = [], src.split('\n'), 0
while i < len(lines):
    l = lines[i]
    if not l.strip():
        i += 1
    elif l.startswith('#'):
        n = len(l) - len(l.lstrip('#'))
        text = l[n:].strip()
        cls = ' class="part"' if n == 2 and text.startswith('Part ') else ''
        out.append('<h%d%s>%s</h%d>' % (n, cls, inline(text), n))
        i += 1
    elif l.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
            i += 1
        body = ''.join('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in r) + '</tr>' for r in rows[2:])
        out.append('<div class="tw"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>' + body + '</tbody></table></div>')
    elif l.startswith('> '):
        out.append('<div class="paste"><span>Paste to the Staff assistant</span><p>' + inline(l[2:]) + '</p></div>')
        i += 1
    elif re.match(r'(\d+\.|-) ', l):
        tag = 'ol' if l[0].isdigit() else 'ul'
        items = []
        while i < len(lines) and re.match(r'(\d+\.|-) ', lines[i]):
            items.append('<li>' + inline(re.sub(r'^(\d+\.|-) ', '', lines[i])) + '</li>')
            i += 1
        out.append('<%s>%s</%s>' % (tag, ''.join(items), tag))
    else:
        out.append('<p>' + inline(l) + '</p>')
        i += 1

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--fg:#1c2320;--muted:#5c6662;--line:#dbd9d0;--accent:#0f6b54;--soft:#e5f0eb;--warnbg:#fbf1d9;--warn:#8a5a00}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141816;--card:#1c2220;--fg:#e8ece9;--muted:#9aa5a0;--line:#2f3835;--accent:#62c7a6;--soft:#1f302a;--warnbg:#33290f;--warn:#e8c26a;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141816;--card:#1c2220;--fg:#e8ece9;--muted:#9aa5a0;--line:#2f3835;--accent:#62c7a6;--soft:#1f302a;--warnbg:#33290f;--warn:#e8c26a;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:16px/1.6 Inter,system-ui,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding-block:28px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1,h2,h3{font-family:"Space Grotesk",Inter,sans-serif;line-height:1.25;text-wrap:balance}
h1{font-size:2rem;margin:0 0 12px}h2{font-size:1.3rem;margin:36px 0 10px;padding-top:18px;border-top:1px solid var(--line)}h3{font-size:1.05rem;margin:24px 0 6px}
h2.part{background:var(--accent);color:var(--bg);border:0;border-radius:8px;padding:10px 14px}
p,li{max-width:70ch}p{margin:10px 0}ol,ul{padding-left:1.3rem;margin:10px 0}li{margin:5px 0}
a{color:var(--accent);overflow-wrap:anywhere}.doc{color:var(--muted)}
code{font-family:ui-monospace,Menlo,monospace;font-size:.9em;background:var(--soft);padding:1px 5px;border-radius:4px}
.tw{overflow-x:auto;margin:12px 0}table{border-collapse:collapse;width:100%;background:var(--card);font-size:.94rem}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}th{background:var(--soft)}
.paste{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px;margin:12px 0}
.paste span{font-size:.75rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.paste p{margin:4px 0 0;font-family:ui-monospace,Menlo,monospace;font-size:.92rem;user-select:all;overflow-wrap:anywhere}
"""
page = ('<title>Owner Test Playbook</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">\n'
        '<style>' + CSS + '</style>\n<div class="wrap">\n' + '\n'.join(out) + '\n</div>\n')
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'owner-test-playbook.html')
open(dest, 'w', encoding='utf-8').write(page)
print(dest, len(page))
