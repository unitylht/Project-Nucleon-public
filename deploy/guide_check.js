// Walk through the team testing guide, revision 3 (docs/qa/test-pack-v3), as a tester would, and check its stated outcomes.
//   NODE_PATH=<dir with node_modules/playwright> node deploy/guide_check.js <base> <service-log> <out-dir> [TAG]
// Needs a scratch server in live mode (real model) with the fictional sample, so the business date is Fri 16 Oct 2026.
// Uses the pack's template CSV files with a fresh tag. Never run it on the shared instance: it creates and reverts records.
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const [BASE, LOG, OUT] = process.argv.slice(2);
require('./scratch_only')('guide check', BASE, LOG);
const TAG = process.argv[5] || 'GV' + Date.now().toString(36).slice(-5).toUpperCase();
const t = fs.readFileSync(LOG, 'utf8');
const codes = Object.fromEntries([...t.slice(t.lastIndexOf(' URL: http')).matchAll(/^(STAFF|OWNER|OPERATOR) access code: (\S+)$/gm)].map(m => [m[1].toLowerCase(), m[2]]));
const TEMPLATES = path.join(__dirname, '../docs/qa/test-pack-v3/Nucleon-Team-Test-Pack-v3/templates');
fs.mkdirSync(OUT, { recursive: true });
const csv = name => { const f = path.join(OUT, `${TAG}-${name}`); fs.writeFileSync(f, fs.readFileSync(path.join(TEMPLATES, name), 'utf8').replaceAll('TESTTAG', TAG)); return f; };
const results = [];
const check = (name, ok, detail = '') => { results.push(!!ok); console.log(`${ok ? 'PASS' : 'FAIL'} ${name.padEnd(74)} ${String(detail).replace(/\s+/g, ' ').slice(0, 170)}`); };
const errors = [];
const text = (page, sel) => page.textContent(sel).then(x => (x || '').replace(/\s+/g, ' ').trim()).catch(() => '');
const go = (page, hash) => page.evaluate(h => { location.hash = h; }, hash);
const dlg = page => page.locator('dialog[open]');
const held = page => page.evaluate(async () => (await (await fetch('/api/session')).json()).signedIn);
const status = page => page.getAttribute('[data-testid=status]', 'data-status');
const settled = (page, want, timeout = 400000) => page.waitForFunction(w => { const s = document.querySelector('[data-testid=status]')?.dataset.status; return s && (w ? w.includes(s) : !['received', 'analysing'].includes(s)); }, want || null, { timeout });
async function save(page, click) {
  const reload = page.waitForResponse(r => new URL(r.url()).pathname === '/api/records' && r.request().method() === 'GET', { timeout: 30000 });
  await click(); await reload; await page.waitForTimeout(300);
}
async function signIn(page, code) { await page.waitForSelector('#signin'); await page.fill('#code', code); await page.click('#signin [type=submit]'); await page.waitForSelector('header.top'); }
async function role(page, r) { await page.click(`[data-role=${r}]`); await page.waitForFunction(x => document.querySelector(`[data-role=${x}]`)?.getAttribute('aria-pressed') === 'true', r); }
async function customer(page, name) {
  await go(page, '#/customers'); await page.waitForSelector('#cust-rows');
  await page.fill('#cust-q', name); await page.waitForTimeout(200);
  await page.click(`#cust-rows a:text-is("${name}")`); await page.waitForSelector('.tab-body');
  return page.evaluate(() => location.hash.split('/')[2].split('?')[0]);
}
async function upload(page, shape, label, file) {
  await go(page, '#/imports'); await page.waitForSelector('.page-imports h1');
  await page.click('.page-actions a:has-text("Import a CSV file")'); await page.waitForSelector('#upload');
  await page.check(`#upload [name=shape][value=${shape}]`); await page.fill('#upload [name=sourceLabel]', label);
  await page.setInputFiles('#upload [name=file]', file); await page.click('#upload button:has-text("Upload and check")'); await page.waitForSelector('#params');
}
// The guide (revision 3) predates the desk: its Requests steps are the list view at #/cases and its form at #/cases/new.
async function form(page) {
  await go(page, '#/cases'); await page.waitForSelector('.queue');
  await page.click('.queue-head a[href="#/cases/new"]'); await page.waitForSelector('#composer');
}
async function send(page, message) {
  await form(page);
  await page.fill('#message', message); await page.click('#composer button:has-text("Send to the agent")');
  await page.waitForFunction(() => location.hash.startsWith('#/case/'));
  const id = await page.evaluate(() => location.hash.slice(7).split('?')[0]);
  await settled(page);
  return id;
}

(async () => {
  const browser = await chromium.launch();
  console.log(`GUIDE CHECK revision 3 | ${BASE} | tag ${TAG} | Chromium ${browser.version()}`);
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await ctx.newPage();
  page.on('pageerror', e => errors.push(e.message));
  try {
    // Before you start
    await page.goto(BASE);
    // T1
    await signIn(page, codes.staff);
    const areas = await page.$$eval('nav.mainnav a', as => as.map(a => a.innerText.trim()).join(' '));
    check('Before: the header shows the five areas', areas === 'Requests Customers Imports Knowledge Setup', areas);
    check('Before: the context line names the business date', (await text(page, '.context')).startsWith('Practice workspace with fictional data. Business date Fri 16 Oct 2026'));
    await page.click('[data-role=owner]'); await page.waitForSelector('#signin');
    check('T1 the page asks "Sign in as owner"', (await text(page, '#signin h1')) === 'Sign in as owner');
    await page.fill('#code', codes.staff); await page.click('#signin button:has-text("Sign in as owner")');
    await page.waitForFunction(() => document.querySelector('[data-error-for=accessCode]')?.textContent);
    check('T1 step 2 message as written', (await text(page, '[data-error-for=accessCode]')) === 'That is the staff code. Enter the owner code to continue as owner.');
    await page.fill('#code', codes.owner); await page.click('#signin [type=submit]'); await page.waitForSelector('header.top');
    await role(page, 'staff'); await role(page, 'owner');
    check('T1 switching needs no code the second time', !(await page.$('#signin')));
    await role(page, 'staff'); await form(page);
    await page.fill('#message', `${TAG} unsent text`); await page.waitForTimeout(600);
    await page.click('button:has-text("Sign out")'); await page.waitForSelector('#signin');
    check('T1 step 6 message as written', (await text(page, '#signin .callout')) === 'Signed out of owner and staff in this browser.');
    await page.reload(); await page.waitForSelector('#signin');
    check('T1 still signed out after a reload', JSON.stringify(await held(page)) === '[]');
    await signIn(page, codes.staff); await form(page);
    check('T1 step 8: "Customer\'s message" is empty after signing out', (await page.inputValue('#message')) === '' && (await text(page, 'label[for=message]')).startsWith('Customer\'s message'));
    await page.click('[data-role=owner]'); await signIn(page, codes.owner); await role(page, 'staff');
    check('T1 no demo console link for staff', !(await page.$('a[href="#/console"]')));

    // T2
    await go(page, '#/customers'); await page.waitForSelector('.page-customers h1');
    await page.click('button:has-text("Add customer")'); await dlg(page).locator('[name=name]').fill(`${TAG} Manual A fictional`);
    await dlg(page).locator('button:has-text("Add customer")').click(); await page.waitForSelector('.tab-body');
    check('T2 you land on that customer\'s page', (await text(page, 'h1')) === `${TAG} Manual A fictional`);
    await page.click('.page-actions button:has-text("Add invoice")');
    check('T2 the dialog names the customer and has no customer list', (await text(page, 'dialog[open] .fixed')).includes(`${TAG} Manual A fictional`) && !(await page.$('dialog[open] select[name=customerId]')));
    check('T2 "Correct as of" is empty when the dialog opens', (await dlg(page).locator('[name=stillOwedAsOf]').inputValue()) === '');
    for (const [k, v] of [['reference', `${TAG}-001`], ['issueDate', '2026-10-05'], ['total', '1000.00']]) await dlg(page).locator(`[name=${k}]`).fill(v);
    await save(page, () => dlg(page).locator('button:has-text("Add invoice")').click());
    const rowA = await text(page, `tr:has-text("${TAG}-001")`);
    check('T2 Manual A: due "Not on record", still owed "Not recorded"', rowA.includes('Not on record') && rowA.includes('Not recorded'), rowA);
    await page.click('.back a:has-text("Customers")'); await page.waitForSelector('.page-customers h1');
    await page.click('button:has-text("Add customer")'); await dlg(page).locator('[name=name]').fill(`${TAG} Manual B fictional`);
    await dlg(page).locator('button:has-text("Add customer")').click(); await page.waitForSelector('.tab-body');
    await page.click('.page-actions button:has-text("Add invoice")');
    for (const [k, v] of [['reference', `${TAG}-001`], ['issueDate', '2026-10-05'], ['total', '200.00'], ['dueDate', '2026-10-10']]) await dlg(page).locator(`[name=${k}]`).fill(v);
    await save(page, () => dlg(page).locator('button:has-text("Add invoice")').click());
    check('T2 the same number is accepted for a second customer', (await text(page, '.tab-body')).includes(`${TAG}-001`));
    await page.click('.page-actions button:has-text("Add invoice")'); await dlg(page).locator('[name=reference]').fill('typed'); await page.keyboard.press('Escape');
    await page.waitForSelector('dialog[open]', { state: 'detached' }); await page.click('.page-actions button:has-text("Add invoice")');
    check('T2 optional: Esc keeps the draft, with "Start again"', (await dlg(page).locator('[name=reference]').inputValue()) === 'typed' && (await text(page, 'dialog[open] .restored')).includes('Start again'));
    await page.click('dialog[open] [data-forget]'); await page.waitForTimeout(200); await page.keyboard.press('Escape');

    // T3
    await go(page, '#/knowledge'); await page.waitForSelector('.page-knowledge h1');
    await page.click('button:has-text("Add a note")');
    await dlg(page).locator('[name=text]').fill(`${TAG} fictional test customer. Prefers a written payment date.`);
    await dlg(page).locator('[name=scope]').selectOption(await dlg(page).locator('[name=scope] option', { hasText: `${TAG} Manual A fictional` }).getAttribute('value'));
    await save(page, () => dlg(page).locator('button:has-text("Save draft")').click());
    await role(page, 'owner'); await go(page, '#/knowledge'); await page.waitForSelector('.page-knowledge h1');
    check('T3 Knowledge tells the owner drafts wait', (await text(page, '.page-knowledge .callout')).includes('for you to confirm'));
    await page.click('[data-note-filter=waiting]'); await page.waitForSelector('.notes');
    await save(page, () => page.click(`.notes li:has-text("${TAG} fictional test") button:has-text("Confirm")`));
    await role(page, 'staff');
    const c3 = await send(page, `Test ${TAG}. Could we pay invoice ${TAG}-001 on 14 November 2026 instead?`);
    check('T3 "The agent needs a detail"', (await text(page, '#answer h2')) === 'The agent needs a detail', await text(page, '[data-testid=status]'));
    await page.click('#answer button:has-text("Send to the agent")');
    check('T3 step 4 message as written', (await text(page, '[data-error-for=invoiceId]')) === 'Choose which customer\'s invoice this is.');
    await page.click(`#answer label:has-text("${TAG} Manual A fictional")`); await page.click('#answer button:has-text("Send to the agent")');
    await settled(page, ['awaiting_owner']);
    check('T3 the case says "With the owner"', (await text(page, '[data-testid=status]')).includes('With the owner'));
    await role(page, 'owner'); await go(page, '#/cases'); await page.waitForSelector('.case-row');
    await page.click(`.case-row[href="#/case/${c3}"]`); await page.waitForSelector('#decide');
    check('T3 the owner sees "What you\'ve noted" with the confirmed note', (await text(page, '.case-main')).includes(`${TAG} fictional test customer`));
    await page.click('#decide button:has-text("Record decision")');
    check('T3 step 5 message as written', (await text(page, '[data-error-for=outcome]')) === 'Choose an outcome: approve the date asked for, approve a different date, or decline.');
    await page.click('#decide label:has-text("Approve Sat 14 Nov")');
    check('T3 the button names the outcome', (await text(page, '#decide [type=submit]')) === 'Approve Sat 14 Nov');
    await page.fill('#reason', 'Fictional test only'); await page.click('#decide [type=submit]'); await settled(page, ['completed']);
    const s3 = await text(page, '.case');
    check('T3 approved; still owed not recorded; due date not on record', s3.includes('Approved. New payment date: Sat 14 Nov 2026.') && s3.includes('Not recorded') && s3.includes('Not on record'));
    await role(page, 'staff'); await go(page, '#/case/' + c3); await page.waitForSelector('#copy');
    await page.click('#copy'); await page.waitForFunction(() => document.querySelector('#copy')?.textContent.trim() === 'Copied');
    check('T3 the reply says "Saturday 14 November 2026" and the button says "Copied"', (await page.evaluate(() => navigator.clipboard.readText())).includes('The new payment date is Saturday 14 November 2026.'));
    await page.click('#tab-activity');
    check('T3 Activity names Manual A, not a code', (await text(page, '#panel-activity')).includes(`Staff answered: ${TAG} Manual A fictional`));
    await page.click('.case-sub a:has-text("Customer records")'); await page.waitForSelector('.tab-body');
    check('T3 "← Back to the request about TAG-001"', (await text(page, '.back')) === `← Back to the request about ${TAG}-001`);
    await page.click('.back a'); await page.waitForSelector(`.case[data-case="${c3}"]`);

    // T4
    const f01 = csv('01-invoices.csv');
    await upload(page, 'invoices', `${TAG} Invoice test`, f01);
    const cols = await page.$$eval('#params .mapping select', s => s.map(x => [x.labels[0].textContent.replace(' (required)', ''), x.options[x.selectedIndex].text]));
    check('T4 the five columns are matched; nothing for amounts owed or paid', ['Customer', 'Invoice number', 'Invoice date', 'Invoice amount', 'Due date'].every(n => cols.some(([, v]) => v === n))
      && cols.filter(([, v]) => v !== '— not in this file —').length === 5, JSON.stringify(cols));
    check('T4 "Apply" cannot be used and "Before applying" lists the unknown customers', (await page.getAttribute('#apply', 'aria-disabled')) === 'true' && (await text(page, '.callout.warn')).includes('Before applying'));
    for (const s of await page.$$('#params select[name^=cust-]')) await s.selectOption('new');
    await page.click('#params button:has-text("Update the rows below")'); await page.waitForSelector('#apply:not([aria-disabled=true])');
    const r4 = await text(page, '.rows-table');
    check('T4 rows show Mon 5 Oct 2026, AUD 1,000.00, Sat 10 Oct 2026 and AUD 200.00', r4.includes(`${TAG} Imported A fictional`) && r4.includes('Mon 5 Oct 2026') && r4.includes('AUD 1,000.00') && r4.includes('Sat 10 Oct 2026') && r4.includes('AUD 200.00'));
    await page.click('#apply:has-text("Apply 2 rows")'); await page.waitForSelector('.status-line .chip.done');
    check('T4 the import shows "Applied"', (await text(page, '.status-line')) === 'Applied');
    await upload(page, 'invoices', `${TAG} Invoice test`, f01);
    check('T4 "This exact file was applied before"; every row "Already recorded"', (await text(page, '.callout')).includes('This exact file was applied before') && (await page.$$eval('.rows-table tbody tr', rs => rs.every(r => r.textContent.includes('Already recorded')))));
    await page.click('a:has-text("Keep as a draft and close")'); await page.waitForSelector('#drafts-title');
    await page.click(`#drafts-title ~ div tr:has-text("${TAG} Invoice test") button:has-text("Discard")`); await dlg(page).locator('button:has-text("Discard draft")').click();
    await page.waitForSelector('dialog[open]', { state: 'detached' }); await page.waitForTimeout(500);
    check('T4 the draft leaves "Drafts not applied"; listed as discarded', !(await page.$(`#drafts-title ~ div tr:has-text("${TAG} Invoice test")`)) && (await text(page, '.more-list')).includes(`(${TAG} Invoice test)`));
    await upload(page, 'invoices', `${TAG} Invalid preview`, csv('03-invalid-preview-only.csv'));
    const r3 = await text(page, '.rows-table');
    check('T4 two rows "Rejected" (2026-02-31, 1O0.00) and one "New" of AUD 250.00', (r3.match(/Rejected/g) || []).length === 2 && r3.includes('2026-02-31') && r3.includes('1O0.00') && r3.includes('AUD 250.00'));
    await page.click('#discard'); await dlg(page).locator('button:has-text("Discard draft")').click(); await page.waitForSelector('.page-imports h1');
    const ia = await customer(page, `${TAG} Imported A fictional`);
    check('T4 one TAG-CSV-001 under Imported A', (await page.$$(`tr:has-text("${TAG}-CSV-001")`)).length === 1);

    // T5
    await upload(page, 'payments', `${TAG} Payment test`, csv('02-payments.csv'));
    const r5 = await text(page, '.rows-table');
    check('T5 rows: AUD 600.00 on Mon 12 Oct 2026 "Allocates AUD 600.00 to TAG-CSV-001"; AUD 50.00 no invoice', r5.includes(`Allocates AUD 600.00 to ${TAG}-CSV-001`) && r5.includes('Mon 12 Oct 2026') && r5.includes('AUD 50.00'));
    await page.click('#apply:has-text("Apply 2 rows")'); await page.waitForSelector('.status-line .chip.done');
    await customer(page, `${TAG} Imported A fictional`);
    const a5 = await text(page, `tr:has-text("${TAG}-CSV-001")`);
    check('T5 Imported A: "At most" AUD 400.00 with "AUD 600.00 allocated from payments"', a5.includes('AUD 400.00') && a5.includes('At most') && a5.includes('AUD 600.00 allocated from payments'), a5);
    const ib = await customer(page, `${TAG} Imported B fictional`);
    check('T5 Imported B: "Not recorded"', (await text(page, `tr:has-text("${TAG}-CSV-001")`)).includes('Not recorded'));
    await page.click('.subnav a:has-text("Payments")'); await page.waitForSelector(`tr:has-text("${TAG}-PAY-002")`);
    check('T5 the AUD 50.00 shows under "Not allocated"', (await text(page, `tr:has-text("${TAG}-PAY-002")`)).includes('Not allocated'));
    await page.click(`tr:has-text("${TAG}-PAY-002") button:has-text("Allocate")`);
    const opts = await dlg(page).locator('[name=invoiceId] option').evaluateAll(o => o.filter(x => x.value).map(x => x.textContent));
    check('T5 the dialog offers only Imported B\'s own invoice', opts.length === 1 && opts[0].startsWith(`${TAG}-CSV-001, AUD 200.00`), opts.join(' | '));
    await dlg(page).locator('button:has-text("Cancel")').click();

    // T6
    await role(page, 'owner'); await go(page, `#/customers/${ia}/invoices`); await page.waitForSelector('.tab-body');
    await page.click('.subnav a:has-text("Opening balance")'); await page.waitForSelector('button:has-text("Add opening balance")');
    await page.click('button:has-text("Add opening balance")');
    await dlg(page).locator('[name=asOf]').fill('2026-09-30'); await dlg(page).locator('[name=amount]').fill('0.00');
    await dlg(page).locator('label:has-text("Owed by the customer") input').check(); await dlg(page).locator('[name=credits]').selectOption({ label: 'It includes none' });
    await dlg(page).locator('[name=sourceLabel]').fill('Fictional test dataset starts from zero');
    await save(page, () => dlg(page).locator('button:has-text("Save opening balance")').click());
    check('T6 the opening balance shows "Entered by the owner"', (await text(page, '.kv')).includes('Entered by the owner'));
    await page.click(`button:has-text("Confirm completeness for ${TAG} Imported A fictional")`);
    check('T6 "Only the customers ticked below" with only Imported A ticked', await dlg(page).locator('[name=scope][value=some]').isChecked() && (await dlg(page).locator('[name=customer]:checked').count()) === 1);
    await dlg(page).locator('label:has-text("Payments received") input').check();
    await dlg(page).locator('[name=from]').fill('2026-10-01'); await dlg(page).locator('[name=to]').fill('2026-10-16');
    await dlg(page).locator('[name=sourceLabel]').fill('Fictional test pack contains the full payment history'); await dlg(page).locator('[name=confirm]').check();
    await save(page, () => dlg(page).locator('button:has-text("Confirm completeness")').click());
    await page.click('.subnav a:has-text("Invoices")'); await page.waitForSelector(`tr:has-text("${TAG}-CSV-001")`);
    const e6 = await text(page, `tr:has-text("${TAG}-CSV-001") .amount`);
    check('T6 Imported A: AUD 400.00 "Exact", as of Fri 16 Oct', e6.includes('AUD 400.00') && e6.includes('Exact') && e6.includes('as of Fri 16 Oct'), e6);
    await go(page, `#/customers/${ib}/invoices`); await page.waitForSelector(`tr:has-text("${TAG}-CSV-001")`);
    check('T6 Imported B stays "Not recorded"', (await text(page, `tr:has-text("${TAG}-CSV-001")`)).includes('Not recorded'));
    await role(page, 'staff');
    const c6 = await send(page, `Test ${TAG}. Could we pay invoice ${TAG}-CSV-001 on 14 November 2026 instead?`);
    if ((await status(page)) === 'needs_information') { await page.click(`#answer label:has-text("${TAG} Imported A fictional")`); await page.click('#answer button:has-text("Send to the agent")'); await settled(page, ['awaiting_owner']); }
    await role(page, 'owner'); await go(page, '#/case/' + c6); await page.waitForSelector('#decide');
    const f6 = await text(page, '.facts');
    check('T6 the case: AUD 400.00 "Exact", 6 days overdue, 35-day extension', f6.includes('AUD 400.00') && f6.includes('Exact') && f6.includes('6 days') && f6.includes('35 days'), f6);
    check('T6 it says which records are confirmed complete', (await text(page, '.case-main')).includes('Payment records are confirmed complete to Fri 16 Oct 2026'));
    await page.click('#decide label:has-text("Approve Sat 14 Nov")'); await page.fill('#reason', 'Fictional test only'); await page.click('#decide [type=submit]'); await settled(page, ['completed']);
    await page.screenshot({ path: path.join(OUT, 'guide-T6-owner-case.png'), fullPage: true });

    // T7
    await role(page, 'staff'); await go(page, `#/customers/${ia}/invoices`); await page.waitForSelector('.tab-body');
    await page.click('.page-actions button:has-text("Record payment or credit")');
    await dlg(page).locator('label:has-text("Money received") input').check(); await dlg(page).locator('[name=receivedDate]').fill('2026-10-14');
    await dlg(page).locator('[name=amount]').fill('10.00'); await dlg(page).locator('[name=reference]').fill(`${TAG}-LATE-ENTRY`);
    await save(page, () => dlg(page).locator('button:has-text("Record it")').click());
    await page.click(`tr:has-text("${TAG}-CSV-001") details.why summary`);
    check('T7 "At most" again; "Why not exact" names the added entry', (await text(page, `tr:has-text("${TAG}-CSV-001") .amount`)).includes('At most') && (await text(page, `tr:has-text("${TAG}-CSV-001") details.why`)).includes(`${TAG}-LATE-ENTRY was added inside that period after it was confirmed`));
    const box7 = await text(page, '.att-summary');
    check('T7 the box at the top says "1 item needs attention" and names the added entry', box7.startsWith('1 item needs attention') && box7.includes(`Payment records are no longer confirmed complete: ${TAG}-LATE-ENTRY was added`), box7);
    await page.click('.att-summary a:has-text("Review it")'); await page.waitForSelector('.attention');
    check('T7 "Review it" opens the Needs attention tab: the statement no longer holds, and why', (await text(page, '#tab-title')) === 'Needs attention' && (await text(page, '.attention')).includes('no longer holds') && (await text(page, '.attention')).includes(`${TAG}-LATE-ENTRY was added`));
    await go(page, '#/case/' + c6); await page.waitForSelector('[data-testid=flag]');
    const fl = await text(page, '[data-testid=flag]');
    check('T7 the case: records changed, payment named, staff, exactly → at most, decision stands', fl.includes('The records changed after this decision.') && fl.includes(`${TAG}-LATE-ENTRY`) && fl.includes('recorded by staff') && fl.includes('was exactly AUD 400.00') && fl.includes('now at most AUD 400.00') && fl.includes('The decision stands'), fl);
    await page.click('#tab-activity');
    check('T7 its Activity lists the change', (await text(page, '#panel-activity')).includes('Records changed after the decision'));
    const mb = await customer(page, `${TAG} Manual B fictional`);
    await page.click(`tr:has-text("${TAG}-001") button:has-text("Correct")`);
    await dlg(page).locator('[name=total]').fill('220.00'); await dlg(page).locator('[name=reason]').fill('Fictional correction test');
    await save(page, () => dlg(page).locator('button:has-text("Save correction")').click());
    const b7 = await text(page, `tr:has-text("${TAG}-001")`);
    check('T7 Manual B: AUD 220.00, "Corrected by staff", "Version 2"', b7.includes('AUD 220.00') && b7.includes('Corrected by staff') && b7.includes('Version 2'), b7);
    void mb;

    // T8
    await upload(page, 'invoices', `${TAG} Revert test`, csv('04-revert-only.csv'));
    for (const s of await page.$$('#params select[name^=cust-]')) await s.selectOption('new');
    await page.click('#params button:has-text("Update the rows below")'); await page.waitForSelector('#apply:not([aria-disabled=true])');
    await page.click('#apply'); await page.waitForSelector('#impact .points');
    const w8 = await text(page, '#impact');
    check('T8 "What reverting would do" lists TAG-RV-001 and the Revert Demo customer', w8.includes('What reverting would do') && w8.includes(`Invoice ${TAG}-RV-001 (${TAG} Revert Demo fictional) is marked reverted`) && w8.includes(`Customer ${TAG} Revert Demo fictional is marked reverted`));
    await page.click('button:has-text("Revert import…")'); await dlg(page).locator('[name=reason]').fill('Fictional reversal test');
    await dlg(page).locator('button:has-text("Revert import")').click(); await page.waitForSelector('.status-line .chip.wait');
    check('T8 the import shows "Reverted"', (await text(page, '.status-line')).includes('Reverted'));
    await go(page, '#/imports'); await page.waitForSelector('.page-imports h1');
    await page.click(`tr:has-text("01-invoices.csv"):has-text("${TAG} Invoice test"):has-text("New 2") a:has-text("View or revert")`); await page.waitForSelector('#impact .callout');
    check('T8 the 01 import "can\'t be reverted yet", no revert button', (await text(page, '#impact')).includes("can't be reverted yet") && !(await page.$('#revert')));
    await go(page, '#/imports'); await page.waitForSelector('.page-imports h1');
    await page.click(`tr:has-text("02-payments.csv"):has-text("${TAG} Payment test") a:has-text("View or revert")`); await page.waitForSelector('#impact .callout.warn');
    const w8b = await text(page, '#impact');
    const links = await page.$$eval('#impact .callout a', as => as.map(a => a.getAttribute('href')));
    check('T8 the 02 import lists only your T6 case under "Check these first"', w8b.includes('Check these first') && links.length === 1 && links[0] === '#/case/' + c6, links.join(' '));
    await page.click('#revert');
    check('T8 the button reads "Revert, having checked the above"', (await text(page, 'dialog[open] [type=submit]')) === 'Revert, having checked the above');
    await dlg(page).locator('[name=reason]').fill('Fictional dependent revert test'); await dlg(page).locator('[type=submit]').click();
    await page.waitForSelector('.status-line .chip.wait');
    await go(page, '#/case/' + c6); await page.waitForSelector('[data-testid=flag]');
    check('T8 the T6 case shows a second note naming the reverted import', (await page.$$('[data-testid=flag]')).length === 2 && (await text(page, '.case-head')).includes(`02-payments.csv, ${TAG} Payment test`));
  } catch (e) {
    check('guide walkthrough completed', false, e.message.split('\n')[0]);
    await page.screenshot({ path: path.join(OUT, 'guide-error.png'), fullPage: true }).catch(() => {});
  }
  check('no script errors', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log(`RESULT guide: ${results.filter(Boolean).length}/${results.length} checks passed (tag ${TAG})`);
  process.exit(results.every(Boolean) ? 0 : 1);
})();
