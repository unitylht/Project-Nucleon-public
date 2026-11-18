'use strict';
// The Owner's control panel: #/delegation (docs/ADAPTIVE-DECISION-AUTHORITY.md; the route and the file keep the name Delegation). The Owner, as a person, sets how far the assistant may decide credit requests on its
// own (a versioned policy: every save is a new version, with the version the Owner was shown) and pauses it. What waits for the Owner and what the agent decided is
// acted on in ONE place, the Decide page (review.js); here those sections only count and link. Everything shown is the backend's: the page works out nothing about
// credit; it only collects the Owner's settings and words. Also defines helpers the other Owner pages share (caseLine, countsHtml, feedbackText, gateWords).
// Uses core.js helpers (api, keyFor, busy, pageHead, field, selectField, radios, esc, dateText, money, plainAmount, stamp, toast, formError, showErrors).

const DG = { policy: null, history: [], cases: [], suggestions: [], stats: null, notice: null, prefill: {}, flight: false, formDirty: false };

// A share is a fraction in the backend ("0.25") and a percentage in the form: shifted two places as TEXT, so nothing passes through a float.
function pctOfFraction(f) {
  if (f === null || f === undefined || f === '') return '';
  const [ip, fp = ''] = String(f).split('.');
  const whole = BigInt(ip + fp.slice(0, 2).padEnd(2, '0')).toString();
  const rest = fp.slice(2).replace(/0+$/, '');
  return whole + (rest ? '.' + rest : '');
}
function fractionOfPct(text) {
  const t = String(text ?? '').trim().replace(/%$/, '').trim();
  if (!t) return null;
  if (!/^\d{1,3}(\.\d{1,4})?$/.test(t) || Number(t) > 100) return t;   // not a percentage: the backend refuses it, and says which field
  const [ip, fp = ''] = t.split('.');
  const padded = String(BigInt(ip)).padStart(2, '0');
  const frac = (padded.slice(0, -2) || '0') + '.' + padded.slice(-2) + fp;
  return frac.replace(/0+$/, '').replace(/\.$/, '');
}
const moneyText = m => (m ? plainAmount(m) : '');

// How an Owner feedback entry reads. A tacit agreement is the policy's doing, never the Owner's words: it is shown as "Treated as agreed after N days (no Owner objection)" and its
// stored reason (written by the system) is not shown as the Owner's reason. N is the entry's afterDays, else the number in the stored sentence.
function tacitDays(f) { return f.afterDays ?? (/within (\d+) day/.exec(f.reason || '') || [])[1] ?? null; }
function feedbackText(f) {
  if (f.verdict === 'tacit_agree') return `Treated as agreed${tacitDays(f) ? ' after ' + days(Number(tacitDays(f))) : ''} (no Owner objection)`;
  const word = f.override ? 'You overrode it' : f.verdict === 'agree' ? 'You agreed' : 'You disagreed';
  return word + (f.reason ? ': ' + f.reason : '');
}
// What the track-record gate counted: reliability.sources (the setting) and reliability.gatedOn (what actually gated this time).
const SOURCE_WORDS = { fictional: 'fictional cases only', live: 'live Owner-reviewed cases only', both: 'fictional and live cases together' };
const GATED_WORDS = { fictional: 'the fictional evaluation cases', live: 'live Owner-reviewed cases', pooled: 'fictional and live cases pooled' };
const gateWords = (r) => r ? `Setting: ${SOURCE_WORDS[r.sources] || r.sources}. Counted this time: ${GATED_WORDS[r.gatedOn] || r.gatedOn}.` : '';

// The five reads. keepPolicy: the policy and its versions on screen stay as they are (the Owner has typed into the form, which is saved against
// the version it was drawn from, so a change made elsewhere is refused at the save and not overwritten unseen).
async function dgLoad(keepPolicy = false) {
  const [policy, history, cases, suggestions, stats, research, schedules, records] = await Promise.all([api('/api/delegation/policy'), api('/api/delegation/policy/history'), api('/api/delegation/cases'),
    api('/api/delegation/suggestions'), api('/api/delegation/stats'), api('/api/delegation/research').catch(() => null), api('/api/delegation/schedules').catch(() => ({ schedules: [] })),
    api('/api/records').catch(() => null)]);
  Object.assign(DG, { cases: cases.cases, suggestions: suggestions.suggestions, stats, research, schedules: schedules.schedules || [], customers: records?.customers || [] });
  if (!keepPolicy) Object.assign(DG, { policy, history: history.versions });
  if (!DG.presets) DG.presets = (await api('/api/delegation/presets').catch(() => ({ presets: [] }))).presets;
  DG.quick = await api('/api/delegation/quick-setup').catch(() => null);   // the levels and the answers that describe the policy, for the quick settings at the top
  return policy.version;
}

function policySummary(p) {
  const row = (l, v) => `<div class="fact"><dt>${esc(l)}</dt><dd>${esc(v)}</dd></div>`;
  const ext = p.extensions;
  const on = ext.enabled ? [`up to ${days(ext.maxDays)} after the current due date`, ext.maxDaysFromRequest != null ? `at most ${days(ext.maxDaysFromRequest)} after the request` : null,
    ext.maxDaysPastOriginalDue != null ? `at most ${days(ext.maxDaysPastOriginalDue)} after the original due date` : null].filter(Boolean).join('; ') : 'off';
  const trial = p.newCustomers.trialCredit === 'limited' ? `on, exposure up to ${money(p.newCustomers.maxExposure)}, deposit at least ${pctOfFraction(p.newCustomers.minDepositShare)}%, terms up to ${days(p.newCustomers.maxTermsDays)}` : 'off';
  return `<dl class="facts" data-testid="policy-summary">${row('Mode', p.mode === 'delegated' ? 'Delegated: the agent may decide inside these bounds' : 'Advisory: the agent only recommends')}
    ${row('Most money one request may involve', money(p.limits.maxDecisionExposure))}${row('Most one customer may owe you in total', money(p.limits.maxCustomerExposure))}
    ${row('Extensions', on)}${row('Trial credit for new customers', trial)}
    ${row('A little over a money limit', p.smallOverage?.enabled ? 'still approved: up to ' + [p.smallOverage.maxShare != null ? pctOfFraction(p.smallOverage.maxShare) + '% of the limit' : null, p.smallOverage.maxAmount ? money(p.smallOverage.maxAmount) : null].filter(Boolean).join(p.smallOverage.rule === 'both' ? ' and ' : ' or ') : 'goes to you')}
    ${row('The agent declining on its own', p.autoDecline?.enabled ? 'on, for extensions over: ' + [p.autoDecline.maxExtensionDays != null ? days(p.autoDecline.maxExtensionDays) : null, p.autoDecline.maxDecisionExposure ? money(p.autoDecline.maxDecisionExposure) + ' on the invoice' : null, p.autoDecline.maxCustomerExposure ? money(p.autoDecline.maxCustomerExposure) + ' owed in all' : null, p.autoDecline.maxPriorLateShare != null ? pctOfFraction(p.autoDecline.maxPriorLateShare) + '% late payments' : null].filter(Boolean).join(', ') + ' (when the assistant recommends declining)' : 'off: every decline is yours')}
    ${row('Records confirmed complete', p.evidence?.confirmedCoverageAbove ? `needed above ${money(p.evidence.confirmedCoverageAbove)}: above it every request comes to you until you confirm the customer's records (Staff cannot)` : 'never asked')}
    ${row('Deposit that Staff only checked', p.newCustomers.staffCheckedDepositUpTo ? `counts when the exposure is up to ${money(p.newCustomers.staffCheckedDepositUpTo)}` : 'not accepted: only a payment recorded in Nucleon Records counts')}${row('Customers the agent never decides', p.restrictions.holdCustomers.length ? p.restrictions.holdCustomers.map(dgCustomerName).join(', ') : 'none')}</dl>`;
}

// The gate's current counts, from the stats: per kind, the fictional and live cases the policy would approve that were reviewed, what is pooled, and what gated.
function trackRecordHtml() {
  const t = DG.stats?.trackRecord;
  if (!t) return '';
  const names = { extension: 'Payment extensions', trial_credit: 'Trial credit for new customers' };
  const rows = Object.keys(names).filter(k => t[k]).map(k => {
    const g = t[k].gate, line = (label, c) => `${label} ${c.cases} (the policy would approve, Owner approved ${c.approved})`;
    return `<div class="fact wide"><dt>${esc(names[k])}</dt><dd><span class="tr-line">${esc(line('Fictional:', g.fictional))}</span> <span class="tr-line">${esc(line('Live:', g.live))}${g.live.cases ? ` (${g.live.explicit} explicit, ${g.live.tacit} treated as agreed)` : ''}</span>
      <span class="tr-line">Pooled for the gate: ${esc(g.pooled.cases)}</span><span class="hint-inline">${esc(gateWords(t[k]))}${g.needed ? ` Needs ${esc(g.needed)}${g.shortBy ? '; ' + esc(g.shortBy) + ' more' : ''}.` : ''}</span></dd></div>`;
  }).join('');
  return `<div class="facts-card tr-counts" data-testid="track-counts"><p class="hint">Where the track record stands now, with the current rules:</p><dl class="facts">${rows}</dl></div>`;
}

function policyForm(p) {
  const f = DG.prefill;
  const val = (name, fallback) => (name in f ? f[name] : fallback);
  const check = (name, label, on, hint) => `<label class="choice"><input type="checkbox" name="${name}"${on ? ' checked' : ''}><span>${esc(label)}${hint ? `<small>${esc(hint)}</small>` : ''}</span></label>`;
  return `<form id="dg-form" novalidate data-testid="policy-form">${REQUIRED_LEGEND}
    <fieldset class="dg-basic"><legend>Basic</legend>
      ${selectField({ name: 'mode', id: 'dg-mode', label: 'Mode', placeholder: null, value: val('mode', p.mode), hint: 'Advisory: the agent only recommends, and every request comes to you. Delegated: the agent decides the requests that are inside every rule below, and sends you the rest.',
        options: [{ value: 'advisory', label: 'Advisory' }, { value: 'delegated', label: 'Delegated' }] })}
      ${field({ name: 'limits.maxDecisionExposure', id: 'dg-max-decision', label: 'Most money one request may involve (the exposure of one decision)', value: val('limits.maxDecisionExposure', moneyText(p.limits.maxDecisionExposure)), attrs: 'inputmode="decimal"', hint: 'Exposure is money a customer owes you that you have not been paid yet. For one request it is the amount still unpaid on the invoice (a payment extension), or the order less the deposit already received (trial credit). Example with a limit of 1,000: more time on an invoice with 700 unpaid is inside it; on an invoice with 1,500 unpaid it comes to you.' })}
      ${field({ name: 'limits.maxCustomerExposure', id: 'dg-max-customer', label: 'Most one customer may owe you in total (the customer\'s total exposure)', value: val('limits.maxCustomerExposure', moneyText(p.limits.maxCustomerExposure)), attrs: 'inputmode="decimal"', hint: 'Everything that customer would still owe you, across all their invoices, if the request is granted. Example with a limit of 1,000: a customer asks for more time on an invoice with 700 unpaid and also has another invoice with 500 unpaid. That is 1,200 in total, so it comes to you, even though 700 alone is inside the limit above.' })}
      ${check('extensions.enabled', 'The agent may decide payment extensions', val('extensions.enabled', p.extensions.enabled), 'A payment extension is a customer asking for more time to pay an invoice. Off: every such request comes to you.')}
      ${field({ name: 'extensions.maxDays', id: 'dg-ext-days', label: "Longest single extension (days after the invoice's current due date)", value: val('extensions.maxDays', p.extensions.maxDays), attrs: 'inputmode="numeric"',
        hint: 'How much later than the date the invoice is due now the new payment date may be. It is counted from that due date: not from today, and not from the invoice date. Example with 30: an invoice due 1 March may be moved to 31 March at the latest. An invoice already 29 days late that asks for 14 more days from today counts as 43, so it comes to you.' })}
      ${field({ name: 'extensions.maxDaysFromRequest', id: 'dg-ext-from-request', label: 'Latest new payment date (days after the day the request is received)', optional: true, value: val('extensions.maxDaysFromRequest', p.extensions.maxDaysFromRequest ?? ''), attrs: 'inputmode="numeric"',
        hint: 'Counted from the day the customer asks. Example with 14: the new payment date may be at most two weeks after the request, however late the invoice already is. Leave empty to not use this limit.' })}
      ${field({ name: 'extensions.maxDaysPastOriginalDue', id: 'dg-ext-total', label: 'Most an invoice may be late in total (days after its original due date)', optional: true, value: val('extensions.maxDaysPastOriginalDue', p.extensions.maxDaysPastOriginalDue ?? ''), attrs: 'inputmode="numeric"',
        hint: 'Counted from the first due date the invoice ever had, so asking again and again cannot go past it. Example with 60: two 30-day extensions fit; a third comes to you. Leave empty to not use this limit.' })}
      ${selectField({ name: 'newCustomers.trialCredit', id: 'dg-trial', label: 'Trial credit for new customers', placeholder: null, value: val('newCustomers.trialCredit', p.newCustomers.trialCredit), hint: 'Trial credit is a first order on credit for a customer with no earlier invoices. It is not given to every new customer: it is only what the agent may say yes to when one asks. Off: you decide every one. On: the agent may approve it inside the limits below.',
        options: [{ value: 'off', label: 'Off: the Owner decides every first credit' }, { value: 'limited', label: 'On, within the limits below' }] })}
      ${field({ name: 'newCustomers.maxExposure', id: 'dg-trial-max', label: 'Most trial credit exposure (the order less the deposit received)', value: val('newCustomers.maxExposure', moneyText(p.newCustomers.maxExposure)), attrs: 'inputmode="decimal"', hint: 'What a new customer would owe you after their deposit. Example with a limit of 500: an order of 600 with a deposit of 150 received leaves 450 unpaid, which is inside it. The same order with no deposit leaves 600, so it comes to you.' })}
      ${field({ name: 'newCustomers.minDepositShare', id: 'dg-trial-dep', label: 'Smallest deposit (% of the order; 0 = none asked)', value: val('newCustomers.minDepositShare', pctOfFraction(p.newCustomers.minDepositShare)), attrs: 'inputmode="decimal"', hint: 'The part of the order a new customer must have paid up front before the agent may approve. Example: 25 on an order of 600 means a deposit of at least 150. With 0 no deposit is asked.' })}
      ${check('newCustomers.requireIdentity', 'A new customer must confirm their business identity (ABN or ACN) before a trial credit', val('newCustomers.requireIdentity', p.newCustomers.requireIdentity !== false), 'On: before the agent may approve, Staff give the registration number and trading name and say where they saw them. An ABN is checked for typing mistakes, and you are shown it with how long the business has been registered; that is for you to read, and no rule uses it. Off: the assistant does not ask. For trying things, not for real money.')}
    </fieldset>
    <fieldset class="dg-basic dg-review" data-testid="review-settings"><legend>Approvals the agent made that you have not looked at, and how it earns trust</legend>
      ${field({ name: 'feedback.tacitAgreeAfterDays', id: 'dg-tacit', label: 'Count an approval the agent made as agreed when you have not reviewed it for (days)', optional: true, value: val('feedback.tacitAgreeAfterDays', p.feedback?.tacitAgreeAfterDays ?? ''),
        attrs: 'inputmode="numeric" placeholder="off"', hint: 'This is only about approvals the agent has already made, inside your rules. It never makes the agent decide a request that is waiting for you. Empty (or "off"): an approval you have not looked at stays "not reviewed" and counts neither for nor against the agent. Example with 7: an approval you have not reviewed for 7 days is recorded as "Treated as agreed" and counts as agreement in the track record. It is labelled as such, never as something you wrote, and you can still disagree or override it later. Not applied while delegation is paused, nor to a decision you overrode. 1 to 365 days.' })}
      ${radios({ name: 'trackRecord.sources', legend: 'Which reviewed cases count as the agent\'s track record', hint: 'The track record is the agent\'s score card: of the cases your rules would approve, how often you agreed. It grows each time you agree or disagree with a decision on the Decide page. It only holds the agent back if you set a minimum under Advanced ("Track record"): until the score card reaches it, requests of that kind come to you.', value: val('trackRecord.sources', p.trackRecord.sources || 'both'),
        options: [{ value: 'fictional', label: 'Fictional cases only', note: 'The made-up practice cases that come with the demo data; a simulation. Your reviews of real decisions are shown but do not count toward the minimum.' },
                  { value: 'live', label: 'Live cases only', note: 'Only your own reviews of real decisions count (the ones you gave and the ones treated as agreed, shown apart). Until enough are reviewed, those requests come to you.' },
                  { value: 'both', label: 'Both, pooled (default)', note: 'The practice cases and your reviews of real decisions are added together for the minimum. They are always shown apart, never as one number.' }] })}
      ${trackRecordHtml()}
    </fieldset>
    <fieldset class="dg-basic" data-testid="exception-settings"><legend>Exceptions the agent may decide</legend>
      <p class="hint">Normally a request over a limit comes to you. Here you can let the agent approve one that is a little over a money limit or over the longest extension, but only when both safeguards hold: the team's model gives a high chance that you would approve it, and you approved enough of the most similar earlier cases. A request that breaks any other rule still comes to you. Off by default.</p>
      ${check('exceptions.enabled', 'The agent may approve these exceptions', val('exceptions.enabled', p.exceptions?.enabled ?? false))}
      ${field({ name: 'exceptions.maxOverExposureShare', id: 'dg-exc-over', label: 'How far over a money limit the agent may go (% over the limit)', value: val('exceptions.maxOverExposureShare', pctOfFraction(p.exceptions?.maxOverExposureShare ?? '0.5')), attrs: 'inputmode="decimal"', hint: 'A percentage of the limit, so the amount grows with the limit. With a limit of 1,000: 5 allows up to 1,050, and 50 allows up to 1,500. With a limit of 5,000,000: 5 allows 250,000 over, and 50 allows 2,500,000 over. Start small.' })}
      ${field({ name: 'exceptions.maxExtraDays', id: 'dg-exc-days', label: 'How many days over the longest extension the agent may go', value: val('exceptions.maxExtraDays', p.exceptions?.maxExtraDays ?? 15), attrs: 'inputmode="numeric"', hint: 'Example: with a longest extension of 30 days and 15 here, the agent may approve up to 45 days.' })}
      ${field({ name: 'exceptions.minModelApprove', id: 'dg-exc-model', label: 'Safeguard 1: the chance of your approval the model must give (%)', value: val('exceptions.minModelApprove', pctOfFraction(p.exceptions?.minModelApprove ?? '0.8')), attrs: 'inputmode="decimal"', hint: 'The model estimates, from the decisions you made before, how likely you are to approve this request. 80 means it must put that chance at 80% or more. With no model fitted yet (Model page), no exception is approved.' })}
      ${field({ name: 'exceptions.minSimilarApproved', id: 'dg-exc-similar', label: 'Safeguard 2: of the 5 most similar earlier cases, at least this many you approved', value: val('exceptions.minSimilarApproved', p.exceptions?.minSimilarApproved ?? 3), attrs: 'inputmode="numeric"', hint: 'Nucleon finds the 5 earlier cases most like this one (same kind, similar amount and days). 3 means you must have approved at least 3 of them.' })}
      ${field({ name: 'exceptions.suggestDeclineAbove', id: 'dg-exc-decline', label: 'Prepare a decline for you when the model\'s chance of a decline is at least (%)', optional: true, value: val('exceptions.suggestDeclineAbove', pctOfFraction(p.exceptions?.suggestDeclineAbove ?? '0.8')), attrs: 'inputmode="decimal"', hint: 'This does not decline anything: it writes the reason and gives you one click on the Decide page. Leave empty for never. To let the agent decline on its own, see the section below.' })}
    </fieldset>
    <fieldset class="dg-basic" data-testid="small-overage-settings"><legend>A little over a money limit</legend>
      <p class="hint">For a request whose only problem is being slightly over a money limit: the agent may approve it anyway, with no model and no similar cases needed. Every other rule still applies: days, identity, overdue invoices, earlier dealings, a held customer and incomplete records still come to you. Off by default, so a request even 1 over a limit comes to you.</p>
      ${check('smallOverage.enabled', 'The agent may approve a small amount over a money limit', val('smallOverage.enabled', p.smallOverage?.enabled ?? false))}
      ${field({ name: 'smallOverage.maxShare', id: 'dg-so-share', label: 'Slightly over means at most this % over the limit', optional: true, value: val('smallOverage.maxShare', pctOfFraction(p.smallOverage?.maxShare ?? '0.1')), attrs: 'inputmode="decimal"', hint: 'A percentage, not an amount of money. Example: 10 with a limit of 1,000 lets a request of up to 1,100 pass. Leave it empty to use only the amount below.' })}
      ${field({ name: 'smallOverage.maxAmount', id: 'dg-so-amount', label: 'Or at most this amount over the limit', optional: true, value: val('smallOverage.maxAmount', moneyText(p.smallOverage?.maxAmount)), attrs: 'inputmode="decimal"', hint: 'An amount of money. Example: 50 with a limit of 1,000 lets a request of up to 1,050 pass. Leave it empty to use only the percentage.' })}
      ${radios({ name: 'smallOverage.rule', legend: 'When both are set', value: val('smallOverage.rule', p.smallOverage?.rule || 'either'),
                options: [{ value: 'either', label: 'Either is enough', note: 'Within the percentage OR within the amount. Example with 10% and 50 on a limit of 1,000: a request of 1,080 passes, because it is within 10%.' }, { value: 'both', label: 'Both must hold', note: 'Within the percentage AND within the amount. The same 1,080 comes to you, because it is more than 50 over.' }] })}
    </fieldset>
    <fieldset class="dg-basic" data-testid="auto-decline-settings"><legend>When the agent may decline on its own</legend>
      <p class="hint">Unless you turn this on, the agent never says no: whatever it cannot approve comes to you. With it on, the agent may decline a payment extension by itself when two things are both true: the assistant recommended declining, and the request is over at least one of the lines you set below. A request over a line is never approved by the agent: if the assistant did not recommend declining, it comes to you. A held customer, advisory mode or a pause still send everything to you. You can reverse any decline on the Decide page, and Nucleon never tells the customer. Payment extensions only. Off by default.</p>
      ${check('autoDecline.enabled', 'The agent may decline an extension on its own', val('autoDecline.enabled', p.autoDecline?.enabled ?? false))}
      ${field({ name: 'autoDecline.maxExtensionDays', id: 'dg-ad-days', label: 'Decline an extension longer than (days past the current due date)', optional: true, value: val('autoDecline.maxExtensionDays', p.autoDecline?.maxExtensionDays ?? ''), attrs: 'inputmode="numeric"', hint: 'Example with 60: a request to pay 90 days after the due date may be declined by the agent. Leave empty to not use this line.' })}
      ${field({ name: 'autoDecline.maxDecisionExposure', id: 'dg-ad-amount', label: 'Decline when the amount still unpaid on the invoice is over', optional: true, value: val('autoDecline.maxDecisionExposure', moneyText(p.autoDecline?.maxDecisionExposure)), attrs: 'inputmode="decimal"', hint: 'Example with 5,000: more time on an invoice with 8,000 unpaid may be declined. Leave empty to not use this line.' })}
      ${field({ name: 'autoDecline.maxCustomerExposure', id: 'dg-ad-customer', label: 'Decline when everything the customer owes is over', optional: true, value: val('autoDecline.maxCustomerExposure', moneyText(p.autoDecline?.maxCustomerExposure)), attrs: 'inputmode="decimal"', hint: 'Everything the customer owes across all their invoices, as the records show it. Example with 20,000: more time for a customer who owes 25,000 in all may be declined. While the records are incomplete this line is not used.' })}
      ${field({ name: 'autoDecline.maxPriorLateShare', id: 'dg-ad-late', label: 'Decline when more than this % of earlier payments were late', optional: true, value: val('autoDecline.maxPriorLateShare', pctOfFraction(p.autoDecline?.maxPriorLateShare)), attrs: 'inputmode="decimal"', hint: 'Example with 50: a customer who paid 6 of 10 earlier invoices late (60%) may be declined. Leave empty to not use this line.' })}
    </fieldset>
    <details class="sec dg-advanced"><summary>Advanced (extra controls; all can be left as they are)</summary>
      ${field({ name: 'limits.maxAutonomousExposure30d', id: 'dg-auto30', label: 'Most the agent may approve in 30 days (all approvals still in force)', optional: true, value: val('limits.maxAutonomousExposure30d', moneyText(p.limits.maxAutonomousExposure30d)), attrs: 'inputmode="decimal"', hint: 'A budget for the agent: the exposure of everything it approved in the last 30 days, added up. Example with 10,000: once its approvals reach that, further requests come to you. Leave empty for no limit.' })}
      ${check('extensions.requireNothingElseOverdue', 'An extension needs nothing else overdue', val('extensions.requireNothingElseOverdue', p.extensions.requireNothingElseOverdue), 'On: the agent gives more time on one invoice only when the customer has no other invoice past its due date. Off: other overdue invoices do not matter.')}
      ${field({ name: 'extensions.maxPriorLateShare', id: 'dg-late', label: 'Most earlier payments that may have been late (%)', optional: true, value: val('extensions.maxPriorLateShare', pctOfFraction(p.extensions.maxPriorLateShare)), attrs: 'inputmode="decimal"', hint: 'Example with 30: a customer who paid 4 of 10 earlier invoices late (40%) comes to you. Leave empty for no limit.' })}
      ${field({ name: 'newCustomers.maxTermsDays', id: 'dg-terms', label: 'Longest trial terms (days)', value: val('newCustomers.maxTermsDays', p.newCustomers.maxTermsDays), attrs: 'inputmode="numeric"', hint: 'How long a new customer may take to pay a trial order. Example with 14: payment within two weeks is inside it; a request for 30-day terms comes to you.' })}
      ${field({ name: 'newCustomers.tradeReferenceAbove', id: 'dg-traderef', label: 'A trade reference is needed above this exposure', optional: true, value: val('newCustomers.tradeReferenceAbove', moneyText(p.newCustomers.tradeReferenceAbove)), attrs: 'inputmode="decimal"', hint: 'A trade reference is another supplier vouching for the customer. Above this exposure Staff must record who gave it and what they said before the agent may approve. Leave empty to never ask.' })}
      ${field({ name: 'newCustomers.staffCheckedDepositUpTo', id: 'dg-staffchecked', label: 'A deposit Staff only checked counts up to this exposure', optional: true, value: val('newCustomers.staffCheckedDepositUpTo', moneyText(p.newCustomers.staffCheckedDepositUpTo)), attrs: 'inputmode="decimal"', hint: 'Staff-checked means Staff saw the money in the bank account or a receipt; it is not a recorded payment. Above this exposure only a payment recorded in Nucleon Records counts. Leave empty to accept only recorded payments.' })}
      ${field({ name: 'evidence.confirmedCoverageAbove', id: 'dg-coverage', label: 'Records must be confirmed complete above this exposure', optional: true, value: val('evidence.confirmedCoverageAbove', moneyText(p.evidence.confirmedCoverageAbove)), attrs: 'inputmode="decimal"', hint: "Leave empty to never ask. Only you can confirm that a customer's records are complete (Customers page), so above this exposure every request comes to you until you have: Staff cannot supply it. Set it well above what the agent may decide, or leave it empty." })}
      ${field({ name: 'restrictions.holdCustomers', id: 'dg-hold', label: 'Customers the agent never decides (their names, separated by commas)', optional: true, value: val('restrictions.holdCustomers', p.restrictions.holdCustomers.map(dgCustomerName).join(', ')), hint: 'Every request from these customers comes to you, whatever the other rules say. To be stricter or looser with one customer instead, use "Standing rules for one customer" below.' })}
      ${field({ name: 'restrictions.unusualSizeMultiple', id: 'dg-size', label: 'Send to the Owner an amount above this many times the customer\'s median invoice', optional: true, value: val('restrictions.unusualSizeMultiple', p.restrictions.unusualSizeMultiple ?? ''), attrs: 'inputmode="decimal"', hint: 'The median is the customer\'s typical invoice. Example with 3: a customer whose typical invoice is 1,000 asks for more time on one of 4,000, so it comes to you. Leave empty to not compare.' })}
      ${field({ name: 'trackRecord.minReviewedCases', id: 'dg-min-cases', label: 'Track record: reviewed cases needed before the agent decides', optional: true, value: val('trackRecord.minReviewedCases', p.trackRecord.minReviewedCases ?? ''), attrs: 'inputmode="numeric"', hint: 'Counted per kind of request, among the cases your rules would approve. Example with 5: until 5 such payment extensions have been reviewed, extensions come to you. Leave empty for no minimum.' })}
      ${field({ name: 'trackRecord.minAgreement', id: 'dg-min-agree', label: 'Track record: how often you must have agreed (%)', optional: true, value: val('trackRecord.minAgreement', pctOfFraction(p.trackRecord.minAgreement)), attrs: 'inputmode="decimal"', hint: 'Example with 80: you must have agreed with at least 8 of every 10 reviewed cases. Below that, requests of that kind come to you. Leave empty for no minimum.' })}
    </details>
    ${field({ name: 'note', id: 'dg-note', label: 'Note for this version', optional: true, value: val('note', '') })}
    ${formError()}
    <div class="row"><button type="submit" class="btn primary" id="dg-save" data-testid="save-policy" data-track="panel-save">Save as version ${p.version + 1}</button>
      <span class="hint">Nothing changes until you save: what you typed is lost if you leave without saving. Saving makes a new version (the earlier ones stay under Versions) and never changes a decision already made.</span></div></form>`;
}

// The form as the body the backend validates: every field named as its policy path; blank optional fields are null.
function policyBody(form) {
  const v = name => (form.elements[name]?.value ?? '').trim();
  const orNull = x => (x === '' ? null : x);
  const int = x => (/^\d+$/.test(x) ? Number(x) : x);
  const flag = name => !!form.elements[name]?.checked;
  return {
    expectedVersion: DG.policy.version, note: orNull(v('note')), mode: v('mode'),
    limits: { maxDecisionExposure: v('limits.maxDecisionExposure'), maxCustomerExposure: v('limits.maxCustomerExposure'), maxAutonomousExposure30d: orNull(v('limits.maxAutonomousExposure30d')) },
    extensions: { enabled: flag('extensions.enabled'), maxDays: int(v('extensions.maxDays')), requireNothingElseOverdue: flag('extensions.requireNothingElseOverdue'),
      maxPriorLateShare: fractionOfPct(v('extensions.maxPriorLateShare')),
      maxDaysFromRequest: orNull(v('extensions.maxDaysFromRequest')) === null ? null : int(v('extensions.maxDaysFromRequest')),
      maxDaysPastOriginalDue: orNull(v('extensions.maxDaysPastOriginalDue')) === null ? null : int(v('extensions.maxDaysPastOriginalDue')) },
    newCustomers: { trialCredit: v('newCustomers.trialCredit'), maxExposure: v('newCustomers.maxExposure'), minDepositShare: fractionOfPct(v('newCustomers.minDepositShare')) ?? '',
      maxTermsDays: int(v('newCustomers.maxTermsDays')), tradeReferenceAbove: orNull(v('newCustomers.tradeReferenceAbove')),
      staffCheckedDepositUpTo: orNull(v('newCustomers.staffCheckedDepositUpTo')), requireIdentity: flag('newCustomers.requireIdentity') },
    evidence: { confirmedCoverageAbove: orNull(v('evidence.confirmedCoverageAbove')) },
    restrictions: { holdCustomers: v('restrictions.holdCustomers').split(',').map(x => x.trim()).filter(Boolean).map(dgCustomerId), unusualSizeMultiple: orNull(v('restrictions.unusualSizeMultiple')) },
    trackRecord: { minReviewedCases: orNull(v('trackRecord.minReviewedCases')) === null ? null : int(v('trackRecord.minReviewedCases')), minAgreement: fractionOfPct(v('trackRecord.minAgreement')),
      sources: v('trackRecord.sources') },
    feedback: { tacitAgreeAfterDays: /^(|off)$/i.test(v('feedback.tacitAgreeAfterDays')) ? null : int(v('feedback.tacitAgreeAfterDays')) },   // both keys are always sent, as shown
    exceptions: { enabled: flag('exceptions.enabled'), maxOverExposureShare: fractionOfPct(v('exceptions.maxOverExposureShare')) ?? '0', maxExtraDays: int(v('exceptions.maxExtraDays')),
      minModelApprove: fractionOfPct(v('exceptions.minModelApprove')) ?? '0', minSimilarApproved: int(v('exceptions.minSimilarApproved')), suggestDeclineAbove: fractionOfPct(v('exceptions.suggestDeclineAbove')) },
    smallOverage: { enabled: flag('smallOverage.enabled'), maxShare: fractionOfPct(v('smallOverage.maxShare')), maxAmount: orNull(v('smallOverage.maxAmount')), rule: v('smallOverage.rule') || 'either' },
    autoDecline: { enabled: flag('autoDecline.enabled'), maxExtensionDays: orNull(v('autoDecline.maxExtensionDays')) === null ? null : int(v('autoDecline.maxExtensionDays')),
      maxDecisionExposure: orNull(v('autoDecline.maxDecisionExposure')), maxCustomerExposure: orNull(v('autoDecline.maxCustomerExposure')), maxPriorLateShare: fractionOfPct(v('autoDecline.maxPriorLateShare')) },
  };
}

function historyHtml() {
  return `<ol class="dg-history" data-testid="policy-history">${DG.history.map(h => `<li data-version="${h.version}"><b>Version ${h.version}</b> · ${h.mode}${h.paused ? ' · paused' : ''} · ${stamp(h.createdAt)}
    · ${esc(h.createdBy?.actorId || 'not recorded')}${h.note ? ` · ${esc(h.note)}` : ''}</li>`).join('') || '<li class="muted">No version has been saved yet: the policy is version 0 (advisory, nothing executes).</li>'}</ol>`;
}

function caseLine(c) {
  const k = c.keyFacts || {};
  if (k.kind === 'extension') return `Invoice ${esc(k.invoiceReference || '')}: due ${esc(k.currentDueDateText || k.currentDueDate)} → ${esc(k.requestedDueDateText || k.requestedDueDate)} (+${days(k.extensionDays)}); ${esc(k.amountText || (k.amountOwed && k.amountOwed.text) || 'amount not recorded')}`;
  return `Trial credit: order ${esc(k.orderAmount?.text || '')}, verified deposit ${esc(k.verifiedDeposit?.text || '')}, exposure ${esc(k.exposure?.text || '')}, ${k.termsDays ? days(k.termsDays) : ''} terms`;
}

// What waits for the Owner and what the agent decided is acted on in ONE place, the Decide page. Here: the counts and the rows, each linked to its timeline.
const timelineLink = (c, text = 'Timeline') => `<a href="#/decision-cases/${esc(c.caseId)}" data-testid="case-timeline-link">${esc(text)}</a>`;

function waitingHtml() {
  const rows = DG.cases.filter(c => ['awaiting_owner', 'on_hold'].includes(c.status));
  const note = '<p class="hint" data-testid="act-on-review">Decisions and feedback are made on the Decide page, the one place to act. <a href="#/review" data-track="panel-open-review">Open the Decide page</a>.</p>';
  if (!rows.length) return '<p class="muted" data-testid="waiting-none">Nothing is waiting for you here.</p>' + note;
  return note + rows.map(c => `<article class="dg-case" data-testid="waiting-case" data-case="${esc(c.caseId)}" data-kind="${esc(c.kind)}">
    <h3>${esc(c.customer?.name || '')} <span class="chip ${c.status === 'on_hold' ? 'fail' : 'need'}">${c.status === 'on_hold' ? 'On hold by policy' : 'Needs your decision'}</span></h3>
    <p>${caseLine(c)}</p>${c.why ? `<p class="hint">${esc(c.why)}</p>` : ''}
    <p><a class="btn small" href="#/review" data-testid="open-review">Decide on the Decide page</a> ${timelineLink(c)}</p></article>`).join('');
}

function decidedHtml() {
  const rows = DG.cases.filter(c => c.status === 'decided' && c.decision?.by === 'agent').slice(0, 10);
  const note = '<p class="hint" data-testid="act-on-review-recent">To agree, disagree or override, use the <a href="#/review">Decide page</a>.</p>';
  if (!rows.length) return '<p class="muted" data-testid="decided-none">The agent has not decided anything yet.</p>';
  return note + rows.map(c => {
    const last = (c.feedback || []).slice(-1)[0];
    return `<article class="dg-case" data-testid="agent-decision" data-case="${esc(c.caseId)}">
      <h3>${esc(c.customer?.name || '')} ${c.decision.overridden ? '<span class="chip fail">Overridden</span>' : (c.decision.outcome === 'decline' ? '<span class="chip fail">Declined by the agent</span>' : '<span class="chip done">Approved by the agent</span>')}</h3>
      <p>${caseLine(c)}</p><p class="hint" data-testid="decision-feedback">Under policy version ${esc(c.policyVersion)} · ${stamp(c.decision.at)}${last ? ` · ${esc(feedbackText(last))}` : ' · not reviewed yet'}</p>
      ${c.decision.overridden ? `<p class="callout warn" data-testid="external-effects">${esc(c.externalEffects || '')}</p>` : ''}
      <p>${timelineLink(c)}</p></article>`;
  }).join('');
}

function suggestionsHtml() {
  if (!DG.suggestions.length) return '<p class="muted" data-testid="suggestions-none">No suggestions: the reviewed cases do not point to a change.</p>';
  return DG.suggestions.map((s, i) => `<article class="dg-case" data-testid="suggestion" data-field="${esc(s.field)}"><p>${esc(s.text)}</p>
    <p class="hint">Based on ${esc(s.evidence.n)} reviewed cases (${esc(s.evidence.datasets.map(d => d.replace(/_/g, ' ')).join(', '))}). A suggestion only.${s.note ? ' ' + esc(s.note) : ''}</p>
    <div class="row"><button type="button" class="btn small" data-suggest="${i}">Use this as a new version</button></div></article>`).join('');
}

function countsHtml(s = DG.stats) {   // the live counts; the home page draws the same
  const c = s.counts;
  return `<dl class="facts" data-testid="counts"><div class="fact"><dt>Approved by the agent</dt><dd>${c.autonomous}</dd></div><div class="fact"><dt>Declined by the agent</dt><dd>${c.autonomousDeclined ?? 0}</dd></div><div class="fact"><dt>Asking Staff for information</dt><dd>${c.gatheringEvidence}</dd></div>
    <div class="fact"><dt>With the Owner</dt><dd>${c.ownerReview}</dd></div><div class="fact"><dt>On hold</dt><dd>${c.onHold}</dd></div>
    <div class="fact"><dt>Decided by the Owner</dt><dd>${c.ownerDecided}</dd></div><div class="fact"><dt>Overridden</dt><dd>${c.overrides}</dd></div></dl>
    <p class="hint" data-testid="counts-note">Live cases only: ${esc(s.denominator)} in all${s.since ? ' since ' + esc(dateText(s.since)) : ''}. Fictional cases are excluded (${esc(s.excluded.fictional)}). Workflow counts, not decision quality.</p>`;
}

// ---- the Owner's standing rules per customer (policy.customers): a most-owed amount and/or a longest extension, a note, an optional end date. Saved as a policy version.
function dgCustomerName(id) { return (DG.customers || []).find(c => c.id === id)?.name || id; }
// A name the Owner typed, as the customer's id (the policy stores ids); anything that is not a customer's name is sent as typed, and the backend says so.
function dgCustomerId(text) { const t = text.toLowerCase(); return (DG.customers || []).find(c => c.id === text || (c.name || '').toLowerCase() === t)?.id || text; }
// What a scheduled change would change, in the page's words: the parts of the policy that differ from the one in force now.
const SCHED_WORDS = { mode: 'the mode', limits: 'the money limits', extensions: 'the extension rules', newCustomers: 'trial credit', evidence: 'the records rule', restrictions: 'held customers and unusual sizes',
  trackRecord: 'the track record', feedback: 'unreviewed approvals', exceptions: 'exceptions', smallOverage: 'a little over a limit', autoDecline: 'the agent declining', customers: 'customer rules' };
function schedWords(change) {
  const same = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
  const plain = x => (x && typeof x === 'object' && 'minorUnits' in x ? plainAmount(x) : x);
  const differs = k => { const now = DG.policy?.[k], then = change[k];
    if (now && then && typeof now === 'object' && typeof then === 'object' && !Array.isArray(now)) return Object.keys({ ...now, ...then }).some(f => !same(String(plain(now[f]) ?? ''), String(plain(then[f]) ?? '')) && !same(plain(now[f]), plain(then[f])));
    return !same(now, then); };
  const parts = Object.keys(change).filter(k => SCHED_WORDS[k] && differs(k)).map(k => SCHED_WORDS[k]);
  return parts.length ? 'changes ' + parts.join(', ') : 'the same rules as today';
}
function rulesHtml(p) {
  const rules = Object.entries(p.customers || {});
  const list = rules.length ? `<div class="table-wrap"><table class="rtable" data-testid="customer-rules"><caption class="visually-hidden">Customer rules</caption>
    <thead><tr><th scope="col">Customer</th><th scope="col" class="num">Most owed</th><th scope="col" class="num">Longest extension</th><th scope="col">Until</th><th scope="col">Note</th><th scope="col"><span class="visually-hidden">Remove</span></th></tr></thead><tbody>
    ${rules.map(([id, r]) => `<tr data-customer="${esc(id)}"><th scope="row">${esc(dgCustomerName(id))}</th><td class="num" data-label="Most owed">${r.maxExposure ? esc(money(r.maxExposure)) : '—'}</td><td class="num" data-label="Longest extension">${r.maxExtensionDays ?? '—'}${r.maxExtensionDays != null ? ' days' : ''}</td>
      <td data-label="Until">${r.until ? esc(dateText(r.until)) : 'no end'}</td><td data-label="Note">${esc(r.note || '')}</td><td class="actions"><button type="button" class="btn small" data-rule-remove="${esc(id)}" data-testid="rule-remove">Remove</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="muted" data-testid="rules-none">No customer rules. The policy\'s limits apply to everyone.</p>';
  const options = (DG.customers || []).map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('');
  return `${list}
    <form id="dg-rule" class="dg-rules" novalidate data-testid="rule-form"><div class="dg-rules-row">
      ${selectField({ name: 'customerId', id: 'dg-rule-cust', label: 'Customer', options: (DG.customers || []).map(c => ({ value: c.id, label: c.name })), placeholder: 'Choose a customer…' })}
      ${field({ name: 'maxExposure', id: 'dg-rule-max', label: 'Most this customer may owe', optional: true, attrs: 'inputmode="decimal"' })}
      ${field({ name: 'maxExtensionDays', id: 'dg-rule-days', label: 'Longest extension (days)', optional: true, attrs: 'inputmode="numeric"' })}
      ${field({ name: 'until', id: 'dg-rule-until', label: 'Until', type: 'date', optional: true })}
      ${field({ name: 'note', id: 'dg-rule-note', label: 'Note', optional: true })}</div>
      ${formError()}<div class="row"><button type="submit" class="btn" data-testid="rule-add">Add or replace the rule (saves a version)</button>
      <span class="hint">A rule replaces the policy's most-owed limit and longest extension for that customer only. An expired rule no longer applies.</span></div></form>`;
}

// ---- scheduled changes: the values of the form above, applied on a date, and optionally put back on another
function schedulesHtml() {
  const pending = (DG.schedules || []).filter(x => x.status === 'pending'), done = (DG.schedules || []).filter(x => x.status !== 'pending').slice(-5).reverse();
  const row = x => `<li data-testid="schedule" data-status="${esc(x.status)}"><b>${esc(dateText(x.at))}</b>: ${esc(schedWords(x.change))}${x.revertAt ? `, put back on ${esc(dateText(x.revertAt))}` : ''}${x.note ? ` — ${esc(x.note)}` : ''}
      ${x.status === 'pending' ? `<button type="button" class="btn small" data-sched-cancel="${esc(x.id)}" data-testid="schedule-cancel">Cancel</button>` : `<span class="chip ${x.status === 'applied' ? 'done' : x.status === 'failed' ? 'fail' : 'busy'}">${esc(x.status)}${x.appliedVersion ? ' as v' + x.appliedVersion : ''}</span>`}</li>`;
  return `${pending.length ? `<ul class="home-list" data-testid="schedules-pending">${pending.map(row).join('')}</ul>` : '<p class="muted" data-testid="schedules-none">Nothing scheduled.</p>'}
    ${done.length ? `<details class="sec"><summary>Past scheduled changes</summary><ul class="home-list">${done.map(row).join('')}</ul></details>` : ''}
    <form id="dg-sched" class="dg-rules" novalidate data-testid="schedule-form"><div class="dg-rules-row">
      ${field({ name: 'at', id: 'dg-sched-at', label: 'Apply the form above on', type: 'date' })}
      ${field({ name: 'revertAt', id: 'dg-sched-revert', label: 'Put the current values back on', type: 'date', optional: true })}
      ${field({ name: 'note', id: 'dg-sched-note', label: 'Note', optional: true })}</div>
      ${formError()}<div class="row"><button type="submit" class="btn" data-testid="schedule-add">Schedule</button>
      <span class="hint">For a change that should start on a date. Fill in the form above with the values you want, do not save it, then choose the date here and press Schedule. On that day the values become a new version by themselves. Example: lower the limits for December and put today's values back on 1 January.</span></div></form>`;
}

// ---- the team's model, in brief, with the promotion settings (the Model page has the rest)
function modelHtml() {
  const d = DG.research;
  if (!d) return '<p class="muted">Not available.</p>';
  const m = d.model, a = d.agreement, p = d.promotion, s = d.settings.promotion;
  const status = m ? `<b>${esc(m.name)} v${esc(m.version)}</b>, fitted on ${m.trainedOn?.rows ?? '?'} rows.` : 'No model in force yet.';
  const agree = a.n ? ` It agreed with you on ${a.agreed} of ${a.n} scored live cases.` : ' No scored live case has your verdict yet.';
  return `<div class="dg-model"><p data-testid="model-brief">${status}${agree} <a href="#/research">Open the Model page</a> for the coefficients, the versions and the training table.</p>
    <div class="callout ${p.active ? 'ok' : 'warn'} small" data-testid="model-promotion"><p>${esc(p.reason)}</p></div>
    <form id="dg-model" novalidate data-testid="model-form">
      <label class="choice"><input type="checkbox" name="enabled"${s.enabled ? ' checked' : ''}><span>Use the model as an extra caution: when it thinks you would probably decline, the case comes to you<small>It starts only once the model has earned it (the two bars below). Here the model can only send a case to you: it never approves anything your rules would not, and it never declines.</small></span></label>
      <div class="dg-rules-row">${field({ name: 'minCases', id: 'dg-model-cases', label: 'Bar: real cases the model scored that you then decided', value: s.minCases, attrs: 'inputmode="numeric"' })}
      ${field({ name: 'minAgreement', id: 'dg-model-agree', label: 'Bar: how often the model agreed with you (%)', value: Math.round(s.minAgreement * 100), attrs: 'inputmode="numeric"' })}
      ${field({ name: 'threshold', id: 'dg-model-thr', label: 'Send the case to me when the chance of a decline is at least (%)', value: Math.round(s.threshold * 100), attrs: 'inputmode="numeric"' })}
      ${field({ name: 'autoRefitEvery', id: 'dg-model-auto', label: 'Learn again after every N of your decisions', optional: true, value: d.settings.autoRefitEvery ?? '', attrs: 'inputmode="numeric" placeholder="never"' })}</div>
      ${formError()}<div class="row"><button type="submit" class="btn" data-testid="model-save">Save model settings</button><button type="button" class="btn" id="dg-refit" data-testid="model-refit">Fit a new version now</button></div></form></div>`;
}

// The choices of Get started, here as well (12 Nov 2026), so that changing one never means running that path again: the level (it opens Quick setup filled in;
// nothing is saved until the Owner saves there, and the settings a level does not cover stay as they are), the customers the agent never decides for (the
// field under Advanced), and how much the pages show (core.js VIEWS: this browser only, not part of the policy).
function quickSettingsHtml(p) {
  const q = DG.quick, held = p.restrictions.holdCustomers.map(dgCustomerName);
  const levels = q && (q.levels || []).length ? `<div data-testid="dg-levels-block"><h3>How strict the agent is</h3>
      <p class="hint">A level fills six answers in Quick setup from your own open invoices and shows what they would do. You save it there; every other setting stays as it is.</p>
      ${levelButtons(q.levels, p.version > 0 ? qsLevelOf(q.answers, q.levels) : 'none', { testid: 'dg-levels' })}</div>` : '';
  return `<section class="facts-card" aria-labelledby="dg-quick-h" data-testid="dg-quick"><h2 id="dg-quick-h">${icon('flag')}Quick settings</h2><div class="dg-quick">${levels}
    <div><h3>Customers the agent never decides for</h3><p data-testid="dg-held">${held.length ? esc(held.join(', ')) : 'None.'} <button type="button" class="btn small" data-testid="dg-held-change">Change</button></p></div>
    <div>${viewChooser('dg-view')}</div></div></section>`;
}
const DG_JUMP = [['dg-quick-h', 'flag', 'Quick settings'], ['dg-cur', 'doc', 'Current policy'], ['dg-wait', 'inbox', 'Waiting for you'], ['dg-edit', 'rules', 'Change the policy'], ['dg-rules-h', 'user', 'One customer'],
  ['dg-sched-h', 'calendar', 'Scheduled'], ['dg-model-h', 'chip', 'Model'], ['dg-hist', 'history', 'Versions'], ['dg-cnt', 'chart', 'Counts']];
function dgJump(id) {
  const el = document.getElementById(id);
  if (!el) return;
  for (let d = el.closest('details'); d; d = d.parentElement?.closest('details')) d.open = true;
  el.scrollIntoView({ block: 'start' });
}

function renderDelegation() {
  const p = DG.policy, main = $('#main');
  if (!main) return;
  const simple = viewLevel() === 'simple';
  const note = DG.notice ? `<div class="callout ${DG.notice.kind || 'warn'}" role="alert" data-testid="notice"><p>${esc(DG.notice.text)}</p></div>` : '';
  main.innerHTML = `<div class="delegation-page" data-testid="delegation-page">
    ${pageHead({ title: 'Control panel', lede: 'Your rules for the agent. A request that is inside every rule below is decided by the agent; anything outside a rule comes to you. Nothing is ever sent to a customer.',
      actions: `<button type="button" class="btn ${p.paused ? 'primary' : ''}" id="dg-pause" data-testid="${p.paused ? 'resume' : 'pause'}" data-track="panel-${p.paused ? 'resume' : 'pause'}">${p.paused ? 'Resume delegation' : 'Pause delegation'}</button>` })}
    ${note}
    <div class="callout ${p.paused ? 'bad' : p.mode === 'delegated' ? 'ok' : 'warn'}" data-testid="policy-state" role="status"><p><b>Policy version ${p.version}${p.paused ? ' · paused' : ''}.</b>
      ${p.paused ? 'Paused: nothing is decided by the agent; every request comes to you.' : p.mode === 'delegated' ? 'The agent may decide inside the bounds below.' : p.version === 0 ? 'No policy has been saved, so the agent only recommends.' : 'Advisory: the agent only recommends.'}</p></div>
    <nav class="dg-jump" aria-label="On this page" data-testid="dg-jump">${DG_JUMP.map(([id, ic, text]) => `<a href="#/delegation" data-jump="${id}">${icon(ic)}${esc(text)}</a>`).join('')}</nav>
    ${quickSettingsHtml(p)}
    <section class="facts-card" aria-labelledby="dg-cur">${`<h2 id="dg-cur">${icon('doc')}Current policy</h2>`}${policySummary(p)}</section>
    ${simple ? '<details class="sec" data-testid="dg-more-work"><summary>Requests and decisions (also on the Decide page)</summary>' : ''}
    <section aria-labelledby="dg-wait"><h2 id="dg-wait">${icon('inbox')}Waiting for you</h2>${waitingHtml()}</section>
    <section aria-labelledby="dg-dec"><h2 id="dg-dec">${icon('check')}Recent agent decisions</h2>${decidedHtml()}</section>
    <section aria-labelledby="dg-sug"><h2 id="dg-sug">${icon('bulb')}Suggestions</h2>${suggestionsHtml()}</section>
    ${simple ? '</details>' : ''}
    <section class="action-in" aria-labelledby="dg-edit"><h2 id="dg-edit">${icon('rules')}Change the policy</h2><p class="callout" data-testid="quick-setup-link">New here? <a href="#/quick-setup">Quick setup</a> asks a few questions and shows what they would do.</p><p class="hint" data-testid="doctor-link">Wondering why requests still reach you? Ask the <a href="#/doctor">Doctor</a>.</p>${presetsHtml()}${policyForm(p)}</section>
    ${simple ? '<details class="sec" data-testid="dg-more-settings"><summary>More settings and history (one customer, scheduled changes, the model, versions, counts)</summary>' : ''}
    <section aria-labelledby="dg-rules-h"><h2 id="dg-rules-h">${icon('user')}Standing rules for one customer</h2>${rulesHtml(p)}</section>
    <section aria-labelledby="dg-sched-h"><h2 id="dg-sched-h">${icon('calendar')}Scheduled changes</h2>${schedulesHtml()}</section>
    <section aria-labelledby="dg-model-h"><h2 id="dg-model-h">${icon('chip')}The team's model</h2>${modelHtml()}</section>
    <section aria-labelledby="dg-hist"><h2 id="dg-hist">${icon('history')}Versions</h2>${historyHtml()}</section>
    <section aria-labelledby="dg-cnt"><h2 id="dg-cnt">${icon('chart')}Live counts</h2>${countsHtml()}</section>${simple ? '</details>' : ''}</div>`;
  document.title = 'Control panel · Nucleon';
  $$('[data-jump]', main).forEach(a => { a.onclick = e => { e.preventDefault(); dgJump(a.dataset.jump); }; });
  $$('[data-testid=dg-levels] [data-level]', main).forEach(b => { b.onclick = () => { location.hash = b.dataset.level === 'custom' ? '#/quick-setup' : '#/quick-setup?level=' + encodeURIComponent(b.dataset.level); }; });
  const heldChange = $('[data-testid=dg-held-change]', main);
  if (heldChange) heldChange.onclick = () => { const f = $('#dg-hold'); if (f) { const d = f.closest('details'); if (d) d.open = true; f.scrollIntoView({ block: 'center' }); f.focus(); } };
  bindViewChooser(main, () => {   // the menu and the page follow at once; what was typed into the form is kept
    const kept = dgCapture();
    if (kept.edits) DG.prefill = { ...DG.prefill, ...kept.edits };
    renderFrame(S.route); renderDelegation(); dgRestore(kept);
  });
  $('#dg-form').oninput = () => { DG.formDirty = true; };
  markRequired($('#dg-form'));
  // turning trial credit on from the strict defaults: the deposit field still says 100%; the product default is none asked (4 Nov 2026)
  $$('[name="newCustomers.trialCredit"]').forEach(el => { el.addEventListener('change', () => {
    const v = el.type === 'radio' ? (el.checked ? el.value : null) : el.value, dep = $('#dg-trial-dep');
    if (v === 'limited' && dep && Number(dep.value) >= 100) { dep.value = '0'; DG.formDirty = true; }
  }); });
  S.leaveGuard = () => !DG.formDirty || confirm('The policy form has changes you have not saved. Leave without saving them?');
  S.leaveDirty = () => DG.formDirty;
  $('#dg-form').onsubmit = event => { event.preventDefault(); savePolicy(event.target); };
  $('#dg-pause').onclick = () => policyAction(p.paused ? 'resume' : 'pause');
  $$('[data-suggest]').forEach(b => { b.onclick = () => useSuggestion(DG.suggestions[Number(b.dataset.suggest)]); });
  $$('[data-preset]').forEach(b => { b.onclick = () => applyPreset(b.dataset.preset); });
  bindExtras();
}

function bindExtras() {
  const rule = $('#dg-rule');
  if (rule) rule.onsubmit = event => { event.preventDefault(); saveRule(rule); };
  $$('[data-rule-remove]').forEach(b => { b.onclick = () => removeRule(b.dataset.ruleRemove); });
  const sched = $('#dg-sched');
  if (sched) sched.onsubmit = event => { event.preventDefault(); addSchedule(sched); };
  $$('[data-sched-cancel]').forEach(b => { b.onclick = () => cancelSchedule(b.dataset.schedCancel); });
  const model = $('#dg-model');
  if (model) model.onsubmit = event => { event.preventDefault(); saveModelSettings(model); };
  const refit = $('#dg-refit');
  if (refit) refit.onclick = () => refitModel(refit);
}

// A rule is saved as a policy version: the whole current policy with customers changed (the form above is not sent, so unsaved edits there are kept on screen).
async function putRules(customers, note) {
  const p = DG.policy, body = { expectedVersion: p.version, note, mode: p.mode, limits: p.limits, extensions: p.extensions, newCustomers: p.newCustomers, evidence: p.evidence,
    restrictions: p.restrictions, trackRecord: p.trackRecord, feedback: p.feedback, customers, exceptions: p.exceptions, smallOverage: p.smallOverage, autoDecline: p.autoDecline };
  const out = await api('/api/delegation/policy', body, { method: 'PUT', headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
  toast('Saved as version ' + out.version, 'ok');
  return dgRefresh({ kind: 'ok', text: 'Saved as version ' + out.version + '.' });
}
async function saveRule(form) {
  if (DG.flight) return;
  clearErrors(form);
  const v = name => (form.elements[name]?.value ?? '').trim();
  const id = v('customerId');
  if (!id) { showErrors(form, { field: 'customerId', message: 'Choose a customer.' }); return; }
  const rule = { maxExposure: v('maxExposure') || null, maxExtensionDays: v('maxExtensionDays') ? Number(v('maxExtensionDays')) : null, until: v('until') || null, note: v('note') || null };
  DG.flight = true;
  try { await putRules({ ...(DG.policy.customers || {}), [id]: rule }, 'Customer rule: ' + dgCustomerName(id)); }
  catch (error) { if (error.code !== 'SIGNED_OUT') showErrors(form, error); }
  finally { DG.flight = false; }
}
async function removeRule(id) {
  if (DG.flight) return;
  DG.flight = true;
  const customers = { ...(DG.policy.customers || {}) };
  delete customers[id];
  try { await putRules(customers, 'Customer rule removed: ' + dgCustomerName(id)); } catch (error) { if (error.code !== 'SIGNED_OUT') dgRefresh({ kind: 'bad', text: error.message }); } finally { DG.flight = false; }
}

async function addSchedule(form) {
  if (DG.flight) return;
  clearErrors(form);
  const v = name => (form.elements[name]?.value ?? '').trim();
  const policyFormEl = $('#dg-form');
  const change = policyBody(policyFormEl);
  delete change.expectedVersion; delete change.note;
  DG.flight = true;
  try {
    await api('/api/delegation/schedules', { at: v('at'), revertAt: v('revertAt') || null, note: v('note') || null, change }, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    toast('Scheduled.', 'ok');
    DG.flight = false;
    return dgRefresh({ kind: 'ok', text: 'Scheduled for ' + v('at') + '. Nothing changes before then.' });
  } catch (error) { if (error.code !== 'SIGNED_OUT') showErrors(form, error); } finally { DG.flight = false; }
}
async function cancelSchedule(id) {
  if (DG.flight) return;
  DG.flight = true;
  try { await api('/api/delegation/schedules/' + encodeURIComponent(id) + '/cancel', {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); DG.flight = false; return dgRefresh({ kind: 'ok', text: 'Cancelled.' }); }
  catch (error) { if (error.code !== 'SIGNED_OUT') dgRefresh({ kind: 'bad', text: error.message }); } finally { DG.flight = false; }
}

async function saveModelSettings(form) {
  if (DG.flight) return;
  clearErrors(form);
  const v = name => (form.elements[name]?.value ?? '').trim();
  const body = { autoRefitEvery: v('autoRefitEvery') ? Number(v('autoRefitEvery')) : null,
    promotion: { enabled: !!form.elements.enabled?.checked, minCases: Number(v('minCases')), minAgreement: Number(v('minAgreement')) / 100, threshold: Number(v('threshold')) / 100 } };
  DG.flight = true;
  try { DG.research = await api('/api/delegation/research/settings', body, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); toast('Model settings saved.', 'ok'); renderDelegation(); }
  catch (error) { if (error.code !== 'SIGNED_OUT') showErrors(form, error); } finally { DG.flight = false; }
}
async function refitModel(button) {
  if (DG.flight) return;
  DG.flight = true; button.disabled = true;
  try { DG.research = await api('/api/delegation/research/refit', {}, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } }); toast('Fitted ' + DG.research.model.name + ' v' + DG.research.model.version, 'ok'); renderDelegation(); }
  catch (error) { if (error.code !== 'SIGNED_OUT') dgRefresh({ kind: 'bad', text: error.message }); } finally { DG.flight = false; }
}

async function dgRefresh(notice) {
  DG.notice = notice || null;
  try { await dgLoad(); } catch (error) { if (error.code === 'SIGNED_OUT') return; DG.notice = { kind: 'bad', text: error.message }; }
  if (S.route?.name === 'delegation') renderDelegation();
}

// A save is a PUT of the whole policy with the version the Owner was shown; a stale version (another tab, a pause) is refused and the page is read again.
async function savePolicy(form) {
  if (DG.flight) return;
  DG.flight = true;
  const button = $('#dg-save');
  button.disabled = true;
  clearErrors(form);
  // a name that is no customer's would be stored and never match anyone: say so before saving (11 Nov 2026)
  const unknown = (DG.customers || []).length ? policyBody(form).restrictions.holdCustomers.filter(id => !DG.customers.some(c => c.id === id)) : [];
  if (unknown.length) {
    const adv = document.querySelector('.dg-advanced'); if (adv) adv.open = true;
    showErrors(form, { field: 'restrictions.holdCustomers', message: 'No customer is called "' + unknown.join('", "') + '". Type each name as it appears on the Customers page, separated by commas.' });
    DG.flight = false; button.disabled = false;
    return;
  }
  try {
    const out = await api('/api/delegation/policy', policyBody(form), { method: 'PUT', headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    DG.prefill = {}; DG.formDirty = false;
    toast('Saved as version ' + out.version, 'ok');
    DG.flight = false;
    return dgRefresh({ kind: 'ok', text: 'Saved as version ' + out.version + '. Decisions already made are unchanged.' });
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    if (error.code === 'POLICY_CHANGED') { DG.flight = false; DG.prefill = {}; DG.formDirty = false; return dgRefresh({ kind: 'bad', text: error.message + ' Your edits were not saved.' }); }
    if (error.code === 'CSRF_REQUIRED') { try { S.session = await api('/api/session'); } catch { /* shown below */ } toast('The page\'s security token was refreshed. Nothing was saved. Try again.', 'bad'); }
    else showErrors(form, error);
  } finally {
    DG.flight = false;
    if (button.isConnected) button.disabled = false;
  }
}

async function policyAction(action) {
  if (DG.flight) return;
  DG.flight = true;
  try {
    const out = await api('/api/delegation/policy/' + action, { expectedVersion: DG.policy.version }, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    DG.flight = false;
    return dgRefresh({ kind: 'ok', text: (out.paused ? 'Delegation is paused' : 'Delegation is running') + ' (version ' + out.version + ').' });
  } catch (error) {
    if (error.code === 'SIGNED_OUT') return;
    DG.flight = false;
    return dgRefresh({ kind: 'bad', text: error.message });
  } finally { DG.flight = false; }
}

// A suggestion fills the form; the Owner still reads it and saves it as a new version.
// Presets (4 Nov 2026): one that fits the fictional records, one wide open for testers. Each is saved as a new version with its name in the note.
function presetsHtml() {
  const list = DG.presets || [];
  if (!list.length) return '';
  return `<div class="facts-card" data-testid="presets"><p><b>Presets.</b> Each saves a new version at once (named in the versions list), so you can go back to any earlier one.</p>
    <p class="row">${list.map(x => `<button type="button" class="btn" data-preset="${esc(x.name)}" data-testid="preset-${esc(x.name)}">${esc(x.label)}</button>`).join(' ')}</p>
    ${list.map(x => `<p class="hint"><b>${esc(x.label)}:</b> ${esc(x.description)}</p>`).join('')}</div>`;
}

async function applyPreset(name) {
  const x = (DG.presets || []).find(p => p.name === name);
  if (!x || DG.flight) return;
  if (!confirm('Save "' + x.label + '" as a new policy version now? Decisions already made are unchanged, and the earlier versions stay.')) return;
  DG.flight = true;
  try {
    const out = await api('/api/delegation/presets/' + encodeURIComponent(name), { expectedVersion: DG.policy.version }, { headers: { 'X-Nucleon-CSRF': S.session.csrf || '' } });
    DG.prefill = {}; DG.formDirty = false; DG.flight = false;
    toast('Saved as version ' + out.version, 'ok');
    return dgRefresh({ kind: 'ok', text: 'Preset "' + x.label + '" saved as version ' + out.version + '.' });
  } catch (error) {
    DG.flight = false;
    if (error.code === 'POLICY_CHANGED') return dgRefresh({ kind: 'bad', text: error.message });
    toast(error.message, 'bad');
  }
}

function useSuggestion(s) {
  const value = s.field === 'newCustomers.maxExposure' ? moneyText(s.suggested) : String(s.suggested);
  DG.prefill = { ...DG.prefill, [s.field]: value };
  DG.notice = { kind: 'warn', text: 'The form below now holds this suggestion. Nothing is saved until you review it and save it as a new version.' };
  renderDelegation();
  $('#dg-form').scrollIntoView({ block: 'center' });
}

PAGES.delegation = async (r, seq) => {
  const main = $('#main');
  if (S.role !== 'owner') {
    main.innerHTML = `<div class="state-msg" data-testid="delegation-owner-only">${pageHead({ title: 'Control panel', lede: 'Where the Owner sets how far the assistant may decide on its own.' })}<p>Only the Owner sets how far the assistant may decide on its own. Staff can read the current policy through the assistant.</p></div>`;
    return;
  }
  main.innerHTML = loading('the control panel');
  DG.notice = null; DG.prefill = {}; DG.formDirty = false;
  await dgLoad();
  if (!live(seq)) return;
  renderDelegation();
  keepFresh(seq);
};

// The page reads itself again every REFRESH_MS while it is visible, and when the window or tab comes back (core.js): a request that arrives while the Owner is
// here shows without a reload. What the Owner has typed (a reason, the form), the open "Advanced" section and the focused field are kept across it, and nothing is read
// while a save or a decision is in flight.
function dgCapture() {
  const form = $('#dg-form'), typed = {};
  $$('[data-why]').forEach(t => { if (t.value) typed[t.id] = t.value; });
  const edits = DG.formDirty && form ? Object.fromEntries([...form.elements].filter(e => e.name && (e.type !== 'radio' || e.checked)).map(e => [e.name, e.type === 'checkbox' ? e.checked : e.value])) : null;
  const a = document.activeElement, inPage = a && a.id && $('#main')?.contains(a);
  return { typed, edits, advanced: !!$('.dg-advanced')?.open, focus: inPage ? { id: a.id, start: a.selectionStart, end: a.selectionEnd } : null, y: scrollY };
}
function dgRestore(k) {
  $$('[data-why]').forEach(t => { if (k.typed[t.id]) t.value = k.typed[t.id]; });
  const adv = $('.dg-advanced'); if (adv && k.advanced) adv.open = true;
  const f = k.focus && document.getElementById(k.focus.id);
  if (f) { f.focus({ preventScroll: true }); try { f.setSelectionRange(k.focus.start, k.focus.end); } catch { /* not a text field */ } }
  scrollTo(0, k.y);
}
REFRESH.delegation = async seq => {
  if (DG.flight || $('dialog[open]')) return;
  const kept = dgCapture();
  let policyVersion;
  try { policyVersion = await dgLoad(!!kept.edits); } catch (error) { if (error.code === 'SIGNED_OUT' || error.status === 401) throw error; return; }   // a failed read leaves the page as it is
  if (!live(seq) || S.route?.name !== 'delegation') return;
  if (kept.edits) {
    DG.prefill = { ...DG.prefill, ...kept.edits };
    if (policyVersion !== DG.policy.version) DG.notice = { kind: 'warn', text: `The policy was changed elsewhere (it is now version ${policyVersion}). What you typed is kept, but saving it will be refused so that you can read the new version first.` };
  }
  renderDelegation();
  dgRestore(kept);
};
