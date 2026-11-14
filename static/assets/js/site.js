/* Brando Cantillo — interacciones sin dependencias. */
(() => {
  const d = document, root = d.documentElement;
  root.classList.add('js');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(pointer: fine)').matches;
  const $ = (s, c = d) => c.querySelector(s);
  const $$ = (s, c = d) => [...c.querySelectorAll(s)];
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  addEventListener('load', () => requestAnimationFrame(() => root.classList.add('loaded')));
  setTimeout(() => root.classList.add('loaded'), 1200);

  /* Menú */
  const burger = $('.burger'), menu = $('#menu');
  burger?.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    burger.setAttribute('aria-expanded', open);
    d.body.style.overflow = open ? 'hidden' : '';
  });
  $$('#menu a').forEach(a => a.addEventListener('click', () => { menu.classList.remove('open'); burger?.setAttribute('aria-expanded', 'false'); d.body.style.overflow = ''; }));

  /* Hero: lente que revela el color sobre la foto en blanco y negro */
  const photo = $('.hero-photo');
  if (photo && !reduce) {
    const set = (x, y, r) => { photo.style.setProperty('--mx', x + 'px'); photo.style.setProperty('--my', y + 'px'); if (r != null) photo.style.setProperty('--rad', r + 'px'); };
    const R = () => Math.min(170, photo.clientWidth * .3);
    const toLocal = e => { const b = photo.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top]; };
    photo.addEventListener('pointerenter', e => { const [x, y] = toLocal(e); set(x, y, R()); });
    photo.addEventListener('pointermove', e => { const [x, y] = toLocal(e); set(x, y); });
    photo.addEventListener('pointerleave', () => photo.style.setProperty('--rad', '0px'));
    if (!fine) {  // móvil: la lente aparece sobre el rostro y sigue el dedo
      setTimeout(() => set(photo.clientWidth * .5, photo.clientHeight * .3, R() * .8), 900);
      photo.addEventListener('touchmove', e => { const t = e.touches[0]; const [x, y] = toLocal(t); set(x, y); }, { passive: true });
    }
  } else if (photo) photo.style.setProperty('--rad', '0px');

  /* Manifiesto palabra por palabra */
  const q = $('.manifesto blockquote p');
  let words = [];
  if (q) {
    const hl = (q.dataset.highlight || '').split('|');
    q.innerHTML = q.textContent.trim().split(/\s+/).map(w => `<span class="w${hl.includes(w.toLowerCase().replace(/[.,;:]/g, '')) ? ' hl' : ''}">${w}</span>`).join(' ');
    words = $$('.w', q);
  }

  /* Revelado sutil */
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -10% 0px' });
  $$('.reveal').forEach(el => reduce ? el.classList.add('in') : io.observe(el));

  /* Contador (solo cifras reales del contenido) */
  $$('[data-count]').forEach(el => {
    const to = +el.dataset.count; if (reduce) { el.textContent = to; return; }
    el.textContent = '0';
    new IntersectionObserver((es, o) => es.forEach(e => {
      if (!e.isIntersecting) return; o.disconnect();
      const t0 = performance.now();
      const step = t => { const p = clamp((t - t0) / 1100); el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    }), { threshold: .6 }).observe(el);
  });

  /* Marketing: la foto sigue sutilmente el puntero */
  const mk = $('.mk-photo');
  if (mk && fine && !reduce) {
    mk.addEventListener('pointermove', e => { const b = mk.getBoundingClientRect(); mk.style.setProperty('--px', ((e.clientX - b.left) / b.width - .5) * -14 + 'px'); mk.style.setProperty('--py', ((e.clientY - b.top) / b.height - .5) * -14 + 'px'); });
    mk.addEventListener('pointerleave', () => { mk.style.setProperty('--px', '0px'); mk.style.setProperty('--py', '0px'); });
  }

  /* Botones magnéticos (solo con mouse) */
  if (fine && !reduce) $$('[data-magnetic]').forEach(b => {
    b.addEventListener('pointermove', e => { const r = b.getBoundingClientRect(); b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * .18}px,${(e.clientY - r.top - r.height / 2) * .3}px)`; });
    b.addEventListener('pointerleave', () => { b.style.transform = ''; });
  });

  /* Scroll: nav sobre fondo oscuro, escalera, manifiesto, tarjetas apiladas, progreso de lectura */
  const nav = $('.nav'), darks = $$('[data-dark]');
  const ladder = $('.ladder'), rungs = $$('.rung');
  const manif = $('.manifesto-stage');
  const cards = $$('.stack-card');
  const progress = $('.progress'), article = $('.prose');
  const toc = $$('.toc a'), heads = toc.map(a => d.getElementById(a.hash.slice(1))).filter(Boolean);
  let ticking = false;
  const frame = () => {
    ticking = false;
    const navH = nav ? nav.offsetHeight : 0;
    if (nav) nav.classList.toggle('on-dark', darks.some(s => { const r = s.getBoundingClientRect(); return r.top <= navH / 2 && r.bottom > navH / 2; }));
    if (ladder) {
      const r = ladder.getBoundingClientRect(), mid = innerHeight * .62;
      const p = reduce ? 1 : clamp((mid - r.top) / r.height);
      ladder.style.setProperty('--fill', p.toFixed(3));
      rungs.forEach(g => g.classList.toggle('lit', reduce || g.getBoundingClientRect().top + 30 < mid));
    }
    if (manif && words.length && !reduce) {
      const wide = innerWidth > 900;
      const r = manif.getBoundingClientRect();
      const p = wide ? clamp(-r.top / (r.height - innerHeight)) : clamp((innerHeight - $('.manifesto blockquote').getBoundingClientRect().top) / (innerHeight * .85));
      const n = Math.round(p * 1.15 * words.length);
      words.forEach((w, i) => w.classList.toggle('on', i < n));
    }
    if (cards.length && !reduce) cards.forEach((c, i) => {
      const next = cards[i + 1]; if (!next) return;
      const cover = clamp(1 - (next.getBoundingClientRect().top - c.getBoundingClientRect().top) / c.offsetHeight);
      c.style.transform = `scale(${1 - cover * .05})`; c.style.filter = `brightness(${1 - cover * .25})`;
    });
    if (progress && article) { const r = article.getBoundingClientRect(); progress.style.setProperty('--read', clamp(-r.top / (r.height - innerHeight)).toFixed(4)); }
    if (heads.length) { let cur = heads[0]; heads.forEach(h => { if (h.getBoundingClientRect().top < 160) cur = h; }); toc.forEach(a => a.classList.toggle('active', a.hash === '#' + cur.id)); }
  };
  const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  if (reduce) words.forEach(w => w.classList.add('on'));
  frame();
})();

/* Casos: pestañas accesibles (clic, teclado y flechas) */
(() => {
  document.querySelectorAll('[data-tabs]').forEach(box => {
    const tabs = [...box.querySelectorAll('[role="tab"]')];
    const show = t => {
      tabs.forEach(x => { const on = x === t; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; document.getElementById(x.getAttribute('aria-controls')).hidden = !on; });
      t.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    };
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => show(t));
      t.addEventListener('keydown', e => {
        const k = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
        if (k) { e.preventDefault(); const n = tabs[(i + k + tabs.length) % tabs.length]; n.focus(); show(n); }
      });
    });
  });
})();

/* Medición: cada clic en WhatsApp o correo cuenta como contacto (lead) en Google Analytics */
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[href]');
  if (!a || typeof window.gtag !== 'function') return;
  const h = a.getAttribute('href');
  const metodo = /wa\.me|whatsapp/.test(h) ? 'whatsapp' : h.startsWith('mailto:') ? 'email' : null;
  if (metodo) window.gtag('event', 'generate_lead', { method: metodo, link_text: (a.textContent || '').trim().slice(0, 60), page_path: location.pathname });
}, { capture: true });
