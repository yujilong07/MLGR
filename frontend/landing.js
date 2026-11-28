/* Landing page motion: intro, scroll reveal, the live editor demo in the hero,
   formula demos, requirement ↔ page highlighting. Everything degrades to the final,
   static state when the user prefers reduced motion. */
(() => {
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  document.documentElement.classList.toggle('still', still);
  requestAnimationFrame(() => document.body.classList.add('is-ready'));

  /* ── nav shadow once the page scrolls ── */
  const nav = $('#lp-nav');
  const onScroll = () => nav?.classList.toggle('scrolled', window.scrollY > 8);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ── KaTeX, loaded lazily (same CDN build the editor uses) ── */
  const KATEX = 'https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11';
  let katexP = null;
  const katex = () => katexP ??= new Promise((resolve, reject) => {
    document.head.appendChild(Object.assign(document.createElement('link'), { rel: 'stylesheet', href: `${KATEX}/katex.min.css` }));
    const s = Object.assign(document.createElement('script'), { src: `${KATEX}/katex.min.js`, async: true });
    s.onload = () => resolve(window.katex);
    s.onerror = reject;
    document.head.appendChild(s);
  });
  const math = (latex, display) => window.katex
    ? window.katex.renderToString(latex, { displayMode: display, throwOnError: false })
    : `<code>${esc(latex)}</code>`;
  const inlineMath = text => text.split(/(\$[^$]+\$)/).map(part =>
    part.startsWith('$') && part.endsWith('$') ? math(part.slice(1, -1), false) : esc(part)).join('');
  function renderFormulas() {
    $$('[data-latex]').forEach(el => { el.innerHTML = math(el.dataset.latex, el.classList.contains('fx-out')); });
    // one wrapper span: the box centres its content, loose text nodes would each become a row
    $$('[data-inline]').forEach(el => { el.innerHTML = `<span>${inlineMath(el.dataset.inline)}</span>`; });
  }
  renderFormulas();
  katex().then(renderFormulas).catch(() => {});

  /* ── scroll reveal; children of a group come in one after another ── */
  $$('[data-reveal-group]').forEach(group =>
    $$('[data-reveal]', group).forEach((el, i) => el.style.setProperty('--i', i)));
  const revealed = new Set();
  const onReveal = new Map();      // element -> callback run once when it appears
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('is-in');
    if (e.target.matches('[data-reveal-group]')) e.target.classList.add('is-in');
    io.unobserve(e.target);
    revealed.add(e.target);
    onReveal.get(e.target)?.();
  }), { threshold: 0.18, rootMargin: '0px 0px -40px 0px' });
  $$('[data-reveal], [data-reveal-group]').forEach(el => still ? el.classList.add('is-in') : io.observe(el));

  /* ── rotating word in the headline ── */
  const rot = $('.rot-word');
  if (rot && !still) {
    const words = rot.dataset.words.split('|');
    const box = rot.parentElement;
    let k = 0;
    const fit = word => {
      const probe = Object.assign(document.createElement('span'), { className: 'rot-word', textContent: word });
      probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap';
      box.appendChild(probe);
      box.style.width = `${probe.getBoundingClientRect().width}px`;
      probe.remove();
    };
    fit(words[0]);
    setInterval(async () => {
      k = (k + 1) % words.length;
      rot.classList.add('out');
      await sleep(280);
      rot.textContent = words[k];
      fit(words[k]);
      rot.classList.remove('out');
      rot.classList.add('in');
      await sleep(320);
      rot.classList.remove('in');
    }, 2600);
    window.addEventListener('resize', () => fit(rot.textContent));
  }

  /* ── hero: the editor fills itself in and the document assembles ── */
  const shot = $('#shot');
  if (shot) {
    const typed = $$('[data-type]', shot);
    const steps = $$('[data-step]', shot);
    const chips = $$('[data-chip]', shot);
    const formula = $('.shot-formula', shot);
    const saved = $('.shot-saved', shot);
    const finalState = () => {
      typed.forEach(el => { el.textContent = el.dataset.type; });
      steps.forEach(el => el.classList.add('on'));
      chips.forEach(el => el.classList.add('on'));
      formula?.classList.add('rendered');
    };
    if (still) finalState();
    else {
      let visible = false;
      new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0.2 }).observe(shot);
      const waitVisible = async () => { while (!visible) await sleep(250); };
      const type = async (el, speed) => {
        const text = el.dataset.type;
        el.classList.add('typing');
        for (let i = 1; i <= text.length; i++) {
          await waitVisible();
          el.textContent = text.slice(0, i);
          await sleep(text[i - 1] === ' ' ? speed * 0.4 : speed);
        }
        el.classList.remove('typing');
      };
      const flashSaved = () => { saved.classList.remove('on'); void saved.offsetWidth; saved.classList.add('on'); };
      (async function loop() {
        for (;;) {
          typed.forEach(el => { el.textContent = ''; });
          steps.forEach(el => el.classList.remove('on'));
          chips.forEach(el => el.classList.remove('on'));
          formula?.classList.remove('rendered');
          await sleep(500);
          await type(typed[0], 34);
          await type(typed[1], 26);
          flashSaved();
          for (const el of steps.slice(0, 3)) { el.classList.add('on'); await sleep(140); }
          await type(typed[2], 14);
          chips[0]?.classList.add('on');
          await type(typed[3], 40);
          await sleep(250);
          formula?.classList.add('rendered');
          chips[1]?.classList.add('on');
          for (const el of steps.slice(3)) { el.classList.add('on'); await sleep(120); }
          await type(typed[4], 16);
          flashSaved();
          await sleep(500);
          chips[2]?.classList.add('on');
          await sleep(4200);
        }
      })();

      // A gentle 3D tilt that follows the pointer
      const stage = $('.shot-stage');
      if (stage && window.matchMedia('(pointer: fine)').matches) {
        stage.addEventListener('pointermove', e => {
          const r = stage.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
          shot.style.transform = `rotateX(${(-y * 4).toFixed(2)}deg) rotateY(${(x * 5).toFixed(2)}deg)`;
        });
        stage.addEventListener('pointerleave', () => { shot.style.transform = ''; });
      }
    }
  }

  /* ── formula demos: the source types itself, then the formula appears ── */
  $$('.fx-card').forEach(card => {
    const src = $('.fx-src', card);
    const run = async () => {
      if (still) { src.textContent = src.dataset.fxType; card.classList.add('done'); return; }
      await sleep(Number(card.style.getPropertyValue('--i') || 0) * 350);
      const text = src.dataset.fxType;
      for (let i = 1; i <= text.length; i++) { src.textContent = text.slice(0, i); await sleep(22); }
      await sleep(200);
      card.classList.add('done');
    };
    if (still) run(); else onReveal.set(card, run);
  });

  /* ── conclusion streams in word by word ── */
  const quote = $('[data-quote]');
  if (quote && !still) {
    const words = quote.textContent.trim().split(/\s+/);
    quote.innerHTML = words.map((w, i) => `<span class="qw" style="--w:${i}">${esc(w)}</span>`).join(' ');
    onReveal.set(quote.closest('[data-reveal]'), () => quote.classList.add('play'));
  }

  /* ── requirement ↔ place on the page ── */
  const anatomy = $('.anatomy');
  const rows = $$('.spec-list [data-part]');
  if (anatomy && rows.length) {
    let auto = 0, timer = null, hovering = false;
    const show = part => {
      rows.forEach(r => r.classList.toggle('active', r.dataset.part === part));
      anatomy.dataset.show = part || '';
      $$('[data-part]', anatomy).forEach(el => el.classList.toggle('hl', el.dataset.part === part));
    };
    rows.forEach(r => {
      r.addEventListener('mouseenter', () => { hovering = true; show(r.dataset.part); });
      r.addEventListener('focus', () => show(r.dataset.part));
      r.tabIndex = 0;
    });
    $('.spec-list').addEventListener('mouseleave', () => { hovering = false; });
    $$('[data-part]', anatomy).forEach(el => el.addEventListener('mouseenter', () => { hovering = true; show(el.dataset.part); }));
    anatomy.addEventListener('mouseleave', () => { hovering = false; });
    // Walks through the requirements by itself until the user takes over
    const cycle = () => {
      if (!hovering) { show(rows[auto % rows.length].dataset.part); auto++; }
    };
    if (still) show('margins');
    else onReveal.set(anatomy, () => { cycle(); timer = setInterval(cycle, 2200); });
  }
})();
