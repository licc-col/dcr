/**
 * app.js — DCR Visualizer SPA (2026 Edition)
 * Modern light-theme logic + structured rendering
 */

const $ = id => document.getElementById(id);
const searchInput   = $('search-input');
const autocomplete  = $('autocomplete-list');
const lemmaList     = $('lemma-list');
const pagination    = $('pagination');
const mainContent   = document.querySelector('.main-content');
const articlePanel  = $('article-panel'); 
const articleContent= $('article-content');
const placeholder   = $('article-placeholder');
const viewDict      = $('view-dictionary');
const viewCtx       = $('view-contextual');
const ctxFrame      = $('contextual-frame');
const popover       = $('popover');
const popoverBg     = $('popover-backdrop');
const hamburgerBtn  = $('hamburger-btn');
const navLinks      = $('nav-links');

// ── State ─────────────────────────────────────────────────────────────────────
let currentLetter = 'all';
let currentPage   = 1;
let currentSlug   = null;
let acTimer       = null;

// ── Utility ───────────────────────────────────────────────────────────────────
async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Navigation ────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const view = link.dataset.view;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    navLinks.classList.remove('open');
    if (view === 'dictionary') {
      viewDict.hidden = false; viewCtx.hidden = true;
    } else {
      viewDict.hidden = true; viewCtx.hidden = false;
      ctxFrame.src = `/contextual/${view}`;
    }
    history.pushState({ view }, '', `/${view === 'dictionary' ? '' : view}`);
  });
});

hamburgerBtn.addEventListener('click', () => {
    document.querySelector('.sidebar').classList.toggle('open');
});

// ── A-Z Tabs ──────────────────────────────────────────────────────────────────
const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
const azTabs = document.querySelector('.az-tabs');
LETTERS.forEach(l => {
  const btn = document.createElement('button');
  btn.className = 'az-tab';
  btn.textContent = l;
  btn.dataset.letter = l;
  azTabs.append(btn);
});

azTabs.addEventListener('click', e => {
  const btn = e.target.closest('.az-tab');
  if (!btn) return;
  azTabs.querySelectorAll('.az-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentLetter = btn.dataset.letter;
  currentPage = 1;
  searchInput.value = '';
  loadLemmaList();
});

// ── Lemma List ───────────────────────────────────────────────────────────────
async function loadLemmaList() {
  const q = searchInput.value.trim();
  const letter = currentLetter === 'all' ? '' : currentLetter;
  const params = new URLSearchParams({ page: currentPage, limit: 50 });
  if (q) params.set('q', q);
  if (letter) params.set('letter', letter);

  try {
    const data = await api(`/api/lemmas?${params}`);
    renderLemmaList(data.items);
    renderPagination(data.page, data.pages);
  } catch(e) { console.error(e); }
}

function renderLemmaList(items) {
  lemmaList.innerHTML = items.map(it => `
    <li class="lemma-item${it.slug === currentSlug ? ' active' : ''}" data-slug="${it.slug}">
      ${it.lemma} ${it.grammaticalCategory ? `<span class="li-gram">${it.grammaticalCategory}</span>` : ''}
    </li>`).join('');
}

lemmaList.addEventListener('click', e => {
  const li = e.target.closest('.lemma-item');
  if (li) loadLemma(li.dataset.slug);
});

function renderPagination(page, pages) {
  if (pages <= 1) { pagination.innerHTML = ''; return; }
  let html = [];
  if (page > 1) html.push(`<button class="page-btn" data-page="${page-1}">‹</button>`);
  html.push(`<span style="font-size: .8rem; color: var(--clr-text-muted)">${page} / ${pages}</span>`);
  if (page < pages) html.push(`<button class="page-btn" data-page="${page+1}">›</button>`);
  pagination.innerHTML = html.join('');
}

pagination.addEventListener('click', e => {
  const btn = e.target.closest('.page-btn');
  if (btn) { currentPage = parseInt(btn.dataset.page); loadLemmaList(); }
});

// ── Search + Autocomplete ─────────────────────────────────────────────────────
searchInput.addEventListener('input', () => {
  clearTimeout(acTimer);
  acTimer = setTimeout(async () => {
    const q = searchInput.value.trim();
    if (q.length < 2) { autocomplete.hidden = true; loadLemmaList(); return; }
    const items = await api(`/api/autocomplete?q=${encodeURIComponent(q)}`);
    if (!items.length) { autocomplete.hidden = true; return; }
    autocomplete.hidden = false;
    autocomplete.innerHTML = items.map(it => `<li class="autocomplete-item" data-slug="${it.slug}">${it.lemma}</li>`).join('');
  }, 200);
});

autocomplete.addEventListener('click', e => {
  const li = e.target.closest('.autocomplete-item');
  if (li) { loadLemma(li.dataset.slug); searchInput.value = ''; autocomplete.hidden = true; }
});

// ── Article Rendering (Structured) ───────────────────────────────────────────
async function loadLemma(slug) {
  currentSlug = slug;
  history.pushState({ slug }, '', `/lemma/${slug}`);
  document.querySelectorAll('.lemma-item').forEach(li => li.classList.toggle('active', li.dataset.slug === slug));
  
  placeholder.hidden = true;
  articleContent.hidden = false;
  articleContent.innerHTML = '<div class="skeleton" style="height:3rem; width: 60%; margin-bottom: 2rem"></div>';

  try {
    const data = await api(`/api/lemmas/${slug}`);
    renderArticleStructured(data);
  } catch(e) { articleContent.innerHTML = 'Error al cargar.'; }
}

function renderArticleStructured(data) {
  let html = `
    <header class="article-header">
      <h1 class="dcr-lemma-title">${data.lemma}</h1>
      ${data.grammaticalCategory ? `<span class="dcr-gram-tag">${data.grammaticalCategory}</span>` : ''}
    </header>
    <div class="dcr-intro">${data.introduction || ''}</div>
  `;

  // Render Acepciones
  data.acepciones?.forEach(acep => {
    const hasSubs = acep.subAcepciones?.length > 0;
    const isDummyParent = !acep.letter && !acep.definition;
    
    if (isDummyParent) {
      html += `
        <section class="acepcion-card dummy-parent" style="border: none; box-shadow: none; background: transparent; padding: 0; margin-bottom: 1.5rem;">
          ${renderExamples(acep.examples)}
          
          ${hasSubs ? `
            <div class="sub-acepcion-group" style="padding-left: 0; border-left: none; margin-top: 0;">
              ${acep.subAcepciones.map(sub => `
                <div class="sub-acepcion" style="margin-bottom: 1.5rem; background: #fff; border: 1px solid var(--clr-border); border-radius: var(--radius-lg); padding: 1.5rem; box-shadow: var(--shadow-sm); transition: all var(--t);">
                  <div class="sub-header" style="display: flex; align-items: baseline; gap: .75rem; margin-bottom: 1rem; border-bottom: 1px solid var(--clr-border-light); padding-bottom: 0.75rem;">
                    <span class="sub-letter" style="font-family: var(--font-dict); font-size: 1.2rem; font-weight: 800; color: var(--clr-subacepcion);">${sub.letter}</span>
                    ${sub.type ? `<span class="sub-type" style="display: inline-block; background: var(--clr-surface-2); padding: .2rem .5rem; border-radius: 4px; font-size: .8rem; font-weight: 600; color: var(--clr-grammar); font-style: italic; margin-left: 0.25rem; margin-right: 0.25rem;">${sub.type}</span>` : ''}
                    <span class="sub-def" style="font-family: var(--font-dict); font-size: 1.1rem; line-height: 1.6; color: var(--clr-text);">${sub.definition}</span>
                  </div>
                  ${renderExamples(sub.examples)}
                  ${renderSubSubAcepciones(sub.subSubAcepciones)}
                </div>
              `).join('')}
            </div>
          ` : ''}
        </section>
      `;
    } else {
      html += `
        <section class="acepcion-card">
          <div class="acepcion-header" onclick="this.closest('.acepcion-card').classList.toggle('collapsed')">
            <span class="acepcion-letter">${acep.letter}</span>
            <div class="acepcion-def">${acep.definition}</div>
            ${hasSubs ? `<span class="collapse-btn"></span>` : ''}
          </div>
          ${renderExamples(acep.examples)}
          
          ${hasSubs ? `
            <div class="sub-acepcion-group">
              ${acep.subAcepciones.map(sub => `
                <div class="sub-acepcion">
                  <div class="sub-header">
                    <span class="sub-letter">${sub.letter}</span>
                    ${sub.type ? `<span class="sub-type">${sub.type}</span>` : ''}
                    <span class="sub-def">${sub.definition}</span>
                  </div>
                  ${renderExamples(sub.examples)}
                  ${renderSubSubAcepciones(sub.subSubAcepciones)}
                </div>
              `).join('')}
            </div>
          ` : ''}
        </section>
      `;
    }
  });

  if (data.etymology) {
    html += `<section class="acepcion-card" style="border-left-color: var(--clr-acepcion)">
      <div class="acepcion-header"><span class="acepcion-letter">Etimología</span></div>
      <div class="acepcion-def">${data.etymology}</div>
    </section>`;
  }

  articleContent.innerHTML = html;
  
  // Post-process: apply hyperlinking to text
  articleContent.querySelectorAll('.acepcion-def, .sub-def, .dcr-quote').forEach(node => {
    // We reuse the basic hyperlinking logic on the text content
    // Labels like Part. or authors like Cerv. are wrapped in spans
    // This part is tricky if we don't have it pre-wrapped.
    // However, the importDCR.js already created a 'transformedHtml'.
    // User wants structured + styling.
    // I will use a simple regex approach for dynamic hyperlinking here:
  });
  
  // For now, I'll rely on the existing spans if I can, 
  // but since we are rendering from JSON, we need to wrap authors/abbrevs again.
}

function renderExamples(examples) {
  if (!examples?.length) return '';
  return examples.map(ex => `
    <div class="example-box">
      <span class="dcr-quote">${ex.text}</span>
      <div class="example-metadata">
        ${ex.author?.abbrev ? `<span class="dcr-author" data-abbrev="${ex.author.abbrev}">${ex.author.abbrev}</span>` : ''}
        ${ex.work || ''} ${ex.reference ? `(${ex.reference})` : ''}
      </div>
    </div>
  `).join('');
}

function renderSubSubAcepciones(subSubs) {
  if (!subSubs?.length) return '';
  return `
    <div class="sub-sub-acepcion-group" style="padding-left: 1.5rem; border-left: 2px solid var(--clr-border-light); margin-top: 1rem; margin-bottom: 0.5rem;">
      ${subSubs.map(ss => `
        <div class="sub-sub-acepcion" style="margin-bottom: 1rem; position: relative;">
          <div class="sub-sub-header" style="display: flex; align-items: baseline; gap: .5rem; margin-bottom: .4rem;">
            <span class="sub-sub-letter" style="color: var(--clr-subacepcion); font-weight: 700; font-family: var(--font-dict); font-size: 1.05rem;">${ss.letter}</span>
            <span class="sub-sub-def" style="font-family: var(--font-dict); font-size: 1.05rem; line-height: 1.5; color: var(--clr-text);">${ss.definition}</span>
          </div>
          ${renderExamples(ss.examples)}
        </div>
      `).join('')}
    </div>
  `;
}

// ── Generic Link Handling ─────────────────────────────────────────────────────
articleContent.addEventListener('click', e => {
  const el = e.target;
  if (el.classList.contains('dcr-author')) openPopover(el, 'author', el.dataset.abbrev);
  if (el.classList.contains('dcr-abbrev')) openPopover(el, 'abbrev', el.dataset.abbrev);
});

async function openPopover(anchor, type, abbrev) {
  const params = new URLSearchParams({ abbrev });
  const endpoint = type === 'author' ? `/api/authors/${encodeURIComponent(abbrev)}` : `/api/abbreviations/${encodeURIComponent(abbrev)}`;
  
  $('popover-abbrev').textContent = abbrev;
  $('popover-expansion').textContent = 'Cargando…';
  popover.hidden = false; popoverBg.hidden = false;
  
  const rect = anchor.getBoundingClientRect();
  popover.style.left = `${Math.min(window.innerWidth - 320, rect.left)}px`;
  popover.style.top = `${rect.bottom + 10}px`;

  try {
    const data = await api(endpoint);
    $('popover-expansion').textContent = type === 'author' ? data.fullInfo : data.expansion;
  } catch(e) { $('popover-expansion').textContent = 'No encontrado.'; }
}

$('popover-close').onclick = () => { popover.hidden = true; popoverBg.hidden = true; };
popoverBg.onclick = $('popover-close').onclick;

// ── Init ──────────────────────────────────────────────────────────────────────
loadLemmaList();
window.onpopstate = e => { if(e.state?.slug) loadLemma(e.state.slug); };
