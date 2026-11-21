"""Bot de Telegram: tú apruebas, los agentes trabajan.

  python -m agents.bot propose   → el Radar + Curador te envían los temas del día
  python -m agents.bot poll      → revisa tus respuestas una vez (para GitHub Actions)
  python -m agents.bot loop      → bot siempre encendido, respuesta inmediata (para tu PC o un servidor)
"""
import json, os, subprocess, sys, time, traceback
from . import radar, equipo
from .core import ROOT, DATA, SITE, CFG, COSTO, tg, send, send_document, send_video_bot, env, esc, load_state, save_state, chat_id, log

AYUDA = ("<b>Comandos</b>\n/temas — proponer temas ahora\n/virales — temas de actualidad para VIDEO (llegan al bot de videos)\n/tema &lt;texto&gt; — escribir sobre tu propio tema\n"
         "/marketing — solo marketing político\n/comunicacion — solo comunicación política\n/marca — solo marca personal y comunidades\n"
         "/ia — solo IA para emprendedores\n/mensual — columna inédita para tu espacio en medios regionales\n/estado — qué está pasando\n/cancelar — descartar lo pendiente")
SOLO = {"/marketing": "marketing-politico", "/comunicacion": "comunicacion-politica", "/marca": "marca-personal", "/ia": "ia-para-emprendedores"}

def _costo():
    return f"Tokens: {COSTO['in']:,} entrada / {COSTO['out']:,} salida · búsquedas web: {COSTO['searches']}"

# ------------------------------------------------------------------ Propuestas
ICONOS = {"marketing-politico": "🗳", "comunicacion-politica": "🏛", "marca-personal": "📣", "ia-para-emprendedores": "🤖"}

def propose(state, pista="", solo=None):
    send("📡 Revisando noticias, tendencias y búsquedas de hoy…")
    try:
        temas = equipo.curador(radar.noticias(), pista=pista, solo=solo)
    except Exception as e:
        send(f"⚠️ No pude preparar los temas esta vez ({esc(str(e)[:300])}). Lo intento de nuevo en el próximo turno; también puedes escribir /temas.")
        raise
    state["proposal"] = {"temas": temas, "ts": time.time()}
    lineas, botones = ["<b>Temas propuestos para hoy</b>\n"], []
    for i, t in enumerate(temas):
        icono = ICONOS.get(t["categoria"], "📝")
        cat = SITE["categories"][t["categoria"]]["name"]
        lineas.append(f"{icono} <b>{i+1}. {esc(t['titulo'])}</b>\n{esc(cat)} · {esc(t.get('tipo_seo',''))} · <code>{esc(t.get('keyword',''))}</code>\n<i>{esc(t.get('angulo',''))}</i>\nPor qué hoy: {esc(t.get('por_que_hoy',''))}\n")
        botones.append([(f"✅ Escribir el {i+1}", f"t:{i}")])
    botones.append([("🔄 Otros temas", "mas"), ("✏️ Propongo yo", "propio")])
    lineas.append("Elige uno. Si quieres, después me dices tu opinión y la columna gira alrededor de ella.")
    send("\n".join(lineas), botones)

# ------------------------------------------------------------------ Escritura
def correr_pipeline(state):
    p = state["pending"]
    p["stage"] = "writing"; save_state(state)
    try:
        meta, cuerpo, dossier = equipo.escribir(p["topic"], p.get("note", ""), avisar=lambda m: send(m))
    except Exception as e:
        traceback.print_exc(); p["stage"] = "error"; save_state(state)
        send(f"⚠️ Falló la escritura: {esc(str(e)[:600])}\nPulsa para reintentar.", [[("🔁 Reintentar", "retry"), ("🗑 Descartar", "descartar")]]); return
    p.update({"meta": meta, "body": cuerpo, "dossier": dossier[:12000], "stage": "review"})
    save_state(state); mostrar_borrador(p)

def _archivo(meta, cuerpo):
    return "---json\n" + json.dumps(meta, ensure_ascii=False, indent=2) + "\n---\n" + cuerpo.strip() + "\n"

def mostrar_borrador(p):
    meta, cuerpo = p["meta"], p["body"]
    import re
    palabras = len(re.findall(r"\w+", cuerpo))
    borr = DATA / "borradores"; borr.mkdir(exist_ok=True)
    f = borr / f"{meta['slug']}.md"; f.write_text(_archivo(meta, cuerpo), encoding="utf-8")
    send_document(f, caption=f"Borrador completo · {palabras} palabras")
    inicio = "\n\n".join(cuerpo.split("\n\n")[:3])
    send(f"<b>{esc(meta['title'])}</b>\n<i>{esc(meta['description'])}</i>\n\nKeyword: <code>{esc(meta['keywords'][0])}</code> · {palabras} palabras · "
         f"{len(meta.get('sources', []))} fuentes\n\n{esc(inicio[:1500])}…\n\n{_costo()}",
         [[("🚀 Publicar", "pub")], [("✏️ Pedir cambios", "cambios"), ("🗑 Descartar", "descartar")]])

def publicar(state):
    p = state["pending"]; meta = p["meta"]
    dest = ROOT / "content/posts" / f"{meta['date'][:10]}-{meta['slug']}.md"
    dest.write_text(_archivo(meta, p["body"]), encoding="utf-8")
    state.setdefault("history", []).insert(0, meta["title"]); state["history"] = state["history"][:100]
    state["pending"] = None; state["published"] = True; save_state(state)
    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, cwd=ROOT)
    if os.environ.get("GIT_PUSH") == "1":  # modo PC/servidor; en GitHub Actions el workflow hace el commit
        subprocess.run(["git", "add", "content", "data/state.json"], cwd=ROOT)
        subprocess.run(["git", "commit", "-m", f"Columna: {meta['title']}"], cwd=ROOT)
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=ROOT)
        subprocess.run(["git", "push"], cwd=ROOT)
    url = f"{SITE['url']}/columnas/{meta['slug']}/"
    send(f"✅ Publicada. En 1-3 minutos estará en línea:\n{url}\n\nPreparando piezas para redes…")
    guion_video(meta, p["body"])
    try:
        d = equipo.distribuidor(meta, p["body"])
        hilo = "\n\n".join(f"{i+1}/ {esc(t)}" for i, t in enumerate(d.get("hilo_x", [])))
        send(f"<b>Hilo para X</b>\n\n{hilo}")
        send(f"<b>LinkedIn</b>\n\n{esc(d.get('linkedin',''))}")
        send(f"<b>WhatsApp</b>\n\n{esc(d.get('whatsapp',''))}")
    except Exception as e:
        log("Distribuidor falló:", e)
    try:
        pr = equipo.relacionista(meta, p["body"], meta.get("quote", ""))
        send("<b>📰 Kit de relaciones públicas</b>\nObjetivo: que medios grandes te citen y enlacen tu web. Revisa, ajusta y envía tú mismo.")
        for x in pr.get("pitch_periodistas", []):
            send(f"<b>Para: {esc(x.get('medio',''))}</b> ({esc(x.get('seccion',''))})\nAsunto: {esc(x.get('asunto',''))}\n\n{esc(x.get('cuerpo',''))}")
        ci = pr.get("columna_invitada", {})
        send(f"<b>Columna invitada</b>\nMedios: {esc(', '.join(ci.get('medios_sugeridos', [])))}\nTítulo: {esc(ci.get('titulo',''))}\n\n{esc(ci.get('entrada',''))}")
        send(f"<b>Artículo de LinkedIn</b>\n\n{esc(pr.get('linkedin_articulo',''))}")
        send(f"<b>Respuesta experta (foros y periodistas)</b>\n\n{esc(pr.get('respuesta_experta',''))}")
    except Exception as e:
        log("Relacionista falló:", e)
    indexnow(url)
    if state.get("proposal"):
        send("¿Quieres escribir otro de los temas propuestos hoy? Usa los botones del mensaje de temas o /temas.")

def guion_video(meta, cuerpo):
    """Guion para grabar el video de la columna. Llega al bot de videos con un botón que se lo pasa al editor."""
    try:
        g = equipo.guionista(meta, cuerpo)
    except Exception as e:
        log("Guionista falló:", e); send(f"⚠️ No pude preparar el guion del video ({esc(str(e)[:200])})."); return
    cifras = ", ".join(g.get("cifras", [])) or "—"
    texto = (f"🎬 <b>Guion para video</b> · columna «{esc(meta['title'])}»\n\n"
             f"<b>{esc(g.get('titulo', ''))}</b>\n\n{esc(g.get('guion', ''))}\n\n"
             f"Cifras que dices: {esc(cifras)}\n"
             f"Nota para el editor: {esc(g.get('nota_editor', ''))}\n\n"
             f"Pie sugerido:\n{esc(g.get('pie', ''))}")
    boton = [[("📌 Usar en mi próxima grabación", f"guion:{meta['slug'][:50]}")]]
    try:
        send_video_bot(texto, boton)
        if env("TELEGRAM_VIDEO_BOT_TOKEN", required=False):
            send("🎬 El guion para grabar el video de esta columna te llegó al bot de videos.")
    except Exception as e:
        log("Envío del guion falló:", e); send(texto)

def virales(state, pista=""):
    """Temas de actualidad para video. Llegan al bot de videos, cada uno con su gancho y guion listos para grabar."""
    from . import radar
    try:
        ya = [t["tema"] for t in state.get("virales", [])][-40:]
        temas, _ = equipo.cazador_virales(radar.virales(), ya=ya, pista=pista)
    except Exception as e:
        log("Cazador de virales falló:", e); send(f"⚠️ No pude preparar los temas virales ({esc(str(e)[:200])}). Prueba /virales más tarde."); return
    state["virales"] = (state.get("virales", []) + [{"tema": t["tema"], "fecha": time.strftime("%Y-%m-%d")} for t in temas])[-60:]
    save_state(state)
    destino = send_video_bot if env("TELEGRAM_VIDEO_BOT_TOKEN", required=False) else send
    destino(f"🔥 <b>Temas de actualidad para video</b> · {time.strftime('%d/%m')}\n3 de debate y 2 tips para tu audiencia. Graba primero los de «graba hoy».")
    for i, t in enumerate(temas, 1):
        fuentes = "\n".join(esc(u) for u in t.get("fuentes", [])[:2])
        etiqueta = "💡 TIP" if t.get("tipo") == "tip" else "⚔️ DEBATE"
        destino(f"{etiqueta}\n<b>{i}. {esc(t.get('tema', ''))}</b>\n"
                f"⏱ {esc(t.get('urgencia', ''))} · debate {esc(t.get('debate', ''))} · alcance {esc(t.get('alcance', ''))}\n"
                f"{'🚫' if t.get('tipo') == 'tip' else '⚔️'} {esc(t.get('bandos', ''))}\n"
                f"📈 {esc(t.get('por_que_ahora', ''))}\n"
                f"🎯 {esc(t.get('angulo', ''))}\n\n"
                f"<b>Gancho:</b> {esc(t.get('gancho', ''))}\n\n"
                f"<b>Guion:</b>\n{esc(t.get('guion', ''))}\n\n"
                f"<b>Portada:</b> {esc(t.get('portada', ''))}\n{fuentes}")
    if destino is send_video_bot:
        send("🔥 Te llegaron los temas virales del día al bot de videos.")

def mensual(state, medio=""):
    medios = CFG.get("medios_regionales", ["un medio regional"])
    for m in ([medio] if medio else medios):
        tema, texto = equipo.columna_regional(m, avisar=lambda x: send(x))
        import unicodedata
        nombre = unicodedata.normalize("NFKD", m).encode("ascii", "ignore").decode().lower().replace(" ", "-")
        f = DATA / "borradores" / f"columna-{nombre}-{time.strftime('%Y-%m')}.md"
        f.parent.mkdir(exist_ok=True); f.write_text(texto, encoding="utf-8")
        send_document(f, caption=f"Columna inédita para {m} · {len(texto.split())} palabras")
        send(f"<b>Columna mensual para {esc(m)}</b>\nEs inédita: no se publica en tu blog para respetar la exclusividad del medio. "
             f"Revísala, ajústala y envíala a tu editor. Cuando el medio la publique, compárteme el enlace con /tema para escribir una columna complementaria en tu web.")

def indexnow(url):
    """Avisa a Bing, Yandex y otros buscadores que hay una URL nueva (Google la descubre por el sitemap)."""
    key = SITE.get("indexnow_key")
    if not key or "CAMBIAR" in SITE["url"]: return
    try:
        from .core import http
        body = json.dumps({"host": SITE["url"].split("//")[1], "key": key, "keyLocation": f"{SITE['url']}/{key}.txt", "urlList": [url, SITE["url"] + "/columnas/", SITE["url"] + "/sitemap.xml"]}).encode()
        http("https://api.indexnow.org/indexnow", body, {"content-type": "application/json"}, timeout=20)
        log("IndexNow OK")
    except Exception as e:
        log("IndexNow falló:", e)

# ------------------------------------------------------------------ Manejo de mensajes
def elegir(state, tema):
    state["pending"] = {"topic": tema, "stage": "awaiting_note", "note": ""}
    save_state(state)
    send(f"Elegiste: <b>{esc(tema['titulo'])}</b>\n\n¿Qué opinas tú? Escríbeme tu postura, una anécdota o un dato que solo tú sabes "
         "(puede ser una nota de voz transcrita o un par de líneas). Eso es lo que hace que la columna suene a ti.",
         [[("✍️ Escribir sin nota", "nota:skip")]])

def on_callback(state, data):
    p = state.get("pending")
    if data.startswith("t:"):
        temas = (state.get("proposal") or {}).get("temas", [])
        i = int(data[2:])
        if i < len(temas): elegir(state, temas[i])
    elif data == "mas": propose(state, pista="Propón temas distintos a los anteriores: " + "; ".join(t["titulo"] for t in (state.get("proposal") or {}).get("temas", [])))
    elif data == "propio":
        state["pending"] = {"stage": "awaiting_topic"}; save_state(state); send("Escríbeme el tema y, si quieres, tu postura en el mismo mensaje.")
    elif data == "nota:skip" and p and p["stage"] == "awaiting_note": correr_pipeline(state)
    elif data == "retry" and p: correr_pipeline(state)
    elif data == "pub" and p and p["stage"] == "review": publicar(state)
    elif data == "cambios" and p and p["stage"] == "review":
        p["stage"] = "awaiting_changes"; save_state(state); send("Dime qué cambio quieres (tono, una idea, un dato, más corto, otro título…).")
    elif data == "descartar":
        state["pending"] = None; save_state(state); send("Descartado. Usa /temas cuando quieras más propuestas.")

def on_text(state, text):
    p = state.get("pending")
    t = text.strip()
    if t.startswith("/start") or t.startswith("/ayuda"): send(AYUDA); return
    if t.startswith("/temas"): propose(state); return
    if t.startswith("/virales"): send("🔥 Buscando lo que está explotando hoy…"); virales(state, t[8:].strip()); return
    if t.startswith("/mensual"): mensual(state, t[8:].strip()); return
    for cmd, cat in SOLO.items():
        if t.startswith(cmd): propose(state, solo=cat); return
    if t.startswith("/estado"):
        send(f"Pendiente: {esc((p or {}).get('stage', 'nada'))}\n{esc(((p or {}).get('topic') or {}).get('titulo', ''))}"); return
    if t.startswith("/cancelar"): state["pending"] = None; save_state(state); send("Listo, cancelado."); return
    if t.startswith("/tema"):
        t = t[5:].strip()
        if not t: send("Escribe el tema después del comando. Ej: /tema Cómo comunica un presidente en X y qué puede copiar un alcalde"); return
        p = None
    if p and p["stage"] == "awaiting_note":
        p["note"] = t; save_state(state); send("Anotado. Arranco."); correr_pipeline(state); return
    if p and p["stage"] == "awaiting_changes":
        send("Aplicando cambios…")
        p["body"] = equipo.revisar(p["body"], [t], p.get("dossier", ""))
        if any(w in t.lower() for w in ("título", "titulo")):
            p["meta"]["title"] = equipo.claude(f"Propón un solo título nuevo (máx 95 caracteres) para esta columna según esta indicación: {t}\n\n{p['body'][:3000]}\nResponde solo el título.")[0].strip('" \n')
        p["stage"] = "review"; save_state(state); mostrar_borrador(p); return
    if (p and p["stage"] == "awaiting_topic") or text.strip().startswith("/tema") or not p:
        low = f" {t.lower()} "
        cat = ("ia-para-emprendedores" if any(w in low for w in (" ia ", "inteligencia artificial", "emprend", "chatgpt", "claude", "pyme")) else
               "marca-personal" if any(w in low for w in ("influenc", "creador", "marca personal", "comunidad", "tiktok", "contenido")) else
               "marketing-politico" if any(w in low for w in ("campaña", "candidat", "elecci", "voto", "electoral", "marketing")) else "comunicacion-politica")
        elegir(state, {"categoria": cat, "tipo_seo": "", "titulo": t[:120], "angulo": t, "keyword": "", "fuentes": []}); return
    send("No entendí. " + AYUDA)

# ------------------------------------------------------------------ Bucle
def handle_updates(state, timeout=0):
    updates = tg("getUpdates", offset=state.get("offset", 0), timeout=timeout, allowed_updates=["message", "callback_query"])
    for u in updates:
        state["offset"] = u["update_id"] + 1; save_state(state)
        if "callback_query" in u:
            cq = u["callback_query"]
            try: tg("answerCallbackQuery", callback_query_id=cq["id"])
            except Exception: pass
            if str(cq["message"]["chat"]["id"]) != chat_id(): continue
            on_callback(state, cq.get("data", ""))
        elif "message" in u and "text" in u["message"]:
            if str(u["message"]["chat"]["id"]) != chat_id():
                log("Mensaje ignorado de chat no autorizado:", u["message"]["chat"]["id"]); continue
            on_text(state, u["message"]["text"])
    return len(updates)

def escuchar(state, minutos):
    """Escucha Telegram en vivo (long polling) durante unos minutos: respuestas casi instantáneas."""
    fin = time.time() + minutos * 60
    while time.time() < fin:
        try: handle_updates(state, timeout=int(max(1, min(50, fin - time.time()))))
        except Exception as e: log("Error escuchando:", e); time.sleep(5)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "poll"
    state = load_state(); state["published"] = False
    if cmd == "propose":
        propose(state)
        virales(state)  # van en el mismo turno: una tarea aparte la cancelaba GitHub por chocar con la escucha de Telegram
        escuchar(state, float(os.environ.get("MINUTOS_TRAS_PROPONER", 20)))
    elif cmd == "mensual": mensual(state)
    elif cmd == "virales": virales(state)
    elif cmd == "poll":
        escuchar(state, float(os.environ.get("MINUTOS_ESCUCHA", 9)))
    elif cmd == "loop":
        log("Bot encendido. Ctrl+C para detener.")
        while True:
            try: handle_updates(state, timeout=50)
            except Exception as e: log("Error:", e); time.sleep(5)
    elif cmd == "chatid":  # ayuda para el primer uso
        for u in tg("getUpdates"):
            m = u.get("message") or {}
            if m: print("TELEGRAM_CHAT_ID =", m["chat"]["id"], "·", m["chat"].get("first_name", ""))
        return
    save_state(state)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f: f.write(f"published={'true' if state.get('published') else 'false'}\n")
    log(_costo())

if __name__ == "__main__":
    main()
