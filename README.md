# Ecosistema digital de Brando Cantillo

Tres piezas que trabajan juntas:

1. **La web** (`templates/`, `static/`, `build.py`): estilo Apple, animaciones con scroll, SEO técnico completo.
2. **El equipo de agentes** (`agents/`): investigan, escriben y optimizan una columna diaria.
3. **El bot de Telegram**: te propone temas, tú eliges y opinas, y apruebas antes de publicar.

Analogía: la web es tu **tarima**, los agentes son tu **equipo de prensa** y Telegram es tu **celular de jefe de campaña**: nada sale sin tu visto bueno.

---

## Cómo funciona el día a día

```
6:00 a. m.  Radar lee noticias (RSS, gratis) → Curador (Haiku) propone 5 temas → te llegan a Telegram
Tú          Eliges un tema → escribes tu opinión o anécdota (o "sin nota")
Agentes     Investigador (Sonnet + búsqueda web) → Estratega SEO (Haiku) → Columnista (Sonnet)
            → Editor (Haiku) revisa muletillas de IA, datos sin fuente y longitud → corrige si hace falta
Tú          Recibes el borrador completo (.md) → 🚀 Publicar · ✏️ Pedir cambios · 🗑 Descartar
Publicador  Guarda la columna → la web se actualiza sola → Distribuidor te manda hilo de X, LinkedIn y WhatsApp
```

---

## Paso a paso para ponerlo en marcha (≈ 1 hora)

### Paso 1. Personaliza tus datos
1. Abre `config/site.json` y cambia todo lo que dice `CAMBIAR`: correo, WhatsApp (formato `573001234567`), redes, ciudad y dominio (`url`).
2. Abre `config/voz-brando.md` y agrega **tus frases, convicciones e historias reales**. Este archivo es el que hace que las columnas suenen a ti. Dedícale 20 minutos.
3. Lee la columna de ejemplo en `content/posts/` y ajústala: va publicada con tu nombre.

### Paso 2. Crea el repositorio en GitHub
1. Entra a github.com → **New repository** → nombre `brandocantillo-web`.
2. Recomendado: **Public**. Con repositorio público, GitHub Actions es gratis sin límite. Tus claves igual quedan protegidas en "Secrets". Si lo haces privado, tienes 2.000 minutos al mes y el bot consume unos 2.700; en ese caso usa la opción del Paso 6.
3. Sube todos los archivos de esta carpeta (botón **Add file → Upload files**, arrastra todo, **Commit**).

### Paso 3. Publica la web gratis en Cloudflare Pages
1. Crea cuenta en dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → elige el repositorio.
2. Configuración de build:
   - Framework preset: **None**
   - Build command: `python3 build.py`
   - Build output directory: `public`
3. **Save and Deploy**. En 1–2 minutos tienes una URL `*.pages.dev`.
4. Dominio: compra `brandocantillo.com` (o `.co`) y en Pages → **Custom domains** → agrégalo. Si cambias de dominio, actualiza `url` en `config/site.json`.

Cada vez que el bot publique una columna, Cloudflare reconstruye la web solo.

### Paso 4. Crea el bot de Telegram
1. En Telegram busca **@BotFather** → escribe `/newbot` → ponle nombre (ej. "Redacción Brando") → copia el **token**.
2. Abre tu bot nuevo y escríbele `/start`.
3. Para saber tu `TELEGRAM_CHAT_ID`, en tu computador ejecuta:
   ```bash
   TELEGRAM_BOT_TOKEN=tu_token python3 -m agents.bot chatid
   ```
   O abre en el navegador `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` y busca `"chat":{"id":...}`.
   Solo tu chat puede dar órdenes; el bot ignora a cualquier otra persona.

### Paso 5. Conecta Claude (la API)
1. Entra a console.anthropic.com → **API Keys** → **Create key**.
2. Carga saldo (con 20 USD alcanza para empezar; revisa el consumo real la primera semana).
3. En GitHub: tu repositorio → **Settings → Secrets and variables → Actions → New repository secret**. Crea tres:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Ve a la pestaña **Actions** → activa los workflows → abre **Propuestas del día** → **Run workflow**. En 1–2 minutos te llegan los temas a Telegram.

Con esto queda automático: propuestas a las 6:00 a. m. y el bot revisa tus respuestas cada 10 minutos (6 a. m.–7 p. m.) y cada 20 minutos (7–11 p. m.).

### Paso 6 (opcional). Respuesta inmediata desde tu PC
Si no quieres esperar hasta 10 minutos entre cada paso:
```bash
cp .env.ejemplo .env      # llénalo con tus 3 claves
bash run_local.sh         # deja esta ventana abierta
```
Este modo publica haciendo `git push` desde tu PC. Si lo usas, desactiva el workflow **Bot Telegram** en GitHub para que no se crucen.

---

## Columna mensual en medios regionales
El día 25 de cada mes el bot te envía una columna inédita (700–850 palabras) para cada medio de `medios_regionales` en `config/agentes.json`. No se publica en tu web, para respetar la exclusividad. También puedes pedirla cuando quieras con `/mensual` o `/mensual El Pilón`.

## Comandos del bot
| Comando | Qué hace |
|---|---|
| `/temas` | Propone temas en ese momento |
| `/tema La comunicación de Bukele en X y qué copiar en una alcaldía` | Escribe sobre tu tema |
| `/marketing`, `/comunicacion`, `/marca`, `/ia` | Temas solo de esa categoría |
| `/mensual` | Columna inédita para tu espacio en medios regionales |
| `/estado` | Muestra en qué va |
| `/cancelar` | Descarta lo pendiente |

También puedes escribirle un tema directamente sin comando.

---

## Estrategia de posicionamiento (lo que hacen los agentes)
1. **Clústeres de temas.** Cuatro categorías con su página pilar: Marketing político, Comunicación política, Marca personal y comunidades, e IA para emprendedores. El Curador equilibra la semana según `mezcla_semanal` en `config/agentes.json`.
2. **Newsjacking + evergreen.** Cada día mezcla temas de actualidad (Google Trends Colombia y noticias, para Google Discover y News) con guías que se buscan todo el año.
3. **Citas a medios grandes.** Cada columna cita y enlaza al menos 4 medios o estudios reconocidos (El Tiempo, Semana, La Silla Vacía, BBC, Reuters…). Eso da autoridad (E-E-A-T) y abre la puerta a que esos medios te conozcan. El editor rechaza la columna si faltan citas.
4. **Enlazado interno.** Mínimo 3 enlaces por columna hacia otras columnas y páginas pilar, para que la autoridad fluya hacia el inicio y /marketing/.
5. **Relaciones públicas digitales (el tráfico de los sitios grandes hacia el tuyo).** Después de publicar, el Relacionista te manda por Telegram correos listos para periodistas ofreciéndote como fuente experta, una versión de columna invitada para otros medios, un artículo de LinkedIn con "Publicado originalmente en…" y una respuesta experta para foros. Cada medio que te cite con enlace es un backlink que sube tu posición. Tú revisas y envías: nada sale solo.
6. **Indexación rápida.** Sitemap de Google News para lo publicado en las últimas 48 h, aviso automático a Bing y otros buscadores (IndexNow) y datos estructurados con las fuentes citadas.

Importante: los agentes nunca copian textos de otros medios. Copiar contenido ajeno hace que Google penalice el sitio; lo que posiciona es el análisis propio con fuentes enlazadas.

## Costos aproximados
- Web, hosting, GitHub Actions y RSS: **0** (solo pagas el dominio, unos 10–15 USD/año).
- Por columna: la investigación con búsqueda web y la escritura (Sonnet) son la mayor parte; lo demás corre en Haiku, el modelo más barato. Cada borrador te muestra los tokens usados para que calcules con la tarifa vigente en anthropic.com/pricing. Como referencia, una columna así suele quedar en centavos de dólar, no en dólares.
- Para bajar más el costo: en `config/agentes.json` baja `busquedas_max_por_columna` o pon `"escritor": "claude-haiku-5-5"` (más barato y menos fino).

## SEO incluido
- Títulos, descripciones, canonical, hreflang `es-CO`, Open Graph y X Cards en cada página.
- Datos estructurados: `Person`, `WebSite`, `ProfessionalService`, `BlogPosting`, `BreadcrumbList`, `FAQPage`, `ItemList`.
- `sitemap.xml`, `robots.txt`, `feed.xml` (RSS), `llms.txt` (para buscadores con IA como ChatGPT y Perplexity).
- Imágenes WebP responsivas, carga diferida, fuentes con `display=swap` y sin frameworks pesados (rápida en Core Web Vitals).
- Cada columna sale con keyword principal y secundarias, H2 pensados para búsquedas reales, FAQ, enlaces internos a columnas anteriores y fuentes enlazadas.

**Después de publicar:** registra el sitio en Google Search Console, verifica con la etiqueta (pega el código en `google_site_verification` de `config/site.json`) y envía `https://tudominio.com/sitemap.xml`. Si quieres analítica, pon tu ID de GA4 en `ga4_id`.

## Estructura
```
config/        datos del sitio, voz, modelos y fuentes RSS
content/posts/ las columnas (markdown con metadatos JSON)
templates/     HTML de la web
static/        CSS, JS, imágenes
agents/        radar, equipo editorial y bot
data/          estado del bot
build.py       genera la web en public/
```

Probar la web localmente:
```bash
python3 build.py && cd public && python3 -m http.server 8000
# abre http://localhost:8000
```
