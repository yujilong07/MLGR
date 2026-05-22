/* ═══════════════════════════════════════════════════════
   CONFIG
═══════════════════════════════════════════════════════ */
const API_URL = 'http://localhost:8000';

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
let allReports = [];

async function initDashboard() {
  auth.guard();
  fillSidebar();

  document.getElementById('btn-new')?.addEventListener('click', () => { window.location.href = 'editor.html'; });

  const searchInput = document.getElementById('search-input');
  searchInput?.addEventListener('input', () => renderGrid(searchInput.value));

  await loadReports();
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
  const list = q
    ? allReports.filter(r => r.title?.toLowerCase().includes(q) || r.discipline?.toLowerCase().includes(q))
    : allReports;

  if (!list.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-ico">📄</div>
        <h3>${q ? 'Нічого не знайдено' : 'Ще немає звітів'}</h3>
        <p>${q ? 'Спробуй інший пошук' : 'Натисни «Новий звіт» щоб почати'}</p>
      </div>`;
    return;
  }

  grid.innerHTML = list.map(r => `
    <div class="card card-hover report-card fade-in" data-id="${r.id}">
      <div class="rc-top">
        <div class="rc-title">${esc(r.title)}</div>
        <span class="badge badge-purple">${esc((r.discipline || '').slice(0, 14) || 'Без теми')}</span>
      </div>
      <div class="rc-meta">
        <div class="rc-row">👨‍🏫 ${esc(r.teacher || '—')}</div>
        <div class="rc-row">👥 ${esc(r.group || '—')}</div>
      </div>
      <div class="rc-footer">
        <span class="rc-date">${fmtDate(r.created_at)}</span>
        <div class="flex gap-6">
          <button class="btn btn-sm btn-secondary" data-action="dl"  title="Скачати .docx">⬇</button>
          <button class="btn btn-sm btn-danger"    data-action="del" title="Видалити">✕</button>
        </div>
      </div>
    </div>`).join('');

  grid.querySelectorAll('.report-card').forEach(card => {
    const id = parseInt(card.dataset.id);
    card.addEventListener('click', e => {
      const action = e.target.closest('[data-action]')?.dataset.action;
      if (!action) { window.location.href = `editor.html?id=${id}`; return; }
      if (action === 'del') deleteReport(id);
      if (action === 'dl')  downloadDocx(id);
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
  try { await download(`/reports/${id}/download`, `report_${id}.docx`); }
  catch (ex) { toast(ex.message, 'err'); }
}

/* ═══════════════════════════════════════════════════════
   PAGE: EDITOR  (editor.html)
═══════════════════════════════════════════════════════ */
let reportId    = null;
let sections    = [];
let sse_conc    = null;
let sse_gen     = null;

async function initEditor() {
  auth.guard();
  fillSidebar();

  document.getElementById('btn-add-sec')?.addEventListener('click', addSection);
  document.getElementById('btn-save')?.addEventListener('click', saveReport);
  document.getElementById('btn-conclusion')?.addEventListener('click', streamConclusion);
  document.getElementById('btn-generate')?.addEventListener('click', generateDocx);

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

    sections = (r.sections || []).map((s, i) => ({
      id: i, title: s.title || '', text: s.text || '', code: s.code || '', language: s.language || 'python',
    }));
    renderSections();

    if (r.conclusion) {
      const out = document.getElementById('ai-output');
      out.textContent = r.conclusion;
      out.classList.remove('placeholder');
    }
  } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
}

/* ── sections ── */
function addSection() {
  sections.push({ id: Date.now(), title: '', text: '', code: '', language: 'python' });
  renderSections();
  document.querySelectorAll('.section-item').at(-1)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function removeSection(idx) {
  sections.splice(idx, 1);
  renderSections();
}

function renderSections() {
  const container = document.getElementById('sections-container');
  if (!container) return;

  if (!sections.length) {
    container.innerHTML = '<p class="text-sm text-muted" style="text-align:center;padding:18px 0">Натисни «+ Розділ» щоб додати перший розділ</p>';
    return;
  }

  const langs = ['python','javascript','typescript','java','cpp','c','sql','bash','html','css'];

  container.innerHTML = sections.map((sec, i) => `
    <div class="section-item fade-in">
      <div class="section-head">
        <span class="sec-num">${i + 1}</span>
        <input class="sec-name" placeholder="Назва розділу..."
               value="${esc(sec.title)}" oninput="sections[${i}].title = this.value">
        <button class="btn btn-ghost btn-sm" onclick="removeSection(${i})" title="Видалити розділ">✕</button>
      </div>
      <div class="section-body">
        <div class="form-group">
          <label>Текст розділу</label>
          <textarea rows="4" placeholder="Опишіть хід роботи, результати спостережень..."
                    oninput="sections[${i}].text = this.value">${esc(sec.text)}</textarea>
        </div>
        <div class="form-group">
          <label>Код <span class="text-muted text-sm">(необов'язково)</span></label>
          <div class="code-wrap">
            <div class="code-head">
              <select class="lang-select" onchange="sections[${i}].language = this.value">
                ${langs.map(l => `<option value="${l}" ${sec.language === l ? 'selected' : ''}>${l}</option>`).join('')}
              </select>
              <span class="text-sm text-muted font-mono">код</span>
            </div>
            <textarea placeholder="# вставте код тут..." oninput="sections[${i}].code = this.value">${esc(sec.code)}</textarea>
          </div>
        </div>
        <div class="form-group">
          <label>Скріншоти <span class="text-muted text-sm">(необов'язково)</span></label>
          <div class="upload-zone" onclick="triggerUpload(${i})"
               ondragover="event.preventDefault(); this.classList.add('drag')"
               ondragleave="this.classList.remove('drag')"
               ondrop="handleDrop(event,${i}); this.classList.remove('drag')">
            📎 Натисни або перетягни зображення
          </div>
          <input type="file" id="fu-${i}" accept="image/*" multiple style="display:none"
                 onchange="handleFileInput(this, ${i})">
          <div class="img-grid" id="imgs-${i}"></div>
        </div>
      </div>
    </div>`).join('');
}

/* ── file upload ── */
function triggerUpload(i) { document.getElementById(`fu-${i}`)?.click(); }

async function handleDrop(e, i) {
  e.preventDefault();
  const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
  await uploadFiles(files, i);
}

async function handleFileInput(input, i) {
  await uploadFiles(Array.from(input.files), i);
  input.value = '';
}

async function uploadFiles(files, sectionIdx) {
  if (!reportId) { toast('Спочатку збережи звіт', 'err'); return; }
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('report_id', reportId);
    fd.append('section_index', sectionIdx);
    try {
      const res = await fetch(`${API_URL}/upload/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token()}` },
        body: fd,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      appendThumb(sectionIdx, data.url, data.id);
    } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
  }
}

function appendThumb(i, url, imgId) {
  const grid = document.getElementById(`imgs-${i}`);
  if (!grid) return;
  const div = document.createElement('div');
  div.className = 'img-thumb';
  div.dataset.imgId = imgId;
  div.innerHTML = `<img src="${API_URL}${url}" alt="скріншот"><button class="rm" onclick="removeThumb(this)">✕</button>`;
  grid.appendChild(div);
}

function removeThumb(btn) { btn.closest('.img-thumb').remove(); }

/* ── save ── */
async function saveReport() {
  const btn = document.getElementById('btn-save');
  setLoading(btn, true);

  const payload = {
    title:      document.getElementById('f-title').value,
    discipline: document.getElementById('f-discipline').value,
    teacher:    document.getElementById('f-teacher').value,
    group:      document.getElementById('f-group').value,
    goal:       document.getElementById('f-goal').value,
    sections:   sections.map(s => ({ title: s.title, text: s.text, code: s.code, language: s.language })),
  };

  try {
    if (reportId) {
      await req('PATCH', `/reports/${reportId}`, payload);
      toast('Збережено ✓');
    } else {
      const r = await req('POST', '/reports', payload);
      reportId = r.id;
      window.history.replaceState({}, '', `editor.html?id=${reportId}`);
      document.getElementById('editor-heading').textContent = 'Редагування звіту';
      toast('Звіт створено ✓');
    }
  } catch (ex) { toast(ex.message, 'err'); }
  finally      { setLoading(btn, false); }
}

/* ── AI conclusion SSE ── */
function streamConclusion() {
  if (!reportId) { toast('Спочатку збережи звіт', 'err'); return; }
  if (sse_conc)  { sse_conc.close(); sse_conc = null; }

  const out = document.getElementById('ai-output');
  const btn = document.getElementById('btn-conclusion');

  out.classList.remove('placeholder');
  out.classList.add('streaming');
  out.innerHTML = '<span class="ai-cursor"></span>';
  setLoading(btn, true);

  let text = '';
  sse_conc = new EventSource(`${API_URL}/reports/${reportId}/stream-conclusion?token=${auth.token()}`);

  sse_conc.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.token) {
      text += data.token;
      out.innerHTML = esc(text) + '<span class="ai-cursor"></span>';
      out.scrollTop = out.scrollHeight;
    }
    if (data.done) {
      sse_conc.close(); sse_conc = null;
      out.classList.remove('streaming');
      out.textContent = text;
      setLoading(btn, false);
      toast('Висновок згенеровано ✓');
    }
  };

  sse_conc.onerror = () => {
    sse_conc?.close(); sse_conc = null;
    out.classList.remove('streaming');
    if (!text) { out.textContent = ''; out.classList.add('placeholder'); }
    setLoading(btn, false);
    toast('Помилка підключення до AI', 'err');
  };
}

/* ── generate docx ── */
async function generateDocx() {
  if (!reportId) { toast('Спочатку збережи звіт', 'err'); return; }
  if (sse_gen)   { sse_gen.close(); sse_gen = null; }

  const btn      = document.getElementById('btn-generate');
  const pWrap    = document.getElementById('gen-progress');
  const pFill    = document.getElementById('gen-fill');
  const pLbl     = document.getElementById('gen-label');

  pWrap?.classList.remove('hidden');
  if (pFill) pFill.style.width = '0%';
  if (pLbl)  pLbl.textContent  = 'Запускаємо генерацію...';
  setLoading(btn, true);

  try {
    const genData = await req('POST', `/reports/${reportId}/generate`);

    sse_gen = new EventSource(`${API_URL}/reports/${reportId}/generate/status?task_id=${genData.task_id}&token=${auth.token()}`);

    sse_gen.onmessage = async e => {
      const data = JSON.parse(e.data);
      if (pFill) pFill.style.width = `${data.progress ?? 0}%`;
      if (pLbl)  pLbl.textContent  = data.message || '';

      if (data.status === 'done') {
        sse_gen.close(); sse_gen = null;
        pWrap?.classList.add('hidden');
        setLoading(btn, false);
        toast('Документ готовий! Завантажується...');
        try { await download(`/reports/${reportId}/download`, `report_${reportId}.docx`); }
        catch (ex) { toast(ex.message, 'err'); }
      } else if (data.status === 'error') {
        sse_gen.close(); sse_gen = null;
        pWrap?.classList.add('hidden');
        setLoading(btn, false);
        toast(data.message || 'Помилка генерації', 'err');
      }
    };

    sse_gen.onerror = () => {
      if (!sse_gen) return;   // already closed cleanly in onmessage — ignore
      sse_gen.close(); sse_gen = null;
      pWrap?.classList.add('hidden');
      setLoading(btn, false);
      toast('Помилка підключення', 'err');
    };

  } catch (ex) {
    pWrap?.classList.add('hidden');
    setLoading(btn, false);
    toast(ex.message, 'err');
  }
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
