// Real-browser check of the deployed UI (headless Chromium via Playwright). Run on the server:
//   NODE_PATH=<dir containing node_modules/playwright> node deploy/browser_check.js [base-url] [--fallback | --legacy | --records]
// Reads the current codes from the private service log (NUCLEON_LOG overrides the path) and writes screenshots,
// which never show a code, to ~/srv/nucleon/reports/browser (NUCLEON_SHOTS overrides). Run each mode on an isolated database
// (nucleonctl isolate <name>): --fallback with `unreachable-model`; --legacy on a copy of an extension-v0.2 database;
// --records on a database seeded as an empty practice workspace (deploy/e2e_records_check.py seed <db> practice).
// The live mode resets the demo data through the console (and undoes it): never run it on the shared instance.
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BASE = process.argv.slice(2).find(a => !a.startsWith('--')) || 'https://nucleon.dracooz.top';
const MODE = process.argv.includes('--fallback') ? 'fallback' : process.argv.includes('--legacy') ? 'legacy' : process.argv.includes('--records') ? 'records' : 'live';
const LOG = process.env.NUCLEON_LOG || path.join(os.homedir(), 'Library/Logs/nucleon/service.log');
const OUT = process.env.NUCLEON_SHOTS || path.join(os.homedir(), 'srv/nucleon/reports/browser');
fs.mkdirSync(OUT, { recursive: true });
const logText = fs.readFileSync(LOG, 'utf8');
const latest = logText.slice(logText.lastIndexOf(' URL: http'));   // codes printed by the most recent start
const codes = Object.fromEntries([...latest.matchAll(/^(STAFF|OWNER|OPERATOR) access code: (\S+)$/gm)].map(m => [m[1].toLowerCase(), m[2]]));
const results = [];
const check = (name, ok, detail = '') => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'} ${name.padEnd(60)} ${String(detail).replace(/\s+/g, ' ').slice(0, 140)}`); };
const shot = (page, name, full = false) => page.screenshot({ path: path.join(OUT, `v05-${MODE}-${name}.png`), fullPage: full });
const expected = [];   // deliberate failures this script provokes: [status, path pattern]

async function signIn(page, code) {
  await page.waitForSelector('#signin');
  await page.fill('#code', code);
  await page.click('#signin [type=submit]');
  await page.waitForSelector('header.top');
}
const status = page => page.getAttribute('[data-testid=status]', 'data-status');
const settle = (page, timeout = 300000) => page.waitForFunction(() => { const s = document.querySelector('[data-testid=status]')?.dataset.status; return s && !['received', 'analysing'].includes(s); }, null, { timeout });
const go = (page, hash) => page.evaluate(h => { location.hash = h; }, hash);
async function submit(page, sample) {
  await go(page, '#/cases/new');
  await page.waitForSelector('#composer');
  await page.click('#composer details.samples summary');
  await page.click(`[data-sample="${sample}"]`);
  await page.click('#composer [type=submit]');
  await page.waitForFunction(() => location.hash.startsWith('#/case/'));
  const id = await page.evaluate(() => location.hash.slice(7).split('?')[0]);
  await page.waitForSelector(`.case[data-case="${id}"]`);   // the case itself, not just the list highlight
  return id;
}
async function openCase(page, id) {
  await go(page, '#/case/' + id);
  await page.waitForSelector(`.case[data-case="${id}"]`);
}
async function asRole(page, role) {
  await page.click(`[data-role=${role}]`);
  await page.waitForFunction(r => document.querySelector(`[data-role=${r}]`)?.getAttribute('aria-pressed') === 'true', role);
}
const held = page => page.evaluate(async () => (await (await fetch('/api/session')).json()).signedIn);
// After a dialog's save the page reloads the records (GET /api/records) and draws itself again.
async function save(page, click) {
  const reload = page.waitForResponse(r => new URL(r.url()).pathname === '/api/records' && r.request().method() === 'GET', { timeout: 30000 });
  await click();
  await reload;
  await page.waitForTimeout(250);
}

async function live(page) {
  await signIn(page, codes.staff);
  await page.click('[data-role=owner]');            // not signed in as owner yet: asks for the code once
  await signIn(page, codes.owner);
  await asRole(page, 'staff');
  check('one browser holds staff and owner sign-ins', JSON.stringify(await held(page)) === '["owner","staff"]');
  await page.waitForFunction(() => document.querySelector('#agent span')?.textContent === 'Agent ready', null, { timeout: 15000 }).catch(() => {});
  check('agent status shown in the top bar', (await page.textContent('#agent')).includes('Agent ready'), await page.textContent('#agent'));

  // 1. Unclear customer: the agent asks; a wrong invoice gets an inline error that keeps the input.
  const unclear = await submit(page, 3);
  const progress = await page.waitForSelector('[data-testid=progress]', { timeout: 8000 }).then(() => true).catch(() => false);
  check('progress shown while the agent works', progress);
  if (progress) await shot(page, '01-staff-progress');
  await settle(page);
  check('unclear customer: agent asks staff for the invoice', (await status(page)) === 'needs_information', await page.textContent('[data-testid=status]'));
  await page.fill('[name=invoiceReference]', 'DEMO-999');
  expected.push([422, '/clarifications/']);
  await page.click('#answer [type=submit]');
  await page.waitForFunction(() => document.querySelector('[data-error-for=invoiceReference]')?.textContent.length > 0, null, { timeout: 10000 });
  check('unknown invoice: error under the field, input kept', (await page.inputValue('[name=invoiceReference]')) === 'DEMO-999', await page.textContent('[data-error-for=invoiceReference]'));
  await shot(page, '02-staff-clarify-error');
  await page.fill('[name=invoiceReference]', 'DEMO-101');
  await page.click('#answer [type=submit]');
  await page.waitForFunction(() => document.querySelector('[data-testid=status]')?.dataset.status !== 'needs_information', null, { timeout: 15000 });
  await settle(page);
  check('answer continues to the owner', (await status(page)) === 'awaiting_owner', await page.textContent('[data-testid=status]'));

  // 2. Overdue invoice and 3. clear request, both for the owner.
  const overdue = await submit(page, 4);
  await settle(page);
  check('overdue invoice: red late lane on the timeline', await page.isVisible('.timeline .span.late') && (await page.textContent('.timeline')).includes('7 days late'));
  const clear = await submit(page, 0);
  await settle(page);
  check('clear request: with the owner, prepared by Gemma', (await status(page)) === 'awaiting_owner' && (await page.textContent('[data-testid=provenance]')).includes('Gemma'));
  check('facts written by the app: 10 days, AUD 1,250.00', (await page.textContent('.facts')).includes('10 days') && (await page.textContent('.facts')).includes('AUD 1,250.00'));
  check('customer words underlined where the agent quoted them', await page.isVisible('[data-testid=message] mark'));
  check('staff page has no decision controls', !(await page.isVisible('#decide')));
  await shot(page, '03-staff-with-owner', true);

  // Owner: one click to switch; decide the clear request with a different date, decline the overdue one.
  await asRole(page, 'owner');
  await go(page, '#/cases');
  await page.waitForSelector('.group h2');
  check('owner list leads with cases needing a decision', (await page.textContent('.group h2')).startsWith('For you') && (await page.$$('.group:first-child .case-row')).length === 3);
  await openCase(page, clear);
  await page.waitForSelector('#decide');
  await shot(page, '04-owner-decision');
  check('decision panel states there is no recommendation', (await page.textContent('#decide')).includes("doesn't recommend"));
  await page.check('input[name=outcome][value=other]');
  await page.fill('#approvedDueDate', '2026-11-03');
  await page.fill('#reason', 'Browser check: this invoice only');
  check('button names the action', (await page.textContent('#decide [type=submit]')) === 'Approve Tue 3 Nov', await page.textContent('#decide [type=submit]'));
  await page.click('#decide [type=submit]');
  await page.waitForFunction(() => document.querySelector('[data-testid=status]')?.dataset.status === 'completed', null, { timeout: 20000 });
  check('owner-chosen date committed', (await page.textContent('[data-testid=status]')).includes('Tue 3 Nov 2026'));
  await openCase(page, overdue);
  await page.waitForSelector('#decide');
  await page.check('input[name=outcome][value=decline]');
  await page.fill('#reason', 'Browser check: decline');
  await page.click('#decide [type=submit]');
  await page.waitForFunction(() => document.querySelector('[data-testid=status]')?.dataset.status === 'completed', null, { timeout: 20000 });
  check('decline committed; original due date stays', (await page.textContent('[data-testid=status]')).includes('Declined'));

  // The clarified DEMO-101 case was prepared before the approval moved the due date: it is now stale.
  await openCase(page, unclear);
  await page.waitForSelector('#decide');
  await page.check('input[name=outcome][value=approve]');
  await page.fill('#reason', 'Browser check: stale');
  expected.push([409, '/decisions']);
  await page.click('#decide [type=submit]');
  await page.waitForFunction(() => document.querySelector('#decide [data-error-for=form]')?.textContent.length > 0, null, { timeout: 10000 }).catch(() => {});
  check('stale evidence caught before deciding', ((await page.textContent('#decide [data-error-for=form]').catch(() => '')) || '').includes('changed') || (await status(page)) === 'analysing',
    await page.textContent('#decide [data-error-for=form]').catch(() => 'case moved on'));

  // Staff copy the reply for the changed-date decision.
  await asRole(page, 'staff');
  await openCase(page, clear);
  await page.waitForSelector('#copy');
  check('reply draft states the owner\'s date only, written out', (await page.textContent('#draft')).includes('Tuesday 3 November 2026') && !(await page.textContent('#draft')).includes('2026-'));
  await page.click('#copy');
  await page.waitForFunction(() => document.querySelector('#copy')?.textContent.trim() === 'Copied', null, { timeout: 5000 });
  check('copy reply confirms on the button and puts the draft on the clipboard', (await page.evaluate(() => navigator.clipboard.readText())).includes('Tuesday 3 November 2026'));
  await shot(page, '05-staff-reply', true);
  await page.reload();
  await page.waitForSelector('#copy');
  check('decision survives a page reload', (await status(page)) === 'completed');

  // Demo console: reset, then undo. The console asks for its own code; staff have no link to it.
  check('staff see no demo console link', !(await page.$('a[href="#/console"]')));
  await go(page, '#/console');
  await signIn(page, codes.operator);
  await page.waitForSelector('#reset');
  await page.click('#reset');
  await page.click('dialog[open] [type=submit]');
  await page.waitForSelector('[data-testid=console-result]');
  check('console reset clears every case', (await page.textContent('[data-testid=console-cases]')).startsWith('No cases'), await page.textContent('[data-testid=console-result]'));
  await shot(page, '06-console-after-reset', true);
  await page.click('#undo');
  await page.waitForFunction(() => document.querySelector('[data-testid=console-result]')?.textContent.includes('Undone'));
  check('undo restores the cases', (await page.textContent('[data-testid=console-cases]')).startsWith('3 cases'), await page.textContent('[data-testid=console-cases]'));
}

// Stage 3 records, as a person uses them: opening balance and credits, a suggestion confirmed, a payment allocated, completeness
// confirmed by the owner, an exact amount, and a credit that blocks an amount until it is accounted for.
async function records(page) {
  await signIn(page, codes.owner);
  await page.click('[data-role=staff]');
  await signIn(page, codes.staff);
  await asRole(page, 'owner');
  await go(page, '#/setup');
  await page.waitForSelector('#basics');
  await page.fill('#f-businessName', 'Browser check (fictional)');
  await page.click('#basics [type=submit]');
  await page.waitForSelector('.checklist');
  const today = await page.evaluate(() => api('/api/setup').then(s => s.asOfDate));   // the page's own helper says which role is acting
  const day = n => { const d = new Date(today + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const asat = day(-18);
  const ids = {};
  for (const name of ['Bayside Café', 'Kiosk Co']) {
    await go(page, '#/customers');
    await page.click('[data-act=add-customer]');
    await page.fill('dialog[open] [name=name]', name);
    await page.click('dialog[open] [type=submit]');
    await page.waitForFunction(() => /^#\/customers\/customer_/.test(location.hash));
    ids[name] = await page.evaluate(() => location.hash.split('/')[2].split('?')[0]);
    await page.waitForSelector('.tab-body');
  }
  const dialog = page.locator('dialog[open]');
  const opening = async (customer, amount, direction, credits) => {
    await go(page, `#/customers/${ids[customer]}/balance`);
    await page.click('[data-act=opening]');
    await dialog.locator('[name=asOf]').fill(asat);
    await dialog.locator('[name=amount]').fill(amount);
    await dialog.locator(`[name=direction][value=${direction}]`).check();
    await dialog.locator('[name=credits]').selectOption(credits);
    await dialog.locator('[name=sourceLabel]').fill("Accountant's balance list (fictional)");
    await save(page, () => dialog.locator('[type=submit]').click());
  };
  await opening('Bayside Café', '1500.00', 'owed', 'none');
  await opening('Kiosk Co', '50.00', 'credit', '');
  const invoice = async (customer, ref, issue, total, owed) => {
    await go(page, `#/customers/${ids[customer]}/invoices`);
    await page.click('.page-actions [data-act=add-invoice]');
    await dialog.locator('[name=reference]').fill(ref);
    await dialog.locator('[name=issueDate]').fill(issue);
    await dialog.locator('[name=total]').fill(total);
    await dialog.locator('[name=dueDate]').fill(day(-2));
    await dialog.locator('[name=stillOwed]').fill(owed || '');
    if (owed) await dialog.locator('[name=stillOwedAsOf]').fill(asat);
    await save(page, () => dialog.locator('[type=submit]').click());
    await page.waitForSelector(`.rtable tr:has-text("${ref}")`, { timeout: 5000 }).catch(async () => {
      throw new Error('invoice ' + ref + ' not added');
    });
  };
  await invoice('Bayside Café', 'INV-77', day(-47), '1200.00', '1200.00');
  await invoice('Bayside Café', 'INV-78', day(-33), '300.00', '300.00');
  const row77 = await page.textContent('tr:has-text("INV-77")'), summary = await page.textContent('.att-summary');
  await page.click('.att-summary a');                             // "Review all": the questions and the suggestion are on their own tab
  await page.waitForSelector('.attention');
  check('records: equal amounts are offered as a suggestion, not applied', summary.includes('about the opening balance') &&
    (await page.textContent('.attention')).includes('suggests they make it up') && row77.includes('not answered'), summary);
  await shot(page, '01-records-suggestion', true);
  await save(page, () => page.click('[data-act=confirm-suggestion]'));
  await go(page, `#/customers/${ids['Bayside Café']}/invoices`);
  await page.waitForSelector('tr:has-text("INV-77")');
  check('records: a person confirms the suggestion in one step', (await page.textContent('tr:has-text("INV-77")')).includes('Part of the opening balance'));
  await invoice('Bayside Café', 'INV-501', day(-16), '1000.00');
  await invoice('Kiosk Co', 'INV-K1', day(-13), '100.00');
  await go(page, `#/customers/${ids['Bayside Café']}/payments`);
  await page.click('.page-actions [data-act=add-payment]');
  await dialog.locator('[name=receivedDate]').fill(day(-5));
  await dialog.locator('[name=amount]').fill('600.00');
  await dialog.locator('[name=reference]').fill('EFT 7781');
  await save(page, () => dialog.locator('[type=submit]').click());
  await page.click('tr:has-text("EFT 7781") [data-act=allocate]');
  const target = await dialog.locator('[name=invoiceId] option').evaluateAll(options => options.map(o => [o.value, o.textContent]));
  check('records: a payment is allocated only to its own customer\'s invoices', target.filter(([v]) => v).every(([, text]) => !text.startsWith('INV-K1')), target.map(t => t[1]).join(', '));
  await dialog.locator('[name=invoiceId]').selectOption(target.find(([, text]) => text.startsWith('INV-501'))[0]);
  await dialog.locator('[name=amount]').fill('600.00');
  await save(page, () => dialog.locator('[type=submit]').click());
  await go(page, `#/customers/${ids['Bayside Café']}/invoices`);
  await page.waitForSelector('tr:has-text("INV-501")');
  check('records: allocated payment gives "at most", with why it is not exact', (await page.textContent('tr:has-text("INV-501")')).includes('AUD 400.00') &&
    (await page.textContent('tr:has-text("INV-501")')).includes('At most') && await page.isVisible('tr:has-text("INV-501") details.why'));
  await go(page, `#/completeness`);
  await page.click('.page-actions [data-act=coverage]');
  await dialog.locator('[name=scope][value=all]').check();
  await dialog.locator('[name=type][value=payments]').check();
  await dialog.locator('[name=from]').fill(day(-17));
  await dialog.locator('[name=to]').fill(today);
  await dialog.locator('[name=sourceLabel]').fill('Checked against the bank statements (fictional)');
  await dialog.locator('[type=submit]').click();
  await page.waitForFunction(() => document.querySelector('dialog[open] [data-error-for=confirm]')?.textContent.length > 0);
  check('records: completeness needs the explicit tick', true);
  await dialog.locator('[name=confirm]').check();
  await save(page, () => dialog.locator('[type=submit]').click());
  await go(page, `#/customers/${ids['Bayside Café']}/invoices`);
  await page.waitForSelector('tr:has-text("INV-501")');
  check('records: exact amount once payments are confirmed complete', (await page.textContent('tr:has-text("INV-501") .amount')).includes('Exact'), await page.textContent('tr:has-text("INV-501")'));
  await go(page, `#/customers/${ids['Kiosk Co']}/invoices`);
  await page.click('tr:has-text("INV-K1") details.why summary');
  check('records: an unaccounted opening credit is named as the reason', (await page.textContent('tr:has-text("INV-K1") details.why')).includes('credit of AUD 50.00'));
  await go(page, `#/customers/${ids['Kiosk Co']}/payments`);
  await page.click('.page-actions [data-act=add-payment]');
  await dialog.locator('[name=kind][value=credit]').check();
  await dialog.locator('[name=receivedDate]').fill(asat);
  await dialog.locator('[name=amount]').fill('50.00');
  await dialog.locator('[name=reference]').fill('Credit note CN-12');
  await dialog.locator('[name=inclusion][value=included]').check();
  await save(page, () => dialog.locator('[type=submit]').click());
  check('records: a credit is recorded and shown as part of the opening balance', (await page.textContent('tr:has-text("CN-12")')).includes('Part of the opening balance'));
  await shot(page, '02-records-credit', true);
}

async function fallback(page) {
  await signIn(page, codes.staff);
  await submit(page, 3);   // 'Unclear customer' has neither an invoice number nor an ISO date for the basic parser
  await settle(page);
  check('model failure shown as prepared without AI', (await page.textContent('[data-testid=provenance]')).startsWith('Prepared without AI'));
  check('headline says the AI could not read it', (await page.textContent('[data-testid=status]')).includes("couldn't read"));
  await shot(page, '01-fallback-staff');
  await page.fill('[name=invoiceReference]', 'DEMO-201');
  await page.fill('[name=requestedDueDate]', '2026-10-23');
  await page.click('#answer [type=submit]');
  await page.waitForFunction(() => document.querySelector('[data-testid=status]')?.dataset.status === 'awaiting_owner', null, { timeout: 20000 });
  await page.click('[data-role=owner]');
  await signIn(page, codes.owner);
  await go(page, '#/cases');
  await page.waitForSelector('.group h2');
  check('owner list marks the case as prepared without AI', (await page.textContent('.group:first-child .case-row')).includes('without AI'));
  await page.click('.group:first-child .case-row');
  await page.waitForSelector('#decide');
  check('owner still sees facts and decides', (await page.textContent('.facts')).includes('AUD 480.00'));
  await shot(page, '02-fallback-owner');
}

async function legacy(page) {
  await signIn(page, codes.owner);
  await page.waitForSelector('.case-row');
  const ids = await page.$$eval('.case-row', rows => rows.map(r => r.getAttribute('href').slice(7)));
  let seen = 0;
  for (const id of ids) {
    await openCase(page, id);
    if (await page.isVisible('[data-testid=legacy]')) {
      seen += 1;
      check('legacy case labelled; old suggestion shown only as unused history', (await page.textContent('#sheet')).includes('never validated') && !(await page.isVisible('#decide') && (await page.textContent('#decide')).includes('suggest')));
      if (seen === 1) await shot(page, '01-legacy', true);
    }
  }
  check('legacy cases found and readable', seen > 0, `${seen} of ${ids.length}`);
}

(async () => {
  const browser = await chromium.launch();
  console.log(`BROWSER CHECK ${MODE} | ${BASE} | Chromium ${browser.version()}`);
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await ctx.newPage();
  const errors = [], failed = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) errors.push(m.text()); });
  page.on('response', r => { if (r.status() >= 400) failed.push([r.status(), new URL(r.url()).pathname]); });
  try {
    await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
    check('sign-in served', await page.isVisible('#signin'), page.url());
    await ({ live, fallback, legacy, records })[MODE](page);
    // Widths below are compared with the configured 390, not innerWidth: mobile emulation widens innerWidth to fit wide content.
    const phone = await (await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true })).newPage();
    phone.on('pageerror', e => errors.push(e.message));
    await phone.goto(BASE);
    await signIn(phone, codes.owner);
    if (MODE === 'records') {
      await go(phone, '#/customers');
      await phone.waitForSelector('#cust-rows');
      check('phone: Customers page without horizontal scroll', !(await phone.evaluate(() => document.documentElement.scrollWidth > 390)));
      await phone.screenshot({ path: path.join(OUT, `v05-${MODE}-07-phone-customers.png`), fullPage: true });
    } else {
      await phone.waitForSelector('.case-row');
      check('phone: list without horizontal scroll', !(await phone.evaluate(() => document.documentElement.scrollWidth > 390)));
      await phone.screenshot({ path: path.join(OUT, `v05-${MODE}-07-phone-list.png`) });
      await phone.click('.case-row');
      await phone.waitForSelector('[data-testid=status]');
      check('phone: case alone on screen, no horizontal scroll', !(await phone.isVisible('.queue')) && !(await phone.evaluate(() => document.documentElement.scrollWidth > 390)));
      await phone.screenshot({ path: path.join(OUT, `v05-${MODE}-08-phone-case.png`), fullPage: true });
    }
    check('no JavaScript or console errors', errors.length === 0, errors.join(' | '));
    const unexpected = failed.filter(([code, p]) => !expected.some(([c, pattern]) => c === code && p.includes(pattern)));
    check('only the deliberate 4xx responses occurred', unexpected.length === 0, failed.map(f => f.join(' ')).join(' | ') || 'none');
  } catch (e) {
    check('browser flow completed', false, e.message);
    await shot(page, 'error', true).catch(() => {});
  }
  await browser.close();
  console.log(`RESULT browser ${MODE}: ${results.filter(Boolean).length}/${results.length} checks passed`);
  process.exit(results.every(Boolean) ? 0 : 1);
})();
