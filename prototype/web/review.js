'use strict';
// The Owner's Review page: #/review (Owner only; Staff get "Page not found" from core.js route()). The one place to act on what needs the Owner:
//   (a) Waiting for you: escalated (awaiting_owner) and held (on_hold) cases, each with the one-line why, the key facts, the assistant's recommendation and reasoning, a summary of
//       the closest reviewed cases, and Approve / Decline (an exception, when the case is on hold) with a required reason;
//   (b) Autonomous decisions to review: what the agent decided that the Owner has not answered (a treated-as-agreed one is shown with its label): Agree (one click, the reason
//       optional), Disagree (a reason), Override (a reason, and the words on what an override does not undo, before it is confirmed);
//   (c) Recently reviewed: the last ten.
// Every row links to its case timeline. A row is "viewed" (POST .../viewed: the Owner's intervention time starts) the first time it is opened on this page, not when the list is drawn.
// Everything shown and decided is the backend's: a stale case version is refused (409) and the row is read again; a double click is one write (Idempotency-Key). The page reads
// itself again like the control panel (core.js keepFresh) and keeps the reasons being typed, the open rows and the focus.
// Uses core.js helpers (api, keyFor, keyDone, pageHead, esc, stamp, toast, loading, live, keepFresh, REFRESH, decideStart, decideDone) and delegation.js (caseLine, feedbackText, gateWords, timelineLink).

const RV = { cases: [], open: new Set(), viewed: new Set(), seen: {}, confirming: null, flight: false, notice: null };   // seen: the case version each open row was read at

const rvLast = c => (c.feedback || []).slice(-1)[0];
const rvWaiting = c => ['awaiting_owner', 'on_hold'].includes(c.status);
const rvAuto = c => c.status === 'decided' && c.decision?.by === 'agent' && !c.decision.overridden && (!rvLast(c) || rvLast(c).verdict === 'tacit_agree');
const rvReviewedAt = c => rvLast(c)?.at || c.decision?.at || '';
const rvReviewed = c => c.status === 'decided' && ((c.decision?.by === 'agent' && (c.decision.overridden || (rvLast(c) && rvLast(c).verdict !== 'tacit_agree'))) || ['owner', 'owner_exception'].includes(c.decision?.by));
const rvName = c => c.customer?.name || 'A customer';
const rvOwnApproval = c => c.status === 'decided' && ['owner', 'owner_exception'].includes(c.decision?.by) && c.decision.outcome === 'approve' && !c.decision.overridden;   // the Owner may take it back

// The version a row was read at: the one its buttons send. A row left open while the case changes keeps that version, says so, and is read again on request,
// so a refresh never moves what the Owner is about to confirm to facts they have not seen.
const rvShown = c => (RV.open.has(c.caseId) && RV.seen[c.caseId] !== undefined ? RV.seen[c.caseId] : c.version);
const rvChanged = c => RV.open.has(c.caseId) && RV.seen[c.caseId] !== undefined && RV.seen[c.caseId] !== c.version;
const rvChangedNote = c => (rvChanged(c) ? `<div class="callout warn small" role="alert" data-testid="row-changed"><p>This case changed while it was open. Read it again before you decide.</p>
  <p><button type="button" class="btn small" data-act="reread" data-testid="act-reread">I have read it again</button></p></div>` : '');

function comparablesLine(c) {
  const k = c.comparables;
  if (!k || !k.n) return 'No closely similar reviewed case yet.';
  return `The ${k.n} closest reviewed cases: ${k.approved} you approved, ${k.declined} you declined${k.sameCustomer ? `; ${k.sameCustomer} this customer's own` : ''}. Analogies, not this customer's history.`;
}

// The team's classifier, as a shadow: its figure is shown to the Owner as research and compared with the Owner's decision later; the rules never read it.
function researchLine(s) {
  if (!s.available) return `Research score (${s.model} v${s.version}): not available for this case (missing ${(s.missing || []).join(', ')}).`;
  return `Research score, not used in this decision: the team's model ${s.model} v${s.version} puts the chance you decline at ${Math.round(s.probability * 100)}%.`;
}

// The reason as the Owner reads it on their own page (11 Nov 2026): said to "you", starting with a capital, and a hold says which of its two causes it is.
// The backend's sentence is shared with Staff's status text ("so the Owner decides"), so it is reworded here and not there.
function rvWhy(c) {
  let t = String(c.why || (c.reasons || [])[0] || c.statusText || '');
  if (/on hold by policy/.test(t)) t = (c.evidence?.contradictions || []).length ? 'On hold: what Staff confirmed contradicts the records' : 'On hold: this customer is on your list of customers the agent never decides (Control panel, Advanced)';
  t = t.replace(/what the Owner delegated/g, 'what you delegated').replace(/the Owner set/g, 'you set').replace(/goes to the Owner/g, 'comes to you').replace(/so the Owner decides/g, 'so you decide');
  return t ? t[0].toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? '' : '.') : '';
}
function rvHead(c, chip) {
  const open = RV.open.has(c.caseId);
  return `<div class="rv-head"><div class="rv-title"><b>${esc(rvName(c))}</b> ${chip} <span class="rv-why" data-testid="row-why">${esc(rvWhy(c))}</span>
      ${open ? '' : `<span class="rv-line hint" data-testid="row-line">${caseLine(c)}</span>`}</div>
    <div class="rv-tools"><button type="button" class="btn small" data-open aria-expanded="${open}" aria-controls="rv-body-${esc(c.caseId)}" data-testid="row-open">${open ? 'Close' : 'Open'}</button>
      <a href="#/decision-cases/${esc(c.caseId)}" data-testid="row-timeline">Request page</a></div></div>`;
}

function rvBodyFacts(c) {
  const rec = c.recommendation;
  return `<p data-testid="row-facts">${caseLine(c)}</p>
    ${rec ? `<p class="hint" data-testid="row-recommendation"><b>${esc(rec.text || 'The assistant recommended ' + rec.recommendation)}</b>${rec.reasoning ? ': ' + esc(rec.reasoning) : ''}</p>` : ''}
    <p class="hint" data-testid="row-comparables">${esc(comparablesLine(c))}</p>
    ${c.reliability ? `<p class="hint" data-testid="row-track">${esc(gateWords(c.reliability))}</p>` : ''}
    ${c.research?.shadow ? `<p class="hint" data-testid="row-research">${esc(researchLine(c.research.shadow))}</p>` : ''}
    ${(c.reasons || []).length ? `<ul class="dg-reasons">${c.reasons.slice(0, 4).map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}`;
}

// A counter-offer: approve, but not as asked. An extension with a different due date; a trial credit with shorter terms or a smaller line. Prefilled with what was asked.
function termsBox(c) {
  const k = c.keyFacts || {}, id = esc(c.caseId);
  if (c.kind === 'extension') {
    return `<div class="field rv-terms"><label for="rv-date-${id}">If you approve, the new due date (asked: ${esc(dateText(k.requestedDueDate))})</label>
      <input id="rv-date-${id}" type="date" data-terms="approvedDueDate" value="${esc(k.requestedDueDate || '')}" min="${esc(k.currentDueDate || '')}"></div>`;
  }
  return `<div class="rv-terms-row"><div class="field rv-terms"><label for="rv-days-${id}">If you approve, terms in days (asked: ${esc(k.termsDays)})</label>
      <input id="rv-days-${id}" type="number" min="1" max="${esc(k.termsDays)}" data-terms="termsDays" value="${esc(k.termsDays)}"></div>
    <div class="field rv-terms"><label for="rv-line-${id}">Credit line (asked: ${esc(k.exposure?.text || '')})</label>
      <input id="rv-line-${id}" inputmode="decimal" data-terms="exposure" value="${esc(plainAmount(k.exposure))}"></div></div>`;
}

// What the row's terms inputs say, as the backend takes them; null when nothing differs from what was asked.
function readTerms(row, c) {
  const k = c.keyFacts || {};
  if (c.kind === 'extension') {
    const v = $('[data-terms=approvedDueDate]', row)?.value || k.requestedDueDate;
    return { approvedDueDate: v };
  }
  const days = Number($('[data-terms=termsDays]', row)?.value), line = ($('[data-terms=exposure]', row)?.value || '').trim();
  const terms = {};
  if (Number.isInteger(days) && days !== k.termsDays) terms.termsDays = days;
  if (line && line !== plainAmount(k.exposure)) terms.exposure = line;
  return Object.keys(terms).length ? { terms } : {};
}

// A reason stays required (the reasons are what the business learns from later); common ones are one click, and can be edited before deciding (12 Nov 2026).
const RV_REASONS = {
  decide: ['Reliable customer, I agree', 'Agreed with the customer directly', 'They already owe too much', 'They have paid late too often'],
  feedback: ['The agent was right', 'Too generous for this customer', 'I know something the records do not show'],
};
function reasonBox(c, label, quick) {
  const chips = RV_REASONS[quick] ? `<div class="reason-chips" data-testid="reason-chips">${RV_REASONS[quick].map(t => `<button type="button" data-reason="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : '';
  return `<label for="rv-why-${esc(c.caseId)}">${esc(label)}</label>${chips}<textarea id="rv-why-${esc(c.caseId)}" rows="2" data-why></textarea><p class="error" data-error role="alert"></p>`;
}

function waitingRow(c) {
  const hold = c.status === 'on_hold', open = RV.open.has(c.caseId);
  return `<article class="dg-case rv-row" data-testid="review-row" data-section="waiting" data-case="${esc(c.caseId)}" data-kind="${esc(c.kind)}" data-version="${esc(rvShown(c))}">
    ${rvHead(c, `<span class="chip ${hold ? 'fail' : 'need'}">${hold ? 'On hold by policy' : 'Needs your decision'}</span>`)}
    <div class="rv-body" id="rv-body-${esc(c.caseId)}"${open ? '' : ' hidden'}>${rvChangedNote(c)}${rvBodyFacts(c)}
      ${hold ? '<p class="callout warn small">The policy holds this customer: approving is an exception to it, recorded as such.</p>' : ''}
      ${c.suggested ? `<div class="callout warn small" data-testid="suggested-decline"><p><b>Prepared for you:</b> ${esc(c.suggested.text)}</p><p><button type="button" class="btn small danger" data-suggest-decline data-testid="act-decline-suggested">Decline as suggested</button></p></div>` : ''}
      ${c.exception && c.exception.considered && !c.exception.applied && c.exception.reason ? `<p class="hint" data-testid="exception-note">Exception band: ${esc(c.exception.reason)}.</p>` : ''}
      <div class="dg-decide">${termsBox(c)}${reasonBox(c, 'Your reason (required)', 'decide')}
        <div class="row"><button type="button" class="btn primary" data-act="approve" data-track="review-approve" data-testid="act-approve">${hold ? 'Approve as an exception' : 'Approve'}</button>
          <button type="button" class="btn danger" data-act="decline" data-track="review-decline" data-testid="act-decline">Decline</button>
          ${c.kind === 'extension' && c.requestId ? `<a class="btn quiet" href="#/case/${esc(c.requestId)}" data-testid="open-request">Open the whole request</a>` : ''}</div></div></div></article>`;
}

// A request that came through the form: the facts are on its own page, with the same Approve and Decline buttons.
function formRow(r) {
  const what = r.invoiceReference ? 'Invoice ' + r.invoiceReference + (r.requestedDueDate ? ', asked for ' + dateText(r.requestedDueDate, false) : '') : r.excerpt || '';
  return `<article class="dg-case rv-row rv-form" data-testid="review-form-row" data-section="waiting-form" data-request="${esc(r.id)}">
    <div class="rv-head"><div class="rv-title"><b>${esc(r.customerName || 'Customer not identified yet')}</b> <span class="chip need">Needs your decision</span> <span class="rv-why" data-testid="row-why">Sent through the form${what ? ': ' + esc(what) : ''}</span></div>
      <div class="rv-tools"><a class="btn small primary" href="#/case/${esc(r.id)}" data-testid="row-request">Open and decide</a></div></div></article>`;
}

function autoRow(c) {
  const last = rvLast(c), tacit = last && last.verdict === 'tacit_agree', open = RV.open.has(c.caseId), asking = RV.confirming === c.caseId;
  const declined = c.decision?.outcome === 'decline';   // the agent's own decline under your decline rules (8 Nov 2026)
  const chip = (tacit ? `<span class="chip done" data-testid="tacit-label">${esc(feedbackText(last))}</span>` : '<span class="chip need">Not reviewed yet</span>')
    + (declined ? ' <span class="chip fail" data-testid="agent-declined-label">Declined by the agent</span>' : '')
    + (c.exception?.applied ? ' <span class="chip busy" data-testid="exception-label" title="Approved inside the exception band you delegated">Exception</span>' : '');
  const undo = declined ? 'Override: approve the date asked for' : c.kind === 'extension' ? 'Override: decline and restore the due date' : 'Override: revoke the credit line';
  return `<article class="dg-case rv-row" data-testid="review-row" data-section="auto" data-case="${esc(c.caseId)}" data-kind="${esc(c.kind)}" data-version="${esc(rvShown(c))}"${tacit ? ' data-tacit="true"' : ''}>
    ${rvHead(c, chip)}
    <div class="rv-body" id="rv-body-${esc(c.caseId)}"${open ? '' : ' hidden'}>${rvChangedNote(c)}${rvBodyFacts(c)}
      <p class="hint">Decided by the agent under policy version ${esc(c.policyVersion)} · ${stamp(c.decision.at)}${tacit ? '. Your answer replaces the treated-as-agreed one.' : ''}</p>
      <div class="dg-decide">${reasonBox(c, 'Reason (optional to agree; required to disagree or override)', 'feedback')}
        <div class="row"><button type="button" class="btn small primary" data-act="agree" data-track="review-agree" data-testid="act-agree">Agree</button>
          <button type="button" class="btn small" data-act="disagree" data-track="review-disagree" data-testid="act-disagree">Disagree</button>
          <button type="button" class="btn small danger" data-act="override" data-track="review-override" data-testid="act-override">${esc(undo)}</button></div>
        ${asking ? `<div class="callout warn" data-testid="override-confirm" role="alert"><p><b>Before you override:</b> <span data-testid="override-effects">${esc(c.overrideEffects || '')}</span></p>
          <div class="row"><button type="button" class="btn danger solid" data-act="override-confirm" data-track="review-override-confirm" data-testid="act-override-confirm">Confirm the override</button>
          <button type="button" class="btn" data-act="override-cancel" data-testid="act-override-cancel">Not now</button></div></div>` : ''}</div></div></article>`;
}

function reviewedRow(c) {
  const last = rvLast(c), owner = ['owner', 'owner_exception'].includes(c.decision?.by), asking = RV.confirming === c.caseId;
  const what = owner ? (c.decision.overridden ? 'You withdrew your approval' : `You ${c.decision.outcome === 'approve' ? 'approved' : 'declined'}${c.decision.by === 'owner_exception' ? ' (an exception)' : ''}`)
    : c.decision.overridden ? (c.decision.outcome === 'decline' ? 'You reversed the agent\'s decline' : 'You overrode it') : last.verdict === 'agree' ? 'You agreed' : 'You disagreed';
  // A wrong click is taken back here: the Owner's own approval can be withdrawn like an agent approval is overridden (Tony, 6 Nov 2026).
  const undo = !rvOwnApproval(c) ? '' : `<details class="rv-undo" data-testid="withdraw"${asking ? ' open' : ''}><summary>Approved by mistake? Withdraw it</summary>
      ${reasonBox(c, 'Why you withdraw it (required)')}<div class="row"><button type="button" class="btn small danger" data-act="override" data-track="review-withdraw" data-testid="act-withdraw">${c.kind === 'extension' ? 'Withdraw: decline and restore the due date' : 'Withdraw: revoke the credit line'}</button></div>
      ${asking ? `<div class="callout warn" data-testid="override-confirm" role="alert"><p><b>Before you withdraw it:</b> <span data-testid="override-effects">${esc(c.overrideEffects || '')}</span></p>
        <div class="row"><button type="button" class="btn danger solid" data-act="override-confirm" data-track="review-withdraw-confirm" data-testid="act-override-confirm">Confirm</button>
        <button type="button" class="btn" data-act="override-cancel" data-testid="act-override-cancel">Not now</button></div></div>` : ''}</details>`;
  return `<li class="dg-case rv-done" data-testid="reviewed-row" data-case="${esc(c.caseId)}" data-version="${esc(c.version)}"><b>${esc(rvName(c))}</b> <span class="chip ${c.decision?.overridden ? 'fail' : 'done'}">${esc(what)}</span>
    <span class="home-note">${caseLine(c)} · ${stamp(rvReviewedAt(c))}</span>${!owner && last?.reason ? `<span class="home-note" data-testid="reviewed-reason">${esc(last.reason)}</span>` : ''}
    <a href="#/decision-cases/${esc(c.caseId)}" data-testid="row-timeline">Request page</a>${undo}</li>`;
}

function renderReview() {
  const main = $('#main');
  if (!main || S.route?.name !== 'review') return;
  RV.cases.forEach(c => { if (RV.open.has(c.caseId) && RV.seen[c.caseId] === undefined) RV.seen[c.caseId] = c.version; });
  const forms = RV.forms || [], wait = RV.cases.filter(rvWaiting), auto = RV.cases.filter(rvAuto).sort((a, b) => (b.decision.at || '').localeCompare(a.decision.at || '')), shown = auto.slice(0, 30);
  const done = RV.cases.filter(rvReviewed).sort((a, b) => rvReviewedAt(b).localeCompare(rvReviewedAt(a))).slice(0, 10);
  const note = RV.notice ? `<div class="callout ${RV.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(RV.notice.text)}</p></div>` : '';
  main.innerHTML = `<div class="review-page" data-testid="review-page">
    ${pageHead({ title: 'Decide', lede: 'Your work list: what needs your decision, whether it came through the assistant or the form, and what the assistant decided on its own for you to agree with, disagree with or override. Every request also has its own page, with the same buttons, under <a href="#/cases">Requests</a>.' })}<p class="hint" data-testid="review-doctor-link">Too many here? Ask the <a href="#/doctor">Doctor</a> why.</p>${note}
    <section aria-labelledby="rv-wait"><h2 id="rv-wait">Waiting for you <span class="count" data-testid="waiting-count"${wait.length + forms.length ? '' : ' hidden'}>${wait.length + forms.length}</span></h2>
      ${wait.length + forms.length ? wait.map(waitingRow).join('') + forms.map(formRow).join('') : '<p class="muted" data-testid="waiting-none">Nothing is waiting for you.</p>'}</section>
    <section aria-labelledby="rv-auto"><h2 id="rv-auto">Autonomous decisions to review <span class="count" data-testid="auto-count"${auto.length ? '' : ' hidden'}>${auto.length}</span></h2>
      <p class="hint">Agree takes one click. A decision you leave alone stays here; if you set a number of days on the <a href="#/delegation">control panel</a>, it is recorded as treated as agreed after that time and still listed, labelled.</p>
      ${shown.length ? shown.map(autoRow).join('') + (auto.length > shown.length ? `<p class="hint">Showing the newest ${shown.length} of ${auto.length}.</p>` : '') : '<p class="muted" data-testid="auto-none">Nothing to review: every autonomous decision has your answer.</p>'}</section>
    <section aria-labelledby="rv-done"><h2 id="rv-done">Recently reviewed</h2>
      ${done.length ? `<ul class="home-list rv-done-list">${done.map(reviewedRow).join('')}</ul>` : '<p class="muted" data-testid="reviewed-none">Nothing reviewed yet.</p>'}</section></div>`;
  document.title = 'Decide · Nucleon';
  bindReview();
}

function bindReview() {
  $$('.rv-row').forEach(row => {
    const id = row.dataset.case, body = $('.rv-body', row), toggle = $('[data-open]', row);
    if (!toggle) return;   // a form request's row has no body to open: its page has the facts
    toggle.onclick = () => {
      const open = body.hidden;   // hidden now: this opens it
      body.hidden = !open; toggle.setAttribute('aria-expanded', String(open)); toggle.textContent = open ? 'Close' : 'Open';
      if (open) { RV.open.add(id); RV.seen[id] = RV.cases.find(x => x.caseId === id)?.version; markViewed(id); } else { RV.open.delete(id); delete RV.seen[id]; }
    };
    $$('[data-why]', row).forEach(t => { t.onfocus = () => decideStart(id); });
    $$('[data-reason]', row).forEach(b => { b.onclick = () => { const why = $('[data-why]', b.closest('.dg-decide') || row); if (why) { why.value = b.dataset.reason; why.focus(); } }; });
    $$('[data-act]', row).forEach(b => { b.onclick = () => reviewAct(b); });
    $$('[data-suggest-decline]', row).forEach(b => { b.onclick = () => {   // one click: the prepared reason goes into the box and the ordinary decline runs
      const c = RV.cases.find(x => x.caseId === id), why = $('[data-why]', row), decline = $('[data-act=decline]', row);
      if (c?.suggested && why && decline) { why.value = c.suggested.reason; reviewAct(decline); }
    }; });
  });
}

// The Owner opened a row: the intervention time of this case starts (once per case per visit to the page; the server writes at most one `viewed` a minute anyway).
function markViewed(id) {
  if (RV.viewed.has(id)) return;
  RV.viewed.add(id);
  api(`/api/decision-cases/${encodeURIComponent(id)}/viewed`, {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }).catch(() => RV.viewed.delete(id));
}

// An extension is decided through its request (POST /api/requests/<id>/decisions, as the request page does): read the case and the request now, refuse if the case is no longer
// the one the Owner was shown, then send the request's own version, analysis and evidence version with the date the customer asked for (approve) or none (decline).
async function decideExtension(c, outcome, reason, shown, approvedDueDate) {
  const fresh = await api('/api/decision-cases/' + encodeURIComponent(c.caseId));
  if (fresh.version !== shown) throw Object.assign(new Error('The case changed since you loaded it. Reload it before deciding.'), { code: 'STALE_CASE' });
  const r = await api('/api/requests/' + encodeURIComponent(c.requestId));
  const f = r.analysis?.snapshot?.facts;
  if (r.status !== 'awaiting_owner' || !f || !r.analysis.snapshot.evidenceVersion) throw Object.assign(new Error('The assistant is still preparing this request. Try again in a moment, or open the whole request.'), { code: 'NOT_READY' });
  const body = { expectedRequestVersion: r.version, analysisId: r.analysis.id, evidenceVersion: r.analysis.snapshot.evidenceVersion, outcome, approvedDueDate: outcome === 'approve' ? (approvedDueDate || f.requestedDueDate) : null, reason };
  const key = 'rv-ext:' + c.caseId + ':' + JSON.stringify(body);
  const out = await api(`/api/requests/${encodeURIComponent(c.requestId)}/decisions`, body, { key: keyFor(key) });
  keyDone(key);
  return out;
}

async function reviewAct(button) {
  const row = button.closest('[data-case]'), id = row.dataset.case, act = button.dataset.act, slot = $('[data-error]', row), why = $('[data-why]', row);
  const c = RV.cases.find(x => x.caseId === id);
  if (!c || RV.flight) return;
  slot.textContent = '';
  if (act === 'override-cancel') { RV.confirming = null; return rerender(); }
  if (act === 'reread') { RV.seen[id] = c.version; return rerender(); }
  const reason = why.value.trim();
  if (act !== 'agree' && !reason) { slot.textContent = 'Enter a brief reason.'; why.focus(); return; }
  decideStart(id);
  if (act === 'override') { RV.confirming = id; RV.open.add(id); rerender(); $('[data-act=override-confirm]', $(`[data-case="${CSS.escape(id)}"]`))?.focus(); return; }
  RV.flight = true;
  $$('[data-act]', row).forEach(b => { b.disabled = true; });
  const version = Number(row.dataset.version), waiting = rvWaiting(c), name = act === 'override-confirm' ? 'override' : act;
  let keyId = null, text;
  try {
    if (waiting && c.kind === 'extension') {
      const t = readTerms(row, c);
      await decideExtension(c, act, reason, version, t.approvedDueDate);
      text = act === 'approve' ? (t.approvedDueDate !== c.keyFacts?.requestedDueDate ? 'Approved, with a different due date.' : 'Approved.') : 'Declined.';
    } else if (waiting) {
      const sent = { outcome: act, reason, version, ...(act === 'approve' ? readTerms(row, c) : {}) };
      keyId = 'rv-decide:' + id + ':' + JSON.stringify(sent);
      await api(`/api/decision-cases/${encodeURIComponent(id)}/decide`, sent, { key: keyFor(keyId), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
      text = act === 'approve' ? (c.status === 'on_hold' ? 'Approved as an exception.' : 'Approved.') : 'Declined.';
    } else {
      const sent = act === 'override-confirm' ? { verdict: 'disagree', override: true, reason, version } : { verdict: act, reason: reason || 'Agreed (no reason given).', version };
      keyId = 'rv-feedback:' + id + ':' + JSON.stringify(sent);
      const out = await api(`/api/decision-cases/${encodeURIComponent(id)}/feedback`, sent, { key: keyFor(keyId), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
      text = act === 'override-confirm' ? (c.decision?.by === 'agent' ? (c.decision.outcome === 'decline' ? 'The agent\'s decline was reversed: the date asked for is approved. ' : 'The agent\'s approval was overridden. ') : 'Your approval was withdrawn. ') + (out.externalEffects || '') : act === 'agree' ? 'Agreement recorded.' : 'Disagreement recorded.';
    }
    if (keyId) keyDone(keyId);
    RV.confirming = null; delete RV.seen[id];
    toast('Recorded', 'ok');
    decideDone(id, name, true);
    RV.flight = false;
    return reviewRefresh({ kind: 'ok', text });
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    RV.flight = false;
    decideDone(id, name, false);
    if (keyId && error.code !== 'NETWORK' && !(error.status >= 500)) keyDone(keyId);   // a retry after a lost answer reuses the key; a refusal does not
    const stale = ['STALE_CASE', 'STALE_VERSION', 'STALE_EVIDENCE'].includes(error.code);
    if (stale || ['ALREADY_DECIDED', 'INVALID_TRANSITION'].includes(error.code)) {
      return reviewRefresh({ kind: 'bad', text: (stale ? 'This case changed while you were reading it, so nothing was recorded. ' : '') + error.message + (stale ? ' The row is up to date below: read it again, then decide.' : ' Nothing was changed.') });
    }
    slot.textContent = error.message;
    $$('[data-act]', row).forEach(b => { b.disabled = false; });
  } finally { RV.flight = false; }
}

function rerender() {
  const kept = reviewCapture();
  renderReview();
  reviewRestore(kept);
}

async function reviewLoad() {
  const [out, reqs] = await Promise.all([api('/api/delegation/cases'), api('/api/requests')]);
  RV.cases = out.cases;
  // A request sent through the form (no assistant, so no decision case of its own) waits here too; it is decided on its own page.
  RV.forms = reqs.filter(r => r.status === 'awaiting_owner' && !RV.cases.some(c => c.requestId === r.id));
  if (RV.confirming && !RV.cases.some(c => c.caseId === RV.confirming && (rvAuto(c) || rvOwnApproval(c)))) RV.confirming = null;
}

async function reviewRefresh(notice) {
  RV.notice = notice || null;
  if (S.route?.name === 'decision-case' && typeof tlReload === 'function') return tlReload(notice);   // the same buttons on a request's own page (timeline.js)
  const kept = reviewCapture();
  try { await reviewLoad(); } catch (error) { if (error.code === 'SIGNED_OUT') return; RV.notice = { kind: 'bad', text: error.message }; }
  refreshCount();   // the navigation count, not only this list
  if (S.route?.name !== 'review') return;
  renderReview();
  reviewRestore(kept);
}

// What the Owner has typed and where they were survives a redraw (a refresh, a decision on another row, a stale-case message).
function reviewCapture() {
  const typed = {};
  $$('[data-why]').forEach(t => { if (t.value) typed[t.id] = t.value; });
  const a = document.activeElement, inPage = a && a.id && $('#main')?.contains(a);
  return { typed, focus: inPage ? { id: a.id, start: a.selectionStart, end: a.selectionEnd } : null, y: scrollY };
}
function reviewRestore(k) {
  $$('[data-why]').forEach(t => { if (k.typed[t.id]) t.value = k.typed[t.id]; });
  const f = k.focus && document.getElementById(k.focus.id);
  if (f) { f.focus({ preventScroll: true }); try { f.setSelectionRange(k.focus.start, k.focus.end); } catch { /* not a text field */ } }
  scrollTo(0, k.y);
}

PAGES.review = async (r, seq) => {
  $('#main').innerHTML = loading('what needs your review');
  Object.assign(RV, { open: new Set(), viewed: new Set(), seen: {}, confirming: null, flight: false, notice: null });
  await reviewLoad();
  if (!live(seq)) return;
  renderReview();
  keepFresh(seq);
};
REFRESH.review = async seq => {
  if (RV.flight || $('dialog[open]')) return;
  const kept = reviewCapture();
  try { await reviewLoad(); } catch (error) { if (error.code === 'SIGNED_OUT' || error.status === 401) throw error; return; }   // a failed read leaves the page as it is
  if (!live(seq) || S.route?.name !== 'review') return;
  renderReview();
  reviewRestore(kept);
};
