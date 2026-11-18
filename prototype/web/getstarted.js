'use strict';
// Get started (12 Nov 2026): the Owner's first run as one path of three steps, asked for by an owner who wanted to "go to the home page and follow the prompts"
// instead of moving between pages. Step 1 picks how strict the agent is (the three levels of Quick setup, worked out from the business's own open invoices, with
// what they would do shown beside them); step 2 the customers the agent must never decide for, and whether new customers may get a small first order on credit
// (13 Nov 2026: from a clean start trial credit stayed off, so every first order went to the Owner); step 3 how much the pages show (core.js VIEWS), with a preview.
// Nothing is saved until the last button: one ordinary policy version (PUT api/delegation/policy), exactly what Quick setup would save for the same answers, so
// settings this path does not ask about are left as they are. Every choice here can be changed later on the Control panel without coming back.
// Uses core.js helpers and quicksetup.js (levelButtons, qsLevelOf, qsCsrf).

const GS = { data: null, step: 1, level: null, hold: [], newc: 'owner', preview: null, seq: 0, done: null, error: '' };

const GS_STEPS = ['How strict', 'Customers', 'What you see'];

function gsAnswers() {
  const level = (GS.data.levels || []).find(l => l.name === GS.level);
  return { ...GS.data.answers, ...(level ? level.answers : {}), holdCustomers: GS.hold, newCustomers: GS.newc };
}

// The amount a new customer's first order may put at risk: the one-request limit of the chosen level (or of the rules kept), as money text when it is one of
// the two amounts worked out from the open invoices.
function gsTrialText() {
  const plain = gsAnswers().maxInvoice || '', a = GS.data.amounts || {};
  const known = [a.median, a.largest].find(m => m && m.plain === plain);
  return known ? known.text : plain;
}

function gsStepsHtml() {
  return `<ol class="gs-steps" data-testid="gs-steps">${GS_STEPS.map((t, i) => `<li${i + 1 === GS.step ? ' aria-current="step"' : ''} class="${i + 1 < GS.step ? 'done' : ''}">${i + 1 < GS.step ? icon('check') : ''}<span>${i + 1}. ${esc(t)}</span></li>`).join('')}</ol>`;
}

function gsPreviewHtml() {
  const v = GS.preview;
  if (!v) return '<p class="muted">Working out what this would do…</p>';
  const n = (k, label) => `<div class="fact"><dt>${label}</dt><dd data-testid="gs-count-${k}">${v.counts[k]}</dd></div>`;
  const list = (title, rows) => (rows.length ? `<h3>${title}</h3><ul>${rows.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '');
  return `${v.total ? `<p class="keep hint">If each customer asked today for 14 more days on each open invoice:</p><dl class="facts">${n('agent', 'The agent decides')}${n('owner', 'Comes to you')}${n('held', 'Never decided by the agent')}</dl>`
      : '<p class="muted">There are no open invoices to try this on yet.</p>'}
    ${list('The agent decides by itself', v.summary.decides)}${list('Always comes to you', v.summary.comesToYou)}`;
}

async function gsRunPreview() {
  const seq = ++GS.seq, side = $('#gs-preview');
  if (side) side.setAttribute('aria-busy', 'true');
  try {
    const out = await api('/api/delegation/quick-setup/preview', { answers: gsAnswers(), days: 14 }, { headers: qsCsrf() });
    if (seq !== GS.seq) return;
    GS.preview = out; GS.error = '';
  } catch (error) {
    if (seq !== GS.seq) return;
    GS.preview = null; GS.error = error.message;
  }
  const now = $('#gs-preview');
  if (now) { now.removeAttribute('aria-busy'); now.innerHTML = GS.error ? `<p class="error" role="alert">${esc(GS.error)}</p>` : gsPreviewHtml(); }
}

// The same piece of the Control panel at each level, so the choice can be seen before it is made.
function gsDemoHtml(level) {
  const menu = level === 'simple' ? 'Home · Assistant · Decide · Rules · More' : 'Home · Assistant · Decide · Control panel · Dashboard · Customers · More';
  return `<div class="view-demo" data-demo="${esc(level)}" data-testid="gs-demo" aria-label="Preview"><p class="demo-fold">Menu: ${esc(menu)}</p>
    <div class="field"><label>Most one customer may owe you in total</label>
      <p class="hint">Everything that customer would still owe you, across all their invoices, if the request is granted. Example with a limit of 1,000: a customer asks for more time on an invoice with 700 unpaid and also has another invoice with 400 unpaid, so 1,100 in all, which is over the limit and comes to you.</p>
      <input type="text" value="1,000.00" readonly tabindex="-1" aria-hidden="true"></div>
    <p class="demo-fold">${level === 'detailed' ? 'Every section is shown: suggestions, the team\'s model, versions, live counts.' : level === 'standard' ? 'Sections for occasional use are shown, each explanation in one line.' : 'Sections for occasional use are folded under "More settings".'}</p></div>`;
}

function gsBody() {
  const d = GS.data, saved = d.policy.version > 0;
  if (GS.step === 1) {
    const current = saved ? qsLevelOf(d.answers, d.levels) : null;
    return `<div class="gs-two"><div><h2>${icon('rules')}How strict should the agent be?</h2>
        <p class="hint keep">Customers ask for more time to pay. Inside the level you choose the agent answers by itself; everything else comes to you. The amounts come from your own open invoices. You can pause the agent or change any number later.</p>
        ${levelButtons(d.levels, GS.level, { custom: false, testid: 'gs-levels' })}
        <p class="row">${saved ? `<button type="button" class="btn small${GS.level ? '' : ' primary'}" data-testid="gs-keep" data-keep>Keep my rules as they are${current ? ' (' + esc((d.levels.find(l => l.name === current) || {}).label || '') + ')' : ''}</button> ` : ''}
          <a class="btn small" href="#/quick-setup" data-testid="gs-custom">Answer each question myself</a></p></div>
      <aside class="gs-side" aria-live="polite"><h3>What this would do</h3><div id="gs-preview">${gsPreviewHtml()}</div></aside></div>`;
  }
  if (GS.step === 2) {
    const held = new Set(GS.hold);
    return `<h2>${icon('user')}Any customer the agent must never decide for?</h2>
      <p class="hint keep">Tick the customers you want to handle personally. Their requests always come to you, whatever the level. Leave all empty if there is none.</p>
      <div class="gs-customers" data-testid="gs-customers">${d.customers.map(c => `<label class="choice"><input type="checkbox" name="gs-hold" value="${esc(c.id)}"${held.has(c.id) ? ' checked' : ''}><span>${esc(c.name)}</span></label>`).join('')
        || '<p class="muted">No customers are recorded yet.</p>'}</div>
      <h2>${icon('user')}New customers</h2>
      <div data-testid="gs-new">${radios({ name: 'gs-new', legend: 'When a new customer asks for a first order on credit', value: GS.newc, options: [
        { value: 'owner', label: 'It always comes to me', note: 'Nothing is decided for a new customer without you.' },
        { value: 'trial', label: 'The agent may give a small first order on credit', note: `Up to ${gsTrialText()} at risk after the deposit (the same limit as one request), a deposit of at least a quarter and up to 30 days to pay, once Staff confirm who the business is. Larger first orders come to you.` }] })}</div>`;
  }
  return `<div class="gs-two"><div><h2>${icon('eye')}How much should the pages show?</h2>
      <p class="hint keep">This changes only what you see in this browser, not what the agent does. Every setting stays available at every level.</p>
      ${viewChooser('gs-view')}</div>
    <aside class="gs-side"><h3>Preview</h3><div id="gs-demo-slot">${gsDemoHtml(viewLevel())}</div></aside></div>`;
}

function gsDoneHtml() {
  const assistant = assistantHref(), v = GS.done;
  return `<div class="callout ok" role="status" data-testid="gs-done"><p><b>${v.saved ? 'Saved as policy version ' + esc(v.version) + '.' : 'Your rules stay as they were (version ' + esc(v.version) + ').'}</b> The agent uses them from the next request.</p>
    <p>${assistant ? `<a class="btn primary" href="${esc(assistant)}" target="_blank" rel="noopener">Try a request in the assistant</a> ` : ''}<a class="btn${assistant ? '' : ' primary'}" href="#/review" data-testid="gs-to-decide">Open the Decide page</a>
      <a class="btn" href="#/">Home</a></p>
    <p class="hint keep">To change any of this later, open the <a href="#/delegation">Control panel</a>: the level, the customers and the display are at the top of it.</p></div>`;
}

function gsRender() {
  const main = $('#main');
  if (!main || S.route?.name !== 'get-started') return;
  const last = GS.step === 3;
  main.innerHTML = `<div class="page gs-page" data-testid="get-started-page" data-step="${GS.step}">
    ${pageHead({ title: 'Get started', lede: 'Three choices, then the agent is ready. Nothing is saved until the last step, and nothing is ever sent to a customer.' })}
    ${GS.done ? gsDoneHtml() : `${gsStepsHtml()}${gsBody()}
    <p class="error" id="gs-error" role="alert">${esc(GS.step === 1 ? '' : GS.error)}</p>
    <div class="gs-nav">${GS.step > 1 ? '<button type="button" class="btn" data-testid="gs-back">Back</button>' : '<a class="btn" href="#/">Not now</a>'}
      <button type="button" class="btn primary" data-testid="${last ? 'gs-finish' : 'gs-next'}">${last ? 'Save and finish' : 'Next'}</button></div>`}</div>`;
  if (GS.done) return;
  $$('[data-testid=gs-levels] [data-level]').forEach(b => { b.onclick = () => { GS.level = b.dataset.level; GS.preview = null; gsRender(); gsRunPreview(); }; });
  const keep = $('[data-keep]');
  if (keep) keep.onclick = () => { GS.level = null; GS.preview = null; gsRender(); gsRunPreview(); };
  $$('[name=gs-hold]').forEach(el => { el.onchange = () => { GS.hold = $$('[name=gs-hold]:checked').map(x => x.value); }; });
  $$('[name=gs-new]').forEach(el => { el.onchange = () => { if (el.checked) GS.newc = el.value; }; });
  bindViewChooser(main, level => { $('#gs-demo-slot').innerHTML = gsDemoHtml(level); renderFrameKeepMain(); });
  const back = $('[data-testid=gs-back]'), next = $('[data-testid=gs-next]'), finish = $('[data-testid=gs-finish]');
  if (back) back.onclick = () => { GS.step -= 1; GS.error = ''; gsRender(); };
  if (next) next.onclick = () => { GS.step += 1; gsRender(); $('#main').focus(); };
  if (finish) finish.onclick = () => gsFinish(finish);
}

// The menu follows the display level at once (simple shortens it); the page itself stays as it is.
function renderFrameKeepMain() {
  const main = $('#main'), kept = main ? [...main.childNodes] : [];
  renderFrame(S.route);
  const fresh = $('#main');
  if (fresh) kept.forEach(n => fresh.appendChild(n));
}

async function gsFinish(button) {
  await busy(button, async () => {
    try {
      const d = GS.data, sameHold = JSON.stringify([...GS.hold].sort()) === JSON.stringify([...(d.answers.holdCustomers || [])].sort());
      if (!GS.level && sameHold && GS.newc === (d.answers.newCustomers || 'owner') && d.policy.version > 0) { GS.done = { saved: false, version: d.policy.version }; gsRender(); return; }
      const out = await api('/api/delegation/quick-setup/preview', { answers: gsAnswers(), days: 14 }, { headers: qsCsrf() });
      const label = (d.levels.find(l => l.name === GS.level) || {}).label;
      const saved = await api('/api/delegation/policy', { ...out.policy, expectedVersion: d.policy.version, note: 'Saved from Get started' + (label ? ' (' + label + ')' : '') }, { method: 'PUT', headers: qsCsrf() });
      GS.done = { saved: true, version: saved.version };
      toast('Saved as version ' + saved.version, 'ok');
    } catch (error) {
      GS.error = error.code === 'POLICY_CHANGED' ? 'The rules were changed somewhere else while you were here. Open Get started again to see them.' : error.message;
    }
    gsRender();
  });
}

PAGES['get-started'] = async (r, seq) => {
  const main = $('#main');
  if (S.role !== 'owner') {
    main.innerHTML = `<div class="state-msg" data-testid="delegation-owner-only">${pageHead({ title: 'Get started' })}<p>Only the Owner sets how far the assistant may decide on its own.</p></div>`;
    return;
  }
  main.innerHTML = loading('the first steps');
  let data;
  try { data = await api('/api/delegation/quick-setup'); } catch (error) {
    if (!live(seq)) return;
    main.innerHTML = `<div class="page gs-page" data-testid="get-started-page">${pageHead({ title: 'Get started' })}
      <div class="callout warn" data-testid="gs-no-records"><p><b>First, your records.</b> ${esc(error.message)}</p><p><a class="btn primary" href="#/setup">Open Setup</a> <a class="btn" href="#/imports">Import invoices and payments</a></p></div></div>`;
    return;
  }
  if (!live(seq)) return;
  const saved = data.policy.version > 0;
  Object.assign(GS, { data, step: 1, level: saved ? null : 'balanced', hold: [...(data.answers.holdCustomers || [])], newc: data.answers.newCustomers || 'owner', preview: null, done: null, error: '' });
  gsRender();
  await gsRunPreview();
};
