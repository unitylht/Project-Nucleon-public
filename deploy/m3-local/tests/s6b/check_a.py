import sys; sys.path.insert(0,'/Users/unitylht/Developer/nucleon-local/tests/s6b')
from lc import *
with sync_playwright() as p:
    b,ctx,pg=session(p); got={}
    def on(r):
        if r.url.endswith('/api/config') and r.status==200:
            try: got['c']=r.json()
            except Exception: pass
    pg.on('response',on)
    c=admin_creds(); login(pg,c['email'],c['password']); pg.reload(); pg.wait_for_timeout(4000)
    i=got['c'].get('interface',{}); print({k:i.get(k) for k in ['modelSelect','presets','prompts','bookmarks','multiConvo','parameters','customWelcome','agents']})
    pg.screenshot(path=SHOTS+'/A-admin-home.png'); b.close()
