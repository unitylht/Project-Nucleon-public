import sys; sys.path.insert(0,'/Users/unitylht/Developer/nucleon-local/tests/s6b')
from lc import *
with sync_playwright() as p:
    for role in ['owner','staff']:
        b,ctx,pg=session(p); a=role_creds(role); perms={}
        def on(r):
            if '/api/roles/' in r.url and r.status==200:
                try: perms[r.url.split('/')[-1]]=r.json().get('permissions',{}).get('AGENTS')
                except Exception: pass
        pg.on('response',on)
        login(pg,a['email'],a['password']); pg.goto(BASE+'/c/new'); pg.wait_for_timeout(3000)
        pg.locator("button[aria-label*='odel' i], #new-conversation-menu").first.click(); pg.wait_for_timeout(800)
        pg.get_by_text("My Agents").first.click(); pg.wait_for_timeout(1500)
        opts=[x.strip() for x in pg.locator("[role=option], [role=menuitem]").all_inner_texts()]
        print(role,'picker agents:',[o for o in opts if 'Nucleon' in o]); pg.screenshot(path=SHOTS+f'/C-{role}-agents-list.png')
        pg.keyboard.press('Escape')
        pg.goto(BASE+'/agents'); pg.wait_for_timeout(3500)
        body=pg.locator('body').inner_text()
        print(role,'marketplace: Owner agent',('Nucleon ADA Owner' in body),'Staff agent',('Nucleon ADA Staff' in body))
        pg.screenshot(path=SHOTS+f'/C-{role}-marketplace.png')
        print(role,'builder entry points:', pg.locator("[data-testid=nav-panel-agents], [aria-label='Agent Builder'], [data-testid=agent-builder]").count(),
              '| edit/create controls on marketplace:', pg.get_by_role('button',name=re.compile('edit|create agent',re.I)).count())
        print(role,'role perms AGENTS:',perms)
        b.close()
