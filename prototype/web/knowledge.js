'use strict';
// Knowledge: short notes the agent shows the owner in requests. Staff write drafts; only notes the owner confirms are used.
// Uses core.js and customers.js helpers.

const NOTE_FILTERS = [['waiting', 'Waiting for the owner'], ['confirmed', 'Confirmed'], ['all', 'All']];

PAGES.knowledge = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('notes');
  await loadRecords();
  if (!live(seq)) return;
  if (!R.setup.settings) return renderNotReady(main);
  const notes = R.data.notes.filter(n => ['draft', 'confirmed'].includes(n.status));
  const retired = R.data.notes.filter(n => n.status === 'retired').length;
  const counts = { waiting: notes.filter(n => n.status === 'draft').length, confirmed: notes.filter(n => n.status === 'confirmed').length, all: notes.length };
  const filter = recalled('note-filter') || (isOwner() && counts.waiting ? 'waiting' : 'all');
  const shown = notes.filter(n => filter === 'all' || (filter === 'waiting' ? n.status === 'draft' : n.status === 'confirmed'));
  main.innerHTML = `${pageHead({ title: 'Knowledge', lede: 'Short notes the agent shows the owner in requests: context about a customer or the business, or a rule staff should follow. Only notes the owner has confirmed are used, and none of them change a calculation.',
      actions: '<button type="button" class="btn primary" data-act="add-note">Add a note</button>' })}
    ${isOwner() && counts.waiting ? `<p class="callout warn"><b>${plural(counts.waiting, 'draft waits', 'drafts wait')} for you to confirm.</b> Staff wrote ${counts.waiting === 1 ? 'it' : 'them'}; ${counts.waiting === 1 ? 'it isn\'t' : 'they aren\'t'} used until you confirm.</p>` : ''}
    ${!isOwner() ? '<p class="hint">Notes you add are drafts until the owner confirms them.</p>' : ''}
    <div class="filters" role="group" aria-label="Show notes">${NOTE_FILTERS.map(([k, label]) => `<button type="button" data-note-filter="${k}" aria-pressed="${k === filter}">${label}<span class="n">${counts[k]}</span></button>`).join('')}</div>
    ${shown.length ? `<ul class="notes">${shown.map(noteHtml).join('')}</ul>` : `<p class="empty">${filter === 'waiting' ? 'No drafts wait for the owner.' : 'Nothing noted yet. Notes are optional.'}</p>`}
    ${retired ? `<p class="hint">${plural(retired, 'retired note is', 'retired notes are')} kept in the history and no longer used.</p>` : ''}`;
  $$('[data-note-filter]', main).forEach(b => { b.onclick = () => { remember('note-filter', b.dataset.noteFilter); route(); }; });
  bindActions(main);
};

function noteDialog(scope) {
  const owner = isOwner();
  const options = [{ value: 'business', label: 'The whole business' }, ...customersActive().map(c => ({ value: c.id, label: `${c.name} (${c.displayCode})` }))];
  const body = `${field({ name: 'text', label: 'Note', type: 'textarea', rows: 3, attrs: 'required', hint: 'One fact or rule, in a sentence or two. The agent quotes it to the owner; it is never sent to customers.' })}
    ${selectField({ name: 'scope', label: 'About', value: scope || '', options })}
    ${radios({ name: 'kind', legend: 'Kind', value: 'context', options: [{ value: 'context', label: 'Context to know' }, { value: 'rule', label: 'A rule staff should follow', note: 'Shown to the owner. The system doesn\'t enforce it.' }] })}
    ${owner ? '<label class="tick confirm"><input type="checkbox" name="confirm"> This is correct and applies until I change it. Leave this unticked to save a draft.</label>' : '<p class="hint">Saved as a draft. It is used once the owner confirms it.</p>'}`;
  openDialog({ key: 'note:new:' + (scope || ''), title: 'Add a note', body, submitLabel: owner ? 'Save note' : 'Save draft', submit: async form => {
    if (!fval(form, 'text')) { showErrors(form, { field: 'text', message: 'Write the note.' }); return false; }
    if (!fval(form, 'scope')) { showErrors(form, { field: 'scope', message: 'Choose the whole business or one customer.' }); return false; }
    const confirmed = !!form.elements.confirm?.checked;
    const result = await dialogAction(form, '/api/records/notes', { text: fval(form, 'text'), scope: fval(form, 'scope'), kind: form.elements.kind.value, confirm: confirmed }, null,
      confirmed ? 'Note saved and confirmed' : 'Draft saved');
    if (result.error) return false;
    S.afterDialog = afterChange; return true;
  } });
}
