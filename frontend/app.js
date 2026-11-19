/* ═══════════════════════════════════════════════════════
   CONFIG
═══════════════════════════════════════════════════════ */
const API_URL = location.port === '3000' ? 'http://localhost:8000' : '/api';

/* ═══════════════════════════════════════════════════════
   AUTH
═══════════════════════════════════════════════════════ */
const auth = {
  token:      () => localStorage.getItem('mlgr_token'),
  setToken:   (t) => localStorage.setItem('mlgr_token', t),
  clearToken: () => localStorage.removeItem('mlgr_token'),
  user:       () => { try { return JSON.parse(localStorage.getItem('mlgr_user')); } catch { return null; } },
  setUser:    (u) => localStorage.setItem('mlgr_user', JSON.stringify(u)),
  clearUser:  () => localStorage.removeItem('mlgr_user'),
  guard: () => {
    if (!auth.token()) { window.location.href = 'auth.html'; }
  },
  logout: async () => {
    try { await req('DELETE', '/auth/logout'); } catch { /* ignore */ }
    auth.clearToken();
    auth.clearUser();
    window.location.href = 'index.html';
  },
};

/* ═══════════════════════════════════════════════════════
   HTTP CLIENT
═══════════════════════════════════════════════════════ */
async function req(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth.token()) headers['Authorization'] = `Bearer ${auth.token()}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) { auth.clearToken(); auth.clearUser(); window.location.href = 'index.html'; return; }
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(Array.isArray(err.detail) ? err.detail[0]?.msg : (err.detail || 'Помилка сервера'));
  }
  return res.json();
}

async function download(path, filename) {
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${auth.token()}` } });
  if (!res.ok) throw new Error('Не вдалось скачати файл');
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement('a'), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

/* ═══════════════════════════════════════════════════════
   TOAST
═══════════════════════════════════════════════════════ */
function toast(msg, type = 'ok') {
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) { wrap = Object.assign(document.createElement('div'), { className: 'toast-wrap' }); document.body.appendChild(wrap); }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="t-dot"></span><span>${msg}</span>`;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3400);
}

/* ═══════════════════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════════════════ */
function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' });
}
function initials(email) { return (email || '?')[0].toUpperCase(); }
const ICONS = {
  file:     '<svg class="icon" viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>',
  download: '<svg class="icon" viewBox="0 0 24 24"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>',
  trash:    '<svg class="icon" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>',
  image:    '<svg class="icon" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>',
  plus:     '<svg class="icon" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  minus:    '<svg class="icon" viewBox="0 0 24 24"><path d="M5 12h14"/></svg>',
  x:        '<svg class="icon" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  up:       '<svg class="icon" viewBox="0 0 24 24"><path d="m6 15 6-6 6 6"/></svg>',
  down:     '<svg class="icon" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>',
  undo:     '<svg class="icon" viewBox="0 0 24 24"><path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/></svg>',
  redo:     '<svg class="icon" viewBox="0 0 24 24"><path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/></svg>',
  code:     '<svg class="icon" viewBox="0 0 24 24"><path d="m8 7-5 5 5 5M16 7l5 5-5 5"/></svg>',
  edit:     '<svg class="icon" viewBox="0 0 24 24"><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  eye:      '<svg class="icon" viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
};
function esc(s) { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function setLoading(btn, on) {
  if (on) { btn._html = btn.innerHTML; btn.innerHTML = '<span class="spinner"></span>'; btn.disabled = true; }
  else     { btn.innerHTML = btn._html; btn.disabled = false; }
}

function fillSidebar() {
  const u = auth.user();
  const emailEl = document.getElementById('sb-email');
  const avaEl   = document.getElementById('sb-avatar');
  if (emailEl) emailEl.textContent = u?.email ?? '';
  if (avaEl)   avaEl.textContent   = initials(u?.email);
  document.getElementById('sb-logout')?.addEventListener('click', auth.logout);
}

/* ═══════════════════════════════════════════════════════
   PAGE: AUTH  (index.html)
═══════════════════════════════════════════════════════ */
function initAuth() {
  if (auth.token()) { window.location.href = 'dashboard.html'; return; }

  // відкрити таб реєстрації якщо прийшли з лендінгу з ?tab=register
  const startTab = new URLSearchParams(window.location.search).get('tab');

  const tabs        = document.querySelectorAll('.tab-btn');
  const loginForm   = document.getElementById('form-login');
  const regForm     = document.getElementById('form-register');

  if (startTab === 'register') {
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === 'register'));
    loginForm.classList.add('hidden');
    regForm.classList.remove('hidden');
  }

  tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    const isLogin = t.dataset.tab === 'login';
    loginForm.classList.toggle('hidden', !isLogin);
    regForm.classList.toggle('hidden', isLogin);
  }));

  loginForm?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = loginForm.querySelector('[type=submit]');
    const err = document.getElementById('login-err');
    err.classList.add('hidden');
    setLoading(btn, true);
    try {
      const data = await req('POST', '/auth/login', {
        email:    document.getElementById('login-email').value,
        password: document.getElementById('login-pass').value,
      });
      auth.setToken(data.access_token);
      auth.setUser(data.user);
      window.location.href = 'dashboard.html';
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.remove('hidden');
      setLoading(btn, false);
    }
  });

  regForm?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = regForm.querySelector('[type=submit]');
    const err = document.getElementById('reg-err');
    err.classList.add('hidden');
    setLoading(btn, true);
    try {
      const data = await req('POST', '/auth/register', {
        email:    document.getElementById('reg-email').value,
        password: document.getElementById('reg-pass').value,
      });
      auth.setToken(data.access_token);
      auth.setUser(data.user);
      window.location.href = 'dashboard.html';
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.remove('hidden');
      setLoading(btn, false);
    }
  });
}

/* ═══════════════════════════════════════════════════════
   PAGE: DASHBOARD  (dashboard.html)
═══════════════════════════════════════════════════════ */
let allReports   = [];
let currentView  = 'reports'; // 'reports' | 'disciplines'
let activeDisc   = null;      // null = all, string = filtered by discipline

async function initDashboard() {
  auth.guard();
  fillSidebar();

  document.getElementById('btn-new')?.addEventListener('click', () => { window.location.href = 'editor.html'; });

  document.getElementById('nav-reports')?.addEventListener('click', e => {
    e.preventDefault();
    activeDisc = null;
    switchView('reports');
  });

  document.getElementById('nav-discs')?.addEventListener('click', e => {
    e.preventDefault();
    switchView('disciplines');
  });

  document.getElementById('btn-back-disc')?.addEventListener('click', () => {
    activeDisc = null;
    switchView('disciplines');
  });

  const searchInput = document.getElementById('search-input');
  searchInput?.addEventListener('input', () => renderGrid(searchInput.value));

  await loadReports();
}

function switchView(view) {
  currentView = view;
  const reportsSection = document.getElementById('reports-section');
  const discSection    = document.getElementById('disc-section');
  const backBtn        = document.getElementById('btn-back-disc');
  const titleEl        = document.getElementById('page-title');
  const subtitleEl     = document.getElementById('page-subtitle');

  document.getElementById('nav-reports')?.classList.toggle('active', view === 'reports');
  document.getElementById('nav-discs')?.classList.toggle('active', view === 'disciplines');

  if (view === 'disciplines') {
    reportsSection?.classList.add('hidden');
    discSection?.classList.remove('hidden');
    backBtn?.classList.add('hidden');
    if (titleEl)    titleEl.textContent    = 'Дисципліни';
    if (subtitleEl) subtitleEl.textContent = 'Звіти, згруповані за дисциплінами';
    renderDiscGrid();
  } else {
    reportsSection?.classList.remove('hidden');
    discSection?.classList.add('hidden');
    if (activeDisc) {
      backBtn?.classList.remove('hidden');
      if (titleEl)    titleEl.textContent    = activeDisc;
      if (subtitleEl) subtitleEl.textContent = 'Звіти з цієї дисципліни';
    } else {
      backBtn?.classList.add('hidden');
      if (titleEl)    titleEl.textContent    = 'Мої звіти';
      if (subtitleEl) subtitleEl.textContent = 'Усі звіти, від нових до старих';
    }
    renderGrid(document.getElementById('search-input')?.value ?? '');
  }
}

function renderDiscGrid() {
  const grid = document.getElementById('disc-grid');
  if (!grid) return;

  const map = {};
  allReports.forEach(r => {
    const d = r.discipline || 'Без дисципліни';
    (map[d] = map[d] || []).push(r);
  });

  const entries = Object.entries(map).sort((a, b) => b[1].length - a[1].length);

  if (!entries.length) {
    grid.innerHTML = `<div class="empty-state"><h3>Дисциплін поки немає</h3><p>Вони з'являться, щойно ви створите перший звіт.</p></div>`;
    return;
  }

  grid.innerHTML = entries.map(([disc, reports]) => {
    const latest  = [...reports].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
    const n       = reports.length;
    const label   = n === 1 ? 'звіт' : n < 5 ? 'звіти' : 'звітів';
    return `
    <div class="card card-hover disc-card" data-disc="${esc(disc)}">
      <div class="dc-name">${esc(disc)}</div>
      <div class="dc-count">${n} ${label}</div>
      <div class="dc-date">останній — ${fmtDate(latest.created_at)}</div>
    </div>`;
  }).join('');

  grid.querySelectorAll('.disc-card').forEach(card => {
    card.addEventListener('click', () => {
      activeDisc = card.dataset.disc;
      switchView('reports');
    });
  });
}

async function loadReports() {
  const grid = document.getElementById('reports-grid');
  try {
    allReports = await req('GET', '/reports');
    updateStats();
    renderGrid();
  } catch (ex) {
    grid.innerHTML = `<div class="error-box">Не вдалось завантажити звіти: ${esc(ex.message)}</div>`;
  }
}

function updateStats() {
  const now   = new Date();
  const month = allReports.filter(r => new Date(r.created_at).getMonth() === now.getMonth()).length;
  const discs = new Set(allReports.map(r => r.discipline).filter(Boolean)).size;
  const totalEl = document.getElementById('stat-total');
  const monthEl = document.getElementById('stat-month');
  const discEl  = document.getElementById('stat-discs');
  if (totalEl) totalEl.textContent = allReports.length;
  if (monthEl) monthEl.textContent = month;
  if (discEl)  discEl.textContent  = discs;
}

function renderGrid(query = '') {
  const grid = document.getElementById('reports-grid');
  const q    = query.toLowerCase();
  let list   = activeDisc
    ? allReports.filter(r => (r.discipline || 'Без дисципліни') === activeDisc)
    : allReports;
  if (q) list = list.filter(r => r.title?.toLowerCase().includes(q) || r.discipline?.toLowerCase().includes(q));

  if (!list.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <h3>${q ? 'Нічого не знайдено' : 'Звітів поки немає'}</h3>
        <p>${q ? 'Спробуйте інший запит.' : 'Створіть перший — кнопка «Новий звіт» угорі праворуч.'}</p>
      </div>`;
    return;
  }

  const sorted = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  grid.innerHTML = sorted.map(r => `
    <div class="report-card card-hover" data-id="${r.id}">
      <div class="rc-icon">${ICONS.file}</div>
      <div class="rc-title">${esc(r.title || 'Без назви')}</div>
      <div class="rc-meta">
        <span class="badge">${esc(r.discipline || 'Без дисципліни')}</span>
        ${r.group   ? `<span>${esc(r.group)}</span>` : ''}
        ${r.teacher ? `<span class="dot-sep">${esc(r.teacher)}</span>` : ''}
        <span class="dot-sep">${fmtDate(r.created_at)}</span>
      </div>
      <div class="rc-actions">
        <button class="btn btn-sm btn-ghost"  data-action="view" title="Переглянути">${ICONS.eye}</button>
        <button class="btn btn-sm btn-ghost"  data-action="dl"  title="Завантажити .docx">${ICONS.download}</button>
        <button class="btn btn-sm btn-danger" data-action="del" title="Видалити">${ICONS.trash}</button>
      </div>
    </div>`).join('');

  grid.querySelectorAll('.report-card').forEach(card => {
    const id = parseInt(card.dataset.id);
    card.addEventListener('click', e => {
      const action = e.target.closest('[data-action]')?.dataset.action;
      if (!action) { window.location.href = `editor.html?id=${id}`; return; }
      if (action === 'del') deleteReport(id);
      if (action === 'dl')  downloadDocx(id);
      if (action === 'view') openPreview(id, allReports.find(r => r.id === id)?.title, { onClose: changed => changed && loadReports() });
    });
  });
}

async function deleteReport(id) {
  if (!confirm('Видалити цей звіт назавжди?')) return;
  try {
    await req('DELETE', `/reports/${id}`);
    allReports = allReports.filter(r => r.id !== id);
    updateStats();
    renderGrid(document.getElementById('search-input')?.value);
    toast('Звіт видалено');
  } catch (ex) { toast(ex.message, 'err'); }
}

async function downloadDocx(id) {
  const title = allReports.find(r => r.id === id)?.title;
  try {
    toast('Складаємо документ…');
    await runGeneration(id);
    await download(`/reports/${id}/download`, fileName(title, 'docx'));
  } catch (ex) { toast(ex.message, 'err'); }
}

/* ═══════════════════════════════════════════════════════
   PAGE: EDITOR  (editor.html)
═══════════════════════════════════════════════════════ */
let reportId     = null;
let sections     = [];
let sse_conc     = null;
let reportImages = [];                          // [{id, url, caption, section_path}]
const genders    = { student: 'm', teacher: 'f' };

async function initEditor() {
  auth.guard();
  fillSidebar();

  ['btn-add-sec', 'btn-add-sec-bottom', 'btn-add-sec-side'].forEach(id =>
    document.getElementById(id)?.addEventListener('click', addSection));
  document.getElementById('btn-save')?.addEventListener('click', () => saveReport());
  document.getElementById('btn-conclusion')?.addEventListener('click', streamConclusion);
  document.getElementById('btn-generate')?.addEventListener('click', generateDocx);
  document.getElementById('btn-preview')?.addEventListener('click', previewReport);

  document.querySelectorAll('.seg[data-gender]').forEach(seg => seg.addEventListener('click', e => {
    const g = e.target.closest('[data-g]')?.dataset.g;
    if (g) setGender(seg.dataset.gender, g);
  }));
  setGender('student', 'm');
  setGender('teacher', 'f');

  ['f-title', 'f-discipline', 'f-group', 'f-student', 'f-teacher', 'f-goal', 'ai-output'].forEach(id =>
    document.getElementById(id)?.addEventListener('input', updateReadiness));

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && !document.querySelector('.pv')) {
      e.preventDefault();
      saveReport();
    }
  });

  const params = new URLSearchParams(window.location.search);
  reportId = params.get('id') ? parseInt(params.get('id')) : null;

  if (reportId) {
    document.getElementById('editor-heading').textContent = 'Редагування звіту';
    await loadReport(reportId);
  } else {
    sections = [];
    renderSections();
  }
}

function setGender(who, g) {
  genders[who] = g;
  document.querySelectorAll(`.seg[data-gender="${who}"] [data-g]`).forEach(b => {
    const on = b.dataset.g === g;
    b.classList.toggle('on', on);
    b.setAttribute('aria-checked', on);
  });
}

async function loadReport(id) {
  try {
    const [r, imgs] = await Promise.all([
      req('GET', `/reports/${id}`),
      req('GET', `/reports/${id}/images`).catch(() => []),
    ]);
    document.getElementById('f-title').value      = r.title        || '';
    document.getElementById('f-discipline').value = r.discipline   || '';
    document.getElementById('f-teacher').value    = r.teacher      || '';
    document.getElementById('f-student').value    = r.student_name || '';
    document.getElementById('f-group').value      = r.group        || '';
    document.getElementById('f-goal').value       = r.goal         || '';
    setGender('student', r.student_gender || 'm');
    setGender('teacher', r.teacher_gender || 'f');

    sections = toEditableSections(r.sections);
    reportImages = imgs || [];
    renderSections();

    document.getElementById('ai-output').value = r.conclusion || '';
    updateReadiness();
  } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
}

function toEditableSections(raw) {
  const toBlock = (s, i) => ({
    id: i, title: s.title || '', text: s.text || '', code: s.code || '', language: s.language || 'python',
  });
  return (raw || []).map((s, i) => ({ ...toBlock(s, i), subsections: (s.subsections || []).map(toBlock) }));
}

function sectionsPayload(list) {
  const pick = b => ({ title: b.title, text: b.text, code: b.code, language: b.language });
  return list.map(s => ({ ...pick(s), subsections: (s.subsections || []).map(pick) }));
}

/* ── image paths follow their sections when the structure changes ── */
// mapPath("1.0") → new path, or null when the image's section is gone
const pathMaps = {
  removeSection: i => p => {
    const [a, b] = p.split('.').map(Number);
    if (a === i) return null;
    return a > i ? [a - 1, b].filter(x => x !== undefined).join('.') : p;
  },
  removeSubsection: (i, j) => p => {
    const [a, b] = p.split('.').map(Number);
    if (a !== i || b === undefined) return p;
    if (b === j) return null;
    return b > j ? `${a}.${b - 1}` : p;
  },
  swapSections: (i, k) => p => {
    const [a, ...rest] = p.split('.');
    const n = Number(a);
    return n === i ? [k, ...rest].join('.') : n === k ? [i, ...rest].join('.') : p;
  },
};

async function remapImages(id, images, mapPath) {
  const kept = [];
  for (const img of images) {
    const next = mapPath(img.section_path);
    try {
      if (next === null) { await req('DELETE', `/reports/${id}/images/${img.id}`); continue; }
      if (next !== img.section_path) await req('PATCH', `/reports/${id}/images/${img.id}`, { section_path: next });
    } catch (ex) { toast('Не вдалося оновити зображення: ' + ex.message, 'err'); }
    kept.push({ ...img, section_path: next ?? img.section_path });
  }
  return kept;
}

const hasContent = b => Boolean(b.title?.trim() || b.text?.trim() || b.code?.trim() || b.subsections?.length);

/* ── sections ── */
// path: "0" — section, "0.1" — its subsection (same format the backend stores for images)
function blockAt(path) {
  const [i, j] = String(path).split('.').map(Number);
  return j === undefined ? sections[i] : sections[i].subsections[j];
}

function newBlock() {
  return { id: Date.now(), title: '', text: '', code: '', language: 'python' };
}

function addSection() {
  sections.push({ ...newBlock(), subsections: [] });
  renderSections();
  const last = document.querySelectorAll('#sections-container > .section-item');
  last[last.length - 1]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  last[last.length - 1]?.querySelector('.sec-name')?.focus({ preventScroll: true });
}

async function structureChanged(mapPath) {
  renderSections();
  if (!reportId) return;
  reportImages = await remapImages(reportId, reportImages, mapPath);
  renderSections();
  await saveReport({ quiet: true });   // images are already moved on the server — keep sections in step
}

async function removeSection(idx) {
  if (hasContent(sections[idx]) && !confirm(`Видалити розділ ${idx + 1} разом із його вмістом і скріншотами?`)) return;
  sections.splice(idx, 1);
  await structureChanged(pathMaps.removeSection(idx));
}

async function moveSection(idx, dir) {
  const k = idx + dir;
  if (k < 0 || k >= sections.length) return;
  [sections[idx], sections[k]] = [sections[k], sections[idx]];
  await structureChanged(pathMaps.swapSections(idx, k));
}

function addSubsection(i) {
  sections[i].subsections.push(newBlock());
  renderSections();
  const el = document.getElementById(`sec-${i}-${sections[i].subsections.length - 1}`);
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el?.querySelector('.sec-name')?.focus({ preventScroll: true });
}

async function removeSubsection(i, j) {
  if (hasContent(sections[i].subsections[j]) && !confirm(`Видалити підрозділ ${i + 1}.${j + 1}?`)) return;
  sections[i].subsections.splice(j, 1);
  await structureChanged(pathMaps.removeSubsection(i, j));
}

function setBlockTitle(path, value) {
  blockAt(path).title = value;
  renderOutline();
  updateReadiness();
}

const LANGS = ['python','javascript','typescript','java','cpp','c','sql','bash','html','css'];

function blockFieldsHtml(path, block, kind) {
  const id = String(path).replace('.', '-');
  return `
        <div class="form-group">
          <label>Текст ${kind}</label>
          <textarea rows="4" placeholder="Що було зроблено, які результати отримано"
                    oninput="blockAt('${path}').text = this.value; updateReadiness()">${esc(block.text)}</textarea>
        </div>
        <div class="form-group">
          <label>Код <span class="text-muted">— якщо є</span></label>
          <div class="code-wrap">
            <div class="code-head">
              <select class="lang-select" onchange="blockAt('${path}').language = this.value">
                ${LANGS.map(l => `<option value="${l}" ${block.language === l ? 'selected' : ''}>${l}</option>`).join('')}
              </select>
            </div>
            <textarea spellcheck="false" placeholder="Вставте код" oninput="blockAt('${path}').code = this.value">${esc(block.code)}</textarea>
          </div>
        </div>
        <div class="form-group">
          <label>Скріншоти <span class="text-muted">— якщо є</span></label>
          <div class="upload-zone" onclick="triggerUpload('${path}')"
               ondragover="event.preventDefault(); this.classList.add('drag')"
               ondragleave="this.classList.remove('drag')"
               ondrop="handleDrop(event,'${path}'); this.classList.remove('drag')">
            ${ICONS.image} Перетягніть зображення або натисніть, щоб вибрати
          </div>
          <input type="file" id="fu-${id}" accept="image/*" multiple style="display:none"
                 onchange="handleFileInput(this, '${path}')">
          <div class="img-grid" id="imgs-${id}"></div>
        </div>`;
}

function renderSections() {
  const container = document.getElementById('sections-container');
  if (!container) return;

  if (!sections.length) {
    container.innerHTML = '<p class="text-sm text-muted" style="text-align:center;padding:14px 0">Розділів ще немає. Додайте перший — наприклад, «Хід роботи».</p>';
  } else {
    container.innerHTML = sections.map((sec, i) => `
    <div class="section-item" id="sec-${i}">
      <div class="section-head">
        <span class="sec-num">${i + 1}</span>
        <input class="sec-name" placeholder="Назва розділу..."
               value="${esc(sec.title)}" oninput="setBlockTitle('${i}', this.value)">
        <button class="btn btn-ghost btn-sm" onclick="removeSection(${i})" title="Видалити розділ">${ICONS.trash}</button>
      </div>
      <div class="section-body">
        ${blockFieldsHtml(`${i}`, sec, 'розділу')}
        ${sec.subsections.map((sub, j) => `
        <div class="section-item subsection-item" id="sec-${i}-${j}">
          <div class="section-head">
            <span class="sec-num">${i + 1}.${j + 1}</span>
            <input class="sec-name" placeholder="Назва підрозділу..."
                   value="${esc(sub.title)}" oninput="setBlockTitle('${i}.${j}', this.value)">
            <button class="btn btn-ghost btn-sm" onclick="removeSubsection(${i},${j})" title="Видалити підрозділ">${ICONS.trash}</button>
          </div>
          <div class="section-body">
            ${blockFieldsHtml(`${i}.${j}`, sub, 'підрозділу')}
          </div>
        </div>`).join('')}
        <div><button class="btn btn-ghost btn-sm" onclick="addSubsection(${i})">${ICONS.plus} Підрозділ ${i + 1}.${sec.subsections.length + 1}</button></div>
      </div>
    </div>`).join('');
    reportImages.forEach(img => appendThumb(img.section_path, img.url, img.id));
  }
  renderOutline();
  updateReadiness();
}

/* ── right panel: outline + readiness ── */
function renderOutline() {
  const nav = document.getElementById('outline');
  if (!nav) return;
  if (!sections.length) {
    nav.innerHTML = '<p class="outline-empty">Тут з\'явиться зміст звіту. Розділи можна додавати звідси, не прокручуючи сторінку.</p>';
    return;
  }
  const n = sections.length;
  nav.innerHTML = sections.map((s, i) => `
    <div class="ol-item">
      <a href="#sec-${i}" class="ol-link" data-target="sec-${i}">
        <span class="ol-num">${i + 1}</span>
        <span class="ol-title ${s.title.trim() ? '' : 'untitled'}">${esc(s.title.trim() || 'Без назви')}</span>
      </a>
      <span class="ol-actions">
        <button class="pv-icon-btn" title="Вище" ${i === 0 ? 'disabled' : ''} onclick="moveSection(${i},-1)">${ICONS.up}</button>
        <button class="pv-icon-btn" title="Нижче" ${i === n - 1 ? 'disabled' : ''} onclick="moveSection(${i},1)">${ICONS.down}</button>
        <button class="pv-icon-btn" title="Додати підрозділ" onclick="addSubsection(${i})">${ICONS.plus}</button>
      </span>
    </div>
    ${s.subsections.map((sub, j) => `
    <a href="#sec-${i}-${j}" class="ol-link ol-sub" data-target="sec-${i}-${j}">
      <span class="ol-num">${i + 1}.${j + 1}</span>
      <span class="ol-title ${sub.title.trim() ? '' : 'untitled'}">${esc(sub.title.trim() || 'Без назви')}</span>
    </a>`).join('')}`).join('');

  nav.querySelectorAll('.ol-link').forEach(a => a.onclick = e => {
    e.preventDefault();
    const el = document.getElementById(a.dataset.target);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el?.querySelector('.sec-name')?.focus({ preventScroll: true });
  });
}

function updateReadiness() {
  const val = id => document.getElementById(id)?.value.trim();
  const checks = [
    ['Назва роботи',  () => val('f-title'),      'f-title'],
    ['Дисципліна',    () => val('f-discipline'), 'f-discipline'],
    ['Група',         () => val('f-group'),      'f-group'],
    ['Студент',       () => val('f-student'),    'f-student'],
    ['Викладач',      () => val('f-teacher'),    'f-teacher'],
    ['Мета',          () => val('f-goal'),       'f-goal'],
    ['Хоча б один розділ з текстом', () => sections.some(s => s.text.trim() || s.subsections.some(b => b.text.trim())), 'btn-add-sec'],
    ['Назви всіх розділів', () => sections.length && sections.every(s => s.title.trim() && s.subsections.every(b => b.title.trim())), 'sections-container'],
    ['Висновки',      () => val('ai-output'),    'ai-output'],
  ];
  const missing = checks.filter(([, ok]) => !ok());
  const done = checks.length - missing.length;
  const valEl = document.getElementById('readiness-val');
  if (!valEl) return;
  valEl.textContent = `${done} / ${checks.length}`;
  document.getElementById('readiness-fill').style.width = `${(done / checks.length) * 100}%`;
  const box = document.getElementById('readiness-missing');
  box.innerHTML = missing.length
    ? missing.map(([label, , target]) => `<button class="chip" data-target="${target}">${esc(label)}</button>`).join('')
    : '<span class="text-sm ready-ok">Усе заповнено — можна завантажувати</span>';
  box.querySelectorAll('.chip').forEach(c => c.onclick = () => {
    const el = document.getElementById(c.dataset.target);
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (el?.matches('input, textarea')) el.focus({ preventScroll: true });
  });
}

/* ── file upload ── */
function triggerUpload(path) { document.getElementById(`fu-${String(path).replace('.', '-')}`)?.click(); }

async function handleDrop(e, i) {
  e.preventDefault();
  const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
  await uploadFiles(files, i);
}

async function handleFileInput(input, i) {
  await uploadFiles(Array.from(input.files), i);
  input.value = '';
}

// Uploads to the server and returns the created images ({id, url, caption, section_path})
async function uploadImages(id, files, sectionPath) {
  const created = [];
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('report_id', id);
    fd.append('section_path', sectionPath);
    try {
      const res = await fetch(`${API_URL}/upload/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token()}` },
        body: fd,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      created.push({ id: data.id, url: data.url, section_path: String(sectionPath),
                     caption: `Зображення ${String(sectionPath).split('.').map(n => Number(n) + 1).join('.')}` });
    } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
  }
  return created;
}

async function uploadFiles(files, sectionPath) {
  if (!reportId) { toast('Спершу збережіть звіт — тоді можна додавати скріншоти', 'err'); return; }
  const created = await uploadImages(reportId, files, sectionPath);
  reportImages.push(...created);
  created.forEach(img => appendThumb(img.section_path, img.url, img.id));
}

function appendThumb(path, url, imgId) {
  const grid = document.getElementById(`imgs-${String(path).replace('.', '-')}`);
  if (!grid) return;
  const div = document.createElement('div');
  div.className = 'img-thumb';
  div.dataset.imgId = imgId;
  div.innerHTML = `<img src="${API_URL}${url}" alt="скріншот"><button class="rm" title="Видалити" onclick="removeThumb(this)">✕</button>`;
  grid.appendChild(div);
}

async function removeThumb(btn) {
  const thumb = btn.closest('.img-thumb');
  const imgId = Number(thumb.dataset.imgId);
  try {
    await req('DELETE', `/reports/${reportId}/images/${imgId}`);
    reportImages = reportImages.filter(i => i.id !== imgId);
    thumb.remove();
  } catch (ex) { toast('Не вдалося видалити: ' + ex.message, 'err'); }
}

/* ── save ── */
async function saveReport({ quiet = false } = {}) {
  const btn = document.getElementById('btn-save');
  if (!quiet) setLoading(btn, true);

  const payload = {
    title:          document.getElementById('f-title').value,
    discipline:     document.getElementById('f-discipline').value,
    teacher:        document.getElementById('f-teacher').value,
    teacher_gender: genders.teacher,
    student_name:   document.getElementById('f-student').value,
    student_gender: genders.student,
    group:          document.getElementById('f-group').value,
    goal:           document.getElementById('f-goal').value,
    conclusion:     document.getElementById('ai-output').value,
    sections:       sectionsPayload(sections),
  };

  try {
    if (reportId) {
      await req('PATCH', `/reports/${reportId}`, payload);
      if (!quiet) toast('Збережено');
    } else {
      const r = await req('POST', '/reports', payload);
      reportId = r.id;
      window.history.replaceState({}, '', `editor.html?id=${reportId}`);
      document.getElementById('editor-heading').textContent = 'Редагування звіту';
      if (!quiet) toast('Звіт створено');
    }
    return true;
  } catch (ex) { toast(ex.message, 'err'); return false; }
  finally      { if (!quiet) setLoading(btn, false); }
}

/* ── AI conclusion SSE ── */
async function streamConclusion() {
  const out = document.getElementById('ai-output');
  if (out.value.trim() && !confirm('Замінити поточний текст висновків новою чернеткою?')) return;
  if (sse_conc) { sse_conc.close(); sse_conc = null; }

  // The draft is written from the saved report, so save the latest edits first
  if (!(await saveReport({ quiet: true }))) return;

  const btn = document.getElementById('btn-conclusion');
  const statusEl = document.getElementById('conc-status');
  const previous = out.value;
  out.value = '';
  out.readOnly = true;
  out.classList.add('streaming');
  setLoading(btn, true);

  let text = '';
  const setStatus = msg => { statusEl.textContent = msg || ''; statusEl.classList.toggle('hidden', !msg); };
  const finish = () => {
    sse_conc?.close(); sse_conc = null;
    out.readOnly = false;
    out.classList.remove('streaming');
    setLoading(btn, false);
    setStatus('');
    updateReadiness();
  };
  const fail = msg => {
    finish();
    if (!text) out.value = previous;
    toast(msg || 'Не вдалося отримати висновки, спробуйте ще раз', 'err');
  };

  setStatus('Читаємо роботу…');
  sse_conc = new EventSource(`${API_URL}/reports/${reportId}/stream-conclusion?token=${auth.token()}`);

  sse_conc.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.status) setStatus(data.status);
    if (data.token) {
      if (!text) setStatus('');
      text += data.token;
      out.value = text;
      out.scrollTop = out.scrollHeight;
    }
    if (data.error) fail(data.error);
    if (data.done) {
      finish();
      toast('Чернетку висновків готово — перевірте її');
    }
  };

  sse_conc.onerror = () => { if (sse_conc) fail(); };
}

/* ── generate docx ── */
async function generateDocx() {
  if (!(await saveReport({ quiet: true }))) return;

  const btn   = document.getElementById('btn-generate');
  const pWrap = document.getElementById('gen-progress');
  const pFill = document.getElementById('gen-fill');
  const pLbl  = document.getElementById('gen-label');

  pWrap?.classList.remove('hidden');
  if (pFill) pFill.style.width = '15%';
  if (pLbl)  pLbl.textContent  = 'Складаємо документ…';
  setLoading(btn, true);

  try {
    await runGeneration(reportId, msg => {
      if (pFill) pFill.style.width = '60%';
      if (pLbl)  pLbl.textContent  = msg;
    });
    await download(`/reports/${reportId}/download`, fileName(currentTitle(), 'docx'));
    toast('Документ готовий');
  } catch (ex) {
    toast(ex.message, 'err');
  } finally {
    pWrap?.classList.add('hidden');
    setLoading(btn, false);
  }
}

async function previewReport() {
  if (!(await saveReport({ quiet: true }))) return;
  // Edits made in the document go straight to the server — reload the form afterwards
  openPreview(reportId, currentTitle(), { onClose: changed => changed && loadReport(reportId) });
}

function currentTitle() {
  return document.getElementById('f-title')?.value || `Звіт ${reportId}`;
}

/* ═══════════════════════════════════════════════════════
   GENERATION  (shared by editor and dashboard)
═══════════════════════════════════════════════════════ */
// Builds .docx + .pdf on the server; resolves when the files are ready
function runGeneration(id, onStatus) {
  return new Promise(async (resolve, reject) => {
    let task;
    try { task = await req('POST', `/reports/${id}/generate`); }
    catch (ex) { reject(ex); return; }

    let finished = false;
    const es = new EventSource(`${API_URL}/reports/${id}/generate/status?task_id=${task.task_id}&token=${auth.token()}`);
    const finish = (err) => {
      if (finished) return;
      finished = true;
      es.close();
      err ? reject(err) : resolve();
    };
    es.onmessage = e => {
      const data = JSON.parse(e.data);
      if (data.status === 'done')       finish();
      else if (data.status === 'error') finish(new Error(data.message || 'Не вдалося скласти документ'));
      else if (data.message)            onStatus?.(data.message);
    };
    es.onerror = () => finish(new Error('Втрачено зʼєднання з сервером'));
  });
}

function fileName(title, ext) {
  const base = String(title || 'Звіт').replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 120);
  return `${base || 'Звіт'}.${ext}`;
}

async function fetchBytes(path) {
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${auth.token()}` } });
  if (res.status === 404) throw new Error('PDF_UNAVAILABLE');
  if (!res.ok) throw new Error('Не вдалося завантажити файл');
  return res.arrayBuffer();
}

/* ═══════════════════════════════════════════════════════
   PREVIEW  (editable document + exact pdf.js view)
═══════════════════════════════════════════════════════ */
const PDFJS_URL    = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
const PDFJS_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
let pdfjsPromise = null;

function loadPdfJs() {
  if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
  pdfjsPromise ??= new Promise((resolve, reject) => {
    const s = Object.assign(document.createElement('script'), { src: PDFJS_URL, async: true });
    s.onload  = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER; resolve(window.pdfjsLib); };
    s.onerror = () => { pdfjsPromise = null; reject(new Error('Не вдалося завантажити переглядач PDF')); };
    document.head.appendChild(s);
  });
  return pdfjsPromise;
}

const ZOOM_STEPS = [0.5, 0.67, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2];
const SHEET_PX = 210 / 25.4 * 96;          // A4 width in CSS px

// contenteditable="plaintext-only" keeps pasted formatting out; older browsers get "true" + paste handler
const PLAIN_EDIT = (() => {
  const el = document.createElement('div');
  try { el.contentEditable = 'plaintext-only'; } catch { return 'true'; }
  return el.contentEditable === 'plaintext-only' ? 'plaintext-only' : 'true';
})();

const paras = text => {
  const lines = String(text || '').split('\n').map(l => l.trim()).filter(Boolean);
  return lines.length ? lines.map(l => `<p>${esc(l)}</p>`).join('') : '<p><br></p>';
};
// What the backend stores: one line per paragraph, no empty lines
const readParas = el => el.innerText.split('\n').map(l => l.trim()).filter(Boolean).join('\n');

/**
 * Opens the document window. Default tab — the document itself, editable in place
 * (title page, headings, text, code, captions, conclusion); changes are saved
 * automatically. The PDF tab shows the exact layout from the server.
 * opts.onClose(changed) is called when the window closes.
 */
async function openPreview(id, title, opts = {}) {
  document.querySelector('.pv')?.remove();

  const root = document.createElement('div');
  root.className = 'pv';
  root.setAttribute('role', 'dialog');
  root.setAttribute('aria-modal', 'true');
  root.setAttribute('aria-label', 'Документ');
  root.innerHTML = `
    <header class="pv-bar">
      <div class="pv-title">
        <span class="pv-doc">${ICONS.file}</span>
        <div><b class="pv-name">${esc(title)}</b><small class="pv-status">Відкриваємо…</small></div>
      </div>
      <div class="pv-tools">
        <div class="pv-tabs" role="tablist">
          <button role="tab" data-mode="edit" class="on">${ICONS.edit} Редагування</button>
          <button role="tab" data-mode="pdf">${ICONS.eye} PDF</button>
        </div>
        <span class="pv-sep"></span>
        <span class="pv-edit-only">
          <button class="pv-icon-btn" data-cmd="undo" title="Скасувати (Ctrl+Z)">${ICONS.undo}</button>
          <button class="pv-icon-btn" data-cmd="redo" title="Повторити (Ctrl+Y)">${ICONS.redo}</button>
          <span class="pv-sep"></span>
        </span>
        <button class="pv-icon-btn" data-zoom="-1" title="Зменшити">${ICONS.minus}</button>
        <button class="pv-zoom-val" data-zoom="fit" title="Підігнати за шириною">100%</button>
        <button class="pv-icon-btn" data-zoom="1" title="Збільшити">${ICONS.plus}</button>
        <span class="pv-pdf-only" hidden><span class="pv-sep"></span><span class="pv-counter">1 / 1</span></span>
      </div>
      <div class="pv-actions">
        <span class="pv-save" data-state="saved"></span>
        <button class="btn btn-secondary btn-sm" data-dl="docx">${ICONS.download} DOCX</button>
        <button class="btn btn-primary btn-sm" data-dl="pdf">${ICONS.download} PDF</button>
        <button class="pv-icon-btn pv-close" title="Закрити (Esc)">${ICONS.x}</button>
      </div>
    </header>
    <div class="pv-body">
      <aside class="pv-outline"></aside>
      <aside class="pv-thumbs" hidden></aside>
      <main class="pv-stage" data-mode="edit"><div class="dv-pages"></div></main>
      <main class="pv-stage" data-mode="pdf" hidden><div class="pv-pages"></div></main>
    </div>`;
  document.body.appendChild(root);
  document.body.classList.add('pv-open');
  requestAnimationFrame(() => root.classList.add('in'));

  const $ = sel => root.querySelector(sel);
  const status = msg => { $('.pv-status').textContent = msg; };
  let mode = 'edit', closed = false, changed = false;
  let doc = null, images = [], pdfView = null;
  const zoom = { edit: { scale: 1, user: false }, pdf: { scale: 1, user: false } };

  /* ── saving ── */
  // filesStale: .docx/.pdf on the server are older than the edits; viewStale: so is the PDF tab
  let saveTimer = null, saving = null, dirty = false, filesStale = true, viewStale = true;
  const dirtyCaptions = new Set();
  const saveEl = $('.pv-save');
  const setSave = (state, text) => { saveEl.dataset.state = state; saveEl.textContent = text; };
  setSave('saved', 'Усі зміни збережено');

  const touch = () => {
    dirty = true; changed = true; filesStale = viewStale = true;
    setSave('pending', 'Є незбережені зміни');
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flush, 900);
  };
  async function flush() {
    clearTimeout(saveTimer);
    if (saving) await saving;
    if (!dirty) return true;
    dirty = false;
    setSave('saving', 'Зберігаємо…');
    const captions = [...dirtyCaptions];
    dirtyCaptions.clear();
    saving = (async () => {
      await req('PATCH', `/reports/${id}`, {
        title: doc.title, discipline: doc.discipline, group: doc.group,
        teacher: doc.teacher, teacher_gender: doc.teacher_gender,
        student_name: doc.student_name, student_gender: doc.student_gender,
        goal: doc.goal, conclusion: doc.conclusion, sections: sectionsPayload(doc.sections),
      });
      for (const imgId of captions) {
        const img = images.find(i => i.id === imgId);
        if (img) await req('PATCH', `/reports/${id}/images/${imgId}`, { caption: img.caption });
      }
    })();
    try {
      await saving;
      if (!dirty) setSave('saved', 'Усі зміни збережено');
      return true;
    } catch (ex) {
      dirty = true;
      captions.forEach(c => dirtyCaptions.add(c));
      setSave('error', 'Не збережено — повторимо');
      saveTimer = setTimeout(flush, 4000);
      toast('Не вдалося зберегти: ' + ex.message, 'err');
      return false;
    } finally { saving = null; }
  }

  /* ── close / keys ── */
  const close = async () => {
    if (closed) return;
    await flush();
    closed = true;
    pdfView?.destroy();
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', onResize);
    window.removeEventListener('beforeunload', onUnload);
    document.body.classList.remove('pv-open');
    root.classList.remove('in');
    setTimeout(() => root.remove(), 180);
    opts.onClose?.(changed);
  };
  const onUnload = e => { if (dirty) { flush(); e.preventDefault(); } };
  const onKey = e => {
    if (e.key === 'Escape') { close(); return; }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); flush(); return; }
    if (e.target.closest?.('[contenteditable]') || e.target.matches?.('input, textarea')) return;
    if (e.key === '+' || e.key === '=') setZoom(1);
    if (e.key === '-') setZoom(-1);
  };
  let resizeTimer = null;
  const onResize = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (!zoom[mode].user) setZoom('fit', true); }, 150);
  };
  document.addEventListener('keydown', onKey);
  window.addEventListener('resize', onResize);
  window.addEventListener('beforeunload', onUnload);
  $('.pv-close').onclick = close;

  /* ── data ── */
  try {
    [doc, images] = await Promise.all([req('GET', `/reports/${id}`), req('GET', `/reports/${id}/images`)]);
  } catch (ex) {
    status('Помилка');
    $('.dv-pages').innerHTML = `<div class="pv-message"><h3>Не вдалося відкрити звіт</h3><p>${esc(ex.message)}</p></div>`;
    root.querySelectorAll('[data-dl], [data-mode]').forEach(b => b.disabled = true);
    return;
  }
  if (closed) return;
  doc.sections = toEditableSections(doc.sections);

  /* ── downloads always reflect the latest edits ── */
  root.querySelectorAll('[data-dl]').forEach(b => b.onclick = async () => {
    const fmt = b.dataset.dl;
    setLoading(b, true);
    try {
      if (!(await flush())) return;
      if (filesStale) { status('Складаємо документ…'); await runGeneration(id, status); filesStale = false; }
      await download(`/reports/${id}/download?format=${fmt}`, fileName(doc.title, fmt));
    } catch (ex) {
      toast(ex.message === 'Не вдалось скачати файл' && fmt === 'pdf' ? 'PDF на цьому сервері недоступний — завантажте DOCX' : ex.message, 'err');
    } finally { setLoading(b, false); status(statusText()); }
  });

  /* ── tabs, zoom, undo ── */
  root.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => setMode(b.dataset.mode));
  root.querySelectorAll('[data-zoom]').forEach(b => b.onclick = () => setZoom(b.dataset.zoom));
  root.querySelectorAll('[data-cmd]').forEach(b => b.onmousedown = e => { e.preventDefault(); document.execCommand(b.dataset.cmd); });

  function statusText() {
    return mode === 'edit'
      ? 'Клацніть по тексту, щоб редагувати · зміни зберігаються самі'
      : pdfView?.pages ? `${pdfView.pages} ${plural(pdfView.pages, 'сторінка', 'сторінки', 'сторінок')} · A4` : '';
  }

  async function setMode(next) {
    mode = next;
    root.querySelectorAll('.pv-tabs [data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === mode));
    root.querySelectorAll('.pv-stage').forEach(s => s.hidden = s.dataset.mode !== mode);
    $('.pv-outline').hidden = mode !== 'edit';
    $('.pv-thumbs').hidden = mode !== 'pdf' || !pdfView?.pages;
    $('.pv-edit-only').hidden = mode !== 'edit';
    $('.pv-pdf-only').hidden = mode !== 'pdf';
    $('.pv-zoom-val').textContent = `${Math.round(zoom[mode].scale * 100)}%`;
    status(statusText());
    if (mode === 'pdf') await showPdf();
  }

  function setZoom(dir, keepUser = false) {
    const z = zoom[mode];
    if (!keepUser) z.user = dir !== 'fit';
    if (dir === 'fit') z.scale = fitScale();
    else {
      const i = ZOOM_STEPS.findIndex(v => v >= z.scale - 0.001);
      const cur = i === -1 ? ZOOM_STEPS.length - 1 : i;
      z.scale = ZOOM_STEPS[Math.min(ZOOM_STEPS.length - 1, Math.max(0, cur + Number(dir)))];
    }
    $('.pv-zoom-val').textContent = `${Math.round(z.scale * 100)}%`;
    if (mode === 'edit') $('.dv-pages').style.zoom = z.scale;
    else pdfView?.render(z.scale);
  }

  function fitScale() {
    const stage = $(`.pv-stage[data-mode="${mode}"]`);
    const pad = stage.clientWidth < 700 ? 24 : 64;
    const width = mode === 'edit' ? SHEET_PX : (pdfView?.baseWidth || SHEET_PX);
    return Math.min(mode === 'edit' ? 1 : 1.25, Math.max(0.3, (stage.clientWidth - pad) / width));
  }

  /* ═════════ editable document ═════════ */
  const pages = $('.dv-pages');
  const editAttr = (bind, ph, kind = 'line') =>
    `data-bind="${bind}" data-kind="${kind}" data-ph="${esc(ph)}" contenteditable="${kind === 'paras' ? 'true' : PLAIN_EDIT}" spellcheck="true"`;
  const getField = bind => {
    const [k, a, b] = bind.split('|');
    if (k === 'doc') return doc[a];
    if (k === 'img') return images.find(i => i.id === Number(a))?.caption ?? '';
    const block = b === undefined ? doc.sections[+a] : doc.sections[+a].subsections[+b];
    return block?.[k];
  };
  const setField = (bind, value) => {
    const [k, a, b] = bind.split('|');
    if (k === 'doc') { doc[a] = value; return; }
    if (k === 'img') { const img = images.find(i => i.id === Number(a)); if (img) { img.caption = value; dirtyCaptions.add(img.id); } return; }
    const [field, i, j] = [k, +a, b === undefined ? undefined : +b];
    const block = j === undefined ? doc.sections[i] : doc.sections[i].subsections[j];
    block[field] = value;
  };
  const blockBind = (field, i, j) => j === undefined ? `${field}|${i}` : `${field}|${i}|${j}`;

  function render() {
    const scrollTop = $('.pv-stage[data-mode="edit"]').scrollTop;
    const did = doc.student_gender === 'f' ? 'Виконала:' : 'Виконав:';
    const took = doc.teacher_gender === 'm' ? 'Прийняв:' : 'Прийняла:';
    const gBtn = (who, label) =>
      `<button class="dv-gender" data-gender="${who}" title="Натисніть, щоб змінити форму">${label}</button>`;

    const titlePage = `
      <section class="dv-sheet dv-title">
        <p>Міністерство освіти і науки України</p>
        <p>Харківський національний університет радіоелектроніки</p>
        <p>&nbsp;</p>
        <p>Кафедра штучного інтелекту</p>
        <p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>
        <p>Дисципліна «<span ${editAttr('doc|discipline', 'Назва дисципліни')}>${esc(doc.discipline)}</span>»</p>
        <p><span ${editAttr('doc|title', 'Назва роботи')}>${esc(doc.title)}</span></p>
        <p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>
        <div class="dv-sign">
          <div>
            <p>${gBtn('student', did)}</p>
            <p>ст. гр. <span ${editAttr('doc|group', 'група')}>${esc(doc.group)}</span></p>
            <p><span ${editAttr('doc|student_name', 'Прізвище І. Б. студента')}>${esc(doc.student_name)}</span></p>
          </div>
          <div>
            <p>${gBtn('teacher', took)}</p>
            <p><span ${editAttr('doc|teacher', 'Прізвище І. Б. викладача')}>${esc(doc.teacher)}</span></p>
          </div>
        </div>
        <p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>
        <p>Харків – ${new Date().getFullYear()}</p>
      </section>`;

    let listing = 0, figure = 0;
    const blockHtml = (b, i, j) => {
      const path = j === undefined ? `${i}` : `${i}.${j}`;
      const num = j === undefined ? `${i + 1}` : `${i + 1}.${j + 1}`;
      const title = b.title.trim() || (j === undefined ? `Розділ ${num}` : `Підрозділ ${num}`);
      const tag = j === undefined ? 'h1' : 'h2';
      let html = `
        <div class="dv-block" id="dv-${path.replace('.', '-')}" data-path="${path}">
          <div class="dv-hover">
            ${j === undefined ? `<button data-act="sub" data-path="${path}" title="Додати підрозділ">${ICONS.plus} Підрозділ</button>` : ''}
            ${b.code ? '' : `<button data-act="code" data-path="${path}" title="Додати лістинг коду">${ICONS.code} Код</button>`}
            <button data-act="img" data-path="${path}" title="Додати рисунок">${ICONS.image} Рисунок</button>
            <button data-act="del" data-path="${path}" class="danger" title="Видалити">${ICONS.trash}</button>
          </div>
          <${tag} class="dv-h"><span class="dv-num">${num}</span> <span ${editAttr(blockBind('title', i, j), j === undefined ? 'Назва розділу' : 'Назва підрозділу')}>${esc(b.title)}</span></${tag}>
          <div class="dv-text" ${editAttr(blockBind('text', i, j), 'Текст — що зроблено, які результати', 'paras')}>${paras(b.text)}</div>`;
      if (b.code) {
        listing++;
        html += `<p class="dv-cap-left" data-cap-of="${path}">Лістинг ${listing} – ${esc(title)}</p>
          <pre class="dv-code" ${editAttr(blockBind('code', i, j), 'Код', 'code')}>${esc(b.code.replace(/\r/g, ''))}</pre>`;
      }
      for (const img of images.filter(im => im.section_path === path)) {
        figure++;
        html += `<figure class="dv-fig" data-img="${img.id}">
            <img src="${API_URL}${img.url}" alt="">
            <figcaption>Рисунок ${figure} – <span ${editAttr(`img|${img.id}`, 'підпис рисунка')}>${esc(img.caption)}</span></figcaption>
            <button class="dv-fig-del" data-act="delimg" data-img="${img.id}" title="Видалити рисунок">${ICONS.trash}</button>
          </figure>`;
      }
      return html + '</div>';
    };

    const toc = [['МЕТА РОБОТИ', 1]];
    doc.sections.forEach((s, i) => {
      toc.push([`${i + 1} ${(s.title.trim() || `Розділ ${i + 1}`).toUpperCase()}`, 1, `${i}`]);
      s.subsections.forEach((b, j) => toc.push([`${i + 1}.${j + 1} ${b.title.trim() || `Підрозділ ${i + 1}.${j + 1}`}`, 2, `${i}.${j}`]));
    });
    toc.push(['ВИСНОВКИ', 1]);

    pages.innerHTML = titlePage + `
      <section class="dv-sheet dv-toc">
        <p class="dv-toc-title">ЗМІСТ</p>
        ${toc.map(([t, l]) => `<p class="dv-toc-row l${l}"><span>${esc(t)}</span><i></i></p>`).join('')}
        <p class="dv-note">Зміст складається автоматично; номери сторінок з'являться в документі (вкладка PDF).</p>
      </section>
      <section class="dv-sheet dv-body">
        <h1 class="dv-h">Мета роботи</h1>
        <div class="dv-text" ${editAttr('doc|goal', 'Мета роботи', 'paras')}>${paras(doc.goal)}</div>
        ${doc.sections.map((s, i) => blockHtml(s, i) + s.subsections.map((b, j) => blockHtml(b, i, j)).join('')).join('')}
        <button class="dv-add" data-act="section">${ICONS.plus} Додати розділ ${doc.sections.length + 1}</button>
        <h1 class="dv-h">Висновки</h1>
        <div class="dv-text" ${editAttr('doc|conclusion', 'Висновки (можна згенерувати в редакторі)', 'paras')}>${paras(doc.conclusion)}</div>
      </section>`;

    pages.querySelectorAll('[data-bind]').forEach(markEmpty);
    renderOutlineNav();
    $('.pv-stage[data-mode="edit"]').scrollTop = scrollTop;
  }

  function markEmpty(el) {
    el.classList.toggle('is-empty', !el.textContent.trim());
  }

  // Only titles affect other places (TOC, outline, listing captions) — refresh those without re-rendering the page
  function refreshDerived() {
    const tocRows = pages.querySelectorAll('.dv-toc-row span');
    let r = 1;
    doc.sections.forEach((s, i) => {
      tocRows[r++].textContent = `${i + 1} ${(s.title.trim() || `Розділ ${i + 1}`).toUpperCase()}`;
      s.subsections.forEach((b, j) => { tocRows[r++].textContent = `${i + 1}.${j + 1} ${b.title.trim() || `Підрозділ ${i + 1}.${j + 1}`}`; });
    });
    pages.querySelectorAll('[data-cap-of]').forEach(p => {
      const [i, j] = p.dataset.capOf.split('.').map(Number);
      const b = j === undefined ? doc.sections[i] : doc.sections[i].subsections[j];
      const title = b.title.trim() || (j === undefined ? `Розділ ${i + 1}` : `Підрозділ ${i + 1}.${j + 1}`);
      p.textContent = p.textContent.replace(/ – .*$/, ` – ${title}`);
    });
    renderOutlineNav();
  }

  function renderOutlineNav() {
    const nav = $('.pv-outline');
    const item = (label, target, cls = '') =>
      `<button class="pvo-item ${cls}" data-target="${target}"><span>${esc(label)}</span></button>`;
    nav.innerHTML = `<p class="pvo-head">Зміст</p>`
      + item('Титульна сторінка', '.dv-title')
      + item('Мета роботи', '.dv-body')
      + doc.sections.map((s, i) => item(`${i + 1} ${s.title.trim() || 'Без назви'}`, `#dv-${i}`)
          + s.subsections.map((b, j) => item(`${i + 1}.${j + 1} ${b.title.trim() || 'Без назви'}`, `#dv-${i}-${j}`, 'sub')).join('')).join('')
      + item('Висновки', '.dv-add')
      + `<button class="btn btn-secondary btn-sm pvo-add" data-act="section">${ICONS.plus} Розділ</button>`;
    nav.querySelectorAll('.pvo-item').forEach(b => b.onclick = () =>
      pages.querySelector(b.dataset.target)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  /* typing */
  pages.addEventListener('input', e => {
    const el = e.target.closest('[data-bind]');
    if (!el) return;
    const kind = el.dataset.kind;
    const value = kind === 'paras' ? readParas(el)
      : kind === 'code' ? el.innerText.replace(/\n$/, '')
      // textContent, not innerText: innerText applies text-transform (h1 titles are shown in caps)
      : el.textContent.replace(/\s+/g, ' ').trim();
    setField(el.dataset.bind, value);
    markEmpty(el);
    if (el.dataset.bind.startsWith('title|')) refreshDerived();
    if (el.dataset.bind === 'doc|title') $('.pv-name').textContent = value || 'Без назви';
    touch();
  });
  pages.addEventListener('keydown', e => {
    const el = e.target.closest?.('[data-bind]');
    if (!el) return;
    if (e.key === 'Enter' && el.dataset.kind === 'line') e.preventDefault();
    if (e.key === 'Tab' && el.dataset.kind === 'code') { e.preventDefault(); document.execCommand('insertText', false, '    '); }
  });
  // Keep pasted text plain (Word / web pages bring styles along)
  pages.addEventListener('paste', e => {
    const el = e.target.closest?.('[data-bind]');
    if (!el) return;
    e.preventDefault();
    let text = e.clipboardData.getData('text/plain');
    if (el.dataset.kind === 'line') text = text.replace(/\s+/g, ' ');
    document.execCommand('insertText', false, text);
  });
  // An empty paragraph block must keep one <p>, or the browser starts typing into a bare text node
  pages.addEventListener('focusout', e => {
    const el = e.target.closest?.('[data-kind="paras"]');
    if (el && !el.querySelector('p')) el.innerHTML = paras(getField(el.dataset.bind));
  });

  /* structure buttons */
  root.addEventListener('click', async e => {
    const g = e.target.closest('.dv-gender');
    if (g) {
      const key = g.dataset.gender === 'student' ? 'student_gender' : 'teacher_gender';
      doc[key] = doc[key] === 'f' ? 'm' : 'f';
      g.textContent = g.dataset.gender === 'student'
        ? (doc[key] === 'f' ? 'Виконала:' : 'Виконав:')
        : (doc[key] === 'm' ? 'Прийняв:' : 'Прийняла:');
      touch();
      return;
    }
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const [i, j] = (btn.dataset.path || '').split('.').map(Number);
    const block = btn.dataset.path ? (Number.isNaN(j) || j === undefined ? doc.sections[i] : doc.sections[i].subsections[j]) : null;
    const isSub = j !== undefined && !Number.isNaN(j);

    if (act === 'section') {
      doc.sections.push({ ...newBlock(), subsections: [] });
      touch(); render();
      focusBind(`title|${doc.sections.length - 1}`);
    } else if (act === 'sub') {
      doc.sections[i].subsections.push(newBlock());
      touch(); render();
      focusBind(`title|${i}|${doc.sections[i].subsections.length - 1}`);
    } else if (act === 'code') {
      block.code = ' ';
      render();
      const pre = pages.querySelector(`[data-bind="${blockBind('code', i, isSub ? j : undefined)}"]`);
      pre.textContent = ''; block.code = ''; markEmpty(pre);
      pre.focus();
    } else if (act === 'del') {
      const label = isSub ? `підрозділ ${i + 1}.${j + 1}` : `розділ ${i + 1}`;
      if (hasContent(block) && !confirm(`Видалити ${label} разом із вмістом і рисунками?`)) return;
      if (isSub) doc.sections[i].subsections.splice(j, 1); else doc.sections.splice(i, 1);
      images = await remapImages(id, images, isSub ? pathMaps.removeSubsection(i, j) : pathMaps.removeSection(i));
      touch(); render(); flush();
    } else if (act === 'img') {
      const input = Object.assign(document.createElement('input'), { type: 'file', accept: 'image/*', multiple: true });
      input.onchange = async () => {
        status('Завантажуємо рисунок…');
        images.push(...await uploadImages(id, [...input.files], btn.dataset.path));
        changed = true; filesStale = viewStale = true;
        render(); status(statusText());
      };
      input.click();
    } else if (act === 'delimg') {
      const imgId = Number(btn.dataset.img);
      if (!confirm('Видалити цей рисунок?')) return;
      try {
        await req('DELETE', `/reports/${id}/images/${imgId}`);
        images = images.filter(im => im.id !== imgId);
        changed = true; filesStale = viewStale = true;
        render();
      } catch (ex) { toast(ex.message, 'err'); }
    }
  });

  function focusBind(bind) {
    const el = pages.querySelector(`[data-bind="${bind}"]`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el?.focus({ preventScroll: true });
  }

  /* ═════════ PDF tab ═════════ */
  async function showPdf() {
    pdfView ??= createPdfView(root, id);
    if (!(await flush())) return;
    if (!viewStale && pdfView.pages) return;
    viewStale = filesStale = false;
    await pdfView.load(status);
    if (mode !== 'pdf' || closed || !pdfView.pages) return;
    $('.pv-thumbs').hidden = false;
    if (!zoom.pdf.user) zoom.pdf.scale = fitScale();
    $('.pv-zoom-val').textContent = `${Math.round(zoom.pdf.scale * 100)}%`;
    pdfView.render(zoom.pdf.scale);
    status(statusText());
  }

  render();
  zoom.edit.scale = fitScale();
  setZoom('fit', true);
  status(statusText());
  if (opts.mode === 'pdf') setMode('pdf');
}

/* pdf.js view used by the PDF tab: load(), render(scale), destroy() */
function createPdfView(root, id) {
  const $ = sel => root.querySelector(sel);
  const stage = $('.pv-stage[data-mode="pdf"]');
  const wrap = $('.pv-pages');
  const thumbs = $('.pv-thumbs');
  let pdf = null, observer = null, scale = 1, base = null, gen = 0;

  const view = {
    pages: 0,
    baseWidth: 0,
    async load(status) {
      const my = ++gen;
      pdf?.destroy(); pdf = null; view.pages = 0;
      thumbs.innerHTML = '';
      wrap.innerHTML = `<div class="pv-skeleton"><div class="pv-sk-line w40 c"></div><div class="pv-sk-line"></div><div class="pv-sk-line"></div><div class="pv-sk-line w70"></div><div class="pv-sk-gap"></div><div class="pv-sk-line"></div><div class="pv-sk-line w85"></div><div class="pv-sk-line"></div><div class="pv-sk-line w60"></div></div>`;
      try {
        status('Складаємо документ…');
        await runGeneration(id, status);
        status('Відкриваємо PDF…');
        const [lib, bytes] = await Promise.all([loadPdfJs(), fetchBytes(`/reports/${id}/download?format=pdf`)]);
        if (my !== gen) return;
        pdf = await lib.getDocument({ data: bytes }).promise;
      } catch (ex) {
        if (my !== gen) return;
        const unavailable = ex.message === 'PDF_UNAVAILABLE';
        status(unavailable ? 'PDF недоступний' : 'Помилка');
        wrap.innerHTML = `
          <div class="pv-message">
            <h3>${unavailable ? 'На цьому сервері немає конвертера PDF' : 'Не вдалося підготувати PDF'}</h3>
            <p>${unavailable ? 'Документ .docx уже готовий — його можна завантажити кнопкою вгорі.' : esc(ex.message)}</p>
          </div>`;
        return;
      }
      view.pages = pdf.numPages;
      const first = await pdf.getPage(1);
      base = first.getViewport({ scale: 1 });
      view.baseWidth = base.width;
      wrap.innerHTML = '';
      renderThumbs(my);
    },
    render(s) {
      if (!pdf) return;
      scale = s;
      const ratio = stage.scrollTop / Math.max(1, stage.scrollHeight);
      renderPages();
      stage.scrollTop = ratio * stage.scrollHeight;
    },
    destroy() { gen++; observer?.disconnect(); pdf?.destroy(); },
  };

  function renderPages() {
    observer?.disconnect();
    wrap.innerHTML = '';
    const vp = base.clone({ scale });
    for (let n = 1; n <= pdf.numPages; n++) {
      const page = document.createElement('div');
      page.className = 'pv-page';
      page.dataset.page = n;
      page.style.width = `${vp.width}px`;
      page.style.height = `${vp.height}px`;
      wrap.appendChild(page);
    }
    // Render lazily: only pages near the viewport get a canvas
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const el = entry.target;
        if (entry.isIntersecting && !el.dataset.done) { el.dataset.done = '1'; drawPage(el, Number(el.dataset.page)); }
      });
    }, { root: stage, rootMargin: '600px 0px', threshold: 0 });
    wrap.querySelectorAll('.pv-page').forEach(el => observer.observe(el));
    stage.onscroll = () => {
      const s = stage.getBoundingClientRect();
      const el = [...wrap.children].find(c => c.getBoundingClientRect().bottom > s.top + s.height * 0.4);
      if (el) setCurrent(Number(el.dataset.page));
    };
  }

  async function drawPage(el, n, target = el, s = scale) {
    const page = await pdf.getPage(n);
    const vp = page.getViewport({ scale: s });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const canvas = document.createElement('canvas');
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = `${vp.width}px`;
    canvas.style.height = `${vp.height}px`;
    await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null }).promise;
    target.replaceChildren(canvas);
    target.classList.add('ready');
  }

  async function renderThumbs(my) {
    thumbs.innerHTML = '';
    for (let n = 1; n <= pdf.numPages; n++) {
      const t = document.createElement('button');
      t.className = 'pv-thumb';
      t.dataset.page = n;
      t.innerHTML = `<div class="pv-thumb-img" style="aspect-ratio:${base.width}/${base.height}"></div><span>${n}</span>`;
      t.onclick = () => $(`.pv-page[data-page="${n}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      thumbs.appendChild(t);
    }
    setCurrent(1);
    for (let n = 1; n <= pdf.numPages && my === gen; n++) {
      const holder = thumbs.querySelector(`.pv-thumb[data-page="${n}"] .pv-thumb-img`);
      if (holder) await drawPage(holder, n, holder, 116 / base.width);
    }
  }

  function setCurrent(n) {
    $('.pv-counter').textContent = `${n} / ${pdf?.numPages || 1}`;
    thumbs.querySelectorAll('.pv-thumb').forEach(t => t.classList.toggle('active', Number(t.dataset.page) === n));
    thumbs.querySelector('.pv-thumb.active')?.scrollIntoView({ block: 'nearest' });
  }

  return view;
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

/* ═══════════════════════════════════════════════════════
   ROUTER
═══════════════════════════════════════════════════════ */
(function route() {
  const p = window.location.pathname;
  if      (p.endsWith('dashboard.html')) initDashboard();
  else if (p.endsWith('editor.html'))    initEditor();
  else if (p.endsWith('auth.html'))      initAuth();
  // index.html — лендінг, нічого ініціалізувати не потрібно
})();
