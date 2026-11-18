'use strict';
// The Owner's dashboard: #/dashboard (Owner only; Staff get "Page not found" from core.js route()). How the assistant is doing, as numbers a person can check:
//   (a) the impact report (GET /api/delegation/impact, with a from/to date and a policy-version filter): one tile per metric with its value, its numerator over denominator and
//       where the number comes from (measured, derived, or an assumption nobody measured). A value the backend cannot establish is null and reads "no data yet", never 0;
//   (b) the loop: how many live cases are at each of the six stages now (GET /api/delegation/loop, counted by the backend);
//   (c) outcomes by label as simple bars (CSS widths set from the page's script: the page's CSP allows no inline style);
//   (d) usage: the pages' own telemetry (GET /api/delegation/ui-summary), kept on this machine; and the button that observes outcomes now (POST /api/delegation/observe-outcomes).
// Fictional cases are never in these numbers. Nothing is calculated here: the page words and lays out what the backend returned. Uses core.js helpers (api, pageHead, esc, dateText, loading, live,
// keepFresh, REFRESH, toast, busy) and delegation.js (SOURCE_WORDS).

const DASH = { impact: null, loop: null, usage: null, versions: [], exposure: null, filter: { from: '', to: '', policyVersion: '' }, notice: null, observed: null, flight: false };

// Every customer, what they owe now and what is overdue, against the limit that applies to them (their own rule or the policy's). Backend figures (GET /api/delegation/exposure).
function exposureHtml(x) {
  if (!x) return '<p class="muted">Not available.</p>';
  const rows = x.customers.map(r => `<tr data-testid="exposure-row" data-over="${r.over}"${r.over ? ' class="over"' : ''}><th scope="row"><a href="#/customers/${esc(r.customer.id)}">${esc(r.customer.name)}</a>${r.rule ? ' <span class="chip busy" title="Your standing rule applies">rule</span>' : ''}${r.incomplete ? ' <span class="chip need" title="The records for this customer are incomplete">incomplete</span>' : ''}</th>
      <td class="num" data-label="Outstanding balance">${esc(r.debt.text)}</td><td class="num" data-label="Of which overdue">${esc(r.overdue.text)}${r.daysPastDue ? ` <span class="muted">(${r.daysPastDue} d)</span>` : ''}</td>
      <td class="num" data-label="Trial credit in force">${esc(r.linesInForce.text)}</td><td class="num" data-label="Total at risk">${esc(r.exposure.text)}</td><td class="num" data-label="Limit">${esc(r.limit.text)}${r.over ? ' <span class="chip fail">over</span>' : ''}</td>
      <td class="num" data-label="Open cases">${r.openCases || ''}</td></tr>`).join('');
  return `<p data-testid="exposure-totals">Across ${x.customers.length} customers: total at risk <b>${esc(x.totals.exposure.text)}</b>, of which overdue <b>${esc(x.totals.overdue.text)}</b>, ${x.totals.overLimit} over their limit${x.totals.incomplete ? `, ${x.totals.incomplete} with incomplete records` : ''}. As of ${esc(dateText(x.asOf))}.</p>
    <div class="table-wrap"><table class="rtable" data-testid="exposure-table"><caption class="visually-hidden">What each customer owes and the total at risk</caption><thead><tr><th scope="col">Customer</th><th scope="col" class="num">Outstanding balance</th><th scope="col" class="num">Of which overdue</th><th scope="col" class="num">Trial credit in force</th><th scope="col" class="num">Total at risk</th><th scope="col" class="num">Limit</th><th scope="col" class="num">Open cases</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="hint" data-testid="exposure-note">Total at risk = outstanding balance + trial credit in force; the limit is checked against it. "Of which overdue" is part of the outstanding balance, with the oldest days past due in brackets. When a customer has one open invoice, all of it overdue, and no trial credit, the three money columns show the same figure.</p>`;
}

const NO_DATA = 'no data yet';
const SOURCE_LABEL = { measured: 'measured', derived: 'derived', assumption: 'assumption, not measured' };
const pct = v => `${(Math.round(v * 1000) / 10).toFixed(1).replace(/\.0$/, '')}%`;
function span(seconds) {   // whole seconds as words
  const s = Math.round(seconds);
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min${s % 60 ? ' ' + (s % 60) + ' s' : ''}`;
  if (s < 86400) return `${Math.floor(s / 3600)} h${Math.floor((s % 3600) / 60) ? ' ' + Math.floor((s % 3600) / 60) + ' min' : ''}`;
  return `${Math.floor(s / 86400)} d${Math.floor((s % 86400) / 3600) ? ' ' + Math.floor((s % 86400) / 3600) + ' h' : ''}`;
}
const FORMATS = { count: v => String(v), rate: pct, time: span };

// One metric as a tile. m = {value, numerator, denominator, source, dataset, note}; kind: how the value is worded.
function tile(key, title, m, kind = 'count') {
  const none = m.value === null || m.value === undefined;
  const fraction = m.numerator !== null && m.numerator !== undefined && m.denominator !== null && m.denominator !== undefined ? `${m.numerator} of ${m.denominator}` : '';
  const timeSaved = key === 'timeSaved';
  return `<div class="tile" data-testid="tile" data-tile="${esc(key)}" data-source="${esc(m.source)}" data-raw="${esc(JSON.stringify(m.value ?? null))}" data-num="${esc(m.numerator ?? '')}" data-den="${esc(m.denominator ?? '')}" title="${esc(m.note || '')}">
    <p class="tile-label">${esc(title)}</p>
    <p class="tile-value${none ? ' none' : ''}" data-testid="tile-value">${timeSaved ? 'not measured — set from PoV interviews' : none ? NO_DATA : esc(FORMATS[kind](m.value))}</p>
    <p class="tile-frac" data-testid="tile-frac">${esc(fraction)}</p>
    <p class="tile-src"><span class="chip ${m.source === 'assumption' ? 'need' : m.source === 'derived' ? 'busy' : 'done'}" data-testid="tile-source">${esc(SOURCE_LABEL[m.source] || m.source)}</span> <span class="tile-set" data-testid="tile-dataset">${esc(m.dataset)} cases</span></p></div>`;
}

function tilesHtml(r) {
  const out = [
    tile('cases', 'Cases', r.cases), tile('autonomousCoverage', 'Decided by the agent', r.autonomousCoverage, 'rate'), tile('escalationRate', 'Sent to you (escalation rate)', r.escalationRate, 'rate'),
    tile('overridesCount', 'Overrides', r.overrides.count), tile('overridesRate', 'Override rate', r.overrides.rate, 'rate'), tile('disagreements', 'Disagreements', r.disagreements.count),
    tile('agreementRate', 'Your agreement (explicit and treated as agreed)', r.liveAgreement.agreementRate, 'rate'), tile('agreementExplicit', 'Explicit verdicts', r.liveAgreement.explicit),
    tile('agreementTacit', 'Treated as agreed (tacit)', r.liveAgreement.tacit),
    tile('evidenceRequests', 'Information requests to Staff', r.evidenceRequests.count), tile('evidenceAnswered', 'Answered', r.evidenceRequests.answered),
    tile('evidenceTurnaround', 'Median time to answer', r.evidenceRequests.medianTurnaroundSeconds, 'time'),
    tile('timeToDecision', 'Median time to decision', r.timeToDecisionSeconds.median, 'time'), tile('timeToDecisionP90', 'Slowest tenth (90th percentile)', r.timeToDecisionSeconds.p90, 'time'),
    tile('ownerIntervention', 'Median time you spend on a case', r.ownerInterventionSeconds.median, 'time'), tile('ownerInterventionCases', 'Cases with your time measured', r.ownerInterventionSeconds.cases),
    tile('timeSaved', 'Time saved', r.timeSaved, 'time')];
  return `<div class="tiles" data-testid="tiles">${out.join('')}</div>`;
}

function loopHtml(l) {
  return `<ol class="loop-strip" data-testid="loop-strip" aria-label="Live cases at each stage of the loop">${l.stages.map(s => `<li class="loop-stage${s.count ? ' has' : ''}" data-testid="loop-stage" data-stage="${esc(s.stage)}" data-count="${s.count}">
      <span class="loop-count" data-testid="loop-count">${s.count}</span><span class="loop-name">${esc(s.label)}</span></li>`).join('')}</ol>
    <p class="hint" data-testid="loop-note">${l.total} live case${l.total === 1 ? '' : 's'}${l.closed ? `, ${l.closed} closed (out of the loop)` : ''}. ${esc(l.note)}</p>`;
}

const OUTCOME_ORDER = ['on_time', 'late_paid', 'partial', 'open_not_due', 'open_past_due', 'written_off', 'unknown'];
function outcomesHtml(r) {
  const by = r.outcomes.byLabel, total = OUTCOME_ORDER.reduce((n, k) => n + (by[k]?.value || 0), 0);
  const rows = OUTCOME_ORDER.map(k => `<div class="bar-row" data-testid="outcome-row" data-label="${k}" data-count="${by[k]?.value || 0}"><span class="bar-label">${esc(outcomeWord(k))}</span>
    <span class="bar-track"><span class="bar" data-w="${total ? ((by[k].value / total) * 100).toFixed(2) : 0}"></span></span><span class="bar-n">${by[k]?.value || 0}</span></div>`).join('');
  return `<div data-testid="outcomes">${total ? rows : `<p class="muted" data-testid="outcomes-none">No outcome has been observed yet.</p>`}
    <p class="hint">${r.outcomes.pending.value} approved decision${r.outcomes.pending.value === 1 ? '' : 's'} waiting for an observation; ${r.outcomes.neverObserved.value} declined or overridden, which are never observed.</p></div>`;
}

function usageHtml(u) {
  if (!u || !u.events) return '<p class="muted" data-testid="usage-none">No page use has been recorded in this period.</p>';
  const rows = u.pages.map(p => `<tr data-testid="usage-row" data-page="${esc(p.page)}"><th scope="row" data-label="Page">${esc(p.page)}</th><td class="num" data-label="Visits">${p.enters}</td><td class="num" data-label="Median time on the page">${p.medianDwellSeconds === null ? NO_DATA : esc(span(p.medianDwellSeconds))}</td><td class="num" data-label="Marked clicks">${p.clicks}</td></tr>`).join('');
  const d = u.decisions;
  return `<div class="table-wrap"><table class="rtable" data-testid="usage-table"><thead><tr><th scope="col">Page</th><th scope="col">Visits</th><th scope="col">Median time on the page</th><th scope="col">Marked clicks</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="hint" data-testid="usage-decisions">Decisions on the Decide page: ${d.started} started, ${d.done} recorded; median ${d.medianSeconds === null ? NO_DATA : esc(span(d.medianSeconds))}. ${esc(u.note)}</p>`;
}

function renderDashboard() {
  const main = $('#main');
  if (!main || S.route?.name !== 'dashboard') return;
  const f = DASH.filter, r = DASH.impact;
  const notice = DASH.notice ? `<div class="callout ${DASH.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(DASH.notice.text)}</p></div>` : '';
  const seen = DASH.observed ? `<div class="callout ok" role="status" data-testid="observed-result"><p>Observed ${DASH.observed.observed} approved decision${DASH.observed.observed === 1 ? '' : 's'} as of ${esc(dateText(DASH.observed.asOf))}: ${DASH.observed.changed} new or changed, ${DASH.observed.unchanged} unchanged.</p></div>` : '';
  main.innerHTML = `<div class="dashboard-page" data-testid="dashboard-page">
    ${pageHead({ title: 'Dashboard', lede: 'How the assistant is doing: how much it decides, how often you step in, and what happened to its decisions.',
      actions: '<button type="button" class="btn" id="observe" data-testid="observe-outcomes" data-track="dash-observe">Observe outcomes now</button>' })}${notice}${seen}
    <form id="dash-filter" class="dash-filter" novalidate data-testid="dash-filter"><div class="field"><label for="df-from">From</label><input id="df-from" type="date" name="from" value="${esc(f.from)}"></div>
      <div class="field"><label for="df-to">To</label><input id="df-to" type="date" name="to" value="${esc(f.to)}"></div>
      <div class="field"><label for="df-version">Policy version</label><select id="df-version" name="policyVersion"><option value="">All versions</option>${DASH.versions.map(v => `<option value="${v}"${String(v) === String(f.policyVersion) ? ' selected' : ''}>Version ${v}</option>`).join('')}</select></div>
      <div class="field dash-apply"><button type="submit" class="btn primary" data-testid="apply-filter" data-track="dash-filter">Apply</button></div></form>
    <p class="hint" data-testid="window-note">${esc(r.window.note)}</p>
    <section aria-labelledby="d-exp"><h2 id="d-exp">What customers owe now</h2>${exposureHtml(DASH.exposure)}</section>
    <section aria-labelledby="d-loop"><h2 id="d-loop">Where the live cases are in the loop</h2>${loopHtml(DASH.loop)}</section>
    <section aria-labelledby="d-impact"><h2 id="d-impact">Impact</h2>${tilesHtml(r)}</section>
    <section aria-labelledby="d-out"><h2 id="d-out">What happened to the approved decisions</h2>${outcomesHtml(r)}</section>
    <section aria-labelledby="d-use"><h2 id="d-use">Usage</h2>${usageHtml(DASH.usage)}</section>
    <p class="hint" data-testid="fictional-note">Fictional cases are excluded. ${esc(r.excluded.note)} Every number here is for live cases only.</p></div>`;
  document.title = 'Dashboard · Nucleon';
  $$('.bar').forEach(b => { b.style.width = b.dataset.w + '%'; });   // set through the CSSOM: the page's CSP allows no inline style attribute
  $('#dash-filter').oninput = event => { DASH.filter[event.target.name] = event.target.value; };
  $('#dash-filter').onsubmit = event => { event.preventDefault(); dashRefresh(null, true); };
  $('#observe').onclick = observeNow;
}

function query() {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(DASH.filter)) if (v !== '') q.set(k, v);
  return q.toString() ? '?' + q : '';
}
async function dashLoad() {
  const q = query(), usageQ = new URLSearchParams([...new URLSearchParams(q)].filter(([k]) => k === 'from' || k === 'to')).toString();
  const [impact, loop, usage, history, exposure] = await Promise.all([api('/api/delegation/impact' + q), api('/api/delegation/loop'), api('/api/delegation/ui-summary' + (usageQ ? '?' + usageQ : '')), api('/api/delegation/policy/history'),
    api('/api/delegation/exposure').catch(() => null)]);
  Object.assign(DASH, { impact, loop, usage, exposure, versions: history.versions.map(v => v.version).sort((a, b) => b - a) });
}

async function dashRefresh(notice, userAction = false) {
  DASH.notice = notice || null;
  try { await dashLoad(); } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    DASH.notice = { kind: 'bad', text: error.message };
    if (!DASH.impact) throw error;
  }
  if (S.route?.name !== 'dashboard') return;
  renderDashboard();
  if (userAction && !DASH.notice) $('[data-testid=apply-filter]')?.focus();
}

async function observeNow() {
  if (DASH.flight) return;
  DASH.flight = true;
  const button = $('#observe');
  button.disabled = true;
  try {
    DASH.observed = await api('/api/delegation/observe-outcomes', {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    DASH.flight = false;
    return dashRefresh(null);
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    DASH.flight = false;
    DASH.observed = null;
    return dashRefresh({ kind: 'bad', text: error.message });
  } finally { DASH.flight = false; }
}

PAGES.dashboard = async (r, seq) => {
  $('#main').innerHTML = loading('the dashboard');
  Object.assign(DASH, { filter: { from: '', to: '', policyVersion: '' }, notice: null, observed: null, flight: false });
  await dashLoad();
  if (!live(seq)) return;
  renderDashboard();
  keepFresh(seq);
};
REFRESH.dashboard = async seq => {
  if (DASH.flight) return;
  const a = document.activeElement, focus = a && a.id && $('#main')?.contains(a) ? a.id : null, y = scrollY;
  try { await dashLoad(); } catch (error) { if (error.code === 'SIGNED_OUT' || error.status === 401) throw error; return; }   // a failed read leaves the page as it is
  if (!live(seq) || S.route?.name !== 'dashboard') return;
  renderDashboard();
  if (focus) document.getElementById(focus)?.focus({ preventScroll: true });
  scrollTo(0, y);
};
