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
