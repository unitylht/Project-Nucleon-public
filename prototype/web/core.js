'use strict';
// Nucleon front end, shared core: formatting, the API, dialogs and feedback, sessions and roles, routing and the page frame.
// Pages live in requests.js, actions.js, delegation.js, customers.js, imports.js, knowledge.js, setup.js and console.js. No build step; loaded last, it starts the app.

// ---------------------------------------------------------------- formatting

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const utc = iso => new Date(iso + 'T00:00:00Z');
const dayNum = iso => Math.round(utc(iso).getTime() / 86400000);
// Business dates: "Fri 16 Oct 2026". Day counts use these, never the clock.
const dateText = (iso, year = true) => { if (!iso) return ''; const d = utc(iso); return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}${year ? ' ' + d.getUTCFullYear() : ''}`; };
const nextDay = iso => { const d = utc(iso); d.setUTCDate(d.getUTCDate() + 1); return d.toISOString().slice(0, 10); };
const days = n => n === 1 ? '1 day' : n + ' days';
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
// Recorded times: when something actually happened, on the real clock in Sydney time (QA U5: shown as such, next to a fixed business date).
const sydney = (iso, opts) => new Intl.DateTimeFormat('en-AU', { timeZone: 'Australia/Sydney', ...opts }).format(new Date(iso));
const timeText = iso => iso ? sydney(iso, { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';
const clockText = iso => iso ? sydney(iso, { hour: 'numeric', minute: '2-digit', second: '2-digit' }) : '';
const stamp = iso => iso ? `<time datetime="${esc(iso)}" title="Recorded on the real clock (Sydney time)">${esc(timeText(iso))}</time>` : '';
// Who decided, from the record itself (decisionSource, else the actor in decidedBy), never from who normally decides.
// subject: 'The owner' / 'Staff, within the owner\'s authority'; a decision with neither says so.
// A named actor (the AI Agent) is named with the role it acted as; the ordinary demo actors keep their words (`plain`).
const actorWho = (rec, plain) => rec?.actorName ? `${rec.actorName} (as ${rec.actorRole})` : plain;
const AGENT_ID = 'ai_agent';
function deciderText(d) {
  const src = d?.decisionSource, by = String(d?.decidedBy || '');
  if (src === 'delegated_policy') return `Decided by the agent under Owner policy v${d.authority?.policyVersion ?? '?'}`;
  if (src === 'owner_override') return 'The owner (overriding an earlier approval)';
  if (d?.actorName) return actorWho(d) + (src === 'staff_within_authority' ? ", within the owner's authority" : '');
  if (src === 'staff_within_authority') return "Staff, within the owner's authority";
  if (src === 'owner') return 'The owner';
  return /^staff/i.test(by) ? 'Staff' : /^owner/i.test(by) ? 'The owner' : 'Not recorded';
}
const money = m => {   // integer minor units, never floats; negative amounts (credits) keep their sign
  const n = BigInt(m.minorUnits), a = n < 0n ? -n : n, f = 10n ** BigInt(m.scale);
  return `${m.currency} ${n < 0n ? '−' : ''}${(a / f).toLocaleString('en-AU')}${m.scale ? '.' + (a % f).toString().padStart(m.scale, '0') : ''}`;
};
const plainAmount = m => m ? money(m).replace(/^[A-Z]{3} /, '').replace(/,/g, '') : '';
// The page may be served under a path prefix ('/preview/' behind a proxy): API calls and storage keys follow it, so two
// instances on one host share neither. At '/' the base is '' and the keys are 'nucleon.*', as before.
const BASE_PATH = location.pathname.replace(/\/[^/]*$/, '');
const STORAGE = 'nucleon' + BASE_PATH.replace(/\//g, '-') + '.';
const store = (k, v) => { try { v === undefined ? localStorage.removeItem(STORAGE + k) : localStorage.setItem(STORAGE + k, v); } catch { /* storage may be blocked */ } };
const stored = k => { try { return localStorage.getItem(STORAGE + k); } catch { return null; } };
const remember = (k, v) => { try { v === undefined ? sessionStorage.removeItem(STORAGE + k) : sessionStorage.setItem(STORAGE + k, v); } catch { /* ignore */ } };
const recalled = k => { try { return sessionStorage.getItem(STORAGE + k); } catch { return null; } };

// The certainty of an amount, always shown with it: exact, at most, stated as of a date, worked out by the replay, or not recorded. The
// line style of the mark carries the meaning (solid, dashed, dotted, double), so it reads the same everywhere and without colour.
function certainty(kind, amount, detail = '') {
  const label = { exact: 'Exact', atMost: 'At most', stated: 'Stated', workedOut: 'Worked out', none: 'Not recorded', settled: 'Settled', recorded: 'As recorded' }[kind];
  return `<span class="amount ${kind}">${amount ? `<span class="figure">${esc(amount)}</span>` : ''}<span class="sure">${esc(label)}</span>${detail ? `<span class="sure-detail">${esc(detail)}</span>` : ''}</span>`;
}

// What a customer owes now, worked out by the same replay as the assessment, with its parts (positions.customers[id].owed). The
// recorded invoices less recorded payments leaves out the opening balance and is shown apart, never as this.
function owedNowHtml(o) {
  const some = m => m && BigInt(m.minorUnits) > 0n;
  const parts = [[o.overdue, 'overdue'], [o.notYetDue, 'not yet due'], [o.noDueDate, 'with no due date, so overdue is not known'],
                 [o.openingOwing, `left of the opening balance of ${money(o.openingBalance)}, of unknown age`]].filter(([m]) => some(m));
  const said = [parts.length ? parts.map(([m, w]) => `${money(m)} ${w}`).join('; ') + '.' : '',
                o.openingPaid ? `The opening balance of ${money(o.openingBalance)} was paid by earlier payments, oldest first.` : '',
                some(o.creditHeld) ? `Customer credit held ${money(o.creditHeld)}.` : '', o.incompleteText || ''].filter(Boolean);
  if (!said.length) return certainty('workedOut', money(o.owedNow));
  // the parts open beside a wide page's figure; on a phone they fold under it (one tap), so the records stay on the first screen
  return `<details class="owed-details"${innerWidth >= 700 ? ' open' : ''}><summary>${certainty('workedOut', money(o.owedNow))}<span class="owed-toggle">parts</span></summary><span class="owed-parts">${esc(said.join(' '))}</span></details>`;
}

// ---------------------------------------------------------------- API

const ROLE_NAMES = { staff: 'Staff', owner: 'Owner', operator: 'Demo console' };
const S = { session: null, held: [], role: stored('role'), seq: 0, epoch: 0, route: null, cases: [], current: null, model: null, keys: {}, busy: false,
            drafts: {}, poll: null, justDecided: null, notice: null };

// S.epoch changes at sign-out: a response to a request made before it is dropped, so nothing signed out is ever drawn again.
async function api(path, body, { key, role, timeout = 0, headers: more, method } = {}) {
  const epoch = S.epoch;
  const headers = { ...more };   // more: extra headers (the confirmation page's X-Nucleon-CSRF)
  const acting = role === undefined ? S.role : role;
  if (acting) headers['X-Nucleon-Role'] = acting;
  if (acting && S.agent && role === undefined) headers['X-Nucleon-Follow-Role'] = '1';   // the AI Agent's page follows the shared role
  const options = { headers };
  if (body !== undefined) {
    options.method = method || 'POST';   // PUT saves the Owner's delegation policy
    headers['Content-Type'] = 'application/json';
    if (key) headers['Idempotency-Key'] = key;
    options.body = JSON.stringify(body);
  }
  const stale = () => Object.assign(new Error('Signed out.'), { code: 'SIGNED_OUT' });
  const abort = timeout ? new AbortController() : null;
  if (abort) { options.signal = abort.signal; setTimeout(() => abort.abort(), timeout); }
  let response;
  try { response = await fetch(BASE_PATH + path, options); } catch {
    if (epoch !== S.epoch) throw stale();
    throw Object.assign(new Error('The app could not be reached. Check the connection, then try again.'), { code: 'NETWORK' });
  }
  let data = {};
  try { data = await response.json(); } catch { /* empty body */ }
  if (epoch !== S.epoch) throw stale();
  if (!response.ok && data.error === 'ROLE_CHANGED' && S.session) {   // the AI Agent's role was switched in another tab or the Lab: follow it
    S.session = null;
    loadSession().then(() => route()).catch(() => {});
  }
  if (!response.ok) throw Object.assign(new Error(data.message || 'That didn\'t work. Try again.'), { code: data.error, field: data.field, status: response.status, impact: data.impact, data });
  return data;
}
// One idempotency key per distinct action and payload, kept until it succeeds, so a retry can't act twice.
const keyFor = id => (S.keys[id] ??= crypto.randomUUID());
const keyDone = id => { delete S.keys[id]; };

// ---------------------------------------------------------------- feedback

function toast(text, kind = '') {
  if (!S.session) return;   // nothing is announced over the sign-in or sign-out pages
  const t = $('#toast');
  t.textContent = text;
  t.className = 'toast ' + kind;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}

async function busy(button, work) {
  if (S.busy) return;
  S.busy = true;
  const label = button?.innerHTML;
  if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  try { await work(); } finally {
    S.busy = false;
    if (button?.isConnected) { button.disabled = false; button.removeAttribute('aria-busy'); button.innerHTML = label; }
  }
}

function clearErrors(form) {
  $$('.error', form).forEach(e => { e.textContent = ''; });
  $$('[aria-invalid]', form).forEach(e => e.removeAttribute('aria-invalid'));
}

// An error goes next to its field when the server names one, else at the top of the form. The field is focused.
function showErrors(form, error) {
  if (error?.code === 'SIGNED_OUT') return;
  clearErrors(form);
  const input = error.field && form.querySelector(`[name="${error.field}"]`);
  const slot = (input && form.querySelector(`[data-error-for="${error.field}"]`)) || form.querySelector('[data-error-for="form"]');
  if (input) { input.setAttribute('aria-invalid', 'true'); input.focus(); }
  if (slot) slot.textContent = error.message;
  else toast(error.message, 'bad');
}

// Form fields. Every input has a visible label, optional help, and an error slot announced to screen readers.
function field({ name, label, type = 'text', value = '', hint = '', optional = false, id, attrs = '', rows }) {
  const fid = id || 'f-' + name;
  const control = type === 'textarea' ? `<textarea id="${fid}" name="${name}" rows="${rows || 3}" ${attrs}${hint ? ` aria-describedby="${fid}-hint"` : ''}>${esc(value)}</textarea>`
    : `<input id="${fid}" name="${name}" type="${type}" value="${esc(value)}" ${attrs}${hint ? ` aria-describedby="${fid}-hint"` : ''}>`;
  return `<div class="field"><label for="${fid}">${esc(label)}${optional ? ' <span class="opt">(optional)</span>' : ''}</label>
    ${hint ? `<p class="hint" id="${fid}-hint">${hint}</p>` : ''}${control}<p class="error" data-error-for="${name}" role="alert"></p></div>`;
}
function selectField({ name, label, options, value = '', hint = '', optional = false, id, placeholder = 'Choose…' }) {
  const fid = id || 'f-' + name;
  return `<div class="field"><label for="${fid}">${esc(label)}${optional ? ' <span class="opt">(optional)</span>' : ''}</label>
    ${hint ? `<p class="hint" id="${fid}-hint">${hint}</p>` : ''}<select id="${fid}" name="${name}"${hint ? ` aria-describedby="${fid}-hint"` : ''}>
    ${placeholder === null ? '' : `<option value="">${esc(placeholder)}</option>`}${options.map(o => `<option value="${esc(o.value)}"${String(o.value) === String(value) ? ' selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
    <p class="error" data-error-for="${name}" role="alert"></p></div>`;
}
function radios({ name, legend, options, value = '', hint = '' }) {
  return `<fieldset class="choices"><legend>${esc(legend)}</legend>${hint ? `<p class="hint">${hint}</p>` : ''}
    ${options.map(o => `<label class="choice"><input type="radio" name="${name}" value="${esc(o.value)}"${String(o.value) === String(value) ? ' checked' : ''}><span>${esc(o.label)}${o.note ? `<small>${esc(o.note)}</small>` : ''}</span></label>`).join('')}
    <p class="error" data-error-for="${name}" role="alert"></p></fieldset>`;
}
const formError = () => '<p class="error form-error" data-error-for="form" role="alert"></p>';
// A form where nobody should have to guess (the Owner's Control panel and Quick setup, 11 Nov 2026): every text or select field is marked "Required" or
// "Optional" in words, the input says so to a screen reader, and one line at the top explains the two. Call it after the form is drawn.
const REQUIRED_LEGEND = '<p class="hint req-legend" data-testid="required-legend"><span class="req">Required</span> must be filled in. <span class="opt">Optional</span> can be left empty.</p>';
function markRequired(form) {
  if (!form) return;
  $$('.field', form).forEach(f => {
    const label = f.querySelector('label'), control = f.querySelector('input, select, textarea'), opt = label?.querySelector('.opt');
    if (!label || !control || label.querySelector('.req')) return;
    if (opt) opt.textContent = 'Optional';
    else { label.insertAdjacentHTML('beforeend', ' <span class="req">Required</span>'); control.setAttribute('aria-required', 'true'); }
  });
  form.classList.add('marked');
}

// ---------------------------------------------------------------- dialogs

// A modal dialog for creating, correcting, removing and confirming. Closing it keeps what was typed (until it is saved), so
// reopening the same dialog restores the draft. `submit(form, values)` returns true when the dialog should close.
function openDialog(options) {
  const { key, title, intro = '', body, submitLabel, danger = false, wide = false, submit, onOpen, cancelLabel = 'Cancel', noSubmit = false } = options;
  const d = document.createElement('dialog');
  d.className = 'dialog' + (wide ? ' wide' : '');
  d.setAttribute('aria-labelledby', 'dlg-title');
  d.innerHTML = `<form method="dialog" class="dialog-form" novalidate>
      <header class="dialog-head"><h2 id="dlg-title">${esc(title)}</h2><button type="button" class="icon-btn" data-close aria-label="Close">×</button></header>
      <div class="dialog-body">${intro ? `<p class="lede">${intro}</p>` : ''}<div class="restored" hidden></div>${body}${formError()}</div>
      <footer class="dialog-foot">${noSubmit ? '' : `<button type="submit" class="btn ${danger ? 'danger solid' : 'primary'}">${esc(submitLabel)}</button>`}
        <button type="button" class="btn" data-close>${noSubmit ? 'Close' : esc(cancelLabel)}</button></footer></form>`;
  document.body.append(d);
  const form = $('form', d);
  const saved = key && S.drafts[key];
  if (saved) {
    for (const [name, v] of Object.entries(saved)) {
      const els = form.elements[name];
      if (!els) continue;
      if (els instanceof RadioNodeList || els.type === 'radio') { $$(`[name="${name}"]`, form).forEach(r => { r.checked = r.value === v; }); }
      else if (els.type === 'checkbox') els.checked = v === true;
      else els.value = v;
    }
    const note = $('.restored', d);
    note.hidden = false;
    note.innerHTML = 'Restored what you typed before. <button type="button" class="btn link" data-forget>Start again</button>';
    $('[data-forget]', note).onclick = () => { forget = true; delete S.drafts[key]; S.afterDialog = () => openDialog(options); d.close(); };
  }
  let done = false, forget = false;
  const snapshot = () => {
    const values = {};
    for (const el of form.elements) {
      if (!el.name || el.type === 'submit' || el.type === 'button' || el.type === 'file') continue;
      if (el.type === 'radio') { if (el.checked) values[el.name] = el.value; } else if (el.type === 'checkbox') values[el.name] = el.checked; else values[el.name] = el.value;
    }
    return values;
  };
  const initial = JSON.stringify(snapshot());
  d.addEventListener('close', () => {
    if (key && !done && !forget && S.session && JSON.stringify(snapshot()) !== initial) { S.drafts[key] = snapshot(); toast('Draft kept. Open it again to carry on.'); }
    d.remove();
    if (S.afterDialog) { const f = S.afterDialog; S.afterDialog = null; f(); }
  });
  $$('[data-close]', d).forEach(b => { b.onclick = () => d.close(); });
  form.onsubmit = event => {
    event.preventDefault();
    const button = $('[type=submit]', form);
    busy(button, async () => {
      clearErrors(form);
      const closed = await submit(form, d);
      if (closed) { done = true; if (key) delete S.drafts[key]; d.close(); }
    });
  };
  d.showModal();
  if (onOpen) onOpen(form, d);
  const first = form.querySelector('[aria-invalid], input:not([type=hidden]):not([disabled]), select, textarea');
  (first || $('[type=submit]', form) || $('[data-close]', d))?.focus();
  return d;
}

// Run an API action from a dialog form. Field errors land next to the field; returns the result, or null on error.
async function dialogAction(form, path, body, key, done) {
  const id = path + ':' + JSON.stringify(body);
  try {
    const result = await api(path, body, { key: keyFor(key || id) });
    keyDone(key || id);
    if (done) toast(done, 'ok');
    return result;
  } catch (error) { showErrors(form, error); return { error }; }
}

// ---------------------------------------------------------------- sessions and roles

async function loadSession(preferred) {
  const probe = await api('/api/session', undefined, { role: '' });
  S.held = probe.signedIn || [];
  S.agent = probe.identity?.kind === 'agent';
  // The AI Agent has one selected role, shared with the Lab and every tab through the Lab's cookie: the server names it.
  const shared = S.agent && probe.selectedRole;
  const want = (shared && S.held.includes(shared) ? [preferred, shared] : [preferred, S.role, stored('role')]).find(r => r && S.held.includes(r)) || (S.agent && S.held.includes('staff') ? 'staff' : S.held.find(r => r !== 'operator')) || S.held[0];
  if (!want) { S.session = null; S.role = null; return; }
  S.role = want;
  store('role', want);
  if (S.agent && want !== 'operator' && shared !== want) {   // record the choice where the Lab reads it (Path: the Lab's root, above these pages)
    const path = BASE_PATH.replace(/\/records$/, '') || '/';
    try { await api('/api/session/role', { role: want, path }, { role: '' }); } catch { /* the choice still holds in this tab */ }
  }
  S.session = await api('/api/session');
}

// The sign-in screen. With a role in mind (switching to the owner, opening the console) it asks for that role's code and refuses
// another role's code with a message (QA U2). A browser already holding a role can continue as it, or sign out (QA U11).
function renderGate(intent, notice) {
  stopPolling();
  S.route = { name: 'gate' };
  document.title = 'Sign in · Nucleon';
  const role = intent && ROLE_NAMES[intent] ? intent : null;
  const heading = role === 'operator' ? 'Open the demo console' : role ? `Sign in as ${ROLE_NAMES[role].toLowerCase()}` : 'Sign in to Nucleon';
  const lede = role === 'operator' ? 'Enter the demo console code. The console resets and restores the practice data for presentations.'
    : role === 'owner' ? 'Enter the owner code. The owner decides requests and confirms what the records say.'
    : role === 'staff' ? 'Enter the staff code. Staff send requests to the agent and keep the records up to date.'
    : 'Payment extension requests, prepared by an agent for the owner to decide. Enter your access code: it decides whether you work as staff or as the owner.';
  const others = S.held.filter(r => r !== role);
  $('#root').innerHTML = `
    <main class="gate" id="main">
      <form id="signin" novalidate>
        <p class="brandmark">Nucleon</p>
        <h1>${esc(heading)}</h1>
        <p class="lede">${esc(lede)}</p>
        ${notice ? `<p class="callout ok" role="status">${esc(notice)}</p>` : ''}
        ${field({ name: 'accessCode', label: 'Access code', type: 'password', id: 'code', attrs: 'autocomplete="off" required spellcheck="false"' })}
        ${formError()}
        <button class="btn primary wide" type="submit">${role ? `Sign in as ${esc(ROLE_NAMES[role].toLowerCase())}` : 'Sign in'}</button>
        ${others.length ? `<div class="held"><p>Already signed in here as ${esc(others.map(r => ROLE_NAMES[r]).join(' and '))}.</p>
          <div class="row">${others.map(r => `<button type="button" class="btn" data-continue="${r}">Continue as ${esc(ROLE_NAMES[r].toLowerCase())}</button>`).join('')}
          <button type="button" class="btn link" id="gate-signout">Sign out of this browser</button></div></div>` : ''}
        <p class="fine">Codes are given out privately. Never put a code in a screenshot or a document.</p>
      </form>
    </main>`;
  const form = $('#signin');
  $('#code').focus();
  form.onsubmit = event => {
    event.preventDefault();
    busy($('[type=submit]', form), async () => {
      clearErrors(form);
      const code = $('#code').value.trim();
      if (!code) return showErrors(form, { field: 'accessCode', message: 'Enter the access code.' });
      try {
        const actor = await api('/api/demo/login', role ? { accessCode: code, role } : { accessCode: code }, { role: '' });
        setSignout(null);   // a sign-in here ends any sign-out still pending in this browser
        await loadSession(actor.role);
        if (actor.role === 'operator') location.hash = '#/console';
        else if (readRoute().name === 'console') location.hash = '#/';
        await route();
      } catch (error) {
        showErrors(form, error.code === 'FORBIDDEN' ? { field: 'accessCode', message: 'That code isn\'t valid. Check it and try again.' } : error);
      }
    });
  };
  $$('[data-continue]', form).forEach(b => {
    b.onclick = async () => { await loadSession(b.dataset.continue); if (b.dataset.continue === 'operator') location.hash = '#/console'; else if (readRoute().name === 'console') location.hash = '#/'; await route(); };
  });
  const out = $('#gate-signout');
  if (out) out.onclick = signOut;
}

async function switchRole(role) {
  if (role === S.role) return;
  trackLeave(); flushTrack();   // reported under the role it happened in
  if (!S.held.includes(role)) return renderGate(role);
  await loadSession(role);
  const here = readRoute();
  if (here.name === 'console' || (here.owner && role !== 'owner')) location.hash = '#/';   // the console and the Owner's pages are not there for the other role
  await route();
}

// Sign out ends every role this browser holds (QA B1); people signed in on other browsers are not affected.
// It is reported as done only when the server shows no session for this browser. Until then the page shows nothing signed in,
// local drafts are gone, and every tab of this browser follows (the state is shared through localStorage).
const SIGNOUT_TIMEOUT = 10000;
const signoutState = () => { try { return JSON.parse(stored('signout') || 'null'); } catch { return null; } };
const setSignout = state => store('signout', state ? JSON.stringify({ state, at: Date.now() }) : undefined);

// Remove what this browser keeps for the signed-in user: the request draft, this tab's filters and searches, dialog drafts,
// and the records, cases and console state held in memory.
function forgetLocal() {
  store('draft'); store('role');
  try { Object.keys(sessionStorage).filter(k => k.startsWith(STORAGE)).forEach(k => sessionStorage.removeItem(k)); } catch { /* storage may be blocked */ }
  S.drafts = {}; S.keys = {}; S.cases = []; S.current = null; S.justDecided = null;
  if (typeof R !== 'undefined') Object.assign(R, { setup: null, data: null, imports: [], ix: null });
  if (typeof CONSOLE !== 'undefined') Object.assign(CONSOLE, { state: null, last: null });
}

// Stop everything signed in: late responses are dropped, timers stop, dialogs close without keeping drafts.
function leaveSignedIn() {
  TRACK.queue = []; TRACK.page = null; TRACK.since = null; TRACK.acc = 0; clearTimeout(TRACK.timer); TRACK.timer = null;
  S.epoch += 1; S.seq += 1;
  S.session = null; S.role = null; S.held = [];
  stopPolling();
  closeDialogs();
  const t = $('#toast'); if (t) { t.hidden = true; t.textContent = ''; }
}

async function signOut() {
  trackLeave(); flushTrack();   // what this page reported so far goes before the session ends
  leaveSignedIn();
  forgetLocal();
  setSignout('pending');
  await confirmSignOut();
}

async function confirmSignOut() {
  renderSignoutState('pending');
  let ended = null, probe = null;
  try { ended = (await api('/api/demo/logout', {}, { role: '', timeout: SIGNOUT_TIMEOUT })).signedOut || []; } catch { /* checked below */ }
  try { probe = await api('/api/session', undefined, { role: '', timeout: SIGNOUT_TIMEOUT }); } catch { /* not confirmed */ }
  if (probe && !(probe.signedIn || []).length) {
    setSignout('done');
    history.replaceState(null, '', '#/');
    return renderGate(null, ended === null ? 'Signed out. The server shows no session for this browser.'
      : ended.length ? `Signed out of ${ended.map(r => ROLE_NAMES[r].toLowerCase()).join(' and ')} in this browser.` : 'Signed out.');
  }
  setSignout('unconfirmed');
  renderSignoutState('unconfirmed', { reached: ended !== null, held: probe?.signedIn || null });
}

// The pages shown while a sign-out is pending or could not be confirmed: nothing signed in, and one action.
function renderSignoutState(state, { reached = false, held = null, elsewhere = false } = {}) {
  stopPolling();
  S.route = { name: 'signout' };
  document.title = 'Signing out · Nucleon';
  const heading = state === 'pending' ? (elsewhere ? 'Signing out in another tab' : 'Signing out') : 'Sign-out not confirmed';
  const why = state === 'pending' ? '<p class="lede" role="status">Ending your session on the server.</p>'
    : `<p class="lede">This page shows no records, and drafts kept in this browser were removed.</p>
       <p class="lede"><b>${held && held.length
        ? `${reached ? '' : 'The app did not receive confirmation of the sign-out request. '}The server still has a session for this browser (${esc(held.map(r => ROLE_NAMES[r].toLowerCase()).join(' and '))}), so it could still be used here.`
        : reached ? 'The server answered, but the app could not check that your session ended.'
        : 'The app did not receive confirmation of the sign-out request and could not check with the server, so your session may still be active.'}</b></p>
       <p class="lede">Try again once the connection is back. If it keeps failing, ask whoever runs the app to restart it, which ends every session. Quitting the browser removes its copy of the session, but the server keeps it until then.</p>`;
  $('#root').innerHTML = `<main class="gate" id="main"><div class="signout-card" data-testid="${state === 'pending' ? 'signout-pending' : 'signout-unconfirmed'}"${elsewhere ? ' data-elsewhere="true"' : ''}>
      <p class="brandmark">Nucleon</p><h1>${esc(heading)}</h1>${why}
      ${state === 'pending' ? '' : '<button type="button" class="btn primary wide" data-testid="signout-retry">Try signing out again</button>'}
    </div></main>`;
  const retry = $('[data-testid=signout-retry]');
  if (retry) retry.onclick = () => busy(retry, async () => { setSignout('pending'); await confirmSignOut(); });
}

// Another tab of this browser signed out, or signed in again: follow it.
function followOtherTab() {
  const s = signoutState();
  if (!s) {   // signed in again elsewhere: show what this browser now holds
    if (!S.session && S.route?.name === 'signout') loadSession().then(route).catch(() => renderGate());
    return;
  }
  leaveSignedIn();
  forgetLocal();
  if (s.state === 'done') {
    history.replaceState(null, '', '#/');
    renderGate(null, 'Signed out in another tab of this browser.');
    $('#signin').dataset.testid = 'signed-out-elsewhere';
  } else renderSignoutState(s.state, { elsewhere: true });
}

// ---------------------------------------------------------------- page-use telemetry (D11)

// What the pages report about their own use: entering and leaving a page (with the time on it), a click on an element marked data-track="<name>", and how long a decision
// took (decide_start / decide_done). Local only: POST /api/ui-events stores it in this machine's database, the Owner's dashboard summarises it, nothing goes to any other
// service. Only a person's session reports (the AI Agent's page and any service do not); the server drops more than 60 events a minute without an error. The page names
// routes and buttons, never a customer, a case or anything typed. A failed report is forgotten: it never gets in the way of the page.
const TRACK = { queue: [], page: null, since: null, acc: 0, timer: null };
const tracking = () => !!S.session && !S.agent && (S.role === 'staff' || S.role === 'owner');
function trackEvent(kind, data, page) {
  if (!tracking()) return;
  const name = page || TRACK.page;
  if (!name || !/^[a-z][a-z0-9-]{0,39}$/.test(name)) return;
  TRACK.queue.push({ page: name, kind, ...(data ? { data } : {}), at: new Date().toISOString() });
  if (TRACK.queue.length > 200) TRACK.queue.splice(0, TRACK.queue.length - 200);
  if (TRACK.queue.length >= 20) flushTrack(); else if (!TRACK.timer) TRACK.timer = setTimeout(() => flushTrack(), 5000);
}
const dwellMs = () => Math.round(TRACK.acc + (TRACK.since !== null ? performance.now() - TRACK.since : 0));   // the time the page was visible
function trackLeave() {
  if (TRACK.page && tracking()) trackEvent('page_leave', { ms: dwellMs() }, TRACK.page);
  TRACK.page = null; TRACK.since = null; TRACK.acc = 0;
}
function trackRoute(next) {   // a move to another page: leave the one before, enter this one
  trackLeave();
  if (!tracking() || ['gate', 'signout', 'console', 'notfound'].includes(next.name)) return;
  TRACK.page = next.name; TRACK.since = document.visibilityState === 'visible' ? performance.now() : null;
  trackEvent('page_enter', undefined, next.name);
}
// unloading: sendBeacon cannot carry the role header, so it names the role in the address
function flushTrack(unloading = false) {
  clearTimeout(TRACK.timer); TRACK.timer = null;
  if (!tracking()) { TRACK.queue = []; return; }
  while (TRACK.queue.length) {
    const body = JSON.stringify(TRACK.queue.splice(0, 50)), url = BASE_PATH + '/api/ui-events';
    let sent = false;
    if (unloading && navigator.sendBeacon) { try { sent = navigator.sendBeacon(url + '?role=' + encodeURIComponent(S.role), new Blob([body], { type: 'application/json' })); } catch { /* fall back below */ } }
    if (!sent) fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Nucleon-Role': S.role }, body, keepalive: true }).catch(() => {});
    if (!unloading) break;   // the rest goes with the next timer (the server keeps 60 a minute anyway)
  }
  if (TRACK.queue.length && !TRACK.timer) TRACK.timer = setTimeout(() => flushTrack(), 2000);
}
function trackVisibility() {
  if (document.visibilityState === 'hidden') {
    if (TRACK.since !== null) { TRACK.acc += performance.now() - TRACK.since; TRACK.since = null; }
    flushTrack(true);
  } else if (TRACK.page && TRACK.since === null) TRACK.since = performance.now();
}
// A decision's duration: the Owner's first move on a decision form to its recorded result (the Decide page calls these).
const DECIDING = {};
function decideStart(id) { if (!DECIDING[id]) { DECIDING[id] = performance.now(); trackEvent('decide_start', undefined, 'review'); } }
function decideDone(id, name, ok) {
  const t0 = DECIDING[id] ?? performance.now();
  delete DECIDING[id];
  trackEvent('decide_done', { name, ms: Math.round(performance.now() - t0), ok: !!ok }, 'review');
}

// ---------------------------------------------------------------- routing

// Routes are hash paths so links can be shared: #/ (home), #/cases, #/case/<id>, #/review, #/dashboard, #/decision-cases/<id>, #/actions/<id>, #/customers/<id>?from=<case id>, #/imports/<id> …
function readRoute() {
  const raw = location.hash.replace(/^#\/?/, '');
  const [path, query = ''] = raw.split('?');
  const q = Object.fromEntries(new URLSearchParams(query));
  const p = path.split('/').filter(Boolean);
  // #/ is the role landing page (home.js). The request queue is #/cases (#/requests, which earlier links used, is the same), its form
  // #/cases/new. The Records desk chat that was the landing page was removed on 31 Oct 2026.
  if (!p.length) return { name: 'home', area: 'home', q };
  if (p[0] === 'cases' || p[0] === 'requests') return { name: p[1] === 'new' ? 'compose' : 'requests', area: 'requests', q };
  if (p[0] === 'case' && p[1]) return { name: 'case', area: 'requests', id: p[1], q };
  if (p[0] === 'actions' && p[1]) return { name: 'action', area: 'requests', id: p[1], q };   // the confirmation page of an action the assistant prepared (actions.js)
  if (p[0] === 'customers') return p[1] ? { name: 'customer', area: 'customers', id: p[1], tab: p[2] || q.tab || 'invoices', q } : { name: 'customers', area: 'customers', q };
  if (p[0] === 'completeness') return { name: 'completeness', area: 'customers', q };
  if (p[0] === 'imports') return p[1] === 'new' ? { name: 'import-new', area: 'imports', q } : p[1] ? { name: 'import', area: 'imports', id: p[1], q } : { name: 'imports', area: 'imports', q };
  if (p[0] === 'knowledge') return { name: 'knowledge', area: 'knowledge', q };
  if (p[0] === 'setup') return { name: 'setup', area: 'setup', q };
  if (p[0] === 'delegation') return { name: 'delegation', area: 'delegation', q };   // the Owner's control panel: delegation policy and decisions (delegation.js)
  if (p[0] === 'quick-setup') return { name: 'quick-setup', area: 'delegation', owner: true, q };
  if (p[0] === 'get-started') return { name: 'get-started', area: 'home', owner: true, q };   // the Owner's first run in three steps (getstarted.js)
  if (p[0] === 'doctor') return { name: 'doctor', area: 'delegation', owner: true, q };   // the Owner's questions about how the setup is working (doctor.js)   // the Owner's first setup in a few questions (quicksetup.js)
  if (p[0] === 'review' || p[0] === 'dashboard' || p[0] === 'research') return { name: p[0], area: p[0], owner: true, q };   // review.js, dashboard.js, research.js (the Model page)   // the Owner's batch review (review.js) and dashboard (dashboard.js)
  if (p[0] === 'decision-cases' && p[1]) return { name: 'decision-case', area: S.role === 'owner' ? 'review' : 'requests', id: p[1], q };   // one case's timeline (timeline.js), for the Owner and Staff
  if (p[0] === 'console') return { name: 'console', area: 'console', q };
  if (p[0] === 'records') return { name: 'customers', area: 'customers', q, legacy: true };   // links from the earlier version
  return { name: 'notfound', area: '', q };
}

const PAGES = {};   // name → render(route, seq), registered by the page files
// True while the page that started an async load is still the one on screen (QA B7: no rendering into a page that has gone).
const live = seq => seq === S.seq;

async function route() {
  const next = readRoute();
  S.leaveGuard = null; S.leaveDirty = null;   // a page that wants one sets it when it renders
  S.seq += 1;
  const seq = S.seq;
  stopPolling();
  closeDialogs();
  if (!S.session) return renderGate(next.name === 'console' ? 'operator' : null);
  if (next.name === 'console' && S.role !== 'operator') {
    if (S.held.includes('operator')) await loadSession('operator');
    else return renderGate('operator');
  }
  if (next.name !== 'console' && S.role === 'operator') {
    const caseRole = S.held.find(r => r !== 'operator');
    if (caseRole) await loadSession(caseRole);
    else return renderGate(null);
  }
  if (!live(seq)) return;
  if (next.legacy) { history.replaceState(null, '', '#/customers'); }
  if (next.owner && S.role !== 'owner') { next.name = 'notfound'; next.area = ''; }   // the Owner's pages are not there for Staff
  // Before setup, the workspace has nothing to check requests against: setup comes first.
  if (S.role !== 'operator' && !S.session.workspace && next.area !== 'setup') { history.replaceState(null, '', '#/setup'); return route(); }
  // Another page or record starts at its top; the same page drawn again (after a change, or another tab) keeps its place.
  const moved = S.route?.name !== next.name || S.route?.id !== next.id;
  S.route = next;
  if (moved) trackRoute(next);
  renderFrame(next);
  if (moved) scrollTo(0, 0);
  const page = PAGES[next.name] || PAGES.notfound;
  try { await page(next, seq); } catch (error) { if (live(seq)) renderFailure(error, () => route()); }
}

function closeDialogs() { $$('dialog[open]').forEach(d => d.close()); }

// A page that could not load says what failed and offers to try again.
function renderFailure(error, retry, target = '#main') {
  const el = $(target);
  if (!el || error?.code === 'SIGNED_OUT' || !S.session) return;
  if (error?.status === 401) { S.session = null; return renderGate(null, 'Your session ended, for example because the app restarted. Sign in again.'); }
  el.innerHTML = `<div class="state-msg" role="alert"><h2>This page didn't load</h2><p>${esc(error?.message || 'Something went wrong.')}</p>
    <button type="button" class="btn primary" id="retry">Try again</button></div>`;
  $('#retry').onclick = retry;
}
const loading = what => `<p class="state-msg loading" role="status"><span class="spinner" aria-hidden="true"></span>Loading ${esc(what)}…</p>`;

// ---------------------------------------------------------------- the frame: header, navigation, page

// One navigation for both roles, kept short (11 Nov 2026: the owners and both testers found eleven tabs overwhelming). top: the roles that see the page in the
// bar itself; every other page the role may open sits under "More". phone: the roles that get it in the phone tab bar (four at most, then "More").
// owner: the Owner's own pages; external: the assistant, which opens in a new tab and is offered only when the config gives its address (assistantUrl).
const NAV = [
  { area: 'home', href: '#/', label: 'Home', top: ['owner', 'staff'], phone: ['owner', 'staff'] },
  { area: 'assistant', label: 'Assistant', external: true, top: ['owner', 'staff'] },
  { area: 'review', href: '#/review', label: 'Decide', owner: true, top: ['owner'], phone: ['owner'] },   // the Owner's work list: decide, agree, disagree, override (review.js)
  { area: 'requests', href: '#/cases', label: 'Requests', top: ['staff'], phone: ['staff'] },
  { area: 'delegation', href: '#/delegation', label: 'Control panel', owner: true, top: ['owner'], phone: ['owner'] },   // the Owner's page (delegation.js); not offered to staff
  { area: 'dashboard', href: '#/dashboard', label: 'Dashboard', owner: true, top: ['owner'], phone: ['owner'] },
  { area: 'customers', href: '#/customers', label: 'Customers', top: ['owner', 'staff'], phone: ['staff'] },
  { area: 'imports', href: '#/imports', label: 'Imports', phone: ['staff'] },
  { area: 'research', href: '#/research', label: 'Model', owner: true },   // the team's classifier as a shadow (research.js)
  { area: 'knowledge', href: '#/knowledge', label: 'Knowledge' },
  { area: 'setup', href: '#/setup', label: 'Setup' },
];

// ---------------------------------------------------------------- how much the Owner's pages show (12 Nov 2026)
// Owners asked for "a simplified view and an advanced view": the settings are worth having, the words around them are not needed every day. Three levels, kept
// in this browser (each person chooses their own): simple hides the explanations and folds the extra sections, and shortens the Owner's menu; standard shows one
// line of each explanation, and a click on it shows the rest; detailed shows everything. The Owner's pages only: Staff forms keep their instructions.
// The choice is offered in Get started and on the Control panel. CSS does the work (app.css, html[data-view]).
const VIEWS = [
  { name: 'simple', label: 'Simple', says: 'Only the settings and the results. Explanations are hidden and the extra sections are folded away.' },
  { name: 'standard', label: 'Standard', says: 'One line of explanation under each setting. Click a line to read all of it.' },
  { name: 'detailed', label: 'Detailed', says: 'Every explanation and every section, in full.' },
];
function viewLevel() {
  try { const v = localStorage.getItem('nucleon.view'); return VIEWS.some(x => x.name === v) ? v : 'standard'; } catch { return 'standard'; }
}
function applyView() { document.documentElement.dataset.view = S.role === 'owner' ? viewLevel() : 'detailed'; }
function setViewLevel(v) {
  if (!VIEWS.some(x => x.name === v)) return;
  try { localStorage.setItem('nucleon.view', v); } catch { /* no storage: the choice lasts until the page is closed */ }
  applyView();
}
document.addEventListener('click', e => {   // standard view: a click on a shortened explanation opens it, another closes it
  const h = e.target.closest ? e.target.closest('.hint') : null;
  if (h && document.documentElement.dataset.view === 'standard' && !e.target.closest('a,button,input,select,textarea,label')) h.classList.toggle('open');
});
// The three levels as a choice. onChange runs after the level is applied (to draw the menu again, for example).
function viewChooser(testid = 'view-chooser') {
  const now = viewLevel();
  return `<fieldset class="view-chooser" data-testid="${testid}"><legend>How much the pages show</legend><div class="level-row">${VIEWS.map(v => `<label class="level${v.name === now ? ' on' : ''}">
    <input type="radio" name="viewLevel" value="${v.name}"${v.name === now ? ' checked' : ''} data-testid="view-${v.name}"><span><b>${esc(v.label)}</b><small>${esc(v.says)}</small></span></label>`).join('')}</div></fieldset>`;
}
function bindViewChooser(root, onChange) {
  $$('[name=viewLevel]', root).forEach(el => { el.onchange = () => {
    setViewLevel(el.value);
    $$('.view-chooser .level', root).forEach(l => l.classList.toggle('on', l.querySelector('input').checked));
    if (onChange) onChange(el.value);
  }; });
}
// Small line icons for section titles and big links (drawn in the text colour; decorative, so hidden from screen readers).
const ICONS = {
  rules: '<path d="M4 7h9m4 0h3M4 17h3m4 0h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  inbox: '<path d="M4 13l2.5-7h11L20 13v5H4z"/><path d="M4 13h4.5a3.5 3.5 0 0 0 7 0H20"/>',
  check: '<circle cx="12" cy="12" r="8"/><path d="M8.5 12.2l2.4 2.4 4.6-5"/>',
  bulb: '<path d="M9 17h6M10 20h4M8 13a5.5 5.5 0 1 1 8 0c-.7.8-1 1.5-1 2.5H9c0-1-.3-1.7-1-2.5z"/>',
  user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c.8-3.6 3.5-5.5 7-5.5s6.2 1.9 7 5.5"/>',
  calendar: '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
  chip: '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 4v3M14 4v3M10 17v3M14 17v3M4 10h3M4 14h3M17 10h3M17 14h3"/>',
  history: '<path d="M4.5 12a7.5 7.5 0 1 0 2.4-5.5L4.5 8.8"/><path d="M4.5 4.5v4.3h4.3M12 8v4.3l3 1.8"/>',
  chart: '<path d="M4 20h16M7 20v-6M12 20V6M17 20v-9"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
  flag: '<path d="M6 21V4M6 5h11l-2.5 4 2.5 4H6"/>',
  doc: '<path d="M7 3.5h7l4 4V20.5H7z"/><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6"/>',
  chat: '<path d="M4.5 6h15v10h-8l-4.5 3.5V16h-2.5z"/>',
  pulse: '<path d="M3 12h4l2.5-6 4 12 2.5-6h5"/>',
};
const icon = name => (ICONS[name] ? `<svg class="ico" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${ICONS[name]}</svg>` : '');
// In the simple view the Owner's menu is Home, Assistant, Decide and Rules (Quick setup); every other page is under "More".
const NAV_SIMPLE = { area: 'delegation', href: '#/quick-setup', label: 'Rules', owner: true, rules: true };
const SIMPLE_TOP = ['home', 'assistant', 'review'];
const simpleOwner = () => S.role === 'owner' && viewLevel() === 'simple';
// Sentences written for both roles say "the Owner"; on the Owner's own pages they read "you" (12 Nov 2026).
function ownerWords(text) {
  let t = String(text ?? '');
  if (typeof navRole !== 'function' || navRole() !== 'owner') return t;
  const swaps = [[/The Owner decided/g, 'You decided'], [/what the Owner delegated/g, 'what you delegated'], [/the Owner delegated/g, 'you delegated'], [/the Owner set/g, 'you set'],
    [/goes to the Owner/g, 'comes to you'], [/so the Owner decides/g, 'so you decide'], [/The Owner can reverse it/g, 'You can reverse it'], [/the Owner's decline rules/g, 'your decline rules'],
    [/the Owner's delegation policy/g, 'your delegation policy'], [/The Owner opened this case/g, 'You opened this case'], [/The Owner decides/g, 'You decide'], [/the Owner decides/g, 'you decide'],
    [/waits for the Owner/g, 'waits for you'], [/sent to the Owner/g, 'sent to you']];
  for (const [a, b] of swaps) t = t.replace(a, b);
  return t;
}
const navRole = () => (S.role === 'owner' ? 'owner' : 'staff');
const navCountArea = () => (S.role === 'owner' ? 'review' : 'requests');   // where "N need you" sits: the page this role acts on
// The assistant's address from the session, only if it is an http(s) link (the server checks it too): never any other kind of link.
const assistantHref = () => { const u = S.session?.assistantUrl; return typeof u === 'string' && /^https?:\/\/[^\s"'<>`\\]+$/.test(u) ? u : null; };
const navItems = () => {
  const list = NAV.filter(n => (!n.owner || S.role === 'owner') && (!n.external || assistantHref()));
  if (!simpleOwner()) return list;
  const at = list.findIndex(n => n.area === 'review');
  return [...list.slice(0, at + 1), NAV_SIMPLE, ...list.slice(at + 1)];
};
const navTop = n => (simpleOwner() ? !!n.rules || SIMPLE_TOP.includes(n.area) : (n.top || []).includes(navRole()));

function renderFrame(r) {
  const operator = S.role === 'operator';
  const s = S.session;
  const label = n => `<span class="nav-label">${esc(n.label)}</span>${n.external ? '<span aria-hidden="true"> ↗</span><span class="visually-hidden"> (opens in a new tab)</span>' : ''}`
    + (n.area === navCountArea() ? '<span class="count" data-count hidden></span>' : '') + (n.area === 'setup' && s.workspace && !s.hasRecords ? '<span class="dot" title="Setup isn\'t finished"></span>' : '');
  const link = (n, cls) => n.external
    ? `<a class="${cls} external" href="${esc(assistantHref())}" target="_blank" rel="noopener" data-area="${n.area}" data-testid="nav-assistant">${label(n)}</a>`
    : `<a class="${cls}" href="${n.href}"${n.area === r.area && (!simpleOwner() || n.area !== 'delegation' || !!n.rules === (r.name === 'quick-setup')) ? ' aria-current="page"' : ''} data-area="${n.area}"${n.rules ? ' data-testid="nav-rules"' : ''}>${label(n)}</a>`;
  const setupDot = s.workspace && !s.hasRecords ? '<span class="dot" title="Setup isn\'t finished"></span>' : '';
  applyView();
  const rest = navItems().filter(n => !navTop(n));
  const navLinks = cls => navItems().filter(navTop).map(n => link(n, cls)).join('') + (rest.length ? `<details class="nav-more" data-testid="nav-more-top">
      <summary class="${cls}${rest.some(n => n.area === r.area) ? ' current' : ''}"><span class="nav-label">More</span>${setupDot}</summary><div class="nav-more-menu">${rest.map(n => link(n, 'more-link')).join('')}</div></details>` : '');
  // On a phone the tab bar holds the primary pages and a "More" menu with the rest; the menu is closed by every page change (the frame is drawn again).
  const onPhone = n => (simpleOwner() ? navTop(n) : (n.phone || []).includes(navRole()));
  const more = navItems().filter(n => !onPhone(n));
  const tabLinks = () => navItems().filter(onPhone).map(n => link(n, 'tab-link')).join('') + `<details class="tab-more" data-testid="nav-more"><summary class="tab-link${more.some(n => n.area === r.area) ? ' current' : ''}">
      <span class="nav-label">More</span>${s.workspace && !s.hasRecords ? '<span class="dot" title="Setup isn\'t finished"></span>' : ''}</summary><div class="more-menu">${more.map(n => link(n, 'more-link')).join('')}</div></details>`;
  const caseRoles = ['staff', 'owner'];
  const date = s.asOfDate ? `Business date ${dateText(s.asOfDate)}${s.fixedDate ? ', fixed for practice' : ''}` : '';
  const mode = s.dataMode === 'fictional' || s.workspace === 'practice' ? 'Practice workspace with fictional data.' : s.workspace === 'real' ? 'Real business records.' : '';
  $('#root').innerHTML = `
    <a class="skip" href="#main">Skip to content</a>
    <header class="top${S.role === 'owner' ? ' top-owner' : ''}">
      <div class="top-in">
        <a class="brand" href="${operator ? '#/console' : '#/'}">Nucleon</a>
        ${operator ? '<p class="top-title">Demo console</p>' : `<nav class="mainnav" aria-label="Main">${navLinks('nav-link')}</nav>`}
        <div class="util">
          <p class="agent" id="agent" role="status"><i aria-hidden="true"></i><span></span></p>
          ${s.identity?.kind === 'agent' ? `<span class="chip" data-testid="identity">${esc(s.identity.name)}</span>` : ''}
          ${operator ? (S.held.some(x => caseRoles.includes(x)) ? '<a class="btn small" href="#/">Back to the app</a>' : '') : `
          <div class="roles" role="group" aria-label="Acting as">
            ${caseRoles.map(x => `<button type="button" data-role="${x}" aria-pressed="${S.role === x}"${S.held.includes(x) ? '' : ' title="Asks for the ' + x + ' code"'}>${ROLE_NAMES[x]}${S.held.includes(x) ? '' : '<span class="visually-hidden"> (needs its code)</span>'}</button>`).join('')}
          </div>`}
          <button type="button" class="btn small quiet" id="signout">Sign out</button>
        </div>
      </div>
      ${operator ? '' : `<p class="context">${esc(mode)}${date ? ` <span>${esc(date)}.</span>` : ''} <span class="context-times">Times show when things were actually recorded.</span></p>`}
    </header>
    <main id="main" class="page page-${esc(r.name)}" tabindex="-1"></main>
    ${operator ? '' : `<nav class="tabbar" aria-label="Main">${tabLinks()}</nav>`}
    <footer class="foot">Nothing is sent to customers. Replies are drafts. Decisions are the Owner’s, or the agent’s within the Owner’s delegation policy.</footer>`;
  $$('[data-role]').forEach(b => { b.onclick = () => switchRole(b.dataset.role); });
  $('#signout').onclick = signOut;
  $('.skip').onclick = event => { event.preventDefault(); $('#main').focus(); };   // a hash link would change the route
  renderAgent();
  if (!S.model) refreshModel();   // the first frame after sign-in shows the agent's real state, not "Checking" for 30 s
  updateCount();
  if (!operator && s.workspace && (!S.countAt || Date.now() - S.countAt > 15000)) refreshCount();   // any page, not only the lists (11 Nov 2026)
  document.title = (NAV.find(n => n.area === r.area)?.label || (operator ? 'Demo console' : 'Nucleon')) + ' · Nucleon';
}

// The Requests count in the navigation: cases waiting for this role, from the form and from the assistant (statusOf and decisionStatusOf in requests.js).
function updateCount() {
  const mine = S.cases.filter(c => statusOf(c).mine).length + (S.decisionCases || []).filter(c => decisionStatusOf(c).mine && !(c.requestId && S.cases.some(r => r.id === c.requestId))).length;
  $$('[data-count]').forEach(el => { el.hidden = !mine; el.textContent = mine; el.setAttribute('aria-label', plural(mine, 'needs you', 'need you')); });
}

// The count read again after a decision on Review or a case page (Hoang, 6 Nov 2026: "2 need you" stayed until a reload). Quiet when it fails: the next page load counts again.
async function refreshCount() {
  S.countAt = Date.now();
  try {
    const [requests, decisions] = await Promise.all([api('/api/requests'), api('/api/decision-cases').then(x => x.cases)]);
    if (!S.session) return;
    S.cases = requests; S.decisionCases = decisions;
    updateCount();
  } catch { /* counted again on the next page load */ }
}

// A page header: where you came from, the title, one line about the page, and its main actions.
function pageHead({ back, title, lede = '', actions = '', id = 'page-title' }) {
  return `<div class="page-head">${back ? `<p class="back"><a href="${esc(back.href)}">← ${esc(back.label)}</a></p>` : ''}
    <div class="page-head-row"><div><h1 id="${id}">${esc(title)}</h1>${lede ? `<p class="lede">${lede}</p>` : ''}</div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</div></div>`;
}

function renderAgent() {
  const el = $('#agent');
  if (!el || !S.session) return;
  const mode = S.session.agent.mode;
  const m = S.model;
  let cls = '', text = 'Checking the agent';
  if (mode === 'mock') { cls = 'warn'; text = 'Test agent, no AI'; }
  else if (mode === 'unavailable') { cls = 'down'; text = 'AI switched off'; }
  else if (m?.state === 'ready') { cls = 'ready'; text = 'Agent ready'; }
  else if (m?.state === 'reachable_not_loaded') { cls = 'warn'; text = 'Agent loading'; }
  else if (m?.state === 'unreachable') { cls = 'down'; text = 'Agent offline'; }
  el.className = 'agent ' + cls;
  el.title = mode === 'live' ? (m?.state === 'unreachable' ? 'New cases are prepared without AI until the model is back.' : S.session.agent.label) : '';
  $('span', el).textContent = text;
}

async function refreshModel() {
  if (!S.session || S.session.agent.mode !== 'live') return;
  try { S.model = await api('/api/model-status'); } catch { S.model = { state: 'unreachable' }; }
  renderAgent();
}

function stopPolling() { clearTimeout(S.poll); S.poll = null; }

// A page that keeps itself current registers REFRESH[route name] = async seq => … (the Owner's home and control panel, and the landing page's waiting
// list for Staff). The page asks for the timer with keepFresh(seq) after it is drawn: every REFRESH_MS while the tab is visible, and at once when the window
// regains focus or the tab becomes visible. A route change stops it (stopPolling). No other page polls on this timer.
const REFRESH = {}, REFRESH_MS = 20000;
function keepFresh(seq) {
  clearTimeout(S.poll);
  S.poll = setTimeout(() => refreshNow(seq), REFRESH_MS);
}
async function refreshNow(seq, onlyIfVisible = true) {
  const name = S.route?.name;
  if (!live(seq) || !S.session || !REFRESH[name]) return;
  if (onlyIfVisible && document.visibilityState !== 'visible') return keepFresh(seq);
  S.refreshedAt = Date.now();
  try { await REFRESH[name](seq); } catch (error) { if (error?.status === 401) { S.session = null; return renderGate(null, 'Your session ended, for example because the app restarted. Sign in again.'); } }
  if (live(seq)) keepFresh(seq);
}
// Coming back to the window or the tab: read again now, unless a read has only just been made.
function backInView() {
  if (document.visibilityState !== 'visible' || !S.session || !REFRESH[S.route?.name] || Date.now() - (S.refreshedAt || 0) < 2000) return;
  refreshNow(S.seq);
}

PAGES.notfound = () => { $('#main').innerHTML = `<div class="state-msg"><h1>Page not found</h1><p>This address doesn't match a page.</p><a class="btn primary" href="#/">Go to the home page</a></div>`; };

// ---------------------------------------------------------------- start

async function start() {
  window.addEventListener('hashchange', () => { if (S.route?.name !== 'signout') route(); });
  window.addEventListener('focus', backInView);
  document.addEventListener('visibilitychange', backInView);
  document.addEventListener('visibilitychange', trackVisibility);
  window.addEventListener('pagehide', () => { trackLeave(); flushTrack(true); });
  window.addEventListener('beforeunload', event => { if (S.leaveDirty && S.leaveDirty()) { event.preventDefault(); event.returnValue = ''; } });
  // a click on anything marked data-track="<name>" is one `click` event with that name (capture phase: the element may be drawn again by the click)
  document.addEventListener('click', event => { const el = event.target.closest?.('[data-track]'); if (el && !el.disabled) trackEvent('click', { name: el.dataset.track }); }, true);
  // A link to the page already open draws it again (the address does not change, so there is no hashchange).
  document.addEventListener('click', event => {
    const a = event.target.closest?.('a[href^="#"]');
    if (!a || event.defaultPrevented || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || a.target === '_blank') return;
    const norm = h => h.replace(/^#\/?/, '');
    if (S.leaveGuard && norm(a.getAttribute('href')) !== norm(location.hash) && !S.leaveGuard()) { event.preventDefault(); return; }   // unsaved edits: ask first
    if (norm(a.getAttribute('href')) === norm(location.hash) && S.session && !S.route?.name?.match(/^(signout|gate)$/)) route();
  });
  window.addEventListener('storage', event => { if (event.key === STORAGE + 'signout') followOtherTab(); });
  const pending = signoutState();
  if (pending && pending.state !== 'done') { forgetLocal(); await confirmSignOut(); }   // a sign-out not yet confirmed is finished first
  else {
    try { await loadSession(); } catch { /* shown as signed out */ }
    await route();
  }
  refreshModel();
  setInterval(refreshModel, 30000);
  setInterval(() => {   // keep the case list current, but never while someone is typing or a dialog is open
    if (document.hidden || !S.session || S.busy || $('dialog[open]') || document.activeElement?.closest('form')) return;
    if (S.route?.name === 'console') PAGES.console?.(S.route, S.seq, true);
    else if (S.route?.area === 'requests') refreshCases(S.seq);
  }, 8000);
}

document.addEventListener('DOMContentLoaded', start);   // after every page file has registered itself
