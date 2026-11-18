'use strict';
// Quick setup (11 Nov 2026; docs/superpowers/specs/2026-11-11-quick-setup-design.md): the Owner's first setup in a few plain questions, beside the Control panel.
// Every change asks the server what the resulting policy would do with the Owner's own open invoices (api/delegation/quick-setup/preview: read only, the same
// rules a real request meets); Save stores it as an ordinary policy version (PUT api/delegation/policy). Uses core.js helpers.

const QS = { data: null, preview: null, seq: 0, timer: null, version: 0, saved: false, conflict: false };

const qsCsrf = () => ({ 'X-Nucleon-CSRF': S.session.csrf || '' });

function qsAnswers(form) {
  const v = name => (form.elements[name]?.value ?? '').trim();
  const num = x => (x === '' ? null : /^\d+$/.test(x) ? Number(x) : x);
  return {
    start: form.querySelector('[name=start]:checked')?.value || 'now',
    maxInvoice: v('maxInvoice'), maxCustomer: v('maxCustomer'),
    daysFromRequest: num(v('daysFromRequest')), daysPastOriginalDue: num(v('daysPastOriginalDue')),
    allowOtherOverdue: !!form.elements.allowOtherOverdue?.checked,
    lateHistory: form.querySelector('[name=lateHistory]:checked')?.value || 'some',
    holdCustomers: $$('[name=hold]:checked', form).map(x => x.value),
    agentDeclines: !!form.elements.agentDeclines?.checked,
    newCustomers: form.querySelector('[name=newCustomers]:checked')?.value || 'owner'
  };
}

// A suggestion from the Doctor (#/quick-setup?try=<JSON>): only the known answers, each of its own type, are taken; anything else is ignored. Nothing is saved.
// Only the six answers the Doctor ever suggests: never how the agent starts, the never-decide list or declining on its own.
const QS_TRY = { maxInvoice: v => typeof v === 'string', maxCustomer: v => typeof v === 'string', daysFromRequest: v => v === null || Number.isInteger(v),
  daysPastOriginalDue: v => Number.isInteger(v), allowOtherOverdue: v => typeof v === 'boolean', lateHistory: v => ['any', 'some', 'none'].includes(v) };
const QS_TRY_NAMES = { maxInvoice: 'the largest invoice', maxCustomer: 'the most one customer may owe', daysFromRequest: 'the days after the customer asks',
  daysPastOriginalDue: 'the most an invoice may be late in total', allowOtherOverdue: 'customers with other overdue invoices', lateHistory: 'customers who paid late before' };
function qsTry(raw) {
  if (!raw) return null;
  let given;
  try { given = JSON.parse(raw); } catch { return null; }
  if (!given || typeof given !== 'object' || Array.isArray(given)) return null;
  const out = {};
  for (const [k, ok] of Object.entries(QS_TRY)) if (Object.prototype.hasOwnProperty.call(given, k) && ok(given[k])) out[k] = given[k];
  return Object.keys(out).length ? out : null;
}

// The three ready-made levels (delegation.py QUICK_LEVELS; 12 Nov 2026). A level fills six answers and saves nothing; "Custom" is whatever else the form says.
// Used here, in Get started (getstarted.js) and on the Control panel (delegation.js).
const QS_LEVEL_KEYS = ['maxInvoice', 'maxCustomer', 'daysFromRequest', 'daysPastOriginalDue', 'allowOtherOverdue', 'lateHistory'];
function qsLevelOf(answers, levels) {
  const same = (a, b) => (a ?? '') === (b ?? '') || (a !== '' && b !== '' && a != null && b != null && typeof a !== 'boolean' && !isNaN(Number(a)) && Number(a) === Number(b));
  return (levels || []).find(l => QS_LEVEL_KEYS.every(k => !(k in l.answers) || same(answers[k], l.answers[k])))?.name || null;
}
function levelButtons(levels, current, { custom = true, testid = 'levels' } = {}) {
  const one = (name, label, says) => `<button type="button" class="level${name === (current || 'custom') ? ' on' : ''}" data-level="${esc(name)}" data-testid="level-${esc(name)}" aria-pressed="${name === (current || 'custom')}"><span><b>${esc(label)}</b><small>${esc(says)}</small></span></button>`;
  return `<div class="level-row" data-testid="${testid}">${(levels || []).map(l => one(l.name, l.label, l.says)).join('')}${custom ? one('custom', 'Custom', 'Your own answers to each question.') : ''}</div>`;
}
function qsApplyLevel(form, answers) {
  for (const k of ['maxInvoice', 'maxCustomer', 'daysFromRequest', 'daysPastOriginalDue']) if (k in answers && form.elements[k]) form.elements[k].value = answers[k] ?? '';
  if ('allowOtherOverdue' in answers && form.elements.allowOtherOverdue) form.elements.allowOtherOverdue.checked = !!answers.allowOtherOverdue;
  if ('lateHistory' in answers) $$('[name=lateHistory]', form).forEach(x => { x.checked = x.value === answers.lateHistory; });
}
function qsMarkLevel() {
  const form = $('#qs-form'), row = $('[data-testid=qs-levels]');
  if (!form || !row) return;
  const now = qsLevelOf(qsAnswers(form), QS.data.levels) || 'custom';
  $$('[data-level]', row).forEach(b => { const on = b.dataset.level === now; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
}

function qsChoices(key) {
  const a = QS.data.amounts;
  if (!a) return '';
  const button = (which, label, m) => `<button type="button" class="btn small" data-testid="qs-amount-choice" data-for="${key}" data-which="${which}" data-value="${esc(m.plain)}">${esc(label)}: ${esc(m.text)}</button>`;
  return `<p class="row">${button('median', 'A typical open invoice', a.median)} ${button('largest', 'The largest open invoice', a.largest)}</p>`;
}

function qsQuestions(a) {
  const check = (name, label, on, hint) => `<label class="choice"><input type="checkbox" id="qs-${name}" name="${name}"${on ? ' checked' : ''}><span>${esc(label)}${hint ? `<small>${esc(hint)}</small>` : ''}</span></label>
    <p class="error" data-error-for="${name}" role="alert"></p>`;
  const q = (key, body) => `<div class="qs-q" data-testid="qs-q-${key}">${body}</div>`;
  const held = new Set(a.holdCustomers || []);
  return `${q('start', radios({ name: 'start', legend: 'How should the agent start?', value: a.start, options: [
      { value: 'now', label: 'It decides from today, inside the limits below', note: 'Best for trying it out: you see the effect at once.' },
      { value: 'after_reviews', label: 'It decides after you have reviewed some of its recommendations', note: 'Until you have reviewed 5 and agreed with at least 80% of them, everything comes to you.' },
      { value: 'recommend', label: 'It only recommends; you decide everything', note: 'Nothing is decided without you.' }] }))}
    ${q('maxInvoice', field({ name: 'maxInvoice', id: 'qs-maxInvoice', label: 'The largest invoice the agent may give more time on, by itself', value: a.maxInvoice || '', attrs: 'inputmode="decimal" autocomplete="off"',
      hint: 'The amount still owed on the invoice. Anything larger comes to you.' }) + qsChoices('maxInvoice'))}
    ${q('maxCustomer', field({ name: 'maxCustomer', id: 'qs-maxCustomer', label: 'The most one customer may owe in total, for the agent to decide', value: a.maxCustomer || '', attrs: 'inputmode="decimal" autocomplete="off"',
      hint: 'Everything that customer owes you, all invoices together. Above it, the request comes to you.' }) + qsChoices('maxCustomer'))}
    ${q('daysFromRequest', field({ name: 'daysFromRequest', id: 'qs-daysFromRequest', label: 'The latest new payment date, in days after the day the customer asks', optional: true, value: a.daysFromRequest ?? '', attrs: 'inputmode="numeric"',
      hint: 'For example 14: a customer asking on 10 November may get a date up to 24 November. Leave empty for no such limit.' }))}
    ${q('daysPastOriginalDue', field({ name: 'daysPastOriginalDue', id: 'qs-daysPastOriginalDue', label: 'The most an invoice may be late in total, in days after its first due date', value: a.daysPastOriginalDue ?? '', attrs: 'inputmode="numeric"',
      hint: 'Counted from the due date the invoice first had, so asking again and again cannot go past it. An invoice already 40 days late needs more than 40 here.' }))}
    ${q('allowOtherOverdue', check('allowOtherOverdue', 'The agent may decide even when the customer has other overdue invoices', a.allowOtherOverdue, 'Off: any customer with another overdue invoice comes to you. Many customers have one.'))}
    ${q('lateHistory', radios({ name: 'lateHistory', legend: 'A customer who paid late before', value: a.lateHistory, options: [
      { value: 'any', label: 'The agent may still decide' },
      { value: 'some', label: 'Only if at most a quarter of their earlier payments were late' },
      { value: 'none', label: 'Never: they come to you', note: 'Most customers have paid late at least once.' }] }))}
    ${q('holdCustomers', `<fieldset class="choices"><legend>Customers the agent must never decide for</legend><p class="hint">Their requests always come to you.</p>
      ${QS.data.customers.map(c => `<label class="choice"><input type="checkbox" name="hold" value="${esc(c.id)}"${held.has(c.id) ? ' checked' : ''}><span>${esc(c.name)}</span></label>`).join('')}
      <p class="error" data-error-for="holdCustomers" role="alert"></p></fieldset>`)}
    ${q('newCustomers', radios({ name: 'newCustomers', legend: 'When a new customer asks for a first order on credit', value: a.newCustomers || 'owner', options: [
      { value: 'owner', label: 'It always comes to you' },
      { value: 'trial', label: 'The agent may give a small first order on credit', note: 'Up to the largest-invoice limit above at risk after the deposit, a deposit of at least a quarter and up to 30 days to pay, once Staff confirm who the business is. The Control panel has the finer settings.' }] }))}
    ${q('agentDeclines', check('agentDeclines', 'The agent may say no by itself to a request for more days than your limit, when the assistant recommends saying no', a.agentDeclines,
      'Off: those come to you. You can reverse any of its decisions on the Decide page.'))}`;
}

function qsPreviewHtml() {
  const v = QS.preview;
  if (!v) return '<p class="muted">Working out what these answers would do…</p>';
  const n = (k, label) => `<div class="fact"><dt>${label}</dt><dd data-testid="qs-count-${k}">${v.counts[k]}</dd></div>`;
  const ex = k => v.examples[k].length ? `<ul class="home-list">${v.examples[k].map(e => `<li>${esc(e.customer)}, invoice ${esc(e.invoice || '')} (${esc(e.amountText || '')})${e.reason ? ` — ${esc(e.reason)}` : ''}</li>`).join('')}</ul>` : '';
  const none = v.total && !v.counts.agent ? '<div class="callout warn" data-testid="qs-none"><p>With these answers the agent would decide none of these. Every request would come to you.</p></div>' : '';
  const reasons = v.reasons.length ? `<h3>Why they come to you</h3><ul class="home-list">${v.reasons.map(r => `<li>${r.question
      ? `<button type="button" class="btn small" data-testid="qs-reason" data-question="${esc(r.question)}">${esc(r.label)}: ${r.count}</button>`
      : `<a data-testid="qs-reason" href="#/delegation">${esc(r.label)}: ${r.count}</a>`}</li>`).join('')}</ul>` : '';
  return `${v.total ? `<dl class="facts">${n('agent', 'The agent decides')}${n('owner', 'Comes to you')}${n('held', 'Never decided by the agent')}</dl>` : '<p class="muted">There are no open invoices to try these answers on.</p>'}
    ${none}${reasons}
    ${v.examples.agent.length ? `<details><summary>Examples the agent decides</summary>${ex('agent')}</details>` : ''}${v.examples.owner.length ? `<details><summary>Examples that come to you</summary>${ex('owner')}</details>` : ''}
    ${v.truncated ? '<p class="hint">Only the first 200 open invoices were tried.</p>' : ''}`;
}

function qsSummaryHtml() {
  const s = QS.preview?.summary;
  if (!s) return '';
  return `<div class="facts-card" data-testid="qs-summary"><h3>The agent decides by itself</h3><ul>${s.decides.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    <h3>Always comes to you</h3><ul>${s.comesToYou.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
}

function qsDrawPreview() {
  const box = $('[data-testid=qs-preview]');
  if (!box) return;
  box.dataset.total = QS.preview ? QS.preview.total : '';
  $('#qs-preview-body').innerHTML = qsPreviewHtml();
  $('#qs-summary-slot').innerHTML = qsSummaryHtml();
  $$('[data-testid=qs-reason][data-question]').forEach(b => { b.onclick = () => {
    const target = $('[data-testid="qs-q-' + b.dataset.question + '"]');
    target?.scrollIntoView({ block: 'center' });
    (target?.querySelector('input:checked, input, select') || target)?.focus();
  }; });
}

async function qsRunPreview() {
  const form = $('#qs-form');
  if (!form) return;
  const seq = ++QS.seq, box = $('[data-testid=qs-preview]');
  box.setAttribute('aria-busy', 'true');
  try {
    const out = await api('/api/delegation/quick-setup/preview', { answers: qsAnswers(form), days: Number($('#qs-days').value) || 14 }, { headers: qsCsrf() });
    if (seq !== QS.seq) return;
    clearErrors(form);
    const before = QS.preview;
    QS.preview = out; box.classList.remove('stale');
    qsDrawPreview();
    const same = $('#qs-same');   // an owner changed a limit, saw the same counts and could not tell whether anything had been worked out (12 Nov 2026)
    if (same) same.textContent = before && out.total && JSON.stringify(before.counts) === JSON.stringify(out.counts) ? 'Worked out again with your change: the same result. No open invoice crosses the limit you moved.' : '';
  } catch (error) {
    if (seq !== QS.seq) return;
    box.classList.add('stale');
    showErrors(form, error);
  } finally {
    if (seq === QS.seq) box.removeAttribute('aria-busy');
  }
}

function qsChanged() {
  QS.saved = false; QS.conflict = false;
  qsMarkLevel();
  $('#qs-after').innerHTML = '';
  clearTimeout(QS.timer);
  QS.timer = setTimeout(qsRunPreview, 400);
  const box = $('[data-testid=qs-preview]');
  if (box) box.setAttribute('aria-busy', 'true');
}

async function qsSave(button) {
  const form = $('#qs-form');
  await busy(button, async () => {
    clearTimeout(QS.timer);
    try {
      const out = await api('/api/delegation/quick-setup/preview', { answers: qsAnswers(form), days: Number($('#qs-days').value) || 14 }, { headers: qsCsrf() });
      QS.preview = out; qsDrawPreview();
      const saved = await api('/api/delegation/policy', { ...out.policy, expectedVersion: QS.version, note: 'Saved from Quick setup' }, { method: 'PUT', headers: qsCsrf() });
      QS.version = saved.version; QS.saved = true; QS.conflict = false;
      toast('Saved as version ' + saved.version, 'ok');
    } catch (error) {
      if (error.code === 'POLICY_CHANGED') {
        QS.conflict = true;
        try { QS.version = (await api('/api/delegation/policy')).version; } catch { /* the next save tries again */ }
        qsRunPreview();
      } else showErrors(form, error);
    }
    qsDrawAfter();
  });
}

function qsDrawAfter() {
  const after = $('#qs-after'), assistant = assistantHref();
  if (QS.conflict) after.innerHTML = '<div class="callout warn" role="alert" data-testid="qs-conflict"><p>The rules were changed somewhere else. Your answers are kept; check the preview and save again.</p></div>';
  else if (QS.saved) after.innerHTML = `<div class="callout ok" role="status" data-testid="qs-saved"><p><b>Saved as policy version ${esc(QS.version)}.</b> The agent uses these rules from the next request.</p>
    <p>${assistant ? `<a class="btn" href="${esc(assistant)}" target="_blank" rel="noopener">Try a request in the assistant</a> ` : ''}<a class="btn" href="#/review">Open the Decide page</a> <a class="btn" href="#/delegation">Fine-tune on the Control panel</a></p></div>`;
  else after.innerHTML = '';
}

PAGES['quick-setup'] = async (r, seq) => {
  const main = $('#main');
  if (S.role !== 'owner') {
    main.innerHTML = `<div class="state-msg" data-testid="delegation-owner-only">${pageHead({ title: 'Quick setup' })}<p>Only the Owner sets how far the assistant may decide on its own. Staff can read the current policy through the assistant.</p></div>`;
    return;
  }
  main.innerHTML = loading('quick setup');
  const data = await api('/api/delegation/quick-setup');
  if (!live(seq)) return;
  const tried = qsTry(r.q?.try);
  if (tried) data.answers = { ...data.answers, ...tried };
  Object.assign(QS, { data, preview: null, version: data.policy.version, saved: false, conflict: false });
  main.innerHTML = `<div class="page qs-page" data-testid="quick-setup-page">
    ${pageHead({ title: 'Quick setup', lede: 'A few questions about how far the agent may decide on its own. You see what your answers would do before you save them. Every setting stays on the Control panel.' })}
    <div class="callout ok" data-testid="qs-assurances"><ul><li>Nucleon never contacts your customer.</li><li>You can undo any decision the agent makes, on the Decide page.</li>
      <li>You can pause the agent at any time with one button on the Control panel.</li></ul></div>
    ${tried ? `<p class="callout warn" data-testid="qs-from-doctor">Filled in from the Doctor: ${esc(Object.keys(tried).map(k => QS_TRY_NAMES[k]).join(', '))}. Nothing is saved until you press Save.</p>` : ''}
    ${(data.levels || []).length ? `<section class="level-set" aria-labelledby="qs-level-title"><h2 id="qs-level-title">${icon('rules')}Start from a level</h2>
      <p class="hint">A level fills in six of the answers below from your own open invoices. Nothing is saved until you press Save. How the agent starts, the customers it never decides for and whether it may say no stay as they are.</p>
      ${levelButtons(data.levels, qsLevelOf(data.answers, data.levels), { testid: 'qs-levels' })}</section>` : ''}
    <form id="qs-form" novalidate>${REQUIRED_LEGEND}${qsQuestions(data.answers)}${formError()}</form>
    <section aria-labelledby="qs-prev-title" data-testid="qs-preview" aria-busy="true">
      <h2 id="qs-prev-title">If each customer asked today for <select id="qs-days" aria-label="How many more days">${[7, 14, 30].map(d => `<option value="${d}"${d === 14 ? ' selected' : ''}>${d}</option>`).join('')}</select> more days on each open invoice</h2>
      <p class="hint">An estimate: it assumes the assistant recommends approving, judges each invoice on its own, and leaves out the team's model.</p><div id="qs-preview-body"></div><p class="hint keep" id="qs-same" data-testid="qs-same" role="status"></p></section>
    <div id="qs-summary-slot"></div>
    <div class="row"><button type="button" class="btn primary" data-testid="qs-save">Save these rules</button><span class="hint">Saving makes a new policy version. Earlier versions stay, and decisions already made are unchanged.</span></div>
    <div id="qs-after"></div></div>`;
  const form = $('#qs-form');
  markRequired(form);
  form.addEventListener('input', qsChanged);
  form.addEventListener('change', qsChanged);
  form.onsubmit = e => e.preventDefault();
  $('#qs-days').onchange = qsChanged;
  $$('[data-testid=qs-amount-choice]', form).forEach(b => { b.onclick = () => { form.elements[b.dataset.for].value = b.dataset.value; qsChanged(); }; });
  $('[data-testid=qs-save]').onclick = e => qsSave(e.currentTarget);
  $$('[data-testid=qs-levels] [data-level]').forEach(b => { b.onclick = () => {
    const level = (data.levels || []).find(l => l.name === b.dataset.level);
    if (level) { qsApplyLevel(form, level.answers); qsChanged(); } else form.elements.maxInvoice?.focus();
  }; });
  const asked = (data.levels || []).find(l => l.name === r.q?.level);   // from the Control panel: #/quick-setup?level=strict fills the answers and saves nothing
  if (asked) { qsApplyLevel(form, asked.answers); qsMarkLevel(); }
  qsDrawPreview();
  await qsRunPreview();
};
