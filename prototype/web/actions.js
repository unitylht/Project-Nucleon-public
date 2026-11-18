'use strict';
// The confirmation page of an action the assistant prepared: #/actions/<id>. A person reads exactly what would be submitted and confirms it here,
// in Nucleon; the assistant never reaches this page's buttons (docs/CONTROLLED-AGENT-ACTIONS.md). Every fact, date, warning and state comes from
// GET /api/actions/<id> (the backend's view): nothing is worked out in this file. Confirming submits a request to the OWNER for review; it approves
// nothing, and the page says so. Uses core.js helpers (api, keyFor, busy, openDialog, pageHead, esc, dateText, stamp, timeText).

const ACT = { id: null, action: null, notice: null, replayed: false, uncertain: null, flight: false, result: null };

// What the viewer may do with an action in the state the backend gave. Only a person signed in as staff confirms (the backend refuses everyone
// else: this just does not offer what would be refused); staff and the owner may cancel. The assistant's identity and a service session are neither.
function actionControls(a, session) {
  const person = session.identity?.kind !== 'agent' && session.channel !== 'service';
  const live = a.status === 'proposed';
  return { person, confirm: live && person && session.role === 'staff', cancel: live && person && ['staff', 'owner'].includes(session.role) };
}

// The banner for each state: [callout class, headline, sentence]. The sentence for invalidated / expired is the backend's own outcome message.
function actionBanner(a, role) {
  const said = a.outcome?.message;
  switch (a.status) {
    case 'proposed': return ['warn', 'Awaiting confirmation', role === 'staff' ? 'Nothing has been submitted yet. Check the details below, then submit it for the owner to review.'
      : 'Nothing has been submitted yet. Staff confirm a proposal before it reaches you.'];
    case 'executed': return ['ok', 'Submitted for owner review', 'The request is with the owner, who has not decided it yet.'];
    case 'expired': return ['bad', 'Expired', said || 'It was not confirmed in time, so it cannot be submitted. Ask the assistant to prepare a new proposal.'];
    case 'superseded': return ['bad', 'Replaced by a newer proposal', said || 'A newer proposal for this invoice replaced it, so this one cannot be submitted.'];
    case 'cancelled': return ['bad', 'Cancelled', said || 'A person cancelled it before it was submitted. Nothing was submitted.'];
    case 'invalidated': return ['bad', 'No longer valid, not submitted', (said || 'The records changed after it was prepared.') + ' Ask the assistant to prepare a new proposal.'];
    default: return ['warn', 'Status unavailable', 'This page cannot tell where this action stands. Nothing here shows it was submitted.'];
  }
}

function actionFacts(a) {
  const p = a.params, inv = a.preview?.fromRecords?.invoice || {};
  const amount = inv.amountText ? `${esc(inv.amountText)}${inv.mark && !String(inv.amountText).toLowerCase().includes(String(inv.mark).toLowerCase()) ? ` <span class="muted">(${esc(inv.mark)})</span>` : ''}` : '<span class="muted">Not recorded</span>';
  return `<dl class="facts">
    <div class="fact"><dt>Customer</dt><dd><a href="#/customers/${esc(p.customerId)}" data-testid="customer-link">${esc(p.customerName)}</a></dd></div>
    <div class="fact"><dt>Invoice</dt><dd data-testid="invoice">${esc(p.invoiceReference)}</dd></div>
    <div class="fact"><dt>Still owed (as recorded)</dt><dd>${amount}</dd></div>
    <div class="fact"><dt>Original due date</dt><dd data-testid="from-date">${esc(dateText(p.currentDueDate))}</dd></div>
    <div class="fact"><dt>Proposed due date</dt><dd data-testid="to-date">${esc(dateText(p.requestedDueDate))}</dd></div>
    <div class="fact"><dt>Extension</dt><dd data-testid="days">${esc(days(p.days))}</dd></div>
    <div class="fact"><dt>Prepared</dt><dd>${stamp(a.createdAt)}</dd></div>
    ${a.status === 'executed' ? '' : `<div class="fact"><dt>${a.status === 'proposed' ? 'Expires' : 'Would have expired'}</dt><dd>${stamp(a.expiresAt)}</dd></div>`}
  </dl>`;
}

// The assistant's draft of why the customer asked: read-only. It is part of what is submitted, so to change it the proposal is replaced.
function reasonHtml(a) {
  const reason = a.params.reasonDraft;
  return `<section aria-labelledby="act-reason-title"><h2 id="act-reason-title">Reason</h2>
    ${reason ? `<blockquote class="voice short" data-testid="reason">${esc(reason)}</blockquote>` : '<p data-testid="reason" class="muted">No reason was drafted.</p>'}
    <p class="hint">Drafted by the assistant, and submitted exactly as shown. To change the wording, cancel this proposal and ask the assistant to prepare a new one.</p></section>`;
}

// The records' own completeness / certainty words for this customer, verbatim; anything but an explicit "established" reads as a warning.
function warningsHtml(a) {
  const c = a.preview?.completeness || {};
  const established = c.balanceEstablished === true;
  return `<div class="callout ${established ? 'ok' : 'warn'}" data-testid="completeness"><p><b>${established ? 'Records confirmed complete' : 'Unconfirmed'}</b></p>
    <p>${esc(c.caveatText || 'The records gave no completeness statement for this customer.')}</p></div>`;
}

// After it was submitted: the request's id and where it stands, in this viewer's words (the backend's label).
function submittedHtml(a) {
  const r = a.request;
  if (a.status !== 'executed') return '';
  const id = r?.id || a.requestId;
  const mine = S.role === 'owner' ? 'Submitted by staff for your review.' : 'Submitted for the owner to review.';
  return `<section class="callout ok" data-testid="submitted" aria-labelledby="act-sub-title"><h2 id="act-sub-title">${esc(mine)}</h2>
    <p>Request <b>${esc(id || 'not recorded')}</b>${r?.label ? ` · <span class="chip ${['withdrawn', 'decided', 'completed'].includes(r.status) ? 'done' : 'wait'}" data-testid="request-label">${esc(r.label)}</span>` : ''}</p>
    ${ACT.replayed ? '<p data-testid="replayed"><b>It was already submitted.</b> Nothing was submitted a second time.</p>' : ''}
    <p class="hint">Confirming submitted this request to the owner for review. It did not approve the extension; the owner decides.</p>
    ${id ? `<p><a class="btn" href="#/case/${esc(id)}" data-testid="request-link">${S.role === 'owner' ? 'Open the request to decide' : 'Open the request'}</a></p>` : ''}</section>`;
}

function renderAction() {
  const a = ACT.action, main = $('#main');
  if (!a || !main) return;
  const [tone, headline, sentence] = actionBanner(a, S.role);
  const can = actionControls(a, S.session);
  const owner = S.role === 'owner';
  const note = ACT.notice ? `<div class="callout ${ACT.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(ACT.notice.text)}</p>${ACT.notice.link ? `<p><a href="${esc(ACT.notice.link.href)}">${esc(ACT.notice.link.label)}</a></p>` : ''}</div>` : '';
  const uncertain = ACT.uncertain ? `<div class="callout warn" role="alert" data-testid="uncertain"><p><b>${ACT.uncertain.known ? 'Not submitted yet.' : 'Outcome uncertain.'}</b> ${esc(ACT.uncertain.text)}</p>
      <div class="row"><button type="button" class="btn" id="act-check">Check again</button></div></div>` : '';
  const live = a.status === 'proposed';
  const controls = !live ? '' : `<section class="action-in" aria-labelledby="act-do-title" data-testid="controls"><h2 id="act-do-title">${can.confirm ? 'Submit this request?' : 'This proposal'}</h2>
      <p data-testid="statement"><b>Confirming submits this request to the owner for review. It does not approve the extension.</b></p>
      ${can.confirm ? '' : `<p class="hint">${!can.person ? 'This sign-in belongs to the assistant or a service, so it cannot confirm or cancel a proposal. A person signed in to Nucleon does that.'
        : owner ? 'Staff submit proposals for your review. You can read this one, and cancel it if it should not go ahead.' : ''}</p>`}
      <div class="row">
        ${can.confirm ? `<button type="button" class="btn primary" id="act-confirm" data-testid="confirm">${ACT.uncertain && ACT.uncertain.retry ? 'Try again' : 'Submit for owner review'}</button>` : ''}
        ${can.cancel ? '<button type="button" class="btn" id="act-cancel" data-testid="cancel">Cancel proposal</button>' : ''}
      </div></section>`;
  main.innerHTML = `<div class="action-page" data-testid="action-page" data-action="${esc(a.id)}" data-status="${esc(a.status)}">
    ${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: 'Payment-extension request', lede: `Prepared by the assistant for ${esc(a.params.customerName)}. ${esc(a.status === 'proposed' ? 'Nothing is submitted until a person confirms it here.' : '')}` })}
    <div class="callout ${tone}" data-testid="banner" role="status"><p><b>${esc(headline)}.</b> ${esc(sentence)}</p></div>
    ${note}${uncertain}${submittedHtml(a)}
    <section class="facts-card" aria-labelledby="act-facts-title"><h2 id="act-facts-title">${a.status === 'executed' ? 'What was submitted' : 'What would be submitted'}</h2>${actionFacts(a)}</section>
    ${reasonHtml(a)}${warningsHtml(a)}${controls}
    <p class="hint"><span class="muted">Action</span> ${esc(a.id)}</p>
  </div>`;
  document.title = 'Request proposal · Nucleon';
  const confirm = $('#act-confirm'), cancel = $('#act-cancel'), check = $('#act-check');
  if (confirm) confirm.onclick = () => confirmAction(confirm);
  if (cancel) cancel.onclick = () => cancelDialog(a);
  if (check) check.onclick = () => rereadAction('check');
}

// Confirm: the same key for the same action until an answer comes (a retry after a lost response is the same operation), the page's csrf token,
// and the version of the proposal that was shown. The button is disabled while the call is in flight. A lost response or a server fault is never
// treated as a failure of the action: the action is read again and the page shows what is recorded.
async function confirmAction(button) {
  const a = ACT.action;
  if (ACT.flight || !a || a.status !== 'proposed') return;
  const id = 'confirm-action:' + a.id;
  ACT.flight = true;
  ACT.notice = null;
  if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  try {
    const out = await api(`/api/actions/${encodeURIComponent(a.id)}/confirm`, { version: a.version }, { key: keyFor(id), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    keyDone(id);
    ACT.action = out.action; ACT.replayed = out.replayed === true; ACT.uncertain = null;
    toast(ACT.replayed ? 'It was already submitted' : 'Submitted for owner review', 'ok');
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    if (error.status === 401) { S.session = null; return renderGate(null, 'Your session ended, for example because the app restarted. Sign in again; this proposal is unchanged.'); }
    if (error.code === 'NETWORK' || error.status >= 500) await rereadAction('lost');   // same key kept: Try again is the same operation
    else {
      keyDone(id);
      await refused(error);
    }
  } finally {
    ACT.flight = false;
    if (S.route?.name === 'action') renderAction();
  }
}

// A definite refusal from the backend: say why in its words; the action it settled (expired, invalidated…) comes with the answer, else it is read again.
async function refused(error) {
  const text = error.message;
  if (error.code === 'CSRF_REQUIRED') {   // this page's token is out of date (a new sign-in elsewhere): fetch the session again
    try { S.session = await api('/api/session'); } catch { /* shown below */ }
    ACT.notice = { kind: 'bad', text: 'The page\'s security token was out of date and has been refreshed. Nothing was submitted. Try again.' };
    return;
  }
  if (error.data?.action) ACT.action = error.data.action;
  else await rereadAction('refused', true);
  ACT.uncertain = null;
  ACT.notice = { kind: 'bad', text, ...(error.data?.requestId ? { link: { href: '#/case/' + error.data.requestId, label: 'Open the request that is already open on this invoice' } } : {}) };
}

// Read the action again and show what is recorded. why: 'lost' (a confirm whose answer did not arrive: the persisted state decides), 'check', 'refused'.
async function rereadAction(why, quiet) {
  const id = ACT.action.id;
  try {
    const fresh = await api('/api/actions/' + encodeURIComponent(id));
    ACT.action = fresh;
    if (fresh.status === 'executed') {
      keyDone('confirm-action:' + id);
      ACT.uncertain = null; ACT.replayed = false;
      if (why === 'lost') ACT.notice = { kind: 'ok', text: 'The connection dropped, but it did go through: this request is submitted. Nothing was submitted twice.' };
    } else if (fresh.status === 'proposed') {
      ACT.uncertain = why === 'refused' || quiet ? null : { retry: why === 'lost', known: true, text: why === 'lost'
        ? 'The answer did not arrive. The records show it has not been submitted. You can try again: it is the same submission, so it cannot be submitted twice.'
        : 'The records show it has not been submitted.' };
    } else ACT.uncertain = null;   // expired, cancelled, superseded, invalidated: the banner says which
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    if (error.status === 401) { S.session = null; return renderGate(null, 'Your session ended. Sign in again; this proposal is unchanged.'); }
    ACT.uncertain = { retry: false, text: 'The page could not reach Nucleon to check, so it cannot tell whether this was submitted. Check again in a moment; do not ask the assistant to prepare it again until you know.' };
  }
  if (why === 'check' && S.route?.name === 'action') renderAction();
}

function cancelDialog(a) {
  openDialog({
    title: 'Cancel this proposal?', intro: 'Nothing has been submitted. The assistant can prepare a new proposal if you still want one.', body: '',
    submitLabel: 'Cancel proposal', cancelLabel: 'Keep it', danger: true,
    submit: async form => {
      const id = 'cancel-action:' + a.id;
      try {
        const out = await api(`/api/actions/${encodeURIComponent(a.id)}/cancel`, {}, { key: keyFor(id), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
        keyDone(id);
        ACT.action = out.action; ACT.notice = null; ACT.uncertain = null;
        toast('Proposal cancelled', 'ok');
        renderAction();
        return true;
      } catch (error) {
        if (error.code === 'SIGNED_OUT') return true;
        if (error.code !== 'NETWORK' && !(error.status >= 500)) keyDone(id);
        if (error.code === 'CSRF_REQUIRED') { try { S.session = await api('/api/session'); } catch { /* ignore */ } }
        showErrors(form, error.code === 'NETWORK' || error.status >= 500 ? { message: error.message + ' Check the proposal\'s state before trying again.' } : error);
        return false;
      }
    },
  });
}

PAGES.action = async (r, seq) => {
  const main = $('#main');
  if (ACT.id !== r.id) Object.assign(ACT, { id: r.id, action: null, notice: null, replayed: false, uncertain: null, flight: false, result: null });
  if (!ACT.action) main.innerHTML = loading('the proposal');
  try {
    const fresh = await api('/api/actions/' + encodeURIComponent(r.id));
    if (!live(seq)) return;
    ACT.action = fresh;
    if (fresh.kind === 'evidence') return renderEvidence();   // an evidence request for a decision case: facts for Staff to confirm
  } catch (error) {
    if (!live(seq)) return;
    if (error.status === 404) {
      main.innerHTML = `<div class="state-msg" data-testid="action-missing">${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: 'Proposal not found' })}
        <p>There is no proposal with this address. The demo data may have been reset, or the link is wrong. Nothing was submitted from it.</p></div>`;
      return;
    }
    throw error;   // route() offers "Try again"
  }
  renderAction();
};


// ---------------------------------------------------------------- the evidence page (Adaptive Decision Authority)
// An evidence action: the assistant asked for facts Staff can confirm, for a credit request that is waiting on them. Staff type what they have seen; Nucleon
// keeps each as a confirmed fact with who confirmed it, and applies the Owner's delegation policy at once. Confirming facts is not approving credit.
// Everything shown (what is asked, the amounts, the case's status sentence and handling) is the backend's; the form only collects what the person typed.

const HANDLING_WORDS = { autonomous_approve: 'Approved by the agent within the Owner\'s policy', autonomous_decline: 'Declined by the agent under the Owner\'s decline rules', request_evidence: 'More information is needed', owner_review: 'With the Owner for review', policy_hold: 'On hold by policy for the Owner' };

function evidenceBanner(a) {
  const said = a.outcome?.message;
  switch (a.status) {
    case 'proposed': return ['warn', 'Information needed', 'Nothing has been decided. Confirm what you can below.'];
    case 'executed': return ['ok', 'Information recorded', 'Your answer was recorded and the request was assessed again under the Owner\'s policy.'];
    case 'expired': return ['bad', 'Expired', said || 'This request was not answered in time. Ask the assistant for the request again: the same request gets a fresh page; a different one for this customer replaces it.'];
    case 'superseded': return ['bad', 'Replaced by a newer request', said || 'A newer request for this case replaced this one.'];
    default: return ['warn', 'Not open', said || 'This request is no longer open, so it cannot be answered here.'];
  }
}

// One block of fields per thing the backend asked for (need.kind). Names are the item fields the backend validates.
function evidenceFields(n) {
  const t = n.kind;
  const head = `<legend>${esc(n.label)}</legend><p class="hint">${esc(n.how || '')}${n.atLeastText ? ` At least <b>${esc(n.atLeastText)}</b> is needed.` : ''}</p>`;
  if (t === 'deposit' && n.recordPayment) return `<fieldset class="ev-note" data-testid="need-deposit-record"><legend>${esc(n.label)}</legend>
    <p class="hint">${esc(n.how || '')}${n.atLeastText ? ` At least <b>${esc(n.atLeastText)}</b> is needed.` : ''}</p>
    <p><b>Staff cannot supply this by confirming it here.</b> Open Records, record the payment as a receipt for this customer, then ask the assistant to resolve the request again.</p></fieldset>`;
  if (t === 'deposit') return `<fieldset class="ev-item" data-kind="deposit" data-testid="need-deposit">${head}
    ${field({ name: 'deposit.amount', id: 'ev-dep-amount', label: 'Amount received', attrs: 'inputmode="decimal" autocomplete="off"', hint: 'In the workspace currency, for example 150.00.' })}
    ${field({ name: 'deposit.receivedDate', id: 'ev-dep-date', label: 'Date received', type: 'date' })}
    ${field({ name: 'deposit.reference', id: 'ev-dep-ref', label: 'Payment reference', optional: true })}
    ${radios({ name: 'deposit.basis', legend: 'How do you know the money arrived?', hint: 'Required. This is shown with the decision. It is not a recorded payment: only Records holds those.',
      options: [{ value: 'bank', label: 'I saw it arrive in the bank account or payment system', note: 'Staff-checked. It counts only up to the limit the Owner set for deposits Staff check.' },
        { value: 'document', label: 'I saw a receipt or remittance document', note: 'Staff-checked, as above.' },
        { value: 'customer_statement', label: 'The customer said they paid', note: 'Kept and shown as "reported by the customer, not verified". It never counts as a deposit.' }] })}</fieldset>`;
  if (t === 'business_identity') return `<fieldset class="ev-item" data-kind="business_identity" data-testid="need-business_identity">${head}
    ${field({ name: 'business_identity.registration', id: 'ev-id-reg', label: 'Business registration number (ABN or ACN in Australia; the registry number elsewhere)', hint: 'Why it is asked: it shows the customer is a registered business, not only a name. Take it from a registry lookup or from a document the customer gave you.' })}
    ${field({ name: 'business_identity.tradingName', id: 'ev-id-name', label: 'Trading name' })}
    ${radios({ name: 'business_identity.basis', legend: 'Where did you see this?', hint: 'Required.',
      options: [{ value: 'registry', label: 'In a registry lookup' }, { value: 'document', label: 'On a document' }] })}
    ${field({ name: 'business_identity.registeredSince', id: 'ev-id-since', label: 'Registered since', type: 'date', optional: true, hint: 'The date the register shows the business as active from (for an ABN: "ABN status: Active from" on abr.business.gov.au). The Owner sees how long that is. It is information only: no rule uses it.' })}
    <p class="hint" id="ev-id-abn" data-testid="abn-check" role="status"></p></fieldset>`;
  if (t === 'trade_reference') return `<fieldset class="ev-item" data-kind="trade_reference" data-testid="need-trade_reference">${head}
    ${field({ name: 'trade_reference.referee', id: 'ev-tr-ref', label: 'Who gave the reference' })}
    ${field({ name: 'trade_reference.summary', id: 'ev-tr-sum', label: 'What they said', type: 'textarea', rows: 3 })}</fieldset>`;
  return '';
}

function evidenceKeyFacts(a) {
  const k = a.keyFacts || {};
  const row = (l, v) => v ? `<div class="fact"><dt>${esc(l)}</dt><dd>${esc(v)}</dd></div>` : '';
  return `<dl class="facts">${row('Customer', a.customer?.name)}${row('Order amount', k.orderAmount?.text)}${row('Verified deposit so far', k.verifiedDeposit?.text)}${row('Exposure', k.exposure?.text)}
    ${row('Terms', k.termsDays ? days(k.termsDays) : '')}${row('Due date if approved', k.dueDateIfApproved ? dateText(k.dueDateIfApproved) : '')}</dl>${depositSourcesHtml(k)}`;
}

// Where each deposit came from and how it is known, in the backend's words ("checked by Staff in the bank account (not a recorded payment)").
function depositSourcesHtml(k) {
  const rows = k?.depositSources || [];
  if (!rows.length) return '';
  return `<div data-testid="deposit-sources"><h3>Deposit: how it is known</h3><ul>${rows.map(x => `<li data-level="${esc(x.level)}" data-counted="${x.counted ? 'yes' : 'no'}">${esc(x.text)}</li>`).join('')}</ul></div>`;
}

// What the backend said after the submission (or the case as it stands): the status sentence is its own words, with its status and handling.
function evidenceResult(c) {
  if (!c) return '';
  const next = c.actionId && c.status === 'gathering_evidence' ? `<p><a class="btn primary" href="#/actions/${esc(c.actionId)}" data-testid="next-action">Provide the remaining information</a></p>` : '';
  return `<section class="callout ${c.status === 'decided' ? 'ok' : 'warn'}" data-testid="case-result" aria-labelledby="ev-res-title"><h2 id="ev-res-title">Where the request stands now</h2>
    <p data-testid="case-status-text">${esc(c.statusText)}</p>
    <p class="hint">Status: <b data-testid="case-status">${esc(String(c.status || '').replace(/_/g, ' '))}</b> · ${esc(HANDLING_WORDS[c.handling] || c.handling || '')}${ACT.replayed ? ' · <b>This was already answered; nothing was recorded twice.</b>' : ''}</p>
    ${depositSourcesHtml(c.keyFacts)}
    ${(c.warnings || []).length ? `<ul>${c.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
    <p class="hint">Nucleon sent nothing to the customer. Staff informs the customer.</p>${next}</section>`;
}

function renderEvidence() {
  const a = ACT.action, main = $('#main');
  if (!a || !main) return;
  const [tone, headline, sentence] = evidenceBanner(a);
  const person = S.session.identity?.kind !== 'agent' && S.session.channel !== 'service';
  const open = a.status === 'proposed', mayAnswer = open && person && S.role === 'staff';
  const note = ACT.notice ? `<div class="callout ${ACT.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(ACT.notice.text)}</p></div>` : '';
  const asked = (a.needs || []).filter(n => !n.recordPayment).length;   // a need only Records can meet has nothing to type here
  const form = !open ? '' : `<section class="action-in" aria-labelledby="ev-do-title" data-testid="evidence-form"><h2 id="ev-do-title">What you can confirm</h2>
    <p class="hint">Only confirm what you have seen yourself. Leave out anything you have not.</p>
    ${mayAnswer && !asked ? (a.needs || []).map(evidenceFields).join('') : mayAnswer ? `<form id="ev-form" novalidate>${(a.needs || []).map(evidenceFields).join('')}
      <label class="choice"><input type="checkbox" name="no_prior_account"><span>This customer has no earlier account with us <small>Optional. It is checked against the records.</small></span></label>
      ${formError()}<div class="row"><button type="submit" class="btn primary" id="ev-submit" data-testid="submit">Submit information</button></div></form>`
      : `<p class="hint">${!person ? 'This sign-in belongs to the assistant or a service, so it cannot confirm facts. A person signed in to Nucleon as staff does that.' : 'Staff confirm these facts. You can read the request here.'}</p>`}</section>`;
  main.innerHTML = `<div class="action-page" data-testid="evidence-page" data-action="${esc(a.id)}" data-status="${esc(a.status)}">
    ${pageHead({ back: { href: '#/cases', label: 'Requests' }, title: 'Information needed', lede: `For ${esc(a.customer?.name || 'a customer')}'s credit request.` })}
    <div class="callout warn" data-testid="not-approving" role="note"><p><b>You are confirming facts, not approving credit.</b> Nucleon applies the Owner's policy after you submit.</p></div>
    <div class="callout ${tone}" data-testid="banner" role="status"><p><b>${esc(headline)}.</b> ${esc(sentence)}</p></div>
    ${note}${evidenceResult(ACT.result || (a.status === 'executed' ? a.case : null))}
    <section class="facts-card" aria-labelledby="ev-facts-title"><h2 id="ev-facts-title">The request</h2>${evidenceKeyFacts(a)}
      <p class="hint">Prepared ${stamp(a.createdAt)}${open ? ` · expires ${stamp(a.expiresAt)}` : ''}</p></section>
    ${form}
    <p class="hint"><span class="muted">Action</span> ${esc(a.id)}</p></div>`;
  document.title = 'Information needed · Nucleon';
  const f = $('#ev-form');
  if (f) { f.onsubmit = event => { event.preventDefault(); submitEvidence(f); }; bindAbnCheck(f); }
}

// An 11-digit registration is an ABN: its own arithmetic tells a typing mistake from a well-formed number (the same check as delegation.abn_check). Anything
// else (an ACN, another country's registry number) is not judged. It never stops the form: the Owner reads the result, and no rule uses it.
function abnCheck(text) {
  const digits = String(text || '').replace(/^\s*ABN[\s:.]*/i, '').replace(/[\s-]/g, '');
  if (!/^\d{11}$/.test(digits)) return null;
  const w = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19];
  return [...digits].reduce((sum, d, i) => sum + w[i] * (Number(d) - (i === 0 ? 1 : 0)), 0) % 89 === 0;
}
function bindAbnCheck(form) {
  const input = form.elements['business_identity.registration'], out = $('#ev-id-abn', form);
  if (!input || !out) return;
  const say = () => { const ok = abnCheck(input.value);
    out.textContent = ok === null ? '' : ok ? 'This is a well-formed ABN (the number passes the ABN check). Nucleon does not look it up: check it is active on abr.business.gov.au.' : 'This number fails the ABN check, so one of its digits is probably mistyped. You can still send it; the Owner will see that it failed.'; };
  input.addEventListener('input', say); say();
}

// The items typed, in the shape the backend validates; a blank optional field is left out and a blank required one is the backend's to refuse.
function evidenceItems(form) {
  const v = name => (form.elements[name]?.value || '').trim();
  const items = [];
  for (const box of $$('.ev-item', form)) {
    const kind = box.dataset.kind;
    const names = { deposit: ['amount', 'receivedDate', 'reference', 'basis'], business_identity: ['registration', 'tradingName', 'basis', 'registeredSince'], trade_reference: ['referee', 'summary'] }[kind];
    const item = { kind };
    const optional = n => (kind === 'deposit' && n === 'reference') || (kind === 'business_identity' && n === 'registeredSince');
    for (const n of names) { const x = v(kind + '.' + n); if (x || !optional(n)) item[n] = x; }
    items.push(item);
  }
  if (form.elements.no_prior_account?.checked) items.push({ kind: 'no_prior_account', confirmed: true });
  return items;
}

async function submitEvidence(form) {
  const a = ACT.action;
  if (ACT.flight || !a || a.status !== 'proposed') return;
  const items = evidenceItems(form);
  const id = 'evidence-action:' + a.id + ':' + JSON.stringify(items);
  ACT.flight = true; ACT.notice = null;
  const button = $('#ev-submit');
  if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  clearErrors(form);
  try {
    const out = await api(`/api/actions/${encodeURIComponent(a.id)}/evidence`, { version: a.version, items }, { key: keyFor(id), headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    keyDone(id);
    ACT.action = out.action; ACT.result = out.case; ACT.replayed = out.replayed === true;
    toast('Information recorded', 'ok');
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    if (error.status === 401) { S.session = null; return renderGate(null, 'Your session ended. Sign in again; nothing was recorded.'); }
    if (error.code === 'NETWORK' || error.status >= 500) {   // the answer may have been lost: read the action again and show what is recorded
      try { const fresh = await api('/api/actions/' + encodeURIComponent(a.id)); ACT.action = fresh; if (fresh.status === 'executed') { keyDone(id); ACT.notice = { kind: 'ok', text: 'The connection dropped, but your information was recorded. Nothing was recorded twice.' }; } else ACT.notice = { kind: 'warn', text: 'Nothing was recorded yet. You can submit again: it is the same submission.' }; } catch { ACT.notice = { kind: 'warn', text: error.message + ' Check the request before trying again.' }; }
    } else {
      keyDone(id);
      if (error.code === 'CSRF_REQUIRED') { try { S.session = await api('/api/session'); } catch { /* shown below */ } ACT.notice = { kind: 'bad', text: 'The page\'s security token was out of date and has been refreshed. Nothing was recorded. Try again.' }; }
      else if (error.data?.action) { ACT.action = error.data.action; ACT.notice = { kind: 'bad', text: error.message }; }
      else if (error.status === 400 && S.route?.name === 'action') {   // the form keeps what was typed; the errors show beside the fields
        ACT.flight = false; const f2 = $('#ev-form');
        if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
        if (f2) showErrors(f2, error); return;
      }
      else ACT.notice = { kind: 'bad', text: error.message };
    }
  } finally {
    ACT.flight = false;
    if (S.route?.name === 'action' && ACT.action?.kind === 'evidence' && !$('#ev-form .error:not(:empty)')) renderEvidence();
  }
}
