'use strict';
// Customers: the list, one page per customer (invoices, payments and credits, opening balance and completeness, notes, requests),
// completeness statements, and the questions that need a person. Every change happens in a dialog that says what it affects.
// Uses core.js helpers.

const R = { setup: null, data: null, imports: [], ix: null };
const isActive = rec => (rec.status || 'active') === 'active';
const isOwner = () => S.role === 'owner';
const INCLUSION = { included: 'Part of the opening balance', missed: 'Missed from the opening balance', unresolved: 'Opening balance: not answered' };
const CREDITS = { none: 'It includes no credits or prepayments', recorded: 'Every credit in it is recorded here' };

async function loadRecords() {
  [R.setup, R.data, R.imports] = await Promise.all([api('/api/setup'), api('/api/records'), api('/api/imports').catch(() => [])]);
  indexRecords();
}

// Lookups for one render, so each row finds its allocations and invoices directly instead of scanning every record.
function indexRecords() {
  const group = (list, key) => { const m = new Map(); for (const r of list) { if (!m.has(r[key])) m.set(r[key], []); m.get(r[key]).push(r); } return m; };
  const allocations = R.data.allocations.filter(isActive);
  R.ix = { customer: new Map(R.data.customers.map(c => [c.id, c])), invoice: new Map(R.data.invoices.map(i => [i.id, i])), payment: new Map(R.data.payments.map(p => [p.id, p])),
           allocation: new Map(R.data.allocations.map(a => [a.id, a])), byInvoice: group(allocations, 'invoiceId'), byPayment: group(allocations, 'paymentId'),
           invoicesOf: group(R.data.invoices.filter(isActive), 'customerId'), paymentsOf: group(R.data.payments.filter(isActive), 'customerId') };
}
const customersActive = () => R.data.customers.filter(isActive);
const customerName = id => R.ix.customer.get(id)?.name || 'Unknown customer';
const viewOf = id => R.data.positions?.customers?.[id];
const openingOf = id => (R.data.openingBalances || []).find(o => o.customerId === id && isActive(o));
const creditsOf = ob => ob ? ('credits' in ob ? ob.credits : ob.noCredits === true ? 'none' : null) : null;
const abs = m => ({ ...m, minorUnits: String(BigInt(m.minorUnits) < 0n ? -BigInt(m.minorUnits) : BigInt(m.minorUnits)) });
const leftOn = p => BigInt(p.amount.minorUnits) - (R.ix.byPayment.get(p.id) || []).reduce((n, a) => n + BigInt(a.amount.minorUnits), 0n);
const ROLE_WORD = { staff: 'staff', owner: 'the owner' };

// Who put a record here, and how: "Entered by staff, 18 Oct 2026, 3:38 pm", "From import: Accounts list", "Corrected by the owner".
function sourceOf(rec) {
  const o = rec.setBy || rec.origin;
  if (!o) return 'Sample data';
  const who = actorWho(o, ROLE_WORD[o.role] || 'a person');
  if (o.kind === 'file') return 'From import: ' + (o.sourceLabel || 'a file');
  if (o.kind === 'correction') return 'Corrected by ' + who;
  if (o.kind === 'revert') return 'Restored when an import was reverted';
  return 'Entered by ' + who;
}
const sourceHtml = rec => `${esc(sourceOf(rec))}${(rec.setBy || rec.origin)?.at ? ', ' + stamp((rec.setBy || rec.origin).at) : ''}${rec.version > 1 ? `<span class="ver">Version ${rec.version}</span>` : ''}`;

async function act(button, path, body, done) {
  const id = path + ':' + JSON.stringify(body);
  let result = null;
  await busy(button, async () => {
    try { result = await api(path, body, { key: keyFor(id) }); keyDone(id); if (done) toast(done, 'ok'); }
    catch (error) { toast(error.message, 'bad'); result = { error }; }
  });
  return result;
}

// After any change: reload the records and draw the same page again, keeping the scroll position.
async function afterChange() {
  const y = scrollY;
  try { await loadSession(S.role); } catch { /* keep the old session data */ }
  await route();
  scrollTo(0, y);
}

// ---------------------------------------------------------------- amounts and questions

// What is still owed on one invoice, with its certainty and, when not exact, why (QA U6, U7).
function owedHtml(i) {
  const p = R.data.positions?.invoices?.[i.id];
  const why = R.data.positions?.notExact?.[i.id];
  const notExact = why?.length && p?.status !== 'settled' ? `<details class="why"><summary>Why not exact</summary><ul>${why.map(t => `<li>${esc(t)}</li>`).join('')}</ul></details>` : '';
  if (p?.exact) return p.status === 'settled' ? certainty('settled', '', 'complete records to ' + dateText(p.exact.asOf, false))
    : certainty('exact', money(p.exact.amount), 'as of ' + dateText(p.exact.asOf, false)) + (p.exact.later ? `<p class="hint">At most ${esc(money(p.atMost))} now, after later payments.</p>` : '');
  if (p) return (p.status === 'settled' ? certainty('settled', '', money(p.allocated) + ' allocated from payments')
    : certainty('atMost', money(p.atMost), p.basis === 'total' ? money(p.allocated) + ' allocated from payments' : money(p.stated) + ' stated as of ' + dateText(p.statedAsOf, false) + (BigInt(p.counted.minorUnits) ? ', less ' + money(p.counted) : '')))
    + (p.status === 'conflict' ? '<p class="hint bad">The records contradict each other.</p>' : '') + notExact;
  if (i.outstandingAmount) return certainty('stated', money(i.outstandingAmount), i.outstandingAsOf ? 'as of ' + dateText(i.outstandingAsOf, false) : '') + notExact;
  const left = viewOf(i.customerId)?.owed?.left?.[i.id];   // none recorded: what the replay leaves on it, as the assessment reads the records
  if (left) return certainty('workedOut', money(left), 'not recorded; the invoice amount less the payments applied to it, recorded allocations first, then oldest first') + notExact;
  return certainty('none', '', 'No amount stated and no payment allocated yet; record a payment against this invoice or state the amount owed.') + notExact;
}

function inclusionChip(customerId, recordId) {
  const status = viewOf(customerId)?.opening?.records.find(r => r.id === recordId)?.status;
  return status && status !== 'new' ? ` <span class="chip incl ${status === 'unresolved' ? 'need' : status === 'missed' ? 'wait' : 'done'}">${esc(INCLUSION[status])}</span>` : '';
}

// Questions a person has to answer, and contradictions to look at. Nothing here is decided by the app.
function attentionFor(customerId) {
  const c = R.ix.customer.get(customerId);
  const items = [];
  const v = viewOf(customerId)?.opening;
  if (v?.suggestion) items.push({ kind: 'question', group: 'opening', ref: v.suggestion.references.join(', '), html: `<p>The amounts still owed on <b>${esc(v.suggestion.references.join(', '))}</b> at ${esc(dateText(v.asOf, false))} add up exactly to the opening balance. That suggests they make it up, but a missing invoice and a missing credit would add up just as well. Are they all part of it?</p>
    <div class="row"><button type="button" class="btn" data-act="confirm-suggestion" data-ids="${esc(v.suggestion.ids.join(','))}">Yes, all of them are part of it</button><span class="hint">Otherwise answer each one below.</span></div>` });
  v?.records.filter(r => r.status === 'unresolved').forEach(r => items.push({ kind: 'question', group: 'opening', ref: r.reference, html: `<p>Is ${r.kind === 'invoice' ? 'invoice' : 'the payment'} <b>${esc(r.reference)}</b>${r.date ? ' (' + esc(dateText(r.date, false)) + ')' : ''} already part of the opening balance as at ${esc(dateText(v.asOf, false))}?</p>
    <div class="row"><button type="button" class="btn" data-act="inclusion" data-kind="${r.kind === 'invoice' ? 'invoices' : 'payments'}" data-id="${esc(r.id)}" data-status="included">Yes, it's part of it</button>
      <button type="button" class="btn" data-act="inclusion" data-kind="${r.kind === 'invoice' ? 'invoices' : 'payments'}" data-id="${esc(r.id)}" data-status="missed">No, it was missed</button>
      <span class="hint">Not sure? Leave it: it isn't counted either way.</span></div>` }));
  (v?.conflicts || []).forEach(t => items.push({ kind: 'conflict', group: 'conflict', ref: 'the opening balance', html: `<p>${esc(t)}</p>` }));
  const cov = viewOf(customerId)?.coverage;
  ['invoices', 'payments'].forEach(kind => (cov?.[kind].contradicted || []).forEach(x => items.push({ kind: 'conflict', group: 'completeness', short: `${kind === 'payments' ? 'Payment' : 'Invoice'} records are no longer confirmed complete: ${(x.changes || x.records.map(r => ({ record: r }))).map(ch => ch.record + (ch.change === 'added' ? ' was added' : ch.change === 'removed' ? ' was taken out' : ' changed')).join('; ')}`, html: `<p>The statement that ${kind === 'payments' ? 'payment' : 'invoice'} records were complete${x.from ? ` from ${esc(dateText(x.from, false))} to ${esc(dateText(x.to, false))}` : ''} no longer holds for ${esc(c?.name || '')}: ${esc(changesText(x))}. It doesn't count until completeness is confirmed again${isOwner() ? '' : ' by the owner'}, or the record is removed if it was a mistake.</p>` })));
  Object.entries(R.data.positions?.invoices || {}).forEach(([id, p]) => {
    const inv = R.ix.invoice.get(id);
    if (!inv || inv.customerId !== customerId) return;
    p.inclusion.unresolved.forEach(aid => {
      const a = R.ix.allocation.get(aid), pay = a && R.ix.payment.get(a.paymentId);
      if (pay) items.push({ kind: 'question', group: 'counted', ref: inv.reference, html: `<p>Was the ${esc(money(a.amount))} paid on ${esc(dateText(pay.receivedDate, false))}${pay.reference ? ' (' + esc(pay.reference) + ')' : ''} already taken off the ${esc(money(p.stated))} stated still owed on ${esc(inv.reference)} as of ${esc(dateText(p.statedAsOf, false))}?${p.inclusion.reconciles.includes(aid) ? ' <span class="hint">The amounts reconcile, which suggests yes; an unrecorded credit would reconcile just as well.</span>' : ''}</p>
        <div class="row"><button type="button" class="btn" data-act="statement" data-id="${esc(aid)}" data-status="included">Yes, already counted</button><button type="button" class="btn" data-act="statement" data-id="${esc(aid)}" data-status="missed">No, it still comes off</button></div>` });
    });
    p.conflicts.forEach(t => items.push({ kind: 'conflict', group: 'conflict', ref: inv.reference, html: `<p>${esc(inv.reference)}: ${esc(t)}</p>` }));
  });
  return items;
}
// "LATE-1 was added inside that period after it was confirmed" (QA U7: added, not "changed").
const changesText = x => (x.changes || x.records.map(r => ({ record: r, change: 'changed' }))).map(ch => `${ch.record} was ${ch.change === 'added' ? 'added inside its period' : ch.change === 'removed' ? 'taken out of its period' : 'changed inside its period'} after it was confirmed`).join('; ');

function attentionHtml(customerId) {
  const items = attentionFor(customerId);
  if (!items.length) return '<p class="empty">Nothing needs attention for this customer.</p>';
  return `<section class="attention" aria-label="Needs attention">
    <p class="hint">Until these are answered, amounts that depend on them aren't counted either way and nothing is called exact.</p>
    <ul>${items.map(x => `<li class="${x.kind}">${x.html}</li>`).join('')}</ul></section>`;
}

// Above the records: how many items need attention, one line per kind, naming the records; blocking ones first. The details and
// the answers are on the Needs attention tab.
function attentionSummary(c, items, keep) {
  if (!items.length) return '';
  const refs = list => { const names = [...new Set(list.map(x => x.ref))]; return names.slice(0, 3).join(', ') + (names.length > 3 ? ` and ${names.length - 3} more` : ''); };
  const of = g => items.filter(x => x.group === g);
  const lines = [
    of('conflict').length && { cls: 'conflict', text: `Records contradict each other: ${refs(of('conflict'))}` },
    ...of('completeness').map(x => ({ cls: 'conflict', text: x.short })),
    of('opening').length && { cls: 'question', text: `${of('opening').length === 1 ? 'A question' : of('opening').length + ' questions'} about the opening balance: ${refs(of('opening'))}` },
    of('counted').length && { cls: 'question', text: `${of('counted').length === 1 ? 'A question' : of('counted').length + ' questions'} about payments already counted: ${refs(of('counted'))}` },
  ].filter(Boolean);
  return `<section class="att-summary" aria-labelledby="att-sum-title"><h2 id="att-sum-title">${plural(items.length, 'item needs', 'items need')} attention</h2>
    <ul>${lines.map(l => `<li class="${l.cls}">${esc(l.text)}</li>`).join('')}</ul>
    <a class="btn small" href="#/customers/${esc(c.id)}/attention${keep}">Review ${items.length === 1 ? 'it' : 'all ' + items.length}</a></section>`;
}

// Buttons that answer a question or change one thing directly, anywhere on a records page.
function bindActions(root) {
  root.addEventListener('click', async event => {
    const b = event.target.closest('[data-act]');
    if (!b) return;
    const a = b.dataset.act;
    let result;
    if (a === 'inclusion') result = await act(b, `/api/records/${b.dataset.kind}/${b.dataset.id}/inclusion`, { status: b.dataset.status }, 'Answer saved');
    if (a === 'statement') result = await act(b, `/api/records/allocations/${b.dataset.id}/statement`, { status: b.dataset.status }, 'Answer saved');
    if (a === 'confirm-suggestion') {   // a person confirms each suggested record; one answer per record, all attributed
      for (const id of b.dataset.ids.split(',')) { result = await act(b, `/api/records/invoices/${id}/inclusion`, { status: 'included' }); if (result?.error) break; }
      if (!result?.error) toast('Answers saved', 'ok');
    }
    if (a === 'confirm-note') result = await act(b, `/api/records/notes/${b.dataset.id}/confirm`, {}, 'Note confirmed');
    if (result && !result.error) await afterChange();
    if (DIALOGS[a]) DIALOGS[a](b.dataset);
  });
}

// ---------------------------------------------------------------- customers list

PAGES.customers = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('customers');
  await loadRecords();
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  const customers = customersActive();
  const q = recalled('cust-q') || '';
  const onlyAttention = recalled('cust-att') === '1';
  const attention = new Map(customers.map(c => [c.id, attentionFor(c.id).length]));
  const totalAttention = [...attention.values()].reduce((n, x) => n + x, 0);
  const gone = R.data.customers.length - customers.length;
  main.innerHTML = `${pageHead({ title: 'Customers', lede: 'Each customer\'s invoices, payments, opening balance and completeness. Open a customer to see or change their records.',
      actions: `<button type="button" class="btn primary" data-act="add-customer">Add customer</button><a class="btn" href="#/completeness">Completeness statements</a>` })}
    ${totalAttention ? `<p class="callout warn"><b>${plural(totalAttention, 'item needs', 'items need')} attention</b> for ${plural([...attention.values()].filter(Boolean).length, 'customer', 'customers')}: questions to answer or records that contradict each other. They're marked below.</p>` : ''}
    ${customers.length ? `<div class="toolbar"><div class="field inline-field"><label for="cust-q">Find a customer or invoice number</label><input id="cust-q" type="search" value="${esc(q)}" autocomplete="off"></div>
      <label class="tick"><input type="checkbox" id="cust-att"${onlyAttention ? ' checked' : ''}> Needs attention only</label></div>
      <div class="table-wrap"><table class="rtable customers-table"><caption class="visually-hidden">Customers</caption>
        <thead><tr><th scope="col">Customer</th><th scope="col" class="num">Open invoices</th><th scope="col" class="num">Not allocated</th><th scope="col">Opening balance</th><th scope="col">Payments complete to</th><th scope="col">Needs attention</th></tr></thead>
        <tbody id="cust-rows"></tbody></table></div>
      <p class="empty" id="cust-none" hidden>No customer matches. <button type="button" class="btn link" id="cust-clear">Clear the search</button></p>`
    : `<div class="state-msg start"><h2>No customers yet</h2><p>Add a customer and their invoices by hand, or import an invoice list.</p><div class="row"><button type="button" class="btn primary" data-act="add-customer">Add customer</button><a class="btn" href="#/imports/new">Import a CSV file</a></div></div>`}
    ${gone ? `<p class="hint">${plural(gone, 'removed or reverted customer is', 'removed or reverted customers are')} kept in the history and not used by the agent.</p>` : ''}`;
  const rows = () => {
    const text = ($('#cust-q')?.value || '').trim().toLowerCase();
    const att = $('#cust-att')?.checked;
    remember('cust-q', text || undefined); remember('cust-att', att ? '1' : undefined);
    const shown = customers.filter(c => (!att || attention.get(c.id)) && (!text || c.name.toLowerCase().includes(text) || (c.displayCode || '').toLowerCase().includes(text)
      || (R.ix.invoicesOf.get(c.id) || []).some(i => i.reference.toLowerCase().includes(text)) || (c.aliases || []).some(x => x.toLowerCase().includes(text))));
    $('#cust-rows').innerHTML = shown.map(c => {
      const p = viewOf(c.id) || {};
      const ob = p.opening;
      const open = (R.ix.invoicesOf.get(c.id) || []).filter(i => R.data.positions?.invoices?.[i.id]?.status !== 'settled').length;
      const unalloc = p.unallocatedOpen && BigInt(p.unallocatedOpen.minorUnits) > 0n ? money(p.unallocatedOpen) : null;
      const complete = p.coverage?.payments?.completeTo;
      return `<tr><th scope="row" data-label="Customer"><a href="#/customers/${esc(c.id)}">${esc(c.name)}</a><span class="code">${esc(c.displayCode)}</span></th>
        <td data-label="Open invoices" class="num">${open}</td>
        <td data-label="Not allocated" class="num">${unalloc ? esc(unalloc) : '<span class="muted">None</span>'}</td>
        <td data-label="Opening balance">${ob ? `${esc(money(abs(ob.openingBalance.amount)))} ${BigInt(ob.openingBalance.amount.minorUnits) < 0n ? 'in credit' : 'owed'}<span class="hint-inline">as at ${esc(dateText(ob.asOf, false))}</span>` : '<span class="muted">None</span>'}</td>
        <td data-label="Payments complete to">${complete ? esc(dateText(complete, false)) : '<span class="muted">Not confirmed</span>'}</td>
        <td data-label="Needs attention">${attention.get(c.id) ? `<a class="chip need" href="#/customers/${esc(c.id)}/attention">${plural(attention.get(c.id), 'item', 'items')}</a>` : '<span class="muted">Nothing</span>'}</td></tr>`;
    }).join('');
    $('#cust-none').hidden = shown.length > 0;
  };
  if (customers.length) {
    rows();
    $('#cust-q').oninput = rows; $('#cust-att').onchange = rows;
    $('#cust-clear').onclick = () => { $('#cust-q').value = ''; $('#cust-att').checked = false; rows(); };
  }
  bindActions(main);
};

function renderNotReady(main) {
  main.innerHTML = `${pageHead({ title: 'Customers' })}<div class="callout warn"><p><b>The workspace isn't set up yet.</b> The owner chooses the currency, decimal places and time zone first.</p><p><a class="btn primary" href="#/setup">Open setup</a></p></div>`;
}

// ---------------------------------------------------------------- one customer

// Short tab labels; each tab's own heading gives the full name.
const TABS = [['invoices', 'Invoices'], ['payments', 'Payments'], ['balance', 'Opening balance'], ['notes', 'Notes'], ['requests', 'Requests'], ['attention', 'Needs attention']];
const TAB_TITLES = { invoices: 'Invoices', payments: 'Payments and credits', balance: 'Opening balance and completeness', notes: 'Notes', requests: 'Requests', attention: 'Needs attention' };

PAGES.customer = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('the customer');
  await loadRecords();
  if (!S.cases.length || r.tab === 'requests') { try { S.cases = await api('/api/requests'); } catch { /* the tab says so */ } }
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  const c = R.ix.customer.get(r.id);
  if (!c) { main.innerHTML = `${pageHead({ back: { href: '#/customers', label: 'Customers' }, title: 'Customer not found' })}<p>This customer isn't in the records. The link may be wrong, or a demo reset cleared it.</p>`; return; }
  if (!isActive(c)) { main.innerHTML = `${pageHead({ back: { href: '#/customers', label: 'Customers' }, title: c.name })}<p class="callout">This customer was ${c.status === 'reverted' ? 'reverted with the import that created it' : 'removed'}. Their records are kept in the history and the agent no longer uses them.</p>`; return; }
  // Opened from a case: the way back to it is kept on every tab (contextual return).
  const fromCase = r.q.from && r.q.from.startsWith('req_') ? r.q.from : null;
  const theCase = fromCase && S.cases.find(x => x.id === fromCase);
  const keep = fromCase ? '?from=' + encodeURIComponent(fromCase) : '';
  const back = fromCase ? { href: '#/case/' + fromCase + '?from=' + c.id, label: `Back to the request${theCase?.invoiceReference ? ' about ' + theCase.invoiceReference : ''}` } : { href: '#/customers', label: 'Customers' };
  const p = viewOf(c.id) || {};
  const invoices = R.ix.invoicesOf.get(c.id) || [];
  const payments = R.ix.paymentsOf.get(c.id) || [];
  const attention = attentionFor(c.id);
  const counts = { invoices: invoices.length, payments: payments.length, notes: R.data.notes.filter(n => n.scope === c.id && ['draft', 'confirmed'].includes(n.status)).length,
                   requests: S.cases.filter(x => x.customerId === c.id).length, attention: attention.length };
  const tab = TAB_RENDER[r.tab] ? r.tab : 'invoices';
  // Order: who, the routine actions, what needs attention (briefly), the key facts, then the records. Totals and rare actions last.
  main.innerHTML = `${pageHead({ back, title: c.name, lede: `Customer ${esc(c.displayCode)}${(c.aliases || []).length ? '. Also known as ' + esc(c.aliases.join(', ')) : ''}`,
      actions: `<button type="button" class="btn primary" data-act="add-invoice" data-customer="${esc(c.id)}">Add invoice</button>
        <button type="button" class="btn" data-act="add-payment" data-customer="${esc(c.id)}">Record payment or credit</button>` })}
    ${tab === 'attention' ? '' : attentionSummary(c, attention, keep)}
    ${keyLine(p)}
    <nav class="subnav" aria-label="${esc(c.name)} records">${TABS.filter(([k]) => k !== 'attention' || tab === 'attention').map(([k, label]) => `<a href="#/customers/${esc(c.id)}/${k}${keep}"${k === tab ? ' aria-current="page"' : ''}${k === 'attention' ? ' class="att-tab"' : ''}>${label}${counts[k] != null ? ` <span class="n">${counts[k]}</span>` : ''}</a>`).join('')}</nav>
    <section class="tab-body" aria-labelledby="tab-title"><h2 id="tab-title" class="tab-title">${esc(TAB_TITLES[tab])}</h2>${TAB_RENDER[tab](c, p)}</section>
    ${totalsHtml(p)}
    <section class="record-admin" aria-labelledby="admin-title"><h2 id="admin-title">This customer record</h2>
      <p class="hint">${esc(sourceOf(c))}${c.version > 1 ? ', version ' + c.version : ''}. A customer can be removed only when none of their records is still active.</p>
      <div class="row"><button type="button" class="btn small" data-act="correct-customer" data-id="${esc(c.id)}">Correct name</button>
      <button type="button" class="btn small danger" data-act="remove" data-kind="customers" data-id="${esc(c.id)}">Remove customer</button></div></section>`;
  bindActions(main);
};

// The facts that say how far the amounts can be trusted, on one line: money not allocated, payments complete to, and what is owed now
// (worked out, with its parts). The balance from the opening balance is on the Opening balance tab.
function keyLine(p) {
  const complete = p.coverage?.payments?.completeTo;
  const unalloc = p.unallocatedOpen && BigInt(p.unallocatedOpen.minorUnits) > 0n;
  return `<dl class="keyline">
    <div><dt>Received, not matched to an invoice</dt><dd>${unalloc ? `<span class="warn-text">${esc(money(p.unallocatedOpen))}</span>` : 'None'}</dd></div>
    <div><dt>Payments complete to</dt><dd>${complete ? esc(dateText(complete, false)) : '<span class="warn-text">Not confirmed</span>'}</dd></div>
    <div><dt>Owed now</dt><dd>${p.owed ? owedNowHtml(p.owed) : '<span class="muted">Not calculated</span>'}</dd></div>
  </dl>`;
}

// What has been entered, as totals: not what is owed.
function totalsHtml(p) {
  return `<section class="totals" aria-labelledby="totals-title"><h2 id="totals-title">Recorded totals</h2><dl class="kv">
    <div><dt>Invoices recorded</dt><dd>${p.invoicesRecorded ? esc(money(p.invoicesRecorded)) : '<span class="muted">None</span>'}${p.invoicesWithoutAmount ? `<span class="hint-inline">and ${plural(p.invoicesWithoutAmount, 'invoice', 'invoices')} without an amount</span>` : ''}</dd></div>
    <div><dt>Payments and credits recorded</dt><dd>${p.payments ? esc(money(p.paymentsRecorded)) : '<span class="muted">None</span>'}${p.markedUnrelated && BigInt(p.markedUnrelated.minorUnits) ? `<span class="hint-inline">${esc(money(p.markedUnrelated))} marked as not for an open invoice</span>` : ''}</dd></div>
    ${p.recordedNet ? `<div><dt>Recorded invoices less recorded payments</dt><dd>${esc(money(p.recordedNet))}<span class="hint-inline">A difference of records that may be incomplete${p.owed?.hasOpening ? '; it leaves out the opening balance' : ''}. It is not what is owed: see Owed now.</span></dd></div>` : ''}
  </dl><p class="hint">Totals of what has been entered, not what is owed.</p></section>`;
}

const TAB_RENDER = {
  attention(c) { return attentionHtml(c.id); },
  invoices(c) {
    const invoices = R.ix.invoicesOf.get(c.id) || [];
    const gone = R.data.invoices.filter(i => i.customerId === c.id && !isActive(i)).length;
    if (!invoices.length) return `<div class="empty"><p>No invoices for ${esc(c.name)}.</p><button type="button" class="btn primary" data-act="add-invoice" data-customer="${esc(c.id)}">Add invoice</button></div>`;
    return `<div class="table-wrap"><table class="rtable"><caption class="visually-hidden">Invoices of ${esc(c.name)}</caption>
      <thead><tr><th scope="col">Invoice</th><th scope="col">Issued</th><th scope="col" class="num">Amount</th><th scope="col">Due</th><th scope="col">Still owed</th><th scope="col">Source</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead>
      <tbody>${invoices.map(i => `<tr><th scope="row" data-label="Invoice">${esc(i.reference)}${inclusionChip(c.id, i.id)}</th>
        <td data-label="Issued">${i.issueDate ? esc(dateText(i.issueDate)) : '<span class="muted">Not recorded</span>'}</td>
        <td data-label="Amount" class="num">${i.total ? esc(money(i.total)) : '<span class="muted">Not recorded</span>'}</td>
        <td data-label="Due">${i.originalDueDate ? esc(dateText(i.originalDueDate)) : '<span class="muted">Not on record</span>'}${dueChange(i)}</td>
        <td data-label="Still owed">${owedHtml(i)}</td>
        <td data-label="Source" class="src">${sourceHtml(i)}</td>
        <td data-label="Actions" class="actions">${recordActions('invoices', i)}</td></tr>`).join('')}</tbody></table></div>
      ${gone ? `<p class="hint">${plural(gone, 'removed or reverted invoice is', 'removed or reverted invoices are')} kept in the history and not used by the agent.</p>` : ''}
      <p class="hint">A due date moved by an approved request shows under Due. The invoice record keeps its original due date.</p>`;
  },
  payments(c) {
    const payments = R.ix.paymentsOf.get(c.id) || [];
    if (!payments.length) return `<div class="empty"><p>No payments or credits recorded for ${esc(c.name)}. No payment recorded is not proof that an invoice is unpaid.</p><button type="button" class="btn primary" data-act="add-payment" data-customer="${esc(c.id)}">Record payment or credit</button></div>`;
    return `<p class="hint">Allocate money received to this customer's invoices yourself. Nothing is allocated automatically, and money not allocated stays visible.</p>
      <div class="table-wrap"><table class="rtable"><caption class="visually-hidden">Payments and credits of ${esc(c.name)}</caption>
      <thead><tr><th scope="col">Received</th><th scope="col" class="num">Amount</th><th scope="col">Allocated to</th><th scope="col" class="num">Not allocated</th><th scope="col">Source</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead>
      <tbody>${payments.map(p => {
        const used = R.ix.byPayment.get(p.id) || [];
        const left = leftOn(p);
        return `<tr><th scope="row" data-label="Received">${esc(dateText(p.receivedDate))}${p.kind === 'credit' ? ' <span class="chip wait">Credit</span>' : ''}${p.reference ? `<span class="code">${esc(p.reference)}</span>` : ''}${inclusionChip(c.id, p.id)}</th>
          <td data-label="Amount" class="num">${esc(money(p.amount))}</td>
          <td data-label="Allocated to">${used.map(a => `<span class="alloc">${esc(R.ix.invoice.get(a.invoiceId)?.reference || 'an invoice')} ${esc(money(a.amount))} <button type="button" class="btn link small" data-act="remove" data-kind="allocations" data-id="${esc(a.id)}">Remove<span class="visually-hidden"> this allocation</span></button></span>`).join('') || '<span class="muted">Not allocated</span>'}</td>
          <td data-label="Not allocated" class="num">${left > 0n ? esc(money({ ...p.amount, minorUnits: String(left) })) + (p.notForOpenInvoices ? '<span class="hint-inline">Not for an open invoice</span>' : '') : '<span class="muted">None</span>'}</td>
          <td data-label="Source" class="src">${sourceHtml(p)}</td>
          <td data-label="Actions" class="actions">${left > 0n ? `<button type="button" class="btn small" data-act="allocate" data-id="${esc(p.id)}">Allocate</button><button type="button" class="btn small" data-act="unrelated" data-id="${esc(p.id)}">${p.notForOpenInvoices ? 'It may be for an invoice' : 'Not for an open invoice'}</button>` : ''}${recordActions('payments', p)}</td></tr>`;
      }).join('')}</tbody></table></div>`;
  },
  balance(c, p) {
    const v = p.opening;
    const ob = openingOf(c.id);
    const cov = p.coverage || {};
    const statements = (R.data.coverage || []).filter(isActive).filter(s => s.customers === 'all' || s.customers.includes(c.id));
    return `<div class="split">
      <section aria-labelledby="ob-title"><h3 id="ob-title">Opening balance</h3>
        ${v ? `<dl class="kv">
          <div><dt>As at</dt><dd>${esc(dateText(v.asOf))}</dd></div>
          <div><dt>Amount</dt><dd>${esc(money(abs(v.openingBalance.amount)))} ${BigInt(v.openingBalance.amount.minorUnits) < 0n ? 'held in credit for them' : 'owed by the customer'}</dd></div>
          <div><dt>Credits or prepayments in it</dt><dd>${esc(CREDITS[v.credits] || 'Not stated')}</dd></div>
          <div><dt>Where the figure comes from</dt><dd>${esc(v.openingBalance.sourceLabel)}</dd></div>
          <div><dt>Who and when</dt><dd>${ob ? sourceHtml(ob) : ''}</dd></div>
          <div><dt>Customer balance from it</dt><dd>${v.balance ? certainty('recorded', money(v.balance), 'the whole account, not one invoice; only what is recorded') : `<span class="muted">Not calculated: ${esc(v.withoutAmount.join(', '))} has no amount</span>`}
            ${v.unresolvedInvoices.count > v.unresolvedInvoices.withoutAmount ? `<span class="hint-inline">plus up to ${esc(money(v.unresolvedInvoices.amount))} in invoices not answered</span>` : ''}
            ${v.unresolvedInvoices.withoutAmount ? `<span class="hint-inline">plus ${plural(v.unresolvedInvoices.withoutAmount, 'invoice', 'invoices')} not answered and with no amount</span>` : ''}
            ${v.unresolvedPayments.count ? `<span class="hint-inline">minus up to ${esc(money(v.unresolvedPayments.amount))} in payments not answered</span>` : ''}
            ${v.impliedCredits ? `<span class="hint-inline">credits of at least ${esc(money(v.impliedCredits))} implied</span>` : ''}</dd></div>
        </dl>
        <div class="row"><button type="button" class="btn" data-act="opening" data-customer="${esc(c.id)}" data-id="${esc(ob.id)}">Correct</button><button type="button" class="btn danger" data-act="remove" data-kind="openingBalances" data-id="${esc(ob.id)}">Remove</button></div>`
        : `<p>No opening balance for ${esc(c.name)}. It states what they owed, or held in credit, at one date: everything up to then in one figure. An exact amount still owed needs one.</p>
          <button type="button" class="btn primary" data-act="opening" data-customer="${esc(c.id)}">Add opening balance</button>`}
        <p class="hint">Who may enter opening balances is still an open business question, so staff and the owner both can. Each one shows who entered it.</p>
      </section>
      <section aria-labelledby="cov-title"><h3 id="cov-title">Completeness</h3>
        <p class="hint">Records are complete only when the owner says so, for a period. Entering records or importing a file never makes them complete. An exact amount still owed needs payment records confirmed complete.</p>
        <div class="table-wrap"><table class="rtable"><thead><tr><th scope="col">Records</th><th scope="col">Confirmed complete to</th><th scope="col">Latest record</th></tr></thead><tbody>
          ${['invoices', 'payments'].map(k => `<tr><th scope="row" data-label="Records">${k === 'invoices' ? 'Invoices' : 'Payments received'}</th><td data-label="Confirmed complete to">${cov[k]?.completeTo ? esc(dateText(cov[k].completeTo)) : '<span class="muted">Not confirmed</span>'}</td><td data-label="Latest record">${cov[k]?.lastActivity ? esc(dateText(cov[k].lastActivity)) : '<span class="muted">None</span>'}</td></tr>`).join('')}
        </tbody></table></div>
        ${statements.length ? `<h4>Statements that cover ${esc(c.name)}</h4><ul class="statements">${statements.map(s => statementHtml(s, c.id)).join('')}</ul>` : ''}
        ${isOwner() ? `<button type="button" class="btn primary" data-act="coverage" data-customers="${esc(c.id)}">Confirm completeness for ${esc(c.name)}</button>` : '<p class="hint">The owner confirms completeness.</p>'}
      </section></div>`;
  },
  notes(c) {
    const notes = R.data.notes.filter(n => (n.scope === c.id || n.scope === 'business') && ['draft', 'confirmed'].includes(n.status));
    return `<p class="hint">Notes the agent shows the owner in this customer's requests. Only notes the owner has confirmed are used. <a href="#/knowledge">All notes</a></p>
      ${notes.length ? `<ul class="notes">${notes.map(noteHtml).join('')}</ul>` : '<p class="empty">No notes about this customer.</p>'}
      <button type="button" class="btn primary" data-act="add-note" data-scope="${esc(c.id)}">Add a note about ${esc(c.name)}</button>`;
  },
  requests(c) {
    const cases = S.cases.filter(x => x.customerId === c.id);
    if (!cases.length) return `<p class="empty">No requests from ${esc(c.name)} yet.</p>`;
    return `<ul class="cases wide">${cases.map(x => `<li><a class="case-row" href="#/case/${esc(x.id)}?from=${esc(c.id)}"><span class="who">Invoice ${esc(x.invoiceReference || 'not identified')}${x.requestedDueDate ? ', asked for ' + esc(dateText(x.requestedDueDate, false)) : ''}</span><span class="meta">${chip(statusOf(x))}<time datetime="${esc(x.createdAt)}">${esc(timeText(x.createdAt))}</time></span></a></li>`).join('')}</ul>`;
  },
};

// Approved requests move an invoice's due date in the evidence; the record keeps the original (QA test data note).
function dueChange(i) {
  const moved = S.cases.filter(x => x.invoiceId === i.id && x.outcome === 'approve' && x.approvedDueDate).sort((a, b) => a.createdAt.localeCompare(b.createdAt)).pop();
  return moved ? `<span class="hint-inline">Extended to ${esc(dateText(moved.approvedDueDate))} by an approved request</span>` : '';
}

// Correct is always possible; Remove only for hand-entered records with nothing depending on them. Otherwise say why.
function recordActions(kind, rec) {
  const imported = [rec.origin?.kind, rec.setBy?.kind].includes('file');
  const allocated = (kind === 'invoices' && R.ix.byInvoice.has(rec.id)) || (kind === 'payments' && R.ix.byPayment.has(rec.id));
  const why = imported ? 'From an import: revert that import instead' : allocated ? 'Has allocations: remove those first' : '';
  return `<button type="button" class="btn small" data-act="correct-${kind}" data-id="${esc(rec.id)}">Correct<span class="visually-hidden"> ${esc(rec.reference || dateText(rec.receivedDate))}</span></button>${why
    ? `<span class="hint-inline">${esc(why)}${imported && (rec.setBy?.batchId || rec.origin?.batchId) ? ` <a href="#/imports/${esc(rec.setBy?.batchId || rec.origin?.batchId)}">Open the import</a>` : ''}</span>`
    : `<button type="button" class="btn small danger" data-act="remove" data-kind="${kind}" data-id="${esc(rec.id)}">Remove<span class="visually-hidden"> ${esc(rec.reference || dateText(rec.receivedDate))}</span></button>`}`;
}

function statementHtml(s, onlyFor) {
  const scope = s.customers === 'all' ? 'All customers' : s.customers.map(customerName).join(', ');
  const broken = customersActive().filter(c => !onlyFor || c.id === onlyFor).flatMap(c => ['invoices', 'payments'].flatMap(kind =>
    (viewOf(c.id)?.coverage?.[kind].contradicted || []).filter(x => x.coverageId === s.id).map(x => ({ customer: c.name, text: changesText(x) }))));
  return `<li><p><b>${esc(s.recordTypes.map(t => t === 'payments' ? 'Payments received' : 'Invoices').join(' and '))}</b> complete from ${esc(dateText(s.from))} to ${esc(dateText(s.to))}, for ${esc(scope)}.</p>
    <p class="hint">How the owner knows: ${esc(s.sourceLabel)}. Confirmed by ${esc(ROLE_WORD[s.confirmedRole] || 'the owner')}, ${stamp(s.confirmedAt)}${s.basis === 'export' ? '. Came with an import' : ''}.</p>
    ${broken.map(x => `<p class="callout warn small">No longer holds for ${esc(x.customer)}: ${esc(x.text)}.</p>`).join('')}
    ${isOwner() && s.basis !== 'export' ? `<button type="button" class="btn small" data-act="retire-coverage" data-id="${esc(s.id)}">Retire</button>` : ''}</li>`;
}

function noteHtml(n) {
  const about = n.scope === 'business' ? 'Whole business' : customerName(n.scope);
  const who = n.status === 'confirmed' ? 'Confirmed by the owner' : `Draft by ${n.origin === 'owner' ? 'the owner' : n.origin === 'staff' ? 'staff' : esc(n.origin || 'staff')}, waiting for the owner`;
  return `<li class="note ${n.status}"><p>${esc(n.text)}</p><p class="hint">${esc(about)}. ${n.kind === 'rule' ? 'A rule staff should follow (the system doesn\'t enforce it)' : 'Context to know'}. ${who}.</p>
    <div class="row">${isOwner() && n.status === 'draft' ? `<button type="button" class="btn small primary" data-act="confirm-note" data-id="${esc(n.id)}">Confirm</button>` : ''}
    ${isOwner() || n.status === 'draft' ? `<button type="button" class="btn small" data-act="retire-note" data-id="${esc(n.id)}">Retire</button>` : ''}</div></li>`;
}

// ---------------------------------------------------------------- completeness statements (all customers)

PAGES.completeness = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('completeness');
  await loadRecords();
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  const statements = (R.data.coverage || []).filter(isActive);
  const customers = customersActive();
  main.innerHTML = `${pageHead({ back: { href: '#/customers', label: 'Customers' }, title: 'Completeness statements',
      lede: 'The owner\'s statements that every record of a type is in the records for a period. They make exact amounts possible, and stop holding for a customer when a record enters or leaves their period afterwards.',
      actions: isOwner() ? '<button type="button" class="btn primary" data-act="coverage">Confirm completeness</button>' : '' })}
    ${isOwner() ? '' : '<p class="callout">Only the owner confirms or retires completeness statements. Staff can see them here.</p>'}
    <div class="table-wrap"><table class="rtable"><caption>Confirmed complete to, per customer</caption><thead><tr><th scope="col">Customer</th><th scope="col">Invoices</th><th scope="col">Payments received</th></tr></thead><tbody>
      ${customers.map(c => { const v = viewOf(c.id)?.coverage; const cell = k => v?.[k]?.completeTo ? esc(dateText(v[k].completeTo)) : '<span class="muted">Not confirmed</span>';
        return `<tr><th scope="row" data-label="Customer"><a href="#/customers/${esc(c.id)}/balance">${esc(c.name)}</a></th><td data-label="Invoices">${cell('invoices')}</td><td data-label="Payments received">${cell('payments')}</td></tr>`; }).join('')}
    </tbody></table></div>
    <h2>Statements</h2>${statements.length ? `<ul class="statements">${statements.map(s => statementHtml(s)).join('')}</ul>` : '<p class="empty">No completeness statements yet.</p>'}`;
  bindActions(main);
};

// ---------------------------------------------------------------- dialogs

const customerOptions = () => customersActive().map(c => ({ value: c.id, label: `${c.name} (${c.displayCode})` }));
const reasonField = (name = 'reason', label = 'Reason for the correction') => field({ name, label, hint: 'The earlier values are kept in the history.', attrs: 'required autocomplete="off"' });
const fixedCustomer = c => `<p class="fixed"><span>Customer</span><b>${esc(c.name)}</b> <span class="code">${esc(c.displayCode)}</span></p>`;
const inclusionQuestion = customerId => {
  const ob = openingOf(customerId);
  if (!ob) return '';
  return radios({ name: 'inclusion', legend: `If it is dated on or before ${dateText(ob.asOf)}: is it already part of the opening balance?`, value: 'unsure',
    hint: 'Records dated after the opening balance are new activity, and this answer is ignored for them.',
    options: [{ value: 'included', label: 'Yes, it\'s part of it' }, { value: 'missed', label: 'No, it was missed' }, { value: 'unsure', label: 'Not sure', note: 'It isn\'t counted either way until someone answers.' }] });
};
const fval = (form, name) => form.elements[name]?.value?.trim() ?? '';

const DIALOGS = {
  // name: prefilled (the desk's prepared customer); added(record): what happens after, instead of opening the new customer
  'add-customer'({ name = '', added } = {}) {
    openDialog({ key: 'customer:new' + (name ? ':' + name : ''), title: 'Add customer', body: field({ name: 'name', label: 'Customer name', value: name, attrs: 'required autocomplete="off"', hint: 'As it appears on their invoices. Similar names are checked when you import.' }),
      submitLabel: 'Add customer', submit: async form => {
        if (!fval(form, 'name')) { showErrors(form, { field: 'name', message: 'Enter the customer\'s name.' }); return false; }
        const result = await dialogAction(form, '/api/records/customers', { name: fval(form, 'name') }, null, 'Customer added');
        if (result.error) return false;
        S.afterDialog = added ? () => added(result.record) : () => { location.hash = '#/customers/' + result.record.id; };
        return true;
      } });
  },
  'correct-customer'({ id }) {
    const c = R.ix.customer.get(id);
    openDialog({ key: 'customer:' + id, title: 'Correct the name of ' + c.name, body: field({ name: 'name', label: 'Customer name', value: c.name, attrs: 'required' }) + reasonField(),
      submitLabel: 'Save correction', submit: async form => {
        const result = await dialogAction(form, '/api/records/customers/' + id, { name: fval(form, 'name'), reason: fval(form, 'reason') }, null, 'Name corrected');
        if (result.error) return false;
        S.afterDialog = afterChange; return true;
      } });
  },
  'add-invoice'({ customer }) { invoiceDialog(R.ix.customer.get(customer)); },
  'correct-invoices'({ id }) { const i = R.ix.invoice.get(id); invoiceDialog(R.ix.customer.get(i.customerId), i); },
  'add-payment'({ customer }) { paymentDialog(R.ix.customer.get(customer)); },
  'correct-payments'({ id }) { const p = R.ix.payment.get(id); paymentDialog(R.ix.customer.get(p.customerId), p); },
  opening({ customer, id }) { openingDialog(R.ix.customer.get(customer), id ? (R.data.openingBalances || []).find(o => o.id === id) : null); },
  allocate({ id }) {
    const p = R.ix.payment.get(id);
    const c = R.ix.customer.get(p.customerId);
    const open = (R.ix.invoicesOf.get(p.customerId) || []).filter(i => R.data.positions?.invoices?.[i.id]?.status !== 'settled');
    const left = { ...p.amount, minorUnits: String(leftOn(p)) };
    openDialog({ key: 'allocate:' + id, title: 'Allocate a payment', intro: `${esc(money(p.amount))} received ${esc(dateText(p.receivedDate))}${p.reference ? ' (' + esc(p.reference) + ')' : ''}. ${esc(money(left))} is not allocated yet.`,
      body: fixedCustomer(c) + (open.length ? selectField({ name: 'invoiceId', label: 'Invoice of this customer', options: open.map(i => ({ value: i.id, label: `${i.reference}${i.total ? ', ' + money(i.total) : ''}${i.issueDate ? ', issued ' + dateText(i.issueDate, false) : ''}` })), placeholder: 'Choose an invoice', hint: 'Only this customer\'s open invoices. A payment never moves to another customer\'s invoice.' })
        + field({ name: 'amount', label: 'Amount to allocate', value: plainAmount(left), attrs: 'inputmode="decimal" required', hint: 'The rest of the payment stays not allocated.' })
        : `<p class="callout">${esc(c.name)} has no open invoice to allocate to.</p>`),
      submitLabel: 'Allocate', noSubmit: !open.length, submit: async form => {
        if (!fval(form, 'invoiceId')) { showErrors(form, { field: 'invoiceId', message: 'Choose the invoice this money is for.' }); return false; }
        const result = await dialogAction(form, '/api/records/allocations', { paymentId: id, allocations: [{ invoiceId: fval(form, 'invoiceId'), amount: fval(form, 'amount') }] }, null, 'Allocated');
        if (result.error) return false;
        S.afterDialog = afterChange; return true;
      } });
  },
  unrelated({ id }) {
    const p = R.ix.payment.get(id);
    const marked = !!p.notForOpenInvoices;
    openDialog({ key: 'unrelated:' + id, title: marked ? 'Undo "not for an open invoice"' : 'Mark as not for an open invoice',
      intro: marked ? `Recorded as not for any open invoice: ${esc(p.notForOpenInvoices.reason)}.` : 'Only if the money not allocated is not for any open invoice, for example a deposit for a future order. An exact amount still owed needs every payment to be allocated or marked like this.',
      body: field({ name: 'reason', label: 'Reason', attrs: 'required autocomplete="off"' }), submitLabel: marked ? 'Undo' : 'Mark it', submit: async form => {
        const result = await dialogAction(form, `/api/records/payments/${id}/unrelated`, { unrelated: !marked, reason: fval(form, 'reason') }, null, 'Saved');
        if (result.error) return false;
        S.afterDialog = afterChange; return true;
      } });
  },
  remove({ kind, id }) { removeDialog(kind, id); },
  coverage({ customers }) { coverageDialog(customers ? customers.split(',') : []); },
  'retire-coverage'({ id }) {
    openDialog({ key: 'retire-cov:' + id, title: 'Retire a completeness statement', intro: 'Retiring it means it no longer counts. Amounts that relied on it stop being exact.',
      body: field({ name: 'reason', label: 'Why is it no longer true?', attrs: 'required autocomplete="off"' }), submitLabel: 'Retire statement', danger: true, submit: async form => {
        const result = await dialogAction(form, `/api/records/coverage/${id}/retire`, { reason: fval(form, 'reason') }, null, 'Statement retired');
        if (result.error) return false;
        S.afterDialog = afterChange; return true;
      } });
  },
  'add-note'({ scope }) { noteDialog(scope); },
  'retire-note'({ id }) {
    openDialog({ key: 'retire-note:' + id, title: 'Retire a note', intro: 'A retired note is kept in the history and no longer shown to the owner in requests.',
      body: field({ name: 'reason', label: 'Why retire it?', attrs: 'required autocomplete="off"' }), submitLabel: 'Retire note', danger: true, submit: async form => {
        const result = await dialogAction(form, `/api/records/notes/${id}/retire`, { reason: fval(form, 'reason') }, null, 'Note retired');
        if (result.error) return false;
        S.afterDialog = afterChange; return true;
      } });
  },
};

function invoiceDialog(c, i) {
  const asOf = R.setup.asOfDate;
  const body = fixedCustomer(c)
    + (i ? `<p class="fixed"><span>Invoice</span><b>${esc(i.reference)}</b></p>` : field({ name: 'reference', label: 'Invoice number', attrs: 'required autocomplete="off"', hint: 'Another customer may use the same number. Staff then choose the customer when a request mentions it.' }))
    + `<div class="two">${field({ name: 'issueDate', label: 'Invoice date', type: 'date', value: i?.issueDate || '', attrs: 'required' })}
       ${field({ name: 'total', label: 'Invoice amount', value: plainAmount(i?.total), attrs: 'inputmode="decimal" required', hint: 'Digits only, for example 1200.50.' })}</div>
       ${field({ name: 'dueDate', label: 'Due date', type: 'date', value: i?.originalDueDate || '', optional: true, hint: 'Recommended. Without it a request can\'t say how long the extension is.' })}
       <fieldset class="group-box"><legend>Amount still owed <span class="opt">(optional)</span></legend>
       <p class="hint">Only if a source states what is still owed on it. Leave both empty otherwise: an invoice amount alone doesn't say what is still owed.</p>
       <div class="two">${field({ name: 'stillOwed', label: 'Amount still owed', value: plainAmount(i?.outstandingAmount), attrs: 'inputmode="decimal"' })}
       ${field({ name: 'stillOwedAsOf', label: 'Correct as of', type: 'date', value: i?.outstandingAsOf || '', attrs: `max="${esc(asOf)}"`, hint: 'Needed with an amount. Requests then say "stated as of" this date.' })}</div></fieldset>`
    + (i ? reasonField() : inclusionQuestion(c.id));
  openDialog({ key: i ? 'invoice:' + i.id : 'invoice:new:' + c.id, title: i ? `Correct invoice ${i.reference}` : `Add invoice for ${c.name}`, body, wide: true,
    submitLabel: i ? 'Save correction' : 'Add invoice', submit: async form => {
      if (!i && !fval(form, 'reference')) { showErrors(form, { field: 'reference', message: 'Enter the invoice number.' }); return false; }
      if (!fval(form, 'issueDate')) { showErrors(form, { field: 'issueDate', message: 'Enter the invoice date.' }); return false; }
      if (!fval(form, 'total')) { showErrors(form, { field: 'total', message: 'Enter the invoice amount.' }); return false; }
      if (fval(form, 'stillOwed') && !fval(form, 'stillOwedAsOf')) { showErrors(form, { field: 'stillOwedAsOf', message: 'Enter the date the amount still owed was correct.' }); return false; }
      const body = { issueDate: fval(form, 'issueDate'), total: fval(form, 'total'), dueDate: fval(form, 'dueDate') || null, stillOwed: fval(form, 'stillOwed') || null,
        stillOwedAsOf: fval(form, 'stillOwed') ? fval(form, 'stillOwedAsOf') : null, ...(form.elements.inclusion && !i ? { inclusion: form.elements.inclusion.value } : {}) };
      const result = i ? await dialogAction(form, '/api/records/invoices/' + i.id, { ...body, reason: fval(form, 'reason') }, null, `Invoice ${i.reference} corrected`)
        : await dialogAction(form, '/api/records/invoices', { ...body, customerId: c.id, reference: fval(form, 'reference') }, null, `Invoice ${fval(form, 'reference')} added for ${c.name}`);
      if (result.error) return false;
      S.afterDialog = afterChange; return true;
    } });
}

function paymentDialog(c, p, duplicate) {
  const body = fixedCustomer(c)
    + (p ? '' : radios({ name: 'kind', legend: 'This is', value: duplicate?.kind || 'payment', options: [{ value: 'payment', label: 'Money received' }, { value: 'credit', label: 'A credit held for the customer', note: 'For example a credit note, or a prepayment carried in the opening balance.' }] }))
    + `<div class="two">${field({ name: 'receivedDate', label: 'Date received', type: 'date', value: p?.receivedDate || duplicate?.receivedDate || '', attrs: `max="${esc(R.setup.asOfDate)}" required`, hint: `On or before the business date, ${esc(dateText(R.setup.asOfDate))}.` })}
       ${field({ name: 'amount', label: 'Amount', value: p ? plainAmount(p.amount) : duplicate?.amount || '', attrs: 'inputmode="decimal" required' })}</div>
       ${field({ name: 'reference', label: 'Reference', value: p?.reference || duplicate?.reference || '', optional: true, attrs: 'autocomplete="off"', hint: 'The bank or remittance reference, if there is one.' })}`
    + (duplicate ? `<div class="callout warn"><p>${esc(duplicate.message)}</p><label class="tick"><input type="checkbox" name="confirmDistinct"> This is a different payment</label></div>` : '')
    + (p ? reasonField() : inclusionQuestion(c.id));
  openDialog({ key: p ? 'payment:' + p.id : 'payment:new:' + c.id, title: p ? `Correct the ${p.kind === 'credit' ? 'credit' : 'payment'}` : `Record a payment or credit for ${c.name}`, body, wide: true,
    submitLabel: p ? 'Save correction' : 'Record it', submit: async form => {
      if (!fval(form, 'receivedDate')) { showErrors(form, { field: 'receivedDate', message: 'Enter the date the money was received.' }); return false; }
      if (!fval(form, 'amount')) { showErrors(form, { field: 'amount', message: 'Enter the amount.' }); return false; }
      const body = { receivedDate: fval(form, 'receivedDate'), amount: fval(form, 'amount'), reference: fval(form, 'reference') || null, ...(form.elements.confirmDistinct?.checked ? { confirmDistinct: true } : {}),
        ...(p ? {} : { kind: form.elements.kind?.value || 'payment' }), ...(form.elements.inclusion && !p ? { inclusion: form.elements.inclusion.value } : {}) };
      const result = p ? await dialogAction(form, '/api/records/payments/' + p.id, { ...body, reason: fval(form, 'reason') }, null, 'Payment corrected')
        : await dialogAction(form, '/api/records/payments', { ...body, customerId: c.id }, null, (body.kind === 'credit' ? 'Credit' : 'Payment') + ' recorded for ' + c.name);
      if (result.error?.code === 'POSSIBLE_DUPLICATE') { S.afterDialog = () => paymentDialog(c, p, { ...body, message: result.error.message }); return true; }
      if (result.error) return false;
      S.afterDialog = afterChange; return true;
    } });
}

function openingDialog(c, ob) {
  const credit = ob && BigInt(ob.amount.minorUnits) < 0n;
  const body = fixedCustomer(c) + `<p class="hint">What ${esc(c.name)} owed, or held in credit, as at one date: everything up to that date in one figure. Invoices and payments dated on or before it are then asked about: already part of it, missed from it, or not sure.</p>
    <div class="two">${field({ name: 'asOf', label: 'As at', type: 'date', value: ob?.asOf || '', attrs: `max="${esc(R.setup.asOfDate)}" required` })}
    ${field({ name: 'amount', label: 'Amount', value: ob ? plainAmount(abs(ob.amount)) : '', attrs: 'inputmode="decimal" required' })}</div>
    ${radios({ name: 'direction', legend: 'This amount is', value: credit ? 'credit' : 'owed', options: [{ value: 'owed', label: 'Owed by the customer' }, { value: 'credit', label: 'Held in credit for them' }] })}
    ${selectField({ name: 'credits', label: 'Credits or prepayments in this figure', value: creditsOf(ob) || '', placeholder: 'Not stated', hint: 'A credit could settle a later invoice, so amounts are only exact once this is said.',
      options: [{ value: 'none', label: 'It includes none' }, { value: 'recorded', label: 'Every one is recorded here, dated on or before the as-at date' }] })}
    ${field({ name: 'sourceLabel', label: 'Where this figure comes from', value: ob?.sourceLabel || '', attrs: 'required autocomplete="off"', hint: 'For example: the accountant\'s balance list. It is shown with the figure everywhere, with who entered it.' })}
    ${ob ? reasonField() : ''}`;
  openDialog({ key: ob ? 'opening:' + ob.id : 'opening:new:' + c.id, title: ob ? 'Correct the opening balance' : 'Add an opening balance', body, wide: true,
    submitLabel: ob ? 'Save correction' : 'Save opening balance', submit: async form => {
      if (!fval(form, 'asOf')) { showErrors(form, { field: 'asOf', message: 'Enter the date the balance was correct.' }); return false; }
      if (!fval(form, 'amount')) { showErrors(form, { field: 'amount', message: 'Enter the amount, or 0.00.' }); return false; }
      if (!fval(form, 'sourceLabel')) { showErrors(form, { field: 'sourceLabel', message: 'Say where this figure comes from.' }); return false; }
      const body = { asOf: fval(form, 'asOf'), amount: fval(form, 'amount'), direction: form.elements.direction.value, sourceLabel: fval(form, 'sourceLabel'), credits: fval(form, 'credits') || null };
      const result = ob ? await dialogAction(form, '/api/records/openingBalances/' + ob.id, { ...body, reason: fval(form, 'reason') }, null, 'Opening balance corrected')
        : await dialogAction(form, '/api/records/openingBalances', { ...body, customerId: c.id }, null, 'Opening balance saved');
      if (result.error) return false;
      S.afterDialog = afterChange; return true;
    } });
}

function coverageDialog(preset) {
  const customers = customersActive();
  const body = `${radios({ name: 'scope', legend: 'For', value: preset.length ? 'some' : '', options: [{ value: 'some', label: 'Only the customers ticked below' }, { value: 'all', label: 'All customers', note: 'Including customers added later. On a shared practice instance, use only your own customers.' }] })}
    <fieldset class="ticks"><legend>Customers</legend>${customers.map(c => `<label class="tick"><input type="checkbox" name="customer" value="${esc(c.id)}"${preset.includes(c.id) ? ' checked' : ''}> ${esc(c.name)} <span class="code">${esc(c.displayCode)}</span></label>`).join('')}
      <p class="error" data-error-for="customers" role="alert"></p></fieldset>
    <fieldset class="ticks"><legend>Which records</legend><label class="tick"><input type="checkbox" name="type" value="invoices"> Invoices</label><label class="tick"><input type="checkbox" name="type" value="payments"> Payments received</label>
      <p class="error" data-error-for="recordTypes" role="alert"></p></fieldset>
    <div class="two">${field({ name: 'from', label: 'From', type: 'date', attrs: `max="${esc(R.setup.asOfDate)}" required`, hint: 'For an exact amount: the day after the customer\'s opening balance.' })}
      ${field({ name: 'to', label: 'To', type: 'date', value: R.setup.asOfDate, attrs: `max="${esc(R.setup.asOfDate)}" required` })}</div>
    ${field({ name: 'sourceLabel', label: 'How you know', attrs: 'required autocomplete="off"', hint: 'For example: checked against the bank statements.' })}
    <label class="tick confirm"><input type="checkbox" name="confirm"> Every record of these types, for these customers, in this period is in the records. For payments, this also means there are no credit notes or other adjustments in the period, which this version can't record.</label>
    <p class="error" data-error-for="confirm" role="alert"></p>`;
  openDialog({ key: 'coverage:' + preset.join(','), title: 'Confirm records are complete', intro: 'A statement about the business, confirmed by the owner. It stops holding for a customer if a record enters or leaves their period afterwards.',
    body, wide: true, submitLabel: 'Confirm completeness', submit: async form => {
      const all = form.elements.scope.value === 'all';
      if (!form.elements.scope.value) { showErrors(form, { field: 'scope', message: 'Choose all customers or only the ones ticked.' }); return false; }
      const ticked = $$('input[name=customer]:checked', form).map(i => i.value);
      if (!all && !ticked.length) { showErrors(form, { field: 'customers', message: 'Tick at least one customer.' }); return false; }
      const types = $$('input[name=type]:checked', form).map(i => i.value);
      if (!types.length) { showErrors(form, { field: 'recordTypes', message: 'Tick invoices, payments received, or both.' }); return false; }
      if (!form.elements.confirm.checked) { showErrors(form, { field: 'confirm', message: 'Tick the statement to confirm it.' }); return false; }
      const result = await dialogAction(form, '/api/records/coverage', { customers: all ? 'all' : ticked, recordTypes: types, from: fval(form, 'from'), to: fval(form, 'to'), sourceLabel: fval(form, 'sourceLabel'), confirm: true }, null, 'Completeness confirmed');
      if (result.error) return false;
      S.afterDialog = afterChange; return true;
    } });
}

// Removal: say what it affects before anything happens. The server checks again and may refuse or ask for review.
function removeDialog(kind, id, review) {
  const rec = kind === 'customers' ? R.ix.customer.get(id) : kind === 'allocations' ? R.ix.allocation.get(id) : kind === 'openingBalances' ? (R.data.openingBalances || []).find(o => o.id === id)
    : (kind === 'invoices' ? R.ix.invoice : R.ix.payment).get(id);
  const what = kind === 'customers' ? `customer ${rec.name}` : kind === 'invoices' ? `invoice ${rec.reference}` : kind === 'payments' ? `the ${rec.kind === 'credit' ? 'credit' : 'payment'} of ${money(rec.amount)} received ${dateText(rec.receivedDate)}`
    : kind === 'allocations' ? `the allocation of ${money(rec.amount)} to invoice ${R.ix.invoice.get(rec.invoiceId)?.reference}` : `the opening balance of ${customerName(rec.customerId)}`;
  const cases = list => list.map(cid => { const x = S.cases.find(y => y.id === cid); return `<li><a href="#/case/${esc(cid)}">${esc(x ? (x.customerName || 'Request') + ', invoice ' + (x.invoiceReference || '') : 'Request ' + cid.slice(-6))}</a></li>`; }).join('');
  const impact = review?.impact || {};
  const intro = `Nothing is deleted: ${esc(what)} is marked removed and kept in the history, and the agent stops using it.${kind === 'openingBalances' ? ' Amounts for this customer stop being exact.' : ''}`;
  openDialog({ key: 'remove:' + kind + ':' + id, title: `Remove ${what}`, intro, danger: true, submitLabel: review ? 'Remove anyway' : 'Remove',
    body: (review ? `<div class="callout warn" role="alert"><p><b>Check before removing.</b> ${esc(review.message)}</p>
        ${impact.pendingCases?.length ? `<p>Waiting for the owner, prepared again:</p><ul>${cases(impact.pendingCases)}</ul>` : ''}
        ${impact.decidedCases?.length ? `<p>Decided, keep their decision and get a note:</p><ul>${cases(impact.decidedCases)}</ul>` : ''}</div>` : '')
      + field({ name: 'reason', label: 'Why remove it?', value: review?.reason || '', attrs: 'required autocomplete="off"' }),
    submit: async form => {
      if (!fval(form, 'reason')) { showErrors(form, { field: 'reason', message: 'Say why it is being removed.' }); return false; }
      const result = await dialogAction(form, `/api/records/${kind}/${id}/remove`, { reason: fval(form, 'reason'), ...(review ? { confirm: true } : {}) }, 'remove:' + kind + ':' + id + ':' + !!review, 'Removed');
      if (result.error?.code === 'REVIEW_REQUIRED') { S.afterDialog = () => removeDialog(kind, id, { message: result.error.message, impact: result.error.impact || {}, reason: fval(form, 'reason') }); return true; }
      if (result.error?.code === 'REMOVE_BLOCKED') {
        const parts = Object.entries(result.error.impact || {}).filter(([, x]) => x && x.length).map(([k, x]) => `${{ invoices: 'Invoices', notes: 'Notes', payments: 'Payments', openingBalances: 'An opening balance', allocations: 'Allocations' }[k] || k}${Array.isArray(x) && typeof x[0] === 'string' && !x[0].includes('_') ? ': ' + x.join(', ') : ''}`);
        showErrors(form, { message: result.error.message + (parts.length ? ' Still there: ' + parts.join('; ') + '.' : '') });
        return false;
      }
      if (result.error) return false;
      S.afterDialog = kind === 'customers' ? () => { location.hash = '#/customers'; } : afterChange; return true;
    } });
}
