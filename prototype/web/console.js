'use strict';
// The demo console (operator only, practice workspaces): reset, start empty, restore a backup, and the practice messages.
// Uses core.js and requests.js helpers.

const CONSOLE = { state: null, last: null };

PAGES.console = async (r, seq, quiet) => {
  const main = $('#main');
  if (!main) return;
  if (!quiet) main.innerHTML = loading('the demo console');
  let state;
  try { state = await api('/api/demo/console'); } catch (error) { if (live(seq) && $('#main')) renderFailure(error, () => route()); return; }
  if (!live(seq) || !$('#main') || S.route?.name !== 'console') return;   // QA B7: the page may have changed while this loaded
  if (quiet && $('dialog[open]')) return;
  CONSOLE.state = state;
  renderConsole();
};

function caseSummary(c) {
  if (!c.cases) return c.asOfDate ? 'No cases. This is the starting state.' : 'No cases, and no demo records are loaded yet.';
  const names = { awaiting_owner: 'waiting for the owner', needs_information: 'waiting for staff', completed: 'completed', analysing: 'being prepared', received: 'queued', decided: 'being saved', preparation_failed: 'failed to prepare' };
  return `${c.cases === 1 ? 'One case' : c.cases + ' cases'}: ${Object.entries(c.byStatus).map(([k, n]) => `${n} ${names[k] || k}`).join(', ')}.`;
}

function renderConsole() {
  const main = $('#main');
  const c = CONSOLE.state;
  if (!main || !c) return;
  const last = CONSOLE.last;
  const agent = S.model?.state === 'ready' ? 'Ready' : S.model?.state === 'reachable_not_loaded' ? 'Loading the model' : S.model?.state === 'unreachable' ? 'Offline: new cases are prepared without AI' : c.agent.mode === 'mock' ? 'Test agent, no AI' : 'Checking';
  main.innerHTML = `${pageHead({ title: 'Demo console', lede: 'Prepare and repeat presentations on this practice instance. Changes here affect everyone using it.' })}
    ${last ? `<p class="callout ${last.error ? 'bad' : 'ok'}" role="status" data-testid="console-result">${esc(last.text)}${last.undo ? ' <button type="button" class="btn small" id="undo">Undo</button>' : ''}</p>` : ''}
    <section aria-labelledby="reset-title"><h2 id="reset-title">Start again</h2>
      <p><span data-testid="console-cases">${esc(caseSummary(c))}</span></p>
      <p class="hint">Reset clears every case and restores the original demo records and due dates. Start empty clears cases and records but keeps the currency and time zone, to rehearse setup. New workspace clears the currency and time zone too, so the owner sets them again under Setup (for records kept in another currency). All three save a backup first, so each can be undone. Sign-ins stay as they are.</p>
      <div class="row"><button class="btn danger" type="button" id="reset"${c.cases || !c.fixtureCurrent ? '' : ' disabled'}>Reset demo data</button>
        <button class="btn" type="button" id="start-empty">Start empty</button>
        <button class="btn" type="button" id="new-workspace">New workspace</button></div>
    </section>
    <section aria-labelledby="ready-title"><h2 id="ready-title">Before you present</h2><dl class="kv">
      <div><dt>Agent</dt><dd>${esc(agent)}</dd></div>
      <div><dt>Signed in here</dt><dd>${esc(S.held.filter(r => r !== 'operator').map(r => ROLE_NAMES[r]).join(' and ') || 'Nobody yet')}. Sign in as staff and owner in this browser once, then switch with the buttons at the top.</dd></div>
      <div><dt>Business date</dt><dd>${c.asOfDate ? `Fixed at ${esc(dateText(c.asOfDate))}, so day counts stay the same in every run.` : c.workspace === 'practice' ? 'Practice records without the sample use today\'s date.' : 'No demo records yet. Reset demo data loads the fictional sample.'}</dd></div>
    </dl></section>
    <section aria-labelledby="scripts-title"><h2 id="scripts-title">Practice messages</h2>
      <ul class="scripts">${SAMPLES.map((s, i) => `<li><q>${esc(s.text)}</q><p class="hint">${esc(s.label)}. ${esc(s.note)}.</p><button type="button" class="btn small" data-copy="${i}">Copy<span class="visually-hidden"> the ${esc(s.label.toLowerCase())} message</span></button></li>`).join('')}</ul>
    </section>
    <section aria-labelledby="backups-title"><h2 id="backups-title">Backups</h2>
      ${c.backups.length ? `<div class="table-wrap"><table class="rtable"><thead><tr><th scope="col">Saved</th><th scope="col" class="num">Cases</th><th scope="col"><span class="visually-hidden">Restore</span></th></tr></thead><tbody>
        ${c.backups.map(b => `<tr><th scope="row" data-label="Saved">${stamp(b.createdAt)}<span class="code">${esc(b.name)}</span></th><td data-label="Cases" class="num">${b.cases ?? 'Unreadable'}</td><td data-label="Restore" class="actions"><button type="button" class="btn small" data-restore="${esc(b.name)}">Restore</button></td></tr>`).join('')}
      </tbody></table></div><p class="hint">Restoring replaces the current cases with the backup, after saving the current ones in a new backup. Backups are kept on the server, in the folder its operator configured.</p>`
      : '<p class="empty">No backups yet. One is saved every time you reset or start empty.</p>'}
    </section>`;
  const reset = $('#reset');
  reset.onclick = () => confirmConsole('Reset demo data?', 'Every case is cleared and the original demo records come back. A backup is saved first, and Undo restores it.', 'Reset demo data', async () => {
    const result = await api('/api/demo/reset', {});
    CONSOLE.state = result.console;
    const saved = c.cases ? `The previous ${c.cases === 1 ? 'case is' : c.cases + ' cases are'} saved in a backup.` : 'The previous data is saved in a backup.';
    CONSOLE.last = result.reset ? { text: 'Reset. ' + saved, undo: result.backup } : { text: 'Already in the starting state. Nothing changed.' };
  });
  $('#start-empty').onclick = () => confirmConsole('Start empty?', 'Cases and records are cleared; the currency and time zone stay. A backup is saved first, and Undo restores it.', 'Start empty', async () => {
    const result = await api('/api/demo/start-empty', {});
    CONSOLE.state = result.console;
    CONSOLE.last = result.emptied ? { text: 'Emptied. Cases and records are cleared; the previous data is in a backup.', undo: result.backup } : { text: 'Already empty. Nothing changed.' };
  });
  $('#new-workspace').onclick = () => confirmConsole('New workspace?', 'Cases, records, currency and time zone are cleared; the owner sets the currency again under Setup. A backup is saved first, and Undo restores it.', 'New workspace', async () => {
    const result = await api('/api/demo/reset', { to: 'empty' });
    CONSOLE.state = result.console;
    CONSOLE.last = { text: 'New workspace. Everything is cleared, including the currency; the previous data is in a backup.', undo: result.backup };
  });
  const undo = $('#undo');
  if (undo) undo.onclick = () => restoreBackup(undo, CONSOLE.last.undo, true);
  $$('[data-restore]', main).forEach(b => { b.onclick = () => confirmConsole('Restore this backup?', 'The current cases are replaced by the backup. They are saved in a new backup first.', 'Restore', async () => restoreBackup(null, b.dataset.restore)); });
  $$('[data-copy]', main).forEach(b => { b.onclick = async () => { try { await navigator.clipboard.writeText(SAMPLES[b.dataset.copy].text); toast('Message copied', 'ok'); } catch { toast('Select the message and copy it'); } }; });
}

function confirmConsole(title, intro, label, work) {
  openDialog({ title, intro, body: '', submitLabel: label, danger: true, submit: async () => {
    try { await work(); } catch (error) { CONSOLE.last = { text: error.message, error: true }; }
    S.afterDialog = renderConsole;
    return true;
  } });
}

async function restoreBackup(button, name, undoing) {
  const run = async () => {
    try {
      const result = await api('/api/demo/restore', { backup: name });
      CONSOLE.state = result.console;
      CONSOLE.last = { text: undoing ? 'Undone. The previous cases are back.' : 'Restored. ' + caseSummary(result.console) + (result.backup ? ' The cases it replaced are in a new backup.' : '') };
    } catch (error) { CONSOLE.last = { text: error.message, error: true }; }
    renderConsole();
  };
  if (button) await busy(button, run); else await run();
}
