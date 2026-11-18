"""Re-test of the known-issue fixes of 12 Nov 2026 on the fictional data (demo policy loaded; reset the demo data afterwards). Real conversations with the Staff and Owner assistants on the live instance (run only between a snapshot and its restore).
    live_chat.py <out-dir>      (cwd: ~/Developer/nucleon-local/tests/ada-acceptance, for chat.py)"""
import json, os, sys, time
sys.path.insert(0, '.')
from playwright.sync_api import sync_playwright
import chat

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
STAFF, OWNER = 'agent_biPGuKnO2VgHEQ67HsLHL', 'agent_x8IHmsGoFKdtDgdQcgmTX'
TURNS = [
    ('k1-rules', OWNER, None, "What are my current rules?"),
    ('k2-harbourline', STAFF, None, "Harbourline Catering is a new customer and wants AUD 5,000 of stock on 14-day terms; they paid a deposit."),
    ('k3-cityside', STAFF, None, "Cityside Desserts asks for 14 more days on invoice DEMO-410."),
    ('k4-riverside', STAFF, None, "Riverside Foods asks for 10 more days on invoice DEMO-505."),
    ('k5-waiting', OWNER, None, "What is waiting for my decision?"),
    ('k6-vague', STAFF, None, "Bayview Gelato Co wants more time to pay."),
    ('k7-half-answer', STAFF, 'k6-vague', "It is invoice DEMO-301."),
    ('k8-unknown', STAFF, None, "Pine Street Bakery wants AUD 500 of stock on 14-day terms."),
    ('k9-no-commitment', STAFF, None, "Bayview Gelato Co asks to pay invoice DEMO-301 on 20 December 2026. They cannot promise a payment date and have no payment plan."),
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
