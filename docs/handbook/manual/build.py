"""Builds nucleon-manual.html: one self-contained file. Text sources: part1.html, part3.html, settings.py (the Control panel rows). Images: shots/*.jpg inlined as data URIs.
Usage: python3 build.py"""
import base64, html, os, re
from settings import GROUPS, OTHER, PANEL_PARTS, PRESETS, RULES, SCHEDULE, MODEL

HERE = os.path.dirname(os.path.abspath(__file__))
E = lambda s: html.escape(s, quote=True)
used = []


def img_uri(name):
    with open(os.path.join(HERE, 'shots', name), 'rb') as f:
        return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()


def fig(name, alt, caption):
    used.append(name)
    n = len(used)
    return (f'<figure class="shot"><img src="{img_uri(name)}" alt="{E(alt)}" loading="lazy" decoding="async">'
            f'<figcaption><b>Figure {n}.</b> {E(caption)}</figcaption></figure>')


def setting(item, idx):
    label, what, example, up, down, first, kind = item
    a, b = {'num': ('Raise it', 'Lower it'), 'flag': ('Turn it on', 'Turn it off'), 'pick': ('The choices', 'The more cautious choice')}[kind]
    rows = [('What it does', what), ('Example', example), (a, up), (b, down), ('Cautious first week', first)]
    dl = ''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k, v in rows if v)
    return f'<article class="setting"><h4>{E(label)}</h4><dl>{dl}</dl></article>'


def model_setting(item):
    label, what, example, up, down, first = item
    rows = [('What it does', what), ('Example', example), ('Raise it or turn it on', up), ('Lower it or turn it off', down), ('Default and suggestion', first)]
    dl = ''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k, v in rows if v)
    return f'<article class="setting"><h4>{E(label)}</h4><dl>{dl}</dl></article>'


def plain_rows(rows):
    return '<div class="plain">' + ''.join(f'<article class="setting"><h4>{E(k)}</h4><p>{E(v)}</p></article>' for k, v in rows) + '</div>'


PANEL_INTRO = '''
<section id="panel">
<h2>4. The Control panel, item by item</h2>
<p>Many people find the Control panel overwhelming the first time. Three facts make it smaller.</p>
<ul>
<li><b>Only Basic matters at first.</b> Everything after Basic is off, empty or folded away by default. A new Owner can set Basic, save, and stop.</li>
<li><b>A request is decided by the agent only when it is inside every rule.</b> Each setting is one more gate. Turning a gate off, or setting it to empty, means that gate does not exist.</li>
<li><b>Nothing is permanent.</b> Nothing changes until you press Save. Every save is a new version, earlier versions stay, and a save never changes a decision that was already made.</li>
</ul>
<p>Each setting below has the label exactly as it is on screen, what it does, an example with numbers, what raising it or turning it on does, what lowering it or turning it off does, and a suggestion for a cautious first week. A suggestion is marked "Suggestion". A value marked "Default" is what the code starts with. The examples use the fictional demonstration data.</p>
<p class="small">The page is read top to bottom. The sections here follow the same order.</p>
<h3>How a request meets the rules</h3>
<ol class="steps">
<li>If the customer is on the hold list, or Staff's information contradicts the records, it comes to you.</li>
<li>If any limit is exceeded (money, days, history, size, the 30-day budget), it comes to you, unless a little over a limit or an exception applies.</li>
<li>If Staff can supply missing information (a deposit, an identity), Nucleon asks them and checks again.</li>
<li>If a number cannot be established from the records, it comes to you. Unknown is never treated as zero.</li>
<li>If the mode is Advisory, delegation is paused or the kind of request is turned off, it comes to you.</li>
<li>If most of the closest earlier cases were declined by you, or the track record minimum is not met, it comes to you.</li>
<li>If the assistant did not recommend approval, or the model's extra caution fires, it comes to you.</li>
<li>Otherwise the agent approves.</li>
</ol>

<h3 id="cp-top">Top of the page, presets and pause</h3>
'''

PANEL_TOP_AFTER = ''


def build_panel():
    out = [PANEL_INTRO]
    out.append(fig('20-controlpanel-top.jpg', 'The top of the Control panel: the title, the Pause delegation button, a green line saying Policy version 2, a row of links to each section with small icons, the Quick settings box, and the Current policy summary of the saved rules.',
                   'The top of the Control panel. The green line says which version is in force. The row of links jumps to each section. The Pause delegation button is at the top right.'))
    out.append('<h4 class="sub">Quick settings</h4><p>The three choices of Get started, kept here so that you never have to run that path again to change one. '
               '<b>How strict the agent is:</b> Strict, Balanced, Relaxed or Custom. Pressing a level opens Quick setup with six answers filled in and a preview of what they would do; nothing is saved until you press Save there, and every setting a level does not cover stays as it is. The level in force is marked; "Custom" means your numbers match none of the three. '
               '<b>Customers the agent never decides for:</b> the names now on the list, and a Change button that goes to the field under Advanced. '
               '<b>How much the pages show:</b> Simple, Standard or Detailed, for your own browser only; it is not part of the policy and makes no new version.</p>')
    out.append(fig('35-controlpanel-quick-settings.jpg', 'The Quick settings box: four level cards (Strict, Balanced, Relaxed, Custom) with one marked, the list of customers the agent never decides for with a Change button, and three display choices (Simple, Standard, Detailed).',
                   'Quick settings at the top of the Control panel.'))
    out.append(plain_rows(PANEL_PARTS))
    out.append(setting(OTHER[2], 0))
    out.append('<h4 class="sub">Presets</h4><p>Two buttons above the form. Each saves a new version at once, named in the Versions list, after asking you to confirm.</p>')
    out.append(fig('21-controlpanel-presets.jpg', 'The Change the policy section: a note about Quick setup, a note about the Doctor, and the two preset buttons with their descriptions.',
                   'The start of "Change the policy": links to Quick setup and the Doctor, then the two presets.'))
    out.append(plain_rows(PRESETS))
    for g in GROUPS:
        out.append(f'<h3 id="{g["id"]}">{E(g["title"])}</h3><p>{E(g["intro"])}</p>')
        out.append(fig(g['shot'], g['shot_alt'], g['shot_caption']))
        out.append(''.join(setting(it, i) for i, it in enumerate(g['items'])))
    out.append('<h3 id="cp-save">Note and Save</h3>')
    out.append(setting(OTHER[0], 0))
    out.append(setting(OTHER[1], 0))
    out.append('<h3 id="cp-rules">Standing rules for one customer</h3><p>A rule for one customer replaces the general limit for that customer only. It is saved as a new version.</p>')
    out.append(fig('28-controlpanel-customer-rules.jpg', 'The Standing rules for one customer section: a table with one rule for Cityside Desserts (most owed 2,500, longest extension 45 days, until 31 December 2026, with a note) and a form to add another.',
                   'Standing rules. The table shows the rule in force and a Remove button. The form below adds or replaces one.'))
    out.append(plain_rows(RULES))
    out.append('<p class="small">Example with numbers: the general limit is 1,500. With the rule above, a request from Cityside is judged against 2,500 and 45 days until 31 December 2026. From 1 January the general limits apply again.</p>')
    out.append('<h3 id="cp-schedule">Scheduled changes</h3><p>For a change that should start on a date, and optionally be put back on another.</p>')
    out.append(fig('29-controlpanel-scheduled.jpg', 'The Scheduled changes section: one waiting change for 1 December 2026 with a note and a Cancel button, and a form with two dates, a note and a Schedule button.',
                   'Scheduled changes. One change is waiting for 1 December and will be put back on 2 January.'))
    out.append(plain_rows(SCHEDULE))
    out.append('<h3 id="cp-model">The team\'s model</h3>')
    out.append('<p>The team\'s model is a small statistical model fitted on the Owner\'s own past approve and decline decisions. For each request it gives "the chance you would decline". It is used in exactly three places, and nowhere else:</p>'
               '<ol><li><b>Safeguard 1</b> of the exceptions (an approval chance of 80% is a decline chance of 20%).</li>'
               '<li><b>Prepare a decline for you.</b> One click on the Decide page. The Owner still decides.</li>'
               '<li><b>The extra caution switch</b> in this section. A high chance of a decline <b>sends the case to the Owner</b> once the two bars are met.</li></ol>'
               '<p>The model never approves anything the rules would not, except inside the exception band the Owner switched on, and it never declines. With no model fitted, exceptions never apply. The score is also stored on each case and shown for research, and no rule reads it. The questionnaire "Teach it your limits" on the Model page feeds similar cases and the model\'s training table. Its answers do not count toward the agent\'s track record.</p>')
    out.append(fig('30-controlpanel-team-model.jpg', 'The team\'s model section of the Control panel: a summary of the model in force, a note on whether the caution switch is active, the checkbox, three bars and a refit setting, and two buttons.',
                   'The team\'s model section on the Control panel. The Model page has the full detail.'))
    out.append(''.join(model_setting(m) for m in MODEL))
    out.append('<h3 id="cp-versions">Versions and live counts</h3>')
    out.append('<p><b>Versions</b> lists every saved version with its number, its mode, whether it was paused, the date, who saved it and the note. You can read what changed and when. To go back to an earlier version, enter its values again, or use a preset.</p>'
               '<p><b>Live counts</b> shows seven counts: Approved by the agent, Declined by the agent, Asking Staff for information, With the Owner, On hold, Decided by the Owner and Overridden. They count live cases only. Fictional practice cases are excluded. They are workflow counts and say nothing about how good the decisions are.</p>')
    out.append(fig('31-controlpanel-versions-counts.jpg', 'The Versions list with version 1 and version 2, and the Live counts with seven numbers and a note that fictional cases are excluded.',
                   'Versions and live counts at the bottom of the Control panel.'))
    out.append('</section>')
    return '\n'.join(out)


def prompts(text):
    def rep(m):
        pid, body = m.group(1), m.group(2)
        return (f'<div class="prompt"><pre id="{pid}" tabindex="0">{E(body)}</pre>'
                f'<button type="button" class="copy" data-target="{pid}">Copy prompt</button></div>')
    return re.sub(r'\[\[prompt:(\w+)\|(.*?)\]\]', rep, text, flags=re.S)


def figs(text):
    return re.sub(r'\[\[fig:([^|\]]+)\|([^|\]]*)\|([^\]]*)\]\]', lambda m: fig(m.group(1), m.group(2), m.group(3)), text, flags=re.S)


CSS = open(os.path.join(HERE, 'style.css')).read()
SCRIPT = open(os.path.join(HERE, 'copy.js')).read()


def main():
    p1 = figs(open(os.path.join(HERE, 'part1.html')).read())
    panel = build_panel()
    p3 = figs(prompts(open(os.path.join(HERE, 'part3.html')).read()))
    body = p1 + '\n' + panel + '\n' + p3
    doc = ('<title>Nucleon Operating Manual</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>\n' + CSS + '\n</style>\n'
           '<div class="wrap"><main class="manual">\n' + body + '\n</main></div>\n<script>\n' + SCRIPT + '\n</script>\n')
    out = os.path.join(HERE, 'nucleon-manual.html')
    open(out, 'w').write(doc)
    print('written', out, round(len(doc.encode()) / 1e6, 2), 'MB;', len(used), 'figure placements;', len(set(used)), 'distinct images')


main()
