'use strict';
// The Owner's Model page: #/research (Owner only; Staff get "Page not found" from core.js route()). The team's classifier as the Owner sees it:
//   (a) the model in force: name, version, where it came from (a saved version or the config's bootstrap file), what it was fitted on, its features and coefficients;
//   (b) agreement: over the scored live cases the Owner has answered, how often "decline when the chance is at or above the threshold" matched the Owner, and whether the
//       promotion bar is met (then, and only then, the score is a recommendation the rules read at step 9);
//   (c) settings: promotion on/off, the bar (cases, agreement, threshold) and automatic refits every N verdicts (POST /api/delegation/research/settings);
//   (d) refit now (POST /api/delegation/research/refit), the training table (GET /api/delegation/training.csv) and the saved versions.
// Everything shown is the backend's (GET /api/delegation/research); nothing is calculated here. Uses core.js helpers (api, pageHead, esc, dateText, stamp, loading, live, keepFresh,
// REFRESH, toast, BASE_PATH).

const RS = { data: null, notice: null, flight: false, form: null };

const rsPct = v => `${Math.round(v * 100)}%`;
const rsNum = v => (typeof v === 'number' ? (Math.abs(v) >= 100 ? Math.round(v).toString() : (Math.round(v * 1000) / 1000).toString()) : '');

function rsModelHtml(d) {
  const m = d.model;
  if (!m) return `<p class="muted" data-testid="model-none">No model is in force. Fit one below once the training table has decisions of both kinds, or set a bootstrap file in the config.</p>`;
  const t = m.trainedOn || {};
  const entries = m.coefficients ? Object.entries(m.coefficients).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])) : [];
  const top = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.001);
  const coef = m.coefficients ? `<div class="rs-bars" data-testid="coefficient-bars">${entries.map(([k, v]) => `<div class="bar-row" data-feature="${esc(k)}"><span class="bar-label">${esc(k)}</span><span class="bar-track"><span class="bar${v < 0 ? ' neg' : ''}" data-w="${Math.round(Math.abs(v) / top * 100)}"></span></span><span class="num">${esc(rsNum(v))}</span></div>`).join('')}</div>
      <div class="table-wrap rs-coef"><details><summary>As a table</summary><table class="rtable" data-testid="coefficients"><caption class="visually-hidden">Coefficients</caption><thead><tr><th scope="col">Feature</th><th scope="col" class="num">Standardised coefficient</th></tr></thead><tbody>
      ${entries.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td class="num" data-label="Coefficient">${esc(rsNum(v))}</td></tr>`).join('')}</tbody></table></details></div>
      <p class="hint">A positive coefficient pushes towards "decline". Standardised: comparable across features, not a business rule.</p>` : `<p class="hint">Scored by the model service (${esc(m.scoring)}); its internals stay there.</p>`;
  return `<p data-testid="model-line"><b>${esc(m.name)} v${esc(m.version)}</b> (${m.source === 'saved' ? 'saved version' : 'bootstrap file from the config'}${m.createdAt ? ', ' + stamp(m.createdAt) : ''}).
      Fitted on ${t.rows ?? '?'} rows, ${t.positives ?? '?'} declines${t.byDataset ? ' (' + Object.entries(t.byDataset).map(([k, n]) => `${n} ${k.replace('_', ' ')}`).join(', ') + ')' : ''}.
      Features: ${(m.features || []).map(esc).join(', ')}.</p>${coef}`;
}

function rsAgreementHtml(d) {
  const a = d.agreement, p = d.promotion;
  const line = a.n ? `The model's call (decline when the chance is at or above ${rsPct(a.threshold)}) matched yours on <b>${a.agreed} of ${a.n}</b> scored live cases (${rsPct(a.agreed / a.n)}).`
    : 'No scored live case has your verdict yet: agreement is measured as you decide, agree or disagree.';
  const byv = d.agreementByVersion || [];
  const chart = byv.length ? `<div class="rs-bars" data-testid="agreement-by-version">${byv.map(v => `<div class="bar-row"><span class="bar-label">v${esc(v.version)} (${v.agreed} of ${v.n})</span><span class="bar-track"><span class="bar" data-w="${Math.round(v.agreed / v.n * 100)}"></span></span><span class="num">${Math.round(v.agreed / v.n * 100)}%</span></div>`).join('')}</div>` : '';
  const cm = d.confusion, pr = v => (v === null || v === undefined ? '—' : rsPct(v));
  const matrix = cm && (cm.tp + cm.fp + cm.tn + cm.fn) ? `<div class="table-wrap rs-coef"><table class="rtable" data-testid="confusion"><caption class="visually-hidden">Confusion matrix</caption>
      <thead><tr><th scope="col">At the threshold</th><th scope="col" class="num">You declined</th><th scope="col" class="num">You approved</th></tr></thead>
      <tbody><tr><th scope="row">Model said decline</th><td class="num" data-label="You declined">${cm.tp}</td><td class="num" data-label="You approved">${cm.fp}</td></tr>
      <tr><th scope="row">Model said approve</th><td class="num" data-label="You declined">${cm.fn}</td><td class="num" data-label="You approved">${cm.tn}</td></tr></tbody></table></div>
      <p class="hint">Decline precision ${pr(cm.precision)}, decline recall ${pr(cm.recall)} (the notebook's section 17, on real decisions).</p>` : '';
  return `<p data-testid="agreement-line">${line}</p>${chart}${matrix}
    <div class="callout ${p.active ? 'ok' : 'warn'} small" data-testid="promotion-status" data-active="${p.active}"><p>${esc(p.reason)}</p></div>
    <p class="hint">${d.live} live case${d.live === 1 ? '' : 's'} with your verdict, ${d.scored} of them scored; ${d.decided - d.live} fictional cases in the training table, never in the agreement.</p>`;
}

function rsSettingsHtml(d) {
  const s = RS.form || d.settings, p = s.promotion;
  return `<form id="rs-settings" class="rs-settings" novalidate data-testid="rs-settings">
    <label class="choice"><input type="checkbox" name="enabled"${p.enabled ? ' checked' : ''} data-testid="rs-enabled"><span>Promotion: let the score act as a recommendation once the bar is met<small>Only after the bar below is met. The model can send a case to you; it never approves past the rules and never declines.</small></span></label>
    <div class="field"><label for="rs-min-cases">Bar: at least this many scored live cases with your verdict</label><input id="rs-min-cases" type="number" min="1" max="10000" name="minCases" value="${esc(p.minCases)}"></div>
    <div class="field"><label for="rs-min-agreement">Bar: agreement with you, at least (%)</label><input id="rs-min-agreement" type="number" min="0" max="100" name="minAgreement" value="${esc(Math.round(p.minAgreement * 100))}"></div>
    <div class="field"><label for="rs-threshold">Decline threshold (%): a chance at or above it sends the case to you</label><input id="rs-threshold" type="number" min="0" max="100" name="threshold" value="${esc(Math.round(p.threshold * 100))}"></div>
    <div class="field"><label for="rs-auto">Refit automatically every N verdicts (blank: never)</label><input id="rs-auto" type="number" min="1" max="1000" name="autoRefitEvery" value="${esc(s.autoRefitEvery ?? '')}"></div>
    <p><button type="submit" class="btn primary" data-testid="rs-save">Save settings</button></p>
    <p class="error" data-error role="alert"></p></form>
    <p class="hint">Off by default. With promotion off the score is research only and nothing here changes a decision. Turning it off again takes effect at the next request.</p>`;
}

function rsVersionsHtml(d) {
  if (!d.versions.length) return '<p class="muted" data-testid="versions-none">No saved version yet.</p>';
  return `<div class="table-wrap"><table class="rtable" data-testid="versions"><caption class="visually-hidden">Saved versions</caption><thead><tr><th scope="col">Version</th><th scope="col">Fitted</th><th scope="col" class="num">Rows</th><th scope="col" class="num">Declines</th><th scope="col">Features</th><th scope="col">By</th></tr></thead><tbody>
    ${d.versions.map(v => `<tr data-version="${esc(v.version)}"><th scope="row">v${esc(v.version)}</th><td data-label="Fitted">${stamp(v.createdAt)}</td><td class="num" data-label="Rows">${v.trainedOn?.rows ?? ''}</td><td class="num" data-label="Declines">${v.trainedOn?.positives ?? ''}</td>
      <td data-label="Features">${(v.features || []).map(esc).join(', ')}</td><td data-label="By">${v.createdBy?.auto ? 'automatic' : esc(v.createdBy?.role || '')}${v.createdBy?.note ? ': ' + esc(v.createdBy.note) : ''}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderResearch() {
  const main = $('#main');
  if (!main || S.route?.name !== 'research') return;
  const d = RS.data, t = d.training;
  const notice = RS.notice ? `<div class="callout ${RS.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(RS.notice.text)}</p></div>` : '';
  main.innerHTML = `<div class="research-page page" data-testid="research-page">
    ${pageHead({ title: 'Model', lede: 'The team\'s classifier, kept as a shadow: it learns from your decisions, you see how often it agrees with you, and it only ever acts once you set a bar and it meets it.',
      actions: `<button type="button" class="btn" id="rs-refit" data-testid="rs-refit">Fit a new version now</button>` })}${notice}
    <section aria-labelledby="rs-model"><h2 id="rs-model">Model in force</h2>${rsModelHtml(d)}
      <p class="hint" data-testid="provider-line">Provider: ${esc(d.provider.kind)}${d.provider.url ? ' at ' + esc(d.provider.url) : ' (fitted and scored inside Nucleon, no packages)'}.</p></section>
    <section aria-labelledby="rs-agree"><h2 id="rs-agree">Agreement with you</h2>${rsAgreementHtml(d)}</section>
    <section aria-labelledby="rs-set"><h2 id="rs-set">Settings</h2>${rsSettingsHtml(d)}</section>
    <section aria-labelledby="rs-train"><h2 id="rs-train">Training table</h2>
      <p data-testid="training-line">${t.rows} row${t.rows === 1 ? '' : 's'} with your verdict, ${t.positives} declined. Features a refit would use now: ${t.suggestedFeatures.length ? t.suggestedFeatures.map(esc).join(', ') : 'none yet'}.</p>
      <p class="row"><a class="btn" href="${esc(BASE_PATH)}/api/delegation/training.csv?role=${esc(S.role)}" download="nucleon-training.csv" data-testid="training-download">Download the training table (CSV)</a>
        ${d.model ? `<a class="btn" href="${esc(BASE_PATH)}/api/delegation/research/model.json?role=${esc(S.role)}" download data-testid="model-download">Download the model (JSON)</a>` : ''}</p>
      <p class="hint">The notebook's shape: one row per case, the request date, your decision, Target_Deny. Fictional cases are labelled by dataset.</p></section>
    <section aria-labelledby="rs-pref" data-testid="rs-pref"><h2 id="rs-pref">Teach it your limits</h2>${rsPrefHtml()}</section>
    <section aria-labelledby="rs-own-h" data-testid="rs-own"><h2 id="rs-own-h">Add a decision you made yourself</h2>${rsOwnHtml()}</section>
    <section aria-labelledby="rs-versions"><h2 id="rs-versions">Saved versions</h2>${rsVersionsHtml(d)}</section></div>`;
  document.title = 'Model · Nucleon';
  bindPref();
  bindOwn();
  $$('.bar').forEach(b => { b.style.width = b.dataset.w + '%'; });   // through the CSSOM: the page's CSP allows no inline style attribute
  $('#rs-refit').onclick = rsRefit;
  const form = $('#rs-settings');
  form.oninput = () => { RS.form = rsRead(form); };
  form.onsubmit = event => { event.preventDefault(); rsSave(form); };
}

// The Owner's what-ifs (4 Nov 2026): a question about a real customer with numbers the records do not hold, far out first and then narrowed between the
// highest approved and the lowest declined. Each answer is stored as an owner_preference case: the comparables and the training table see it, labelled.
function rsPrefHtml() {
  const p = RS.pref;
  if (!p) return '<p class="muted">Loading the next what-if…</p>';
  const head = `<p class="hint">Real cases are rare, so answer what-ifs about your real customers: each answer teaches the comparables and the model where your limits are. ${p.answered} answered so far.</p>`;
  if (!p.scenario) return head + '<p class="muted" data-testid="pref-none">Nothing more to ask for now: every customer is covered. New customers and invoices bring new questions.</p>';
  const s = p.scenario;
  return `${head}<div class="facts-card" data-testid="pref-card" data-scenario="${esc(s.id)}"><p data-testid="pref-text"><b>${esc(s.text)}</b></p>
    <div class="field"><label for="pref-why">Why (optional, a few words: it is shown beside this answer when it is used as a comparable)</label><input id="pref-why" data-testid="pref-why" maxlength="200"></div>
    <p class="row"><button type="button" class="btn primary" data-pref="approve" data-testid="pref-approve">Yes, approve</button>
      <button type="button" class="btn" data-pref="decline" data-testid="pref-decline">No, decline</button>
      <button type="button" class="btn link" data-pref="skip" data-testid="pref-skip">Ask me something else</button></p></div>`;
}

// A decision of the Owner's own (11 Nov 2026, Hoang: "close the loop" with answers collected outside Nucleon): the Owner types a scenario about one of their
// customers and what they decided. It is stored exactly like an answered what-if (the same endpoint, source 'own'): the comparables and the training table see it,
// labelled; it never counts in the track record and decides nothing by itself.
function rsOwnHtml() {
  const p = RS.pref, rec = RS.records;
  if (!rec || !rec.customers?.length) return '<p class="muted" data-testid="own-none">Add customers first (Customers page): a scenario is about one of your customers.</p>';
  const d = RS.own || {};
  const customers = rec.customers.filter(c => (c.status || 'active') === 'active').map(c => ({ value: c.id, label: c.name }));
  const invoices = (rec.invoices || []).filter(i => i.customerId === d.customerId && (i.status || 'active') === 'active').sort((x, y) => String(y.originalDueDate || '').localeCompare(String(x.originalDueDate || ''))).map(i => ({ value: i.id, label: `Invoice ${i.reference || 'with no number'}${i.originalDueDate ? ', first due ' + dateText(i.originalDueDate) : ''}` }));
  const kind = d.kind || 'extension';
  const recent = (p?.recent || []).length ? `<details class="sec" data-testid="own-recent"><summary>Your last ${p.recent.length} answers (${p.answered} in all, ${p.own || 0} typed in by you)</summary><ul class="home-list">${p.recent.map(a =>
    `<li><span class="chip ${a.ownerDecision === 'approve' ? 'done' : 'fail'}">${a.ownerDecision === 'approve' ? 'Approved' : 'Declined'}</span> ${esc(a.summary || '')}${a.ownerReason ? ': ' + esc(a.ownerReason) : ''}</li>`).join('')}</ul></details>` : '';
  return `<p class="hint">Already decided a case outside Nucleon, on the phone or in a meeting? Add it here. Say which customer, what was asked and what you decided. Nucleon uses it as one more example of your judgement: it appears among the similar cases beside later requests and in the training table of the model. It changes no rule and no invoice.</p>
    <form id="rs-own" novalidate data-testid="own-form">
      ${selectField({ name: 'customerId', id: 'own-customer', label: 'Customer', options: customers, value: d.customerId || '', placeholder: 'Choose a customer…' })}
      ${radios({ name: 'kind', legend: 'What was asked', value: kind, options: [{ value: 'extension', label: 'More time to pay an invoice' }, { value: 'trial_credit', label: 'A first order on credit' }] })}
      <div data-own="extension"${kind === 'extension' ? '' : ' hidden'}>
        ${selectField({ name: 'invoiceId', id: 'own-invoice', label: 'Which invoice', options: invoices, value: d.invoiceId || '', placeholder: d.customerId ? (invoices.length ? 'Choose an invoice…' : 'This customer has no invoice') : 'Choose the customer first' })}
        ${field({ name: 'days', id: 'own-days', label: 'How many days after its due date they wanted to pay', value: d.days || '', attrs: 'inputmode="numeric"', hint: 'Example: 30 for a month after the date the invoice is due now.' })}</div>
      <div data-own="trial_credit"${kind === 'trial_credit' ? '' : ' hidden'}>
        ${field({ name: 'orderAmountText', id: 'own-amount', label: 'Order amount', value: d.orderAmountText || '', attrs: 'inputmode="decimal"' })}
        ${field({ name: 'termsDays', id: 'own-terms', label: 'Days they wanted to pay in', value: d.termsDays || '', attrs: 'inputmode="numeric"', hint: 'Example: 14 for two weeks after delivery.' })}</div>
      ${radios({ name: 'outcome', legend: 'What you decided', value: d.outcome || '', options: [{ value: 'approve', label: 'I approved it' }, { value: 'decline', label: 'I declined it' }] })}
      ${field({ name: 'reason', id: 'own-reason', label: 'Why', optional: true, value: d.reason || '', attrs: 'maxlength="200"', hint: 'A few words. Shown beside this example when it is used.' })}
      ${formError()}<div class="row"><button type="submit" class="btn primary" data-testid="own-add">Add this decision</button></div></form>${recent}`;
}
function ownRead(form) { return Object.fromEntries(['customerId', 'kind', 'invoiceId', 'days', 'orderAmountText', 'termsDays', 'outcome', 'reason'].map(n => [n, (form.elements[n]?.value ?? '').trim()])); }
function ownTyping() { const d = RS.own; return !!d && Object.entries(d).some(([k, v]) => k !== 'kind' && v); }
function ownRedraw() { const sec = document.querySelector('[data-testid=rs-own]'); if (sec) { sec.innerHTML = '<h2 id="rs-own-h">Add a decision you made yourself</h2>' + rsOwnHtml(); bindOwn(); } }
function bindOwn() {
  const form = document.getElementById('rs-own');
  if (!form) return;
  form.oninput = () => { RS.own = ownRead(form); };
  form.elements.customerId.onchange = () => { RS.own = { ...ownRead(form), invoiceId: '' }; ownRedraw(); document.getElementById('own-customer')?.focus(); };
  form.querySelectorAll('[name=kind]').forEach(r => { r.onchange = () => { RS.own = ownRead(form); form.querySelectorAll('[data-own]').forEach(b => { b.hidden = b.dataset.own !== RS.own.kind; }); }; });
  form.onsubmit = event => { event.preventDefault(); ownSubmit(form); };
}
async function ownSubmit(form) {
  if (RS.flight) return;
  clearErrors(form);
  const d = ownRead(form), whole = x => (/^\d+$/.test(x) ? Number(x) : null);
  if (!d.customerId) return showErrors(form, { field: 'customerId', message: 'Choose the customer.' });
  if (d.kind === 'extension' && !d.invoiceId) return showErrors(form, { field: 'invoiceId', message: 'Choose the invoice.' });
  if (d.kind === 'extension' && !(whole(d.days) >= 1 && whole(d.days) <= 365)) return showErrors(form, { field: 'days', message: 'Enter a number of days from 1 to 365.' });
  if (d.kind === 'trial_credit' && !d.orderAmountText) return showErrors(form, { field: 'orderAmountText', message: 'Enter the order amount.' });
  if (d.kind === 'trial_credit' && !(whole(d.termsDays) >= 1 && whole(d.termsDays) <= 365)) return showErrors(form, { field: 'termsDays', message: 'Enter a number of days from 1 to 365.' });
  if (!d.outcome) return showErrors(form, { field: 'outcome', message: 'Say what you decided.' });
  const params = d.kind === 'extension' ? { invoiceId: d.invoiceId, days: whole(d.days) } : { orderAmountText: d.orderAmountText, termsDays: whole(d.termsDays) };
  const keyName = 'own:' + JSON.stringify([d.customerId, d.kind, params, d.outcome]);
  RS.flight = true;
  try {
    const out = await api('/api/delegation/preferences/answer', { source: 'own', customerId: d.customerId, kind: d.kind, params, outcome: d.outcome, reason: d.reason },
                          { key: keyFor(keyName), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    keyDone(keyName);
    RS.pref = { scenario: out.scenario, answered: out.answered, customers: out.customers, own: out.own, recent: out.recent };
    RS.own = null;
    toast('Added: you ' + (d.outcome === 'approve' ? 'approved' : 'declined') + ' it for ' + out.customer.name + '.', 'ok');
    ownRedraw();
  } catch (error) { if (error.code !== 'SIGNED_OUT') showErrors(form, error.field ? { ...error, field: String(error.field).replace(/^params\./, '') } : error); }
  finally { RS.flight = false; }
}

// The Owner is typing a reason for the what-if: a redraw (the timer, or coming back to the tab) would wipe it (Tony, 6 Nov 2026).
function prefTyping() { const w = $('#pref-why'); return !!w && (w.value.trim() !== '' || document.activeElement === w); }

function bindPref() {
  $$('[data-pref]').forEach(b => { b.onclick = () => prefAnswer(b.dataset.pref); });
}

async function prefLoad() { RS.pref = await api('/api/delegation/preferences/next').catch(() => null); }

async function prefAnswer(what) {
  const s = RS.pref?.scenario;
  if (!s) return;
  if (what === 'skip') { RS.skipped = (RS.skipped || 0) + 1; toast('That question is skipped for now; it comes back later.', 'ok'); return; }
  const reason = ($('#pref-why')?.value || '').trim();
  try {
    const out = await api('/api/delegation/preferences/answer', { customerId: s.customer.id, kind: s.kind, params: s.params, outcome: what, reason },
                          { key: keyFor('pref:' + s.id), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    keyDone('pref:' + s.id);
    RS.pref = { scenario: out.scenario, answered: out.answered, customers: out.customers, own: out.own, recent: out.recent };
    toast('Recorded: ' + (what === 'approve' ? 'approve' : 'decline') + ' for ' + out.customer.name, 'ok');
    const sec = $('[data-testid=rs-pref]');
    if (sec) { sec.innerHTML = '<h2 id="rs-pref">Teach it your limits</h2>' + rsPrefHtml(); bindPref(); }
  } catch (error) { toast(error.message, 'bad'); }
}

function rsRead(form) {
  const f = new FormData(form), num = k => (f.get(k) === '' || f.get(k) === null ? null : Number(f.get(k)));
  return { autoRefitEvery: num('autoRefitEvery'), promotion: { enabled: f.get('enabled') === 'on', minCases: num('minCases') ?? 20, minAgreement: (num('minAgreement') ?? 80) / 100, threshold: (num('threshold') ?? 50) / 100 } };
}

async function rsSave(form) {
  if (RS.flight) return;
  const body = rsRead(form), slot = $('[data-error]', form);
  if (!Number.isInteger(body.promotion.minCases) || body.promotion.minCases < 1) { slot.textContent = 'The number of cases is a whole number of at least 1.'; return; }
  if (body.autoRefitEvery !== null && (!Number.isInteger(body.autoRefitEvery) || body.autoRefitEvery < 1)) { slot.textContent = 'Refit every N verdicts: a whole number of at least 1, or blank.'; return; }
  RS.flight = true;
  try {
    RS.data = await api('/api/delegation/research/settings', body, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    RS.form = null; RS.notice = { kind: 'ok', text: 'Settings saved.' };
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    RS.notice = { kind: 'bad', text: error.message };
  } finally { RS.flight = false; }
  renderResearch();
}

async function rsRefit() {
  if (RS.flight) return;
  RS.flight = true;
  $('#rs-refit').disabled = true;
  try {
    RS.data = await api('/api/delegation/research/refit', {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    const m = RS.data.model;
    RS.notice = { kind: 'ok', text: `Fitted ${m.name} v${m.version} on ${m.trainedOn.rows} rows.` };
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    RS.notice = { kind: 'bad', text: error.message };
  } finally { RS.flight = false; }
  renderResearch();
}

async function rsLoad() { [RS.data, , RS.records] = await Promise.all([api('/api/delegation/research'), prefLoad(), api('/api/records').catch(() => null)]); }

PAGES.research = async (r, seq) => {
  $('#main').innerHTML = loading('the model');
  Object.assign(RS, { notice: null, flight: false, form: null, own: null });
  await rsLoad();
  if (!live(seq)) return;
  renderResearch();
  keepFresh(seq);
};
REFRESH.research = async seq => {
  if (RS.flight || RS.form || prefTyping() || ownTyping()) return;   // never redraw under a form being edited, nor over a what-if reason being typed
  try { await rsLoad(); } catch (error) { if (error.code === 'SIGNED_OUT' || error.status === 401) throw error; return; }
  if (!live(seq) || S.route?.name !== 'research') return;
  const y = scrollY;
  renderResearch();
  scrollTo(0, y);
};
