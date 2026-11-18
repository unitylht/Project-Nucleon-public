"""Real conversations with the Staff and Owner assistants on the live instance (run only between a snapshot and its restore).
    live_chat.py <out-dir>      (cwd: ~/Developer/nucleon-local/tests/ada-acceptance, for chat.py)"""
import json, os, sys, time
sys.path.insert(0, '.')
from playwright.sync_api import sync_playwright
import chat

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
STAFF, OWNER = 'agent_biPGuKnO2VgHEQ67HsLHL', 'agent_x8IHmsGoFKdtDgdQcgmTX'
TURNS = [
    ('v1-vague', STAFF, None, "Customer 0010 wants more time to pay."),
    ('v2-answer', STAFF, 'v1-vague', "Invoice 00000080, until 10 November 2026... sorry, until 30 November 2026."),
    ('v3-no-date', STAFF, None, "Customer 0002 asks for more time on invoice 00000065."),
    ('v4-no-invoice', STAFF, None, "Customer 0014 wants two more weeks."),
    ('v5-clear', STAFF, None, "Customer 0016 asks to pay invoice 00000068 on 25 November 2026. They will pay in full then."),
    ('v6-status', STAFF, None, "What is the status of the extension request from Customer 0003?"),
    ('v7-owner-ext', OWNER, None, "Did the extensions the agent approved get paid?"),
    ('v8-relative', STAFF, None, "Customer 0002 called: can they pay invoice 00000065 at the end of the month?"),
]
results, cids = [], {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 1000})
    pg = ctx.new_page()
    chat.login(pg)
    for name, agent, follow, prompt in TURNS:
        chat.AGENT = agent
        t0 = time.time()
        try:
            cid, ok = chat.send(pg, prompt, cids.get(follow))
            cids[name] = cid
            r = {'turn': name, 'prompt': prompt, 'seconds': round(time.time() - t0), 'finished': ok, 'reply': chat.reply(pg), 'tools': chat.panels(pg), 'cards': chat.cards(pg)}
        except Exception as e:
            r = {'turn': name, 'prompt': prompt, 'seconds': round(time.time() - t0), 'error': str(e)[:300]}
        try: pg.screenshot(path=os.path.join(out, name + '.png'), full_page=False)
        except Exception: pass
        results.append(r)
        json.dump(results, open(os.path.join(out, 'chat.json'), 'w'), indent=1)
        print('[%s] %ss finished=%s tools=%s' % (name, r['seconds'], r.get('finished'), len(r.get('tools') or [])), flush=True)
    b.close()
