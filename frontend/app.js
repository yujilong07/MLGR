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

  // 401 on a normal request = the session expired -> back to the start page. But a wrong password
  // on /auth/login is also 401: that one must reach the form as an error message
  if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
    auth.clearToken(); auth.clearUser(); window.location.href = 'index.html'; return;
  }
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
  left:     '<svg class="icon" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6"/></svg>',
  right:    '<svg class="icon" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg>',
  expand:   '<svg class="icon" viewBox="0 0 24 24"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>',
  down:     '<svg class="icon" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>',
  undo:     '<svg class="icon" viewBox="0 0 24 24"><path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/></svg>',
  redo:     '<svg class="icon" viewBox="0 0 24 24"><path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/></svg>',
  code:     '<svg class="icon" viewBox="0 0 24 24"><path d="m8 7-5 5 5 5M16 7l5 5-5 5"/></svg>',
  edit:     '<svg class="icon" viewBox="0 0 24 24"><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  sigma:    '<svg class="icon" viewBox="0 0 24 24"><path d="M18 5H6l6 7-6 7h12"/></svg>',
  text:     '<svg class="icon" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
  table:    '<svg class="icon" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 10v10M15 10v10"/></svg>',
  python:   '<svg class="icon" viewBox="0 0 24 24"><path d="M12 3c-3.5 0-4 1.5-4 3v2h4.5v1H6c-2 0-3 1.5-3 4s1 4 3 4h2v-2.5c0-1.4 1.1-2.5 2.5-2.5h4c1.4 0 2.5-1.1 2.5-2.5V6c0-1.5-1.5-3-5-3z"/><path d="M12 21c3.5 0 4-1.5 4-3v-2h-4.5v-1H18c2 0 3-1.5 3-4"/></svg>',
  eye:      '<svg class="icon" viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
};
const sortImages = list => [...list].sort((a, b) => (a.position ?? 0) - (b.position ?? 0) || a.id - b.id);
const imagesIn = (images, path) => sortImages(images.filter(im => im.section_path === path));
// document order: by section ("0" < "0.1" < "1"), then by position inside a section
const docOrder = images => sortImages(images).sort((a, b) => a.section_path.localeCompare(b.section_path, undefined, { numeric: true }));
function esc(s) { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

/* ═══════════════════════════════════════════════════════
   FORMULAS  (KaTeX in the browser; the server makes Word
   equations / SVG from the same LaTeX)
═══════════════════════════════════════════════════════ */
const KATEX_BASE = 'https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11';
let katexPromise = null;

function ensureKatex() {
  if (window.katex) return Promise.resolve(window.katex);
  katexPromise ??= new Promise((resolve, reject) => {
    document.head.appendChild(Object.assign(document.createElement('link'), { rel: 'stylesheet', href: `${KATEX_BASE}/katex.min.css` }));
    const s = Object.assign(document.createElement('script'), { src: `${KATEX_BASE}/katex.min.js`, async: true });
    s.onload = () => resolve(window.katex);
    s.onerror = () => { katexPromise = null; reject(new Error('KaTeX не завантажився')); };
    document.head.appendChild(s);
  });
  return katexPromise;
}

// HTML for one formula; before KaTeX has loaded (or offline) the LaTeX source is shown
function mathHtml(latex, display = false) {
  if (!latex?.trim()) return '';
  if (!window.katex) return `<code class="math-src">${esc(latex)}</code>`;
  return window.katex.renderToString(latex, { displayMode: display, throwOnError: false, strict: 'ignore', output: 'html' });
}

// "$x$" in text: the same rule as the server (\$ is a literal dollar)
const INLINE_MATH = /(?<!\\)\$(.+?)(?<!\\)\$/g;
const hasInlineMath = text => /(?<!\\)\$(.+?)(?<!\\)\$/.test(text || '');
const unescapeDollar = s => s.replace(/\\\$/g, '$');

// One line of text with its inline formulas rendered
function inlineHtml(line) {
  let out = '', pos = 0;
  for (const m of String(line).matchAll(INLINE_MATH)) {
    out += esc(unescapeDollar(line.slice(pos, m.index))) + mathHtml(m[1].trim());
    pos = m.index + m[0].length;
  }
  return out + esc(unescapeDollar(line.slice(pos)));
}

/* ── content model: a section is an ordered list of blocks ── */
// {type: 'text', text} | {type: 'code', code, language} | {type: 'formula', latex}
function itemBlocks(item) {
  if (Array.isArray(item?.blocks)) return item.blocks.filter(b => ['text', 'code', 'formula', 'table'].includes(b?.type));
  const out = [];
  if (item?.text?.trim()) out.push({ type: 'text', text: item.text });
  if (item?.code?.trim()) out.push({ type: 'code', code: item.code, language: item.language || 'python' });
  return out;
}

const newTextBlock    = () => ({ type: 'text', text: '' });
const newCodeBlock    = () => ({ type: 'code', code: '', language: 'python' });
const newFormulaBlock = () => ({ type: 'formula', latex: '' });
const newTableBlock   = () => ({ type: 'table', caption: '', header: 1, rows: [['', '', ''], ['', '', '']] });
// ДСТУ 3008:2015: appendices use the Ukrainian alphabet without Ґ, Є, З, І, Ї, Й, О, Ч, Ь
const APPENDIX_LETTERS = 'АБВГДЕЖИКЛМНПРСТУФХЦШЩЮЯ';
const newItem = withSubs => ({ title: '', blocks: [newTextBlock()], ...(withSubs ? { subsections: [] } : {}) });

// Sections nest three levels deep (1, 1.1, 1.1.1); appendix: true marks ДОДАТОК А, Б, ...
function toEditableSections(raw) {
  const item = (s, depth) => {
    const blocks = itemBlocks(s).map(b => b.type === 'table'
      ? { ...b, rows: (b.rows || []).map(r => [...r]) } : { ...b });
    const out = { title: s.title || '', blocks: blocks.length ? blocks : [newTextBlock()] };
    if (depth < 3) out.subsections = (s.subsections || []).map(c => item(c, depth + 1));
    if (depth === 1 && s.appendix) out.appendix = true;
    return out;
  };
  return (raw || []).map(s => item(s, 1));
}

function sectionsPayload(list) {
  const blocks = item => item.blocks
    .map(b => b.type === 'text' ? { type: 'text', text: b.text || '' }
      : b.type === 'code' ? { type: 'code', code: b.code || '', language: b.language || 'python' }
      : b.type === 'table' ? { type: 'table', caption: b.caption || '', header: b.header ?? 1, rows: b.rows || [] }
      : { type: 'formula', latex: b.latex || '' })
    .filter(b => !(b.type === 'text' && !b.text.trim()));
  const item = (s, depth) => ({
    title: s.title, blocks: blocks(s),
    ...(depth < 3 ? { subsections: (s.subsections || []).map(c => item(c, depth + 1)) } : {}),
    ...(depth === 1 && s.appendix ? { appendix: true } : {}),
  });
  return list.map(s => item(s, 1));
}

const blockFilled = b => b.type === 'table'
  ? (b.rows || []).some(r => r.some(c => (c || '').trim())) || Boolean((b.caption || '').trim())
  : Boolean((b.type === 'text' ? b.text : b.type === 'code' ? b.code : b.latex)?.trim());
const itemText = item => (item.blocks || []).filter(b => b.type === 'text').map(b => b.text).join('\n').trim();
const hasContent = item => Boolean(item.title?.trim() || item.blocks?.some(blockFilled) || item.subsections?.length);

/* ── LaTeX source helpers (mirror of backend latex_doc.escape_text) ── */
const TEX_ESC = {
  '\\': '\\textbackslash{}', '&': '\\&', '%': '\\%', '#': '\\#', '_': '\\_',
  '{': '\\{', '}': '\\}', '~': '\\textasciitilde{}', '^': '\\textasciicircum{}', '$': '\\$',
};
const texEscape = text => String(text).replace(/[\\&%#_{}~^$]/g, ch => TEX_ESC[ch]);

function inlineToLatex(line) {
  let out = '', pos = 0;
  for (const m of String(line).matchAll(INLINE_MATH)) {
    out += texEscape(unescapeDollar(line.slice(pos, m.index))) + `$${m[1]}$`;
    pos = m.index + m[0].length;
  }
  return out + texEscape(unescapeDollar(line.slice(pos)));
}
const textToLatexParas = text => String(text || '').split('\n').map(l => l.trim()).filter(Boolean).map(inlineToLatex).join('\n\n');

// Replaces the body of \section*{<one of names>} up to the next \section / bibliography / end;
// adds the section when it is missing
function latexReplaceSection(src, names, body, { atStart = false } = {}) {
  const re = new RegExp(`\\\\section\\*\\s*\\{\\s*(${names.join('|')})\\s*\\}`, 'i');
  const m = re.exec(src);
  if (!m) {
    const block = `\\section*{${names[0]}}\n\n${body}\n\n`;
    if (atStart) return block + src;
    const tail = src.search(/\\begin\{thebibliography\}|\\end\{document\}/);
    return tail === -1 ? `${src.trimEnd()}\n\n${block}` : src.slice(0, tail) + block + src.slice(tail);
  }
  const start = m.index + m[0].length;
  const next = src.slice(start).search(/\\section\*?\s*\{|\\begin\{thebibliography\}|\\end\{document\}/);
  const end = next === -1 ? src.length : start + next;
  return `${src.slice(0, start)}\n\n${body}\n\n${src.slice(end).replace(/^\s+/, '')}`;
}

// Snippets for the formula toolbar: [label, latex, cursor offset from the end]
const MATH_SNIPPETS = [
  ['a/b', '\\frac{}{}', 3], ['√', '\\sqrt{}', 1], ['xⁿ', '^{}', 1], ['xᵢ', '_{}', 1],
  ['Σ', '\\sum_{i=1}^{n} ', 0], ['∫', '\\int_{a}^{b} ', 0], ['lim', '\\lim_{x \\to 0} ', 0],
  ['α', '\\alpha ', 0], ['β', '\\beta ', 0], ['σ', '\\sigma ', 0], ['θ', '\\theta ', 0], ['λ', '\\lambda ', 0],
  ['≤', '\\le ', 0], ['≥', '\\ge ', 0], ['≠', '\\ne ', 0], ['·', '\\cdot ', 0], ['∞', '\\infty ', 0],
  ['x̂', '\\hat{}', 1], ['x̄', '\\bar{}', 1], ['ℝ', '\\mathbb{R}', 0],
];

function insertAtCursor(el, text, back = 0) {
  el.focus();
  const { selectionStart: a, selectionEnd: b, value } = el;
  el.value = value.slice(0, a) + text + value.slice(b);
  const pos = a + text.length - back;
  el.setSelectionRange(pos, pos);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

/* Python -> LaTeX (latexify on the server; the code is parsed, never run) */
function openPyDialog(onInsert) {
  const box = document.createElement('div');
  box.className = 'modal-wrap';
  box.innerHTML = `
    <div class="modal card" role="dialog" aria-modal="true" aria-label="Формула з Python">
      <div class="panel-head"><h2 class="panel-title">Формула з Python-коду</h2>
        <button class="pv-icon-btn" data-close title="Закрити">${ICONS.x}</button></div>
      <div class="panel-body">
        <p class="text-sm text-muted">Вставте функцію, вираз або присвоєння — бібліотека
          <a href="https://github.com/google/latexify_py" target="_blank" rel="noopener">latexify</a> перетворить їх на формулу.
          Код не виконується.</p>
        <div class="code-wrap"><textarea class="py-src" spellcheck="false" rows="5"
          placeholder="def sigmoid(x):&#10;    return 1 / (1 + math.exp(-x))"></textarea></div>
        <div class="py-result"></div>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button class="btn btn-ghost btn-sm" data-close>Скасувати</button>
          <button class="btn btn-secondary btn-sm" data-convert>Перетворити</button>
          <button class="btn btn-primary btn-sm" data-insert disabled>Вставити</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(box);
  const src = box.querySelector('.py-src'), result = box.querySelector('.py-result');
  const insertBtn = box.querySelector('[data-insert]');
  let latex = '';
  const close = () => { document.removeEventListener('keydown', onKey, true); box.remove(); };
  const onKey = e => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  const convert = async () => {
    const btn = box.querySelector('[data-convert]');
    setLoading(btn, true);
    try {
      const r = await req('POST', '/latex/from-python', { source: src.value });
      latex = r.latex;
      result.innerHTML = `<div class="py-math">${mathHtml(latex, true)}</div><code class="math-src">${esc(latex)}</code>`
        + (r.error ? `<p class="text-sm warn-text">У Word/PDF формула може відобразитись неточно: ${esc(r.error)}</p>` : '');
      insertBtn.disabled = false;
    } catch (ex) {
      latex = '';
      result.innerHTML = `<div class="error-box">${esc(ex.message)}</div>`;
      insertBtn.disabled = true;
    } finally { setLoading(btn, false); }
  };
  box.addEventListener('click', e => {
    if (e.target === box || e.target.closest('[data-close]')) close();
    if (e.target.closest('[data-convert]')) convert();
    if (e.target.closest('[data-insert]') && latex) { onInsert(latex); close(); }
  });
  src.addEventListener('keydown', e => {
    if (e.key === 'Tab') { e.preventDefault(); insertAtCursor(src, '    '); }
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) convert();
  });
  document.addEventListener('keydown', onKey, true);
  src.focus();
}

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
  document.getElementById('nav-profile')?.addEventListener('click', e => { e.preventDefault(); openProfileModal(); });
}

/* ═══════════════════════════════════════════════════════
   TITLE PAGE TEMPLATES  (GET /templates — the same JSON the
   .docx / PDF / LaTeX builders draw; services/templates.py)
═══════════════════════════════════════════════════════ */
let DOC_TPL = null;
let tplPromise = null;

function loadTemplates() {
  if (DOC_TPL) return Promise.resolve(DOC_TPL);
  tplPromise ??= req('GET', '/templates')
    .then(data => (DOC_TPL = data))
    .catch(ex => { tplPromise = null; throw ex; });
  return tplPromise;
}

const FIELD_PH = {
  ministry: 'міністерство', institution: 'назва навчального закладу', city: 'місто',
  faculty: 'факультет', department: 'кафедра', discipline: 'дисципліна / предмет',
  title: 'тема / назва роботи', group: 'група / клас', teacher: 'Прізвище І. Б.',
  teacher_position: 'посада', work_date: 'дата',
};

// Datalist with Ukrainian universities for the institution field (free text stays allowed)
function institutionOptions() {
  return (DOC_TPL?.institutions || []).map(i => `<option value="${esc(i.name)}">${esc(i.city)}</option>`).join('');
}
const cityOf = name => DOC_TPL?.institutions.find(i => i.name === name)?.city;

/**
 * The title page of `doc` from its template. editAttr(bind, ph, kind) gives the
 * attributes of an editable field (or plain ones in the read-only preview).
 */
function titlePageHtml(doc, editAttr, editable) {
  const tpl = DOC_TPL?.templates[`${doc.level || 'university'}_${doc.kind || 'lab'}`]
           || DOC_TPL?.templates[`university_${doc.kind || 'lab'}`];
  if (!tpl) return `<section class="dv-sheet dv-title"><p>${esc(doc.title)}</p></section>`;

  const names = docLines(doc.student_name);
  const yearMatch = (doc.work_date || '').trim().slice(-4);
  const year = /^\d{4}$/.test(yearMatch) ? yearMatch : String(new Date().getFullYear());
  const word = key => {
    const f = tpl.words[key];
    const k = f.of === 'student'
      ? (names.length > 1 ? 'pl' : doc.student_gender === 'f' ? 'f' : 'm')
      : (doc.teacher_gender === 'f' ? 'f' : 'm');
    return f[k] || f.m;
  };
  const field = name => `<span ${editAttr(`doc|${name}`, FIELD_PH[name] || name)}>${esc(doc[name] || '')}</span>`;
  const namesBlock = () =>
    `<span class="dv-names dv-text" ${editAttr('doc|student_name', 'Прізвище І. Б. (кожен з нового рядка)', 'paras')}>${mathParas(doc.student_name)}</span>`;
  const teachersBlock = () =>
    `<span class="dv-names dv-text" ${editAttr('doc|teacher', 'посада Прізвище І. Б. (кожен з нового рядка)', 'paras')}>${mathParas(doc.teacher)}</span>`;
  const cw = courseWords(doc.meta);
  const computed = { course_title: cw.title, topic_hint: cw.topic_hint, doc_code: doc.meta?.doc_code || '' };
  const city = editable || doc.city ? field('city') : '';

  // Text with {placeholders} -> HTML; empty: whether all placeholders were empty
  const fill = text => {
    let empty = true, html = '', pos = 0;
    for (const m of text.matchAll(/\{(\w+)\}/g)) {
      html += esc(text.slice(pos, m.index));
      pos = m.index + m[0].length;
      const key = m[1];
      if (tpl.words[key]) {
        const of = tpl.words[key].of;
        html += editable && !(of === 'student' && names.length > 1)
          ? `<button class="dv-gender" data-gender="${of}" title="Натисніть, щоб змінити рід">${esc(word(key))}</button>`
          : esc(word(key));
        empty = false;
      } else if (key === 'student' || key === 'students') {
        html += namesBlock();
        empty = empty && !names.length;
      } else if (key === 'supervisor') {
        html += teachersBlock();
        empty = empty && !docLines(doc.teacher).length;
      } else if (key in computed) {
        html += esc(computed[key]);
        if (computed[key]) empty = false;
      } else if (key === 'city_year') {
        html += city ? `${city} ${year}` : year;
        empty = false;
      } else if (key === 'city_dash_year') {
        html += city ? `${city} – ${year}` : year;
        empty = false;
      } else if (key === 'city_year_r') {
        html += city ? `${city} ${year} р.` : `${year} р.`;
        empty = false;
      } else if (key === 'year') {
        html += year; empty = false;
      } else {
        html += field(key);
        if ((doc[key] || '').trim()) empty = false;
      }
    }
    html += esc(text.slice(pos));
    return { html, empty };
  };
  const visible = (spec, text) => !(spec.optional && /\{\w+\}/.test(text) && fill(text).empty && !editable);

  const out = tpl.title_page.map(el => {
    if (el.t === 'line') {
      if (!visible(el, el.text)) return '';
      const style = `text-align:${el.align || 'center'};font-size:${el.size || 14}pt;${el.bold ? 'font-weight:bold;' : ''}`;
      return `<p style="${style}">${fill(el.text).html || '&nbsp;'}</p>`;
    }
    if (el.t === 'blank') return '<p>&nbsp;</p>'.repeat(el.n);
    if (el.t === 'field') {
      if (!visible(el, el.value)) return '';
      return `<div class="dv-field"><span class="lbl">${fill(el.label).html}</span><span class="u">${fill(el.value).html}</span></div>`
        + (el.hint ? `<p class="dv-hint">${fill(el.hint).html}</p>` : '');
    }
    if (el.t === 'columns') {
      const col = lines => lines.map(item => {
        const spec = typeof item === 'string' ? { text: item } : item;
        if (!spec.text) return '<p>&nbsp;</p>';
        if (!visible(spec, spec.text)) return '';
        return `<p>${fill(spec.text).html}</p>`;
      }).join('');
      return `<div class="dv-sign"><div>${col(el.left)}</div><div>${col(el.right)}</div></div>`;
    }
    if (el.t === 'push') return '<div class="dv-push"></div>';
    return '';
  }).join('');
  return `<section class="dv-sheet dv-title">${out}</section>`;
}

/* "Мої дані": defaults for every new report */
const PROFILE_FIELDS = ['level', 'ministry', 'institution', 'city', 'faculty', 'department', 'group', 'student_name', 'student_gender'];
let profileCache = null;

async function loadProfile() {
  if (profileCache) return profileCache;
  try { profileCache = await req('GET', '/auth/profile'); } catch { profileCache = {}; }
  return profileCache;
}

async function saveProfile(values) {
  const body = {};
  PROFILE_FIELDS.forEach(k => { if (values[k] !== undefined && values[k] !== '') body[k] = values[k]; });
  profileCache = await req('PUT', '/auth/profile', body);
  return profileCache;
}

async function openProfileModal() {
  await loadTemplates().catch(() => {});
  const p = await loadProfile();
  const box = document.createElement('div');
  box.className = 'modal-wrap';
  const school = p.level === 'school';
  box.innerHTML = `
    <form class="modal card profile-modal" role="dialog" aria-modal="true" aria-label="Мої дані">
      <div class="panel-head"><h2 class="panel-title">Мої дані</h2>
        <button type="button" class="pv-icon-btn" data-close title="Закрити">${ICONS.x}</button></div>
      <div class="panel-body">
        <p class="text-sm text-muted">Заповніть один раз — і кожен новий звіт чи реферат стартуватиме з цими даними.</p>
        <div class="seg seg-lg" data-pf-level>
          <button type="button" data-v="university" class="${school ? '' : 'on'}">Університет / коледж</button>
          <button type="button" data-v="school" class="${school ? 'on' : ''}">Школа, ліцей, гімназія</button>
        </div>
        <div class="form-group"><label>Назва закладу</label>
          <input name="institution" list="pf-institutions" value="${esc(p.institution || '')}" placeholder="Харківський національний університет радіоелектроніки">
          <datalist id="pf-institutions">${institutionOptions()}</datalist></div>
        <div class="form-row">
          <div class="form-group"><label>Місто</label><input name="city" value="${esc(p.city || '')}" placeholder="Харків"></div>
          <div class="form-group"><label>${school ? 'Клас' : 'Група'}</label><input name="group" value="${esc(p.group || '')}" placeholder="${school ? '9-А' : 'КНТ-22-1'}"></div>
        </div>
        <div class="form-row pf-uni ${school ? 'hidden' : ''}">
          <div class="form-group"><label>Факультет</label><input name="faculty" value="${esc(p.faculty || '')}" placeholder="Комп’ютерних наук"></div>
          <div class="form-group"><label>Кафедра</label><input name="department" value="${esc(p.department || '')}" placeholder="штучного інтелекту"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Прізвище та ініціали</label><input name="student_name" value="${esc(p.student_name || '')}" placeholder="Петренко О. О."></div>
          <div class="form-group"><label>Рід у титулці</label>
            <div class="seg" data-pf-gender>
              <button type="button" data-v="m" class="${p.student_gender === 'f' ? '' : 'on'}">Виконав</button>
              <button type="button" data-v="f" class="${p.student_gender === 'f' ? 'on' : ''}">Виконала</button>
            </div></div>
        </div>
        <div class="form-group"><label>Рядок над назвою закладу <span class="text-muted">— можна очистити</span></label>
          <input name="ministry" value="${esc(p.ministry ?? DOC_TPL?.ministry_default ?? '')}"></div>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button type="button" class="btn btn-ghost btn-sm" data-close>Скасувати</button>
          <button type="submit" class="btn btn-primary btn-sm">Зберегти</button>
        </div>
      </div>
    </form>`;
  document.body.appendChild(box);
  const form = box.querySelector('form');
  const segValue = sel => form.querySelector(`${sel} .on`)?.dataset.v;
  const close = () => { document.removeEventListener('keydown', onKey, true); box.remove(); };
  const onKey = e => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  box.addEventListener('click', e => {
    if (e.target === box || e.target.closest('[data-close]')) close();
    const opt = e.target.closest('[data-pf-level] [data-v], [data-pf-gender] [data-v]');
    if (opt) {
      opt.parentElement.querySelectorAll('[data-v]').forEach(b => b.classList.toggle('on', b === opt));
      if (opt.closest('[data-pf-level]')) {
        const isSchool = opt.dataset.v === 'school';
        form.querySelector('.pf-uni').classList.toggle('hidden', isSchool);
        form.querySelector('[name="group"]').previousElementSibling.textContent = isSchool ? 'Клас' : 'Група';
      }
    }
  });
  form.institution.addEventListener('change', () => { if (!form.city.value) form.city.value = cityOf(form.institution.value) || ''; });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    values.level = segValue('[data-pf-level]');
    values.student_gender = segValue('[data-pf-gender]');
    try {
      await saveProfile(values);
      toast('Збережено — нові звіти заповнюватимуться автоматично');
      close();
      document.dispatchEvent(new CustomEvent('profile-saved'));
    } catch (ex) { toast(ex.message, 'err'); }
  });
  document.addEventListener('keydown', onKey, true);
  form.institution.focus();
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

  const showTab = name => {
    tabs.forEach(x => x.classList.toggle('active', x.dataset.tab === name));
    loginForm.classList.toggle('hidden', name !== 'login');
    regForm.classList.toggle('hidden', name === 'login');
  };
  tabs.forEach(t => t.addEventListener('click', () => showTab(t.dataset.tab)));

  // Server messages -> what a person can act on
  const explain = msg => {
    if (/valid email|@-sign|period/i.test(msg)) return 'Перевірте адресу пошти — вона має виглядати як name@gmail.com.';
    if (/at least 8|8 символів/i.test(msg)) return 'Пароль має містити щонайменше 8 символів.';
    if (/Too Many|Rate limit|exceeded/i.test(msg)) return 'Забагато спроб. Зачекайте хвилину й спробуйте ще раз.';
    if (/Failed to fetch|NetworkError/i.test(msg)) return 'Сервер не відповідає — можливо, він прокидається. Спробуйте за 30 секунд.';
    return msg;
  };
  const showError = (box, html) => { box.innerHTML = html; box.classList.remove('hidden'); };

  // The browser's own hints are in its UI language and vague; say exactly what is wrong
  const regEmail = document.getElementById('reg-email');
  const regPass = document.getElementById('reg-pass');
  regEmail?.addEventListener('input', () => regEmail.setCustomValidity(
    regEmail.validity.patternMismatch || regEmail.validity.typeMismatch
      ? 'Адреса пошти має виглядати як name@gmail.com — з крапкою після @' : ''));
  regPass?.addEventListener('input', () => regPass.setCustomValidity(
    regPass.validity.tooShort ? `Пароль закороткий: ${regPass.value.length} з 8 символів` : ''));

  loginForm?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = loginForm.querySelector('[type=submit]');
    const err = document.getElementById('login-err');
    err.classList.add('hidden');
    setLoading(btn, true);
    try {
      const data = await req('POST', '/auth/login', {
        email:    document.getElementById('login-email').value.trim(),
        password: document.getElementById('login-pass').value,
      });
      auth.setToken(data.access_token);
      auth.setUser(data.user);
      window.location.href = 'dashboard.html';
    } catch (ex) {
      const unknown = /Неправильна пошта|Invalid credentials/.test(ex.message);
      showError(err, esc(explain(ex.message)) + (unknown
        ? ' <br>Ще немає акаунта? <a href="#" data-to-register>Зареєструйтесь</a> — це хвилина.' : ''));
      err.querySelector('[data-to-register]')?.addEventListener('click', ev => {
        ev.preventDefault();
        document.getElementById('reg-email').value = document.getElementById('login-email').value;
        showTab('register');
        document.getElementById('reg-pass').focus();
      });
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
        email:    document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-pass').value,
      });
      auth.setToken(data.access_token);
      auth.setUser(data.user);
      window.location.href = 'dashboard.html';
    } catch (ex) {
      const exists = /вже існує|already exists/.test(ex.message);
      showError(err, esc(explain(ex.message)) + (exists ? ' <a href="#" data-to-login>Перейти до входу</a>' : ''));
      err.querySelector('[data-to-login]')?.addEventListener('click', ev => {
        ev.preventDefault();
        document.getElementById('login-email').value = document.getElementById('reg-email').value;
        showTab('login');
        document.getElementById('login-pass').focus();
      });
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

  ['btn-new', 'nav-new'].forEach(id => document.getElementById(id)?.addEventListener('click', e => {
    e.preventDefault();
    openNewChooser();
  }));

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
  showProfileHint();
  document.addEventListener('profile-saved', () => document.getElementById('profile-hint')?.remove());
}

async function showProfileHint() {
  const p = await loadProfile();
  if (p.institution) return;
  const hint = document.createElement('div');
  hint.id = 'profile-hint';
  hint.className = 'profile-hint';
  hint.innerHTML = `<div><b>Вкажіть свій навчальний заклад один раз</b>
      <span>Університет, коледж чи школа, група або клас, ПІБ — і вони підставлятимуться в кожен новий звіт.</span></div>
    <button class="btn btn-primary btn-sm">Заповнити</button>`;
  hint.querySelector('button').onclick = openProfileModal;
  document.querySelector('.stats-bar')?.before(hint);
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
        ${r.kind === 'essay' ? '<span class="badge badge-kind">Реферат</span>' : r.kind === 'course' ? '<span class="badge badge-kind">Курсова</span>' : ''}
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

/* "New": lab report or essay — they have different title pages and structure */
async function openNewChooser() {
  const level = (await loadProfile()).level === 'school' ? 'school' : 'university';
  const box = document.createElement('div');
  box.className = 'modal-wrap';
  box.innerHTML = `
    <div class="modal card chooser" role="dialog" aria-modal="true" aria-label="Що створюємо">
      <div class="panel-head"><h2 class="panel-title">Що створюємо?</h2>
        <button class="pv-icon-btn" data-close title="Закрити">${ICONS.x}</button></div>
      <div class="chooser-level">
        <div class="seg seg-lg" role="radiogroup" aria-label="Тип закладу">
          <button type="button" data-level="university" class="${level === 'university' ? 'on' : ''}">Університет / коледж</button>
          <button type="button" data-level="school" class="${level === 'school' ? 'on' : ''}">Школа, ліцей, гімназія</button>
        </div>
      </div>
      <div class="chooser-grid">
        <a class="chooser-card" href="editor.html?kind=lab">
          <span class="chooser-ico">${ICONS.code}</span>
          <b>Лабораторна / практична</b>
          <span>Мета роботи, хід роботи з кодом і скріншотами, висновки. Титулка «Виконав / Прийняла».</span>
        </a>
        <a class="chooser-card" href="editor.html?kind=essay">
          <span class="chooser-ico">${ICONS.file}</span>
          <b>Реферат</b>
          <span>Вступ, розділи з нової сторінки, висновки, перелік посилань (ДСТУ 3008:2015). Титулка «РЕФЕРАТ на тему».</span>
        </a>
        <a class="chooser-card" href="editor.html?kind=course" data-uni-only>
          <span class="chooser-ico">${ICONS.table}</span>
          <b>Курсова робота / проєкт</b>
          <span>Пояснювальна записка: кілька керівників, завдання й календарний план, 3 рівні заголовків, таблиці, додатки.</span>
        </a>
      </div>
      <p class="text-sm text-muted chooser-note">Скрізь можна писати формули ($x^2$ у тексті або окремим блоком), додавати таблиці й перемкнутись у режим LaTeX.</p>
    </div>`;
  const close = () => { document.removeEventListener('keydown', onKey, true); box.remove(); };
  const onKey = e => { if (e.key === 'Escape') close(); };
  const setLevel = lv => {
    box.querySelectorAll('[data-level]').forEach(b => b.classList.toggle('on', b.dataset.level === lv));
    box.querySelectorAll('[data-uni-only]').forEach(c => { c.hidden = lv === 'school'; });
    box.querySelectorAll('.chooser-card').forEach(a => {
      const kind = new URL(a.href).searchParams.get('kind');
      a.href = `editor.html?kind=${kind}&level=${lv}`;
    });
  };
  box.addEventListener('click', e => {
    if (e.target === box || e.target.closest('[data-close]')) close();
    const lv = e.target.closest('[data-level]')?.dataset.level;
    if (lv) setLevel(lv);
  });
  setLevel(level);
  document.addEventListener('keydown', onKey, true);
  document.body.appendChild(box);
  box.querySelector('.chooser-card')?.focus();
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
let reportKind   = 'lab';                       // 'lab' | 'essay' (реферат)
let reportLevel  = 'university';                // 'university' (also college) | 'school'
let editorMode   = 'form';                      // 'form' | 'latex'
let sections     = [];
let sse_conc     = null;
let reportImages = [];                          // [{id, url, caption, section_path, position}]
const genders    = { student: 'm', teacher: 'f' };
// LaTeX mode: the source is kept as typed; the server parses it into the same structure
const tex = { source: '', warnings: [], timer: null, saveTimer: null, dirty: false };

const KIND_TEXT = {
  lab:   { heading: 'Звіт', title: 'Назва роботи', titlePh: 'Лабораторна робота №1. Дослідження алгоритмів сортування',
           hint: 'Титулка, зміст і нумерація складуться автоматично' },
  essay: { heading: 'Реферат', title: 'Тема реферату', titlePh: 'Методи оптимізації нейронних мереж',
           hint: 'ДСТУ 3008:2015: кожен розділ з нової сторінки, нумерація в межах розділу' },
  course: { heading: 'Курсова', title: 'Тема курсової', titlePh: 'Аналіз навантаженості плоских важільних механізмів',
            hint: 'Титулка, завдання й календарний план, 3 рівні заголовків, таблиці, додатки' },
};

async function initEditor() {
  auth.guard();
  fillSidebar();
  ensureKatex().then(() => { renderSections(); refreshLive(); }).catch(() => {});
  // Title pages come from the server's templates; without them the preview shows a stub
  await loadTemplates().catch(() => toast('Не вдалося завантажити шаблони титулок', 'err'));
  const list = document.getElementById('institution-list');
  if (list) list.innerHTML = institutionOptions();
  document.getElementById('f-institution')?.addEventListener('change', e => {
    const city = document.getElementById('f-city');
    if (city && !city.value) { city.value = cityOf(e.target.value) || ''; refreshLive(); }
  });
  document.getElementById('level-seg')?.addEventListener('click', e => {
    const lv = e.target.closest('[data-level]')?.dataset.level;
    if (lv && lv !== reportLevel) setLevel(lv);
  });
  document.getElementById('btn-remember')?.addEventListener('click', rememberProfile);
  const tourBtn = document.getElementById('btn-tour');
  tourBtn?.addEventListener('click', startTour);
  tourBtn?.classList.toggle('is-new', tourState() !== 'done');

  ['btn-add-sec', 'btn-add-sec-bottom', 'btn-add-sec-side'].forEach(id =>
    document.getElementById(id)?.addEventListener('click', addSection));
  document.getElementById('btn-save')?.addEventListener('click', () => saveReport());
  document.getElementById('btn-conclusion')?.addEventListener('click', streamConclusion);
  document.getElementById('btn-generate')?.addEventListener('click', generateDocx);
  document.getElementById('btn-preview')?.addEventListener('click', previewReport);
  document.getElementById('btn-tex')?.addEventListener('click', downloadTex);
  document.getElementById('btn-intro')?.addEventListener('click', draftIntroduction);

  document.querySelectorAll('.seg[data-gender]').forEach(seg => seg.addEventListener('click', e => {
    const g = e.target.closest('[data-g]')?.dataset.g;
    if (g) setGender(seg.dataset.gender, g);
  }));
  document.getElementById('kind-seg')?.addEventListener('click', e => {
    const k = e.target.closest('[data-kind]')?.dataset.kind;
    if (k && k !== reportKind) setKind(k);
  });
  document.getElementById('mode-seg')?.addEventListener('click', e => {
    const m = e.target.closest('[data-mode]')?.dataset.mode;
    if (m && m !== editorMode) switchMode(m);
  });
  setGender('student', 'm');
  setGender('teacher', 'f');

  ['f-title', 'f-discipline', 'f-group', 'f-student', 'f-teacher', 'f-goal', 'f-intro', 'f-refs', 'ai-output', 'f-institution'].forEach(id =>
    document.getElementById(id)?.addEventListener('input', updateReadiness));
  document.getElementById('f-student')?.addEventListener('input', updateStudentSeg);
  // In LaTeX mode the conclusion box writes into \section*{Висновки} of the source
  document.getElementById('ai-output')?.addEventListener('input', e => {
    if (editorMode === 'latex') syncTexSection(['Висновки', 'Висновок'], e.target.value);
  });

  for (const secs of [document.getElementById('sections-container'), document.getElementById('appendix-container')]) {
    secs?.addEventListener('click', onImageCardEvent);
    secs?.addEventListener('input', onImageCardEvent);
    secs?.addEventListener('click', onBlocksClick);
    secs?.addEventListener('input', onBlocksInput);
    secs?.addEventListener('change', onBlocksInput);
    secs?.addEventListener('paste', onTablePaste);
    secs?.addEventListener('keydown', e => {
      if (e.key === 'Tab' && e.target.matches('.code-wrap textarea')) { e.preventDefault(); insertAtCursor(e.target, '    '); }
    });
  }
  document.getElementById('btn-add-app')?.addEventListener('click', addAppendix);
  bindCourseCard();
  document.getElementById('unplaced')?.addEventListener('change', placeImage);

  // Text fields grow with their content instead of scrolling inside a small box
  document.addEventListener('input', e => {
    if (e.target.matches('textarea')) autoGrow(e.target);
    refreshLive();
  });
  window.addEventListener('resize', () => {
    document.querySelectorAll('.main textarea').forEach(autoGrow);
    refreshLive();
  });
  document.addEventListener('focusin', e => followFocus(e.target));
  document.getElementById('btn-live-open')?.addEventListener('click', previewReport);
  window.addEventListener('beforeunload', e => { if (tex.dirty) e.preventDefault(); });

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && !document.querySelector('.pv')) {
      e.preventDefault();
      saveReport();
    }
  });

  const params = new URLSearchParams(window.location.search);
  reportId = params.get('id') ? parseInt(params.get('id')) : null;

  if (reportId) {
    await loadReport(reportId);
  } else {
    // A new report starts from "Мої дані"
    const p = await loadProfile();
    const set = (id, value) => { const el = document.getElementById(id); if (el && value) el.value = value; };
    set('f-institution', p.institution); set('f-city', p.city); set('f-faculty', p.faculty);
    set('f-department', p.department); set('f-group', p.group); set('f-student', p.student_name);
    document.getElementById('f-ministry').value = p.ministry ?? DOC_TPL?.ministry_default ?? '';
    if (p.student_gender) setGender('student', p.student_gender);
    updateStudentSeg();
    setLevel(params.get('level') || p.level || 'university', { quiet: true });
    setKind(KIND_TEXT[params.get('kind')] ? params.get('kind') : 'lab');
    setMode('form');
    sections = [];
    renderSections();
  }
  // First time in the editor: offer the tour (it never starts by itself)
  setTimeout(offerTour, 1200);
}

function setLevel(level, { quiet = false } = {}) {
  reportLevel = level === 'school' ? 'school' : 'university';
  document.body.dataset.level = reportLevel;
  document.querySelectorAll('#level-seg [data-level]').forEach(b => {
    b.classList.toggle('on', b.dataset.level === reportLevel);
    b.setAttribute('aria-checked', b.dataset.level === reportLevel);
  });
  const school = reportLevel === 'school';
  // Same form, school words: Клас, Учень, Вчитель, Предмет
  document.querySelectorAll('[data-uni][data-school]').forEach(el => { if (!el.matches('button')) el.textContent = school ? el.dataset.school : el.dataset.uni; });
  document.querySelectorAll('[data-uni-ph]').forEach(el => { el.placeholder = school ? el.dataset.schoolPh : el.dataset.uniPh; });
  // there are no course works at school
  if (!quiet) { setKind(school && reportKind === 'course' ? 'essay' : reportKind); }
}

async function rememberProfile() {
  const v = id => document.getElementById(id)?.value.trim() ?? '';
  const btn = document.getElementById('btn-remember');
  setLoading(btn, true);
  try {
    await saveProfile({
      level: reportLevel, ministry: v('f-ministry'), institution: v('f-institution'), city: v('f-city'),
      faculty: v('f-faculty'), department: v('f-department'), group: v('f-group'),
      student_name: v('f-student'), student_gender: genders.student,
    });
    toast('Запам’ятали — нові звіти заповнюватимуться цими даними');
  } catch (ex) { toast(ex.message, 'err'); }
  finally { setLoading(btn, false); }
}

function setKind(kind) {
  reportKind = kind;
  document.body.dataset.kind = kind;
  const t = KIND_TEXT[kind];
  document.querySelectorAll('#kind-seg [data-kind]').forEach(b => {
    b.classList.toggle('on', b.dataset.kind === kind);
    b.setAttribute('aria-checked', b.dataset.kind === kind);
  });
  document.getElementById('editor-heading').textContent = reportId ? `${t.heading}: редагування` : `Новий ${t.heading.toLowerCase()}`;
  document.getElementById('lbl-title').textContent = t.title;
  document.getElementById('f-title').placeholder = t.titlePh;
  document.getElementById('kind-hint').textContent = t.hint;
  document.getElementById('refs-badge').textContent = kind === 'lab' ? 'необов’язково' : 'обов’язковий за методичкою';
  document.querySelectorAll('.seg[data-gender="teacher"] [data-g]').forEach(b => {
    b.textContent = reportLevel === 'school' ? b.dataset.school : b.dataset[kind === 'course' ? 'essay' : kind];
  });
  // Course work: several supervisors, each "посада Прізвище І. Б." on its own line
  const teacherLabel = document.querySelector('label[for="f-teacher"]');
  if (teacherLabel) teacherLabel.innerHTML = kind === 'course'
    ? 'Керівники <span class="text-muted">— кожен з нового рядка: посада і ПІБ</span>'
    : esc(reportLevel === 'school' ? teacherLabel.dataset.school : teacherLabel.dataset.uni);
  const teacher = document.getElementById('f-teacher');
  if (teacher) teacher.placeholder = kind === 'course' ? 'проф. Табакова І. С.' : 'Іваненко І. І.';
  const date = document.getElementById('f-date');
  if (kind !== 'lab' && reportLevel === 'university' && date && !date.value) date.value = new Date().toLocaleDateString('uk-UA');
  if (kind === 'course') fillCourseCard();
  if (editorMode === 'latex' && tex.source) parseTexSoon();
  renderSections();
  document.querySelectorAll('.main textarea').forEach(autoGrow);
}

function setMode(mode) {
  editorMode = mode;
  document.body.dataset.mode = mode;
  document.querySelectorAll('#mode-seg [data-mode]').forEach(b => {
    b.classList.toggle('on', b.dataset.mode === mode);
    b.setAttribute('aria-checked', b.dataset.mode === mode);
  });
}

function updateStudentSeg() {
  const many = (document.getElementById('f-student')?.value || '').split('\n').filter(l => l.trim()).length > 1;
  document.querySelector('.seg[data-gender="student"]')?.classList.toggle('hidden', many);
}

function autoGrow(el) {
  if (!el.offsetParent) return;           // hidden: nothing to measure
  el.style.height = 'auto';
  el.style.height = `${el.scrollHeight + 2}px`;
}

/* ── live preview (wide screens): the document as it will look, following the focused field ── */
let liveTimer = null, liveFocus = null;

const refsList = () => (document.getElementById('f-refs')?.value || '').split('\n').map(l => l.trim()).filter(Boolean);

function currentDoc() {
  const v = id => document.getElementById(id)?.value ?? '';
  return {
    kind: reportKind, level: reportLevel,
    ministry: v('f-ministry'), institution: v('f-institution'), city: v('f-city'),
    title: v('f-title'), discipline: v('f-discipline'), group: v('f-group'),
    faculty: v('f-faculty'), department: v('f-department'),
    teacher: v('f-teacher'), teacher_gender: genders.teacher, teacher_position: v('f-position'),
    student_name: v('f-student'), student_gender: genders.student, work_date: v('f-date'),
    goal: v('f-goal'), introduction: v('f-intro'), conclusion: v('ai-output'),
    bibliography: refsList(), sections, meta: courseMeta,
  };
}

function refreshLive() {
  clearTimeout(liveTimer);
  liveTimer = setTimeout(() => {
    const box = document.getElementById('live-pages');
    if (!box || !box.offsetParent) return;
    box.innerHTML = buildDocSheets(currentDoc(), reportImages);
    markEmptyFields(box);
    const stage = box.parentElement;
    box.style.zoom = Math.min(1, (stage.clientWidth - 24) / SHEET_PX);
    if (liveFocus) scrollLiveTo(liveFocus, false);
  }, 200);
}

const LIVE_TARGETS = {
  'f-title': '.dv-title', 'f-discipline': '.dv-title', 'f-group': '.dv-title', 'f-faculty': '.dv-title',
  'f-department': '.dv-title', 'f-student': '.dv-title', 'f-teacher': '.dv-title', 'f-position': '.dv-title',
  'f-date': '.dv-title', 'f-goal': '.dv-body', 'f-intro': '.dv-body',
  'f-institution': '.dv-title', 'f-city': '.dv-title', 'f-ministry': '.dv-title',
  'ai-output': '[data-bind="doc|conclusion"]', 'f-refs': '[data-bind="doc|bibliography"]',
};

function followFocus(el) {
  if (!el?.closest) return;
  const sec = el.closest('.section-item');
  const target = sec ? `#dv-${sec.id.replace(/^sec-/, '')}` : LIVE_TARGETS[el.id];
  if (!target) return;
  liveFocus = target;
  scrollLiveTo(target, true);
}

function scrollLiveTo(selector, smooth) {
  const box = document.getElementById('live-pages');
  if (!box?.offsetParent) return;
  box.querySelectorAll('.live-active').forEach(n => n.classList.remove('live-active'));
  const node = box.querySelector(selector);
  if (!node) return;
  if (selector.startsWith('#dv-') || selector.startsWith('[data-bind')) node.classList.add('live-active');
  const stage = box.parentElement;
  const zoom = Number(box.style.zoom) || 1;
  const top = (node.getBoundingClientRect().top - stage.getBoundingClientRect().top) + stage.scrollTop;
  stage.scrollTo({ top: Math.max(0, top - 40 * zoom), behavior: smooth ? 'smooth' : 'auto' });
}

function setGender(who, g) {
  genders[who] = g;
  refreshLive();
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
    const set = (elId, value) => { const el = document.getElementById(elId); if (el) el.value = value || ''; };
    set('f-title', r.title);           set('f-discipline', r.discipline);
    set('f-teacher', r.teacher);       set('f-student', r.student_name);
    set('f-group', r.group);           set('f-goal', r.goal);
    set('f-faculty', r.faculty);       set('f-department', r.department);
    set('f-position', r.teacher_position); set('f-date', r.work_date);
    set('f-intro', r.introduction);    set('f-refs', (r.bibliography || []).join('\n'));
    set('f-institution', r.institution); set('f-city', r.city); set('f-ministry', r.ministry);
    set('ai-output', r.conclusion);
    setGender('student', r.student_gender || 'm');
    setGender('teacher', r.teacher_gender || 'f');
    updateStudentSeg();

    sections = toEditableSections(r.sections);
    courseMeta = r.meta && typeof r.meta === 'object' ? { ...r.meta } : {};
    fillCourseCard();
    reportImages = imgs || [];
    setMode(r.editor_mode === 'latex' ? 'latex' : 'form');
    setLevel(r.level, { quiet: true });
    setKind(KIND_TEXT[r.kind] ? r.kind : 'lab');
    if (editorMode === 'latex') {
      tex.source = r.latex_source || '';
      renderTexPane();
    }
    updateReadiness();
    document.querySelectorAll('.main textarea').forEach(autoGrow);
    refreshLive();
  } catch (ex) { toast('Помилка завантаження: ' + ex.message, 'err'); }
}

/* ── image paths follow their sections when the structure changes ── */
// mapPath("1.0") → new path, or null when the image's section is gone
const pathMaps = {
  // the item at `path` is gone: its images go, later siblings move up by one
  removeItem: path => p => {
    if (p === 'u') return p;
    const t = path.split('.').map(Number), q = p.split('.').map(Number);
    const d = t.length;
    if (q.length < d || t.slice(0, d - 1).some((x, k) => q[k] !== x)) return p;
    if (q[d - 1] === t[d - 1]) return null;
    if (q[d - 1] > t[d - 1]) q[d - 1] -= 1;
    return q.join('.');
  },
  removeSection: i => p => {
    if (p === 'u') return p;
    const [a, b] = p.split('.').map(Number);
    if (a === i) return null;
    return a > i ? [a - 1, b].filter(x => x !== undefined).join('.') : p;
  },
  removeSubsection: (i, j) => p => {
    if (p === 'u') return p;
    const [a, b] = p.split('.').map(Number);
    if (a !== i || b === undefined) return p;
    if (b === j) return null;
    return b > j ? `${a}.${b - 1}` : p;
  },
  swapSections: (i, k) => p => {
    if (p === 'u') return p;
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

// Swaps a figure with its neighbour inside its section; positions are renumbered 0..n
async function moveImage(id, images, imgId, dir) {
  const img = images.find(i => i.id === imgId);
  if (!img) return images;
  const list = imagesIn(images, img.section_path);
  const k = list.findIndex(i => i.id === imgId);
  const to = k + dir;
  if (to < 0 || to >= list.length) return images;
  [list[k], list[to]] = [list[to], list[k]];
  const updates = list.map((im, pos) => ({ im, pos })).filter(({ im, pos }) => im.position !== pos);
  try {
    await Promise.all(updates.map(({ im, pos }) => req('PATCH', `/reports/${id}/images/${im.id}`, { position: pos })));
  } catch (ex) { toast('Не вдалося змінити порядок: ' + ex.message, 'err'); return images; }
  const pos = new Map(list.map((im, p) => [im.id, p]));
  return images.map(im => pos.has(im.id) ? { ...im, position: pos.get(im.id) } : im);
}

/* full-screen image viewer: ←/→ between images, Esc to close */
function openLightbox(list, startId) {
  list = list.filter(i => i.available !== false);
  let k = Math.max(0, list.findIndex(i => i.id === startId));
  if (!list.length) return;
  const box = document.createElement('div');
  box.className = 'lb';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.innerHTML = `
    <button class="lb-btn lb-close" title="Закрити (Esc)">${ICONS.x}</button>
    <button class="lb-btn lb-prev" title="Попереднє (←)">${ICONS.left}</button>
    <figure class="lb-fig"><img alt=""><figcaption></figcaption></figure>
    <button class="lb-btn lb-next" title="Наступне (→)">${ICONS.right}</button>`;
  const show = () => {
    const img = list[k];
    box.querySelector('img').src = `${API_URL}${img.url}`;
    box.querySelector('figcaption').textContent = `${k + 1} / ${list.length} · ${img.caption || ''}`;
    box.querySelector('.lb-prev').disabled = k === 0;
    box.querySelector('.lb-next').disabled = k === list.length - 1;
  };
  const close = () => { document.removeEventListener('keydown', onKey, true); box.remove(); };
  const go = d => { k = Math.min(list.length - 1, Math.max(0, k + d)); show(); };
  const onKey = e => {
    if (e.key === 'Escape') { e.stopPropagation(); close(); }
    if (e.key === 'ArrowLeft') go(-1);
    if (e.key === 'ArrowRight') go(1);
  };
  box.onclick = e => {
    if (e.target.closest('.lb-prev')) go(-1);
    else if (e.target.closest('.lb-next')) go(1);
    else if (e.target.closest('.lb-close') || e.target === box) close();
  };
  document.addEventListener('keydown', onKey, true);
  document.body.appendChild(box);
  show();
}

/* ── sections ── */
// path: "0" — section, "0.1" — its subsection, "0.1.2" — a point (1.2.3); the same format
// the backend stores for images. Sections with appendix: true are ДОДАТОК А, Б, ...
function blockAt(path) {
  const idx = String(path).split('.').map(Number);
  let item = sections[idx[0]];
  for (const k of idx.slice(1)) item = item?.subsections?.[k];
  return item;
}

function parentList(path) {
  const idx = String(path).split('.').map(Number);
  const list = idx.length === 1 ? sections : blockAt(idx.slice(0, -1).join('.')).subsections;
  return { list, index: idx[idx.length - 1] };
}

// "1", "2" for sections, "А", "Б" for appendices — by position in the array
function sectionLabels(list = sections) {
  const labels = {};
  let n = 0, a = 0;
  list.forEach((s, i) => { labels[i] = s.appendix ? APPENDIX_LETTERS[a++ % APPENDIX_LETTERS.length] : String(++n); });
  return labels;
}

function labelOf(path) {
  const idx = String(path).split('.').map(Number);
  return [sectionLabels()[idx[0]], ...idx.slice(1).map(k => k + 1)].join('.');
}

function addSection() {
  sections.push(newItem(true));
  renderSections();
  focusItem(String(sections.length - 1));
}

function addAppendix() {
  sections.push({ ...newItem(true), appendix: true });
  renderSections();
  focusItem(String(sections.length - 1));
}

function focusItem(path) {
  const el = document.getElementById(`sec-${path.replaceAll('.', '-')}`);
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el?.querySelector('.sec-name')?.focus({ preventScroll: true });
}

async function structureChanged(mapPath) {
  renderSections();
  if (!reportId) return;
  reportImages = await remapImages(reportId, reportImages, mapPath);
  renderSections();
  await saveReport({ quiet: true });   // images are already moved on the server — keep sections in step
}

async function removeItem(path) {
  const item = blockAt(path);
  const what = String(path).includes('.') ? (String(path).split('.').length === 2 ? 'підрозділ' : 'пункт')
    : item.appendix ? 'додаток' : 'розділ';
  if (hasContent(item) && !confirm(`Видалити ${what} ${labelOf(path)} разом із вмістом і скріншотами?`)) return;
  const { list, index } = parentList(path);
  list.splice(index, 1);
  await structureChanged(pathMaps.removeItem(String(path)));
}
const removeSection = idx => removeItem(String(idx));
const removeSubsection = (i, j) => removeItem(`${i}.${j}`);

// Up / down among sections of the same kind (sections with sections, appendices with appendices)
async function moveSection(idx, dir) {
  const app = Boolean(sections[idx].appendix);
  let k = idx + dir;
  while (k >= 0 && k < sections.length && Boolean(sections[k].appendix) !== app) k += dir;
  if (k < 0 || k >= sections.length) return;
  [sections[idx], sections[k]] = [sections[k], sections[idx]];
  await structureChanged(pathMaps.swapSections(idx, k));
}

function addChild(path) {
  const item = blockAt(path);
  const depth = String(path).split('.').length;
  item.subsections = item.subsections || [];
  item.subsections.push(newItem(depth < 2));
  renderSections();
  focusItem(`${path}.${item.subsections.length - 1}`);
}
const addSubsection = i => addChild(String(i));

function setBlockTitle(path, value) {
  blockAt(path).title = value;
  renderOutline();
  updateReadiness();
}

const LANGS = ['python','javascript','typescript','java','cpp','c','sql','bash','html','css'];
const BLOCK_LABEL = { text: 'Текст', code: 'Код', formula: 'Формула', table: 'Таблиця' };

function tableEditorHtml(b, no) {
  const rows = b.rows?.length ? b.rows : [['', '']];
  const header = b.header ?? 1;
  return `
      <div class="tbl-box">
        <div class="tbl-cap-row"><span class="tbl-no">Таблиця ${no} –</span>
          <input class="tbl-cap" data-f="caption" value="${esc(b.caption || '')}" placeholder="Назва таблиці"></div>
        <div class="tbl-scroll"><table class="tbl-edit">
          ${rows.map((row, r) => `<tr class="${r < header ? 'is-head' : ''}">${row.map((c, ci) => `
            <td><textarea rows="1" data-cell="${r},${ci}" placeholder="${r < header ? 'Заголовок' : ''}">${esc(c)}</textarea></td>`).join('')}
            <td class="tbl-x"><button type="button" data-tact="delrow" data-r="${r}" title="Видалити рядок" ${rows.length < 2 ? 'disabled' : ''}>${ICONS.x}</button></td></tr>`).join('')}
          <tr class="tbl-coltools">${rows[0].map((_, ci) => `<td><button type="button" data-tact="delcol" data-c="${ci}" title="Видалити стовпець" ${rows[0].length < 2 ? 'disabled' : ''}>${ICONS.x}</button></td>`).join('')}<td></td></tr>
        </table></div>
        <div class="tbl-actions">
          <button type="button" class="btn btn-ghost btn-sm" data-tact="addrow">${ICONS.plus} Рядок</button>
          <button type="button" class="btn btn-ghost btn-sm" data-tact="addcol">${ICONS.plus} Стовпець</button>
          <label class="check"><input type="checkbox" data-tact="header" ${header ? 'checked' : ''}> Перший рядок — заголовок</label>
          <span class="text-sm text-muted">Можна вставити таблицю з Excel чи Google Sheets — просто Ctrl+V у клітинку</span>
        </div>
      </div>`;
}

/* One content block of a section: text / code / formula / table */
function blockCardHtml(path, k, b, total, no) {
  const key = `${path}|${k}`;
  const tools = `
    <span class="blk-tools">
      <button class="pv-icon-btn" data-bact="up" title="Вище" ${k === 0 ? 'disabled' : ''}>${ICONS.up}</button>
      <button class="pv-icon-btn" data-bact="down" title="Нижче" ${k === total - 1 ? 'disabled' : ''}>${ICONS.down}</button>
      <button class="pv-icon-btn danger" data-bact="del" title="Видалити блок">${ICONS.trash}</button>
    </span>`;
  let body = '';
  if (b.type === 'text') {
    body = `
      <textarea rows="3" data-f="text" placeholder="Текст. Формула всередині рядка — у доларах: $E = mc^2$">${esc(b.text)}</textarea>
      <div class="inline-preview ${hasInlineMath(b.text) ? '' : 'hidden'}">${(b.text || '').split('\n').filter(l => l.trim()).map(inlineHtml).join('<br>')}</div>`;
  } else if (b.type === 'code') {
    body = `
      <div class="code-wrap">
        <div class="code-head">
          <select class="lang-select" data-f="language">
            ${LANGS.map(l => `<option value="${l}" ${b.language === l ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
          <span class="text-sm text-muted">лістинг з підписом</span>
        </div>
        <textarea spellcheck="false" data-f="code" placeholder="Вставте код">${esc(b.code)}</textarea>
      </div>`;
  } else if (b.type === 'table') {
    body = tableEditorHtml(b, no);
  } else {
    body = `
      <div class="formula-box">
        <div class="formula-view">${mathHtml(b.latex, true) || '<span class="text-muted text-sm">Попередній вигляд формули</span>'}</div>
        <div class="formula-row">
          <textarea class="formula-src" rows="1" spellcheck="false" data-f="latex"
                    placeholder="\\frac{1}{n}\\sum_{i=1}^{n} x_i">${esc(b.latex)}</textarea>
          <span class="formula-no">(${no})</span>
        </div>
        <div class="snippets">
          ${MATH_SNIPPETS.map(([label], n) => `<button type="button" class="snip" data-snip="${n}" title="${esc(MATH_SNIPPETS[n][1])}">${esc(label)}</button>`).join('')}
          <button type="button" class="snip snip-py" data-bact="py" title="Формула з Python-функції (latexify)">${ICONS.python} З Python</button>
        </div>
        <p class="formula-err warn-text text-sm hidden"></p>
      </div>`;
  }
  return `
    <div class="blk blk-${b.type}" data-blk="${key}">
      <div class="blk-head"><span class="blk-type">${BLOCK_LABEL[b.type]}</span>${tools}</div>
      ${body}
    </div>`;
}

// ctx: {label: section label "1" / "А", local: number tables within the section, f: formula n, t: {n} tables}
function itemBodyHtml(path, item, ctx) {
  const id = String(path).replaceAll('.', '-');
  const blocks = item.blocks.map((b, k) => {
    let no = '';
    if (b.type === 'formula') no = `${ctx.label}.${++ctx.f}`;
    if (b.type === 'table') no = ctx.local ? `${ctx.label}.${++ctx.t.n}` : String(++ctx.t.n);
    return blockCardHtml(path, k, b, item.blocks.length, no);
  }).join('');
  return `
        <div class="blk-list">${blocks}</div>
        <div class="add-bar">
          <span class="text-sm text-muted">Додати:</span>
          <button type="button" class="btn btn-ghost btn-sm" data-add="text" data-path="${path}">${ICONS.text} Текст</button>
          <button type="button" class="btn btn-ghost btn-sm" data-add="code" data-path="${path}">${ICONS.code} Код</button>
          <button type="button" class="btn btn-ghost btn-sm" data-add="formula" data-path="${path}">${ICONS.sigma} Формула</button>
          <button type="button" class="btn btn-ghost btn-sm" data-add="table" data-path="${path}">${ICONS.table} Таблиця</button>
        </div>
        <div class="form-group">
          <label>Рисунки <span class="text-muted">— ідуть після тексту, у цьому порядку; клік — перегляд</span></label>
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

const CHILD_NAME = { 1: 'Підрозділ', 2: 'Пункт' };

function itemHtml(path, item, depth, label, ctx) {
  const id = path.replaceAll('.', '-');
  const ph = depth === 1 ? (item.appendix ? 'Назва додатка...' : 'Назва розділу...')
    : depth === 2 ? 'Назва підрозділу...' : 'Назва пункту...';
  const kids = depth < 3
    ? (item.subsections || []).map((sub, k) => itemHtml(`${path}.${k}`, sub, depth + 1, `${label}.${k + 1}`, ctx)).join('')
    : '';
  const addKid = depth < 3
    ? `<div><button class="btn btn-ghost btn-sm" onclick="addChild('${path}')">${ICONS.plus} ${CHILD_NAME[depth]} ${label}.${(item.subsections || []).length + 1}</button></div>`
    : '';
  return `
    <div class="section-item ${depth > 1 ? 'subsection-item' : ''} depth-${depth}" id="sec-${id}">
      <div class="section-head">
        <span class="sec-num">${depth === 1 && item.appendix ? `Додаток ${label}` : label}</span>
        <input class="sec-name" placeholder="${ph}" value="${esc(item.title)}" oninput="setBlockTitle('${path}', this.value)">
        <button class="btn btn-ghost btn-sm" onclick="removeItem('${path}')" title="Видалити">${ICONS.trash}</button>
      </div>
      <div class="section-body">
        ${itemBodyHtml(path, item, ctx)}
        ${kids}
        ${addKid}
      </div>
    </div>`;
}

function renderSections() {
  const container = document.getElementById('sections-container');
  const appBox = document.getElementById('appendix-container');
  if (!container) return;
  const labels = sectionLabels();
  const local = reportKind !== 'lab';
  const shared = { n: 0 };       // lab report: tables numbered through the document
  const html = { main: [], app: [] };
  sections.forEach((s, i) => {
    const ctx = { label: labels[i], f: 0, local: local || s.appendix, t: (local || s.appendix) ? { n: 0 } : shared };
    html[s.appendix ? 'app' : 'main'].push(itemHtml(String(i), s, 1, labels[i], ctx));
  });
  container.innerHTML = html.main.length ? html.main.join('')
    : `<p class="text-sm text-muted" style="text-align:center;padding:14px 0">Розділів ще немає. Додайте перший — наприклад, «${reportKind === 'lab' ? 'Хід роботи' : 'Аналіз предметної області'}».</p>`;
  if (appBox) appBox.innerHTML = html.app.length ? html.app.join('')
    : '<p class="text-sm text-muted">Додатків немає. Сюди виносять код програми, великі таблиці, креслення — кожен додаток почнеться з нової сторінки.</p>';
  new Set(reportImages.map(i => i.section_path)).forEach(renderImageGrid);
  document.querySelectorAll('#sections-container textarea, #appendix-container textarea').forEach(autoGrow);
  renderUnplaced();
  renderOutline();
  updateReadiness();
  refreshLive();
}

/* ── block events (delegated from the sections and appendix containers) ── */
const blockFromEl = el => {
  const card = el.closest('[data-blk]');
  if (!card) return {};
  const [path, k] = card.dataset.blk.split('|');
  return { card, path, k: Number(k), item: blockAt(path), block: blockAt(path).blocks[Number(k)] };
};

const checkTimers = new WeakMap();
function onBlocksInput(e) {
  const cell = e.target.dataset?.cell;
  if (cell !== undefined) {
    const { block } = blockFromEl(e.target);
    const [r, c] = cell.split(',').map(Number);
    if (block?.rows?.[r]) block.rows[r][c] = e.target.value;
    return;
  }
  if (e.target.dataset?.tact === 'header') {
    const { block } = blockFromEl(e.target);
    block.header = e.target.checked ? 1 : 0;
    renderSections();
    return;
  }
  const field = e.target.dataset?.f;
  if (!field) return;
  const { card, block } = blockFromEl(e.target);
  if (!block) return;
  block[field] = e.target.value;
  if (field === 'text') {
    const prev = card.querySelector('.inline-preview');
    const show = hasInlineMath(block.text);
    prev.classList.toggle('hidden', !show);
    if (show) prev.innerHTML = block.text.split('\n').filter(l => l.trim()).map(inlineHtml).join('<br>');
    updateReadiness();
  }
  if (field === 'latex') {
    card.querySelector('.formula-view').innerHTML = mathHtml(block.latex, true) || '<span class="text-muted text-sm">Попередній вигляд формули</span>';
    // KaTeX is forgiving; check what the Word / PDF converter will make of it
    clearTimeout(checkTimers.get(card));
    checkTimers.set(card, setTimeout(async () => {
      const err = card.querySelector('.formula-err');
      if (!block.latex.trim()) { err.classList.add('hidden'); return; }
      try {
        const r = await req('POST', '/latex/check', { latex: block.latex });
        err.textContent = r.error ? `У Word / PDF ця формула може не відобразитись: ${r.error}` : '';
        err.classList.toggle('hidden', !r.error);
      } catch { /* the preview still works */ }
    }, 700));
  }
}

// Ctrl+V of several cells from Excel / Google Sheets fills the table from that cell on
function onTablePaste(e) {
  const cell = e.target.dataset?.cell;
  if (cell === undefined) return;
  const text = e.clipboardData.getData('text/plain').replace(/\r/g, '').replace(/\n$/, '');
  if (!/[\t\n]/.test(text)) return;
  e.preventDefault();
  const { block, path, k } = blockFromEl(e.target);
  const [r0, c0] = cell.split(',').map(Number);
  const grid = text.split('\n').map(line => line.split('\t'));
  const width = Math.max(block.rows[0].length, c0 + Math.max(...grid.map(g => g.length)));
  while (block.rows.length < r0 + grid.length) block.rows.push([]);
  block.rows = block.rows.map(row => [...row, ...Array(Math.max(0, width - row.length)).fill('')]);
  grid.forEach((line, dr) => line.forEach((v, dc) => { block.rows[r0 + dr][c0 + dc] = v.trim(); }));
  renderSections();
  document.querySelector(`[data-blk="${path}|${k}"] [data-cell="${r0},${c0}"]`)?.focus();
  toast(`Вставлено ${grid.length} × ${Math.max(...grid.map(g => g.length))}`);
}

function onBlocksClick(e) {
  const add = e.target.closest('[data-add]');
  if (add) {
    const item = blockAt(add.dataset.path);
    const make = { text: newTextBlock, code: newCodeBlock, formula: newFormulaBlock, table: newTableBlock }[add.dataset.add];
    item.blocks.push(make());
    renderSections();
    const last = document.querySelector(`[data-blk="${add.dataset.path}|${item.blocks.length - 1}"]`);
    last?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    last?.querySelector('textarea, input')?.focus({ preventScroll: true });
    return;
  }
  const tact = e.target.closest('button[data-tact]');
  if (tact) {
    const { block } = blockFromEl(tact);
    const width = block.rows[0]?.length || 1;
    if (tact.dataset.tact === 'addrow') block.rows.push(Array(width).fill(''));
    if (tact.dataset.tact === 'addcol') block.rows.forEach(row => row.push(''));
    if (tact.dataset.tact === 'delrow' && block.rows.length > 1) block.rows.splice(Number(tact.dataset.r), 1);
    if (tact.dataset.tact === 'delcol' && width > 1) block.rows.forEach(row => row.splice(Number(tact.dataset.c), 1));
    renderSections();
    return;
  }
  const snip = e.target.closest('[data-snip]');
  if (snip) {
    const [, latex, back] = MATH_SNIPPETS[Number(snip.dataset.snip)];
    insertAtCursor(snip.closest('.formula-box').querySelector('.formula-src'), latex, back);
    return;
  }
  const btn = e.target.closest('[data-bact]');
  if (!btn) return;
  const { card, item, k, block } = blockFromEl(btn);
  if (!block) return;
  const act = btn.dataset.bact;
  if (act === 'py') {
    openPyDialog(latex => {
      const src = card.querySelector('.formula-src');
      src.value = latex;
      src.dispatchEvent(new Event('input', { bubbles: true }));
      autoGrow(src);
    });
    return;
  }
  if (act === 'del') {
    if (blockFilled(block) && !confirm(`Видалити блок «${BLOCK_LABEL[block.type]}»?`)) return;
    item.blocks.splice(k, 1);
  } else {
    const to = k + (act === 'up' ? -1 : 1);
    if (to < 0 || to >= item.blocks.length) return;
    [item.blocks[k], item.blocks[to]] = [item.blocks[to], item.blocks[k]];
  }
  renderSections();
}

/* ── right panel: outline + readiness ── */
function renderOutline() {
  const nav = document.getElementById('outline');
  if (!nav) return;
  if (!sections.length) {
    nav.innerHTML = `<p class="outline-empty">${editorMode === 'latex' ? 'Розділи з\'являться тут, щойно ви напишете \\section{…}.' : 'Тут з\'явиться зміст звіту. Розділи можна додавати звідси, не прокручуючи сторінку.'}</p>`;
    return;
  }
  const latex = editorMode === 'latex';
  const labels = sectionLabels();
  const row = (s, i) => {
    const same = sections.map((x, k) => [x, k]).filter(([x]) => Boolean(x.appendix) === Boolean(s.appendix)).map(([, k]) => k);
    const first = same[0] === i, last = same[same.length - 1] === i;
    return `
    <div class="ol-item">
      <a href="#sec-${i}" class="ol-link" data-target="sec-${i}" data-sec="${i}">
        <span class="ol-num">${labels[i]}</span>
        <span class="ol-title ${s.title.trim() ? '' : 'untitled'}">${esc(s.title.trim() || 'Без назви')}</span>
      </a>
      ${latex ? '' : `<span class="ol-actions">
        <button class="pv-icon-btn" title="Вище" ${first ? 'disabled' : ''} onclick="moveSection(${i},-1)">${ICONS.up}</button>
        <button class="pv-icon-btn" title="Нижче" ${last ? 'disabled' : ''} onclick="moveSection(${i},1)">${ICONS.down}</button>
        <button class="pv-icon-btn" title="Додати підрозділ" onclick="addSubsection(${i})">${ICONS.plus}</button>
      </span>`}
    </div>
    ${(s.subsections || []).map((sub, j) => `
    <a href="#sec-${i}-${j}" class="ol-link ol-sub" data-target="sec-${i}-${j}" data-sec="${i}" data-sub="${j}">
      <span class="ol-num">${labels[i]}.${j + 1}</span>
      <span class="ol-title ${sub.title.trim() ? '' : 'untitled'}">${esc(sub.title.trim() || 'Без назви')}</span>
    </a>`).join('')}`;
  };
  const main = sections.map((s, i) => s.appendix ? '' : row(s, i)).join('');
  const apps = sections.map((s, i) => s.appendix ? row(s, i) : '').join('');
  nav.innerHTML = main + (apps ? `<p class="ol-group">Додатки</p>${apps}` : '');

  nav.querySelectorAll('.ol-link').forEach(a => a.onclick = e => {
    e.preventDefault();
    if (editorMode === 'latex') { jumpToTexHeading(Number(a.dataset.sec), a.dataset.sub === undefined ? null : Number(a.dataset.sub)); return; }
    const el = document.getElementById(a.dataset.target);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el?.querySelector('.sec-name')?.focus({ preventScroll: true });
  });
}

// every section / subsection / point, in document order
function allItems(list = sections, depth = 1) {
  return list.flatMap(s => [s, ...(depth < 3 ? allItems(s.subsections || [], depth + 1) : [])]);
}

function updateReadiness() {
  const val = id => document.getElementById(id)?.value.trim();
  const essayLike = reportKind !== 'lab';
  const course = reportKind === 'course';
  const school = reportLevel === 'school';
  const texTarget = id => editorMode === 'latex' ? 'tex-src' : id;
  const meta = courseMeta;
  const checks = [
    ['Навчальний заклад', () => val('f-institution'), 'f-institution'],
    [essayLike ? 'Тема' : 'Назва роботи', () => val('f-title'), 'f-title'],
    [school ? 'Предмет' : 'Дисципліна', () => val('f-discipline'), 'f-discipline'],
    [school ? 'Клас' : 'Група', () => val('f-group'), 'f-group'],
    [school ? 'Учень' : 'Студент', () => val('f-student'), 'f-student'],
    [school ? 'Вчитель' : course ? 'Керівник' : 'Викладач', () => val('f-teacher'), 'f-teacher'],
    ...(essayLike ? [
      ...(school ? [] : [['Факультет і кафедра', () => val('f-faculty') && val('f-department'), 'f-faculty']]),
      ['Вступ', () => val('f-intro'), texTarget('f-intro')],
    ] : [['Мета', () => val('f-goal'), texTarget('f-goal')]]),
    ...(course && meta.task_sheet ? [
      ['Завдання: спеціальність, курс, семестр', () => meta.specialty && meta.year_of_study && meta.semester, 'm-specialty'],
      ['Завдання: терміни', () => meta.deadline && meta.issue_date, 'm-deadline'],
      ['Календарний план', () => (meta.calendar || []).some(r => (r.stage || '').trim()), 'calendar-box'],
    ] : []),
    ['Хоча б один розділ з текстом', () => allItems(sections.filter(s => !s.appendix)).some(itemText), texTarget('btn-add-sec')],
    ['Назви всіх розділів', () => sections.length && allItems().every(s => s.title.trim()), texTarget('sections-container')],
    ['Висновки',      () => val('ai-output'),    'ai-output'],
    ...(essayLike ? [['Перелік посилань', () => refsList().length, texTarget('f-refs')]] : []),
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

/* ═════════ course work: task sheet and calendar plan (report.meta) ═════════ */
let courseMeta = {};
const COURSE_FIELDS = ['doc_code', 'specialty', 'year_of_study', 'semester', 'student_full_dative',
                       'deadline', 'issue_date', 'input_data', 'contents', 'graphics', 'abbreviations'];
const DEFAULT_CALENDAR = [
  'Отримання завдання, вибір і узгодження теми', 'Аналіз предметної області та джерел',
  'Основна частина: розробка, розрахунки, дослідження', 'Оформлення пояснювальної записки', 'Захист на комісії',
].map(stage => ({ stage, deadline: '', note: '', sub: false }));

function fillCourseCard() {
  COURSE_FIELDS.forEach(k => {
    const el = document.getElementById(`m-${k}`);
    if (el) { el.value = courseMeta[k] || ''; autoGrow(el); }
  });
  const task = document.getElementById('m-task_sheet');
  if (task) task.checked = Boolean(courseMeta.task_sheet);
  document.getElementById('task-fields')?.classList.toggle('hidden', !courseMeta.task_sheet);
  document.querySelectorAll('#course-type-seg [data-ct]').forEach(b =>
    b.classList.toggle('on', b.dataset.ct === (courseMeta.course_type || 'project')));
  renderCalendar();
}

function renderCalendar() {
  const box = document.getElementById('calendar-box');
  if (!box) return;
  const rows = courseMeta.calendar || [];
  let n = 0;
  box.innerHTML = rows.length ? `
    <div class="cal-head"><span>№</span><span>Етап</span><span>Строк</span><span>Примітка</span><span></span></div>
    ${rows.map((r, i) => `
    <div class="cal-row ${r.sub ? 'sub' : ''}" data-cal="${i}">
      <span class="cal-no">${r.sub ? '' : ++n}</span>
      <input data-calf="stage" value="${esc(r.stage || '')}" placeholder="${r.sub ? 'Підетап' : 'Назва етапу'}">
      <input data-calf="deadline" value="${esc(r.deadline || '')}" placeholder="09.10.2025">
      <input data-calf="note" value="${esc(r.note || '')}" placeholder="Виконано">
      <span class="cal-tools">
        <button type="button" class="pv-icon-btn" data-calact="sub" title="${r.sub ? 'Зробити етапом' : 'Зробити підетапом (а, б, в)'}">${r.sub ? ICONS.left : ICONS.right}</button>
        <button type="button" class="pv-icon-btn" data-calact="up" title="Вище" ${i === 0 ? 'disabled' : ''}>${ICONS.up}</button>
        <button type="button" class="pv-icon-btn danger" data-calact="del" title="Видалити">${ICONS.trash}</button>
      </span>
    </div>`).join('')}` : '<p class="text-sm text-muted">Етапів ще немає.</p>';
}

function bindCourseCard() {
  const card = document.getElementById('course-card');
  if (!card) return;
  card.addEventListener('input', e => {
    const key = e.target.id?.startsWith('m-') ? e.target.id.slice(2) : null;
    if (key && COURSE_FIELDS.includes(key)) { courseMeta[key] = e.target.value; updateReadiness(); refreshLive(); return; }
    const row = e.target.closest('[data-cal]');
    if (row && e.target.dataset.calf) {
      courseMeta.calendar[Number(row.dataset.cal)][e.target.dataset.calf] = e.target.value;
      updateReadiness();
      refreshLive();
    }
  });
  card.addEventListener('change', e => {
    if (e.target.id === 'm-task_sheet') {
      courseMeta.task_sheet = e.target.checked;
      if (courseMeta.task_sheet && !(courseMeta.calendar || []).length) courseMeta.calendar = DEFAULT_CALENDAR.map(r => ({ ...r }));
      fillCourseCard();
      updateReadiness();
      refreshLive();
    }
  });
  card.addEventListener('click', e => {
    const ct = e.target.closest('[data-ct]')?.dataset.ct;
    if (ct) { courseMeta.course_type = ct; fillCourseCard(); refreshLive(); return; }
    const add = e.target.closest('[data-caladd]')?.dataset.caladd;
    if (add) {
      courseMeta.calendar = courseMeta.calendar || [];
      if (add === 'defaults') {
        if (courseMeta.calendar.some(r => r.stage) && !confirm('Замінити поточний план типовими етапами?')) return;
        courseMeta.calendar = DEFAULT_CALENDAR.map(r => ({ ...r }));
      } else {
        courseMeta.calendar.push({ stage: '', deadline: '', note: '', sub: add === 'sub' });
      }
      renderCalendar();
      document.querySelector(`#calendar-box [data-cal="${courseMeta.calendar.length - 1}"] input`)?.focus();
      refreshLive();
      return;
    }
    const act = e.target.closest('[data-calact]');
    if (!act) return;
    const i = Number(act.closest('[data-cal]').dataset.cal);
    const rows = courseMeta.calendar;
    if (act.dataset.calact === 'del') rows.splice(i, 1);
    if (act.dataset.calact === 'up' && i > 0) [rows[i - 1], rows[i]] = [rows[i], rows[i - 1]];
    if (act.dataset.calact === 'sub') rows[i].sub = !rows[i].sub;
    renderCalendar();
    refreshLive();
  });
}

/* ── file upload ── */
function triggerUpload(path) { document.getElementById(`fu-${String(path).replaceAll('.', '-')}`)?.click(); }

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
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Upload failed');
      created.push({ available: true, ...(await res.json()) });
    } catch (ex) { toast(`${file.name}: ${ex.message}`, 'err'); }
  }
  return created;
}

async function uploadFiles(files, sectionPath) {
  if (!reportId) { toast('Спершу збережіть звіт — тоді можна додавати скріншоти', 'err'); return; }
  const zone = document.querySelector(`#imgs-${String(sectionPath).replaceAll('.', '-')}`)?.previousElementSibling?.previousElementSibling;
  zone?.classList.add('busy');
  const created = await uploadImages(reportId, files, sectionPath);
  zone?.classList.remove('busy');
  reportImages.push(...created);
  renderImageGrid(String(sectionPath));
  if (created.length) refreshLive();
}

// Figures of one section as cards: preview, caption, order, delete
function renderImageGrid(path) {
  const grid = document.getElementById(`imgs-${String(path).replaceAll('.', '-')}`);
  if (!grid) return;
  const list = imagesIn(reportImages, path);
  grid.innerHTML = list.map((img, k) => `
    <div class="img-card ${img.available === false ? 'lost' : ''}" data-img-id="${img.id}">
      ${img.available === false
        ? `<div class="img-lost">Файл втрачено на сервері.<br>Видаліть і завантажте ще раз.</div>`
        : `<button class="img-view" data-imgact="view" title="Переглянути"><img src="${API_URL}${img.url}" alt="" loading="lazy"><span class="img-zoom">${ICONS.expand}</span></button>`}
      <div class="img-meta">
        <span class="img-order">${k + 1}</span>
        <input class="img-cap" value="${esc(img.caption)}" placeholder="Підпис рисунка" data-imgact="caption">
      </div>
      <div class="img-tools">
        <button class="pv-icon-btn" data-imgact="left" title="Раніше" ${k === 0 ? 'disabled' : ''}>${ICONS.left}</button>
        <button class="pv-icon-btn" data-imgact="right" title="Пізніше" ${k === list.length - 1 ? 'disabled' : ''}>${ICONS.right}</button>
        <span class="img-tools-gap"></span>
        <button class="pv-icon-btn danger" data-imgact="delete" title="Видалити">${ICONS.trash}</button>
      </div>
    </div>`).join('');
}

// Images uploaded in LaTeX mode but not referenced in the source: offer to put them in a section
function renderUnplaced() {
  const box = document.getElementById('unplaced');
  if (!box) return;
  const list = reportImages.filter(i => i.section_path === 'u');
  box.classList.toggle('hidden', !list.length || editorMode === 'latex');
  if (!list.length) { box.innerHTML = ''; return; }
  const options = sections.flatMap((s, i) => [
    `<option value="${i}">${i + 1} ${esc(s.title || 'Без назви')}</option>`,
    ...s.subsections.map((b, j) => `<option value="${i}.${j}">${i + 1}.${j + 1} ${esc(b.title || 'Без назви')}</option>`),
  ]).join('');
  box.innerHTML = `
    <p class="text-sm"><b>Не вставлені рисунки</b> <span class="text-muted">— їх немає в документі, поки не оберете розділ</span></p>
    <div class="unplaced-list">${list.map(img => `
      <div class="unplaced-item" data-img-id="${img.id}">
        <img src="${API_URL}${img.url}" alt="">
        <select data-place="${img.id}"><option value="">У розділ…</option>${options}</select>
      </div>`).join('')}</div>`;
}

async function placeImage(e) {
  const sel = e.target.closest('[data-place]');
  if (!sel || !sel.value) return;
  const imgId = Number(sel.dataset.place);
  const position = imagesIn(reportImages, sel.value).length;
  try {
    await req('PATCH', `/reports/${reportId}/images/${imgId}`, { section_path: sel.value, position });
    reportImages = reportImages.map(i => i.id === imgId ? { ...i, section_path: sel.value, position } : i);
    renderSections();
  } catch (ex) { toast(ex.message, 'err'); }
}

const captionTimers = {};
function onImageCardEvent(e) {
  const el = e.target.closest('[data-imgact]');
  const card = e.target.closest('.img-card');
  if (!el || !card) return;
  const imgId = Number(card.dataset.imgId);
  const img = reportImages.find(i => i.id === imgId);
  const act = el.dataset.imgact;
  if (e.type === 'input' && act === 'caption') {
    img.caption = el.value;
    clearTimeout(captionTimers[imgId]);
    captionTimers[imgId] = setTimeout(() =>
      req('PATCH', `/reports/${reportId}/images/${imgId}`, { caption: img.caption })
        .catch(ex => toast('Підпис не збережено: ' + ex.message, 'err')), 700);
    refreshLive();
    return;
  }
  if (e.type !== 'click') return;
  if (act === 'view') openLightbox(docOrder(reportImages), imgId);
  if (act === 'left' || act === 'right') {
    moveImage(reportId, reportImages, imgId, act === 'left' ? -1 : 1).then(list => {
      reportImages = list;
      renderImageGrid(img.section_path);
      refreshLive();
    });
  }
  if (act === 'delete') {
    if (!confirm('Видалити це зображення зі звіту?')) return;
    req('DELETE', `/reports/${reportId}/images/${imgId}`).then(() => {
      reportImages = reportImages.filter(i => i.id !== imgId);
      renderImageGrid(img.section_path);
      refreshLive();
    }).catch(ex => toast('Не вдалося видалити: ' + ex.message, 'err'));
  }
}

/* ═════════ LaTeX mode ═════════ */
async function switchMode(mode) {
  if (mode === 'latex') {
    if (!(await saveReport({ quiet: true }))) return;
    try {
      const r = await req('GET', `/reports/${reportId}/latex`);
      tex.source = r.source;
      setMode('latex');
      renderTexPane();
      await saveTex();
      toast('Режим LaTeX: увесь вміст звіту тепер у коді');
    } catch (ex) { toast(ex.message, 'err'); }
    return;
  }
  if (!confirm('Повернутись до форми? Звіт залишиться, але те, що форма не підтримує (\\textbf, таблиці тощо), буде спрощено до тексту.')) return;
  if (!(await saveTex())) return;
  try {
    await req('PATCH', `/reports/${reportId}`, { editor_mode: 'form' });
    tex.source = '';
    tex.dirty = false;
    setMode('form');
    await loadReport(reportId);
  } catch (ex) { toast(ex.message, 'err'); }
}

function renderTexPane() {
  const pane = document.getElementById('latex-pane');
  if (!pane) return;
  const tools = [
    ['sec', 'Розділ', '\\section{Назва розділу}\n\n'],
    ['sub', 'Підрозділ', '\\subsection{Назва підрозділу}\n\n'],
    ['eq', 'Формула', '\\begin{equation}\n  \n\\end{equation}\n', 15],
    ['inl', '$ в тексті', '$$', 1],
    ['code', 'Код', '\\begin{lstlisting}[language=Python]\n\n\\end{lstlisting}\n', 17],
    ['list', 'Список', '\\begin{itemize}\n  \\item \n\\end{itemize}\n', 15],
    ['cite', 'Посилання [1]', '\\cite{1}'],
  ];
  pane.innerHTML = `
    <div class="tex-toolbar">
      ${tools.map(([id, label]) => `<button type="button" class="snip" data-tex="${id}">${esc(label)}</button>`).join('')}
      <button type="button" class="snip snip-py" data-tex-py>${ICONS.python} Формула з Python</button>
      <button type="button" class="snip" data-tex-img>${ICONS.image} Рисунок</button>
    </div>
    <textarea id="tex-src" class="tex-src" spellcheck="false" rows="16"></textarea>
    <div class="tex-status text-sm" id="tex-status"></div>
    <div id="tex-warnings"></div>
    <div class="tex-images" id="tex-images"></div>
    <p class="text-sm text-muted">Підтримується: <code>\\section</code>, <code>\\subsection</code>, <code>\\section*{Мета роботи / Вступ / Висновки}</code>,
      абзаци, <code>$…$</code>, <code>equation</code>/<code>align</code>/<code>\\[…\\]</code>, <code>lstlisting</code>/<code>minted</code>,
      <code>itemize</code>/<code>enumerate</code>, <code>figure</code> з рисунками звіту, <code>thebibliography</code>.
      Повний документ з преамбулою — кнопка «.tex» угорі (для Overleaf, XeLaTeX).</p>`;
  const ta = pane.querySelector('#tex-src');
  ta.value = tex.source;
  autoGrow(ta);
  ta.addEventListener('input', () => {
    tex.source = ta.value;
    tex.dirty = true;
    setTexStatus('Є незбережені зміни…');
    parseTexSoon();
    clearTimeout(tex.saveTimer);
    tex.saveTimer = setTimeout(saveTex, 2500);       // LaTeX mode saves by itself
  });
  ta.addEventListener('keydown', e => {
    if (e.key === 'Tab') { e.preventDefault(); insertAtCursor(ta, '  '); }
  });
  pane.querySelector('.tex-toolbar').addEventListener('click', e => {
    const b = e.target.closest('[data-tex]');
    if (b) {
      const [, , text, back = 0] = tools.find(t => t[0] === b.dataset.tex);
      insertAtCursor(ta, text, back);
    }
    if (e.target.closest('[data-tex-py]')) {
      openPyDialog(latex => insertAtCursor(ta, `\\begin{equation}\n  ${latex}\n\\end{equation}\n`));
    }
    if (e.target.closest('[data-tex-img]')) {
      const input = Object.assign(document.createElement('input'), { type: 'file', accept: 'image/*', multiple: true });
      input.onchange = async () => {
        const created = await uploadImages(reportId, [...input.files], 'u');
        reportImages.push(...created);
        created.forEach(img => insertAtCursor(ta, figureSnippet(img)));
        renderTexImages();
      };
      input.click();
    }
  });
  pane.querySelector('#tex-images').addEventListener('click', e => {
    const ins = e.target.closest('[data-tex-insert]');
    if (ins) insertAtCursor(ta, figureSnippet(reportImages.find(i => i.id === Number(ins.dataset.texInsert))));
    const view = e.target.closest('[data-tex-view]');
    if (view) openLightbox(docOrder(reportImages), Number(view.dataset.texView));
  });
  renderTexImages();
  parseTexSoon(0);
}

const figureSnippet = img =>
  `\\begin{figure}[h]\n  \\centering\n  \\includegraphics[width=0.8\\textwidth]{img-${img.id}}\n  \\caption{${texEscape(img.caption || '')}}\n\\end{figure}\n`;

function renderTexImages() {
  const box = document.getElementById('tex-images');
  if (!box) return;
  if (!reportImages.length) { box.innerHTML = ''; return; }
  box.innerHTML = `<p class="text-sm"><b>Рисунки звіту</b> <span class="text-muted">— у коді це <code>img-номер</code></span></p>
    <div class="tex-img-list">${reportImages.map(img => `
      <div class="tex-img ${img.section_path === 'u' ? 'unused' : ''}">
        <button class="img-view" data-tex-view="${img.id}" title="Переглянути"><img src="${API_URL}${img.url}" alt="" loading="lazy"></button>
        <code>img-${img.id}</code>
        <span class="text-sm text-muted">${img.section_path === 'u' ? 'не вставлено' : `розділ ${img.section_path.split('.').map(n => Number(n) + 1).join('.')}`}</span>
        <button class="btn btn-ghost btn-sm" data-tex-insert="${img.id}">Вставити</button>
      </div>`).join('')}</div>`;
}

const setTexStatus = msg => { const el = document.getElementById('tex-status'); if (el) el.textContent = msg; };

function parseTexSoon(delay = 500) {
  clearTimeout(tex.timer);
  tex.timer = setTimeout(parseTex, delay);
}

// Live preview / outline / readiness from the source, without saving
async function parseTex() {
  if (editorMode !== 'latex' || !reportId) return;
  try {
    const r = await req('POST', `/reports/${reportId}/latex/parse`, { source: tex.source });
    applyParsed(r);
  } catch (ex) { setTexStatus('Не вдалося розібрати: ' + ex.message); }
}

function applyParsed(r) {
  sections = toEditableSections(r.sections);
  if (r.abbreviations !== undefined) courseMeta.abbreviations = r.abbreviations;
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el && document.activeElement !== el) { el.value = value || ''; autoGrow(el); }
  };
  if (reportKind === 'essay') set('f-intro', r.introduction); else set('f-goal', r.goal);
  set('ai-output', r.conclusion);
  set('f-refs', (r.bibliography || []).join('\n'));
  // figure placement as in the source (saved on the server by saveTex)
  const placed = new Map(r.figures.map(f => [f.image_id, f]));
  reportImages = reportImages.map(img => {
    const f = placed.get(img.id);
    return f ? { ...img, section_path: f.section_path, position: f.position, caption: f.caption ?? img.caption }
             : { ...img, section_path: 'u' };
  });
  tex.warnings = r.warnings || [];
  const w = document.getElementById('tex-warnings');
  if (w) w.innerHTML = tex.warnings.length
    ? `<div class="tex-warn"><b>Спрощено при розборі:</b><ul>${tex.warnings.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
  if (!tex.dirty) setTexStatus(`Розібрано: ${sections.length} ${plural(sections.length, 'розділ', 'розділи', 'розділів')}`);
  renderTexImages();
  renderOutline();
  updateReadiness();
  refreshLive();
}

async function saveTex() {
  clearTimeout(tex.saveTimer);
  if (editorMode !== 'latex') return true;
  setTexStatus('Зберігаємо…');
  try {
    const r = await req('PATCH', `/reports/${reportId}`, { ...titlePayload(), editor_mode: 'latex', latex_source: tex.source });
    tex.dirty = false;
    reportImages = await req('GET', `/reports/${reportId}/images`).catch(() => reportImages);
    applyParsed({ sections: r.sections, goal: r.goal, introduction: r.introduction, conclusion: r.conclusion,
                  bibliography: r.bibliography, warnings: r.latex_warnings,
                  figures: reportImages.filter(i => i.section_path !== 'u')
                    .map(i => ({ image_id: i.id, section_path: i.section_path, position: i.position, caption: i.caption })) });
    setTexStatus('Збережено');
    return true;
  } catch (ex) {
    setTexStatus('Не збережено: ' + ex.message);
    toast('Не вдалося зберегти LaTeX: ' + ex.message, 'err');
    return false;
  }
}

// Text written outside the code (AI conclusion / introduction, conclusion box) goes into its \section*
function syncTexSection(names, text, opts) {
  tex.source = latexReplaceSection(tex.source, names, textToLatexParas(text), opts);
  const ta = document.getElementById('tex-src');
  if (ta) { ta.value = tex.source; autoGrow(ta); }
  tex.dirty = true;
  clearTimeout(tex.saveTimer);
  tex.saveTimer = setTimeout(saveTex, 1500);
}

function jumpToTexHeading(i, j) {
  const ta = document.getElementById('tex-src');
  if (!ta) return;
  const re = /\\(sub)?section(\*?)\s*\{/g;
  let m, sec = -1, sub = -1, pos = null;
  while ((m = re.exec(ta.value))) {
    if (m[2]) continue;
    if (!m[1]) { sec++; sub = -1; } else sub++;
    if (sec === i && (j === null ? !m[1] : m[1] && sub === j)) { pos = m.index; break; }
  }
  if (pos === null) return;
  ta.focus();
  ta.setSelectionRange(pos, pos);
  const line = ta.value.slice(0, pos).split('\n').length;
  const lh = parseFloat(getComputedStyle(ta).lineHeight) || 20;
  window.scrollTo({ top: ta.getBoundingClientRect().top + window.scrollY + line * lh - 160, behavior: 'smooth' });
}

/* ── save ── */
function titlePayload() {
  const v = id => document.getElementById(id)?.value ?? '';
  return {
    kind:             reportKind,
    level:            reportLevel,
    ministry:         v('f-ministry'),
    institution:      v('f-institution'),
    city:             v('f-city'),
    title:            v('f-title'),
    discipline:       v('f-discipline'),
    teacher:          v('f-teacher'),
    teacher_gender:   genders.teacher,
    teacher_position: v('f-position'),
    student_name:     v('f-student').split('\n').map(l => l.trim()).filter(Boolean).join('\n'),
    student_gender:   genders.student,
    group:            v('f-group'),
    faculty:          v('f-faculty'),
    department:       v('f-department'),
    work_date:        v('f-date'),
    meta:             courseMeta,
  };
}

async function saveReport({ quiet = false } = {}) {
  const btn = document.getElementById('btn-save');
  if (reportId && editorMode === 'latex') {
    if (!quiet) setLoading(btn, true);
    const ok = await saveTex();
    if (!quiet) { setLoading(btn, false); if (ok) toast('Збережено'); }
    return ok;
  }
  if (!quiet) setLoading(btn, true);

  const payload = {
    ...titlePayload(),
    editor_mode:  'form',
    goal:         document.getElementById('f-goal').value,
    introduction: document.getElementById('f-intro').value,
    conclusion:   document.getElementById('ai-output').value,
    bibliography: refsList(),
    sections:     sectionsPayload(sections),
  };

  try {
    if (reportId) {
      await req('PATCH', `/reports/${reportId}`, payload);
      if (!quiet) toast('Збережено');
    } else {
      const r = await req('POST', '/reports', payload);
      reportId = r.id;
      window.history.replaceState({}, '', `editor.html?id=${reportId}`);
      setKind(reportKind);
      if (!quiet) toast(reportKind === 'essay' ? 'Реферат створено' : 'Звіт створено');
    }
    return true;
  } catch (ex) { toast(ex.message, 'err'); return false; }
  finally      { if (!quiet) setLoading(btn, false); }
}

/* ── AI: essay introduction ── */
async function draftIntroduction() {
  const out = document.getElementById('f-intro');
  if (out.value.trim() && !confirm('Замінити поточний вступ новою чернеткою?')) return;
  if (!(await saveReport({ quiet: true }))) return;
  const btn = document.getElementById('btn-intro');
  setLoading(btn, true);
  try {
    const r = await req('POST', `/reports/${reportId}/generate-introduction`);
    out.value = r.introduction || '';
    autoGrow(out);
    if (editorMode === 'latex') syncTexSection(['Вступ'], out.value, { atStart: true });
    updateReadiness();
    refreshLive();
    toast('Чернетку вступу готово — перевірте її');
  } catch (ex) { toast(ex.message, 'err'); }
  finally { setLoading(btn, false); }
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
    autoGrow(out);
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
      autoGrow(out);
    }
    if (data.error) fail(data.error);
    if (data.done) {
      finish();
      if (editorMode === 'latex') syncTexSection(['Висновки', 'Висновок'], text);
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

async function downloadTex() {
  if (!(await saveReport({ quiet: true }))) return;
  const btn = document.getElementById('btn-tex');
  setLoading(btn, true);
  try {
    await download(`/reports/${reportId}/download/tex`, fileName(currentTitle(), 'zip'));
    toast('Архів .tex готовий — у Overleaf оберіть компілятор XeLaTeX');
  } catch (ex) { toast(ex.message, 'err'); }
  finally { setLoading(btn, false); }
}

async function previewReport() {
  if (!(await saveReport({ quiet: true }))) return;
  // Edits made in the document go straight to the server — reload the form afterwards
  openPreview(reportId, currentTitle(), {
    readOnly: editorMode === 'latex',
    onClose: changed => changed && loadReport(reportId),
  });
}

function currentTitle() {
  return document.getElementById('f-title')?.value || `Звіт ${reportId}`;
}

/* ═══════════════════════════════════════════════════════
   GUIDED TOUR  (editor) — only when the user asks for it:
   an invite on the first visit, and "Переглянути підказки"
   in the right panel any time
═══════════════════════════════════════════════════════ */
const TOUR_KEY = 'mlgr_tour';                 // null — never answered, 'later', 'done'
const tourState = () => { try { return localStorage.getItem(TOUR_KEY); } catch { return 'done'; } };
const setTourState = v => { try { localStorage.setItem(TOUR_KEY, v); } catch { /* private mode */ } };

const LIGHTBULB = '<svg class="icon" viewBox="0 0 24 24"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.7.5 1.1 1.3 1.1 2.2h5c0-.9.4-1.7 1.1-2.2A6 6 0 0 0 12 3z"/></svg>';

// Small looping illustrations inside the tip (pure CSS, see .tour-demo in style.css)
const TOUR_DEMO = {
  doc: `<div class="tour-demo demo-doc"><div class="dd-form"><i></i><i></i><i></i></div>
          <span class="dd-arrow">→</span><div class="dd-sheet"><b></b><i></i><i></i><i></i><i></i></div></div>`,
  students: `<div class="tour-demo demo-students"><div class="ds-input"><span class="ds-l1">Петренко О. О.</span><span class="ds-l2">Коваль І. І.</span></div>
          <div class="ds-title"><span class="ds-one">Виконав:</span><span class="ds-many">Виконали:</span></div></div>`,
  blocks: `<div class="tour-demo demo-blocks"><span class="db db-t1">Текст</span><span class="db db-c">Код</span>
          <span class="db db-f">Формула</span><span class="db db-t2">Текст</span></div>`,
  formula: () => `<div class="tour-demo demo-formula"><code>$E = mc^2$</code><span class="df-arrow">→</span>
          <span class="df-out">${mathHtml('E = mc^2') || 'E = mc²'}</span></div>`,
  progress: `<div class="tour-demo demo-progress"><div class="dp-bar"><span></span></div><span class="dp-ok">✓</span></div>`,
  typing: `<div class="tour-demo demo-typing"><span>У ході виконання роботи було…</span></div>`,
  done: `<div class="tour-demo demo-done"><svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="23"/><path d="M15 27l7 7 15-15"/></svg></div>`,
};

function tourSteps() {
  const visible = sel => [...document.querySelectorAll(sel)].find(el => el.offsetParent !== null) || null;
  const essay = reportKind === 'essay', school = reportLevel === 'school', latex = editorMode === 'latex';
  return [
    { title: 'Зберемо звіт за кілька кроків',
      body: 'Покажемо, де що заповнювати. Титулку, зміст і нумерацію MLGR складе сам — ваша справа лише вміст.',
      demo: TOUR_DEMO.doc },
    { target: '#kind-seg', title: 'Що пишемо',
      body: 'Лабораторна чи реферат. Від цього залежать титулка й структура: у рефераті — вступ, розділи з нової сторінки й перелік посилань.' },
    { target: ['#level-seg', '#f-institution'], title: 'Навчальний заклад',
      body: 'Університет, коледж чи школа — і назва закладу. Почніть вводити, і з’являться підказки; місто підставиться саме.' },
    { target: '#btn-remember', title: 'Запам’ятайте один раз',
      body: 'Заклад, група й ПІБ збережуться в «Моїх даних» — і кожен наступний звіт почнеться вже заповненим.' },
    { target: ['#f-title', '#f-discipline', '#f-group'], title: 'Дані для титулки',
      body: `Назва роботи, ${school ? 'предмет і клас' : 'дисципліна й група'}. Усе це одразу з’являється на титульній сторінці.` },
    { target: ['#f-student', '.seg[data-gender="student"]'], title: 'Хто виконав',
      body: 'Кілька авторів — кожен з нового рядка. Перемикач поруч обирає «Виконав» чи «Виконала»; для кількох буде «Виконали».',
      demo: TOUR_DEMO.students },
    { target: () => visible('#f-intro') || visible('#f-goal'), title: essay ? 'Вступ' : 'Мета роботи',
      body: essay ? 'Вступ можна написати самому або попросити чернетку — кнопка «Написати чернетку» поруч.'
                  : 'Одне-два речення про те, що досліджуєте. Мета потрапить у документ і допоможе ШІ з висновками.' },
    { target: () => visible('#sections-container .section-item') || visible('#btn-add-sec'), title: 'Розділи',
      body: 'Кожен розділ — це заголовок і вміст. Нумерація «1», «1.1» ставиться сама. Додавати розділи можна й з панелі праворуч.' },
    { target: () => visible('#course-card'), title: 'Завдання і календарний план',
      body: 'Для курсової: проєкт чи робота, позначення документа, а галочкою — сторінки «Завдання» і «Календарний план» одразу після титулки. Етапи плану з підетапами а), б).' },
    { target: () => visible('#sections-container .add-bar'), title: 'Текст, код, формула, таблиця — у будь-якому порядку',
      body: 'Додавайте блоки скільки треба: текст → код → знову текст. Таблицю можна вставити з Excel. Стрілки ↑ ↓ на блоці змінюють порядок; пункти 1.1.1 — кнопкою в підрозділі.',
      demo: TOUR_DEMO.blocks },
    { target: () => visible('#sections-container .blk-formula') || visible('#sections-container [data-add="formula"]'),
      title: 'Формули',
      body: 'У тексті — між доларами: $x^2$. Окрема формула — блок «Формула» з номером (1.1). Кнопка «З Python» перетворить функцію на формулу.',
      demo: TOUR_DEMO.formula },
    { target: () => visible('#sections-container .upload-zone'), title: 'Рисунки',
      body: 'Перетягніть скріншоти — вони стануть «Рисунок 1 – …». Підпис і порядок змінюються на картці, клік відкриває перегляд.' },
    { target: () => visible('#appendix-card .panel-head'), title: 'Додатки',
      body: 'Код програми, великі таблиці, креслення — у додатки: ДОДАТОК А, Б, … кожен з нової сторінки, з нумерацією А.1 всередині.' },
    { target: '#mode-seg', title: latex ? 'Ви в режимі LaTeX' : 'Форма або LaTeX',
      body: latex ? 'Увесь вміст тут — код LaTeX. Він зберігається сам, а документ збирається з нього так само, як із форми.'
                  : 'Якщо вам зручніше LaTeX — перемкніться: увесь вміст стане кодом. Кнопка «.tex» угорі дасть архів для Overleaf.' },
    { target: () => latex ? visible('#latex-pane .tex-toolbar') : null, title: 'Кнопки вставки',
      body: 'Розділ, формула, код, рисунок — вставляються в місце курсора. Рисунки звіту в коді називаються img-номер.' },
    { target: '.outline-card .outline', title: 'Структура',
      body: 'Зміст звіту завжди під рукою: клік переносить до розділу, стрілки змінюють порядок, «+» додає підрозділ.' },
    { target: '.readiness', title: 'Готовність',
      body: 'Що ще не заповнено. Клік по пункту переносить до потрібного поля.', demo: TOUR_DEMO.progress },
    { target: '#btn-conclusion', title: 'Висновки від ШІ',
      body: 'Модель прочитає саме вашу роботу й напише чернетку. Обов’язково перечитайте її перед здачею.',
      demo: TOUR_DEMO.typing },
    { target: () => visible('.live-panel'), title: 'Як виглядатиме',
      body: 'Документ оновлюється, поки ви пишете, і сам прокручується до розділу, який ви редагуєте.' },
    { target: ['#btn-preview', '#btn-generate'], title: 'Перегляд і завантаження',
      body: '«Переглянути» відкриває документ — його можна правити прямо на сторінці, а вкладка PDF показує точний вигляд. Звідти ж — DOCX і PDF.' },
    { title: 'Готово!', body: 'Підказки завжди можна відкрити знову — кнопка «Переглянути підказки» праворуч.', demo: TOUR_DEMO.done },
  ];
}

const tourTargets = target => {
  const raw = typeof target === 'function' ? [target()] : [].concat(target).map(sel => document.querySelector(sel));
  return raw.filter(el => el && el.offsetParent !== null);
};

let tourInstance = null;

function startTour() {
  closeTourInvite();
  if (tourInstance) return;
  const steps = tourSteps().filter(s => !s.target || tourTargets(s.target).length);
  const root = document.createElement('div');
  root.className = 'tour';
  root.innerHTML = `
    <svg class="tour-shade" aria-hidden="true"><defs><mask id="tour-mask">
      <rect width="100%" height="100%" fill="#fff"/><rect class="tour-hole" rx="12" fill="#000"/></mask></defs>
      <rect width="100%" height="100%" mask="url(#tour-mask)"/></svg>
    <div class="tour-spot"></div>
    <div class="tour-tip" role="dialog" aria-modal="false" aria-labelledby="tour-title">
      <span class="tour-arrow"></span>
      <div class="tour-body"></div>
      <div class="tour-foot">
        <span class="tour-count"></span>
        <div class="tour-progress"><span></span></div>
        <div class="flex gap-6">
          <button class="btn btn-ghost btn-sm" data-tour="back">Назад</button>
          <button class="btn btn-primary btn-sm" data-tour="next">Далі</button>
        </div>
      </div>
      <button class="tour-x pv-icon-btn" data-tour="close" title="Закрити (Esc)">${ICONS.x}</button>
    </div>`;
  document.body.appendChild(root);
  const spot = root.querySelector('.tour-spot'), tip = root.querySelector('.tour-tip');
  const hole = root.querySelector('.tour-hole');
  // The dimmed page with a rounded window over the target (an SVG mask: a huge box-shadow
  // is not painted reliably on wide screens)
  const setHole = (x, y, w, h) => Object.assign(hole.style, { x: `${x}px`, y: `${y}px`, width: `${w}px`, height: `${h}px` });
  const arrow = root.querySelector('.tour-arrow');
  let i = 0, raf = 0, moveTimer = null, alive = true;

  const place = () => {
    if (!alive) return;
    const step = steps[i];
    const els = step.target ? tourTargets(step.target) : [];
    const vw = window.innerWidth, vh = window.innerHeight, pad = 8, gap = 14;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    if (!els.length) {
      root.classList.add('centered');
      setHole(vw / 2, vh / 2, 0, 0);
      tip.style.left = `${Math.round((vw - tw) / 2)}px`;
      tip.style.top = `${Math.round((vh - th) / 2)}px`;
      tip.dataset.side = 'none';
    } else {
      root.classList.remove('centered');
      const rects = els.map(el => el.getBoundingClientRect());
      const r = {
        left: Math.min(...rects.map(x => x.left)) - pad, top: Math.min(...rects.map(x => x.top)) - pad,
        right: Math.max(...rects.map(x => x.right)) + pad, bottom: Math.max(...rects.map(x => x.bottom)) + pad,
      };
      Object.assign(spot.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${r.right - r.left}px`, height: `${r.bottom - r.top}px` });
      setHole(r.left, r.top, r.right - r.left, r.bottom - r.top);
      // the side with room for the tip: right, left, below, above
      const room = { right: vw - r.right, left: r.left, bottom: vh - r.bottom, top: r.top };
      const side = room.right >= tw + gap + 12 ? 'right' : room.left >= tw + gap + 12 ? 'left'
                 : room.bottom >= th + gap + 12 ? 'bottom' : room.top >= th + gap + 12 ? 'top' : 'bottom';
      const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
      let x, y;
      if (side === 'right' || side === 'left') {
        x = side === 'right' ? r.right + gap : r.left - gap - tw;
        y = clamp((r.top + r.bottom) / 2 - th / 2, 12, vh - th - 12);
        arrow.style.top = `${clamp((r.top + r.bottom) / 2 - y, 18, th - 18)}px`;
        arrow.style.left = '';
      } else {
        x = clamp((r.left + r.right) / 2 - tw / 2, 12, vw - tw - 12);
        y = side === 'bottom' ? Math.min(r.bottom + gap, vh - th - 12) : Math.max(r.top - gap - th, 12);
        arrow.style.left = `${clamp((r.left + r.right) / 2 - x, 18, tw - 18)}px`;
        arrow.style.top = '';
      }
      tip.dataset.side = side;
      tip.style.left = `${Math.round(x)}px`;
      tip.style.top = `${Math.round(y)}px`;
    }
    raf = requestAnimationFrame(place);
  };

  const show = n => {
    i = Math.max(0, Math.min(steps.length - 1, n));
    const step = steps[i];
    root.classList.add('moving');                       // spot glides to the new target
    clearTimeout(moveTimer);
    moveTimer = setTimeout(() => root.classList.remove('moving'), 550);
    tip.classList.remove('in');
    const demo = typeof step.demo === 'function' ? step.demo() : (step.demo || '');
    root.querySelector('.tour-body').innerHTML = `
      ${demo}
      <h3 id="tour-title">${esc(step.title)}</h3>
      <p>${esc(step.body)}</p>`;
    root.querySelector('.tour-count').textContent = `${i + 1} / ${steps.length}`;
    root.querySelector('.tour-progress span').style.width = `${((i + 1) / steps.length) * 100}%`;
    root.querySelector('[data-tour="back"]').hidden = i === 0;
    root.querySelector('[data-tour="next"]').textContent = i === 0 ? 'Почати' : i === steps.length - 1 ? 'Завершити' : 'Далі';
    const els = step.target ? tourTargets(step.target) : [];
    els[0]?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    requestAnimationFrame(() => requestAnimationFrame(() => tip.classList.add('in')));
    root.querySelector('[data-tour="next"]').focus({ preventScroll: true });
  };

  const close = finished => {
    alive = false;
    cancelAnimationFrame(raf);
    document.removeEventListener('keydown', onKey, true);
    root.classList.add('out');
    setTimeout(() => root.remove(), 260);
    tourInstance = null;
    setTourState('done');
    document.getElementById('btn-tour')?.classList.remove('is-new');
    if (finished) toast('Підказки завжди тут — кнопка «Переглянути підказки» праворуч');
  };
  const onKey = e => {
    if (e.target.matches?.('input, textarea, [contenteditable]')) return;
    if (e.key === 'Escape') { e.preventDefault(); close(false); }
    if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); i === steps.length - 1 ? close(true) : show(i + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(i - 1); }
  };
  root.addEventListener('click', e => {
    const act = e.target.closest('[data-tour]')?.dataset.tour;
    if (act === 'next') i === steps.length - 1 ? close(true) : show(i + 1);
    if (act === 'back') show(i - 1);
    if (act === 'close') close(false);
  });
  document.addEventListener('keydown', onKey, true);
  tourInstance = { close };
  show(0);
  requestAnimationFrame(() => root.classList.add('in'));
  place();
}

/* First visit: offer the tour, never force it */
function offerTour() {
  if (tourState() || document.querySelector('.tour-invite')) return;
  const box = document.createElement('div');
  box.className = 'tour-invite';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', 'Підказки');
  box.innerHTML = `
    <span class="ti-ico">${LIGHTBULB}</span>
    <div class="ti-text"><b>Вперше тут?</b><span>Покажемо за хвилину, як зібрати звіт — з підсвіткою кожного кроку.</span>
      <div class="flex gap-8"><button class="btn btn-primary btn-sm" data-ti="go">Показати підказки</button>
        <button class="btn btn-ghost btn-sm" data-ti="later">Не зараз</button></div></div>
    <button class="pv-icon-btn ti-x" data-ti="later" title="Закрити">${ICONS.x}</button>`;
  box.addEventListener('click', e => {
    const act = e.target.closest('[data-ti]')?.dataset.ti;
    if (act === 'go') startTour();
    if (act === 'later') {
      setTourState('later');
      closeTourInvite();
      toast('Добре! Підказки можна відкрити будь-коли — кнопка праворуч');
    }
  });
  document.body.appendChild(box);
  requestAnimationFrame(() => box.classList.add('in'));
}

function closeTourInvite() {
  const box = document.querySelector('.tour-invite');
  if (!box) return;
  box.classList.remove('in');
  setTimeout(() => box.remove(), 250);
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

/* ═══════════════════════════════════════════════════════
   DOCUMENT  (HTML copy of the .docx — used by the editable
   document and by the live preview in the editor)
═══════════════════════════════════════════════════════ */
const docLines = t => String(t || '').split('\n').map(l => l.trim()).filter(Boolean);
// Paragraphs with inline formulas rendered; editable ones switch to raw text while focused
const mathParas = text => {
  const lines = docLines(text);
  return lines.length ? lines.map(l => `<p>${inlineHtml(l)}</p>`).join('') : '<p><br></p>';
};
const blockValueField = b => b.type === 'text' ? 'text' : b.type === 'code' ? 'code' : b.type === 'table' ? 'caption' : 'latex';

// Mirror of backend course_pages.course_words
const courseWords = meta => meta?.course_type === 'work'
  ? { title: 'КУРСОВА РОБОТА', task_title: 'НА КУРСОВУ РОБОТУ', genitive: 'курсової роботи', noun: 'роботи', finished: 'закінченої роботи', topic_hint: '(тема роботи)' }
  : { title: 'КУРСОВИЙ ПРОЄКТ', task_title: 'НА КУРСОВИЙ ПРОЄКТ', genitive: 'курсового проєкту', noun: 'проєкту', finished: 'закінченого проєкту', topic_hint: '(тема проєкту)' };

const SUB_LETTERS = 'абвгдежиклмнпрстуфхцшщюя';
function calendarRows(meta) {
  let n = 0, sub = 0;
  return (meta?.calendar || []).filter(r => (r.stage || '').trim()).map(r => {
    if (r.sub) {
      const stage = /^\S{1,2}\)/.test(r.stage.trim()) ? r.stage.trim() : `${SUB_LETTERS[sub++ % SUB_LETTERS.length]}) ${r.stage.trim()}`;
      return { no: '', stage, deadline: r.deadline || '', note: r.note || '' };
    }
    sub = 0;
    return { no: String(++n), stage: r.stage.trim(), deadline: r.deadline || '', note: r.note || '' };
  });
}

/* ЗАВДАННЯ and КАЛЕНДАРНИЙ ПЛАН of a course work (read-only here; edited in the form) */
function taskSheetsHtml(doc) {
  const m = doc.meta || {};
  const w = courseWords(m);
  const v = x => esc(String(x || ''));
  const line = (label, value) => `<div class="dv-field"><span class="lbl">${esc(label)}</span><span class="u">${v(value)}</span></div>`;
  const long = (label, value) => `<p class="dv-long">${esc(label)} <u>&nbsp;${v(value)}&nbsp;</u></p>`;
  const student = docLines(doc.student_name)[0] || '';
  const supervisors = docLines(doc.teacher);
  const fields = [
    [`Тема ${w.noun}:`, doc.title], [`Термін здачі студентом ${w.finished}:`, m.deadline], [`Вхідні дані до ${w.noun}:`, m.input_data],
    ['Зміст розрахунково-пояснювальної записки (перелік питань, які підлягають розробці):', m.contents],
    ['Перелік графічного матеріалу (з точним визначенням обов’язкових креслень):', m.graphics],
    ['Дата видачі завдання:', m.issue_date],
  ];
  const rows = calendarRows(m).map(r => `<tr><td>${esc(r.no)}</td><td>${esc(r.stage)}</td><td>${esc(r.deadline)}</td><td>${esc(r.note)}</td></tr>`).join('');
  const sign = [['Студент:', student, '(прізвище, ініціали)'], ...supervisors.map(s => ['Керівник роботи:', s, '(посада, прізвище, ініціали)'])]
    .map(([l, n, h]) => `<tr><td>${esc(l)}</td><td>______________</td><td>${esc(n)}</td></tr><tr class="h"><td></td><td>(підпис)</td><td>${h}</td></tr>`).join('');
  return `
      <section class="dv-sheet dv-task" id="dv-task">
        <p class="c">${esc((doc.institution || '').toUpperCase())}</p>
        ${line('Факультет:', doc.faculty)}${line('Кафедра:', doc.department)}${line('Спеціальність:', m.specialty)}
        <p class="dv-plain">Курс <u>&nbsp;${v(m.year_of_study)}&nbsp;</u> група <u>&nbsp;${v(doc.group)}&nbsp;</u> семестр <u>&nbsp;${v(m.semester)}&nbsp;</u></p>
        <p>&nbsp;</p>
        <p class="c b">ЗАВДАННЯ</p><p class="c b">${w.task_title}</p>
        ${line(doc.student_gender === 'f' ? 'Студентці' : 'Студентові', m.student_full_dative || student)}
        <p class="dv-hint">(прізвище, ім’я, по батькові)</p>
        ${fields.map(([l, x], k) => long(`${k + 1}. ${l}`, x)).join('')}
        ${editable_note()}
      </section>
      <section class="dv-sheet dv-task" id="dv-plan">
        <p class="c b">КАЛЕНДАРНИЙ ПЛАН</p><p>&nbsp;</p>
        <table class="dv-grid"><thead><tr><th>№</th><th>Назви етапів ${w.genitive}</th><th>Строк виконання етапів роботи</th><th>Примітка</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" class="muted">Етапи додаються у формі «Курсова: завдання і план»</td></tr>'}</tbody></table>
        <p>&nbsp;</p>${line('Дата видачі завдання:', m.issue_date)}
        <table class="dv-sign-tbl">${sign}</table>
      </section>`;
}
const editable_note = () => '<p class="dv-note">Завдання й календарний план заповнюються у формі редактора (картка «Курсова: завдання і план»).</p>';

function buildDocSheets(doc, images, { editable = false } = {}) {
  const kind = doc.kind || 'lab';
  const essayLike = kind !== 'lab';
  const course = kind === 'course';
  const meta = doc.meta || {};
  const editAttr = (bind, ph, k = 'line') => editable
    ? `data-bind="${bind}" data-kind="${k}" data-ph="${esc(ph)}" contenteditable="${k === 'paras' ? 'true' : PLAIN_EDIT}" spellcheck="true"`
    : `data-bind="${bind}" data-kind="${k}" data-ph="${esc(ph)}"`;
  const textBlock = (bind, ph, text) =>
    `<div class="dv-text ${hasInlineMath(text) ? 'has-math' : ''}" ${editAttr(bind, ph, 'paras')}>${mathParas(text)}</div>`;
  const pagebreak = essayLike ? '<div class="dv-pagebreak" aria-hidden="true"><span>нова сторінка</span></div>' : '';
  const titlePage = titlePageHtml(doc, editAttr, editable);
  const labels = sectionLabels(doc.sections);

  // Numbering as in report_outline.py: formulas always (section.n); listings, figures, tables
  // through the document in a lab report, within the section otherwise and in appendices
  const global = { listing: 0, figure: 0, table: 0 };
  const toc = [];

  const itemHtml = (item, path, depth, label, ctx) => {
    const isApp = depth === 1 && item.appendix;
    const tag = `h${depth}`;
    const place = depth === 1 ? (isApp ? 'Назва додатка' : 'Назва розділу') : depth === 2 ? 'Назва підрозділу' : 'Назва пункту';
    const title = item.title.trim() || (depth === 1 ? (isApp ? '' : `Розділ ${label}`) : `${depth === 2 ? 'Підрозділ' : 'Пункт'} ${label}`);
    const no = k => ctx.local ? `${ctx.sec}.${++ctx.c[k]}` : String(++global[k]);
    toc.push([isApp ? `ДОДАТОК ${label} ${item.title.trim()}` : `${label} ${depth === 1 ? title.toUpperCase() : title}`, Math.min(depth, 3), path, label, isApp]);

    let html = `
        ${depth === 1 ? pagebreak : ''}
        <div class="dv-block depth-${depth}" id="dv-${path.replaceAll('.', '-')}" data-path="${path}">
          ${editable ? `<div class="dv-hover">
            ${depth < 3 ? `<button data-act="sub" data-path="${path}" title="Додати ${depth === 1 ? 'підрозділ' : 'пункт'}">${ICONS.plus} ${depth === 1 ? 'Підрозділ' : 'Пункт'}</button>` : ''}
            <button data-act="addtext" data-path="${path}" title="Додати абзац тексту">${ICONS.text} Текст</button>
            <button data-act="addcode" data-path="${path}" title="Додати лістинг коду">${ICONS.code} Код</button>
            <button data-act="addformula" data-path="${path}" title="Додати формулу">${ICONS.sigma} Формула</button>
            <button data-act="addtable" data-path="${path}" title="Додати таблицю">${ICONS.table} Таблиця</button>
            <button data-act="img" data-path="${path}" title="Додати рисунок">${ICONS.image} Рисунок</button>
            <button data-act="del" data-path="${path}" class="danger" title="Видалити">${ICONS.trash}</button>
          </div>` : ''}
          ${isApp
            ? `<h1 class="dv-h dv-app"><span class="dv-num">Додаток ${label}</span><span class="dv-app-title" ${editAttr(`sec|${path}`, place)}>${esc(item.title)}</span></h1>`
            : `<${tag} class="dv-h"><span class="dv-num">${label}</span> <span ${editAttr(`sec|${path}`, place)}>${esc(item.title)}</span></${tag}>`}`;

    item.blocks.forEach((b, k) => {
      const bind = `blk|${path}|${k}`;
      const del = editable && (b.type !== 'text' || item.blocks.length > 1)
        ? `<button class="dv-blk-del" data-act="blkdel" data-path="${path}" data-k="${k}" title="Видалити блок">${ICONS.x}</button>` : '';
      if (b.type === 'text') {
        html += `<div class="dv-blk">${del}${textBlock(bind, 'Текст — що зроблено, які результати', b.text)}</div>`;
      } else if (b.type === 'code') {
        html += `<div class="dv-blk">${del}<p class="dv-cap-left" data-cap-of="${path}">Лістинг ${no('listing')} – ${esc(title)}</p>
          <pre class="dv-code" ${editAttr(bind, 'Код', 'code')}>${esc((b.code || '').replace(/\r/g, ''))}</pre></div>`;
      } else if (b.type === 'table') {
        const rows = b.rows?.length ? b.rows : [['']];
        const head = b.header ?? 1;
        html += `<div class="dv-blk dv-table">${del}
          <p class="dv-cap-left">Таблиця ${no('table')} – <span ${editAttr(bind, 'назва таблиці')}>${esc(b.caption || '')}</span></p>
          <table class="dv-grid">${rows.map((row, r) => `<tr>${row.map((c, ci) => {
            const t = r < head ? 'th' : 'td';
            return `<${t} ${editAttr(`tbl|${path}|${k}|${r}|${ci}`, '')}>${editable ? esc(c) : inlineHtml(c)}</${t}>`;
          }).join('')}</tr>`).join('')}</table></div>`;
      } else {
        html += `<div class="dv-blk dv-formula">${del}
          <div class="dv-f-row"><span></span><span class="dv-f-math">${mathHtml(b.latex, true) || (editable ? '<span class="dv-f-empty">формула</span>' : '')}</span><span class="dv-f-no">(${ctx.sec}.${++ctx.c.formula})</span></div>
          ${editable ? `<code class="dv-f-src" ${editAttr(bind, 'LaTeX формули, напр. \\frac{a}{b}')}>${esc(b.latex)}</code>` : ''}
        </div>`;
      }
    });

    const figs = imagesIn(images, path);
    figs.forEach((img, k) => {
      html += `<figure class="dv-fig" data-img="${img.id}">
          ${img.available === false
            ? `<div class="dv-fig-lost">Файл рисунка втрачено на сервері — видаліть його і завантажте ще раз</div>`
            : `<img src="${API_URL}${img.url}" alt="" ${editable ? `data-act="viewimg" data-img="${img.id}" title="Переглянути"` : ''}>`}
          <figcaption>Рисунок ${no('figure')} – <span ${editAttr(`img|${img.id}`, 'підпис рисунка')}>${esc(img.caption)}</span></figcaption>
          ${editable ? `<div class="dv-fig-tools">
            <button data-act="imgup" data-img="${img.id}" title="Раніше" ${k === 0 ? 'disabled' : ''}>${ICONS.up}</button>
            <button data-act="imgdown" data-img="${img.id}" title="Пізніше" ${k === figs.length - 1 ? 'disabled' : ''}>${ICONS.down}</button>
            <button data-act="delimg" data-img="${img.id}" title="Видалити рисунок">${ICONS.trash}</button>
          </div>` : ''}
        </figure>`;
    });
    html += '</div>';
    if (depth < 3) (item.subsections || []).forEach((sub, k) => { html += itemHtml(sub, `${path}.${k}`, depth + 1, `${label}.${k + 1}`, ctx); });
    return html;
  };

  const sectionHtml = (s, i) => {
    const local = essayLike || s.appendix;
    const ctx = { sec: labels[i], local, c: { listing: 0, figure: 0, table: 0, formula: 0 } };
    return itemHtml(s, String(i), 1, labels[i], ctx);
  };

  const refs = doc.bibliography || [];
  const showRefs = essayLike || refs.length > 0;
  const refsTitle = course ? 'Перелік джерел посилання' : 'Перелік посилань';
  const abbreviations = essayLike && docLines(meta.abbreviations).length;
  const front = essayLike
    ? { title: 'Вступ', bind: 'doc|introduction', ph: course ? 'Вступ: актуальність, мета, задачі, об’єкт і предмет' : 'Вступ: актуальність теми, мета реферату', text: doc.introduction }
    : { title: 'Мета роботи', bind: 'doc|goal', ph: 'Мета роботи', text: doc.goal };

  const main = doc.sections.map((s, i) => s.appendix ? '' : sectionHtml(s, i)).join('');
  const mainToc = toc.splice(0);
  const apps = doc.sections.map((s, i) => s.appendix ? sectionHtml(s, i) : '').join('');
  const appToc = toc.splice(0);
  const tocRows = [
    ...(abbreviations ? [['СКОРОЧЕННЯ ТА УМОВНІ ПОЗНАКИ', 1]] : []),
    [front.title.toUpperCase(), 1], ...mainToc, ['ВИСНОВКИ', 1],
    ...(showRefs ? [[refsTitle.toUpperCase(), 1]] : []), ...appToc,
  ];

  return titlePage
    + (course && meta.task_sheet ? taskSheetsHtml(doc) : '') + `
      <section class="dv-sheet dv-toc">
        <p class="dv-toc-title">ЗМІСТ</p>
        ${tocRows.map(([t, l, path, num, isApp]) => `<p class="dv-toc-row l${l}"><span ${path !== undefined ? `data-toc-path="${path}" data-num="${num}" data-app="${isApp ? 1 : ''}"` : ''}>${esc(t)}</span><i></i></p>`).join('')}
        <p class="dv-note">Зміст складається автоматично; номери сторінок з'являться в документі (вкладка PDF).</p>
      </section>
      <section class="dv-sheet dv-body ${essayLike ? 'is-essay' : ''} ${course ? 'is-course' : ''}">
        ${abbreviations ? `<h1 class="dv-h">Скорочення та умовні познаки</h1>${textBlock('meta|abbreviations', 'Термін – пояснення', meta.abbreviations)}${pagebreak}` : ''}
        <h1 class="dv-h">${front.title}</h1>
        ${textBlock(front.bind, front.ph, front.text)}
        ${main}
        ${editable ? `<button class="dv-add" data-act="section">${ICONS.plus} Додати розділ</button>` : '<div class="dv-add-gap"></div>'}
        ${pagebreak}
        <h1 class="dv-h" id="dv-conclusion">Висновки</h1>
        ${textBlock('doc|conclusion', 'Висновки (можна згенерувати в редакторі)', doc.conclusion)}
        ${showRefs ? `${pagebreak}
        <h1 class="dv-h" id="dv-refs">${refsTitle}</h1>
        <div class="dv-text dv-refs" ${editAttr('doc|bibliography', 'Джерела — кожне з нового рядка', 'paras')}>${mathParas(refs.join('\n'))}</div>` : ''}
        ${apps}
        ${editable ? `<button class="dv-add" data-act="appendix">${ICONS.plus} Додати додаток</button>` : ''}
      </section>`;
}

function markEmptyFields(container) {
  container.querySelectorAll('[data-bind]').forEach(el => el.classList.toggle('is-empty', !el.textContent.trim()));
}

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
  let mode = 'edit', closed = false, changed = false, editable = !opts.readOnly;
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
        teacher: doc.teacher, teacher_gender: doc.teacher_gender, teacher_position: doc.teacher_position,
        student_name: doc.student_name, student_gender: doc.student_gender, work_date: doc.work_date,
        faculty: doc.faculty, department: doc.department,
        ministry: doc.ministry, institution: doc.institution, city: doc.city,
        goal: doc.goal, introduction: doc.introduction, conclusion: doc.conclusion,
        bibliography: doc.bibliography, sections: sectionsPayload(doc.sections), meta: doc.meta || {},
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
  doc.bibliography = doc.bibliography || [];
  // LaTeX mode: the code is the source of truth, so the document here is view-only
  if (doc.editor_mode === 'latex') editable = false;
  if (!editable) {
    $('.pv-edit-only').hidden = true;
    $('[data-mode="edit"]').innerHTML = `${ICONS.eye} Документ`;
  }
  ensureKatex().then(() => { if (!closed) render(); }).catch(() => {});
  await loadTemplates().catch(() => {});

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
      ? (editable ? 'Клацніть по тексту, щоб редагувати · зміни зберігаються самі'
                  : 'Режим LaTeX: правте код у редакторі, тут — попередній вигляд')
      : pdfView?.pages ? `${pdfView.pages} ${plural(pdfView.pages, 'сторінка', 'сторінки', 'сторінок')} · A4` : '';
  }

  async function setMode(next) {
    mode = next;
    root.querySelectorAll('.pv-tabs [data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === mode));
    root.querySelectorAll('.pv-stage').forEach(s => s.hidden = s.dataset.mode !== mode);
    $('.pv-outline').hidden = mode !== 'edit';
    $('.pv-thumbs').hidden = mode !== 'pdf' || !pdfView?.pages;
    $('.pv-edit-only').hidden = mode !== 'edit' || !editable;
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
  const itemAt = path => {
    const idx = String(path).split('.').map(Number);
    let item = doc.sections[idx[0]];
    for (const k of idx.slice(1)) item = item?.subsections?.[k];
    return item;
  };
  const listOf = path => {
    const idx = String(path).split('.').map(Number);
    return { list: idx.length === 1 ? doc.sections : itemAt(idx.slice(0, -1).join('.')).subsections, index: idx[idx.length - 1] };
  };
  const getField = bind => {
    const [k, a, b, r, c] = bind.split('|');
    if (k === 'meta') return doc.meta?.[a] || '';
    if (k === 'tbl') return itemAt(a)?.blocks[+b]?.rows?.[+r]?.[+c] ?? '';
    if (k === 'doc') return a === 'bibliography' ? doc.bibliography.join('\n') : doc[a];
    if (k === 'img') return images.find(i => i.id === Number(a))?.caption ?? '';
    if (k === 'sec') return itemAt(a)?.title;
    const blk = itemAt(a)?.blocks[+b];
    return blk ? blk[blockValueField(blk)] : '';
  };
  const setField = (bind, value) => {
    const [k, a, b, r, c] = bind.split('|');
    if (k === 'meta') { doc.meta = { ...(doc.meta || {}), [a]: value }; return; }
    if (k === 'tbl') { const row = itemAt(a)?.blocks[+b]?.rows?.[+r]; if (row) row[+c] = value; return; }
    if (k === 'doc') { doc[a] = a === 'bibliography' ? docLines(value) : value; return; }
    if (k === 'img') { const img = images.find(i => i.id === Number(a)); if (img) { img.caption = value; dirtyCaptions.add(img.id); } return; }
    if (k === 'sec') { itemAt(a).title = value; return; }
    const blk = itemAt(a).blocks[+b];
    blk[blockValueField(blk)] = value;
  };

  function render() {
    const scrollTop = $('.pv-stage[data-mode="edit"]').scrollTop;
    pages.innerHTML = buildDocSheets(doc, images, { editable });
    pages.querySelectorAll('[data-bind]').forEach(markEmpty);
    renderOutlineNav();
    $('.pv-stage[data-mode="edit"]').scrollTop = scrollTop;
  }

  function markEmpty(el) {
    el.classList.toggle('is-empty', !el.textContent.trim());
  }

  // Only titles affect other places (TOC, outline, listing captions) — refresh those without re-rendering the page
  function refreshDerived() {
    pages.querySelectorAll('[data-toc-path]').forEach(span => {
      const item = itemAt(span.dataset.tocPath);
      if (!item) return;
      const depth = span.dataset.tocPath.split('.').length;
      const num = span.dataset.num;
      span.textContent = span.dataset.app ? `ДОДАТОК ${num} ${item.title.trim()}`
        : `${num} ${depth === 1 ? (item.title.trim() || `Розділ ${num}`).toUpperCase() : (item.title.trim() || num)}`;
    });
    pages.querySelectorAll('[data-cap-of]').forEach(p => {
      const item = itemAt(p.dataset.capOf);
      if (item) p.textContent = p.textContent.replace(/ – .*$/, ` – ${item.title.trim() || 'Без назви'}`);
    });
    renderOutlineNav();
  }

  function renderOutlineNav() {
    const nav = $('.pv-outline');
    const labels = sectionLabels(doc.sections);
    const item = (label, target, cls = '') =>
      `<button class="pvo-item ${cls}" data-target="${target}"><span>${esc(label)}</span></button>`;
    const sectionItems = app => doc.sections.map((s, i) => Boolean(s.appendix) !== app ? ''
      : item(`${app ? 'Додаток ' : ''}${labels[i]} ${s.title.trim() || 'Без назви'}`, `#dv-${i}`)
        + (s.subsections || []).map((b, j) => item(`${labels[i]}.${j + 1} ${b.title.trim() || 'Без назви'}`, `#dv-${i}-${j}`, 'sub')).join('')).join('');
    nav.innerHTML = `<p class="pvo-head">Зміст</p>`
      + item('Титульна сторінка', '.dv-title')
      + (pages.querySelector('#dv-task') ? item('Завдання', '#dv-task') + item('Календарний план', '#dv-plan') : '')
      + item(doc.kind === 'lab' ? 'Мета роботи' : 'Вступ', '.dv-body')
      + sectionItems(false)
      + item('Висновки', '#dv-conclusion')
      + (pages.querySelector('#dv-refs') ? item(doc.kind === 'course' ? 'Перелік джерел' : 'Перелік посилань', '#dv-refs') : '')
      + sectionItems(true)
      + (editable ? `<button class="btn btn-secondary btn-sm pvo-add" data-act="section">${ICONS.plus} Розділ</button>` : '');
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
    if (el.dataset.bind.startsWith('sec|')) refreshDerived();
    // a formula's source changed: redraw it right away
    const f = el.closest('.dv-formula');
    if (f) f.querySelector('.dv-f-math').innerHTML = mathHtml(value, true) || '<span class="dv-f-empty">формула</span>';
    if (el.dataset.bind === 'doc|student_name') render();
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
  // Paragraphs with $...$ show rendered formulas; while editing, the raw text is shown instead
  pages.addEventListener('focusin', e => {
    const el = e.target.closest?.('[data-kind="paras"]');
    if (!el?.classList.contains('has-math')) return;
    el.innerHTML = paras(getField(el.dataset.bind));
    // the swap removed the node the click put the caret in — put it at the end instead
    const range = document.createRange();
    range.selectNodeContents(el.lastElementChild || el);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  });
  // An empty paragraph block must keep one <p>, or the browser starts typing into a bare text node
  pages.addEventListener('focusout', e => {
    const el = e.target.closest?.('[data-kind="paras"]');
    if (!el) return;
    const value = getField(el.dataset.bind) || '';
    const math = hasInlineMath(value);
    el.classList.toggle('has-math', math);
    if (math) el.innerHTML = mathParas(value);
    else if (!el.querySelector('p')) el.innerHTML = paras(value);
  });

  /* structure buttons */
  root.addEventListener('click', async e => {
    const g = e.target.closest('.dv-gender');
    if (g) {
      const key = `${g.dataset.gender}_gender`;
      doc[key] = doc[key] === 'f' ? 'm' : 'f';
      touch();
      render();          // one gender changes several words (Виконала, учениця)
      return;
    }
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const path = btn.dataset.path || '';
    const block = path ? itemAt(path) : null;

    if (act === 'section' || act === 'appendix') {
      doc.sections.push({ ...newItem(true), ...(act === 'appendix' ? { appendix: true } : {}) });
      touch(); render();
      focusBind(`sec|${doc.sections.length - 1}`);
    } else if (act === 'sub') {
      const depth = path.split('.').length;
      block.subsections = block.subsections || [];
      block.subsections.push(newItem(depth < 2));
      touch(); render();
      focusBind(`sec|${path}.${block.subsections.length - 1}`);
    } else if (act === 'addtext' || act === 'addcode' || act === 'addformula' || act === 'addtable') {
      block.blocks.push({ addtext: newTextBlock, addcode: newCodeBlock, addformula: newFormulaBlock, addtable: newTableBlock }[act]());
      touch(); render();
      focusBind(act === 'addtable' ? `tbl|${path}|${block.blocks.length - 1}|0|0` : `blk|${path}|${block.blocks.length - 1}`);
    } else if (act === 'blkdel') {
      const k = Number(btn.dataset.k);
      if (blockFilled(block.blocks[k]) && !confirm('Видалити цей блок?')) return;
      block.blocks.splice(k, 1);
      if (!block.blocks.length) block.blocks.push(newTextBlock());
      touch(); render();
    } else if (act === 'del') {
      if (hasContent(block) && !confirm('Видалити разом із вмістом і рисунками?')) return;
      const { list, index } = listOf(path);
      list.splice(index, 1);
      images = await remapImages(id, images, pathMaps.removeItem(path));
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
    } else if (act === 'viewimg') {
      openLightbox(docOrder(images), Number(btn.dataset.img));
    } else if (act === 'imgup' || act === 'imgdown') {
      images = await moveImage(id, images, Number(btn.dataset.img), act === 'imgup' ? -1 : 1);
      changed = true; filesStale = viewStale = true;
      render();
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
    try {
      await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null }).promise;
    } catch { return; }               // cancelled by a re-render (zoom) or the PDF was closed
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
