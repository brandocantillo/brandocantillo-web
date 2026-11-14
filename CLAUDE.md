# Web de Brando Cantillo

Marca personal de Brando Cantillo: estratega político (10 años, concejo a Senado), abogado especialista en derechos de autor y nuevas tecnologías, experto en IA y automatizaciones, creador de marcas personales (Dimelonegrito, Aiton Chinchia, Pechyplayers).

## Herramientas
- Skills `emil-design-eng` y `design-taste-frontend` en `.claude/skills/` (las mismas de mi-proyecto).
- Playwright MCP (`.mcp.json`) para revisar en escritorio y móvil antes de entregar.

## Estructura
- `/` Inicio: quién soy y cómo ayudo (servicios, trayectoria, quién soy, manifiesto, marcas, columnas recientes, contacto).
- `/marketing/` Formatos de contenido y comunidades digitales.
- `/columnas/` Blog diario (comunicación política e IA para emprendedores), escrito por los agentes de `agents/` y aprobado por Telegram.

## Reglas visuales
- Solo blanco (#FFFFFF), rojo (#E3001B) y negro (#0A0A0A), más gris de apoyo.
- Archivo (títulos muy anchos y pesados) + Source Serif 4 para leer columnas.
- Movimiento: ease-out fuerte, respuestas < 300 ms, press scale .97, respetar prefers-reduced-motion.
- No inventar cifras, clientes ni testimonios. Todo el texto en español.

## Comandos
- `python3 build.py` genera `public/`.
- `cd public && python3 -m http.server 8000` para verla en http://localhost:8000
- Ver README.md para publicar y activar los agentes.
