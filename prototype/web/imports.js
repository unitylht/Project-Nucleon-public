'use strict';
// Imports: CSV invoice lists and payment lists. A file becomes a draft; you check its columns, customers and every row with its
// values, then apply it, keep the draft for later, or discard it. An applied import can be reverted after its impact is shown.
// Uses core.js and customers.js helpers.

const ROW = { new: 'New', unchanged: 'Already recorded', updated: 'Update', conflict: 'Conflict', rejected: 'Rejected', unresolved: 'Unknown customer', leftOut: 'Left out', review: 'Needs a decision' };
const ROW_CHIP = { new: 'done', unchanged: 'wait', updated: 'busy', conflict: 'need', rejected: 'fail', unresolved: 'need', leftOut: 'wait', review: 'need' };
const FIELD = { issueDate: 'invoice date', total: 'amount', originalDueDate: 'due date', outstandingAmount: 'amount still owed', outstandingAsOf: 'date the amount was stated', receivedDate: 'date received', amount: 'amount' };
const fieldWords = list => list.map(f => FIELD[f] || f).join(', ');
const SHAPE = { invoices: 'Invoice list', payments: 'Payments received' };
const STATUS_WORDS = { preview: 'Draft, not applied', applied: 'Applied', reverted: 'Reverted', discarded: 'Discarded, never applied' };
const STATUS_CHIP = { preview: 'need', applied: 'done', reverted: 'wait', discarded: 'wait' };
const byRole = id => id === AGENT_ID ? 'AI Agent' : ({ staff: 'staff', owner: 'the owner' }[String(id || '').split('_')[0]] || 'a person');
const rowsText = n => n === 1 ? '1 row' : n + ' rows';

PAGES.imports = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('imports');
  await loadRecords();
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  const drafts = R.imports.filter(b => b.status === 'preview');
  const history = R.imports.filter(b => ['applied', 'reverted'].includes(b.status));
  const discarded = R.imports.filter(b => b.status === 'discarded');
  const counts = b => Object.entries(b.counts).filter(([, n]) => n).map(([k, n]) => `${ROW[k]} ${n}`).join(', ') || 'No rows';
  main.innerHTML = `${pageHead({ title: 'Imports', lede: 'Bring in an invoice list or a list of payments received from a CSV file. You check every row before anything changes, and an applied import can be reverted.',
      actions: '<a class="btn primary" href="#/imports/new">Import a CSV file</a>' })}
    ${drafts.length ? `<section aria-labelledby="drafts-title"><h2 id="drafts-title">Drafts not applied <span class="n">${drafts.length}</span></h2>
      <p class="hint">Nothing in a draft is in the records. Resume one to check and apply it, or discard it.</p>
      <div class="table-wrap"><table class="rtable"><thead><tr><th scope="col">File</th><th scope="col">Uploaded</th><th scope="col">Rows</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead><tbody>
      ${drafts.map(b => `<tr><th scope="row" data-label="File">${esc(b.fileName)}<span class="code">${esc(SHAPE[b.shape])}, ${esc(b.sourceLabel)}</span></th>
        <td data-label="Uploaded">${stamp(b.createdAt)}<span class="hint-inline">by ${esc(byRole(b.createdBy))}</span></td><td data-label="Rows">${esc(counts(b))}</td>
        <td data-label="Actions" class="actions"><a class="btn small primary" href="#/imports/${esc(b.id)}">Resume</a><button type="button" class="btn small danger" data-discard="${esc(b.id)}" data-name="${esc(b.fileName)}">Discard</button></td></tr>`).join('')}
      </tbody></table></div></section>` : ''}
    <section aria-labelledby="hist-title"><h2 id="hist-title">Import history</h2>
      ${history.length ? `<div class="table-wrap"><table class="rtable"><thead><tr><th scope="col">File</th><th scope="col">Applied</th><th scope="col">Rows</th><th scope="col">Status</th><th scope="col"><span class="visually-hidden">Open</span></th></tr></thead><tbody>
      ${history.map(b => `<tr><th scope="row" data-label="File">${esc(b.fileName)}<span class="code">${esc(SHAPE[b.shape])}, ${esc(b.sourceLabel)}${b.asOf ? ', amounts as of ' + esc(dateText(b.asOf, false)) : ''}</span></th>
        <td data-label="Applied">${stamp(b.appliedAt)}<span class="hint-inline">by ${esc(byRole(b.appliedBy))}</span></td><td data-label="Rows">${esc(counts(b))}</td>
        <td data-label="Status"><span class="chip ${STATUS_CHIP[b.status]}">${esc(STATUS_WORDS[b.status])}</span>${b.status === 'reverted' ? `<span class="hint-inline">${esc(b.revertReason || '')}</span>` : ''}</td>
        <td data-label="Open" class="actions"><a class="btn small" href="#/imports/${esc(b.id)}">${b.status === 'applied' ? 'View or revert' : 'View'}</a></td></tr>`).join('')}
      </tbody></table></div>` : '<p class="empty">Nothing imported yet.</p>'}
      ${discarded.length ? `<details class="more-list"><summary>${plural(discarded.length, 'discarded draft', 'discarded drafts')}</summary><ul>${discarded.map(b => `<li>${esc(b.fileName)} (${esc(b.sourceLabel)}), discarded ${stamp(b.discardedAt)} by ${esc(byRole(b.discardedBy))}. Never applied.</li>`).join('')}</ul></details>` : ''}
    </section>`;
  $$('[data-discard]', main).forEach(b => { b.onclick = () => discardDialog(b.dataset.discard, b.dataset.name); });
};

function discardDialog(id, name) {
  openDialog({ title: `Discard the draft ${name}`, intro: 'Nothing from it is in the records, and nothing changes. A discarded draft can\'t be applied later; upload the file again if you need it.',
    body: '', submitLabel: 'Discard draft', danger: true, submit: async form => {
      const result = await dialogAction(form, `/api/imports/${id}/discard`, {}, 'discard:' + id, 'Draft discarded');
      if (result.error) return false;
      S.afterDialog = () => { if (readRoute().name === 'imports') route(); else location.hash = '#/imports'; };
      return true;
    } });
}

// ---------------------------------------------------------------- a new import

PAGES['import-new'] = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('the import form');
  await loadRecords();
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  main.innerHTML = `${pageHead({ back: { href: '#/imports', label: 'Imports' }, title: 'Import a CSV file', lede: 'Choose the file. Next you check its columns, customers and every row. Nothing changes in the records until you apply it.' })}
    <form id="upload" class="narrow" novalidate>
      ${radios({ name: 'shape', legend: 'This file lists', value: r.q.shape || '', options: [
        { value: 'invoices', label: 'Invoices', note: 'One row per invoice: customer, invoice number, invoice date and amount. Optionally a due date and the amount still owed.' },
        { value: 'payments', label: 'Payments received', note: 'One row per payment: customer, date and amount. Optionally a reference and the invoice it pays, for the same customer only.' }] })}
      ${field({ name: 'sourceLabel', label: 'Where is this file from?', attrs: 'required autocomplete="off"', hint: 'For example: Accounts spreadsheet. Use the same name for later exports from the same place, so rows already imported are recognised.' })}
      ${field({ name: 'file', label: 'CSV file', type: 'file', attrs: 'accept=".csv,text/csv"', hint: 'Save a spreadsheet as CSV first. Ledgers, opening balances and XLSX files aren\'t imported in this version.' })}
      <details class="paste"><summary>Paste the rows instead</summary>${field({ name: 'csvText', label: 'Rows, including the heading row', type: 'textarea', rows: 6 })}</details>
      ${formError()}
      <div class="row"><button class="btn primary" type="submit">Upload and check</button><a class="btn" href="#/imports">Cancel</a></div>
    </form>`;
  const form = $('#upload');
  form.onsubmit = event => {
    event.preventDefault();
    busy($('[type=submit]', form), async () => {
      clearErrors(form);
      if (!form.elements.shape.value) return showErrors(form, { field: 'shape', message: 'Choose whether the file lists invoices or payments received.' });
      if (!fval(form, 'sourceLabel')) return showErrors(form, { field: 'sourceLabel', message: 'Say where the file comes from.' });
      let file;
      try { file = await readFile(form.elements.file); } catch (error) { return showErrors(form, error); }
      const text = file?.text || fval(form, 'csvText');
      if (!text) return showErrors(form, { field: 'file', message: 'Choose a CSV file, or paste the rows.' });
      try {
        const batch = await api('/api/imports', { sourceLabel: fval(form, 'sourceLabel'), fileName: file?.name || 'pasted.csv', csvText: text, shape: form.elements.shape.value }, { key: keyFor('upload:' + text.length + ':' + fval(form, 'sourceLabel')) });
        keyDone('upload:' + text.length + ':' + fval(form, 'sourceLabel'));
        location.hash = '#/imports/' + batch.id;
      } catch (error) { showErrors(form, error); }
    });
  };
};

function readFile(input) {
  return new Promise((resolve, reject) => {
    const file = input.files?.[0];
    if (!file) return resolve(null);
    if (file.size > 2_000_000) return reject(Object.assign(new Error('The file is too large (limit about 2 MB).'), { field: 'file' }));
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, text: String(reader.result) });
    reader.onerror = () => reject(Object.assign(new Error('The file could not be read.'), { field: 'file' }));
    reader.readAsText(file);
  });
}

// ---------------------------------------------------------------- one import: a draft to check, or an applied import

PAGES.import = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('the import');
  const [batch] = await Promise.all([api('/api/imports/' + r.id), loadRecords(), api('/api/requests').then(x => { S.cases = x; }).catch(() => {})]);
  if (!live(seq)) return;
  if (batch.status === 'preview') renderDraft(main, batch, seq);
  else renderApplied(main, batch, seq);
};

// The values a row will write, so they can be checked before applying (QA G2).
function rowValues(b, row) {
  const x = row.values || {};
  if (b.shape === 'payments') return { date: x.receivedDate, amount: x.amount, extra: row.invoiceNumber ? 'Invoice ' + row.invoiceNumber : '' };
  return { date: x.issueDate, amount: x.total, due: x.originalDueDate, owed: x.outstandingAmount, owedAsOf: x.outstandingAsOf };
}

function rowsTable(b, editable) {
  const p = b.preview;
  const res = b.params.resolutions || { customers: {}, conflicts: {} };
  const rows = p.rows;
  const payments = b.shape === 'payments';
  return `<div class="table-wrap"><table class="rtable rows-table"><caption class="visually-hidden">Rows in the file</caption>
    <thead><tr><th scope="col">Row</th><th scope="col">Customer</th><th scope="col">${payments ? 'Reference' : 'Invoice'}</th><th scope="col">${payments ? 'Received' : 'Invoice date'}</th>
      <th scope="col" class="num">Amount</th><th scope="col">${payments ? 'Pays' : 'Due'}</th>${payments ? '' : '<th scope="col">Still owed</th>'}<th scope="col">Result</th></tr></thead>
    <tbody>${rows.map(row => {
      const x = rowValues(b, row);
      const status = row.status === 'unresolved' && row.review ? 'review' : row.status;
      return `<tr class="row-${status}"><th scope="row" data-label="Row">${row.row}</th><td data-label="Customer">${esc(row.customerName)}</td><td data-label="${payments ? 'Reference' : 'Invoice'}">${esc(row.reference || '') || '<span class="muted">None</span>'}</td>
        <td data-label="${payments ? 'Received' : 'Invoice date'}">${x.date ? esc(dateText(x.date)) : '<span class="muted">—</span>'}</td>
        <td data-label="Amount" class="num">${x.amount ? esc(money(x.amount)) : '<span class="muted">—</span>'}</td>
        <td data-label="${payments ? 'Pays' : 'Due'}">${payments ? (row.allocation ? `Allocates ${esc(money(row.allocation.amount))} to ${esc(row.allocation.reference)}${row.allocation.note ? `<span class="hint-inline">${esc(row.allocation.note)}</span>` : ''}` : row.allocationNote ? esc(row.allocationNote) : x.extra ? esc(x.extra) : '<span class="muted">Not allocated</span>') : x.due ? esc(dateText(x.due)) : '<span class="muted">None</span>'}</td>
        ${payments ? '' : `<td data-label="Still owed">${x.owed ? `${esc(money(x.owed))}<span class="hint-inline">as of ${esc(dateText(x.owedAsOf, false))}</span>` : '<span class="muted">Not in the file</span>'}</td>`}
        <td data-label="Result"><span class="chip ${ROW_CHIP[status]}">${esc(ROW[status])}</span>${row.reason && (row.status !== 'unresolved' || row.review) ? `<span class="hint-inline">${esc(row.reason)}</span>` : row.status === 'unresolved' ? '<span class="hint-inline">Choose what this customer is, above.</span>' : ''}${row.status === 'updated' ? `<span class="hint-inline">Adds or refreshes: ${esc(fieldWords(Object.keys(row.updates)))}</span>` : ''}
          ${editable && row.review ? selectField({ name: 'row-' + row.row, id: 'rr-' + row.row, label: `Decision for row ${row.row}`, value: res.rows?.[row.row] || '',
              options: [...(row.review === 'possibleDuplicate' ? [{ value: 'same', label: 'The same payment as recorded' }] : []), { value: 'distinct', label: 'A different payment' }, { value: 'skip', label: 'Leave this row out' }] }) : ''}
          ${editable && row.status === 'conflict' ? `<fieldset class="choices compact"><legend>Differs: ${esc(fieldWords(row.conflictFields))}${row.correctedByPerson ? ' (a person corrected this record)' : ''}</legend>
            <label class="choice"><input type="radio" name="conf-${row.row}" value="keep"${res.conflicts[row.row] === 'keep' ? ' checked' : ''}><span>Keep what's recorded<small>The file's values are rejected. The file does not become a source for what's recorded.</small></span></label>
            <label class="choice"><input type="radio" name="conf-${row.row}" value="take"${res.conflicts[row.row] === 'take' ? ' checked' : ''}><span>Replace with the file</span></label></fieldset>` : ''}</td></tr>`;
    }).join('')}</tbody></table></div>`;
}

function renderDraft(main, b, seq) {
  const p = b.preview;
  const columns = b.columns.map((c, n) => ({ value: n, label: c || 'Column ' + (n + 1) }));
  const owedMapped = b.mapping.stillOwed !== undefined || b.mapping.amountPaid !== undefined;
  const customers = customersActive();
  const res = b.params.resolutions || { customers: {}, conflicts: {} };
  const applyCount = p.counts.new + p.counts.updated + p.counts.conflict;
  main.innerHTML = `${pageHead({ back: { href: '#/imports', label: 'Imports' }, title: 'Check the import: ' + b.fileName,
      lede: `${esc(SHAPE[b.shape])} from "${esc(b.sourceLabel)}", ${rowsText(b.rowCount)}. Uploaded ${stamp(b.createdAt)} by ${esc(byRole(b.createdBy))}. Nothing changes in the records until you apply it.` })}
    <p class="status-line"><span class="chip need">Draft, not applied</span>${b.profileUsed ? ' <span class="hint">Column choices remembered from an earlier import of this layout.</span>' : ''}</p>
    ${b.sameFileAs ? `<p class="callout">This exact file was applied before (${stamp(b.sameFileAs.appliedAt)}). Rows already recorded show as "Already recorded" and add nothing.</p>` : ''}
    <form id="params" novalidate>
      <section class="step" aria-labelledby="s-cols"><h2 id="s-cols"><span class="step-n">1</span> Columns</h2>
        <p class="hint">Which column holds each value. Required ones are marked.</p>
        <div class="mapping">${b.fields.map(f => selectField({ name: 'map-' + f.id, id: 'map-' + f.id, label: f.label + (f.required ? ' (required)' : ''), value: b.mapping[f.id] ?? '', options: columns, placeholder: '— not in this file —' })).join('')}</div>
        <div class="two">${selectField({ name: 'dateOrder', id: 'order', label: 'Dates are written', value: b.params.dateOrder || '', placeholder: 'Work it out from the file', options: [{ value: 'dmy', label: 'day/month/year' }, { value: 'mdy', label: 'month/day/year' }] })}
        ${owedMapped ? field({ name: 'asOf', id: 'asof', label: 'Amounts still owed are as of', type: 'date', value: b.params.asOf || '', attrs: `max="${esc(R.setup.asOfDate)}"`, hint: 'The date this file\'s balances were correct. Required when the file has amounts still owed or paid.' }) : ''}</div>
      </section>
      ${p.customers.length ? `<section class="step" aria-labelledby="s-cust"><h2 id="s-cust"><span class="step-n">2</span> Customers not in the records</h2>
        <p class="hint">Say what each name is. Nothing is matched for you, even when a name is similar.</p>
        ${p.customers.map(c => selectField({ name: 'cust-' + c.key, id: 'cr-' + c.key, label: c.name, value: res.customers[c.key] || '', hint: c.suggestions.length ? 'Similar names already recorded: ' + esc(c.suggestions.join(', ')) : '',
          options: [{ value: 'new', label: 'Create a new customer' }, ...customers.map(x => ({ value: x.id, label: `Same as ${x.name} (${x.displayCode})` })), { value: 'skip', label: 'Leave these rows out' }] })).join('')}
      </section>` : ''}
      <section class="step" aria-labelledby="s-cov"><h2 id="s-cov"><span class="step-n">${p.customers.length ? 3 : 2}</span> Completeness <span class="opt">(optional, owner only)</span></h2>
        ${isOwner() ? `<p class="hint">With this file applied, are the records complete for a period? Without an answer, importing never makes records complete.</p>
          ${radios({ name: 'covScope', legend: 'Complete for a period?', value: b.params.coverage?.customers || '', options: [
            { value: '', label: 'Not sure, or not saying', note: 'Nothing is assumed complete.' },
            { value: 'file', label: 'Yes, for the customers in this file', note: `Every ${b.shape === 'payments' ? 'payment' : 'invoice'} of theirs in the period is then in the records${b.shape === 'payments' ? ', and there are no credit notes or other adjustments in it' : ''}.` },
            { value: 'all', label: 'Yes, for all customers' }] })}
          <div class="two">${field({ name: 'covFrom', id: 'cvf', label: 'From', type: 'date', value: b.params.coverage?.from || '', attrs: `max="${esc(R.setup.asOfDate)}"` })}${field({ name: 'covTo', id: 'cvt', label: 'To', type: 'date', value: b.params.coverage?.to || '', attrs: `max="${esc(R.setup.asOfDate)}"` })}</div>`
          : '<p class="hint">Only the owner can say a file makes the records complete for a period. As staff you can import without it: nothing is then assumed complete.</p>'}
      </section>
      ${formError()}
      <div class="row"><button class="btn" type="submit">Update the rows below</button><span class="hint">Use this after changing anything above.</span></div>
      <section class="step" aria-labelledby="s-rows"><h2 id="s-rows"><span class="step-n">${p.customers.length ? 4 : 3}</span> Check the rows</h2>
        <p class="counts">${Object.entries(p.counts).filter(([, n]) => n).map(([k, n]) => `<span class="chip ${ROW_CHIP[k]}">${esc(ROW[k])}: ${n}</span>`).join(' ') || 'No rows yet.'}</p>
        <p class="hint">Check customer, number, dates and amounts against the file. Rejected rows are never applied; the others can still be.</p>
        ${p.needs.length ? `<div class="callout warn"><p><b>Before applying:</b></p><ul>${p.needs.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div>` : ''}
        ${p.rows.some(x => x.status === 'conflict') ? '<p><button type="button" class="btn small" data-keep-all>Keep what\'s recorded for every conflict</button></p>' : ''}
        ${rowsTable(b, true)}
      </section>
    </form>
    <div class="apply-bar">
      <button class="btn primary" type="button" id="apply"${p.ready ? '' : ' aria-disabled="true"'}>${applyCount ? 'Apply ' + rowsText(applyCount) : 'Apply (nothing new)'}</button>
      <a class="btn" href="#/imports">Keep as a draft and close</a>
      <button class="btn danger" type="button" id="discard">Discard draft</button>
      <p class="hint">${p.ready ? (applyCount ? `Applying adds or updates ${rowsText(applyCount)}. It can be reverted later.` : 'Nothing new to apply. Applying records that these rows were also in this file.') : 'Answer what is listed under "Before applying" first.'}</p>
    </div>`;
  const form = $('#params');
  const keepAll = $('[data-keep-all]', main);
  if (keepAll) keepAll.onclick = () => $$('input[value="keep"]', form).forEach(i => { i.checked = true; });
  form.onsubmit = event => {
    event.preventDefault();
    busy($('[type=submit]', form), async () => {
      try {
        const updated = await api(`/api/imports/${b.id}/mapping`, draftParams(form, b), { key: keyFor('params:' + b.id + ':' + JSON.stringify(draftParams(form, b))) });
        if (!live(seq)) return;
        toast('Rows updated', 'ok');
        renderDraft(main, updated, seq);
        $('#s-rows').scrollIntoView({ block: 'start' });
      } catch (error) { showErrors(form, error); }
    });
  };
  $('#apply').onclick = () => {
    if (!p.ready || !applyCount) {
      if (p.ready) return applyNothing(b, seq);
      toast('Answer what is listed under "Before applying" first.', 'bad');
      return $('#s-rows').scrollIntoView({ block: 'start' });
    }
    applyBatch(b, $('#apply'), seq);
  };
  $('#discard').onclick = () => discardDialog(b.id, b.fileName);
}

function applyNothing(b, seq) {
  openDialog({ title: 'Apply with no new rows?', intro: 'Every row is already recorded. Applying adds nothing; it only notes that these rows were also in this file. You can discard the draft instead.',
    body: '', submitLabel: 'Apply anyway', submit: async () => { await applyBatch(b, null, seq); return true; } });
}

async function applyBatch(b, button, seq) {
  const run = async () => {
    try {
      await api(`/api/imports/${b.id}/apply`, {}, { key: keyFor('apply:' + b.id) });
      keyDone('apply:' + b.id);
      toast('Import applied', 'ok');
      try { await loadSession(S.role); } catch { /* the page reloads anyway */ }
      if (live(seq)) { if (readRoute().id === b.id) route(); else location.hash = '#/imports/' + b.id; }
    } catch (error) {
      if (error.code === 'RECORDS_CHANGED') { toast(error.message, 'bad'); if (live(seq)) renderDraft($('#main'), error.data.batch, seq); return; }
      toast(error.message, 'bad');
    }
  };
  if (button) await busy(button, run); else await run();
}

function draftParams(form, b) {
  const mapping = {};
  b.fields.forEach(f => { const val = form.elements['map-' + f.id].value; if (val !== '') mapping[f.id] = Number(val); });
  const customers = {}, conflicts = {}, rows = {};
  b.preview.customers.forEach(c => { const val = form.elements['cust-' + c.key]?.value; if (val) customers[c.key] = val; });
  b.preview.rows.filter(r => r.status === 'conflict').forEach(r => { const val = form.elements['conf-' + r.row]?.value; if (val) conflicts[r.row] = val; });
  b.preview.rows.forEach(r => { const val = form.elements['row-' + r.row]?.value; if (val) rows[r.row] = val; else if (b.params.resolutions?.rows?.[r.row] && !r.review && r.status !== 'unresolved') rows[r.row] = b.params.resolutions.rows[r.row]; });
  const scope = form.elements.covScope?.value;
  const coverage = scope ? { customers: scope, from: form.elements.covFrom.value, to: form.elements.covTo.value } : null;
  return { mapping, dateOrder: form.elements.dateOrder.value || null, asOf: form.elements.asOf?.value || null, resolutions: { customers, conflicts, rows }, coverage };
}

function renderApplied(main, b, seq) {
  const p = b.preview;
  main.innerHTML = `${pageHead({ back: { href: '#/imports', label: 'Imports' }, title: b.fileName, lede: `${esc(SHAPE[b.shape])} from "${esc(b.sourceLabel)}".` })}
    <p class="status-line"><span class="chip ${STATUS_CHIP[b.status]}">${esc(STATUS_WORDS[b.status])}</span></p>
    <dl class="kv">
      <div><dt>Uploaded</dt><dd>${stamp(b.createdAt)} by ${esc(byRole(b.createdBy))}</dd></div>
      ${b.appliedAt ? `<div><dt>Applied</dt><dd>${stamp(b.appliedAt)} by ${esc(byRole(b.appliedBy))}</dd></div>` : ''}
      ${b.revertedAt ? `<div><dt>Reverted</dt><dd>${stamp(b.revertedAt)} by ${esc(byRole(b.revertedBy))}. Reason: ${esc(b.revertReason || '')}</dd></div>` : ''}
      ${b.discardedAt ? `<div><dt>Discarded</dt><dd>${stamp(b.discardedAt)} by ${esc(byRole(b.discardedBy))}. It was never applied.</dd></div>` : ''}
      ${b.params.asOf ? `<div><dt>Amounts still owed as of</dt><dd>${esc(dateText(b.params.asOf))}</dd></div>` : ''}
      <div><dt>Rows</dt><dd>${Object.entries(p.counts).filter(([, n]) => n).map(([k, n]) => `${esc(ROW[k])} ${n}`).join(', ') || 'None'}</dd></div>
    </dl>
    ${b.status === 'applied' ? `<section class="revert" aria-labelledby="rv-title"><h2 id="rv-title">Revert this import</h2><div id="impact">${loading('what a revert would do')}</div></section>` : ''}
    <section aria-labelledby="rows-title"><h2 id="rows-title">Rows in the file</h2>${rowsTable(b, false)}</section>`;
  if (b.status === 'applied') loadImpact(b, seq);
}

// Before anyone types a reason: what reverting would do, what blocks it, and what needs review (QA B3). The server checks again.
async function loadImpact(b, seq) {
  let impact;
  try { impact = await api(`/api/imports/${b.id}/impact`); } catch (error) { if (live(seq)) renderFailure(error, () => loadImpact(b, seq), '#impact'); return; }
  if (!live(seq) || !$('#impact')) return;
  const caseLinks = list => list.map(id => { const x = S.cases.find(y => y.id === id); return `<li><a href="#/case/${esc(id)}">${esc(x ? (x.customerName || 'Request') + ', invoice ' + (x.invoiceReference || '') : 'Request ' + id.slice(-6))}</a></li>`; }).join('');
  $('#impact').innerHTML = impact.blocked.length
    ? `<div class="callout bad"><p><b>This import can't be reverted yet.</b> Records added or changed since depend on it:</p><ul>${impact.blocked.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
        <p>Undo those first, then come back. Nothing has changed.</p></div>`
    : `<p>Nothing is deleted: records from this import are marked reverted, and values it replaced get their earlier version back.</p>
      <h3>What reverting would do</h3><ul class="points">${impact.effects.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
      ${impact.review.length ? `<div class="callout warn"><p><b>Check these first:</b></p><ul>${impact.review.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
        ${impact.cases.pending.length ? `<p>Prepared again:</p><ul>${caseLinks(impact.cases.pending)}</ul>` : ''}${impact.cases.decided.length ? `<p>Decided cases that get a note:</p><ul>${caseLinks(impact.cases.decided)}</ul>` : ''}</div>` : ''}
      <button type="button" class="btn danger" id="revert">Revert import…</button>`;
  const button = $('#revert');
  if (button) button.onclick = () => openDialog({ key: 'revert:' + b.id, title: 'Revert ' + b.fileName, danger: true, submitLabel: impact.needsReview ? 'Revert, having checked the above' : 'Revert import',
    intro: `${impact.effects.map(esc).join(' ')}${impact.review.length ? ' ' + impact.review.map(esc).join(' ') : ''}`,
    body: field({ name: 'reason', label: 'Why revert this import?', attrs: 'required autocomplete="off"' }),
    submit: async form => {
      if (!fval(form, 'reason')) { showErrors(form, { field: 'reason', message: 'Say why it is being reverted.' }); return false; }
      const result = await dialogAction(form, `/api/imports/${b.id}/revert`, { reason: fval(form, 'reason'), ...(impact.needsReview ? { confirm: true } : {}) }, 'revert:' + b.id, 'Import reverted');
      if (result.error?.code === 'REVERT_BLOCKED' || result.error?.code === 'REVIEW_REQUIRED') { S.afterDialog = () => route(); toast('The records changed meanwhile. Check the impact again.', 'bad'); return true; }
      if (result.error) return false;
      S.afterDialog = afterChange; return true;
    } });
}
