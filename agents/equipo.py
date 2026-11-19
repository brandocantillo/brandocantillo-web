"""El equipo editorial. Cada función es un agente con un solo trabajo.

  Curador (Haiku)        → propone temas a partir del Radar
  Investigador (Sonnet)  → busca en la web y arma un dossier con fuentes
  Estratega SEO (Haiku)  → palabra clave, intención, estructura, metadatos, FAQ, enlaces internos
  Columnista (Sonnet)    → escribe la columna con la voz de Brando
  Editor (Haiku)         → revisa muletillas de IA, ritmo, datos sin fuente y longitud
  Columnista (Sonnet)    → corrige solo si el editor encontró problemas
  Distribuidor (Haiku)   → hilo para X, post de LinkedIn y texto para WhatsApp
  Relacionista (Haiku)   → pitches a periodistas, columna invitada y artículo LinkedIn para ganar enlaces de medios grandes
  Guionista (Sonnet)     → guion de 60-90 s para grabar el video de la columna (llega al bot de videos)
  Cazador de virales (Sonnet + web) → cada mañana, 5 temas de actualidad para VIDEO que pueden explotar
"""
import json, re
from datetime import datetime
from zoneinfo import ZoneInfo
from .core import CFG, SITE, VOZ, ROOT, claude, as_json, log

HOY = lambda: datetime.now(ZoneInfo(CFG["zona_horaria"]))
FECHA = lambda: HOY().strftime("%d/%m/%Y")

def _historial():
    p = ROOT / "public/posts.json"
    if not p.exists():
        posts = []
        for f in sorted((ROOT / "content/posts").glob("*.md")):
            m = re.search(r'"title":\s*"(.*?)"', f.read_text(encoding="utf-8"))
            s = re.search(r'"slug":\s*"(.*?)"', f.read_text(encoding="utf-8"))
            if m and s: posts.append({"title": m.group(1), "url": f"/columnas/{s.group(1)}/"})
        return posts
    return json.loads(p.read_text(encoding="utf-8"))

# ------------------------------------------------------------------ 2. Curador
def _mezcla():
    """Cuántas columnas faltan esta semana en cada clúster (para equilibrar el posicionamiento)."""
    from datetime import timedelta
    hace7 = (HOY() - timedelta(days=7)).date().isoformat()
    recientes = [p for p in _historial_completo() if p.get("date", "")[:10] >= hace7]
    meta = {k: v for k, v in CFG.get("mezcla_semanal", {}).items() if not k.startswith("_")}
    return {k: max(0, v - sum(1 for p in recientes if p.get("category") == k)) for k, v in meta.items()}

def _historial_completo():
    out = []
    for f in sorted((ROOT / "content/posts").glob("*.md")):
        m = re.match(r"^---json\s*\n(.*?)\n---", f.read_text(encoding="utf-8"), re.S)
        if m:
            try: out.append(json.loads(m.group(1)))
            except Exception: pass
    return out

def curador(noticias, n_pol=None, n_ia=None, pista="", solo=None):
    total = (CFG["temas_politica_por_dia"] if n_pol is None else n_pol) + (CFG["temas_ia_por_dia"] if n_ia is None else n_ia)
    ya = [p["title"] for p in _historial()][:60]
    compact = {g: [f'- {x["titulo"]} ({x["url"]})' for x in v[:30]] for g, v in noticias.items()}
    bloques = "\n".join(f"{g.upper()}:\n" + "\n".join(v) for g, v in compact.items())
    cats = {k: v["name"] for k, v in SITE["categories"].items()}
    faltan = _mezcla()
    kw = CFG.get("keywords_objetivo", [])
    fase = len(_historial_completo()) < CFG.get("fase_inicial", {}).get("columnas", 0)
    regla_kw = (f"- FASE INICIAL: al menos 2 de los temas deben atacar directamente estas búsquedas objetivo o sus variantes long tail: {kw}." if fase
                else f"- Cuando encaje, conecta los temas con las búsquedas objetivo: {kw}.")
    prompt = f"""Hoy es {FECHA()}. Eres el editor jefe y estratega SEO del blog de Brando Cantillo ({SITE['url']}).
Objetivo del blog: posicionar a Brando en Google como referente nacional en MARKETING POLÍTICO y COMUNICACIÓN POLÍTICA en Colombia, además de marca personal y IA para emprendedores.

NOTICIAS Y TENDENCIAS DE HOY:
{bloques}

CLÚSTERES (categoria → nombre): {json.dumps(cats, ensure_ascii=False)}
COLUMNAS QUE FALTAN ESTA SEMANA POR CLÚSTER (prioriza los que más faltan): {json.dumps(faltan)}
COLUMNAS YA PUBLICADAS (no repetir ángulo): {json.dumps(ya, ensure_ascii=False)}
{('SOLO PROPÓN TEMAS DE: ' + solo) if solo else ''}
{('INDICACIÓN DE BRANDO: ' + pista) if pista else ''}

Propón {total} temas. Reglas:
- Mezcla dos tipos: (a) NEWSJACKING: un hecho de hoy en un gobierno, campaña, marca o creador (de Colombia o del mundo) leído en clave de estrategia, para captar búsquedas de actualidad y Google Discover; (b) EVERGREEN: guías que la gente busca todo el año ("cómo hacer una campaña al concejo", "estrategia de redes para candidatos", "cómo crear una marca personal", etc.).
- Cada tema apunta a una palabra clave con búsquedas reales en Colombia y a una intención clara.
- Política: analiza estrategias de comunicación sin tomar partido.
- ENFOQUE: {CFG.get("enfoque_editorial", "")}
{regla_kw}
Responde SOLO JSON:
{{"temas":[{{"categoria":"una de {list(cats)}","tipo_seo":"newsjacking|evergreen","titulo":"titular atractivo, máx 90 caracteres","angulo":"la tesis en una frase","por_que_hoy":"qué noticia o búsqueda lo dispara","keyword":"palabra clave principal","fuentes":["url1","url2"]}}]}}"""
    txt, _ = claude(prompt, model="rapido", max_tokens=3000)
    temas = as_json(txt)["temas"]
    for t in temas:
        if t.get("categoria") not in SITE["categories"]: t["categoria"] = "comunicacion-politica"
    return temas

# ------------------------------------------------------------------ 3. Investigador
def investigador(tema):
    prompt = f"""Hoy es {FECHA()}. Investiga para una columna de Brando Cantillo.
TEMA: {tema['titulo']}
TESIS: {tema.get('angulo','')}
CLÚSTER: {SITE['categories'][tema['categoria']]['name']} · TIPO SEO: {tema.get('tipo_seo','')}
PISTAS: {', '.join(tema.get('fuentes', []))}

Busca en la web y entrega un DOSSIER en español. Prioriza medios grandes y reconocidos, porque la columna los va a citar y enlazar (El Tiempo, Semana, El Espectador, La Silla Vacía, El Heraldo, El Pilón, Caracol, RCN, Infobae, BBC Mundo, El País, CNN en Español, Reuters, AP, Bloomberg, The New York Times, Forbes, Harvard Business Review, Think with Google, Meta, informes académicos o encuestas oficiales).
Incluye al menos {CFG['citas_externas_minimas'] + 2} datos citables, cada uno con: medio, fecha, dato y URL exacta.
1. Hechos verificados del caso (qué pasó, quién, cuándo, cifras), cada uno con su fuente (medio + URL).
2. Qué hicieron en términos de comunicación: mensaje, canal, vocero, timing, formato. Citas textuales cortas si existen, con fuente.
3. Contexto colombiano relevante y verificado (normas, calendario electoral, casos locales similares) con fuente.
4. {"Herramientas concretas, precios actuales y pasos de uso, con fuente" if tema['categoria']=='ia-para-emprendedores' else "Casos comparables (otros países, otras campañas, otros creadores) y datos de estudios o encuestas, con fuente"}.
5. Datos que NO pudiste verificar (para que el columnista no los use).
Sé preciso. Prioriza fuentes primarias y medios reconocidos. No escribas la columna."""
    dossier, fuentes = claude(prompt, model="escritor", max_tokens=4000, web_search=CFG["busquedas_max_por_columna"])
    log(f"Investigador: dossier {len(dossier)} caracteres, {len(fuentes)} fuentes")
    return dossier, fuentes

# ------------------------------------------------------------------ 4. Estratega SEO
def estratega_seo(tema, dossier):
    internos = [f'{p["title"]} → {p["url"]}' for p in _historial()[:40]]
    prompt = f"""Eres estratega SEO para el blog de Brando Cantillo ({SITE['url']}), en español de Colombia.
TEMA: {tema['titulo']} | KEYWORD SUGERIDA: {tema.get('keyword','')} | CLÚSTER: {SITE['categories'][tema['categoria']]['name']} | TIPO: {tema.get('tipo_seo','')}
PÁGINAS PILAR DE ESTE CLÚSTER (enlázalas): {json.dumps(CFG.get('paginas_pilar', {}).get(tema['categoria'], []))}
OBJETIVO: posicionar a Brando Cantillo como referente en marketing y comunicación política en Colombia.
BÚSQUEDAS OBJETIVO DEL SITIO: {CFG.get('keywords_objetivo', [])}. Si el tema se relaciona, usa una como keyword principal o secundaria, e incluye un enlace interno a "/" con una de ellas como ancla (ej. "estratega político en Colombia").
DOSSIER (resumen):
{dossier[:5000]}
COLUMNAS EXISTENTES PARA ENLAZAR: {json.dumps(internos, ensure_ascii=False)}

Diseña el plan SEO. Responde SOLO JSON:
{{"keyword":"principal (lo que la gente busca en Google Colombia)",
 "secundarias":["4-6 variaciones y long tail"],
 "intencion":"informativa|comercial|navegacional",
 "titulo":"H1 humano y atractivo, máx 95 caracteres, con la keyword natural",
 "seo_title":"título para Google, máx 60 caracteres, keyword al inicio",
 "description":"meta description 140-155 caracteres, con la keyword y un motivo para hacer clic",
 "dek":"subtítulo de 1-2 frases con la voz de Brando",
 "slug":"slug-corto-con-keyword",
 "h2":["5-7 subtítulos H2 que respondan a lo que se busca; al menos 2 en forma de pregunta real"],
 "faq":[{{"q":"pregunta real de búsqueda","a":"respuesta de 2-3 frases"}}],
 "enlaces_internos":[{{"texto":"ancla descriptiva con palabra clave","url":"/columnas/... o página pilar"}}],
 "frase_citable":"una frase de Brando, de máx 25 palabras, que un periodista pueda citar textualmente",
 "entidades":["personas, instituciones, lugares y conceptos que deben aparecer para que Google entienda el tema"]}}
Máximo 4 preguntas FAQ (las que la gente busca en "Otras preguntas de los usuarios"). Entre {CFG['enlaces_internos_minimos']} y 5 enlaces internos, solo de la lista de columnas existentes o de las páginas pilar.
Títulos: el seo_title debe ganar el clic (número, año, "cómo", "guía" o contraste), sin clickbait."""
    txt, _ = claude(prompt, model="rapido", max_tokens=2000)
    return as_json(txt)

# ------------------------------------------------------------------ 5. Columnista
SISTEMA_COLUMNISTA = f"""Eres Brando Cantillo escribiendo tu columna diaria. Escribes en español de Colombia, en primera persona.
Esta es tu guía de voz; síguela al pie de la letra:

{VOZ}

Reglas de oro:
- Solo usas hechos, cifras y citas que estén en el dossier, y enlazas la fuente en el texto con formato markdown [texto](url) la primera vez que usas un dato.
- Las experiencias personales solo salen de la NOTA DE BRANDO. Si no hay nota, no inventas anécdotas: hablas desde el análisis.
- Escribes como una persona, no como un informe: ritmo variable, opinión clara, ejemplos colombianos concretos.
- Formato markdown: párrafos y subtítulos con '## '. Sin H1, sin título al inicio, sin emojis, sin tablas. Listas solo si de verdad son pasos."""

def columnista(tema, dossier, seo, nota=""):
    prompt = f"""Escribe la columna completa.
TÍTULO (no lo repitas en el texto): {seo['titulo']}
CLÚSTER: {SITE['categories'][tema['categoria']]['name']}
TESIS: {tema.get('angulo','')}
KEYWORD PRINCIPAL: {seo['keyword']} (úsala en el primer párrafo y 3-5 veces más de forma natural; usa también: {', '.join(seo.get('secundarias', []))})
SUBTÍTULOS H2 A USAR (puedes ajustar la redacción para que suenen a ti): {json.dumps(seo['h2'], ensure_ascii=False)}
ENTIDADES QUE DEBEN APARECER: {', '.join(seo.get('entidades', []))}
ENLACES INTERNOS (inclúyelos TODOS de forma natural, con el ancla indicada): {json.dumps(seo.get('enlaces_internos', []), ensure_ascii=False)}
FRASE CITABLE (inclúyela tal cual, en un párrafo propio o como cita destacada con '> '): {seo.get('frase_citable','')}
CITAS A MEDIOS: cita y enlaza al menos {CFG['citas_externas_minimas']} medios o estudios distintos del dossier, con atribución natural: "como publicó [El Tiempo](url)", "según un análisis de [La Silla Vacía](url)". Nunca copies párrafos de esos medios: resume con tus palabras y aporta tu lectura estratégica.
NOTA DE BRANDO (su opinión o experiencia, úsala como eje si existe): {nota or '— sin nota —'}

DOSSIER DE INVESTIGACIÓN:
{dossier}

Extensión: alrededor de {CFG['palabras_objetivo']} palabras (mínimo {CFG['palabras_minimas']}). Entrega solo el cuerpo en markdown."""
    txt, _ = claude(prompt, system=SISTEMA_COLUMNISTA, model="escritor", max_tokens=7000, temperature=0.9)
    return txt.strip()

# ------------------------------------------------------------------ 6. Editor
def editor(cuerpo, dossier):
    palabras = len(re.findall(r"\w+", cuerpo))
    prompt = f"""Eres el editor de estilo y verificador de Brando Cantillo. Revisa esta columna ({palabras} palabras).
GUÍA DE VOZ:
{VOZ}
DOSSIER (lo único verificado):
{dossier[:7000]}
COLUMNA:
{cuerpo}

Busca: (a) muletillas o fórmulas típicas de texto generado por IA y frases prohibidas por la guía; (b) estructuras repetidas (todas las secciones abren igual, tríadas, cierres moralizantes); (c) datos, cifras, citas o anécdotas que NO estén en el dossier ni en una nota de Brando; (d) párrafos de relleno; (e) si tiene menos de {CFG['palabras_minimas']} palabras.
Responde SOLO JSON: {{"aprobada": true|false, "problemas": ["instrucción concreta de corrección, citando el fragmento"], "puntaje_voz": 1-10}}
Aprueba solo si no hay datos sin respaldo y el puntaje de voz es 8 o más."""
    txt, _ = claude(prompt, model="rapido", max_tokens=1500)
    r = as_json(txt)
    links = re.findall(r"\]\((\S+?)\)", cuerpo)
    externos = {re.sub(r"^https?://(www\.)?", "", u).split("/")[0] for u in links if u.startswith("http") and SITE["url"].split("//")[1] not in u}
    internos = [u for u in links if u.startswith("/") or SITE["url"].split("//")[1] in u]
    if len(externos) < CFG["citas_externas_minimas"]:
        r["aprobada"] = False; r.setdefault("problemas", []).append(f"Cita y enlaza al menos {CFG['citas_externas_minimas']} medios distintos del dossier (hoy hay {len(externos)}).")
    if len(internos) < CFG["enlaces_internos_minimos"]:
        r["aprobada"] = False; r.setdefault("problemas", []).append(f"Incluye al menos {CFG['enlaces_internos_minimos']} enlaces internos a columnas o páginas pilar (hoy hay {len(internos)}).")
    if palabras < CFG["palabras_minimas"]:
        r["aprobada"] = False; r.setdefault("problemas", []).append(f"Amplía a {CFG['palabras_objetivo']} palabras con análisis y ejemplos aplicados a Colombia (hoy tiene {palabras}).")
    return r

def revisar(cuerpo, instrucciones, dossier=""):
    prompt = f"""Corrige tu columna siguiendo estas instrucciones. Mantén lo que está bien; cambia solo lo necesario.
INSTRUCCIONES:
{chr(10).join('- ' + i for i in instrucciones)}
{('DOSSIER (para verificar datos):' + chr(10) + dossier[:6000]) if dossier else ''}
COLUMNA ACTUAL:
{cuerpo}
Entrega la columna completa corregida, solo el cuerpo en markdown."""
    txt, _ = claude(prompt, system=SISTEMA_COLUMNISTA, model="escritor", max_tokens=7000, temperature=0.8)
    return txt.strip()

# ------------------------------------------------------------------ 7. Distribuidor
def distribuidor(meta, cuerpo):
    url = f"{SITE['url']}/columnas/{meta['slug']}/"
    prompt = f"""Con la voz de Brando Cantillo (directo, opinión clara, sin emojis en exceso, sin hashtags de relleno), crea piezas para difundir esta columna.
TÍTULO: {meta['title']}
URL: {url}
COLUMNA:
{cuerpo[:9000]}
Responde SOLO JSON:
{{"hilo_x":["5-7 posts de máx 270 caracteres; el primero engancha sin clickbait; el último lleva la URL"],
 "linkedin":"post de 120-200 palabras con saltos de línea y la URL al final",
 "whatsapp":"mensaje de 2-3 líneas para estados o listas de difusión, con la URL"}}"""
    txt, _ = claude(prompt, model="rapido", max_tokens=1800)
    return as_json(txt)

# ------------------------------------------------------------------ 8. Relacionista (PR digital → enlaces y tráfico desde medios grandes)
def relacionista(meta, cuerpo, frase=""):
    url = f"{SITE['url']}/columnas/{meta['slug']}/"
    medios = sorted({s["title"].split(" - ")[-1][:60] for s in meta.get("sources", [])})
    prompt = f"""Eres el jefe de relaciones públicas digitales de Brando Cantillo ({SITE['job_title']}).
Objetivo: que medios y sitios grandes lo citen como fuente experta y enlacen a su web, para ganar autoridad en Google y tráfico de referencia.
COLUMNA: {meta['title']} — {url}
FRASE CITABLE: {frase}
MEDIOS QUE LA COLUMNA CITA: {medios}
RESUMEN:
{cuerpo[:5000]}

Entrega SOLO JSON:
{{"pitch_periodistas":[{{"medio":"medio colombiano o latino al que encaja (nacional o regional)","seccion":"política, opinión, tecnología, negocios…","asunto":"asunto del correo, máx 80 caracteres","cuerpo":"correo breve (90-130 palabras) ofreciendo a Brando como fuente experta sobre el tema, con 2 datos o ideas de la columna y el enlace"}}],
 "columna_invitada":{{"medios_sugeridos":["3 medios o portales que publican columnas de invitados"],"titulo":"titular distinto al original","entrada":"primer párrafo nuevo (no duplicar el texto del blog) que remite a la columna completa"}},
 "linkedin_articulo":"introducción de 120-160 palabras para publicar como artículo en LinkedIn, que cierre con 'Publicado originalmente en' + URL",
 "respuesta_experta":"un párrafo de 60-80 palabras que Brando puede usar para responder solicitudes de periodistas o foros sobre este tema, con el enlace"}}
Máximo 3 pitches. Tono profesional, sin exagerar credenciales."""
    txt, _ = claude(prompt, model="rapido", max_tokens=2500)
    return as_json(txt)

# ------------------------------------------------------------------ 8b. Guionista (video corto a partir de la columna)
def guionista(meta, cuerpo):
    """Guion para grabar hablando a cámara. Está pensado para el editor de video:
    cada cifra dicha en voz alta se vuelve una pantalla animada, cada cita una tarjeta,
    cada enumeración una lista y la pregunta final la pantalla de cierre."""
    url = f"{SITE['url']}/columnas/{meta['slug']}/"
    prompt = f"""Convierte esta columna en un guion para un video vertical de 60 a 90 segundos (150-220 palabras habladas) que Brando Cantillo graba hablando a cámara.
TÍTULO: {meta['title']}
URL: {url}
COLUMNA:
{cuerpo[:9000]}

Reglas del guion:
- Primera frase: la idea más fuerte de la columna, afirmación directa, sin saludo ni "hoy les quiero hablar de".
- Di las cifras en voz alta y completas ("el 70 %", "5 de cada 100"). Usa SOLO cifras que estén en la columna; no inventes ninguna.
- Si la columna cita a alguien, incluye una cita textual corta con atribución ("como dijo …: «…»").
- Si hay pasos o razones, enuméralas: "primero…, segundo…, tercero…".
- Frases cortas, para decir de corrido. Sin emojis, sin hashtags, sin acotaciones entre paréntesis.
- Cierra con una pregunta al público.
Responde SOLO JSON:
{{"titulo":"título del video, máx 60 caracteres",
 "gancho":"la primera frase, tal cual",
 "guion":"el texto completo a decir, en párrafos cortos separados por \\n\\n",
 "cifras":["cifras que se dicen, tal cual"],
 "nota_editor":"1-2 líneas para el director de edición: qué enfatizar en pantalla (cifra, cita, lista)",
 "pie":"pie de foto para redes, 2-4 líneas, con la URL al final"}}"""
    txt, _ = claude(prompt, system=VOZ, model="escritor", max_tokens=2500)
    return as_json(txt)

# ------------------------------------------------------------------ 9. Columna mensual exclusiva para medios regionales
def columna_regional(medio, tema=None, nota="", avisar=lambda m: None):
    """Columna de opinión inédita (no se publica en el blog) para el espacio mensual en un medio regional."""
    if not tema:
        from . import radar
        temas = curador(radar.noticias(), n_pol=2, n_ia=0, solo="marketing-politico o comunicacion-politica",
                        pista=f"Columna de opinión para {medio}: un tema del Cesar o del Caribe colombiano con mirada estratégica.")
        tema = temas[0]
    avisar(f"🔎 Investigando para {medio}: {tema['titulo']}")
    dossier, fuentes = investigador(tema)
    prompt = f"""Escribe una columna de opinión INÉDITA para el diario {medio}, firmada por Brando Cantillo ({SITE['job_title']}).
TEMA: {tema['titulo']} · TESIS: {tema.get('angulo','')}
NOTA DE BRANDO: {nota or '— sin nota —'}
Extensión: 700 a 850 palabras (formato habitual de columna en prensa). Título fuerte de máximo 12 palabras en la primera línea con '# '.
Sin enlaces (es para prensa); las fuentes se mencionan en el texto ("según El Tiempo…"). Cierre con una línea de firma:
"Brando Cantillo es {SITE['job_title'].lower()}. Más análisis en {SITE['url'].replace('https://','')}"
DOSSIER:
{dossier}"""
    texto, _ = claude(prompt, system=SISTEMA_COLUMNISTA, model="escritor", max_tokens=3000, temperature=0.85)
    return tema, texto.strip()

# ------------------------------------------------------------------ Orquestación
def escribir(tema, nota="", avisar=lambda m: None):
    avisar("🔎 Investigando…")
    dossier, fuentes = investigador(tema)
    avisar("🧭 Armando el plan SEO…")
    seo = estratega_seo(tema, dossier)
    avisar("✍️ Escribiendo la columna…")
    cuerpo = columnista(tema, dossier, seo, nota)
    for ronda in range(2):
        rev = editor(cuerpo, dossier)
        log(f"Editor ronda {ronda+1}: aprobada={rev.get('aprobada')} voz={rev.get('puntaje_voz')} problemas={len(rev.get('problemas', []))}")
        if rev.get("aprobada"): break
        avisar(f"🧹 El editor pidió {len(rev.get('problemas', []))} ajustes, corrigiendo…")
        cuerpo = revisar(cuerpo, rev["problemas"], dossier)
    usados = [f for f in fuentes if f["url"] in cuerpo] or fuentes[:6]
    meta = {"title": seo["titulo"], "seo_title": seo.get("seo_title", ""), "description": seo["description"], "dek": seo.get("dek", ""),
            "slug": seo["slug"], "date": HOY().replace(microsecond=0).isoformat(), "category": tema["categoria"],
            "seo_type": tema.get("tipo_seo", ""), "quote": seo.get("frase_citable", ""),
            "keywords": [seo["keyword"]] + seo.get("secundarias", []), "faq": seo.get("faq", []), "sources": usados}
    return meta, cuerpo, dossier


# ------------------------------------------------------------------ 10. Cazador de virales (videos)
def cazador_virales(material, ya=(), pista=""):
    """Elige temas de ACTUALIDAD para video con la fórmula del video del baneo de Instagram:
    algo que le está pasando a MUCHA gente hoy + Brando como el experto que lo explica y da la salida."""
    bloques = json.dumps(material, ensure_ascii=False)[:14000]
    prompt = f"""Hoy es {FECHA()}. Eres el productor de contenido de Brando Cantillo, estratega digital y político colombiano, abogado
especialista en derechos de autor y nuevas tecnologías, experto en IA, redes sociales y marca personal.

Su video más exitoso fue sobre el BANEO MASIVO DE CUENTAS DE INSTAGRAM: un tema que estaba afectando a miles de personas ESE día,
explicado por alguien que sabe, con la salida práctica ("qué hacer si te pasó"). Queremos repetir esa fórmula todos los días.

MATERIAL DE HOY (búsquedas en alza en Google y titulares de las últimas 24 h):
{bloques}

Primero usa la búsqueda web para confirmar qué está explotando HOY en Colombia y Latinoamérica en redes (tendencias de X, TikTok,
Instagram, YouTube) y qué dudas tiene la gente. Luego elige 5 temas que pasen este filtro:
1. MASIVO: le interesa o afecta a mucha gente fuera del nicho (usuarios de una app, consumidores, votantes, creadores, emprendedores).
   Prioriza: caídas o cambios de plataformas, bloqueos y baneos, estafas virales, nuevas funciones de IA que todos están probando,
   polémicas de influencers o marcas, videos de políticos que se volvieron virales, leyes o fallos que afectan lo que la gente publica.
2. PUENTE: Brando tiene autoridad real para explicarlo (redes y plataformas, IA, comunicación política, derechos de autor y tecnología, marca personal).
3. VENTANA: está pasando ahora; si se graba en 1-2 días todavía sirve.
4. SALIDA PRÁCTICA: el video le deja a la gente algo que hacer o entender.
Política: analiza la estrategia de comunicación, nunca tomes partido ni ataques a nadie. No inventes datos: solo lo que confirmaste.
Evita tragedias, muertes, víctimas y temas que expongan a personas privadas.
{('Temas ya propuestos o hechos (no repetir): ' + '; '.join(ya)) if ya else ''}
{('Indicación de Brando: ' + pista) if pista else ''}

Responde SOLO JSON:
{{"temas":[{{"tema":"de qué se trata, máx 80 caracteres",
 "por_que_ahora":"la evidencia de que está viral hoy (volumen de búsquedas, tendencia, noticia)",
 "alcance":"alto|medio","urgencia":"graba hoy|graba mañana|esta semana",
 "angulo":"la lectura de Brando en una frase (lo que nadie más está diciendo)",
 "gancho":"primera frase del video, directa, sin saludo (máx 15 palabras)",
 "guion":"guion de 45-70 s (110-170 palabras) para decir a cámara, en párrafos cortos separados por \\n\\n; cierra con una pregunta",
 "portada":"TITULAR DE PORTADA en máx 7 palabras que se lea como una frase completa",
 "fuentes":["url"]}}]}}"""
    txt, fuentes = claude(prompt, system=VOZ, model="escritor", max_tokens=5000, web_search=5)
    temas = as_json(txt)["temas"]
    return temas, fuentes
