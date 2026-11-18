'use strict';
// The landing page of each role: #/ (PAGES.home). (The Owner's Review is review.js, the Dashboard dashboard.js, the case timeline timeline.js.)
// Owner: what waits for them (the control panel's data: /api/delegation/cases), the agent's last five decisions, the live counts, and the big links. A row goes to the Decide page
// (the one place to decide) and to the case timeline.
// Staff: the assistant first, then Requests, Customers and Imports, the requests that wait on them (/api/requests, as the Requests count shows) and the information Nucleon is
// waiting for from them (the open evidence requests: GET /api/actions?kind=evidence&status=open, each linked to #/actions/<id>).
// The page keeps itself current (core.js keepFresh/REFRESH): every 20 s while visible and when the window or tab comes back. It reuses caseLine and countsHtml (delegation.js).
// Uses core.js helpers (api, pageHead, esc, assistantHref, loading, stamp, keepFresh, REFRESH).

const HOME = { cases: [], stats: null, requests: [], evidence: [] };

// A big link: the page's main places, as large targets (also for a thumb).
const bigLink = (href, title, note, { primary = false, external = false, testid, ico = '' } = {}) =>
  `<a class="home-link${primary ? ' primary' : ''}" href="${esc(href)}"${external ? ' target="_blank" rel="noopener"' : ''} data-testid="${testid}" data-track="${testid}">
    <span class="home-link-title">${icon(ico)}${ico ? " " : ""}${esc(title)}${external ? '<span aria-hidden="true">\u00a0↗</span><span class="visually-hidden"> (opens in a new tab)</span>' : ''}</span><span class="home-link-note">${esc(note)}</span></a>`;

function homeLinks() {
  const assistant = assistantHref();
  const open = assistant ? bigLink(assistant, 'Open the assistant', 'Ask it about a customer or a request, in a new tab.', { primary: true, external: true, testid: 'home-assistant', ico: 'chat' }) : '';
  if (S.role === 'owner') {
    return `<nav class="home-links" aria-label="Where to go">${open}${bigLink('#/delegation', 'Control panel', 'Set how far the assistant may decide, and see what it decided.', { testid: 'home-control-panel', ico: 'rules' })}
      ${bigLink('#/review', 'Decide', 'What waits for your decision, and agree or disagree with what the assistant decided.', { testid: 'home-review', ico: 'inbox' })}
      ${bigLink('#/dashboard', 'Dashboard', 'How much the assistant decides, how often you step in, and what happened next.', { testid: 'home-dashboard', ico: 'chart' })}
      ${bigLink('#/doctor', 'Doctor', 'Why requests still reach you, why you correct the agent, and what to change.', { testid: 'home-doctor', ico: 'pulse' })}</nav>`;
  }
  return `<nav class="home-links" aria-label="Where to go">${open}${bigLink('#/cases', 'Requests', 'Customers\' payment-extension requests and who each waits for.', { testid: 'home-requests' })}
    ${bigLink('#/customers', 'Customers', 'Their invoices, payments and balances.', { testid: 'home-customers' })}${bigLink('#/imports', 'Imports', 'Bring in invoices or payments from a CSV file.', { testid: 'home-imports' })}</nav>`;
}

// The first thing the Owner reads (12 Nov 2026): one sentence on what waits, and one button. Before any rules are saved it is the way into Get started.
function ownerBriefHtml() {
  const n = HOME.cases.filter(c => ['awaiting_owner', 'on_hold'].includes(c.status)).length;
  if (HOME.policy && HOME.policy.version === 0) {
    return `<div class="home-brief" data-testid="home-brief" data-state="start"><p><b>The agent has no rules yet.</b> Three choices and it is ready${n ? `; ${plural(n, 'request is', 'requests are')} already waiting for you` : ''}.</p>
      <a class="btn primary" href="#/get-started" data-testid="home-get-started" data-track="home-get-started">Let's get started</a>${n ? ' <a class="btn" href="#/review">Decide now</a>' : ''}</div>`;
  }
  return `<div class="home-brief" data-testid="home-brief" data-state="${n ? 'waiting' : 'clear'}"><p>${n ? `<b>${plural(n, 'request is', 'requests are')} waiting for your decision.</b>` : '<b>Nothing is waiting for you.</b> The agent is handling what your rules allow.'}</p>
    ${n ? '<a class="btn primary" href="#/review" data-testid="home-brief-decide">Decide now</a>' : ''}</div>`;
}

function ownerWaitingHtml() {
  const rows = HOME.cases.filter(c => ['awaiting_owner', 'on_hold'].includes(c.status));
  const list = rows.length ? `<ul class="home-list" data-testid="home-waiting-list">${rows.map(c => `<li data-testid="home-waiting" data-case="${esc(c.caseId)}">
      <a href="#/review"><b>${esc(c.customer?.name || '')}</b> <span class="chip ${c.status === 'on_hold' ? 'fail' : 'need'}">${c.status === 'on_hold' ? 'On hold by policy' : 'Needs your decision'}</span></a>
      <span class="home-note">${caseLine(c)}</span><a class="home-note" href="#/decision-cases/${esc(c.caseId)}" data-testid="home-timeline">Case timeline</a></li>`).join('')}</ul>`
    : '<p class="muted" data-testid="home-waiting-none">Nothing is waiting for you.</p>';
  return `<section aria-labelledby="home-wait"><h2 id="home-wait">Waiting for you <span class="count" data-testid="home-waiting-count"${rows.length ? '' : ' hidden'}>${rows.length}</span></h2>${list}</section>`;
}

function ownerRecentHtml() {
  const rows = HOME.cases.filter(c => c.status === 'decided' && c.decision?.by === 'agent').slice(0, 5);
  const list = rows.length ? `<ul class="home-list" data-testid="home-recent-list">${rows.map(c => {
    const last = (c.feedback || []).slice(-1)[0];
    const state = c.decision.overridden ? '<span class="chip fail">Overridden</span>' : last ? `<span class="chip done">${last.verdict === 'tacit_agree' ? esc(feedbackText(last)) : last.verdict === 'agree' ? 'You agreed' : 'You disagreed'}</span>` : (c.decision.outcome === 'decline' ? '<span class="chip fail">Declined by the agent</span>' : '<span class="chip done">Approved by the agent</span>');
    return `<li data-testid="home-recent" data-case="${esc(c.caseId)}"><a href="#/review"><b>${esc(c.customer?.name || '')}</b> ${state}</a>
      <span class="home-note">${caseLine(c)}</span><span class="home-note">Policy version ${esc(c.policyVersion)} · ${stamp(c.decision.at)}</span><a class="home-note" href="#/decision-cases/${esc(c.caseId)}" data-testid="home-timeline">Case timeline</a></li>`;
  }).join('')}</ul>` : '<p class="muted" data-testid="home-recent-none">The agent has not decided anything yet.</p>';
  return `<section class="v-std" aria-labelledby="home-recent"><h2 id="home-recent">Recent agent decisions</h2>${list}</section>`;
}

function staffWaitingHtml() {
  const rows = HOME.requests.filter(c => statusOf(c).mine);
  const label = c => `${esc(c.customerName || 'A customer')}${c.invoiceReference ? ', invoice ' + esc(c.invoiceReference) : ''}`;
  const list = rows.length ? `<ul class="home-list" data-testid="home-waiting-list">${rows.map(c => `<li data-testid="home-waiting" data-case="${esc(c.id)}"><a href="#/case/${esc(c.id)}"><b>${label(c)}</b> <span class="chip ${statusOf(c).cls}">${esc(statusOf(c).text)}</span></a></li>`).join('')}</ul>`
    : '<p class="muted" data-testid="home-waiting-none">Nothing is waiting for you.</p>';
  return `<section aria-labelledby="home-wait"><h2 id="home-wait">Waiting for you <span class="count" data-testid="home-waiting-count"${rows.length ? '' : ' hidden'}>${rows.length}</span></h2>${list}</section>`;
}

// The information Nucleon is waiting for from Staff: the open evidence requests, each with the customer, what is asked, when it was asked, and its page.
function staffEvidenceHtml() {
  const rows = HOME.evidence;
  const list = rows.length ? `<ul class="home-list" data-testid="home-evidence-list">${rows.map(a => `<li data-testid="home-evidence" data-action="${esc(a.id)}"><a href="${esc(a.link)}" data-track="home-evidence"><b>${esc(a.customer.name)}</b> <span class="chip need">Information needed</span></a>
      <span class="home-note">${esc(a.asks)}</span><span class="home-note">Asked ${stamp(a.createdAt)}</span></li>`).join('')}</ul>` : '<p class="muted" data-testid="home-evidence-none">Nucleon is not waiting for any information from you.</p>';
  return `<section aria-labelledby="home-evid"><h2 id="home-evid">Information Nucleon is waiting for from you <span class="count" data-testid="home-evidence-count"${rows.length ? '' : ' hidden'}>${rows.length}</span></h2>${list}</section>`;
}

// Practice (4 Nov 2026): with it on, the assistant previews every Staff request, stores nothing and sends nothing to the Owner. One switch for the workspace.
function staffPracticeHtml() {
  const p = HOME.practice;
  if (!p) return '';
  return `<section aria-labelledby="home-practice" data-testid="home-practice" data-on="${p.on ? 'true' : 'false'}"><h2 id="home-practice">Requests go to the Owner: ${p.on ? 'OFF (practice)' : 'on'}</h2>
    ${p.on ? '<div class="callout warn"><p><b>Practice mode is on.</b> The assistant assesses every request and says what would happen, but stores nothing and sends nothing to the Owner. Turn it off to send requests for real.</p></div>'
           : '<p>Every request you resolve with the assistant is stored and, when it is outside the delegation, goes to the Owner. Turn this off to practise: the assistant then only shows what would happen.</p>'}
    <p><button type="button" class="btn${p.on ? ' primary' : ''}" id="home-practice-toggle" data-testid="home-practice-toggle">${p.on ? 'Send requests to the Owner again' : 'Practise without sending to the Owner'}</button></p></section>`;
}

function renderHome() {
  const main = $('#main');
  if (!main || S.route?.name !== 'home') return;
  const owner = S.role === 'owner';
  main.innerHTML = `<div class="home-page" data-testid="home-page" data-role-home="${owner ? 'owner' : 'staff'}">
    ${pageHead({ title: 'Home', lede: owner ? 'What needs you now, what the assistant decided lately, and where to go next.' : 'Where to start, and the requests waiting for you.' })}
    ${owner ? ownerBriefHtml() : ''}${homeLinks()}${whereToStartHtml(owner)}
    ${noticesHtml()}${owner ? ownerWaitingHtml() + ownerRecentHtml() + `<section class="v-std" aria-labelledby="home-counts"><h2 id="home-counts">Live counts</h2>${HOME.stats ? countsHtml(HOME.stats) : ''}</section>` : staffPracticeHtml() + staffWaitingHtml() + staffEvidenceHtml()}</div>`;
  const start = $('[data-testid=where-to-start]');
  if (start) start.ontoggle = () => { try { localStorage.setItem('nucleon.start.folded', start.open ? '0' : '1'); } catch { /* fine */ } };
  const practice = $('#home-practice-toggle');
  if (practice) practice.onclick = async () => { try { HOME.practice = await api('/api/staff/practice', { on: !HOME.practice.on }, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); renderHome(); } catch (e) { toast(e.message, 'bad'); } };
  const read = $('#notices-read');
  if (read) read.onclick = async () => { try { HOME.notices = await api('/api/notices/read', { all: true }, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); renderHome(); } catch (e) { toast(e.message, 'bad'); } };
}

// Three steps for someone opening the app for the first time (testers asked where to start, 6 Nov 2026). Folded once read; the choice is kept in this browser.
function whereToStartHtml(owner) {
  let open = true;
  try { open = localStorage.getItem('nucleon.start.folded') !== '1'; } catch { /* no storage: always open */ }
  const assistant = assistantHref();
  const steps = owner ? [
    ['<b>Set the limits once.</b> <a href="#/get-started">Get started</a> does it in three choices. Or answer a few questions in <a href="#/quick-setup">Quick setup</a> and see what the agent would do with your open invoices. The <a href="#/delegation">Control panel</a> has every setting.'],
    [`<b>Decide what comes to you.</b> <a href="#/review">Decide</a> lists what waits for your decision and what the agent decided on its own, to agree, disagree or undo.`],
    ['<b>Watch how it goes.</b> The <a href="#/dashboard">Dashboard</a> counts what the agent decided, how often you stepped in, and what happened next.']
  ] : [
    [`<b>Ask the assistant${assistant ? ` (<a href="${esc(assistant)}" target="_blank" rel="noopener">open it</a>)` : ''}.</b> Name the customer and what they ask for: a later payment date on an invoice, or credit on a first order. It checks the records and answers with a card.`],
    ['<b>When it asks you for information</b> (a deposit you saw, the business registration), the card links to a page where you confirm it; it then decides again by itself.'],
    ['<b>New customer?</b> Their invoice or order must be in Nucleon Records first: add it under <a href="#/customers">Customers</a> or <a href="#/imports">Imports</a>, then ask. <a href="#/cases">Requests</a> shows every request and who it waits for.']
  ];
  return `<details class="start-steps" data-testid="where-to-start"${open ? ' open' : ''}><summary>Where to start</summary><ol>${steps.map(([t]) => `<li>${t}</li>`).join('')}</ol></details>`;
}

function noticesHtml() {
  const n = HOME.notices;
  if (!n) return '';
  const rows = n.notices.filter(x => !x.readAt).slice(0, 20);
  const list = rows.length ? `<ul class="home-list" data-testid="notices">${rows.map(x => `<li data-testid="notice" data-kind="${esc(x.kind)}">${x.link ? `<a href="${esc(x.link)}">${esc(ownerWords(x.text))}</a>` : esc(ownerWords(x.text))} <span class="muted">${stamp(x.createdAt)}</span></li>`).join('')}</ul>
    <p><button type="button" class="btn small" id="notices-read" data-testid="notices-read">Mark all as read</button></p>` : '<p class="muted" data-testid="notices-none">Nothing new.</p>';
  return `<section aria-labelledby="home-notices"><h2 id="home-notices">What happened since you last looked <span class="count" data-testid="notices-count"${n.unread ? '' : ' hidden'}>${n.unread}</span></h2>${list}</section>`;
}

async function homeLoad() {
  HOME.notices = await api('/api/notices').catch(() => null);   // a convenience: the page works without it
  if (S.role === 'owner') {
    const [cases, stats, policy] = await Promise.all([api('/api/delegation/cases'), api('/api/delegation/stats'), api('/api/delegation/policy').catch(() => null)]);
    Object.assign(HOME, { cases: cases.cases, stats, policy });
  } else {
    const [requests, evidence, practice] = await Promise.all([api('/api/requests'), api('/api/actions?kind=evidence&status=open').catch(() => ({ actions: [] })), api('/api/staff/practice').catch(() => null)]);
    HOME.practice = practice;   // the list is a convenience: the page works without it
    HOME.requests = requests; HOME.evidence = evidence.actions;
    S.cases = HOME.requests;   // the Requests count in the navigation reads the same list
    updateCount();
  }
}

PAGES.home = async (r, seq) => {
  $('#main').innerHTML = loading('your home page');
  await homeLoad();
  if (!live(seq)) return;
  renderHome();
  keepFresh(seq);
};
REFRESH.home = async seq => {
  await homeLoad();
  if (live(seq)) renderHome();
};
