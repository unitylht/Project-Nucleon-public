"""S6b browser helpers (run from tests/ada-acceptance dir: sys.path has it). Never prints credentials."""
import sys, os, json, time, re
sys.path.insert(0, os.path.expanduser('~/Developer/nucleon-local/tests/ada-acceptance'))
from playwright.sync_api import sync_playwright
from pw import EX
BASE = 'http://127.0.0.1:3080'
SHOTS = os.path.expanduser('~/Developer/nucleon-local/tests/s6b/shots'); os.makedirs(SHOTS, exist_ok=True)
def admin_creds():
    return dict(l.rstrip('\n').split(': ', 1) for l in open(os.path.expanduser('~/Developer/LibreChat-POC-credentials.txt')) if ': ' in l)
def role_creds(role):
    d = json.load(open(os.path.expanduser('~/Developer/nucleon-local/config/role-accounts.json')))
    return next(a for a in d['accounts'] if a['role'] == role)
def login(pg, email, password):
    pg.goto(BASE + '/login'); pg.wait_for_selector('#email', timeout=30000)
    pg.fill('#email', email); pg.fill('#password', password); pg.click('button[type=submit]')
    pg.wait_for_function("()=>!location.pathname.startsWith('/login')", timeout=45000); pg.wait_for_timeout(3000)
def session(p, w=1440, h=900):
    b = p.chromium.launch(executable_path=EX, headless=True)
    ctx = b.new_context(viewport={'width': w, 'height': h})
    return b, ctx, ctx.new_page()
