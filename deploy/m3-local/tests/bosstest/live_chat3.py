"""Re-test after the session with the owners on 12 Nov 2026 (requested dates, the agent-decline card). Real conversations with the Staff and Owner assistants on the live instance (run only between a snapshot and its restore).
    live_chat.py <out-dir>      (cwd: ~/Developer/nucleon-local/tests/ada-acceptance, for chat.py)"""
import json, os, sys, time
sys.path.insert(0, '.')
from playwright.sync_api import sync_playwright
import chat

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
STAFF, OWNER = 'agent_biPGuKnO2VgHEQ67HsLHL', 'agent_x8IHmsGoFKdtDgdQcgmTX'
TURNS = [
    ('d1-31dec', STAFF, None, "Customer 0014 asks to move invoice 00000066 from its current due date to 31 December 2026. Negotiation is finished: they have severe cash-flow difficulty, no reliable payment plan and cannot commit to paying on that date."),
    ('d2-15day', STAFF, None, "Customer 0016 asks for a 15-day extension on invoice 00000068. They will pay in full then."),
    ('d3-date', STAFF, None, "Customer 0002 asks to pay invoice 00000065 on 20 December 2026 instead. They confirmed they will pay in full on that day."),
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
