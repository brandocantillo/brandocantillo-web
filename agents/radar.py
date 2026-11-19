"""Agente 1 — Radar: lee RSS gratis y arma la lista de noticias del día. No usa IA (costo 0)."""
import json, re, html
import xml.etree.ElementTree as ET
from .core import ROOT, http, log

def _text(el, tag):
    x = el.find(tag)
    return re.sub(r"<[^>]+>", " ", html.unescape(x.text or "")).strip() if x is not None and x.text else ""

def leer(feed, limite=15):
    try:
        root = ET.fromstring(http(feed, timeout=25))
    except Exception as e:
        log("RSS falló:", feed[:70], e); return []
    items = []
    for it in root.iter("item"):
        t = _text(it, "title")
        if not t: continue
        items.append({"titulo": t, "url": _text(it, "link"), "fecha": _text(it, "pubDate"),
                      "resumen": _text(it, "description")[:280]})
        if len(items) >= limite: break
    return items

def noticias():
    fuentes = json.loads((ROOT / "config/fuentes.json").read_text(encoding="utf-8"))
    out = {}
    for grupo, feeds in fuentes.items():
        if grupo.startswith("_"): continue
        vistos, lista = set(), []
        for f in feeds:
            for n in leer(f):
                k = re.sub(r"\W+", "", n["titulo"].lower())[:60]
                if k not in vistos: vistos.add(k); lista.append(n)
        out[grupo] = lista[:45]
        log(f"Radar {grupo}: {len(out[grupo])} noticias")
    return out


# ------------------------------------------------------------------ Radar viral (para videos)
NS_TRENDS = "{https://trends.google.com/trending/rss}"

def tendencias_google(geo="CO", limite=25):
    """Lo más buscado en Google en las últimas horas, con el volumen aproximado (ej. 20.000+)."""
    try:
        root = ET.fromstring(http(f"https://trends.google.com/trending/rss?geo={geo}", timeout=25))
    except Exception as e:
        log("Trends falló:", geo, e); return []
    out = []
    for it in root.iter("item"):
        t = _text(it, "title")
        vol = it.find(NS_TRENDS + "approx_traffic")
        notas = [_text(n, NS_TRENDS + "news_item_title") for n in it.findall(NS_TRENDS + "news_item")][:2]
        out.append({"busqueda": t, "volumen": (vol.text or "").strip() if vol is not None else "", "noticias": notas})
        if len(out) >= limite: break
    return out

VIRALES_FEEDS = {
    "portada_colombia": "https://news.google.com/rss?hl=es-419&gl=CO&ceid=CO:es-419",
    "plataformas": "https://news.google.com/rss/search?q=Instagram+OR+TikTok+OR+WhatsApp+OR+Facebook+OR+YouTube+OR+Meta+when:1d&hl=es-419&gl=CO&ceid=CO:es-419",
    "ia": "https://news.google.com/rss/search?q=inteligencia+artificial+OR+ChatGPT+OR+Gemini+OR+Claude+when:1d&hl=es-419&gl=CO&ceid=CO:es-419",
    "creadores": "https://news.google.com/rss/search?q=influencer+OR+streamer+OR+creador+de+contenido+pol%C3%A9mica+when:1d&hl=es-419&gl=CO&ceid=CO:es-419",
    "politica_redes": "https://news.google.com/rss/search?q=pol%C3%ADtico+video+viral+OR+redes+sociales+pol%C3%A9mica+when:1d&hl=es-419&gl=CO&ceid=CO:es-419",
}

def virales():
    """Material crudo del día: búsquedas en alza (Colombia y México) + titulares de las últimas 24 h."""
    out = {"tendencias_colombia": tendencias_google("CO"), "tendencias_mexico": tendencias_google("MX", 12)}
    for k, f in VIRALES_FEEDS.items():
        out[k] = leer(f, 15)
    log("Radar viral:", {k: len(v) for k, v in out.items()})
    return out
