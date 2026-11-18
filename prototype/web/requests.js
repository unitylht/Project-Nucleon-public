'use strict';
// Requests: the queue, the new-request composer (staff), and the case page with its one next action.
// Uses core.js helpers.

const SAMPLES = [
  { label: 'Clear request', note: 'Goes straight to the owner', text: "Hi, it's Harbour Demo Supplies. Could we pay invoice DEMO-101 on Friday 30 October instead? We're still waiting on a payment from one of our own customers." },
  { label: 'Missing date', note: 'The agent asks staff for the date', text: 'Could we pay invoice DEMO-101 later?' },
  { label: 'Unclear date', note: '"Next Friday", sent on a Friday', text: 'Can we push DEMO-101 back to next Friday?' },
  { label: 'Unclear customer', note: 'Two customers are called Harbour', text: 'Hi, Harbour here - can we move our invoice to 30 October?' },
  { label: 'Overdue invoice', note: 'DEMO-201 is already a week late', text: 'Sorry for the delay on DEMO-201. Could we pay it on 23 October? A client paid us late.' },
];
const TOPICS = { request: 'the request', reason: 'the reason given', payment_promise: 'what they say about paying', other_request: 'a separate request, not handled here',
                 instruction_to_system: 'text aimed at the system (ignored)', other: 'a claim' };
const ACTIVE = ['received', 'analysing'];
const FIELD_WORDS = { requestedDueDate: 'the payment date', invoiceReference: 'the invoice number', invoiceId: "which customer's invoice it is" };

// Where a case stands, from the point of view of the role looking at it.
// A request staff opened by confirming an action (confirmedAction in the list, intake.structured in a case) has fixed details: nothing is answerable.
// A request the assistant resolved under the Owner's delegation policy (delegationCaseId in the list, intake.structured.caseId in a case) is fixed the same way.
const delegatedCaseOf = c => c?.delegationCaseId || c?.intake?.structured?.caseId || null;
const confirmedActionOf = c => c?.confirmedAction || c?.intake?.structured?.actionId || delegatedCaseOf(c) || null;
function statusOf(c, role = S.role) {
  const failed = c.aiStatus === 'failed';
  switch (c.status) {
    case 'received': case 'analysing': return { text: 'Preparing', cls: 'busy', group: 'open' };
    case 'needs_information': if (confirmedActionOf(c)) return role === 'staff' ? { text: 'Withdraw and prepare again', cls: 'need', mine: true, group: 'open' } : { text: 'Waiting for staff', cls: 'wait', group: 'open' };
      return role === 'staff' ? { text: 'Needs your answer', cls: 'need', mine: true, group: 'open' } : { text: 'Waiting for staff', cls: 'wait', group: 'open' };
    case 'awaiting_owner':
      if (c.withStaff) return role === 'staff' ? { text: 'Waiting on you', cls: 'need', mine: true, group: 'open' } : { text: 'Waiting for staff', cls: 'wait', group: 'open' };   // the owner's answer sent it back
      return role === 'owner' ? { text: failed ? 'Needs your decision, prepared without AI' : 'Needs your decision', cls: 'need', mine: true, group: 'open' }
      : { text: 'With the owner', cls: 'wait', group: 'open' };
    case 'decided': return { text: 'Saving the decision', cls: 'busy', group: 'open' };
    case 'preparation_failed': return { text: 'Couldn\'t prepare', cls: 'fail', mine: role === 'staff', group: 'open' };
    case 'withdrawn': return { text: 'Withdrawn', cls: 'done', group: 'done' };
    default: return c.outcome === 'decline' ? { text: 'Declined', cls: 'done', group: 'done' }
      : { text: c.approvedDueDate ? 'Approved to ' + dateText(c.approvedDueDate, false) : 'Approved', cls: 'done', group: 'done' };
  }
}
const chip = st => `<span class="chip ${st.cls}">${esc(st.text)}</span>`;

// A decision case: a request the assistant submitted (GET /api/decision-cases; its page is the timeline, #/decision-cases/<id>; the Owner acts on it on Review).
// The same chips and groups as a form request, so one list holds both.
function decisionStatusOf(c, role = S.role) {
  const d = c.decision || {};
  switch (c.status) {
    case 'awaiting_owner': return role === 'owner' ? { text: 'Needs your decision', cls: 'need', mine: true, group: 'open' } : { text: 'With the owner', cls: 'wait', group: 'open' };
    case 'on_hold': return role === 'owner' ? { text: 'Held by your policy: needs your decision', cls: 'need', mine: true, group: 'open' } : { text: 'On hold with the owner', cls: 'wait', group: 'open' };
    case 'gathering_evidence':
      if (c.evidenceExpired) return role === 'staff' ? { text: 'Information request expired: ask the assistant again', cls: 'fail', mine: true, group: 'open' } : { text: 'Stalled: Staff did not answer in time', cls: 'wait', group: 'open' };
      return role === 'staff' ? { text: 'Information needed from you', cls: 'need', mine: true, group: 'open' } : { text: 'Waiting for staff', cls: 'wait', group: 'open' };
    case 'closed': return { text: 'Closed', cls: 'done', group: 'done' };
    case 'decided': {   // who decided is part of the label: "Approved" alone read as "the owner looked at it" (Tony, 6 Nov 2026)
      const who = role === 'owner' ? 'you' : 'the owner';
      return d.overridden ? { text: d.by === 'agent' ? 'Overridden by ' + who : 'Approval withdrawn by ' + who, cls: 'done', group: 'done' }
        : d.outcome === 'decline' ? { text: d.by === 'agent' ? 'Declined by the assistant' : 'Declined by ' + who, cls: 'done', group: 'done' }
        : { text: d.by === 'agent' ? 'Approved by the assistant within the policy' : 'Approved by ' + who, cls: 'done', group: 'done' };
    }
    default: return { text: String(c.status || '').replace(/_/g, ' '), cls: 'done', group: 'done' };
  }
}
const decisionWhat = c => (typeof caseLine === 'function' && c.keyFacts ? caseLine(c).replace(/<[^>]+>/g, '') : (c.statusText || ''));

PAGES.requests = (r, seq) => renderDesk(r, seq);
PAGES.case = (r, seq) => renderDesk(r, seq);
PAGES.compose = (r, seq) => renderDesk(r, seq);

const FILTERS = [['all', 'All'], ['mine', 'For you'], ['open', 'In progress'], ['done', 'Done']];

async function renderDesk(r, seq) {
  const open = r.name !== 'requests';
  const filter = recalled('filter') || 'all';
  $('#main').innerHTML = `<div class="desk${open ? ' open' : ''}">
    <section class="queue" aria-labelledby="queue-title">
      <div class="queue-head"><div><h1 id="queue-title">Requests</h1><p class="lede">${S.role === 'owner' ? 'Every request, past and present, whether it came through the assistant or the form here, and who each one waits for: the record. To decide, agree, disagree or override, use <a href="#/review">Decide</a>.' : 'Every request, whether you sent it through the assistant or the form here, and who each one is waiting for.'}</p></div>${S.role === 'staff' ? `<div class="row"><a class="btn" href="#/cases/new"${r.name === 'compose' ? ' aria-current="page"' : ''} data-testid="new-request-form">Send one without the assistant</a></div>` : ''}</div>
      <div class="filters" role="group" aria-label="Show requests">${FILTERS.map(([k, label]) => `<button type="button" data-filter="${k}" aria-pressed="${k === filter}">${label}<span class="n" data-n="${k}"></span></button>`).join('')}</div>
      <div id="list" aria-live="polite">${loading('requests')}</div>
    </section>
    <section class="sheet" id="sheet" aria-label="${r.name === 'case' ? 'Case' : 'New request'}"></section>
  </div>`;
  $$('[data-filter]').forEach(b => { b.onclick = () => { remember('filter', b.dataset.filter); $$('[data-filter]').forEach(x => x.setAttribute('aria-pressed', x === b)); renderList(); }; });
  if (r.name === 'compose') renderComposer();
  await refreshCases(seq, true);
}

async function refreshCases(seq, first) {
  if (!$('#list')) return;
  let cases, decisions;
  try { [cases, decisions] = await Promise.all([api('/api/requests'), api('/api/decision-cases').then(x => x.cases).catch(() => S.decisionCases || [])]); } catch (error) {
    if (!live(seq)) return;
    if (error.status === 401) { S.session = null; return renderGate(null, 'Your session ended, for example because the app restarted. Sign in again.'); }
    if (first) renderFailure(error, () => refreshCases(seq, true), '#list');
    return;
  }
  if (!live(seq)) return;
  S.cases = cases;
  S.decisionCases = decisions || [];
  updateCount();
  renderList();
  const r = S.route;
  if (r.name === 'case') {
    const listed = cases.find(c => c.id === r.id);
    const moved = listed && S.current?.id === r.id && (listed.version !== S.current.version || listed.status !== S.current.status);
    if (first || S.current?.id !== r.id || moved) await openCase(r, seq);
  } else if (first && r.name === 'requests') { if (S.role === 'owner') renderOwnerHome(); else renderStaffHome(); }
}

function renderList() {
  const list = $('#list');
  if (!list) return;
  const filter = recalled('filter') || 'all';
  const current = S.route?.name === 'case' ? S.route.id : null;
  // every request as one row shape: the form requests (#/case/<id>) and the assistant's decision cases (#/decision-cases/<id>), newest first
  const all = [
    // a prepared form request has a decision case: its page is the request page; before that (preparing, a question for Staff) the old case page
    ...S.cases.map(c => ({ st: statusOf(c), href: delegatedCaseOf(c) && !['received', 'analysing', 'needs_information', 'preparation_failed'].includes(c.status) ? '#/decision-cases/' + delegatedCaseOf(c) : '#/case/' + c.id, current: c.id === current, createdAt: c.createdAt,
                           who: c.customerName || (ACTIVE.includes(c.status) ? 'New request' : 'Customer not identified yet'),
                           what: c.invoiceReference ? `Invoice ${c.invoiceReference}${c.requestedDueDate ? ', asked for ' + dateText(c.requestedDueDate, false) : ''}` : c.excerpt, via: '' })),
    // a form request that the agent prepared also has a decision case (requestId): one row, the form one, whose page carries the next action
    // Staff asked for information go straight to the page that takes it
    ...(S.decisionCases || []).filter(c => !c.requestId || !S.cases.some(r => r.id === c.requestId)).map(c => ({ st: decisionStatusOf(c), current: false, createdAt: c.createdAt,
                                           href: S.role === 'staff' && c.status === 'gathering_evidence' && c.actionId && !c.evidenceExpired ? '#/actions/' + c.actionId : '#/decision-cases/' + c.caseId,
                                           who: c.customer?.name || 'A customer', what: decisionWhat(c), via: 'Via the assistant', id: c.caseId })),
  ].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')));
  const counts = { all: all.length, mine: all.filter(x => x.st.mine).length, open: all.filter(x => x.st.group === 'open').length, done: all.filter(x => x.st.group === 'done').length };
  $$('[data-n]').forEach(n => { n.textContent = counts[n.dataset.n]; });
  const row = x => `<li><a class="case-row${x.st.mine ? ' mine' : ''}" href="${esc(x.href)}"${x.current ? ' aria-current="page"' : ''}${x.id ? ` data-testid="decision-row" data-case="${esc(x.id)}"` : ''}>
      <span class="who">${esc(x.who)}</span><span class="what">${x.via ? `<span class="chip">${esc(x.via)}</span> ` : ''}${esc(x.what)}</span>
      <span class="meta">${chip(x.st)}<time datetime="${esc(x.createdAt || '')}">${esc(timeText(x.createdAt))}</time></span></a></li>`;
  if (!all.length) {
    list.innerHTML = `<div class="empty"><p><b>No requests yet.</b></p><p>${!S.session.hasRecords ? 'Setup isn\'t finished, so requests can\'t be checked yet. <a href="#/setup">Open setup</a>.'
      : S.role === 'staff' ? 'Ask the assistant, or paste the customer\'s message into the form here.' : 'Requests appear here once staff send them, through the assistant or the form.'}</p></div>`;
    return;
  }
  const shown = filter === 'all' ? all : all.filter(x => filter === 'mine' ? x.st.mine : x.st.group === filter);
  if (!shown.length) { list.innerHTML = `<p class="empty">${filter === 'mine' ? 'Nothing needs you right now.' : 'No requests here.'} <button type="button" class="btn link" data-show-all>Show all</button></p>`; $('[data-show-all]', list).onclick = () => { remember('filter', 'all'); $$('[data-filter]').forEach(x => x.setAttribute('aria-pressed', x.dataset.filter === 'all')); renderList(); }; return; }
  if (filter !== 'all') { list.innerHTML = `<ul class="cases">${shown.map(row).join('')}</ul>`; return; }
  const groups = [['For you', all.filter(x => x.st.mine)], ['In progress', all.filter(x => !x.st.mine && x.st.group === 'open')], ['Done', all.filter(x => x.st.group === 'done')]];
  list.innerHTML = groups.filter(([, cs]) => cs.length).map(([title, cs]) => `<div class="group"><h2>${title} <span class="n">${cs.length}</span></h2><ul class="cases">${cs.map(row).join('')}</ul></div>`).join('');
}

// ---------------------------------------------------------------- composer (staff) and the owner's starting point

function renderComposer() {
  const sheet = $('#sheet');
  if (!sheet) return;
  if (S.role !== 'staff') { sheet.innerHTML = `<div class="state-msg"><p>Only staff send new requests. Switch to Staff at the top to send one.</p></div>`; return; }
  if (!S.session.hasRecords) {
    sheet.innerHTML = `<div class="compose">${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: 'New request' })}
      <div class="callout warn"><p><b>Setup isn't finished.</b> There's nothing to check a request against yet.</p><p><a class="btn primary" href="#/setup">Open setup</a></p></div></div>`;
    return;
  }
  const practice = S.session.dataMode === 'fictional';
  sheet.innerHTML = `<form class="compose" id="composer" novalidate>
    ${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: 'New request', lede: 'Paste the customer\'s message exactly as it arrived. The agent finds the customer and invoice, works out the dates and prepares the case for the owner. Nothing is sent to the customer.' })}
    ${field({ name: 'messageText', label: 'Customer\'s message', type: 'textarea', id: 'message', rows: 7, hint: 'It must be about paying an existing invoice later. Requests for more credit are not handled here.' })}
    ${formError()}
    <div class="row"><button class="btn primary" type="submit">Send to the agent</button>
      <span class="hint">Your draft is kept in this browser until you send it.</span></div>
    ${practice ? `<details class="samples"><summary>Practice messages</summary><ul>${SAMPLES.map((s, i) => `<li><button type="button" class="btn link" data-sample="${i}">${esc(s.label)}</button> <span class="hint">${esc(s.note)}</span></li>`).join('')}</ul></details>` : ''}
  </form>`;
  const form = $('#composer');
  const box = $('#message');
  box.value = stored('draft') || '';
  box.oninput = () => store('draft', box.value || undefined);
  $$('[data-sample]', form).forEach(b => { b.onclick = () => { box.value = SAMPLES[b.dataset.sample].text; store('draft', box.value); box.focus(); }; });
  form.onsubmit = event => {
    event.preventDefault();
    const body = { messageText: box.value };
    if (!body.messageText.trim()) return showErrors(form, { field: 'messageText', message: 'Paste the customer\'s message first.' });
    const id = 'create:' + body.messageText;
    busy($('[type=submit]', form), async () => {
      try {
        const created = await api('/api/requests', body, { key: keyFor(id) });
        keyDone(id);
        store('draft');
        toast('Sent to the agent', 'ok');
        location.hash = '#/case/' + created.id;
      } catch (error) { showErrors(form, error); }
    });
  };
}

function renderOwnerHome() {
  const sheet = $('#sheet');
  if (!sheet) return;
  const waiting = S.cases.filter(c => statusOf(c).mine);
  const decisions = (S.decisionCases || []).filter(c => decisionStatusOf(c).mine && !(c.requestId && S.cases.some(r => r.id === c.requestId)));
  const n = waiting.length + decisions.length;
  sheet.innerHTML = `<div class="state-msg start" data-testid="owner-start">${n
    ? `<h2>${n === 1 ? 'One request needs your decision' : n + ' requests need your decision'}</h2>
       ${decisions.length ? `<p>${decisions.length === 1 ? 'One came through the assistant' : decisions.length + ' came through the assistant'}: decide on the Decide page.</p>
       <p><a class="btn primary" href="#/review" data-testid="owner-start-review">Open Decide</a></p>` : ''}
       ${waiting.length ? `<p>${waiting.length === 1 ? 'One form request: open it to see the facts and decide.' : waiting.length + ' form requests: open one to see the facts and decide. The oldest is first below.'}</p>
       <p><a class="btn${decisions.length ? '' : ' primary'}" href="#/case/${esc(waiting[waiting.length - 1].id)}">Open ${waiting.length === 1 ? 'it' : 'the oldest'}</a></p>` : ''}`
    : '<h2>Nothing needs your decision</h2><p>Requests appear here once staff send them, through the assistant or the form.</p>'}</div>`;
}

// Staff land on the list: the assistant is the way to send a request; the form is the way without it.
function renderStaffHome() {
  const sheet = $('#sheet');
  if (!sheet) return;
  const mine = S.cases.filter(c => statusOf(c).mine).length + (S.decisionCases || []).filter(c => decisionStatusOf(c).mine && !(c.requestId && S.cases.some(r => r.id === c.requestId))).length;
  const assistant = typeof assistantHref === 'function' ? assistantHref() : null;
  sheet.innerHTML = `<div class="state-msg start" data-testid="staff-start">
    <h2>${mine ? (mine === 1 ? 'One request needs you' : mine + ' requests need you') : 'Nothing needs you right now'}</h2>
    <p>${mine ? 'It is under For you on the left.' : 'Every request you send, through the assistant or the form, is listed on the left with who it waits for.'}</p>
    ${assistant ? `<p><a class="btn primary" href="${esc(assistant)}" target="_blank" rel="noopener" data-testid="staff-start-assistant">Ask the assistant ↗</a></p>` : ''}
    <p><a class="btn${assistant ? '' : ' primary'}" href="#/cases/new">Send a request without the assistant</a> <span class="hint">A payment-extension request from the customer's message.</span></p></div>`;
}

// ---------------------------------------------------------------- case page

async function openCase(r, seq) {
  const sheet = $('#sheet');
  if (!sheet) return;
  stopPolling();
  if (S.current?.id !== r.id) sheet.innerHTML = loading('the case');
  let c;
  try { c = await api('/api/requests/' + r.id); } catch (error) {
    if (!live(seq)) return;
    sheet.innerHTML = `<div class="state-msg">${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: error.status === 404 ? 'Case not found' : 'This case didn\'t load' })}
      <p>${error.status === 404 ? 'It may have been cleared by a demo reset, or the link is wrong.' : esc(error.message)}</p>${error.status === 404 ? '' : '<button type="button" class="btn primary" id="retry">Try again</button>'}</div>`;
    const retry = $('#retry');
    if (retry) retry.onclick = () => openCase(r, seq);
    return;
  }
  if (!live(seq)) return;
  S.current = c;
  renderCase(seq);
}

function pollCase(seq) {
  stopPolling();
  if (!S.current || !ACTIVE.includes(S.current.status)) return;
  S.poll = setTimeout(async () => {
    try {
      const fresh = await api('/api/requests/' + S.current.id);
      if (!live(seq) || fresh.id !== S.route?.id) return;   // the user has moved on
      const changed = fresh.status !== S.current.status;
      S.current = fresh;
      renderCase(seq);
      if (changed) refreshCases(seq);
    } catch (error) { if (live(seq)) { if (error.status === 404) openCase(S.route, seq); else pollCase(seq); } }
  }, 1500);
}

function facts(c) {
  const s = c.analysis?.snapshot;
  const f = s?.facts;
  if (!f) return null;
  return { ...f, asOfDate: f.asOfDate || S.session.asOfDate, originalDueDate: s.invoice?.originalDueDate || f.currentEffectiveDueDate, amount: f.invoiceOutstanding ?? null };
}

function headline(c) {
  const d = c.decision;
  const owner = S.role === 'owner';
  switch (c.status) {
    case 'received': case 'analysing': return 'The agent is preparing this case.';
    case 'needs_information': return owner ? 'Staff need to add a missing detail before you can decide.' : c.analysis?.aiStatus === 'failed' ? 'The AI couldn\'t read this message. Add the missing details.' : 'The agent needs one more detail from you.';
    case 'awaiting_owner': return c.withStaff ? (owner ? 'Waiting for staff to answer you.' : 'The owner asked: ' + (c.withStaffWhy || c.withStaff.why) + '.')
      : owner ? 'Ready for your decision.' : 'With the owner for a decision. Nothing for you to do yet.';
    case 'withdrawn': return 'Withdrawn' + (c.withdrawn?.reason ? ': ' + c.withdrawn.reason : '') + '. Nothing was decided.';
    case 'decided': return 'Saving the decision.';
    case 'preparation_failed': return 'The app couldn\'t prepare this case because of a technical fault. The request is saved.';
    default: return d?.outcome === 'decline' ? (c.analysis?.snapshot?.currentEffectiveDueDate ? 'Declined. The original due date stays.' : 'Declined. Nothing changes on the invoice.') : `Approved. New payment date: ${dateText(d?.approvedDueDate)}.`;
  }
}

// A request opened from a confirmed action: who submitted it and which action, in the viewer's words. The owner decides it as any other request.
function submittedLine(c) {
  const id = confirmedActionOf(c);
  if (!id) return '';
  if (delegatedCaseOf(c) && !c.confirmedAction && !c.intake?.structured?.actionId) {
    const n = c.decision?.authority?.policyVersion;
    return `<p class="provenance" data-testid="delegated-request">Resolved by the assistant under ${typeof navRole === 'function' && navRole() === 'owner' ? 'your' : "the Owner's"} delegation policy${n !== undefined && n !== null ? ' (version ' + esc(n) + ')' : ''}, case ${esc(delegatedCaseOf(c))}. ${c.decision ? (c.decision.decisionSource === 'delegated_policy' ? 'The agent decided it inside that policy; ' : '') + 'Nucleon sent nothing to the customer.' : 'It is outside what the Owner delegated, so the Owner decides it.'}${S.role === 'owner' ? ' <a href="#/delegation">Delegation</a>' : ''}</p>`;
  }
  const link = S.role === 'owner' || S.role === 'staff' ? ` (confirmed action <a href="#/actions/${esc(id)}">${esc(id)}</a>)` : ` (confirmed action ${esc(id)})`;
  return `<p class="provenance" data-testid="confirmed-action">${S.role === 'owner' ? 'Submitted by staff for your review' : 'Submitted by staff for the owner\'s review'}${link}.</p>`;
}

function provenance(a, c) {
  if (c && confirmedActionOf(c)) return submittedLine(c) + (a?.aiStatus === 'not_used' ? '<p class="provenance" data-testid="provenance">Application code built this case from the confirmed values; no AI model read it.</p>' : '');
  if (!a) return '';
  if (a.aiStatus === 'failed') return `<p class="callout bad" data-testid="provenance">Prepared without AI: the model was ${a.failure?.kind === 'timeout' ? 'too slow to answer' : a.failure?.kind === 'invalid_output' ? 'returning unusable output' : 'unavailable'}. Code assembled the facts; check them before deciding.</p>`;
  if (a.aiStatus === 'mocked') return '<p class="provenance" data-testid="provenance">Prepared by the test agent. No AI model was used.</p>';
  if (a.aiStatus === 'not_used') return '<p class="provenance" data-testid="provenance">Opened from an action staff confirmed. Application code built this case; no AI model read it.</p>';
  const name = (a.model?.label || 'AI').split(' ')[0];
  return `<p class="provenance" data-testid="provenance">Prepared by the ${esc(name)} agent, running locally${a.brief?.format === 'brief-v1-legacy' ? ', in an earlier version' : ''}.</p>`;
}

function flagsHtml(c) {
  return (c.flags || []).map(fl => `<div class="callout warn" data-testid="flag"><p><b>${fl.kind === 'invoice_no_longer_in_records' ? 'The invoice was removed from the records after this decision.' : 'The records changed after this decision.'}</b>
    ${fl.description ? ` ${esc(fl.description)}.` : ''}${fl.outstandingBefore && fl.outstandingNow && fl.outstandingBefore !== fl.outstandingNow ? ` Amount still owed: was ${esc(fl.outstandingBefore)}; now ${esc(fl.outstandingNow)}.` : ''}</p>
    <p>The decision stands; check it if it matters. Recorded ${stamp(fl.at)}.</p></div>`).join('');
}

function renderCase(seq) {
  const c = S.current;
  const sheet = $('#sheet');
  if (!sheet || !c) return;
  const a = c.analysis;
  const snap = a?.snapshot;
  const f = facts(c);
  const who = snap?.customer?.name || (ACTIVE.includes(c.status) ? 'New request' : 'Customer not identified yet');
  const st = statusOf({ ...c, aiStatus: a?.aiStatus, outcome: c.decision?.outcome, approvedDueDate: c.decision?.approvedDueDate });
  const from = S.route.q.from && S.route.q.from.startsWith('customer_') ? S.route.q.from : null;
  const fromName = from && (R.data?.customers || []).find(x => x.id === from)?.name;
  const customerId = snap?.customer?.id;
  const tab = recalled('case-tab') || 'evidence';
  const panel = panelHtml(c, f) + withdrawHtml(c);
  sheet.innerHTML = `<article class="case" aria-labelledby="case-title" data-case="${esc(c.id)}">
    <p class="back">${from ? `<a href="#/customers/${esc(from)}">← ${esc(fromName || 'Customer')}</a>` : '<a href="#/cases" class="mobile-only">← Requests</a>'}</p>
    <header class="case-head">
      <h1 id="case-title">${esc(who)}</h1>
      <p class="case-sub">${snap?.invoice ? `Invoice ${esc(snap.invoice.reference)}` : 'Invoice not identified yet'}${customerId ? ` <a href="#/customers/${esc(customerId)}?from=${esc(c.id)}">Customer records</a>` : ''}</p>
      <p class="status-line" data-testid="status" data-status="${esc(c.status)}">${chip(st)} <span>${esc(headline(c))}</span></p>
      ${provenance(a, c)}${flagsHtml(c)}
    </header>
    <div class="case-grid${panel ? '' : ' solo'}">
      ${panel ? `<aside class="action" aria-label="Next step">${panel}</aside>` : ''}
      <div class="case-main">
        ${f ? `<section class="facts-card" aria-labelledby="facts-title"><h2 id="facts-title">Key facts</h2>${timelineHtml(c, f)}${factsHtml(f, c)}</section>` : ''}
        ${requestHtml(c)}${checksHtml(c)}${notesHtml(c)}
        <section class="detail-tabs" aria-label="More about this case">
          <div class="tabs" role="tablist" aria-label="More about this case">
            ${[['evidence', 'Evidence'], ['activity', 'Activity'], ['technical', 'Technical']].map(([k, label]) => `<button type="button" role="tab" id="tab-${k}" aria-controls="panel-${k}" aria-selected="${k === tab}" tabindex="${k === tab ? 0 : -1}">${label}</button>`).join('')}
          </div>
          <div class="tab-panel" role="tabpanel" id="panel-evidence" aria-labelledby="tab-evidence"${tab === 'evidence' ? '' : ' hidden'}>${evidenceHtml(c)}</div>
          <div class="tab-panel" role="tabpanel" id="panel-activity" aria-labelledby="tab-activity"${tab === 'activity' ? '' : ' hidden'}>${activityHtml(c)}</div>
          <div class="tab-panel" role="tabpanel" id="panel-technical" aria-labelledby="tab-technical"${tab === 'technical' ? '' : ' hidden'}>${technicalHtml(c)}</div>
        </section>
      </div>
    </div>
  </article>`;
  $$('#sheet [data-x]').forEach(el => {
    el.style.setProperty('--x', el.dataset.x + '%');
    if (el.dataset.w) el.style.setProperty('--w', el.dataset.w + '%');
  });
  bindTabs($('.tabs', sheet), k => remember('case-tab', k));
  bindPanel(c, f, seq);
  $$('.case-row').forEach(row => { if (row.getAttribute('href') === '#/case/' + c.id) row.setAttribute('aria-current', 'page'); else row.removeAttribute('aria-current'); });
  pollCase(seq);
}

// Accessible tabs: arrow keys move between tabs, the selected one is in the tab order.
function bindTabs(list, onSelect) {
  if (!list) return;
  const tabs = $$('[role=tab]', list);
  const select = t => {
    tabs.forEach(x => { const on = x === t; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; $('#' + x.getAttribute('aria-controls')).hidden = !on; });
    onSelect?.(t.id.replace(/^tab-/, ''));
  };
  tabs.forEach((t, i) => {
    t.onclick = () => select(t);
    t.onkeydown = e => {
      const to = e.key === 'ArrowRight' ? tabs[(i + 1) % tabs.length] : e.key === 'ArrowLeft' ? tabs[(i - 1 + tabs.length) % tabs.length] : e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[tabs.length - 1] : null;
      if (to) { e.preventDefault(); select(to); to.focus(); }
    };
  });
}

// The due-date timeline: today (the business date), the due date, the requested date and, once decided, the outcome.
function timelineHtml(c, f) {
  const d = c.decision;
  const points = [f.asOfDate, f.originalDueDate, f.currentEffectiveDueDate, f.requestedDueDate, d?.approvedDueDate].filter(Boolean).map(dayNum);
  const lo = Math.min(...points) - 2, hi = Math.max(...points) + 2;
  const x = iso => ((dayNum(iso) - lo) / (hi - lo)) * 100;
  const due = f.currentEffectiveDueDate;   // null when no due date is on record: no due mark and no extension bar
  const marks = [{ iso: f.asOfDate, title: 'Today', cls: 'today' }];
  if (due) marks.push({ iso: due, title: d?.outcome === 'approve' ? 'Was due' : 'Due' });
  if (due && f.originalDueDate && f.originalDueDate !== due) marks.push({ iso: f.originalDueDate, title: 'First due', cls: 'today' });
  if (!d || d.outcome === 'decline' || d.approvedDueDate === f.requestedDueDate) marks.push({ iso: f.requestedDueDate, title: d?.outcome === 'approve' ? 'Approved' : 'Asked for' });
  else marks.push({ iso: f.requestedDueDate, title: 'Asked for', cls: 'today' }, { iso: d.approvedDueDate, title: 'Approved' });
  marks.sort((p, q) => dayNum(p.iso) - dayNum(q.iso));
  let lastTop = -100;
  const belowAt = [];
  const placed = marks.map(m => {
    const pos = x(m.iso);
    const below = pos - lastTop < 16;
    if (!below) lastTop = pos;
    else belowAt.push(pos);
    const edge = pos < 9 ? ' edge-left' : pos > 91 ? ' edge-right' : '';
    return `<div class="mark ${m.cls || ''}${below ? ' below' : ''}${edge}" data-x="${pos.toFixed(2)}"><b>${esc(m.title)}</b><span>${esc(dateText(m.iso, false))}</span></div>`;
  }).join('');
  const end = d?.outcome === 'approve' ? d.approvedDueDate : f.requestedDueDate;
  const extFrom = due ? x(due) : null, extTo = x(end);
  const extClass = !d ? 'pending' : d.outcome === 'decline' ? 'declined' : S.justDecided === c.id ? 'just' : '';
  if (S.justDecided === c.id) S.justDecided = null;
  const extDays = d?.outcome === 'approve' ? (d.approvedExtensionDays ?? (d.approvedDueDate === f.requestedDueDate ? f.extensionDays : null)) : f.extensionDays;
  const clash = at => belowAt.some(b => Math.abs(b - at) < 16) ? ' low' : '';
  const lateX = f.daysOverdue > 0 ? (x(f.asOfDate) + x(f.currentEffectiveDueDate)) / 2 : null;
  const late = f.daysOverdue > 0 ? `<div class="span late" data-x="${x(f.currentEffectiveDueDate).toFixed(2)}" data-w="${(x(f.asOfDate) - x(f.currentEffectiveDueDate)).toFixed(2)}"></div><div class="gap late${clash(lateX)}" data-x="${lateX.toFixed(2)}">${days(f.daysOverdue)} late</div>` : '';
  const extLabelX = f.daysOverdue > 0 ? (x(f.asOfDate) + extTo) / 2 : (extFrom + extTo) / 2;
  const extShown = extDays > 0 && d?.outcome !== 'decline';
  const tall = (lateX != null && clash(lateX)) || (extShown && clash(extLabelX));
  return `<div class="timeline${tall ? ' tall' : ''}" aria-hidden="true">
    <div class="axis"></div>${late}
    ${due ? `<div class="span ext ${extClass}" data-x="${extFrom.toFixed(2)}" data-w="${(extTo - extFrom).toFixed(2)}"></div>` : ''}
    ${extShown ? `<div class="gap ext${clash(extLabelX)}" data-x="${extLabelX.toFixed(2)}">+${days(extDays)}</div>` : ''}
    ${placed}</div>`;
}

// What is owed on this invoice, with its certainty. "Not recorded" and "at most" are different evidence (QA U6), not one state.
function outstandingHtml(f) {
  if (f.outstandingExact) return certainty('exact', money(f.amount), 'as of ' + dateText(f.outstandingExactAsOf, false));
  if (f.outstandingBound) return certainty('atMost', money(f.amount), f.outstandingNote || money(f.allocatedAmount) + ' allocated from payments');
  if (f.amount) return certainty('stated', money(f.amount), f.outstandingAsOf ? 'as of ' + dateText(f.outstandingAsOf, false) : '');
  if (f.invoiceTotal) {
    const um = f.unmatchedPayments;
    return certainty('none', '', `Invoice ${money(f.invoiceTotal)} · ${money(f.allocatedAmount || { ...f.invoiceTotal, minorUnits: '0' })} allocated · still owed not stated` +
      (um ? `. ${um.count} unmatched payment${um.count === 1 ? '' : 's'} for this customer (${money(um.amount)}) may apply` : ''));
  }
  return certainty('none', '', 'no amount still owed is stated, and no payments are allocated to this invoice');
}

function factsHtml(f, c) {
  const d = c.decision;
  const dueLabel = !d ? 'Due date now' : d.outcome === 'approve' ? 'Previous due date' : 'Due date, unchanged';
  return `<dl class="facts">
    <div class="fact wide"><dt>Still owed on this invoice</dt><dd>${outstandingHtml(f)}</dd></div>
    <div class="fact"><dt>${dueLabel}</dt><dd>${f.currentEffectiveDueDate ? esc(dateText(f.currentEffectiveDueDate)) : '<span class="muted">Not on record</span>'}</dd></div>
    <div class="fact"><dt>Asked to pay on</dt><dd>${esc(dateText(f.requestedDueDate))}</dd></div>
    <div class="fact"><dt>${d?.outcome === 'approve' && d.approvedDueDate !== f.requestedDueDate ? 'Extension asked for' : 'Extension'}</dt><dd>${f.extensionDays == null ? '<span class="muted">Not calculated</span>' : esc(days(f.extensionDays))}</dd></div>
    ${d?.outcome === 'approve' && d.approvedDueDate !== f.requestedDueDate && d.approvedExtensionDays != null ? `<div class="fact"><dt>Extension approved</dt><dd>${esc(days(d.approvedExtensionDays))}</dd></div>` : ''}
    <div class="fact"><dt>Overdue today</dt><dd class="${f.daysOverdue > 0 ? 'late' : ''}">${f.daysOverdue == null ? '<span class="muted">Unknown</span>' : f.daysOverdue > 0 ? esc(days(f.daysOverdue)) : 'No'}</dd></div>
    ${f.originalDueDate && f.originalDueDate !== f.currentEffectiveDueDate ? `<div class="fact"><dt>First due date</dt><dd>${esc(dateText(f.originalDueDate))}</dd></div>` : ''}
  </dl>
  <p class="hint">${f.outstandingExact ? 'Calculated by the app from the invoice, the payments allocated to it and the owner\'s statement that this customer\'s payment records are complete.' : 'Calculated by the app from the invoice record.'}${f.currentEffectiveDueDate ? '' : ' No due date is on record, so the day counts aren\'t calculated.'}${f.daysOverdue == null && f.daysOverdueReason && f.currentEffectiveDueDate ? ' Days overdue aren\'t calculated: ' + esc(f.daysOverdueReason) + '.' : ''} Day counts use the business date, ${esc(dateText(f.asOfDate))}${S.session.fixedDate ? ', fixed for practice' : ''}.</p>`;
}

// The customer's own words, with the agent's quotes underlined in place.
function requestHtml(c) {
  const text = c.intake.text;
  if (confirmedActionOf(c)) return `<section aria-labelledby="msg-title"><h2 id="msg-title">The request as confirmed</h2>
    <blockquote class="voice" data-testid="message">${esc(text)}</blockquote>
    <p class="hint">${delegatedCaseOf(c) && !c.intake?.structured?.actionId ? 'Written by Nucleon from the values the assistant resolved, not the customer\'s words. The reason is the assistant\'s.' : 'Written by Nucleon from the values a person confirmed, not the customer\'s words. The reason was drafted by the assistant and submitted as drafted.'}</p></section>`;
  const statements = c.analysis?.brief?.customerStatements || [];
  const spans = [];
  const unplaced = [];
  for (const s of statements) {
    const needle = s.quote.trim().replace(/[.?!]+$/, '');
    const at = text.toLowerCase().indexOf(needle.toLowerCase());
    if (at < 0 || spans.some(p => at < p.end && at + needle.length > p.start)) unplaced.push(s);
    else spans.push({ start: at, end: at + needle.length, topic: s.topic });
  }
  spans.sort((p, q) => p.start - q.start);
  let html = '', i = 0;
  for (const p of spans) {
    html += esc(text.slice(i, p.start)) + `<mark title="${esc(TOPICS[p.topic] || p.topic)}">${esc(text.slice(p.start, p.end))}</mark><span class="visually-hidden"> (${esc(TOPICS[p.topic] || p.topic)})</span>`;
    i = p.end;
  }
  html += esc(text.slice(i));
  const topics = [...new Set(spans.map(p => TOPICS[p.topic] || p.topic))];
  return `<section aria-labelledby="msg-title"><h2 id="msg-title">What the customer wrote</h2>
    <blockquote class="voice" data-testid="message">${html}</blockquote>
    <p class="hint">Their words as received, not verified.${topics.length ? ` Underlined: ${esc(topics.join(', '))}, as picked out by the agent.` : ''}</p>
    ${unplaced.length ? `<ul class="quotes">${unplaced.map(s => `<li><span>${esc(TOPICS[s.topic] || s.topic)}:</span> <q>${esc(s.quote)}</q></li>`).join('')}</ul>` : ''}
  </section>`;
}

// withSuggest false: the suggestion step's items are left to the suggestion line (the desk shows them there).
function checksHtml(c, withSuggest = true) {
  const b = c.analysis?.brief;
  if (!b) return '';
  const items = ['brief-v2', 'brief-v3'].includes(b.format) ? b.openItems.filter(i => !['fictional', 'unverified_statements'].includes(i.kind) && (withSuggest || i.step !== 'suggest')).map(i => i.text) : [];
  const legacy = b.format === 'brief-v1-legacy' ? `<p class="callout warn" data-testid="legacy">This case was prepared by an earlier version. Its notes were written by the model and weren't checked for meaning, so rely on the calculated facts, or prepare it again.</p>` : '';
  if (!items.length && !legacy) return '';
  return `<section aria-labelledby="check-title"><h2 id="check-title">Worth checking</h2>${legacy}
    ${items.length ? `<ul class="points">${items.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}</section>`;
}

function notesHtml(c) {
  const notes = c.analysis?.brief?.ownerNotes || c.analysis?.snapshot?.confirmedNotes || [];
  const customer = c.analysis?.snapshot?.customer?.name;
  if (!notes.length) return '';
  const scope = n => n.scope?.kind === 'business' ? 'Whole business' : esc(customer || 'This customer');
  return `<section aria-labelledby="notes-title"><h2 id="notes-title">${S.role === 'owner' ? 'What you\'ve noted' : 'What the owner has noted'}</h2>
    <ul class="notes">${notes.map(n => `<li><p>${esc(n.text)}</p><p class="hint">${scope(n)}${n.kind === 'rule' ? '. A rule to follow; the system doesn\'t check it' : ''}. Confirmed by the owner.</p></li>`).join('')}</ul></section>`;
}

// ---------------------------------------------------------------- the next action (one per state)

function panelHtml(c, f) {
  const a = c.analysis;
  if (ACTIVE.includes(c.status)) return `<div class="action-in" aria-live="polite" data-testid="progress">${progressHtml(c)}</div>`;
  if (c.status === 'needs_information' && confirmedActionOf(c)) return `<div class="action-in" data-testid="confirmed-locked"><h2>${S.role === 'staff' ? 'This request cannot be completed here' : 'Waiting for staff'}</h2>
    <p class="agent-q">${esc(c.task.question)}</p><p class="hint">It was opened from a confirmed action, so its customer, invoice and date are fixed and nothing can be answered. ${S.role === 'staff' ? 'Withdraw it, then ask the assistant to prepare a new proposal.' : 'Staff withdraw it and ask the assistant to prepare a new proposal.'}</p></div>`;
  if (c.status === 'needs_information') {
    if (S.role !== 'staff') return `<div class="action-in"><h2>Waiting for staff</h2><p class="agent-q">${esc(c.task.question)}</p><p class="hint">Staff answer this, then the agent prepares the case again. Switch to Staff to answer it yourself.</p></div>`;
    const floor = snapFloor(c);
    return `<form class="action-in" id="answer" novalidate>
      <h2>${a?.aiStatus === 'failed' ? 'Add the missing details' : 'The agent needs a detail'}</h2>
      <p class="agent-q">${esc(c.task.question)}</p>
      ${c.task.missingFields.map(m => m.field === 'invoiceId' ? choiceHtml(m)
        : m.field === 'requestedDueDate' ? field({ name: 'requestedDueDate', label: 'Payment date the customer asked for', type: 'date', id: 'ans-requestedDueDate', attrs: `min="${floor}"`, hint: `On or after ${esc(dateText(floor))}: later than the ${floor > nextDay(c.analysis?.snapshot?.asOfDate || S.session.asOfDate) ? 'current due date' : 'business date'}.` })
        : field({ name: 'invoiceReference', label: 'Invoice number', id: 'ans-invoiceReference', attrs: 'autocomplete="off"', hint: 'As it appears on the invoice, for example DEMO-101.' })).join('')}
      ${formError()}
      <button class="btn primary wide" type="submit">${a?.aiStatus === 'failed' ? 'Save the details' : 'Send to the agent'}</button>
      <p class="hint">Your answer is recorded as coming from staff.</p>
    </form>`;
  }
  if (c.status === 'withdrawn') return `<div class="action-in" data-testid="withdrawn"><h2>Withdrawn</h2><p>${esc(c.withdrawn?.reason || '')}</p><p class="hint">Nothing was decided, and a withdrawn request is not reopened.</p></div>`;
  if (c.status === 'awaiting_owner') {
    if (S.role !== 'owner' && c.withStaff) return `<div class="action-in" data-testid="with-staff"><h2>Waiting on you</h2><p class="agent-q">The owner asked: ${esc(c.withStaffWhy || c.withStaff.why)}</p><p class="hint">Reply in the assistant on the Desk, or raise a concern there; the case then goes back to the owner.</p></div>`;
    if (S.role !== 'owner') return `<div class="action-in"><h2>With the owner</h2><p>The owner decides this request. Nothing for staff to do until then.</p></div>`;
    const floor = nextDay(f.currentEffectiveDueDate > f.asOfDate ? f.currentEffectiveDueDate : f.asOfDate);
    return `<form class="action-in" id="decide" novalidate>
      <h2>Your decision</h2>
      <fieldset class="choices"><legend class="visually-hidden">Outcome</legend>
        <label class="choice"><input type="radio" name="outcome" value="approve"><span>Approve ${esc(dateText(f.requestedDueDate, false))}<small>The date the customer asked for</small></span></label>
        <label class="choice"><input type="radio" name="outcome" value="other"><span>Approve a different date</span></label>
        <div class="field nested" id="other-date" hidden><label for="approvedDueDate">New payment date</label>
          <input id="approvedDueDate" name="approvedDueDate" type="date" min="${floor}" value="${esc(f.requestedDueDate)}">
          <p class="error" data-error-for="approvedDueDate" role="alert"></p></div>
        <label class="choice"><input type="radio" name="outcome" value="decline"><span>Decline<small>${f.currentEffectiveDueDate ? 'The current due date stays' : 'Nothing changes on the invoice'}</small></span></label>
        <p class="error" data-error-for="outcome" role="alert"></p>
      </fieldset>
      ${field({ name: 'reason', label: 'Reason', id: 'reason', attrs: 'autocomplete="off"', hint: 'A short note for the record. The customer doesn\'t see it.' })}
      ${formError()}
      <button class="btn primary wide" type="submit">Record decision</button>
      <p class="hint">${(a.brief?.suggestionStatus || 'off') === 'off' ? 'The agent doesn\'t recommend an outcome. ' : ''}This applies to invoice ${esc(c.analysis.snapshot.invoice.reference)} only, and nothing is sent to the customer.</p>
    </form>`;
  }
  if (c.status === 'preparation_failed') {
    const p = c.preparationFailure || {};
    return `<div class="action-in" data-testid="preparation-failed"><h2>Preparation failed</h2>
      <p>Neither the agent nor the app's no-AI fallback could prepare this case (${esc(p.kind || 'error')}; fallback: ${esc(p.fallbackError || 'error')}). This is a technical fault, not missing information. The customer's message is kept.</p>
      <button class="btn primary wide" type="button" id="prepare-again">Prepare again</button>
      <p class="hint">It won't retry by itself. If it fails again, tell whoever runs the app; the details are under Technical.</p></div>`;
  }
  if (c.status === 'completed' || c.status === 'decided') {
    const d = c.decision;
    return `<div class="action-in" data-testid="decision">
      ${c.responseDraft ? `<h2>Reply to send</h2><div class="draft" id="draft">${esc(c.responseDraft.text)}</div>
        ${S.role === 'staff' ? '<button class="btn primary wide" type="button" id="copy"><span>Copy reply</span></button>' : ''}
        <p class="hint">Not sent. ${S.role === 'staff' ? 'Paste it into your usual email.' : 'Staff send it from their usual email.'}</p>` : '<p>Saving the reply…</p>'}
      <dl class="decision-meta"><div><dt>Decided by</dt><dd>${esc(deciderText(d))}, ${stamp(d.decidedAt)}</dd></div><div><dt>Reason</dt><dd>${esc(d.reason)}</dd></div><div><dt>Applies to</dt><dd>This invoice only</dd></div>${d.decisionSource === 'delegated_policy' ? `<div><dt>Authority</dt><dd data-testid="authority">Owner policy version ${esc(d.authority?.policyVersion)}${S.role === 'owner' ? ' · <a href="#/delegation">Review on the Delegation page</a>' : ''}</dd></div>` : ''}</dl>
    </div>`;
  }
  return '';
}

// A request opened by mistake is closed with a reason, while no decision exists (the withdrawRequest tool; nothing is decided).
const WITHDRAWABLE = ['needs_information', 'awaiting_owner', 'preparation_failed'];
function withdrawHtml(c) {
  if (!WITHDRAWABLE.includes(c.status)) return '';
  return `<details class="withdraw" data-testid="withdraw"><summary>Withdraw this request</summary>
    <form id="withdraw" class="action-in" novalidate>
      <p class="hint">For a request opened by mistake. Nothing is decided, and a withdrawn request is not reopened.</p>
      ${field({ name: 'reason', label: 'Why is it withdrawn?', id: 'withdraw-reason', attrs: 'autocomplete="off" maxlength="500"' })}
      ${formError()}
      <button class="btn wide" type="submit">Withdraw request</button>
    </form></details>`;
}

// One invoice number used by several customers: staff pick the customer's invoice; it is never chosen for them.
function choiceHtml(m) {
  return `<fieldset class="choices"><legend>Which customer's invoice is it?</legend>
    ${m.choices.map(c => `<label class="choice"><input type="radio" name="invoiceId" value="${esc(c.invoiceId)}"><span>${esc(c.customerName)}<small>Customer ${esc(c.customerCode)}, invoice ${esc(c.reference)}${c.issueDate ? ', issued ' + esc(dateText(c.issueDate, false)) : ''}${c.originalDueDate ? ', due ' + esc(dateText(c.originalDueDate, false)) : ''}</small></span></label>`).join('')}
    <p class="error" data-error-for="invoiceId" role="alert"></p></fieldset>`;
}

function snapFloor(c) {
  const due = c.analysis?.snapshot?.currentEffectiveDueDate;
  const today = c.analysis?.snapshot?.asOfDate || S.session.asOfDate;
  return nextDay(due && due > today ? due : today);
}

const STEP = {
  findCustomers: ok => ok ? 'Found the customer' : 'Couldn\'t identify the customer',
  getInvoiceFacts: ok => ok ? 'Checked the invoice' : 'Couldn\'t settle on one invoice',
  getConfirmedKnowledge: () => 'Read the owner\'s notes',
  calculateExtension: ok => ok ? 'Calculated the extension' : 'The requested date doesn\'t work',
};

function progressHtml(c) {
  const run = (c.runs || []).find(x => x.id === c.activeRunId);
  const events = c.history.filter(e => e.data.runId && e.data.runId === c.activeRunId);
  const steps = [];
  for (const e of events) {
    if (e.kind === 'agent.extracted') steps.push(['Read the message', '']);
    else if (e.kind === 'tool.executed' && STEP[e.data.tool]) steps.push([STEP[e.data.tool](e.data.ok), e.data.ok ? '' : 'blocked']);
    else if (e.kind === 'tool.rejected') steps.push(['Stopped a step the agent isn\'t allowed to take', 'blocked']);
    else if (e.kind === 'model.call' && e.data.error) steps.push(['The model didn\'t answer', 'blocked']);
  }
  const started = run?.startedAt ? Math.max(0, Math.round((Date.now() - Date.parse(run.startedAt)) / 1000)) : null;
  return `<h2>Preparing the case</h2>
    <ol class="steps">${steps.map(([t, cls]) => `<li class="${cls}">${esc(t)}</li>`).join('')}
      <li class="now">${started === null ? 'Waiting for the agent to start' : steps.length ? 'Working on the next step' : 'Reading the message'}<small>${started === null ? '' : started + ' s so far'}</small></li></ol>
    <p class="hint">${run?.mode === 'live' ? 'The AI model runs on this server and usually takes 10 to 20 seconds.' : 'Usually a few seconds.'} You can leave this page; the case keeps preparing.</p>`;
}

// Specific messages for missing answers (QA U10), checked before anything is sent.
const MISSING = { invoiceId: 'Choose which customer\'s invoice this is.', requestedDueDate: 'Enter the payment date the customer asked for.', invoiceReference: 'Enter the invoice number.' };

// The desk passes `extra` (more fields for the decision) and `after` (what to draw again); the case page uses the defaults.
function bindPanel(c, f, seq, { extra, after = () => refreshCases(seq, true) } = {}) {
  const answer = $('#answer');
  if (answer) answer.onsubmit = event => {
    event.preventDefault();
    const names = [...new Set($$('input[name]', answer).map(i => i.name))];   // a radio group is one answer
    const body = { expectedRequestVersion: c.version, answers: names.map(name => ({ field: name, value: (answer.elements[name].value || '').trim() })) };
    const missing = body.answers.find(x => !x.value);
    if (missing) return showErrors(answer, { field: missing.field, message: MISSING[missing.field] || 'Enter an answer.' });
    const date = body.answers.find(x => x.field === 'requestedDueDate');
    if (date && date.value < snapFloor(c)) return showErrors(answer, { field: 'requestedDueDate', message: `Enter a date on or after ${dateText(snapFloor(c))}.` });
    const id = 'answer:' + c.id + ':' + JSON.stringify(body);
    busy($('[type=submit]', answer), async () => {
      try { await api(`/api/requests/${c.id}/clarifications/${c.task.id}/answers`, body, { key: keyFor(id) }); keyDone(id); toast('Answer sent to the agent', 'ok'); await after(); }
      catch (error) { showErrors(answer, error); }
    });
  };
  const withdraw = $('#withdraw');
  if (withdraw) withdraw.onsubmit = event => {
    event.preventDefault();
    const reason = withdraw.elements.reason.value.trim();
    if (!reason) return showErrors(withdraw, { field: 'reason', message: 'Say why it is withdrawn.' });
    const id = 'withdraw:' + c.id + ':' + reason;
    busy($('[type=submit]', withdraw), async () => {
      try {
        const done = await api('/api/tools/withdrawRequest', { args: { requestId: c.id, reason } }, { key: keyFor(id) });
        if (done.ok === false) throw { message: done.message };
        keyDone(id); toast('Request withdrawn', 'ok'); await after();
      } catch (error) { showErrors(withdraw, error); }
    });
  };
  const decide = $('#decide');
  if (decide) {
    const submit = $('[type=submit]', decide);
    const update = () => {   // the button names what will be recorded
      const choice = decide.outcome.value;
      $('#other-date').hidden = choice !== 'other';
      submit.textContent = choice === 'approve' ? 'Approve ' + dateText(f.requestedDueDate, false)
        : choice === 'other' ? ($('#approvedDueDate').value ? 'Approve ' + dateText($('#approvedDueDate').value, false) : 'Approve the new date')
        : choice === 'decline' ? 'Decline the request' : 'Record decision';
    };
    $$('input[name=outcome]', decide).forEach(i => { i.onchange = update; });
    $('#approvedDueDate').oninput = update;
    decide.onsubmit = event => {
      event.preventDefault();
      const choice = decide.outcome.value;
      if (!choice) return showErrors(decide, { field: 'outcome', message: 'Choose an outcome: approve the date asked for, approve a different date, or decline.' });
      const approvedOther = $('#approvedDueDate').value;
      if (choice === 'other' && !approvedOther) return showErrors(decide, { field: 'approvedDueDate', message: 'Enter the new payment date.' });
      const reason = $('#reason').value.trim();
      if (!reason) return showErrors(decide, { field: 'reason', message: 'Add a short reason for the record.' });
      const approved = choice === 'approve' ? f.requestedDueDate : choice === 'other' ? approvedOther : null;
      const body = { expectedRequestVersion: c.version, analysisId: c.analysis.id, evidenceVersion: c.analysis.snapshot.evidenceVersion,
        outcome: choice === 'decline' ? 'decline' : 'approve', approvedDueDate: approved, reason, ...extra?.() };
      const id = 'decide:' + c.id + ':' + JSON.stringify(body);
      busy($('[type=submit]', decide), async () => {
        try { await api(`/api/requests/${c.id}/decisions`, body, { key: keyFor(id) }); keyDone(id); S.justDecided = c.id; toast(body.outcome === 'approve' ? 'Approved ' + dateText(approved) : 'Declined', 'ok'); await after(); }
        catch (error) {
          if (error.code === 'STALE_EVIDENCE' || error.code === 'STALE_VERSION') error = { ...error, field: null, message: 'This case changed while you were reading it. It is being prepared again; decide once it is ready.' };
          showErrors(decide, error);
        }
      });
    };
  }
  const copy = $('#copy');
  if (copy) copy.onclick = async () => {   // QA U3: the button itself confirms, as well as the message at the bottom
    try {
      await navigator.clipboard.writeText($('#draft').textContent);
      $('span', copy).textContent = 'Copied';
      copy.classList.add('done');
      toast('Reply copied. Paste it into your email.', 'ok');
      setTimeout(() => { if (copy.isConnected) { $('span', copy).textContent = 'Copy reply'; copy.classList.remove('done'); } }, 2500);
    } catch {
      const range = document.createRange(); range.selectNodeContents($('#draft'));
      getSelection().removeAllRanges(); getSelection().addRange(range);
      toast('Copying isn\'t allowed here. The reply is selected: press Ctrl+C or Cmd+C.');
    }
  };
  $$('#prepare-again, [data-prepare-again]').forEach(again => {
    again.onclick = () => {
      const id = 'reanalyse:' + c.id + ':' + c.version;
      busy(again, async () => {
        try { await api(`/api/requests/${c.id}/reanalyse`, { expectedRequestVersion: c.version }, { key: keyFor(id) }); keyDone(id); toast('Preparing again', 'ok'); await after(); }
        catch (error) { toast(error.message, 'bad'); }
      });
    };
  });
}

// ---------------------------------------------------------------- evidence, activity, technical

// Where a recorded amount came from, from the invoice's own record (outstandingSource, setBy), never from the customer's message.
function recordedText(s) {
  const by = s.setBy || {}, on = by.at ? ' on ' + esc(dateText(String(by.at).slice(0, 10))) : '';
  const who = actorWho(by, by.role === 'owner' ? 'the owner' : by.role === 'staff' ? 'staff' : 'a person');
  const file = by.fileName || by.sourceLabel;
  switch (s.origin) {
    case 'file': return 'From the import of ' + (file ? esc(file) : 'a file') + on;
    case 'correction': return 'Corrected by ' + who + on;
    case 'opening_balance': return 'From the opening balance' + on;
    case 'sample': return 'From the sample records';
    default: return by.role ? 'Entered by ' + who + on : 'Entered manually';   // manual (an analysis stored before setBy was kept says no more)
  }
}

// "owner decision" / "staff decision within the owner's authority" / "decision by AI Agent (as staff)"; a record with no attribution says so neutrally.
function dueDeciderText(s) {
  const t = deciderText(s);
  if (s.actorName) return 'decision by ' + t;
  if (t === 'The owner') return 'owner decision';
  if (t === 'Staff') return 'staff decision';
  if (/^Staff, within/.test(t)) return "staff decision within the owner's authority";
  return 'recorded decision';
}

function sourceText(fact) {
  const s = fact.source || {};
  if (fact.kind === 'unknown') return esc(fact.reason);
  if (fact.kind === 'calculation') return 'Calculated by the app: ' + esc(fact.formula);
  if (fact.kind === 'configuration') return 'The business date for this workspace';
  if (fact.kind === 'owner_decision_record') return 'Set by an earlier ' + dueDeciderText(s) + ', recorded ' + stamp(s.decidedAt);
  if (fact.kind === 'account_fact') return `Invoice ${esc(s.locator)} record${fact.note ? ', ' + esc(fact.note) : ''}`;
  if (fact.kind === 'stated') return recordedText(s) + ' <span class="tag">Not verified</span>';
  if (fact.kind === 'bounded') return 'Payments allocated to invoice ' + esc(s.locator) + (fact.note ? ', ' + esc(fact.note) : '');
  if (s.origin === 'staff_reported') return 'Staff answer <span class="tag">Not confirmed by the customer</span>';
  if (s.origin === 'confirmed_action') return 'Fixed when staff confirmed the proposal <span class="tag">Not verified</span>';
  return `Customer's words "${esc(s.quote)}", read by ${s.interpretedBy === 'model' ? 'the agent' : 'the basic parser'}${s.interpretation === 'relative' ? ' from relative wording' : ''} <span class="tag">Not verified</span>`;
}

// Calculation details: the basis the records froze with the decision once it is decided (never the latest assessment then), else the one
// kept with the latest assessment. Every figure and sentence is the basis's own, written by the records; nothing is worked out here.
const CALC_RESULT = { pass: 'Pass', fail: 'Fail', unknown: 'Unknown', 'not set': 'Not set' };
const CALC_OUTCOME = { approve_within_authority: 'Within the limits the owner set', decline_by_policy: 'Declined by policy', escalate: 'Escalate to the owner' };
const CALC_KIND = { invoice: 'Invoice', payment: 'Payment', allocation: 'Allocation of payment', openingBalance: 'Opening balance' };
const ASSUMED = 'Applied oldest first (an assumption, not a record)';
function calcHtml(c) {
  if (!c.assessment && !c.decision) return '';
  const frozen = c.decision?.basis, b = c.decision ? frozen?.basis : c.assessment?.basis;
  const open = '<details class="why calc" data-testid="calc-details"><summary>Calculation details</summary>';
  // a decision without details says why in the records' words (decisionBasisGap: read from the case's assessments, never from the missing basis alone)
  if (!b) return open + `<p class="hint" data-testid="calc-gap"${c.decision ? ` data-gap="${esc(c.decisionBasisGap?.kind || '')}"` : ''}>${c.decision ? esc(c.decisionBasisGap?.text || 'The records do not say why this decision has no calculation details.')
    : 'Calculation details were not kept for this assessment: it was made before they were recorded.'}</p></details>`;
  const ref = (x, label) => x?.link ? `<a href="${esc(x.link)}">${esc(label ?? x.reference ?? 'no reference')}</a>` : esc(label ?? x?.reference ?? 'no reference');
  const named = x => esc(CALC_KIND[x.kind] || x.kind) + (x.reference ? ' ' + ref(x) : '');
  const table = (label, head, rows) => rows.length ? `<div class="table-wrap"><table class="sources" data-table="${label}"><thead><tr>${head.map(h => `<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>` : '<p class="hint">None.</p>';
  const each = (xs, f) => (xs || []).length ? xs.map(f).join('<br>') : '-';
  const dash = (text, value) => value === 0 || !text ? '-' : esc(text);
  const dl = rows => `<table class="sources"><tbody>${rows.map(r => `<tr><th scope="row">${esc(r.name)}</th><td>${esc(r.text)}${r.note ? `<br><span class="hint-inline">${esc(r.note)}</span>` : ''}</td></tr>`).join('')}</tbody></table>`;
  const inv = b.records.invoices.map(i => `<tr><th scope="row">${ref(i)}</th><td>${esc(i.issueText)}</td><td>${esc(i.originalDueText)}</td>
    <td>${esc(i.effectiveDueText)}${i.effectiveDueSource?.kind === 'decision' ? ` (<a href="${esc(i.effectiveDueSource.link)}">moved by a decision</a>)` : ''}</td><td>${esc(i.totalText)}</td>
    <td>${esc(i.remainderText)} (${esc(i.remainderBasis)})${i.stated && i.counted !== 'stated' ? `; stated ${esc(i.stated.amountText)}${i.stated.asOfText ? ' as of ' + esc(i.stated.asOfText) : ''}` : ''}</td></tr>`);
  const pay = b.records.payments.map(r => ({ ...r, trail: r.step != null ? b.trail[r.step] : null })).map(p => `<tr><td>${esc(p.receivedText)}</td><th scope="row">${ref(p)}</th><td>${esc(p.amountText)}</td>
    <td>${p.trail ? each(p.trail.recorded, x => esc(x.amountText) + ' to ' + ref(x) + (x.statusText ? ' (' + esc(x.statusText) + ')' : '')) : each(p.recordedAllocations, x => esc(x.amountText) + ' to ' + ref(x)) + `<br><span class="hint-inline">${esc(p.note)}</span>`}</td>
    <td>${p.trail ? each(p.trail.oldestFirst, x => esc(x.amountText) + ' to ' + ref(x)) : '-'}</td><td>${p.trail ? dash(p.trail.toOpeningText, p.trail.toOpening) : '-'}</td><td>${p.trail ? dash(p.trail.toCreditText, p.trail.toCredit) : '-'}</td></tr>`);
  const step = e => e.kind === 'invoice'
    ? `<li data-step="invoice">${esc(e.dateText)} · Invoice ${ref(e)} issued: ${esc(e.totalText)}, due ${esc(e.originalDueText)}.<ul class="points">${(e.appliedOnIssue || []).map(x => `<li>${esc(x.label)}: ${esc(x.amountText)}${x.from ? ' from payment ' + ref(x.from) + ' (received before the invoice)' : ''}</li>`).join('')}<li>Left on it: ${esc(e.leftAfterText)}</li></ul></li>`
    : `<li data-step="payment">${esc(e.dateText)} · Payment ${ref(e)} received: ${esc(e.amountText)}. ${esc(e.lateText)}.<ul class="points">${(e.recorded || []).map(x => `<li>Recorded allocation: ${esc(x.amountText)} to ${ref(x)}${x.statusText ? ' (' + esc(x.statusText) + ')' : ''}</li>`).join('')}${(e.oldestFirst || []).map(x => `<li>${ASSUMED}: ${esc(x.amountText)} to ${ref(x)}</li>`).join('')}${e.toOpening > 0 ? `<li>To the opening balance: ${esc(e.toOpeningText)}</li>` : ''}${e.toCredit > 0 ? `<li>To customer credit: ${esc(e.toCreditText)}</li>` : ''}</ul></li>`;
  return open + `<div class="calc-body" data-calc="${esc(b.calculationVersion)}">
    <h4>Basis</h4>${dl([{ name: 'As of', text: b.asOfText }, { name: 'Currency', text: b.currency + ', ' + b.scale + ' decimal places' }, { name: 'Calculation version', text: b.calculationVersion },
      ...(b.assessmentVersion != null ? [{ name: 'Assessment version', text: String(b.assessmentVersion) }] : []), ...b.policy.rows])}
    <h4>Records included</h4>${table('invoices', ['Invoice', 'Issued', 'Original due', 'Effective due', 'Original value', 'Remaining'], inv)}
    ${table('payments', ['Date', 'Reference', 'Amount', 'Recorded allocation', ASSUMED, 'To opening balance', 'To customer credit'], pay)}
    ${b.records.openingBalances.length ? `<ul class="points">${b.records.openingBalances.map(o => `<li>Opening balance ${ref(o, o.kind === 'credit' ? 'credit' : 'owed')} as of ${esc(o.asOfText)}: ${esc(o.amountText)}${o.counted ? '' : ' (not counted: dated after this date)'}</li>`).join('')}</ul>` : ''}
    <h4>Payment by payment</h4>${b.trail.length ? `<ol class="points" data-list="trail">${b.trail.map(step).join('')}</ol>` : '<p class="hint">No invoice or payment dated up to this date.</p>'}
    <p class="hint">Remaining opening balance: ${esc(b.end.remainingOpeningText)}. Customer credit held: ${esc(b.end.creditHeldText)}.</p>
    <h4>${esc(b.exposure.label)}</h4>${dl(b.exposure.rows)}
    <h4>${esc(b.history.label)}</h4>${dl(b.history.rows)}
    <h4>Missing information and assumptions</h4><ul class="points">${b.missing.map(m => `<li>${named(m)} (${esc(m.why)}, ${esc(m.amountText)}): ${esc(m.effect)}</li>`).join('')}${b.assumptions.map(x => `<li>${esc(x.text)}</li>`).join('')}${b.excluded.map(x => `<li>Left out: ${named(x)}${x.count ? ' (' + x.count + ')' : ''}. ${esc(x.effect)}</li>`).join('')}</ul>
    <h4>Policy checks</h4>${table('checks', ['Check', 'Actual', 'Threshold', 'Result'], b.checks.map(x => `<tr><th scope="row">${esc(x.name)}</th><td>${esc(x.actualText)}</td><td>${esc(x.thresholdText)}</td><td data-result="${esc(x.result)}">${esc(CALC_RESULT[x.result] || x.result)}</td></tr>`))}
    <p><b>${esc(CALC_OUTCOME[b.recommendation.outcome] || b.recommendation.outcome)}</b>${b.recommendation.reasons.length ? ' · ' + esc(b.recommendation.reasons.join(' ')) : ''}</p></div></details>`;
}

function evidenceHtml(c) {
  const a = c.analysis;
  if (!a) return '<p class="hint">The agent hasn\'t read this case yet.</p>';
  const b = a.brief;
  const x = a.extraction || {};
  const row = (k, v) => `<tr><th scope="row">${k}</th><td colspan="2">${v}</td></tr>`;
  let html = '';
  if (['brief-v2', 'brief-v3'].includes(b?.format)) {
    html += `<div class="table-wrap"><table class="sources"><caption>Facts and where each comes from</caption>
      <thead><tr><th scope="col">Fact</th><th scope="col">Value</th><th scope="col">Source</th></tr></thead><tbody>
      ${b.facts.map(f => `<tr><th scope="row">${esc(f.label)}</th><td class="val">${esc(f.display)}</td><td>${sourceText(f)}</td></tr>`).join('')}</tbody></table></div>`;
  } else if (b?.format === 'brief-v1-legacy') {
    html += `<p class="hint">Earlier-version notes, written by the model and not checked for meaning:</p><ul class="points">${(b.keyPoints || []).map(p => `<li>${esc(p.text)}</li>`).join('')}</ul>`;
    if (b.historicalSuggestion) html += `<p class="hint">The earlier version also suggested "${esc(b.historicalSuggestion.outcome)}". That suggestion was never validated and isn't used.</p>`;
  }
  const reader = a.aiStatus === 'live' ? 'the agent' : a.aiStatus === 'mocked' ? 'the test agent' : 'the basic parser';
  html += `<div class="table-wrap"><table class="sources"><caption>${a.aiStatus === 'not_used' ? 'What the confirmed action fixed' : `How ${reader} read the message`}</caption><tbody>
    ${row('Invoice', esc(x.invoiceReference || 'Not stated'))}
    ${row('Customer named', esc(x.customerQuery || 'Not stated'))}
    ${row('Date asked for', x.requestedDueDate ? `${esc(dateText(x.requestedDueDate))} from "${esc(x.requestedDateText)}"` : 'Not settled' + (x.requestedDateText ? ` ("${esc(x.requestedDateText)}")` : ''))}
    ${row('Reason', x.reasonQuote ? `"${esc(x.reasonQuote)}"` : x.reason ? esc(x.reason) + ' <span class="tag">Model summary</span>' : 'None given')}
    ${(x.ambiguities || []).length ? row('Unclear', x.ambiguities.map(esc).join('<br>')) : ''}
    ${(x.checks || []).length ? row('App checks', x.checks.map(esc).join('<br>')) : ''}</tbody></table></div>`;
  return html + calcHtml(c);
}

// What a staff answer said, in words: the customer and invoice chosen, a date, or an invoice number (QA B5: not an internal id).
function answerText(d) {
  const choices = (d.task?.missingFields || []).flatMap(m => m.choices || []);
  return Object.entries(d.answers || {}).map(([k, v]) => {
    if (k === 'requestedDueDate') return 'the payment date ' + dateText(v);
    if (k === 'invoiceId') { const ch = choices.find(x => x.invoiceId === v); return ch ? `${ch.customerName} (customer ${ch.customerCode}), invoice ${ch.reference}` : 'one customer\'s invoice'; }
    if (k === 'invoiceReference') return 'invoice number ' + v;
    return v;
  }).join('; ');
}

const WHO = { staff: 'Staff', owner: 'The owner' };

function activityHtml(c) {
  const lines = [];
  const add = (at, text, cls = '') => lines.push(`<li class="${cls}">${stamp(at)}<span>${text}</span></li>`);
  for (const e of c.history) {
    const d = e.data;
    if (e.kind === 'request.received') add(e.at, 'Staff sent the customer\'s message to the agent.');
    else if (e.kind === 'analysis.queued' && d.description) add(e.at, `Records changed: ${esc(d.description)}. The case is prepared again.`);
    else if (e.kind === 'analysis.queued' && /^reanalysis requested/.test(d.cause || '')) add(e.at, `${/owner/.test(d.cause) ? 'The owner' : 'Staff'} asked for the case to be prepared again.`);
    else if (e.kind === 'analysis.started') add(e.at, d.mode === 'live' ? 'The agent started preparing the case.' : d.mode === 'mock' ? 'The test agent started.' : 'Preparation started with AI switched off.');
    else if (e.kind === 'analysis.finished') add(e.at, d.route === 'needs_information' ? 'The agent asked staff for ' + esc((d.missingFields || []).map(m => FIELD_WORDS[m.field] || m.field).join(' and ')) + '.' : 'The case was ready for the owner.');
    else if (e.kind === 'analysis.failed') add(e.at, 'The model failed (' + esc(d.failure?.kind) + '), so the app prepared the case without AI.', 'blocked');
    else if (e.kind === 'preparation.failed') add(e.at, 'Preparation failed (' + esc(d.kind || d.failure?.kind || 'error') + '). It waits for someone to prepare it again.', 'blocked');
    else if (e.kind === 'analysis.discarded') add(e.at, 'An earlier preparation was set aside because the case changed.');
    else if (e.kind === 'clarification.answered') add(e.at, `${esc(actorWho(d, d.origin === 'owner_confirmed' ? 'The owner' : 'Staff'))} answered: ${esc(answerText(d))}.`);
    else if (e.kind === 'decision.committed' && d.decisionSource === 'delegated_policy') add(e.at, `${d.outcome === 'decline' ? 'Declined' : 'Approved ' + esc(dateText(d.approvedDueDate))} by the agent under Owner policy version ${esc(d.authority?.policyVersion)}, giving the reason "${esc(d.reason)}".`);
    else if (e.kind === 'decision.overridden') add(e.at, d.decision?.outcome === 'approve' ? `The owner reversed the agent's decline and approved ${esc(dateText(d.decision.approvedDueDate))}, giving the reason "${esc(d.decision?.reason)}".` : `The owner overrode the earlier approval and declined, giving the reason "${esc(d.decision?.reason)}".`);
    else if (e.kind === 'decision.committed') add(e.at, (/^Not/.test(deciderText(d)) ? 'It was ' : esc(deciderText(d)) + (d.decisionSource === 'staff_within_authority' ? ', ' : ' ')) + (d.outcome === 'approve' ? 'approved ' + esc(dateText(d.approvedDueDate)) : 'declined') + (d.reason ? `, giving the reason "${esc(d.reason)}".` : '.'));
    else if (e.kind === 'concern.raised') add(e.at, `${esc(actorWho(d, 'Staff'))} ${d.kind === 'reply' ? 'replied to the owner' : 'raised a concern'}: “${esc(d.quote)}”.`);
    else if (e.kind === 'concern.answered') add(e.at, d.answers ? `${esc(actorWho(d, 'The owner'))} answered the concern: “${esc(d.text)}”.` : `${esc(actorWho(d, 'The owner'))} ${d.responseKind === 'needs_info' ? 'asked staff on the case' : 'gave guidance on the case'}: “${esc(d.text)}”.`);
    else if (e.kind === 'request.withdrawn') add(e.at, `${esc(actorWho(d, d.role === 'owner' ? 'The owner' : 'Staff'))} withdrew the request${d.reason ? `, giving the reason "${esc(d.reason)}"` : ''}.`);
    else if (e.kind === 'request.completed') add(e.at, 'Reply drafted. Not sent.');
    else if (e.kind === 'evidence.changed_after_decision') add(e.at, `Records changed after the decision${d.description ? ': ' + esc(d.description) : ''}.${d.outstandingBefore && d.outstandingNow && d.outstandingBefore !== d.outstandingNow ? ` Amount still owed was ${esc(d.outstandingBefore)}; now ${esc(d.outstandingNow)}.` : ''} The decision stands.`, 'changed');
  }
  return `<p class="hint">Times are when each step was recorded, on the real clock.</p><ol class="log">${lines.join('')}</ol>
    ${['needs_information', 'awaiting_owner'].includes(c.status) ? `<p class="hint">If the records have changed, ask the agent to prepare this case again. <button type="button" class="btn link" data-prepare-again>Prepare again</button></p>` : ''}`;
}

const CALLER = { live_model: 'agent', mock_adapter: 'test agent', manual_fallback: 'app (no AI)', application_code: 'app', application_template: 'app' };

function technicalHtml(c) {
  const a = c.analysis;
  const m = a?.model;
  const tools = c.history.filter(e => ['tool.executed', 'tool.rejected', 'suggestion.suppressed', 'model.call'].includes(e.kind));
  const runs = [...(c.runs || [])].sort((p, q) => String(p.startedAt || p.queuedAt).localeCompare(String(q.startedAt || q.queuedAt)));
  return `${m ? `<p>${esc(m.label)}, model ${esc(a.modelId || m.modelId || '')}${m.serving ? `, loaded as ${esc(m.serving.arch || '')} ${esc(m.serving.quantization || '')}` : ''}. Prompt ${esc(a.promptVersion || 'none')}.</p>` : ''}
    <h3>Runs</h3><ol class="log">${runs.map(run => `<li><time datetime="${esc(run.queuedAt)}">${esc(clockText(run.startedAt || run.queuedAt))}</time><span>Run ${esc(run.id.slice(-6))}: ${esc(run.mode)}, ${esc(run.status)}${run.stats ? `, ${run.stats.modelCalls} model calls, ${run.stats.toolCalls} tool calls, ${(run.stats.elapsedMs / 1000).toFixed(1)} s` : ''}${run.failure ? ', ' + esc(run.failure.kind) : ''}</span></li>`).join('')}</ol>
    <h3>Steps</h3><ol class="log">${tools.map(e => `<li class="${e.kind === 'tool.rejected' ? 'blocked' : ''}"><time datetime="${esc(e.at)}">${esc(clockText(e.at))}</time><span>${e.kind === 'model.call' ? `Model call ${esc(e.data.task)}${e.data.error ? ' failed: ' + esc(e.data.error) : ', ' + ((e.data.latencyMs || 0) / 1000).toFixed(1) + ' s'}`
      : e.kind === 'suggestion.suppressed' ? 'Removed a recommendation the model offered (recommendations are off)'
      : [esc(e.data.tool), e.kind === 'tool.rejected' ? 'blocked: ' + esc(e.data.result?.error) : e.data.ok === false ? 'returned ' + esc(e.data.result?.error) : '', 'by the ' + esc(CALLER[e.data.caller] || e.data.caller)].filter(Boolean).join(', ')}</span></li>`).join('')}</ol>
    <details><summary>Raw event log</summary><pre class="raw">${esc(JSON.stringify(c.history, null, 2))}</pre></details>`;
}
