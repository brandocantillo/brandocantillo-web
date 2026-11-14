"""Utilidades compartidas: configuración, Claude API, Telegram y estado. Solo librería estándar."""
import json, os, re, time, uuid, urllib.request, urllib.error, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config/agentes.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "config/site.json").read_text(encoding="utf-8"))
VOZ = (ROOT / "config/voz-brando.md").read_text(encoding="utf-8")
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
STATE_FILE = DATA / "state.json"

def env(k, required=True):
    v = os.environ.get(k, "")
    if required and not v: raise SystemExit(f"Falta la variable de entorno {k}. Revisa el README, paso 'Secretos'.")
    return v

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

def http(url, data=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0 (BrandoBot)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# ------------------------------------------------------------------ Claude
COSTO = {"in": 0, "out": 0, "searches": 0}

def claude(prompt, system="", model="rapido", max_tokens=2000, web_search=0, temperature=None, retries=3):
    """Llama a Claude. Devuelve (texto, fuentes[]). web_search = nº máx. de búsquedas permitidas."""
    body = {"model": CFG["modelos"].get(model, model), "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:  # cache del system prompt (la guía de voz se repite en cada llamada → más barato)
        body["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if temperature is not None: body["temperature"] = temperature
    if web_search:
        body["tools"] = [{"type": CFG["web_search_tool"], "name": "web_search", "max_uses": web_search}]
    headers = {"x-api-key": env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for i in range(retries):
        try:
            res = json.loads(http("https://api.anthropic.com/v1/messages", json.dumps(body).encode(), headers, timeout=600))
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")[:500]
            if e.code in (429, 500, 502, 503, 529) and i < retries - 1:
                log(f"Claude {e.code}, reintento…"); time.sleep(10 * (i + 1)); continue
            raise RuntimeError(f"Claude API {e.code}: {msg}")
    u = res.get("usage", {})
    COSTO["in"] += u.get("input_tokens", 0); COSTO["out"] += u.get("output_tokens", 0)
    COSTO["searches"] += (u.get("server_tool_use") or {}).get("web_search_requests", 0)
    text, sources = [], {}
    for b in res.get("content", []):
        if b.get("type") == "text": text.append(b["text"])
        if b.get("type") == "web_search_tool_result" and isinstance(b.get("content"), list):
            for r in b["content"]:
                if r.get("url"): sources[r["url"]] = r.get("title", r["url"])
    return "".join(text).strip(), [{"url": k, "title": v} for k, v in sources.items()]

def as_json(text):
    """Extrae el primer objeto/lista JSON de una respuesta."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m: text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0: raise ValueError("La respuesta no trae JSON:\n" + text[:400])
    return json.JSONDecoder().raw_decode(text[start:])[0]

# ------------------------------------------------------------------ Telegram
def tg(method, **params):
    url = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}"
    data = json.dumps(params).encode()
    res = json.loads(http(url, data, {"content-type": "application/json"}, timeout=70))
    if not res.get("ok"): raise RuntimeError(f"Telegram {method}: {res}")
    return res["result"]

def chat_id(): return env("TELEGRAM_CHAT_ID")

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send(text, buttons=None):
    """buttons: lista de filas, cada fila lista de (texto, callback_data)."""
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [""]
    out = None
    for n, c in enumerate(chunks):
        p = {"chat_id": chat_id(), "text": c, "parse_mode": "HTML", "disable_web_page_preview": True}
        if buttons and n == len(chunks) - 1:
            p["reply_markup"] = {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in buttons]}
        out = tg("sendMessage", **p)
    return out

def send_document(path, caption=""):
    boundary = uuid.uuid4().hex
    path = Path(path)
    parts = []
    for k, v in (("chat_id", chat_id()), ("caption", caption[:1000])):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{path.name}"\r\nContent-Type: text/markdown\r\n\r\n'.encode()
                 + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    url = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendDocument"
    return json.loads(http(url, b"".join(parts), {"content-type": f"multipart/form-data; boundary={boundary}"}))

# ------------------------------------------------------------------ Estado
def load_state():
    if STATE_FILE.exists(): return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"offset": 0, "proposal": None, "pending": None, "history": []}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
