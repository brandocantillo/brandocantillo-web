#!/usr/bin/env python3
"""Genera el sitio estático de Brando Cantillo en ./public

Uso:  python3 build.py
Lee:  config/site.json, content/posts/*.md, templates/*.html, static/
Solo usa la librería estándar de Python (corre igual en tu PC o en GitHub Actions).
"""
import json, re, shutil, html, math
from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime

ROOT = Path(__file__).parent
OUT = ROOT / "public"
CFG = json.loads((ROOT / "config/site.json").read_text(encoding="utf-8"))
URL = CFG["url"].rstrip("/")
TPL = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "templates").glob("*.html")}
esc = lambda s: html.escape(str(s or ""), quote=True)

# ---------------------------------------------------------------- markdown
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    def link(m):
        href = m.group(2).replace("&amp;", "&")
        ext = href.startswith("http") and not href.startswith(URL)
        rel = ' target="_blank" rel="noopener"' if ext else ""
        return f'<a href="{esc(href)}"{rel}>{m.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)

def slugify(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80]

def markdown(md):
    """Conversor mínimo: ##/###, párrafos, listas, citas, ---, negrita, cursiva, enlaces."""
    out, toc, para, lst = [], [], [], None
    def flush():
        nonlocal para, lst
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
        if lst: out.append(f"<{lst[0]}>" + "".join(f"<li>{inline(i)}</li>" for i in lst[1]) + f"</{lst[0]}>"); lst = None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip(): flush(); continue
        m = re.match(r"^(#{2,3})\s+(.*)", line)
        if m:
            flush(); lvl, txt = len(m.group(1)), m.group(2).strip()
            hid = slugify(txt)
            if lvl == 2: toc.append((hid, txt))
            out.append(f'<h{lvl} id="{hid}">{inline(txt)}</h{lvl}>'); continue
        if re.match(r"^#\s", line): continue  # el H1 lo pone la plantilla
        if line.strip() in ("---", "***"): flush(); out.append("<hr>"); continue
        if line.startswith(">"): flush(); out.append("<blockquote><p>" + inline(line.lstrip("> ").strip()) + "</p></blockquote>"); continue
        m = re.match(r"^\s*([-*]|\d+[.)])\s+(.*)", line)
        if m:
            if para: flush()
            kind = "ol" if m.group(1)[0].isdigit() else "ul"
            if not lst or lst[0] != kind: flush(); lst = (kind, [])
            lst[1].append(m.group(2)); continue
        if lst: flush()
        para.append(line.strip())
    flush()
    return "\n".join(out), toc

# ---------------------------------------------------------------- contenido
def load_posts():
    posts = []
    for f in sorted((ROOT / "content/posts").glob("*.md")):
        txt = f.read_text(encoding="utf-8")
        m = re.match(r"^---json\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
        if not m: print("⚠️  sin metadatos:", f.name); continue
        meta, body = json.loads(m.group(1)), m.group(2)
        if meta.get("draft"): continue
        meta["html"], meta["toc"] = markdown(body)
        words = len(re.findall(r"\w+", body))
        meta["words"], meta["minutes"] = words, max(1, math.ceil(words / 230))
        meta.setdefault("slug", slugify(meta["title"]))
        meta.setdefault("updated", meta["date"])
        meta["url"] = f"/columnas/{meta['slug']}/"
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts

MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
def fecha(iso):
    d = datetime.fromisoformat(iso[:10]); return f"{d.day} de {MESES[d.month-1]} de {d.year}"

# ---------------------------------------------------------------- plantillas
def render(tpl, **kw):
    s = TPL[tpl]
    for _ in range(2):  # permite parciales dentro de parciales
        s = re.sub(r"\{\{>\s*(\w+)\s*\}\}", lambda m: TPL[m.group(1)], s)
    from urllib.parse import quote as _q
    kw.setdefault("wa", f'https://wa.me/{CFG["whatsapp"]}?text=' + _q("Hola Brando, vengo de tu página web y quiero hablar contigo."))
    kw.setdefault("year", datetime.now().year)
    def rep(m):
        k = m.group(1)
        if k in kw: return str(kw[k])
        if k.startswith("cfg."):
            v = CFG
            for part in k[4:].split("."): v = v.get(part, "") if isinstance(v, dict) else ""
            return esc(v)
        return ""
    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", rep, s)

def person_ld():
    return {"@type": "Person", "@id": URL + "/#brando", "name": CFG["name"], "url": URL + "/",
            "image": URL + "/assets/img/brando-cantillo-estratega-politico.jpg", "jobTitle": CFG["job_title"],
            "description": CFG["short_bio"], "knowsAbout": CFG["knows_about"],
            "address": {"@type": "PostalAddress", "addressLocality": CFG["city"], "addressRegion": CFG["region"], "addressCountry": CFG["country"]},
            "sameAs": [v for v in CFG["social"].values() if v and "CAMBIAR" not in v]}

def head(title, desc, path, image=None, kind="website", ld=None, extra=""):
    image = image or "/assets/img/og-brando-cantillo.jpg"
    ld = ld or []
    graph = {"@context": "https://schema.org", "@graph": [person_ld(), {"@type": "WebSite", "@id": URL + "/#web", "url": URL + "/", "name": CFG["name"], "inLanguage": CFG["lang"], "publisher": {"@id": URL + "/#brando"}}] + ld}
    ga = ""
    if CFG.get("ga4_id"):
        g = CFG["ga4_id"]
        ga = f'<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{g}");</script>'
    ver = f'<meta name="google-site-verification" content="{esc(CFG["google_site_verification"])}">' if CFG.get("google_site_verification") else ""
    return render("_head", title=esc(title), desc=esc(desc), canonical=URL + path, image=URL + image, kind=kind,
                  jsonld=json.dumps(graph, ensure_ascii=False).replace("</", "<\\/"), ga=ga, verification=ver, extra=extra)

ARROW = '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
def post_rows(posts, n=None):
    if not posts: return '<li class="empty">Las primeras columnas llegan pronto.</li>'
    rows = []
    for p in posts[:n]:
        cat = CFG["categories"].get(p["category"], {}).get("name", "")
        rows.append(f'<li class="post-row"><a href="{p["url"]}"><time datetime="{p["date"][:10]}">{fecha(p["date"])}</time>'
                    f'<div><span class="cat">{esc(cat)} · {p["minutes"]} min</span><h3>{esc(p["title"])}</h3><p>{esc(p["description"])}</p></div><span class="arrow">{ARROW}</span></a></li>')
    return "\n".join(rows)

def write(path, content):
    # quita enlaces a redes que aún no están configuradas (href vacío)
    content = re.sub(r'<a href=""[^>]*>[^<]*</a>', '', content)
    f = OUT / path.lstrip("/"); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(content, encoding="utf-8")

# ---------------------------------------------------------------- build
def build():
    if OUT.exists(): shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    posts = load_posts()
    pol = [p for p in posts if p["category"] == "comunicacion-politica"]
    ia = [p for p in posts if p["category"] == "ia-para-emprendedores"]

    # Home
    faq_home = [
        ("¿Qué hace un estratega político?", "Diseña cómo se comunica un candidato, un gobierno o un partido: qué dice, a quién, por qué canal y en qué momento. Une investigación del territorio, mensaje, contenido digital, pauta y medición."),
        ("¿Qué hace un consultor de campañas?", "Acompaña al candidato desde el diagnóstico hasta el día de la elección: estrategia, mensaje, plan de medios, campaña digital, equipo territorial y seguimiento de resultados."),
        ("¿Quién hace marketing político en el Cesar?", "Brando Cantillo ha liderado la comunicación de campañas en el Cesar para la Gobernación, la Cámara de Representantes, el Senado y alcaldías como Agustín Codazzi, y trabaja con candidatos de todo Colombia."),
        ("¿Dónde puedo leer las columnas de Brando Cantillo?", "En la sección Columnas de este sitio, con análisis diarios sobre marketing político, comunicación política, marca personal e IA para emprendedores."),
    ]
    ld_home = [{"@type": "ProfessionalService", "@id": URL + "/#servicio", "name": f'{CFG["name"]} — Estrategia y marketing político', "url": URL + "/",
                "image": URL + "/assets/img/og-brando-cantillo.jpg", "founder": {"@id": URL + "/#brando"}, "areaServed": {"@type": "Country", "name": "Colombia"},
                "serviceType": ["Consultoría política", "Estrategia electoral", "Comunicación de gobierno", "Reputación digital"]},
               {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_home]}]
    write("index.html", render("home", head=head(CFG["title"], CFG["description"], "/", ld=ld_home,
          extra='<link rel="preload" as="image" href="/assets/img/brando-cantillo-ia-emprendedores-1080.webp" imagesrcset="/assets/img/brando-cantillo-ia-emprendedores-640.webp 640w, /assets/img/brando-cantillo-ia-emprendedores-1080.webp 1080w, /assets/img/brando-cantillo-ia-emprendedores-1600.webp 1600w" imagesizes="50vw">'),
          pol_rows=post_rows(posts, 3),
          faq="".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq_home)))

    # Marketing
    ld_mk = [{"@type": "Service", "name": "Marca personal y formatos de contenido para comunidades digitales", "provider": {"@id": URL + "/#brando"},
              "areaServed": {"@type": "Country", "name": "Colombia"}, "url": URL + "/marketing/",
              "description": "Construcción de marcas personales desde cero con formatos de contenido que convierten audiencias en comunidades digitales."}]
    write("marketing/index.html", render("marketing", head=head("Marca personal y formatos de contenido para comunidades digitales | Brando Cantillo",
          "Construyo marcas personales desde cero con formatos de contenido que convierten audiencias en comunidades. Método, tipos de formatos y protección legal de tu contenido.",
          "/marketing/", image="/assets/img/brando-cantillo-marca-personal.jpg", ld=ld_mk)))

    # Listados
    def listing(path, title, h1, sub, items, current):
        filt = "".join(f'<a href="{href}"{" aria-current=\"page\"" if href == current else ""}>{name}</a>'
                       for href, name in [("/columnas/", "Todas")] + [(f"/columnas/{k}/", v["name"]) for k, v in CFG["categories"].items()])
        ld = [{"@type": "CollectionPage", "name": title, "url": URL + path, "isPartOf": {"@id": URL + "/#web"}},
              {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": URL + p["url"]} for i, p in enumerate(items[:30])]}]
        write(path + "index.html", render("list", head=head(title, sub, path, ld=ld), h1=h1, sub=esc(sub), filters=filt, rows=post_rows(items), year=datetime.now().year))
    listing("/columnas/", "Columnas de Brando Cantillo sobre comunicación política e IA", "Columnas<b>.</b>",
            "Una columna diaria sobre cómo se comunica el poder en el mundo, qué funciona en Colombia y cómo usar la IA para emprender.", posts, "/columnas/")
    for k, v in CFG["categories"].items():
        listing(f"/columnas/{k}/", f'{v["name"]} | Columnas de Brando Cantillo', v["name"], v["description"],
                [p for p in posts if p["category"] == k], f"/columnas/{k}/")

    # Artículos
    for p in posts:
        cat = CFG["categories"].get(p["category"], {"name": ""})
        related = [r for r in posts if r is not p and r["category"] == p["category"]][:3] or [r for r in posts if r is not p][:3]
        ld = [{"@type": "BlogPosting", "@id": URL + p["url"] + "#articulo", "headline": p["title"][:110], "description": p["description"],
               "datePublished": p["date"], "dateModified": p["updated"], "inLanguage": CFG["lang"], "wordCount": p["words"],
               "keywords": ", ".join(p.get("keywords", [])), "articleSection": cat["name"],
               "image": URL + p.get("image", "/assets/img/og-brando-cantillo.jpg"), "author": {"@id": URL + "/#brando"},
               "publisher": {"@id": URL + "/#brando"}, "mainEntityOfPage": URL + p["url"],
               "citation": [{"@type": "CreativeWork", "name": s["title"], "url": s["url"]} for s in p.get("sources", [])][:15],
               "speakable": {"@type": "SpeakableSpecification", "cssSelector": [".article-head h1", ".article-head .dek"]}},
              {"@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Inicio", "item": URL + "/"},
                  {"@type": "ListItem", "position": 2, "name": cat["name"], "item": f'{URL}/columnas/{p["category"]}/'},
                  {"@type": "ListItem", "position": 3, "name": p["title"], "item": URL + p["url"]}]}]
        faq_html = ""
        if p.get("faq"):
            ld.append({"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in p["faq"]]})
            faq_html = '<section class="faq" aria-labelledby="faq-t"><h2 id="faq-t">Preguntas frecuentes</h2>' + "".join(
                f"<details><summary>{esc(f['q'])}</summary><p>{esc(f['a'])}</p></details>" for f in p["faq"]) + "</section>"
        src_html = ""
        if p.get("sources"):
            src_html = '<div class="sources"><p><strong>Fuentes</strong></p><ol>' + "".join(
                f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener nofollow">{esc(s["title"])}</a></li>' for s in p["sources"]) + "</ol></div>"
        share_url = URL + p["url"]
        from urllib.parse import quote
        share = (f'<div class="share" aria-label="Compartir"><a href="https://x.com/intent/post?text={quote(p["title"])}&url={quote(share_url)}" target="_blank" rel="noopener">Compartir en X</a>'
                 f'<a href="https://wa.me/?text={quote(p["title"] + " " + share_url)}" target="_blank" rel="noopener">Enviar por WhatsApp</a>'
                 f'<a href="https://www.linkedin.com/sharing/share-offsite/?url={quote(share_url)}" target="_blank" rel="noopener">Compartir en LinkedIn</a></div>')
        toc = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in p["toc"])
        extra = (f'<meta property="article:published_time" content="{p["date"]}"><meta property="article:modified_time" content="{p["updated"]}">'
                 f'<meta property="article:section" content="{esc(cat["name"])}">' + "".join(f'<meta property="article:tag" content="{esc(k)}">' for k in p.get("keywords", [])))
        write(p["url"] + "index.html", render("post", head=head(p.get("seo_title") or p["title"] + " | Brando Cantillo", p["description"], p["url"], p.get("image"), "article", ld, extra),
              title=esc(p["title"]), dek=esc(p.get("dek", p["description"])), date_iso=p["date"][:10], date=fecha(p["date"]), minutes=p["minutes"],
              cat_name=esc(cat["name"]), cat_url=f'/columnas/{p["category"]}/', toc=toc, body=p["html"], faq=faq_html, sources=src_html, share=share,
              related=post_rows(related), year=datetime.now().year))

    # 404
    write("404.html", render("list", head=head("Página no encontrada | Brando Cantillo", "Esta página no existe.", "/404.html"), h1="Esta página no existe",
          sub="Puede que el enlace haya cambiado. Estas son las columnas más recientes.", filters='<a href="/">Ir al inicio</a>', rows=post_rows(posts, 5), year=datetime.now().year)
          .replace('<meta name="robots" content="index,follow,max-image-preview:large">', '<meta name="robots" content="noindex">'))

    # SEO técnico
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    urls = [("/", now, "1.0"), ("/marketing/", now, "0.9"), ("/columnas/", posts[0]["updated"] if posts else now, "0.9")] + \
           [(f"/columnas/{k}/", now, "0.7") for k in CFG["categories"]] + [(p["url"], p["updated"], "0.8") for p in posts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "\n".join(f"  <url><loc>{URL}{u}</loc><lastmod>{d}</lastmod><priority>{pr}</priority></url>" for u, d, pr in urls) + "\n</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /404.html\n\nSitemap: {URL}/sitemap.xml\nSitemap: {URL}/news-sitemap.xml\n")
    # Sitemap de Google News: columnas de las últimas 48 horas
    from datetime import timedelta
    limite = datetime.now(timezone.utc) - timedelta(hours=48)
    recientes = [p for p in posts if datetime.fromisoformat(p["date"]).astimezone(timezone.utc) >= limite]
    write("news-sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' +
          "\n".join(f'  <url><loc>{URL}{p["url"]}</loc><news:news><news:publication><news:name>{esc(CFG["name"])}</news:name><news:language>es</news:language></news:publication>'
                    f'<news:publication_date>{p["date"]}</news:publication_date><news:title>{esc(p["title"])}</news:title></news:news></url>' for p in recientes) + "\n</urlset>\n")
    if CFG.get("indexnow_key"): write(f'{CFG["indexnow_key"]}.txt', CFG["indexnow_key"])
    items = "".join(f"<item><title>{esc(p['title'])}</title><link>{URL}{p['url']}</link><guid>{URL}{p['url']}</guid>"
                    f"<pubDate>{format_datetime(datetime.fromisoformat(p['date']).replace(tzinfo=datetime.fromisoformat(p['date']).tzinfo or timezone.utc))}</pubDate>"
                    f"<category>{esc(CFG['categories'].get(p['category'],{}).get('name',''))}</category><description>{esc(p['description'])}</description></item>" for p in posts[:30])
    write("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Columnas de {esc(CFG["name"])}</title>'
          f'<link>{URL}/columnas/</link><atom:link href="{URL}/feed.xml" rel="self" type="application/rss+xml"/><description>{esc(CFG["description"])}</description><language>es-co</language>{items}</channel></rss>')
    write("posts.json", json.dumps([{k: p[k] for k in ("title", "slug", "url", "date", "category", "description", "keywords") if k in p} for p in posts], ensure_ascii=False, indent=1))
    write("llms.txt", f"# {CFG['name']}\n\n> {CFG['short_bio']}\n\n## Páginas\n- [Inicio]({URL}/): quién es y qué servicios ofrece\n- [Marketing]({URL}/marketing/): marca personal y formatos de contenido para comunidades\n- [Columnas]({URL}/columnas/): archivo completo\n\n## Columnas recientes\n" +
          "\n".join(f"- [{p['title']}]({URL}{p['url']}): {p['description']}" for p in posts[:40]) + "\n")
    print(f"✅ Sitio generado en {OUT} — {len(posts)} columnas")
    return posts

if __name__ == "__main__":
    build()
