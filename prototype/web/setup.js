'use strict';
// Setup: the workspace type (once), the basics, and the checklist of what the agent needs, each linked to where it is done.
// Uses core.js and customers.js helpers.

const TIER = { required: 'Required before requests', recommended: 'Recommended for reliable answers', good: 'Good to have' };
const STATE = { done: ['Done', 'done'], todo: ['To do', 'need'], partly: ['Partly done', 'need'], skipped: ['Skipped', 'wait'] };
const WHERE = { invoice: ['#/customers', 'Customers'], dueDates: ['#/customers', 'Customers'], stillOwed: ['#/customers', 'Customers'], knowledge: ['#/knowledge', 'Knowledge'] };
const KIND = { read: 'Read', prepare: 'Prepare', act: 'Act', external: 'External' };

// The owner's table of the agent's tools (api/agent-tools): what each does, its kind, who is offered it, and an on/off box.
const agentToolsHtml = tools => `<section aria-labelledby="tools-title" data-testid="agent-tools"><h2 id="tools-title">Agent tools</h2>
  <p>In this fictional preview every implemented tool is on by default. Nothing here sends anything outside Nucleon.</p>
  <div class="table-wrap"><table class="rtable"><caption class="visually-hidden">Agent tools</caption>
    <thead><tr><th scope="col">Tool</th><th scope="col">What it does</th><th scope="col">Kind</th><th scope="col">Roles</th><th scope="col">Needs confirmation</th><th scope="col">Enabled</th></tr></thead><tbody>
    ${tools.map(t => `<tr><th scope="row" data-label="Tool">${esc(t.name)}</th><td data-label="What it does">${esc(t.description)}</td><td data-label="Kind">${esc(KIND[t.kind] || t.kind)}</td>
      <td data-label="Roles">${esc(t.roles.map(r => ROLE_NAMES[r]).join(', '))}</td><td data-label="Confirmation">${t.needsConfirmation ? 'Yes' : 'No'}</td>
      <td data-label="Enabled"><label class="tick"><input type="checkbox" data-agent-tool="${esc(t.name)}"${t.enabled ? ' checked' : ''}${t.kind === 'external' ? ' disabled' : ''}><span>On<span class="visually-hidden">: ${esc(t.name)}</span></span></label></td></tr>`).join('')}
  </tbody></table></div><p class="hint">Turning a tool off or on takes effect from the next message to the agent.</p></section>`;

PAGES.setup = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('setup');
  const [setup, tools] = await Promise.all([api('/api/setup'), isOwner() ? api('/api/agent-tools').catch(() => null) : null]);   // the rest of Setup shows without the table
  if (!live(seq)) return;
  R.setup = setup;
  if (!setup.workspace) return firstRun(main);
  if (!setup.settings) return basics(main);
  const s = setup;
  main.innerHTML = `${pageHead({ title: 'Setup', lede: s.ready ? 'Ready: staff can send requests to the agent.' : 'Finish the required items before staff can send requests.' })}
    <p class="status-line"><span class="chip ${s.ready ? 'done' : 'need'}">${s.ready ? 'Ready' : 'Not ready'}</span></p>
    ${['required', 'recommended', 'good'].map(t => `<section aria-labelledby="tier-${t}"><h2 id="tier-${t}">${esc(TIER[t])}</h2><ul class="checklist">
      ${s.checklist.filter(i => i.tier === t).map(i => `<li><span class="chip ${STATE[i.status][1]}">${STATE[i.status][0]}</span><div><b>${esc(i.label)}</b><p class="hint">${esc(i.detail)}</p></div>
        <div class="row">${i.status !== 'done' && WHERE[i.id] ? `<a class="btn small" href="${WHERE[i.id][0]}">Go to ${WHERE[i.id][1]}</a>` : ''}
        ${isOwner() && t !== 'required' && i.status !== 'done' ? `<button type="button" class="btn small" data-skip="${esc(i.id)}" data-to="${i.status !== 'skipped'}">${i.status === 'skipped' ? 'Undo skip' : 'Skip'}</button>` : ''}</div></li>`).join('')}
    </ul></section>`).join('')}
    <p class="hint">${esc(s.notNeeded)} ${esc(s.notYet)}</p>
    ${s.canLoadSample && isOwner() ? `<section><h2>Practice sample</h2><p>This practice workspace is empty. You can load the fictional sample customers, invoices and notes, with a fixed business date.</p><button type="button" class="btn" id="load-sample">Load the fictional sample</button></section>` : ''}
    <section aria-labelledby="ws-title"><h2 id="ws-title">This workspace</h2><dl class="kv">
      <div><dt>Type</dt><dd>${s.workspace.mode === 'practice' ? 'Practice: everything here is fictional' : 'Real business records'}</dd></div>
      <div><dt>Currency</dt><dd>${esc(s.settings.currency)}, ${plural(s.settings.scale, 'decimal place', 'decimal places')}</dd></div>
      <div><dt>Time zone</dt><dd>${esc(s.settings.timezone)}</dd></div>
      ${s.settings.businessName ? `<div><dt>Business name</dt><dd>${esc(s.settings.businessName)}</dd></div>` : ''}
      <div><dt>Business date</dt><dd>${esc(dateText(s.asOfDate))}${S.session.fixedDate ? '. Fixed for practice, so day counts stay the same in every run.' : '.'}</dd></div>
      <div><dt>About dates and times</dt><dd>Day counts and "as of" dates use the business date. Times such as "Decided 18 Oct 2026, 3:38 pm" are when something was actually recorded, on the real clock, so they can be later than a fixed practice date.</dd></div>
    </dl><p class="hint">The workspace type can't change: a different type needs a new database, so fictional and real records never mix. Currency and decimal places can't change once invoices are recorded.</p></section>
    ${tools ? agentToolsHtml(tools.tools) : ''}`;
  $$('[data-agent-tool]', main).forEach(box => { box.onchange = async () => {
    const name = box.dataset.agentTool, on = box.checked;
    await act(box, '/api/agent-tools', { tool: name, enabled: on }, (on ? 'Turned on: ' : 'Turned off: ') + name);
    await afterChange();   // drawn again from the server, so the box shows what is stored
  }; });
  $$('[data-skip]', main).forEach(b => { b.onclick = async () => { if (!(await act(b, '/api/setup/skip', { item: b.dataset.skip, skip: b.dataset.to === 'true' }, 'Saved'))?.error) await afterChange(); }; });
  const sample = $('#load-sample');
  if (sample) sample.onclick = async () => { if (!(await act(sample, '/api/setup/sample', {}, 'Sample loaded'))?.error) await afterChange(); };
};

function firstRun(main) {
  if (!isOwner()) { main.innerHTML = `${pageHead({ title: 'Not set up yet' })}<p>The owner chooses whether this is a real or a practice workspace. Ask them to sign in; this page then shows the steps.</p>`; return; }
  main.innerHTML = `${pageHead({ title: 'Set up this workspace', lede: 'Choose once. A different type needs a new database, so fictional and real records never mix.' })}
    <form id="workspace" class="narrow" novalidate>
      ${radios({ name: 'mode', legend: 'What is this workspace for?', options: [
        { value: 'real', label: 'My business\'s real records', note: 'Starts empty. The fictional sample can never be loaded here.' },
        { value: 'practice-empty', label: 'Practice, starting empty', note: 'Fictional. Rehearse setup with made-up customers and invoices.' },
        { value: 'practice-sample', label: 'Practice with the sample', note: 'Fictional customers, invoices and notes, with a fixed business date.' }] })}
      ${formError()}<button class="btn primary" type="submit">Continue</button></form>`;
  const form = $('#workspace');
  form.onsubmit = event => {
    event.preventDefault();
    const choice = form.elements.mode.value;
    if (!choice) return showErrors(form, { field: 'mode', message: 'Choose what this workspace is for.' });
    busy($('[type=submit]', form), async () => {
      try { await api('/api/setup/workspace', { mode: choice === 'real' ? 'real' : 'practice', withSample: choice === 'practice-sample' }, { key: keyFor('ws:' + choice) }); toast('Workspace set up', 'ok'); await afterChange(); }
      catch (error) { showErrors(form, error); }
    });
  };
}

function basics(main) {
  if (!isOwner()) { main.innerHTML = `${pageHead({ title: 'Almost set up' })}<p>The owner still needs to choose the currency and time zone.</p>`; return; }
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Australia/Sydney';
  main.innerHTML = `${pageHead({ title: 'Basics', lede: 'Required before anything else, so amounts and dates are read correctly. Currency and decimal places can\'t change once invoices are recorded.' })}
    <form id="basics" class="narrow" novalidate>
      ${field({ name: 'currency', label: 'Currency (three letters)', value: 'AUD', attrs: 'maxlength="3" autocomplete="off" required' })}
      ${field({ name: 'scale', label: 'Decimal places in amounts', type: 'number', value: '2', attrs: 'min="0" max="3" required' })}
      ${field({ name: 'timezone', label: 'Time zone', value: zone, attrs: 'autocomplete="off" required', hint: 'Suggested from this browser. Check it.' })}
      ${field({ name: 'businessName', label: 'Business name', optional: true, attrs: 'autocomplete="organization"' })}
      ${formError()}<button class="btn primary" type="submit">Save</button></form>`;
  const form = $('#basics');
  form.onsubmit = event => {
    event.preventDefault();
    busy($('[type=submit]', form), async () => {
      try {
        await api('/api/setup/settings', { currency: fval(form, 'currency').toUpperCase(), scale: Number(fval(form, 'scale')), timezone: fval(form, 'timezone'), businessName: fval(form, 'businessName') || null }, { key: keyFor('settings:' + fval(form, 'currency')) });
        toast('Saved', 'ok'); await afterChange();
      } catch (error) { showErrors(form, error); }
    });
  };
}
