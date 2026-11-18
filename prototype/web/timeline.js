'use strict';
// The case timeline: #/decision-cases/<caseId>, for the Owner and Staff. One decision case from request to outcome, as the backend recorded it:
//   the loop's six stages (request, evidence, evaluation, decision, Owner feedback, outcome) with the ones reached marked;
//   the three dimensions of the frozen evaluation (evidence, business risk, demonstrated reliability), the decision and the authority it was made under;
//   the Owner's feedback and override (the Owner only: a Staff session is never given them, and this page does not read them for Staff);
//   the outcome: what was observed (the latest stored observation, with when) and, apart, what the current ledger says;
//   and the events in order (GET /api/decision-cases/<id>/events): kind, time, who, the policy version, and a short line of what it recorded.
// Nothing here is worked out by the page: it words what the backend returned. Uses core.js helpers (api, pageHead, esc, stamp, dateText, loading, live) and delegation.js (caseLine, feedbackText, gateWords).

const STAGES = [['request', 'Request'], ['evidence', 'Evidence'], ['evaluation', 'Evaluation'], ['decision', 'Decision'], ['feedback', 'Owner feedback'], ['outcome', 'Outcome']];
const EVENT_STAGE = { created: 'request', evidence_requested: 'evidence', evidence_submitted: 'evidence', evaluated: 'evaluation', escalated: 'evaluation', held: 'evaluation', decided: 'decision', closed: 'decision',
  feedback: 'feedback', override: 'feedback', tacit_agree: 'feedback', viewed: 'feedback', outcome_observed: 'outcome' };
const EVENT_LABEL = { created: 'Request received', evaluated: 'Evaluated', evidence_requested: 'Information asked of Staff', evidence_submitted: 'Information given by Staff', escalated: 'Sent to the Owner', held: 'Held by policy',
  decided: 'Decided', feedback: 'Owner feedback', override: 'Owner override', closed: 'Closed', outcome_observed: 'Outcome observed', tacit_agree: 'Treated as agreed', viewed: 'Opened by the Owner' };
const TL_HANDLING = { autonomous_approve: 'within the Owner\'s policy', autonomous_decline: 'declined by the agent under the Owner\'s decline rules', request_evidence: 'needs more information', owner_review: 'goes to the Owner', policy_hold: 'held by policy' };
const OUTCOME_WORDS = { on_time: 'Paid on time', late_paid: 'Paid late', partial: 'Partly paid', open_not_due: 'Open, not yet due', open_past_due: 'Open and past due', written_off: 'Written off', unknown: 'Unknown',
  repaid: 'Repaid' };
const ACTOR_WORDS = { agent: 'the agent', owner: 'the Owner', staff: 'Staff', system: 'Nucleon' };
const outcomeWord = k => OUTCOME_WORDS[k] || String(k || '').replace(/_/g, ' ');

// A short line for what an event recorded. The Owner's reasons are shown only to the Owner (the backend does not send them to Staff, and this page asks for none).
function eventLine(e, owner) {
  const d = e.data || {}, reason = owner && d.reason ? ` Reason: ${d.reason}` : '';
  switch (e.kind) {
    case 'created': return `${String(d.kind || '').replace(/_/g, ' ')} request${d.recommendation ? '; the assistant recommended ' + d.recommendation.replace(/_/g, ' ') : ''}.`;
    case 'evaluated': return d.handling ? `Handling: ${TL_HANDLING[d.handling] || d.handling.replace(/_/g, ' ')}.${d.why ? ' ' + d.why : ''}` : 'Evaluated against the policy.';
    case 'evidence_requested': return `Asked for ${(d.needs || []).map(n => String(n).replace(/_/g, ' ')).join(', ') || 'information'}.`;
    case 'evidence_submitted': return `Staff confirmed ${(d.kinds || []).map(n => String(n).replace(/_/g, ' ')).join(', ') || 'information'}.`;
    case 'escalated': case 'held': return ownerWords(d.why || d.reason || (e.kind === 'held' ? 'The policy holds this customer.' : 'Outside what the Owner delegated.'));
    case 'decided': return `${d.outcome === 'approve' ? 'Approved' : 'Declined'} by ${d.by === 'agent' ? 'the agent' : d.by === 'owner_exception' ? 'the Owner, as an exception' : 'the Owner'}.${reason}`;
    case 'feedback': return `${d.override ? 'Overridden' : d.verdict === 'agree' ? 'Agreed' : 'Disagreed'}.${reason}`;
    case 'override': return d.outcome === 'approve' ? `The agent's decline was reversed: approved the date asked for.${reason}` : `The approval was replaced: ${d.outcome === 'revoked' ? 'the credit line was revoked' : 'declined'}.${reason}`;
    case 'tacit_agree': return `Treated as agreed${d.afterDays ? ' after ' + days(Number(d.afterDays)) : ''} (no Owner objection).`;
    case 'outcome_observed': return `${outcomeWord(d.outcome)}${d.asOf ? ', as of ' + dateText(d.asOf) : ''}.`;
    case 'viewed': return ownerWords('The Owner opened this case.');
    case 'closed': return d.note || 'The case is closed.';
    default: return '';
  }
}

function stageStrip(c, events, owner) {
  const reached = new Set(events.map(e => EVENT_STAGE[e.kind]).filter(Boolean));
  if (c.status === 'gathering_evidence') reached.add('evidence');
  const current = !events.length ? null : c.status === 'decided' ? (c.outcomeObserved ? 'outcome' : reached.has('feedback') ? 'feedback' : 'decision') : c.status === 'gathering_evidence' ? 'evidence' : c.status === 'closed' ? 'decision' : 'evaluation';
  return `<ol class="tl-stages" data-testid="stages" aria-label="Where this case is in the loop">${STAGES.map(([key, label]) => {
    const hidden = key === 'feedback' && !owner;   // Staff are not shown the Owner's feedback, so this stage is not theirs to read
    const state = hidden ? 'private' : key === current ? 'current' : reached.has(key) ? 'done' : 'todo';
    return `<li class="tl-stage ${state}" data-stage="${key}" data-state="${state}"${state === 'current' ? ' aria-current="step"' : ''}><span class="tl-stage-name">${esc(label)}</span><span class="tl-stage-state">${
      state === 'private' ? 'Owner only' : state === 'current' ? 'now' : state === 'done' ? 'reached' : 'not yet'}</span></li>`;
  }).join('')}</ol>`;
}

function dimensionsHtml(c) {
  const ev = c.evidence || {}, rk = c.risk || {}, rel = c.reliability || {};
  const list = (items, text) => (items || []).length ? `<ul class="dg-reasons">${items.map(i => `<li>${esc(text(i))}</li>`).join('')}</ul>` : '';
  return `<div class="tl-dims" data-testid="dimensions">
    <div class="facts-card" data-testid="dim-evidence"><h3>Evidence</h3><p><span class="chip ${ev.status === 'sufficient' ? 'done' : 'need'}">${esc(String(ev.status || 'not recorded').replace(/_/g, ' '))}</span></p>
      ${list(ev.items, i => `${i.label}: ${i.status}. ${i.detail || ''}`)}${(ev.items || []).filter(i => i.background?.lookupUrl).map(i => `<p class="hint" data-testid="abn-lookup"><a href="${esc(i.background.lookupUrl)}" target="_blank" rel="noopener noreferrer">Look up ABN ${esc(i.background.abn)} in the Australian Business Register</a> (opens abr.business.gov.au).</p>`).join('')}${list(ev.missing, i => `Missing: ${i.label || i.key || i}`)}${list(ev.contradictions, i => `Contradiction: ${i.label || i.detail || i}`)}</div>
    <div class="facts-card" data-testid="dim-risk"><h3>Business risk</h3><p><span class="chip ${rk.status === 'within' ? 'done' : 'fail'}">${esc(String(rk.status || 'not recorded').replace(/_/g, ' '))}</span></p>
      ${list(rk.checks, i => i.sentence || `${i.label}: ${i.status}`)}</div>
    <div class="facts-card" data-testid="dim-reliability"><h3>Demonstrated reliability</h3><p><span class="chip ${rel.status === 'established' ? 'done' : rel.status === 'not_required' ? 'wait' : 'need'}">${esc(String(rel.status || 'not recorded').replace(/_/g, ' '))}</span></p>
      <p class="hint" data-testid="dim-reliability-sources">${esc(gateWords(rel))}</p>${rel.sentence ? `<p class="hint">${esc(rel.sentence)}</p>` : ''}</div></div>`;
}

function decisionHtml(c, owner) {
  const d = c.decision, a = c.authority || {};
  if (!d) return `<p class="muted" data-testid="decision-none">Not decided yet (${esc(String(c.status).replace(/_/g, ' '))}).</p>`;
  const who = d.by === 'agent' ? `Decided by the agent under Owner policy v${esc(a.version ?? '?')}${a.digest ? ' (digest ' + esc(a.digest) + ')' : ''}` : d.by === 'owner_exception' ? 'Decided by the Owner, as an exception to the policy' : 'Decided by the Owner';
  return `<p data-testid="decision-line"><b>${d.outcome === 'approve' ? 'Approved' : 'Declined'}.</b> ${who} · ${stamp(d.at)}${d.overridden ? ' · <span class="chip fail">Overridden by the Owner</span>' : ''}</p>
    ${d.approvedDueDate ? `<p class="hint">Due date: ${esc(d.approvedDueDateText || d.approvedDueDate)}</p>` : ''}${owner && d.reason ? `<p class="hint" data-testid="decision-reason">Reason: ${esc(d.reason)}</p>` : ''}
    ${c.statusText ? `<p class="hint">${esc(ownerWords(c.statusText))}</p>` : ''}`;
}

function feedbackHtml(c) {   // the Owner only
  const rows = c.feedback || [];
  if (!rows.length) return '<p class="muted" data-testid="feedback-none">No feedback from you yet.</p>';
  return `<ul class="dg-reasons" data-testid="feedback-list">${rows.map(f => `<li data-verdict="${esc(f.verdict)}">${esc(feedbackText(f))} · ${stamp(f.at)}</li>`).join('')}</ul>
    ${c.override ? `<p class="callout warn small" data-testid="override-note"><b>Override:</b> ${esc(c.override.reason || '')} ${esc(c.override.externalEffects || '')}</p>` : ''}`;
}

function outcomeHtml(c) {
  const seen = c.outcomeObserved, now = c.outcomeNow;
  const observable = c.decision && c.decision.outcome === 'approve' && !c.decision.overridden;
  const observed = seen ? `<p data-testid="outcome-observed"><b>Observed:</b> ${esc(outcomeWord(seen.outcome))}, as of ${esc(dateText(seen.asOf))} (recorded ${stamp(seen.observedAt)}; policy v${esc(seen.policyVersion ?? '?')})${seen.basis ? `<span class="hint"> ${esc(typeof seen.basis === 'string' ? seen.basis : '')}</span>` : ''}</p>`
    : `<p data-testid="outcome-pending"><b>Observed:</b> ${!c.decision ? 'Not decided yet.' : observable ? 'pending: no outcome has been observed yet.' : 'not observed: a declined or overridden decision has no outcome to watch.'}</p>`;
  const current = now ? `<p class="hint" data-testid="outcome-now"><b>Current ledger says:</b> ${esc(now.text || outcomeWord(now.label))} <span class="chip wait">read now, not stored</span></p>` : '';
  return observed + current;
}

function eventsHtml(c, events, owner) {
  const pending = c.decision && c.decision.outcome === 'approve' && !c.decision.overridden && !c.outcomeObserved && !events.some(e => e.kind === 'outcome_observed');
  return `<ol class="tl" data-testid="events">${events.map(e => `<li class="tl-event" data-testid="tl-event" data-kind="${esc(e.kind)}" data-stage="${esc(EVENT_STAGE[e.kind] || '')}">
      <span class="tl-dot" aria-hidden="true"></span><div class="tl-card"><p class="tl-title"><b>${esc(EVENT_LABEL[e.kind] || e.kind)}</b> <span class="chip wait">${esc((STAGES.find(s => s[0] === EVENT_STAGE[e.kind]) || [0, ''])[1])}</span></p>
        <p class="hint">${stamp(e.at)} · by ${esc(ACTOR_WORDS[e.actor] || e.actor || 'Nucleon')}${e.policyVersion !== null && e.policyVersion !== undefined ? ' · policy v' + esc(e.policyVersion) : ''}</p>
        <p>${esc(eventLine(e, owner))}</p></div></li>`).join('')}
    ${pending ? '<li class="tl-event tl-pending" data-testid="tl-outcome-pending"><span class="tl-dot" aria-hidden="true"></span><div class="tl-card"><p class="tl-title"><b>Outcome</b> <span class="chip wait">pending</span></p><p class="hint">Nothing observed yet. The outcome is read from the records when Nucleon observes it.</p></div></li>' : ''}</ol>`;
}

function comparablesHtml(c, owner) {
  const rows = c.comparables || [];
  if (!rows.length) return '<p class="muted">No closely similar reviewed case.</p>';
  return `<ul class="dg-reasons" data-testid="comparables">${rows.map(x => `<li>${esc(x.customerName || 'A customer')}${x.fictional ? ' (fictional example)' : ''}: ${esc(x.ownerDecision === 'approve' ? 'approved' : 'declined')}${x.outcome ? ', ' + esc(outcomeWord(x.outcome)) : ''}. ${esc(x.analogyNote || '')}${owner && x.ownerReason ? ' Your reason: ' + esc(x.ownerReason) : ''}</li>`).join('')}</ul>`;
}

// The one action that is yours on this request (4 Nov 2026): the Owner gets the Decide page's own row (the same buttons, the same code: review.js), Staff get the
// information page when Nucleon is waiting for them. The row is the Decide list's row for this case, read from /api/delegation/cases.
const TL = { c: null, events: [], row: null, notice: null };

function tlActionHtml(c, owner) {
  if (owner) {
    const row = TL.row;
    if (!row || !(rvWaiting(row) || rvAuto(row))) return '';
    RV.cases = [row]; RV.open.add(row.caseId);
    if (RV.seen[row.caseId] === undefined) RV.seen[row.caseId] = row.version;
    return `<section aria-labelledby="tl-act" data-testid="tl-action"><h2 id="tl-act">${rvWaiting(row) ? 'Your decision' : 'Your verdict on the agent\'s decision'}</h2>${rvWaiting(row) ? waitingRow(row) : autoRow(row)}</section>`;
  }
  if (c.addEvidence && !owner) {   // the Owner has it, and Staff know something Nucleon did not ask for (a deposit that arrived since, the registration)
    return `<section aria-labelledby="tl-act" data-testid="tl-action"><h2 id="tl-act">Know something Nucleon did not ask for?</h2>
      <p>This request waits for the Owner. If you can confirm any of these: ${esc(c.addEvidence.kinds.map(k => k.toLowerCase()).join(', '))} (for example a deposit that arrived after the request), add it here. The request is assessed again with it, and the Owner sees the change.</p>
      <p><button type="button" class="btn" id="tl-add-evidence" data-testid="tl-add-evidence">Add information</button></p></section>`;
  }
  if (c.status !== 'gathering_evidence') return '';
  const needs = (c.needs || []).join(', ');
  return `<section aria-labelledby="tl-act" data-testid="tl-action"><h2 id="tl-act">Your next step</h2>${c.evidenceLink
    ? `<p>Nucleon is waiting for ${esc(needs || 'information')} from you. Nothing is approved until then.</p><p><a class="btn primary" href="${esc(c.evidenceLink)}" data-testid="tl-provide">Provide the information</a></p>`
    : `<div class="callout warn"><p>${esc(c.statusText || 'The information request expired. Ask the assistant for the request again.')}</p></div>`}</section>`;
}

async function tlReload(notice) {
  TL.notice = notice || null;
  const id = TL.c?.caseId;
  if (!id) return;
  refreshCount();   // the navigation count after a decision here
  try {
    const owner = S.role === 'owner';
    const [c, events, rows] = await Promise.all([api('/api/decision-cases/' + encodeURIComponent(id)), api('/api/decision-cases/' + encodeURIComponent(id) + '/events'),
                                                owner ? api('/api/delegation/cases').then(x => x.cases).catch(() => []) : Promise.resolve([])]);
    TL.row = rows.find(x => x.caseId === id) || null;
    renderTimeline(c, events.events);
  } catch (error) { if (error.code === 'SIGNED_OUT') return; toast(error.message, 'bad'); }
}

function renderTimeline(c, events) {
  const main = $('#main'), owner = S.role === 'owner';
  if (!main || S.route?.name !== 'decision-case') return;
  TL.c = c; TL.events = events;
  const back = owner ? { href: '#/review', label: 'Decide' } : { href: '#/cases', label: 'Requests' };
  const notice = TL.notice ? `<div class="callout ${TL.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(TL.notice.text)}</p></div>` : '';
  main.innerHTML = `<div class="timeline-page" data-testid="timeline-page" data-case="${esc(c.caseId)}" data-status="${esc(c.status)}">
    ${pageHead({ back, title: `${c.customer?.name || 'A customer'}: ${c.kind === 'extension' ? 'payment extension' : 'trial credit'}`, lede: esc(ownerWords(c.statusText || '')) })}${notice}
    ${tlActionHtml(c, owner)}
    ${stageStrip(c, events, owner)}
    <section class="facts-card" aria-labelledby="tl-facts"><h2 id="tl-facts">The request</h2><p data-testid="case-facts">${caseLine(c)}</p>
      <p class="hint">Assistant: ${esc(c.recommendation?.text || '')}${c.recommendation?.reasoning ? ' — ' + esc(c.recommendation.reasoning) : ''}</p>
      ${c.requestId ? `<p><a href="#/case/${esc(c.requestId)}" data-testid="open-request">Open the request</a></p>` : ''}</section>
    <section aria-labelledby="tl-dims"><h2 id="tl-dims">What the evaluation found</h2>${dimensionsHtml(c)}
      <details class="sec"><summary>Closest reviewed cases</summary>${comparablesHtml(c, owner)}</details></section>
    <section aria-labelledby="tl-dec"><h2 id="tl-dec">Decision</h2>${decisionHtml(c, owner)}</section>
    ${owner ? `<section aria-labelledby="tl-fb"><h2 id="tl-fb">Your feedback</h2>${feedbackHtml(c)}</section>` : ''}
    <section aria-labelledby="tl-out"><h2 id="tl-out">Outcome</h2>${outcomeHtml(c)}</section>
    <section aria-labelledby="tl-ev"><h2 id="tl-ev">Timeline</h2>${eventsHtml(c, events, owner)}</section></div>`;
  document.title = 'Request · Nucleon';
  if ($('[data-testid=tl-action] .rv-row')) { bindReview(); if (owner && TL.row) markViewed(TL.row.caseId); }
  const add = $('#tl-add-evidence');
  if (add) add.onclick = async () => {
    add.disabled = true;
    try { const out = await api('/api/decision-cases/' + encodeURIComponent(c.caseId) + '/evidence-request', {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); location.hash = out.link; }
    catch (error) { add.disabled = false; tlReload({ kind: 'bad', text: error.message }); }
  };
}

PAGES['decision-case'] = async (r, seq) => {
  $('#main').innerHTML = loading('the case timeline');
  let c, events, rows = [];
  TL.notice = null; TL.row = null;
  try { [c, events, rows] = await Promise.all([api('/api/decision-cases/' + encodeURIComponent(r.id)), api('/api/decision-cases/' + encodeURIComponent(r.id) + '/events'),
                                             S.role === 'owner' ? api('/api/delegation/cases').then(x => x.cases).catch(() => []) : Promise.resolve([])]); }
  catch (error) {
    if (error.code === 'SIGNED_OUT' || !live(seq)) return;
    if (error.status === 404) { $('#main').innerHTML = `<div class="state-msg" data-testid="timeline-missing">${pageHead({ title: 'Case not found' })}<p>There is no such decision case.</p><a class="btn primary" href="#/">Go to the home page</a></div>`; return; }
    throw error;
  }
  if (!live(seq)) return;
  TL.row = rows.find(x => x.caseId === r.id) || null;
  renderTimeline(c, events.events);
};
