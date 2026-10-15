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
      if (action === 'view') openPreview(id, allReports.find(r => r.id === id)?.title);
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
let reportId    = null;
let sections    = [];
let sse_conc    = null;

async function initEditor() {
  auth.guard();
  fillSidebar();

  document.getElementById('btn-add-sec')?.addEventListener('click', addSection);
  document.getElementById('btn-save')?.addEventListener('click', saveReport);
  document.getElementById('btn-conclusion')?.addEventListener('click', streamConclusion);
  document.getElementById('btn-generate')?.addEventListener('click', generateDocx);
  document.getElementById('btn-preview')?.addEventListener('click', previewReport);

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

async function loadReport(id) {
  try {
    const r = await req('GET', `/reports/${id}`);
    document.getElementById('f-title').value      = r.title      || '';
    document.getElementById('f-discipline').value = r.discipline || '';
    document.getElementById('f-teacher').value    = r.teacher    || '';
    document.getElementById('f-group').value      = r.group      || '';
    document.getElementById('f-goal').value       = r.goal       || '';

    const toBlock = (s, i) => ({
      id: i, title: s.title || '', text: s.text || '', code: s.code || '', language: s.language || 'python',
    });
    sections = (r.sections || []).map((s, i) => ({
      ...toBlock(s, i),
      subsections: (s.subsections || []).map(toBlock),
    }));
    renderSections();

    document.getElementById('ai-output').value = r.conclusion || '';
  } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
}

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
  document.querySelectorAll('.section-item').at(-1)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function removeSection(idx) {
  sections.splice(idx, 1);
  renderSections();
}

function addSubsection(i) {
  sections[i].subsections.push(newBlock());
  renderSections();
}

function removeSubsection(i, j) {
  sections[i].subsections.splice(j, 1);
  renderSections();
}

const LANGS = ['python','javascript','typescript','java','cpp','c','sql','bash','html','css'];

function blockFieldsHtml(path, block, kind) {
  const id = String(path).replace('.', '-');
  return `
        <div class="form-group">
          <label>Текст ${kind}</label>
          <textarea rows="4" placeholder="Що було зроблено, які результати отримано"
                    oninput="blockAt('${path}').text = this.value">${esc(block.text)}</textarea>
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
    return;
  }

  container.innerHTML = sections.map((sec, i) => `
    <div class="section-item">
      <div class="section-head">
        <span class="sec-num">${i + 1}</span>
        <input class="sec-name" placeholder="Назва розділу..."
               value="${esc(sec.title)}" oninput="sections[${i}].title = this.value">
        <button class="btn btn-ghost btn-sm" onclick="removeSection(${i})" title="Видалити розділ">${ICONS.trash}</button>
      </div>
      <div class="section-body">
        ${blockFieldsHtml(`${i}`, sec, 'розділу')}
        ${sec.subsections.map((sub, j) => `
        <div class="section-item subsection-item">
          <div class="section-head">
            <span class="sec-num">${i + 1}.${j + 1}</span>
            <input class="sec-name" placeholder="Назва підрозділу..."
                   value="${esc(sub.title)}" oninput="sections[${i}].subsections[${j}].title = this.value">
            <button class="btn btn-ghost btn-sm" onclick="removeSubsection(${i},${j})" title="Видалити підрозділ">${ICONS.trash}</button>
          </div>
          <div class="section-body">
            ${blockFieldsHtml(`${i}.${j}`, sub, 'підрозділу')}
          </div>
        </div>`).join('')}
        <div><button class="btn btn-ghost btn-sm" onclick="addSubsection(${i})">${ICONS.plus} Підрозділ ${i + 1}.${sec.subsections.length + 1}</button></div>
      </div>
    </div>`).join('');
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

async function uploadFiles(files, sectionPath) {
  if (!reportId) { toast('Спершу збережіть звіт — тоді можна додавати скріншоти', 'err'); return; }
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('report_id', reportId);
    fd.append('section_path', sectionPath);
    try {
      const res = await fetch(`${API_URL}/upload/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token()}` },
        body: fd,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      appendThumb(sectionPath, data.url, data.id);
    } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
  }
}

function appendThumb(path, url, imgId) {
  const grid = document.getElementById(`imgs-${String(path).replace('.', '-')}`);
  if (!grid) return;
  const div = document.createElement('div');
  div.className = 'img-thumb';
  div.dataset.imgId = imgId;
  div.innerHTML = `<img src="${API_URL}${url}" alt="скріншот"><button class="rm" onclick="removeThumb(this)">✕</button>`;
  grid.appendChild(div);
}

function removeThumb(btn) { btn.closest('.img-thumb').remove(); }

/* ── save ── */
async function saveReport({ quiet = false } = {}) {
  const btn = document.getElementById('btn-save');
  if (!quiet) setLoading(btn, true);

  const payload = {
    title:      document.getElementById('f-title').value,
    discipline: document.getElementById('f-discipline').value,
    teacher:    document.getElementById('f-teacher').value,
    group:      document.getElementById('f-group').value,
    goal:       document.getElementById('f-goal').value,
    conclusion: document.getElementById('ai-output').value,
    sections:   sections.map(s => ({
      title: s.title, text: s.text, code: s.code, language: s.language,
      subsections: s.subsections.map(b => ({ title: b.title, text: b.text, code: b.code, language: b.language })),
    })),
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
  const previous = out.value;
  out.value = '';
  out.readOnly = true;
  out.classList.add('streaming');
  setLoading(btn, true);

  let text = '';
  const finish = () => {
    sse_conc?.close(); sse_conc = null;
    out.readOnly = false;
    out.classList.remove('streaming');
    setLoading(btn, false);
  };

  sse_conc = new EventSource(`${API_URL}/reports/${reportId}/stream-conclusion?token=${auth.token()}`);

  sse_conc.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.token) {
      text += data.token;
      out.value = text;
      out.scrollTop = out.scrollHeight;
    }
    if (data.done) {
      finish();
      toast('Чернетку висновків готово — перевірте її');
    }
  };

  sse_conc.onerror = () => {
    if (!sse_conc) return;
    finish();
    if (!text) out.value = previous;
    toast('Не вдалося отримати висновки, спробуйте ще раз', 'err');
  };
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
  openPreview(reportId, currentTitle());
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
   PREVIEW  (pdf.js viewer)
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

async function openPreview(id, title) {
  document.querySelector('.pv')?.remove();

  const root = document.createElement('div');
  root.className = 'pv';
  root.setAttribute('role', 'dialog');
  root.setAttribute('aria-modal', 'true');
  root.setAttribute('aria-label', 'Попередній перегляд документа');
  root.innerHTML = `
    <header class="pv-bar">
      <div class="pv-title">
        <span class="pv-doc">${ICONS.file}</span>
        <div><b>${esc(title)}</b><small class="pv-status">Готуємо документ…</small></div>
      </div>
      <div class="pv-tools" hidden>
        <button class="pv-icon-btn" data-zoom="-1" title="Зменшити (−)">${ICONS.minus}</button>
        <button class="pv-zoom-val" data-zoom="fit" title="Підігнати за шириною">100%</button>
        <button class="pv-icon-btn" data-zoom="1" title="Збільшити (+)">${ICONS.plus}</button>
        <span class="pv-sep"></span>
        <span class="pv-counter">1 / 1</span>
      </div>
      <div class="pv-actions">
        <button class="btn btn-secondary btn-sm" data-dl="docx">${ICONS.download} DOCX</button>
        <button class="btn btn-primary btn-sm" data-dl="pdf" disabled>${ICONS.download} PDF</button>
        <button class="pv-icon-btn pv-close" title="Закрити (Esc)">${ICONS.x}</button>
      </div>
    </header>
    <div class="pv-body">
      <aside class="pv-thumbs" hidden></aside>
      <main class="pv-stage">
        <div class="pv-pages">
          <div class="pv-skeleton"><div class="pv-sk-line w40 c"></div><div class="pv-sk-line"></div><div class="pv-sk-line"></div><div class="pv-sk-line w70"></div><div class="pv-sk-gap"></div><div class="pv-sk-line"></div><div class="pv-sk-line w85"></div><div class="pv-sk-line"></div><div class="pv-sk-line w60"></div></div>
        </div>
      </main>
    </div>`;
  document.body.appendChild(root);
  document.body.classList.add('pv-open');
  requestAnimationFrame(() => root.classList.add('in'));

  const $ = sel => root.querySelector(sel);
  const status = msg => { $('.pv-status').textContent = msg; };
  let pdf = null, scale = 1, fitScale = 1, observer = null, closed = false, userZoomed = false, resizeTimer = null, ready = false;

  const close = () => {
    closed = true;
    observer?.disconnect();
    pdf?.destroy();
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', onResize);
    document.body.classList.remove('pv-open');
    root.classList.remove('in');
    setTimeout(() => root.remove(), 180);
  };
  const onKey = e => {
    if (e.key === 'Escape') close();
    if (!pdf || e.target.matches('input, textarea')) return;
    if (e.key === '+' || e.key === '=') setZoom(1);
    if (e.key === '-') setZoom(-1);
  };
  // Keep "fit to width" while the user has not picked a zoom level themselves
  const onResize = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (!ready || userZoomed) return;
      fitScale = computeFit();
      if (Math.abs(fitScale - scale) > 0.01) { scale = fitScale; renderPages(); }
    }, 150);
  };
  document.addEventListener('keydown', onKey);
  window.addEventListener('resize', onResize);
  $('.pv-close').onclick = close;
  root.querySelectorAll('[data-dl]').forEach(b => b.onclick = async () => {
    const fmt = b.dataset.dl;
    try { await download(`/reports/${id}/download?format=${fmt}`, fileName(title, fmt)); }
    catch (ex) { toast(ex.message, 'err'); }
  });

  try {
    await runGeneration(id, status);
    if (closed) return;
    status('Відкриваємо попередній перегляд…');
    const [lib, bytes] = await Promise.all([loadPdfJs(), fetchBytes(`/reports/${id}/download?format=pdf`)]);
    if (closed) return;
    pdf = await lib.getDocument({ data: bytes }).promise;
  } catch (ex) {
    if (closed) return;
    const unavailable = ex.message === 'PDF_UNAVAILABLE';
    status(unavailable ? 'Попередній перегляд недоступний' : 'Помилка');
    $('.pv-pages').innerHTML = `
      <div class="pv-message">
        <h3>${unavailable ? 'На цьому сервері немає конвертера PDF' : 'Не вдалося підготувати перегляд'}</h3>
        <p>${unavailable ? 'Документ .docx уже готовий — його можна завантажити кнопкою вгорі.' : esc(ex.message)}</p>
      </div>`;
    return;
  }

  $('[data-dl="pdf"]').disabled = false;
  $('.pv-tools').hidden = false;
  $('.pv-thumbs').hidden = false;
  status(`${pdf.numPages} ${plural(pdf.numPages, 'сторінка', 'сторінки', 'сторінок')} · A4`);

  const first = await pdf.getPage(1);
  const base = first.getViewport({ scale: 1 });
  const stage = $('.pv-stage');
  const computeFit = () => {
    const pad = stage.clientWidth < 700 ? 24 : 64;
    return Math.min(1.25, Math.max(0.3, (stage.clientWidth - pad) / base.width));
  };
  fitScale = computeFit();
  scale = fitScale;

  renderThumbs();
  renderPages();
  ready = true;

  root.querySelectorAll('[data-zoom]').forEach(b => b.onclick = () => setZoom(b.dataset.zoom));

  function setZoom(dir) {
    userZoomed = dir !== 'fit';
    if (dir === 'fit') scale = fitScale = computeFit();
    else {
      const i = ZOOM_STEPS.findIndex(z => z >= scale - 0.001);
      const cur = i === -1 ? ZOOM_STEPS.length - 1 : i;
      scale = ZOOM_STEPS[Math.min(ZOOM_STEPS.length - 1, Math.max(0, cur + Number(dir)))];
    }
    const ratio = stage.scrollTop / Math.max(1, stage.scrollHeight);
    renderPages();
    stage.scrollTop = ratio * stage.scrollHeight;
  }

  function renderPages() {
    observer?.disconnect();
    $('.pv-zoom-val').textContent = `${Math.round(scale * 100)}%`;
    const wrap = $('.pv-pages');
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
      const visible = [...wrap.children].filter(el => {
        const r = el.getBoundingClientRect(), s = stage.getBoundingClientRect();
        return r.bottom > s.top + s.height * 0.35 && r.top < s.top + s.height * 0.65;
      });
      if (visible[0]) setCurrent(Number(visible[0].dataset.page));
    }, { root: stage, rootMargin: '600px 0px', threshold: [0, 0.35, 0.65] });
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

  async function renderThumbs() {
    const box = $('.pv-thumbs');
    box.innerHTML = '';
    for (let n = 1; n <= pdf.numPages; n++) {
      const t = document.createElement('button');
      t.className = 'pv-thumb';
      t.dataset.page = n;
      t.innerHTML = `<div class="pv-thumb-img" style="aspect-ratio:${base.width}/${base.height}"></div><span>${n}</span>`;
      t.onclick = () => $(`.pv-page[data-page="${n}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      box.appendChild(t);
    }
    setCurrent(1);
    for (let n = 1; n <= pdf.numPages && !closed; n++) {
      const holder = box.querySelector(`.pv-thumb[data-page="${n}"] .pv-thumb-img`);
      await drawPage(holder, n, holder, 116 / base.width);
    }
  }

  function setCurrent(n) {
    $('.pv-counter').textContent = `${n} / ${pdf.numPages}`;
    root.querySelectorAll('.pv-thumb').forEach(t => t.classList.toggle('active', Number(t.dataset.page) === n));
    root.querySelector('.pv-thumb.active')?.scrollIntoView({ block: 'nearest' });
  }
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
