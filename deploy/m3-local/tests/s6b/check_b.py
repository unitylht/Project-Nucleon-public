import sys; sys.path.insert(0,'/Users/unitylht/Developer/nucleon-local/tests/s6b')
from lc import *
sys.path.insert(0,os.path.expanduser('~/Developer/nucleon-local/tests/ada-acceptance'))
import chat
with sync_playwright() as p:
    b,ctx,pg=session(p)
    c=admin_creds(); login(pg,c['email'],c['password'])
    l=pg.locator("[data-testid=nav-nucleon-link]"); print('visible',l.is_visible(),'href',l.get_attribute('href'),'target',l.get_attribute('target'),'rel',l.get_attribute('rel'))
    pg.screenshot(path=SHOTS+'/B-nav-expanded.png')
    with ctx.expect_page() as ni: l.click()
    n=ni.value; print('new tab opened; opener-less:', n.evaluate('window.opener===null')); print('url', n.url[:60]); n.close()
    print('original tab still at', pg.url)
    pg.locator("[data-testid=close-sidebar-button]").click(); pg.wait_for_timeout(800)
    print('collapsed visible', pg.locator("[data-testid=nav-nucleon-link]").is_visible()); pg.screenshot(path=SHOTS+'/B-nav-collapsed.png')
    # MCP card
    chat.BASE=BASE
    pg.goto(f"{BASE}/c/new?agent_id={chat.AGENT}"); pg.wait_for_timeout(3000)
    ta=pg.locator("textarea[aria-label='Message input'],#prompt-textarea").first
    ta.fill("What does Riverside Foods owe?"); pg.keyboard.press("Enter")
    pg.wait_for_selector("iframe[title^='MCP']",timeout=240000)
    chat.wait_done(pg,300)
    print('cards',len(pg.locator("iframe[title^='MCP']").all()),'reply:',chat.reply(pg)[:160].replace('\n',' '))
    pg.screenshot(path=SHOTS+'/B-agent-card.png'); b.close()
