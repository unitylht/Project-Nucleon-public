// Read-only layout check at phone and desktop widths (headless Chromium via Playwright).
//   NODE_PATH=<dir containing node_modules/playwright> node deploy/layout_check.js [base-url] [--seed]
// Measures real layout boxes against the configured width, not window.innerWidth: mobile emulation widens the layout
// viewport to fit wide content, which hid a top-bar overflow before. Signs in (codes from the private service log, never
// printed), switches roles and opens pages; it submits nothing else, so it is safe on the shared practice instance.
// --seed is for a fresh scratch server from deploy/ui_check_server.py only, with NUCLEON_LOG set to its log (deploy/scratch_only.js refuses the rest): it first adds a customer, an invoice
// and a request, so that a case waiting for the owner's decision is measured.
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BASE = process.argv.slice(2).find(a => !a.startsWith('--')) || 'https://nucleon.dracooz.top';
// --seed writes: refuse anything but a scratch server on this machine, with NUCLEON_LOG naming its log, before reading a log or opening a page.
if (process.argv.includes('--seed')) require('./scratch_only')('layout check --seed', BASE, process.env.NUCLEON_LOG);
const LOG = process.env.NUCLEON_LOG || path.join(os.homedir(), 'Library/Logs/nucleon/service.log');
const logText = fs.readFileSync(LOG, 'utf8');
const latest = logText.slice(logText.lastIndexOf(' URL: http'));
const codes = Object.fromEntries([...latest.matchAll(/^(STAFF|OWNER|OPERATOR) access code: (\S+)$/gm)].map(m => [m[1].toLowerCase(), m[2]]));
const results = [];
const check = (name, ok, detail = '') => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'} ${name.padEnd(66)} ${String(detail).replace(/\s+/g, ' ').slice(0, 150)}`); };

async function signIn(page, code) {
  await page.waitForSelector('#signin');
  await page.fill('#code', code);
  await page.click('#signin [type=submit]');
  await page.waitForSelector('header.top');
}
const go = (page, hash) => page.evaluate(h => { location.hash = h; }, hash);

// Everything measured against the configured width: the document, each visible header and navigation control, and any element
// outside a scroll box (the case tabs and customer sub-navigation may scroll sideways by design).
function measure(width) {
  const doc = document.documentElement;
  const controls = [...document.querySelectorAll('header.top a, header.top button, .tabbar a, .tabbar summary')].filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' && !el.closest('details:not([open]) .more-menu'))   // the links in a closed More menu are not on screen
    .map(el => {
      const r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(Math.min(Math.max(r.left + r.width / 2, 0), width - 1), r.top + r.height / 2);
      return { name: (el.getAttribute('aria-label') || el.textContent).trim().replace(/\s+/g, ' ').slice(0, 20), left: Math.round(r.left), right: Math.round(r.right),
               reachable: !!hit && (el === hit || el.contains(hit) || hit.contains(el)) };
    }).filter(c => c.name && c.name !== 'Skip to content');
  const outside = [...document.querySelectorAll('body *')].filter(el => {
    if (el.closest('.tabs, .subnav, .skip, dialog:not([open])') || !el.getClientRects().length) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && (r.right > width + 1 || r.left < -1);
  }).map(el => el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.split(' ')[0] : ''));
  return { scrollWidth: doc.scrollWidth, controls, outside: [...new Set(outside)].slice(0, 6) };
}

async function pageAt(page, label, width) {
  await page.waitForTimeout(400);
  const m = await page.evaluate(measure, width);
  const bad = m.controls.filter(c => c.left < 0 || c.right > width || !c.reachable);
  check(`${label}: document width ${m.scrollWidth} <= ${width}`, m.scrollWidth <= width, m.outside.join(' ') || '');
  check(`${label}: every header and navigation control inside and reachable`, bad.length === 0, bad.map(c => `${c.name} ${c.left}-${c.right}${c.reachable ? '' : ' covered'}`).join(', '));
  check(`${label}: nothing sticks out of the page`, m.outside.length === 0, m.outside.join(' '));
}

async function run(browser, width, mobile) {
  const tag = `${width}px${mobile ? ' mobile' : ''}`;
  const ctx = await browser.newContext({ viewport: { width, height: 844 }, isMobile: mobile, hasTouch: mobile });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await signIn(page, codes.owner);
  await page.waitForSelector('[data-testid=home-page]');
  await pageAt(page, `${tag} the Owner's home page`, width);
  if (mobile || width < 761) {   // the More menu opens over the page and its links stay inside the screen
    await page.click('.tabbar .tab-more summary');
    await page.waitForSelector('.tabbar .more-menu a');
    await pageAt(page, `${tag} the More menu`, width);
    await page.click('.tabbar .tab-more summary');
  }
  await go(page, '#/delegation');
  await page.waitForSelector('[data-testid=delegation-page]');
  await pageAt(page, `${tag} the control panel`, width);
  await go(page, '#/cases');
  await page.waitForSelector('.case-row, .queue .empty');
  await pageAt(page, `${tag} cases (the list)`, width);
  // Role switching: staff asks for its code once, then one click switches either way.
  await page.click('[data-role=staff]');
  await signIn(page, codes.staff);
  const pressed = role => page.getAttribute(`[data-role=${role}]`, 'aria-pressed');
  check(`${tag} role switch to staff`, (await pressed('staff')) === 'true');
  await page.click('[data-role=owner]');
  await page.waitForFunction(() => document.querySelector('[data-role=owner]')?.getAttribute('aria-pressed') === 'true');
  check(`${tag} role switch back to owner`, (await pressed('owner')) === 'true');
  const first = await page.$('.case-row');
  if (first) {
    await first.click();
    await page.waitForSelector('.case');
    await pageAt(page, `${tag} case`, width);
  }
  const nav = mobile || width < 761 ? '.tabbar' : 'header.top';
  await page.click(`${nav} a[data-area=customers]`);
  await page.waitForSelector('#cust-rows, .page-customers .state-msg');
  check(`${tag} Customers reached from the navigation`, (await page.evaluate(() => location.hash)) === '#/customers');
  await pageAt(page, `${tag} customers`, width);
  const customer = await page.$('#cust-rows a');
  if (customer) { await customer.click(); await page.waitForSelector('.tab-body'); await pageAt(page, `${tag} one customer`, width); }
  await page.click(`${nav} a[data-area=imports]`);
  await page.waitForSelector('.page-imports h1');
  await pageAt(page, `${tag} imports`, width);
  await page.click(`${nav} a[data-area=requests]`);
  await page.waitForSelector('.case-row, .queue .empty');
  check(`${tag} back to requests from the navigation`, (await page.evaluate(() => location.hash)) === '#/cases');
  check(`${tag} no demo console link for case roles`, !(await page.$('a[href="#/console"]')));
  await go(page, '#/console');
  await signIn(page, codes.operator);
  await page.waitForSelector('[data-testid=console-cases]');
  check(`${tag} demo console opens with its own code (nothing is reset)`, await page.isVisible('[data-testid=console-cases]'));
  await pageAt(page, `${tag} demo console`, width);
  // Sign out ends every role this browser holds, at once (QA B1).
  await page.click('#signout');
  check(`${tag} one sign-out ends every role in this browser`, await page.waitForSelector('#signin', { timeout: 5000 }).then(() => true, () => false)
    && (await page.evaluate(async () => (await (await fetch('/api/session')).json()).signedIn)).length === 0);
  check(`${tag} no script errors`, errors.length === 0, errors.join(' | '));
  await ctx.close();
}

// --seed: through the API, as a person would enter it: a customer, an invoice and a request that waits for the owner.
async function seed(browser) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await signIn(page, codes.owner);
  await page.click('[data-role=staff]');
  await signIn(page, codes.staff);
  const call = (role, p, body) => page.evaluate(async ([role, p, body]) => (await fetch(BASE_PATH + p, { method: body ? 'POST' : 'GET', body: body && JSON.stringify(body),
    headers: { 'X-Nucleon-Role': role, 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() } })).json(), [role, p, body]);
  const customer = await call('staff', '/api/records/customers', { name: 'Bayside Café' });
  await call('staff', '/api/records/invoices', { customerId: customer.record.id, reference: 'DEMO-501', issueDate: '2026-10-01', dueDate: '2026-10-20', total: '1200.00',
    stillOwed: '1200.00', stillOwedAsOf: '2026-10-16' });
  const made = await call('staff', '/api/requests', { messageText: 'Hi, Bayside Café here. Could we pay invoice DEMO-501 on 2026-11-10 instead?' });
  await page.waitForFunction(async id => { const c = await (await fetch(BASE_PATH + '/api/requests/' + id, { headers: { 'X-Nucleon-Role': 'owner' } })).json();
    return c.status === 'awaiting_owner'; }, made.id, { timeout: 30000, polling: 500 });
  console.log(`seeded ${made.id}: waiting for the owner`);
  await ctx.close();
}

(async () => {
  const browser = await chromium.launch();
  console.log(`LAYOUT CHECK | ${BASE} | Chromium ${browser.version()}`);
  try {
    if (process.argv.includes('--seed')) await seed(browser);
    for (const [width, mobile] of [[375, false], [375, true], [390, false], [390, true], [820, false], [1366, false]]) await run(browser, width, mobile);
  } catch (e) {
    check('layout check completed', false, e.message);
  }
  await browser.close();
  console.log(`RESULT layout: ${results.filter(Boolean).length}/${results.length} checks passed`);
  process.exit(results.every(Boolean) ? 0 : 1);
})();
