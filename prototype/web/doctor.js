'use strict';
// The Doctor (11 Nov 2026; docs/superpowers/specs/2026-11-11-doctor-design.md): six questions about how the Owner's setup is working, answered by code from their
// own cases (GET api/delegation/doctor). A suggestion opens Quick setup with its answers filled in (#/quick-setup?try=...); nothing is ever saved from here.
// Uses core.js helpers.

const DR = { days: '30', list: null, open: null, answer: null, seq: 0 };

function drAnswerHtml(a) {
  const list = (items, testid) => items.length ? `<ul class="home-list">${items.map(x => `<li data-testid="${testid}">${esc(x)}</li>`).join('')}</ul>` : '';
  const suggestions = a.suggestions.length ? `<h4>What would change it</h4><ul class="home-list">${a.suggestions.map(s => `<li data-testid="dr-suggestion"><p>${esc(s.text)}</p>
      ${s.answers ? `<p><a class="btn small" data-testid="dr-try" href="#/quick-setup?try=${encodeURIComponent(JSON.stringify(s.answers))}">Try this in Quick setup</a></p>` : ''}</li>`).join('')}</ul>` : '';
  // "Too few cases" is said once, as the callout: the note that carries the count, or a plain sentence when the answer has none.
  const fewNote = a.notes.find(n => n.startsWith('There are too few cases'));
  const few = a.enough ? null : (fewNote || 'There are too few cases to see a pattern yet. The counts below are everything there is.');
  const notes = a.notes.filter(n => n !== fewNote);
  return `<div class="facts-card dr-answer" data-testid="dr-answer" data-question="${esc(a.question)}" data-days="${esc(DR.days)}">
    <p data-testid="dr-headline"><b>${esc(a.headline)}</b></p>
    ${few ? `<p class="callout warn" data-testid="dr-few">${esc(few)}</p>` : ''}
    ${list(a.findings, 'dr-finding')}${suggestions}${notes.length ? `<div class="hint">${notes.map(n => `<p data-testid="dr-note">${esc(n)}</p>`).join('')}</div>` : ''}</div>`;
}

function drRender() {
  const main = $('#main');
  const assistant = assistantHref();
  const window = `<label class="dr-window">Look at <select data-testid="dr-window" id="dr-window">${[['30', 'the last 30 days'], ['90', 'the last 90 days'], ['all', 'everything']].map(([v, l]) =>
    `<option value="${v}"${v === DR.days ? ' selected' : ''}>${l}</option>`).join('')}</select></label>`;
  main.innerHTML = `<div class="page dr-page" data-testid="doctor-page">
    ${pageHead({ title: 'Doctor', lede: 'Questions about how your setup is working, answered from your own cases. Nothing here changes a setting: a suggestion opens Quick setup, where you see the effect before saving.' })}
    <p>${window}</p>
    <ol class="dr-questions">${DR.list.map(q => `<li><button type="button" class="dr-q${DR.open === q.question ? ' open' : ''}" data-testid="dr-question" data-question="${esc(q.question)}" aria-expanded="${DR.open === q.question}">
      <span class="dr-label">${esc(q.label)}</span><span class="dr-headline-short">${esc(q.headline)}</span></button>
      ${DR.open === q.question ? (DR.answer ? drAnswerHtml(DR.answer) : '<p class="muted">Working it out…</p>') : ''}</li>`).join('')}</ol>
    ${assistant ? `<p class="callout" data-testid="dr-ask">Something else? <a href="${esc(assistant)}" target="_blank" rel="noopener">Ask the assistant</a>. It explains these same figures and takes a minute or two. The numbers on this page are the ones to trust.</p>` : ''}</div>`;
  $$('[data-testid=dr-question]').forEach(b => { b.onclick = () => drOpen(DR.open === b.dataset.question ? null : b.dataset.question); });
  $('#dr-window').onchange = async e => { DR.days = e.target.value; await drLoad(); };
}

async function drOpen(question) {
  DR.open = question; DR.answer = null;
  history.replaceState(null, '', question ? '#/doctor?q=' + encodeURIComponent(question) : '#/doctor');
  drRender();
  if (!question) return;
  const seq = ++DR.seq;
  try {
    const a = await api('/api/delegation/doctor?question=' + encodeURIComponent(question) + '&days=' + encodeURIComponent(DR.days));
    if (seq !== DR.seq || !drShown()) return;
    DR.answer = a;
  } catch (error) {
    if (seq !== DR.seq || !drShown()) return;
    DR.answer = { question, headline: error.message, enough: true, findings: [], suggestions: [], notes: [] };
  }
  drRender();
}

// The Owner may have gone to another page while an answer was loading: nothing is drawn over it.
const drShown = () => S.route?.name === 'doctor' && !!$('[data-testid=doctor-page]');

async function drLoad() {
  try {
    const list = (await api('/api/delegation/doctor?days=' + encodeURIComponent(DR.days))).questions;
    if (!drShown()) return;
    DR.list = list;
  } catch (error) {
    if (drShown()) toast(error.message, 'bad');
    return;
  }
  if (DR.open) await drOpen(DR.open); else drRender();
}

PAGES.doctor = async (r, seq) => {
  const main = $('#main');
  main.innerHTML = loading('the Doctor');
  const asked = r.q?.q;
  DR.open = DR.list && asked === DR.open ? DR.open : (asked || null);
  const list = await api('/api/delegation/doctor?days=' + encodeURIComponent(DR.days));
  if (!live(seq)) return;
  DR.list = list.questions;
  if (DR.open && !DR.list.some(q => q.question === DR.open)) DR.open = null;
  if (DR.open) await drOpen(DR.open); else drRender();
};
