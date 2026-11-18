// Browser regression check of the redesigned interface, driving it as staff, owner and operator would. Fictional data only.
//   NODE_PATH=<dir with node_modules/playwright> node deploy/ui_check.js <base> <service-log> <fault-base> <fault-log> <out-dir>
// <base> is a fresh scratch server from deploy/ui_check_server.py (mock agent, fictional sample); <fault-base> one started
// with --fault-fallback. Never point it at the shared instance: it creates records, imports, decisions and reverts.
// Every record it creates carries a new tag (UXR + base-36 time), so runs never collide.
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const [BASE, LOG, FAULT_BASE, FAULT_LOG, OUT] = process.argv.slice(2);
require('./scratch_only')('ui check', BASE, LOG);
require('./scratch_only')('ui check (fault server)', FAULT_BASE, FAULT_LOG);
const TAG = 'UXR' + Date.now().toString(36).slice(-5).toUpperCase();
const codesFrom = file => { const t = fs.readFileSync(file, 'utf8'); const latest = t.slice(t.lastIndexOf(' URL: http'));
  return Object.fromEntries([...latest.matchAll(/^(STAFF|OWNER|OPERATOR) access code: (\S+)$/gm)].map(m => [m[1].toLowerCase(), m[2]])); };
const codes = codesFrom(LOG), faultCodes = codesFrom(FAULT_LOG);
fs.mkdirSync(OUT, { recursive: true });
const results = [];
const check = (name, ok, detail = '') => { results.push([name, !!ok]); console.log(`${ok ? 'PASS' : 'FAIL'} ${name.padEnd(78)} ${String(detail).replace(/\s+/g, ' ').slice(0, 160)}`); };
const errors = [], failed = [];
const expected = [];   // deliberate 4xx responses: [status, path fragment]
const csv = (name, text) => { const f = path.join(OUT, name); fs.writeFileSync(f, text); return f; };

function watch(page, label) {
  page.on('pageerror', e => errors.push(`${label}: ${e.message}`));
  page.on('console', m => { if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) errors.push(`${label}: ${m.text()}`); });
  page.on('response', r => { if (r.status() >= 400) failed.push([r.status(), new URL(r.url()).pathname]); });
  return page;
}
async function newPage(browser, label, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, permissions: ['clipboard-read', 'clipboard-write'], ...opts });
  return watch(await ctx.newPage(), label);
}
async function signIn(page, code, base = BASE) {
  if (!(await page.$('#signin'))) await page.goto(base);
  await page.waitForSelector('#signin');
  await page.fill('#code', code);
  await page.click('#signin [type=submit]');
  await page.waitForSelector('header.top');
}
const go = (page, hash) => page.evaluate(h => { location.hash = h; }, hash);
const held = page => page.evaluate(async () => (await (await fetch('/api/session')).json()).signedIn);
const text = (page, sel) => page.textContent(sel).then(t => (t || '').replace(/\s+/g, ' ').trim()).catch(() => '');
const dlg = page => page.locator('dialog[open]');
async function save(page, click) {   // a dialog save reloads the records and redraws the page
  const reload = page.waitForResponse(r => new URL(r.url()).pathname === '/api/records' && r.request().method() === 'GET', { timeout: 30000 });
  await click();
  await reload;
  await page.waitForTimeout(300);
}
const status = page => page.getAttribute('[data-testid=status]', 'data-status');
const settled = (page, want) => page.waitForFunction(w => { const s = document.querySelector('[data-testid=status]')?.dataset.status; return s && (w ? w.includes(s) : !['received', 'analysing'].includes(s)); }, want || null, { timeout: 60000 });
const api = (page, role, p, body) => page.evaluate(async ([role, p, body]) => {
  const r = await fetch(p, { method: body ? 'POST' : 'GET', headers: { 'X-Nucleon-Role': role, 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() }, body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, body: await r.json().catch(() => ({})) };
}, [role, p, body]);
async function asRole(page, role) {
  await page.click(`[data-role=${role}]`);
  await page.waitForFunction(r => document.querySelector(`[data-role=${r}]`)?.getAttribute('aria-pressed') === 'true', role);
}
async function request(page, message) {   // through the form, at #/cases/new
  await go(page, '#/cases/new');
  await page.waitForSelector('#composer');
  await page.fill('#message', message);
  await page.click('#composer [type=submit]');
  await page.waitForFunction(() => location.hash.startsWith('#/case/'));
  const id = await page.evaluate(() => location.hash.slice(7).split('?')[0]);
  await page.waitForSelector(`.case[data-case="${id}"]`);
  await settled(page);
  return id;
}
async function openCase(page, id) { await go(page, '#/case/' + id); await page.waitForSelector(`.case[data-case="${id}"]`); }
async function customerId(page, name) {
  const r = await api(page, 'staff', '/api/records');
  return r.body.customers.find(c => c.name === name)?.id;
}
async function addCustomer(page, name) {
  await go(page, '#/customers');
  await page.click('.page-actions [data-act=add-customer], .state-msg [data-act=add-customer]');
  await dlg(page).locator('[name=name]').fill(name);
  await dlg(page).locator('[type=submit]').click();
  await page.waitForFunction(() => /^#\/customers\/customer_/.test(location.hash));
  await page.waitForSelector('.tab-body');
  return page.evaluate(() => location.hash.split('/')[2].split('?')[0]);
}
async function addInvoice(page, id, values) {
  await go(page, `#/customers/${id}/invoices`);
  await page.waitForSelector('.tab-body');
  await page.click('.page-actions [data-act=add-invoice]');
  for (const [k, v] of Object.entries(values)) await dlg(page).locator(`[name=${k}]`).fill(v);
  await save(page, () => dlg(page).locator('[type=submit]').click());
}
async function upload(page, shape, label, file) {
  await go(page, '#/imports/new');
  await page.waitForSelector('#upload');
  await page.check(`#upload [name=shape][value=${shape}]`);
  await page.fill('#upload [name=sourceLabel]', label);
  await page.setInputFiles('#upload [name=file]', file);
  await page.click('#upload [type=submit]');
  await page.waitForSelector('#params');
  return page.evaluate(() => location.hash.split('/')[2]);
}
async function resolveNew(page) {
  for (const sel of await page.$$('#params select[name^=cust-]')) await sel.selectOption('new');
  await page.click('#params [type=submit]');
  await page.waitForFunction(() => !document.querySelector('#params select[name^=cust-]') || [...document.querySelectorAll('#params select[name^=cust-]')].every(s => s.value));
  await page.waitForSelector('#apply:not([aria-disabled=true])');
}
async function applyDraft(page) {
  await page.click('#apply');
  await page.waitForSelector('.page-import .status-line .chip.done', { timeout: 20000 });
}

// ---------------------------------------------------------------- A. sign-in, roles, sign-out

async function sessions(browser) {
  const a = await newPage(browser, 'A1');
  await a.goto(BASE);
  await signIn(a, codes.staff);
  check('A1 staff frame has no demo console link', !(await a.$('a[href="#/console"]')));
  await a.click('[data-role=owner]');
  await a.waitForSelector('#signin');
  check('A1 owner prompt names the role', (await text(a, '#signin h1')) === 'Sign in as owner', await text(a, '#signin h1'));
  expected.push([403, '/api/demo/login']);
  await a.fill('#code', codes.staff);
  await a.click('#signin [type=submit]');
  await a.waitForFunction(() => document.querySelector('[data-error-for=accessCode]')?.textContent.length > 0);
  check('A1 a staff code at the owner prompt is refused with a message (U2)', (await text(a, '[data-error-for=accessCode]')).startsWith('That is the staff code'), await text(a, '[data-error-for=accessCode]'));
  check('A1 the refused code creates no session', JSON.stringify(await held(a)) === '["staff"]', JSON.stringify(await held(a)));
  await a.fill('#code', codes.owner);
  await a.click('#signin [type=submit]');
  await a.waitForSelector('header.top');
  check('A1 owner code at the owner prompt switches to owner', (await a.getAttribute('[data-role=owner]', 'aria-pressed')) === 'true');
  await a.click('#signout');
  await a.waitForSelector('#signin');
  check('A1 sign-out from Owner ends both roles in this browser (B1)', JSON.stringify(await held(a)) === '[]' && (await text(a, '#signin .callout')).includes('owner and staff'), await text(a, '#signin .callout'));
  await a.reload();
  await a.waitForSelector('#signin');
  check('A1 still signed out after a reload', JSON.stringify(await held(a)) === '[]');

  const b = await newPage(browser, 'A2');
  const mate = await newPage(browser, 'A2-teammate');
  await signIn(b, codes.owner);
  await b.click('[data-role=staff]');
  await signIn(b, codes.staff);
  await signIn(mate, codes.staff);
  check('A2 staff selected, owner also held', (await b.getAttribute('[data-role=staff]', 'aria-pressed')) === 'true' && JSON.stringify(await held(b)) === '["owner","staff"]');
  await b.click('#signout');
  await b.waitForSelector('#signin');
  check('A2 sign-out from Staff ends both roles in this browser (B1 mirror)', JSON.stringify(await held(b)) === '[]');
  check('A2 a teammate signed in elsewhere stays signed in', JSON.stringify(await held(mate)) === '["staff"]', JSON.stringify(await held(mate)));
  await b.goto(BASE + '/#/customers');
  await b.waitForSelector('#signin');
  check('A2 records need a sign-in again', await b.isVisible('#signin'));

  const c = await newPage(browser, 'A3');
  await signIn(c, codes.staff);
  await go(c, '#/console');
  await c.waitForSelector('#signin');
  check('A3 the console asks for its own code', (await text(c, '#signin h1')) === 'Open the demo console');
  await c.fill('#code', codes.owner);
  await c.click('#signin [type=submit]');
  await c.waitForFunction(() => document.querySelector('[data-error-for=accessCode]')?.textContent.length > 0);
  check('A3 the owner code at the console prompt is refused, not signed in as owner (U2)', (await text(c, '[data-error-for=accessCode]')).startsWith('That is the owner code') && JSON.stringify(await held(c)) === '["staff"]');

  const d = await newPage(browser, 'A4');
  await signIn(d, codes.operator);
  await d.waitForSelector('[data-testid=console-cases]');
  check('A4 operator lands on the demo console', (await d.evaluate(() => location.hash)) === '#/console');
  check('A4 the console shows no server path (B9)', !(await text(d, '#main')).includes('/Users/') && !(await text(d, '#main')).includes('srv/'));
  await go(d, '#/customers');
  await d.waitForSelector('#signin');
  check('A4 operator off the console can see they are signed in and sign out (U11)', (await text(d, '.held')).includes('Demo console') && await d.isVisible('#gate-signout'));
  await d.click('#gate-signout');
  await d.waitForSelector('#signin .callout');
  check('A4 operator signed out from that page', JSON.stringify(await held(d)) === '[]');
  // B7: leaving the console while it loads draws nothing into the next page.
  await signIn(d, codes.operator);
  await d.waitForSelector('[data-testid=console-cases]');
  await d.route('**/api/demo/console', async r => { await new Promise(x => setTimeout(x, 1500)); await r.continue(); });
  await go(d, '#/requests'); await d.waitForTimeout(150); await go(d, '#/console'); await d.waitForTimeout(150); await go(d, '#/customers');
  await d.waitForTimeout(2500);
  check('A4 navigating away from a loading console raises no error (B7)', !errors.some(e => e.startsWith('A4')), errors.filter(e => e.startsWith('A4')).join(' | '));
  for (const p of [a, b, mate, c, d]) await p.context().close();
}

// ---------------------------------------------------------------- B. the main staff and owner flows

async function main(browser) {
  const page = await newPage(browser, 'B');
  await signIn(page, codes.staff);
  await page.click('[data-role=owner]');
  await signIn(page, codes.owner);
  await asRole(page, 'staff');

  // B1 manual records: the customer is fixed by the page it is added from (U1); no date is filled in for you (G3).
  const manualA = await addCustomer(page, `${TAG} Manual A fictional`);
  const manualB = await addCustomer(page, `${TAG} Manual B fictional`);
  await go(page, `#/customers/${manualA}/invoices`);
  await page.waitForSelector('.tab-body');
  await page.click('.page-actions [data-act=add-invoice]');
  check('B1 add-invoice names the customer and offers no customer picker (U1)', (await text(page, 'dialog[open] .fixed')).includes(`${TAG} Manual A fictional`) && !(await page.$('dialog[open] select[name=customerId]')));
  check('B1 the still-owed date starts empty (G3)', (await dlg(page).locator('[name=stillOwedAsOf]').inputValue()) === '');
  await dlg(page).locator('[name=reference]').fill('DEMO-901');
  await page.keyboard.press('Escape');
  await page.waitForSelector('dialog[open]', { state: 'detached' });
  await page.click('.page-actions [data-act=add-invoice]');
  check('B1 closing a dialog keeps what was typed (draft kept)', (await dlg(page).locator('[name=reference]').inputValue()) === 'DEMO-901' && await page.isVisible('dialog[open] .restored'));
  await page.click('dialog[open] [data-forget]');
  await page.waitForFunction(() => document.querySelector('dialog[open] [name=reference]')?.value === '');
  check('B1 "Start again" discards the kept draft', !(await page.isVisible('dialog[open] .restored')));
  await dlg(page).locator('[name=reference]').fill('DEMO-901');
  await dlg(page).locator('[name=issueDate]').fill('2026-10-05');
  await dlg(page).locator('[name=total]').fill('1000.00');
  await dlg(page).locator('[name=stillOwed]').fill('900.00');
  await dlg(page).locator('[type=submit]').click();
  check('B1 an amount still owed without its date is explained', (await text(page, 'dialog[open] [data-error-for=stillOwedAsOf]')).startsWith('Enter the date'));
  await dlg(page).locator('[name=stillOwed]').fill('');
  await save(page, () => dlg(page).locator('[type=submit]').click());
  check('B1 invoice added under the right customer', (await text(page, '.tab-body')).includes('DEMO-901') && (await text(page, '.tab-body tr:has-text("DEMO-901")')).includes('Worked out'));   // none recorded: the replay's remainder, marked worked out
  await addInvoice(page, manualB, { reference: 'DEMO-901', issueDate: '2026-10-05', total: '200.00', dueDate: '2026-10-10' });
  check('B1 the same invoice number is accepted for a second customer', (await text(page, '.tab-body')).includes('DEMO-901'));

  // B2 knowledge: a staff draft, confirmed by the owner.
  await go(page, '#/knowledge');
  await page.waitForSelector('.page-knowledge h1');
  await page.click('.page-actions [data-act=add-note]');
  await dlg(page).locator('[name=text]').fill(`${TAG} fictional test customer. Prefers a written payment date.`);
  await dlg(page).locator('[name=scope]').selectOption(manualA);
  check('B2 staff see that their note is a draft', (await text(page, 'dialog[open]')).includes('Saved as a draft') && !(await page.$('dialog[open] [name=confirm]')));
  await save(page, () => dlg(page).locator('[type=submit]').click());
  check('B2 staff note listed as a draft waiting for the owner', (await text(page, `.notes li:has-text("${TAG} fictional test")`)).includes('Draft by staff'));
  await asRole(page, 'owner');
  await go(page, '#/knowledge');
  await page.waitForSelector('.page-knowledge h1');
  check('B2 owner is told drafts wait for confirmation', /drafts? waits? for you to confirm/.test(await text(page, '.page-knowledge .callout')), await text(page, '.page-knowledge .callout'));
  await save(page, () => page.click(`.notes li:has-text("${TAG} fictional test") [data-act=confirm-note]`));
  await page.click('[data-note-filter=confirmed]');
  await page.waitForSelector('.notes');
  check('B2 owner confirmed it', (await text(page, `.notes li:has-text("${TAG} fictional test")`)).includes('Confirmed by the owner'));
  await asRole(page, 'staff');

  // B3 a shared invoice number: staff choose the customer, with a specific message if they don't (U10).
  const shared = await request(page, `Test ${TAG}. Could we pay invoice DEMO-901 on 2026-11-14 instead?`);
  check('B3 shared number: the agent asks which customer, offering both', (await status(page)) === 'needs_information' && (await text(page, '#answer')).includes(`${TAG} Manual A fictional`) && (await text(page, '#answer')).includes(`${TAG} Manual B fictional`));
  await page.click('#answer [type=submit]');
  check('B3 sending with no choice says what to choose (U10)', (await text(page, '#answer [data-error-for=invoiceId]')) === 'Choose which customer\'s invoice this is.');
  await page.click(`#answer label:has-text("${TAG} Manual A fictional")`);
  await page.click('#answer [type=submit]');
  await settled(page, ['awaiting_owner']);
  check('B3 with the owner after staff chose', (await status(page)) === 'awaiting_owner');
  await page.click('#tab-activity');
  check('B3 activity names the customer chosen, not an internal id (B5)', (await text(page, '#panel-activity')).includes(`Staff answered: ${TAG} Manual A fictional`) && !(await text(page, '#panel-activity')).includes('invoice_'), await text(page, '#panel-activity'));
  check('B3 activity says the agent asked which customer (B5)', (await text(page, '#panel-activity')).includes("asked staff for which customer's invoice it is"));

  // B4 a missing date: specific message, then a past date refused in the browser, then a valid one.
  await request(page, `Test ${TAG}. Could we pay invoice DEMO-101 later?`);
  check('B4 no date: the agent asks for it', (await status(page)) === 'needs_information' && await page.isVisible('#answer [name=requestedDueDate]'));
  await page.click('#answer [type=submit]');
  check('B4 empty date says what to enter (U10)', (await text(page, '#answer [data-error-for=requestedDueDate]')) === 'Enter the payment date the customer asked for.');
  await page.fill('#answer [name=requestedDueDate]', '2026-10-12');
  await page.click('#answer [type=submit]');
  check('B4 a past date is refused with the earliest date', (await text(page, '#answer [data-error-for=requestedDueDate]')).startsWith('Enter a date on or after'));
  await page.fill('#answer [name=requestedDueDate]', '2026-11-20');
  await page.click('#answer [type=submit]');
  await settled(page, ['awaiting_owner']);
  check('B4 with the owner once the date is given', (await status(page)) === 'awaiting_owner');

  // B5 the owner decides with the keyboard; the button names what will be recorded.
  await asRole(page, 'owner');
  await go(page, '#/cases');
  await page.waitForSelector('#sheet .state-msg h2');
  const waiting = (await api(page, 'owner', '/api/requests')).body.filter(c => c.status === 'awaiting_owner').length;
  check('B5 the owner\'s starting point counts with correct plurals (B8)', (await text(page, '#sheet .state-msg')).startsWith(waiting === 1 ? 'One request needs your decision' : `${waiting} requests need your decision`) && (await text(page, '#sheet .state-msg')).includes(waiting === 1 ? 'Open it' : 'Open one'), await text(page, '#sheet .state-msg'));
  await openCase(page, shared);
  await page.waitForSelector('#decide');
  await page.click('#decide [type=submit]');
  check('B5 deciding with no outcome says what to choose', (await text(page, '#decide [data-error-for=outcome]')).startsWith('Choose an outcome'));
  await page.focus('#decide input[name=outcome][value=approve]');
  await page.keyboard.press('Space');
  check('B5 the button names the outcome', (await text(page, '#decide [type=submit]')) === 'Approve Sat 14 Nov', await text(page, '#decide [type=submit]'));
  await page.focus('#reason');
  await page.keyboard.type('Fictional test only');
  await page.keyboard.press('Enter');
  await settled(page, ['completed']);
  check('B5 approved with the keyboard', (await text(page, '[data-testid=status]')).includes('Approved. New payment date: Sat 14 Nov 2026'));
  await page.screenshot({ path: path.join(OUT, 'after-desktop-owner-decided.png'), fullPage: true });

  // B6 staff copy the unsent reply; the button confirms (U3); the date is written out (U4).
  await asRole(page, 'staff');
  await openCase(page, shared);
  await page.waitForSelector('#copy');
  check('B6 reply date written out, not ISO (U4)', (await text(page, '#draft')).includes('Saturday 14 November 2026') && !(await text(page, '#draft')).includes('2026-11-14'));
  await page.click('#copy');
  await page.waitForFunction(() => document.querySelector('#copy')?.textContent.trim() === 'Copied');
  check('B6 copy confirms on the button and fills the clipboard (U3)', (await page.evaluate(() => navigator.clipboard.readText())).includes('Saturday 14 November 2026'));
  check('B6 decision time is labelled as recorded time (U5)', (await page.getAttribute('[data-testid=decision] time', 'title')).includes('real clock'));

  // B7 from a case to the customer's records and back to the same case.
  await page.click('.case-sub a:has-text("Customer records")');
  await page.waitForSelector('.tab-body');
  check('B7 the customer page offers the way back to the request', (await text(page, '.back')).includes('Back to the request about DEMO-901'), await text(page, '.back'));
  await page.click('.subnav a:has-text("Payments")');
  await page.waitForSelector('.tab-body');
  check('B7 the way back survives a tab change', (await text(page, '.back')).includes('Back to the request'));
  await page.click('.back a');
  await page.waitForSelector(`.case[data-case="${shared}"]`);
  check('B7 back on the same case', (await page.evaluate(() => location.hash)).startsWith('#/case/' + shared));
  check('B7 and the case offers the way back to the customer', (await text(page, '.case .back')).includes(`${TAG} Manual A fictional`));

  // B8 imports: values visible before applying (G2), unchanged re-import, drafts kept or discarded (B4), invalid rows, conflicts.
  const f01 = csv(`${TAG}-01-invoices.csv`, `Customer,Invoice number,Invoice date,Invoice amount,Due date\n${TAG} Imported A fictional,DEMO-951,2026-10-05,1000.00,2026-10-10\n${TAG} Imported B fictional,DEMO-951,2026-10-05,200.00,2026-10-10\n`);
  await upload(page, 'invoices', `${TAG} Invoice test`, f01);
  check('B8 unknown customers hold the import back', (await page.getAttribute('#apply', 'aria-disabled')) === 'true' && (await text(page, '.callout.warn')).includes('Before applying'));
  await resolveNew(page);
  const rows = await text(page, '.rows-table');
  check('B8 the preview shows amounts and dates before applying (G2)', rows.includes('AUD 1,000.00') && rows.includes('AUD 200.00') && rows.includes('Mon 5 Oct 2026') && rows.includes('Sat 10 Oct 2026'), rows.slice(0, 160));
  await page.screenshot({ path: path.join(OUT, 'after-desktop-import-draft.png'), fullPage: true });
  await applyDraft(page);
  const b01 = await page.evaluate(() => location.hash.split('/')[2]);
  check('B8 invoice import applied', (await text(page, '.status-line')).includes('Applied'));
  await upload(page, 'invoices', `${TAG} Invoice test`, f01);
  check('B8 the same file again: recognised, nothing new', (await text(page, '.callout')).includes('This exact file was applied before') && (await text(page, '.rows-table')).includes('Already recorded') && (await text(page, '#apply')) === 'Apply (nothing new)');
  await page.click('.apply-bar a:has-text("Keep as a draft")');
  await page.waitForSelector('.page-imports h1');
  check('B8 a kept draft is listed as not applied (B4)', (await text(page, '#drafts-title')).includes('Drafts not applied'));
  await page.click('[data-discard]');
  await dlg(page).locator('[type=submit]').click();
  await page.waitForSelector('dialog[open]', { state: 'detached' });
  await page.waitForSelector('.page-imports h1');
  await page.waitForTimeout(300);
  check('B8 a discarded draft leaves the drafts list and is noted (B4)', !(await page.$('#drafts-title')) && (await text(page, '.more-list summary')).includes('discarded draft'));
  const f03 = csv(`${TAG}-03-invalid.csv`, `Customer,Invoice number,Invoice date,Invoice amount,Due date\n${TAG} Imported A fictional,${TAG}-BAD-001,2026-02-31,100.00,2026-10-10\n${TAG} Imported A fictional,${TAG}-BAD-002,2026-10-05,1O0.00,2026-10-10\n${TAG} Imported A fictional,${TAG}-VALID-PREVIEW,2026-10-05,250.00,2026-10-10\n`);
  await upload(page, 'invoices', `${TAG} Invalid preview`, f03);
  const bad = await text(page, '.rows-table');
  check('B8 invalid rows are rejected with reasons; the valid row shows its amount', bad.includes('"2026-02-31" is not a valid date') && bad.includes('Enter an amount using digits') && bad.includes('AUD 250.00'));
  await page.click('#discard');
  await dlg(page).locator('[type=submit]').click();
  await page.waitForSelector('.page-imports h1');
  // a person's correction, then the original file again: a conflict to decide
  const importedA = await customerId(page, `${TAG} Imported A fictional`), importedB = await customerId(page, `${TAG} Imported B fictional`);
  await go(page, `#/customers/${importedB}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  await page.click('tr:has-text("DEMO-951") [data-act=correct-invoices]');
  await dlg(page).locator('[name=total]').fill('210.00');
  await dlg(page).locator('[name=reason]').fill('Fictional correction test');
  await save(page, () => dlg(page).locator('[type=submit]').click());
  check('B8 a correction keeps a version and says who', (await text(page, 'tr:has-text("DEMO-951")')).includes('Corrected by staff') && (await text(page, 'tr:has-text("DEMO-951")')).includes('Version 2'));
  await upload(page, 'invoices', `${TAG} Invoice test`, f01);
  check('B8 a person-corrected value in the file is a conflict to decide', (await text(page, '.rows-table')).includes('a person corrected this record'));
  await page.check('#params input[value=keep]');
  await page.click('#params [type=submit]');
  await page.waitForSelector('#apply:not([aria-disabled=true])');
  await applyDraft(page);
  await go(page, `#/customers/${importedB}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  check('B8 "keep what\'s recorded" kept the correction', (await text(page, 'tr:has-text("DEMO-951")')).includes('AUD 210.00'));
  const f02 = csv(`${TAG}-02-payments.csv`, `Customer,Payment date,Amount received,Payment reference,Invoice number\n${TAG} Imported A fictional,2026-10-12,600.00,${TAG}-PAY-001,DEMO-951\n${TAG} Imported B fictional,2026-10-12,50.00,${TAG}-PAY-002,\n`);
  await upload(page, 'payments', `${TAG} Payment test`, f02);
  check('B8 the payment preview shows dates, amounts and the allocation', (await text(page, '.rows-table')).includes('Allocates AUD 600.00 to DEMO-951') && (await text(page, '.rows-table')).includes('AUD 50.00'));
  await applyDraft(page);
  const b02 = await page.evaluate(() => location.hash.split('/')[2]);

  // B9 allocation only within a customer, in the page and on the server.
  await go(page, `#/customers/${importedB}/payments`);
  await page.waitForSelector(`tr:has-text("${TAG}-PAY-002")`);
  await page.click(`tr:has-text("${TAG}-PAY-002") [data-act=allocate]`);
  const options = await dlg(page).locator('[name=invoiceId] option').evaluateAll(o => o.map(x => x.value).filter(Boolean));
  const recs = (await api(page, 'staff', '/api/records')).body;
  const invA = recs.invoices.find(i => i.customerId === importedA && i.reference === 'DEMO-951').id, invB = recs.invoices.find(i => i.customerId === importedB && i.reference === 'DEMO-951').id;
  check('B9 a payment can be allocated only to its own customer\'s invoices', options.length === 1 && options[0] === invB && !options.includes(invA));
  await page.keyboard.press('Escape');
  expected.push([400, '/api/records/allocations'], [409, '/api/records/allocations'], [422, '/api/records/allocations']);
  const pay2 = recs.payments.find(p => p.reference === `${TAG}-PAY-002`).id;
  const cross = await api(page, 'staff', '/api/records/allocations', { paymentId: pay2, allocations: [{ invoiceId: invA, amount: '50.00' }] });
  check('B9 the server refuses an allocation to another customer\'s invoice', cross.status >= 400, cross.status + ' ' + (cross.body.message || ''));

  // B10 from "at most" to exact, and back when a late entry changes the evidence; the decided case is flagged.
  await go(page, `#/customers/${importedA}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  check('B10 an allocated invoice is "at most", with why', (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('At most') && (await text(page, 'tr:has-text("DEMO-951")')).includes('AUD 400.00'));
  await go(page, `#/customers/${importedB}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  check('B10 an invoice with nothing allocated is "worked out" (not recorded), not "at most" (U6)', (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('Worked out') && !(await text(page, 'tr:has-text("DEMO-951") .amount')).includes('At most'));
  await asRole(page, 'owner');
  await go(page, `#/customers/${importedA}/balance`);
  await page.waitForSelector('.tab-body');
  await page.click('[data-act=opening]');
  await dlg(page).locator('[name=asOf]').fill('2026-09-30');
  await dlg(page).locator('[name=amount]').fill('0.00');
  await dlg(page).locator('[name=credits]').selectOption('none');
  await dlg(page).locator('[name=sourceLabel]').fill('Fictional test dataset starts from zero');
  await save(page, () => dlg(page).locator('[type=submit]').click());
  check('B10 the opening balance shows who entered it (B2)', (await text(page, '.kv')).includes('Entered by the owner'));
  await page.click(`.tab-body [data-act=coverage]`);
  await dlg(page).locator('[name=type][value=payments]').check();
  await dlg(page).locator('[name=from]').fill('2026-10-01');
  await dlg(page).locator('[name=sourceLabel]').fill('Fictional test pack contains the full payment history');
  await dlg(page).locator('[name=confirm]').check();
  await save(page, () => dlg(page).locator('[type=submit]').click());
  await go(page, `#/customers/${importedA}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  check('B10 complete records make it exact, with the date', (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('AUD 400.00') && (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('Exact') && (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('as of Fri 16 Oct'));
  await asRole(page, 'staff');
  const caseA = await request(page, `Test ${TAG}. Could we pay invoice DEMO-951 on 2026-11-14 instead?`);
  await page.click(`#answer label:has-text("${TAG} Imported A fictional")`);
  await page.click('#answer [type=submit]');
  await settled(page, ['awaiting_owner']);
  await asRole(page, 'owner');
  await openCase(page, caseA);
  await page.waitForSelector('#decide');
  check('B10 the owner sees the exact amount in the case', (await text(page, '.facts')).includes('AUD 400.00') && (await text(page, '.facts .amount')).includes('Exact'));
  check('B10 the brief names each record type\'s completeness (U8)', (await text(page, '.case-main')).includes('Payment records are confirmed complete to Fri 16 Oct 2026, but invoice records are not'));
  await page.check('#decide input[name=outcome][value=approve]');
  await page.fill('#reason', 'Fictional test only');
  await page.click('#decide [type=submit]');
  await settled(page, ['completed']);
  await asRole(page, 'staff');
  await go(page, `#/customers/${importedA}/payments`);
  await page.waitForSelector('.tab-body');
  await page.click('.page-actions [data-act=add-payment]');
  await dlg(page).locator('[name=receivedDate]').fill('2026-10-14');
  await dlg(page).locator('[name=amount]').fill('10.00');
  await dlg(page).locator('[name=reference]').fill(`${TAG}-LATE-ENTRY`);
  await save(page, () => dlg(page).locator('[type=submit]').click());
  await go(page, `#/customers/${importedA}/invoices`);
  await page.waitForSelector('tr:has-text("DEMO-951")');
  await page.click('tr:has-text("DEMO-951") details.why summary');
  const why = await text(page, 'tr:has-text("DEMO-951") details.why');
  check('B10 a late entry withdraws exactness', (await text(page, 'tr:has-text("DEMO-951") .amount')).includes('At most'));
  check('B10 "why not exact" names the late entry and that it was added (U7)', why.includes(`${TAG}-LATE-ENTRY was added inside that period`) && why.includes('from Thu 1 Oct 2026'), why.slice(0, 200));
  check('B10 the customer page says the statement no longer holds and names the entry', (await text(page, '.att-summary')).includes(`Payment records are no longer confirmed complete: ${TAG}-LATE-ENTRY was added`));
  await page.click('.att-summary a'); await page.waitForSelector('.attention li');
  check('B10 and its Needs attention tab explains why', (await text(page, '.attention')).includes(`${TAG}-LATE-ENTRY was added inside its period after it was confirmed`));
  await openCase(page, caseA);
  const flag = await text(page, '[data-testid=flag]');
  check('B10 the decided case is flagged, naming the record and who (B5)', flag.includes(`Payment ${TAG}-LATE-ENTRY`) && flag.includes('recorded by staff') && flag.includes('was exactly AUD 400.00') && flag.includes('The decision stands'), flag.slice(0, 200));
  await page.click('#tab-activity');
  check('B10 the activity lists the change after the decision (B5)', (await text(page, '#panel-activity')).includes('Records changed after the decision'));
  await page.screenshot({ path: path.join(OUT, 'after-desktop-flagged-case.png'), fullPage: true });

  // B11 reverts: safe, blocked and review-required, each explained before anything is submitted (B3).
  const f04 = csv(`${TAG}-04-revert.csv`, `Customer,Invoice number,Invoice date,Invoice amount,Due date\n${TAG} Revert Demo fictional,DEMO-961,2026-10-05,75.00,2026-10-10\n`);
  await upload(page, 'invoices', `${TAG} Revert test`, f04);
  await resolveNew(page);
  await applyDraft(page);
  await page.waitForSelector('#impact .points');
  const safe = await text(page, '#impact');
  check('B11 safe revert: says what it would do before asking', safe.includes(`Invoice DEMO-961 (${TAG} Revert Demo fictional) is marked reverted`) && safe.includes(`Customer ${TAG} Revert Demo fictional is marked reverted`));
  await page.click('#revert');
  await dlg(page).locator('[name=reason]').fill('Fictional reversal test');
  await dlg(page).locator('[type=submit]').click();
  await page.waitForSelector('.status-line .chip.wait');
  check('B11 safe revert done', (await text(page, '.status-line')).includes('Reverted'));
  await go(page, '#/imports/' + b01);
  await page.waitForSelector('#impact .callout');
  const blocked = await text(page, '#impact');
  check('B11 blocked revert: explained before anything is submitted, no revert button (B3)', blocked.includes("can't be reverted yet") && blocked.includes('has payments allocated to it') && !(await page.$('#revert')) && !blocked.includes('from elsewhere'), blocked.slice(0, 200));
  await go(page, '#/imports/' + b02);
  await page.waitForSelector('#impact .callout.warn');
  const review = await text(page, '#impact');
  check('B11 review-required revert: lists the decided case before asking', review.includes('decided case keeps its decision') && (await page.$$('#impact .callout a')).length >= 1);
  await page.click('#revert');
  check('B11 the confirmation says it was checked', (await text(page, 'dialog[open] [type=submit]')) === 'Revert, having checked the above');
  await dlg(page).locator('[name=reason]').fill('Fictional dependent revert test');
  await dlg(page).locator('[type=submit]').click();
  await page.waitForSelector('.status-line .chip.wait', { timeout: 15000 });
  check('B11 review-required revert done after review', (await text(page, '.status-line')).includes('Reverted'));
  await openCase(page, caseA);
  check('B11 the decided case is flagged again, naming the revert', (await text(page, '.case-head')).includes(`An import was reverted (${path.basename(f02)}`));

  // A customer with several open issues for the phone checks: two records dated before its opening balance, not yet answered.
  await addInvoice(page, importedA, { reference: 'DEMO-952', issueDate: '2026-09-20', total: '300.00' });
  await go(page, `#/customers/${importedA}/payments`); await page.waitForSelector('.tab-body');
  await page.click('.page-actions [data-act=add-payment]');
  await dlg(page).locator('[name=receivedDate]').fill('2026-09-25'); await dlg(page).locator('[name=amount]').fill('25.00');
  await dlg(page).locator('[name=reference]').fill(`${TAG}-EARLY`);
  await save(page, () => dlg(page).locator('[type=submit]').click());
  const issues = (await api(page, 'staff', '/api/records')).body;
  check('B11 the multi-issue customer has its two open questions', issues.positions.customers[importedA].opening.records.filter(r => r.status === 'unresolved').length === 2);
  // A status beside an invoice or payment stays inside its own cell (it once ran into the Issued column on wide screens).
  for (const [tab, row] of [['invoices', 'DEMO-952'], ['payments', `${TAG}-EARLY`]]) {
    await go(page, `#/customers/${importedA}/${tab}`); await page.waitForSelector(`tr:has-text("${row}") th .chip`);
    const cell = await page.evaluate(r => { const th = [...document.querySelectorAll('.tab-body tbody th')].find(t => t.textContent.includes(r)); const c = th.querySelector('.chip:last-child').getBoundingClientRect(), b = th.getBoundingClientRect();
      return { chip: [Math.round(c.left), Math.round(c.right)], cell: [Math.round(b.left), Math.round(b.right)] }; }, row);
    check(`B11 the "Opening balance: not answered" status on ${row} stays inside its cell`, cell.chip[0] >= cell.cell[0] && cell.chip[1] <= cell.cell[1], JSON.stringify(cell));
  }

  // B12 leaving a page while it loads never draws into the next one.
  await page.route('**/api/records', async r => { await new Promise(x => setTimeout(x, 1500)); await r.continue(); });
  await go(page, '#/customers'); await page.waitForTimeout(150); await go(page, '#/cases');
  await page.waitForTimeout(2500);
  check('B12 a slow Customers load does not draw over Requests', await page.isVisible('.queue') && !(await page.$('#cust-rows')));
  await page.unroute('**/api/records');
  await page.click('.queue-head a[href="#/cases/new"]');
  await page.waitForSelector('.queue-head a[href="#/cases/new"][aria-current=page]');   // drawn for #/cases/new, not the list's own form
  check('B12 staff: the list\'s "New request" opens the form', (await text(page, '.queue-head a[href="#/cases/new"]')) === 'New request'
    && await page.isVisible('#composer #message'), await page.evaluate(() => location.hash));
  await page.route('**/api/requests/req_*', async r => { await new Promise(x => setTimeout(x, 1500)); await r.continue(); });
  await go(page, '#/case/' + caseA); await page.waitForTimeout(150); await go(page, '#/imports');
  await page.waitForTimeout(2500);
  check('B12 a slow case load does not draw over Imports', await page.isVisible('.page-imports h1') && !(await page.$('.case')));
  await page.unroute('**/api/requests/req_*');

  // B13 keyboard: skip link, dialog focus and Escape, case tabs with arrow keys.
  await go(page, '#/customers');
  await page.waitForSelector('#cust-rows');
  await page.evaluate(() => document.activeElement?.blur());
  await page.keyboard.press('Tab');
  check('B13 the first Tab reaches "Skip to content"', (await page.evaluate(() => document.activeElement?.textContent)) === 'Skip to content');
  await page.keyboard.press('Enter');
  check('B13 skipping moves focus to the page and keeps the route', (await page.evaluate(() => document.activeElement?.id)) === 'main' && (await page.evaluate(() => location.hash)) === '#/customers');
  await page.focus('.page-actions [data-act=add-customer]');
  await page.keyboard.press('Enter');
  await page.waitForSelector('dialog[open]');
  check('B13 a dialog opens with focus inside it', await page.evaluate(() => !!document.activeElement?.closest('dialog[open]')));
  await page.keyboard.press('Escape');
  await page.waitForSelector('dialog[open]', { state: 'detached' });
  check('B13 Escape closes it and focus returns to the button', await page.evaluate(() => document.activeElement?.dataset.act === 'add-customer'));
  await openCase(page, caseA);
  await page.focus('#tab-evidence');
  await page.keyboard.press('ArrowRight');
  check('B13 case tabs move with the arrow keys', (await page.getAttribute('#tab-activity', 'aria-selected')) === 'true' && await page.isVisible('#panel-activity'));
  await page.screenshot({ path: path.join(OUT, 'after-desktop-staff-case.png'), fullPage: true });
  for (const [hash, name] of [['#/requests', 'requests'], ['#/cases', 'cases'], ['#/customers', 'customers'], [`#/customers/${importedA}/invoices`, 'customer-invoices'], [`#/customers/${importedA}/balance`, 'customer-balance'], ['#/imports', 'imports'], ['#/knowledge', 'knowledge'], ['#/setup', 'setup']]) {
    await go(page, hash); await page.waitForTimeout(700);
    await page.screenshot({ path: path.join(OUT, `after-desktop-${name}.png`), fullPage: true });
  }
  await page.context().close();
  return { importedA, caseA, manualB };
}

// ---------------------------------------------------------------- C. phones: real layout boxes against the configured width

async function phones(browser, ids) {
  for (const width of [375, 390]) {
    const page = await newPage(browser, 'C' + width, { viewport: { width, height: 844 }, isMobile: true, hasTouch: true });
    await page.goto(BASE);
    await signIn(page, codes.staff);
    const measure = () => page.evaluate(w => ({ doc: document.documentElement.scrollWidth,
      out: [...document.querySelectorAll('body *')].filter(el => el.getClientRects().length && !el.closest('.tabs, .subnav, .skip, dialog:not([open])')).filter(el => { const r = el.getBoundingClientRect(); return r.width && (r.right > w + 1 || r.left < -1); }).length }), width);
    const fits = async label => { await page.waitForTimeout(500); const m = await measure(); check(`C ${width}px ${label}: fits the width`, m.doc <= width && m.out === 0, JSON.stringify(m)); };
    check(`C ${width}px the bottom navigation is shown`, await page.isVisible('.tabbar') && !(await page.isVisible('.mainnav')));
    await fits('requests');
    await page.tap('.tabbar a[data-area=customers]');
    await page.waitForSelector('#cust-rows');
    await fits('customers');
    // A routine customer: the records and the routine actions come first.
    await go(page, `#/customers/${ids.manualB}/invoices`); await page.waitForSelector('.tab-body tr');
    const routine = await page.evaluate(() => ({ row: Math.round(document.querySelector('.tab-body tbody th').getBoundingClientRect().bottom), add: Math.round(document.querySelector('.page-actions [data-act=add-invoice]').getBoundingClientRect().bottom),
      bar: Math.round(document.querySelector('.tabbar').getBoundingClientRect().top), summary: !!document.querySelector('.att-summary') }));
    check(`C ${width}px routine customer: the first invoice's number and "Add invoice" on the first screen, no attention box`, routine.row < routine.bar && routine.add < routine.bar && !routine.summary, JSON.stringify(routine));
    await fits('routine customer');
    await page.screenshot({ path: path.join(OUT, `after-${width}-customer-routine.png`) });
    // A customer with several open issues: a short summary that names each, the records still on the first screen.
    await go(page, `#/customers/${ids.importedA}/invoices`); await page.waitForSelector('.att-summary');
    const busy = await page.evaluate(w => { const s = document.querySelector('.att-summary'); const items = [...s.querySelectorAll('li')];
      return { count: s.querySelector('h2').textContent, items: items.map(li => li.textContent), clipped: items.filter(li => li.scrollWidth > li.clientWidth + 1 || li.getBoundingClientRect().right > w).length,
        row: Math.round(document.querySelector('.tab-body tbody th').getBoundingClientRect().bottom), bar: Math.round(document.querySelector('.tabbar').getBoundingClientRect().top),
        add: Math.round(document.querySelector('.page-actions [data-act=add-invoice]').getBoundingClientRect().bottom) }; }, width);
    check(`C ${width}px multi-issue customer: the summary names each issue and its records`, /^[3-9] items need attention$/.test(busy.count) && busy.clipped === 0
      && busy.items.some(x => x.startsWith('Payment records are no longer confirmed complete: ') && x.includes(`${TAG}-LATE-ENTRY was added`))
      && busy.items.some(x => x.startsWith('2 questions about the opening balance: ') && x.includes('DEMO-952') && x.includes(`${TAG}-EARLY`)), JSON.stringify(busy.items));
    check(`C ${width}px multi-issue customer: the first invoice's number and "Add invoice" are still on the first screen`, busy.row < busy.bar && busy.add < busy.bar, JSON.stringify(busy));
    await page.screenshot({ path: path.join(OUT, `after-${width}-customer-invoices.png`) });
    await page.tap('.att-summary a');
    await page.waitForSelector('.attention li');
    const detail = await text(page, '.attention');
    check(`C ${width}px "Review all" opens every explanation, with the questions to answer`, (await page.$$('.attention li')).length === busy.count[0] * 1 && detail.includes('no longer holds') && detail.includes('already part of the opening balance') && (await page.$$('.attention [data-act=inclusion]')).length >= 4);
    await fits('attention tab');
    await page.screenshot({ path: path.join(OUT, `after-${width}-customer-attention.png`) });   // the first screen: a full-page capture under phone emulation misplaces the fixed bar
    await page.tap(`.subnav a[href^="#/customers/${ids.importedA}/invoices"]`);
    await page.waitForSelector('tr:has-text("DEMO-951")');
    const owed = await page.evaluate(w => { const el = [...document.querySelectorAll('tr')].find(t => t.textContent.includes('DEMO-951'))?.querySelector('.amount'); const r = el.getBoundingClientRect(); return { right: Math.round(r.right), left: Math.round(r.left), w }; }, width);
    check(`C ${width}px the amount still owed is fully on screen (U9)`, owed.right <= width && owed.left >= 0, JSON.stringify(owed));
    await fits('customer invoices');
    await page.tap('.page-actions [data-act=add-payment]');
    await page.waitForSelector('dialog[open]');
    const box = await page.evaluate(() => { const r = document.querySelector('dialog[open]').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; });
    check(`C ${width}px a dialog fits the screen`, box[0] >= 0 && box[1] <= width, JSON.stringify(box));
    await page.tap('dialog[open] [data-close]');
    await page.tap('.tabbar a[data-area=requests]');
    await page.waitForSelector('.case-row');
    await page.tap(`.case-row[href="#/case/${ids.caseA}"]`);
    await page.waitForSelector('.case');
    check(`C ${width}px the case is alone on screen with the next step before the facts`, !(await page.isVisible('.queue')) && await page.evaluate(() => { const a = document.querySelector('.action'), f = document.querySelector('.facts-card'); return !a || !f || a.getBoundingClientRect().top < f.getBoundingClientRect().top; }));
    await fits('case');
    await page.screenshot({ path: path.join(OUT, `after-${width}-case.png`), fullPage: true });
    await page.tap('.tabbar a[data-area=customers]');
    await page.waitForSelector('#cust-rows');
    await page.screenshot({ path: path.join(OUT, `after-${width}-customers.png`), fullPage: true });
    // A customer opened from further down the list starts at its top: the summary and the actions, not the middle of its records.
    const before = await page.evaluate(() => { scrollTo(0, document.documentElement.scrollHeight); return Math.round(scrollY); });
    await page.evaluate(id => document.querySelector(`#cust-rows a[href="#/customers/${id}"]`).click(), ids.importedA);
    await page.waitForSelector('.att-summary');
    const opened = await page.evaluate(() => ({ y: Math.round(scrollY), summary: Math.round(document.querySelector('.att-summary').getBoundingClientRect().top) }));
    check(`C ${width}px a customer opened from a scrolled list starts at its top`, before > 0 && opened.y === 0 && opened.summary > 0 && opened.summary < 844, JSON.stringify({ before, ...opened }));
    await page.tap('.tabbar a[data-area=imports]');
    await page.waitForSelector('.page-imports h1');
    await fits('imports');
    await page.screenshot({ path: path.join(OUT, `after-${width}-imports.png`), fullPage: true });
    await page.tap('.tabbar a[data-area=requests]');
    await page.waitForSelector('.queue');
    await page.screenshot({ path: path.join(OUT, `after-${width}-requests.png`) });
    await page.tap('#signout');
    await page.waitForSelector('#signin');
    check(`C ${width}px sign-out works from the phone header`, JSON.stringify(await held(page)) === '[]');
    await page.screenshot({ path: path.join(OUT, `after-${width}-signin.png`) });
    await page.context().close();
  }
}

// ---------------------------------------------------------------- E. sign-out: local content, other tabs, late responses, uncertainty

async function signOuts(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const a = watch(await ctx.newPage(), 'E');
  const localDraft = p => p.evaluate(() => localStorage.getItem('nucleon.draft'));
  const sessionKeys = p => p.evaluate(() => Object.keys(sessionStorage).filter(k => k.startsWith('nucleon.')));
  await a.goto(BASE);
  await signIn(a, codes.staff);
  const secret = `Fictional ${TAG} draft: could Harbour pay DEMO-101 on 2026-11-30 instead?`;
  await go(a, '#/cases/new'); await a.waitForSelector('#composer');
  await a.fill('#message', secret);
  await go(a, '#/customers'); await a.waitForSelector('#cust-q');
  await a.fill('#cust-q', 'Harbour');   // a search kept for this tab
  await go(a, '#/cases/new'); await a.waitForSelector('#composer');
  check('E1 a typed request survives navigation while signed in', (await a.inputValue('#message')) === secret);
  await a.reload(); await a.waitForSelector('#composer');
  check('E1 and a reload while signed in', (await a.inputValue('#message')) === secret);
  const b = watch(await ctx.newPage(), 'E');
  await b.goto(BASE + '/#/cases/new'); await b.waitForSelector('#composer');
  check('E2 another tab of the same browser shows the same draft', (await b.inputValue('#message')) === secret);
  await a.click('#signout'); await a.waitForSelector('#signin .callout');
  check('E1 sign-out removes the stored request draft', (await localDraft(a)) === null);
  check('E1 sign-out removes this tab\'s kept filters and searches', (await sessionKeys(a)).length === 0, JSON.stringify(await sessionKeys(a)));
  await b.waitForSelector('[data-testid=signed-out-elsewhere], #signin', { timeout: 5000 }).catch(() => {});
  check('E2 the other tab leaves the signed-in pages at once', !(await b.$('#composer')) && !(await b.$('header.top')) && (await text(b, 'main')).includes('another tab'), await text(b, 'main'));
  await b.reload(); await b.waitForSelector('#signin');
  check('E2 a reload of the other tab stays signed out, with no draft', !(await b.$('header.top')) && (await localDraft(b)) === null);
  await signIn(a, codes.staff);
  await go(a, '#/cases/new'); await a.waitForSelector('#composer');
  check('E1 after signing in again, New request is empty', (await a.inputValue('#message')) === '');
  await go(a, '#/customers'); await a.waitForSelector('#cust-q');
  check('E1 and the earlier search is gone', (await a.inputValue('#cust-q')) === '');
  // E3: a response that arrives after sign-out draws nothing.
  await a.route('**/api/records', async r => { await new Promise(x => setTimeout(x, 2000)); await r.continue(); });
  await go(a, '#/customers'); await a.waitForTimeout(200);
  await a.click('#signout'); await a.waitForSelector('#signin');
  await a.waitForTimeout(2600);
  check('E3 a late response after sign-out draws no records or error over the sign-in page', await a.isVisible('#signin') && !(await a.$('#cust-rows')) && !(await a.$('header.top')) && !(await text(a, 'main')).includes("didn't load"));
  await a.unroute('**/api/records');
  // E4: the logout request never reaches the server.
  await signIn(a, codes.staff);
  await go(a, '#/cases/new'); await a.waitForSelector('#composer'); await a.fill('#message', secret);
  await a.route('**/api/demo/logout', r => r.abort('internetdisconnected'));
  await a.click('#signout');
  await a.waitForSelector('[data-testid=signout-unconfirmed]', { timeout: 15000 });
  check('E4 an unreached sign-out is not reported as done', (await text(a, 'h1')) === 'Sign-out not confirmed' && !(await a.$('header.top')) && !(await text(a, 'main')).includes('Signed out of'), await text(a, 'main'));
  check('E4 local drafts are removed anyway', (await localDraft(a)) === null && (await sessionKeys(a)).length === 0);
  check('E4 the server still holds the session, as the page says, without guessing why', JSON.stringify(await held(a)) === '["staff"]'
    && (await text(a, 'main')).includes('The app did not receive confirmation') && (await text(a, 'main')).includes('still has a session') && !(await text(a, 'main')).includes('could not reach'), await text(a, 'main'));
  await a.reload(); await a.waitForSelector('[data-testid=signout-unconfirmed]', { timeout: 15000 });
  check('E4 a reload keeps trying to sign out instead of showing the pages', !(await a.$('header.top')));
  await a.unroute('**/api/demo/logout');
  await a.click('[data-testid=signout-retry]'); await a.waitForSelector('#signin .callout');
  check('E4 "Try signing out again" confirms it with the server', JSON.stringify(await held(a)) === '[]' && (await text(a, '#signin .callout')).startsWith('Signed out'), await text(a, '#signin .callout'));
  // E5: the server signs out but the response is lost; the follow-up check with the server confirms it.
  await signIn(a, codes.owner);
  await a.route('**/api/demo/logout', async r => { await r.fetch(); await r.abort('connectionreset'); });
  await a.click('#signout'); await a.waitForSelector('#signin .callout', { timeout: 15000 });
  await a.unroute('**/api/demo/logout');
  check('E5 a lost response is confirmed from what the server holds', JSON.stringify(await held(a)) === '[]' && (await text(a, '#signin .callout')).includes('The server shows no session for this browser'), await text(a, '#signin .callout'));
  // E6: the response is lost and the check fails too: not confirmed, then confirmed on retry.
  await signIn(a, codes.staff);
  await a.route('**/api/demo/logout', async r => { await r.fetch(); await r.abort('connectionreset'); });
  await a.route('**/api/session', r => r.abort('internetdisconnected'));
  await a.click('#signout');
  await a.waitForSelector('[data-testid=signout-unconfirmed]', { timeout: 15000 });
  // The request did reach the server here: the page must not claim it could not.
  check('E6 with no way to confirm, the page says only what is known', (await text(a, 'h1')) === 'Sign-out not confirmed' && !(await a.$('header.top'))
    && (await text(a, 'main')).includes('The app did not receive confirmation') && !(await text(a, 'main')).includes('could not reach'), await text(a, 'main'));
  await a.unroute('**/api/demo/logout'); await a.unroute('**/api/session');
  await a.click('[data-testid=signout-retry]'); await a.waitForSelector('#signin .callout');
  check('E6 retry confirms it', JSON.stringify(await held(a)) === '[]');
  await ctx.close();
}

// ---------------------------------------------------------------- D. a failed preparation and its explicit retry

async function failure(browser) {
  const page = await newPage(browser, 'D');
  await page.goto(FAULT_BASE);
  await signIn(page, faultCodes.staff, FAULT_BASE);
  await go(page, '#/cases/new');
  await page.waitForSelector('#composer');
  await page.fill('#message', `[fallback-fault] Test ${TAG}. Could we pay invoice DEMO-101 on 2026-10-30 instead?`);
  await page.click('#composer [type=submit]');
  await page.waitForFunction(() => location.hash.startsWith('#/case/'));
  await settled(page);
  check('D a failed preparation is shown as a technical fault, with the message kept', (await status(page)) === 'preparation_failed' && await page.isVisible('[data-testid=preparation-failed]') && (await text(page, '[data-testid=message]')).includes('DEMO-101'));
  await page.screenshot({ path: path.join(OUT, 'after-desktop-preparation-failed.png'), fullPage: true });
  await page.waitForTimeout(3000);
  check('D it does not retry by itself', (await status(page)) === 'preparation_failed');
  await page.click('#prepare-again');
  await settled(page, ['awaiting_owner', 'needs_information']);
  check('D "Prepare again" prepares it (here without AI)', (await status(page)) === 'awaiting_owner' && (await text(page, '[data-testid=provenance]')).startsWith('Prepared without AI'));
  const caseId = (await page.evaluate(() => location.hash)).split('/')[2];
  await page.click('[data-role=owner]');
  await signIn(page, faultCodes.owner, FAULT_BASE);
  await go(page, '#/case/' + caseId);
  await page.waitForSelector('[data-testid=provenance]');
  check('D the owner is told on the case that it was prepared without AI, and is offered no suggestion', (await text(page, '[data-testid=provenance]')).startsWith('Prepared without AI')
    && !(await page.$('[data-act=suggest-on]')), await text(page, '[data-testid=provenance]'));
  await page.context().close();
}

(async () => {
  const browser = await chromium.launch();
  console.log(`UI CHECK | ${BASE} and ${FAULT_BASE} | tag ${TAG} | Chromium ${browser.version()}`);
  try {
    await sessions(browser);
    await signOuts(browser);
    const ids = await main(browser);
    await phones(browser, ids);
    await failure(browser);
  } catch (e) {
    check('UI check completed', false, e.stack.split('\n').slice(0, 3).join(' '));
  }
  check('no JavaScript or console errors', errors.length === 0, errors.join(' | '));
  const unexpected = failed.filter(([code, p]) => !expected.some(([c, pattern]) => c === code && p.includes(pattern)));
  check('only deliberate 4xx responses, and no 5xx', unexpected.length === 0, unexpected.map(f => f.join(' ')).join(' | ') || failed.length + ' deliberate');
  await browser.close();
  console.log(`RESULT ui: ${results.filter(r => r[1]).length}/${results.length} checks passed (tag ${TAG})`);
  process.exit(results.every(r => r[1]) ? 0 : 1);
})();
