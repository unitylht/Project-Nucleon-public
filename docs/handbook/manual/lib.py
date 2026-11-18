import sys, os, time, json, tempfile
sys.path.insert(0, os.path.expanduser('~/Developer/Project-Nucleon-qs/deploy'))
from page_check_lib import Scratch, IDS
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = HERE + '/raw/'

class Shooter:
    def __init__(self, S, pw):
        self.S = S
        self.browser = pw.chromium.launch()
        self.ctx = self.browser.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=2, bypass_csp=True)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(15000)
        self.role = None
    def open(self, hash_, role):
        p = self.page
        if self.role != role:
            self.ctx.clear_cookies()
            p.goto(self.S.base + '/')
            p.wait_for_selector('#signin')
            p.fill('#code', self.S.codes[(role, 'access')])
            p.click('#signin') if False else p.evaluate("document.querySelector('#signin').requestSubmit()")
            p.wait_for_selector('header.top')
            p.evaluate("localStorage.setItem('nucleon.view', 'detailed')")   # the manual shows every explanation
            self.role = role
            p.add_style_tag(content='header.top,.tabbar,.sticky{position:static !important} *{caret-color:transparent !important}')
        p.evaluate("location.hash = %s" % json.dumps(hash_))
        time.sleep(1.2)
    def settle(self, t=0.8): time.sleep(t)
    def el(self, name, sel, pad=0):
        loc = self.page.locator(sel).first
        loc.scroll_into_view_if_needed()
        loc.screenshot(path=RAW + name + '.png')
    def range(self, name, a, b):
        """from the top of element a to the bottom of element b"""
        p = self.page
        box = p.evaluate("""([a,b]) => { const A=document.querySelector(a).getBoundingClientRect(), B=document.querySelector(b).getBoundingClientRect();
            return {x:0, y:A.top+scrollY, w:document.documentElement.clientWidth, h:B.bottom-A.top} }""", [a, b])
        p.screenshot(path=RAW + name + '.png', full_page=True, clip={'x': 0, 'y': box['y'], 'width': box['w'], 'height': box['h']})
    def top(self, name, height=900):
        self.page.evaluate("scrollTo(0,0)")
        self.page.screenshot(path=RAW + name + '.png', full_page=True, clip={'x': 0, 'y': 0, 'width': 1280, 'height': height})
    def full(self, name):
        self.page.screenshot(path=RAW + name + '.png', full_page=True)
