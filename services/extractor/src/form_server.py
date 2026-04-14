"""
form_server.py — Mini servidor FastAPI que sirve el formulario dinámico.

Problema anterior: uvicorn se lanzaba en un thread secundario mientras el event
loop principal de asyncio seguía corriendo → conflicto de loops en Docker.

Solución: usar uvicorn.Server.serve() que es una coroutine async nativa.
Se ejecuta con asyncio.gather() junto a un watcher que lo apaga en cuanto
el usuario envía el formulario. Todo en el mismo event loop, sin threads.
"""
from __future__ import annotations
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from form_inspector import FieldInfo


# ──────────────────────────────────────────────────────────────────────────────
# HTML del formulario dinámico
# ──────────────────────────────────────────────────────────────────────────────

def _build_html(fields: list[FieldInfo], url: str) -> str:
    def render_field(f: FieldInfo) -> str:
        field_id = f"field_{f.id}"

        if f.field_type == "select" and f.options:
            opts_html = "".join(
                f'<option value="{o}">{o}</option>' for o in f.options if o
            )
            return f"""
            <div class="field-group">
                <label for="{field_id}">{f.label}</label>
                <div class="select-wrap">
                    <select id="{field_id}" name="{f.id}">
                        <option value="" disabled selected>Selecciona…</option>
                        {opts_html}
                    </select>
                    <span class="arrow">▾</span>
                </div>
            </div>"""

        if f.field_type in ("text", "email", "dropdown"):
            input_type = "email" if f.field_type == "email" else "text"
            ph = f.placeholder or f"Introduce {f.label.lower()}…"
            return f"""
            <div class="field-group">
                <label for="{field_id}">{f.label}</label>
                <input type="{input_type}" id="{field_id}" name="{f.id}"
                       placeholder="{ph}" autocomplete="off">
            </div>"""

        if f.field_type == "textarea":
            return f"""
            <div class="field-group">
                <label for="{field_id}">{f.label}</label>
                <textarea id="{field_id}" name="{f.id}" rows="3"
                          placeholder="{f.placeholder or ''}"></textarea>
            </div>"""

        if f.field_type == "checkbox":
            return f"""
            <div class="field-group field-group--check">
                <input type="checkbox" id="{field_id}" name="{f.id}" value="true">
                <label for="{field_id}">{f.label}</label>
            </div>"""

        # fallback text
        return f"""
        <div class="field-group">
            <label for="{field_id}">{f.label}</label>
            <input type="text" id="{field_id}" name="{f.id}" autocomplete="off">
        </div>"""

    fields_html = "\n".join(render_field(f) for f in fields)
    short_url = url[:70] + "…" if len(url) > 70 else url

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Formulario de acceso</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0d0f14;
    --surface: #151820;
    --surface2: #1c2030;
    --border: #2a3040;
    --accent: #4fffb0;
    --text: #e2e8f0;
    --muted: #6b7a99;
    --error: #ff5e7a;
    --radius: 6px;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'IBM Plex Sans', sans-serif;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
    background-image:
      radial-gradient(ellipse 60% 40% at 20% 0%, rgba(79,255,176,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 40% 30% at 80% 100%, rgba(0,191,255,0.05) 0%, transparent 60%);
  }}

  .card {{
    width: 100%;
    max-width: 520px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 24px 80px rgba(0,0,0,0.5);
    animation: rise 0.4s cubic-bezier(0.16,1,0.3,1) both;
  }}

  @keyframes rise {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  .card-header {{
    padding: 1.75rem 2rem 1.5rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
  }}

  .badge {{
    font-family: var(--mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    background: rgba(79,255,176,0.08);
    border: 1px solid rgba(79,255,176,0.2);
    padding: 0.25rem 0.6rem;
    border-radius: 3px;
    display: inline-block;
    margin-bottom: 0.85rem;
  }}

  .card-header h1 {{
    font-size: 1.25rem;
    font-weight: 500;
    line-height: 1.3;
    margin-bottom: 0.5rem;
  }}

  .url-chip {{
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--muted);
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.3rem 0.6rem;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-top: 0.6rem;
  }}

  .card-body {{ padding: 1.75rem 2rem; }}

  .fields-count {{
    font-size: 0.75rem;
    color: var(--muted);
    font-family: var(--mono);
    margin-bottom: 1.5rem;
  }}

  .field-group {{ margin-bottom: 1.25rem; }}

  label {{
    display: block;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--muted);
    letter-spacing: 0.04em;
    margin-bottom: 0.4rem;
    text-transform: uppercase;
  }}

  input[type="text"],
  input[type="email"],
  textarea {{
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--sans);
    font-size: 0.9rem;
    padding: 0.65rem 0.85rem;
    transition: border-color 0.15s, box-shadow 0.15s;
    outline: none;
  }}

  input[type="text"]:focus,
  input[type="email"]:focus,
  textarea:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(79,255,176,0.1);
  }}

  .select-wrap {{ position: relative; }}

  select {{
    width: 100%;
    appearance: none;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--sans);
    font-size: 0.9rem;
    padding: 0.65rem 2rem 0.65rem 0.85rem;
    cursor: pointer;
    outline: none;
    transition: border-color 0.15s;
  }}

  select:focus {{ border-color: var(--accent); }}

  .arrow {{
    position: absolute;
    right: 0.85rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    pointer-events: none;
    font-size: 0.75rem;
  }}

  .field-group--check {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }}

  .field-group--check label {{
    margin: 0;
    text-transform: none;
    font-size: 0.85rem;
    color: var(--text);
  }}

  input[type="checkbox"] {{
    width: 1rem;
    height: 1rem;
    accent-color: var(--accent);
    cursor: pointer;
  }}

  .divider {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
  }}

  .btn-submit {{
    width: 100%;
    padding: 0.85rem;
    background: var(--accent);
    color: #0d0f14;
    font-family: var(--mono);
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
  }}

  .btn-submit:hover {{ opacity: 0.88; transform: translateY(-1px); }}
  .btn-submit:active {{ transform: translateY(0); }}
  .btn-submit:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}

  #status {{
    display: none;
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    border-radius: var(--radius);
    font-family: var(--mono);
    font-size: 0.78rem;
    text-align: center;
  }}

  #status.ok {{
    background: rgba(79,255,176,0.08);
    border: 1px solid rgba(79,255,176,0.25);
    color: var(--accent);
  }}

  #status.err {{
    background: rgba(255,94,122,0.08);
    border: 1px solid rgba(255,94,122,0.25);
    color: var(--error);
  }}

  .hint {{
    font-size: 0.72rem;
    color: var(--muted);
    font-family: var(--mono);
    text-align: center;
    margin-top: 1rem;
    line-height: 1.5;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <span class="badge">🔍 Formulario detectado</span>
    <h1>Datos de acceso al webcast</h1>
    <span class="url-chip">{short_url}</span>
  </div>
  <div class="card-body">
    <p class="fields-count">{len(fields)} campo(s) detectado(s) · rellena y envía</p>
    <form id="dynForm" autocomplete="off">
      {fields_html}
      <hr class="divider">
      <button type="submit" class="btn-submit" id="submitBtn">
        ▶ Iniciar descarga
      </button>
    </form>
    <div id="status"></div>
    <p class="hint">Esta ventana se puede cerrar una vez enviado.<br>
    El extractor continuará en segundo plano.</p>
  </div>
</div>
<script>
  document.getElementById('dynForm').addEventListener('submit', async (e) => {{
    e.preventDefault();
    const btn = document.getElementById('submitBtn');
    const status = document.getElementById('status');

    btn.textContent = '⏳ Enviando…';
    btn.disabled = true;

    const data = {{}};
    new FormData(e.target).forEach((v, k) => data[k] = v);
    e.target.querySelectorAll('input[type=checkbox]').forEach(cb => {{
      if (!cb.checked) data[cb.name] = 'false';
    }});

    try {{
      const res = await fetch('/submit', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(data)
      }});
      const json = await res.json();
      if (res.ok) {{
        status.className = 'ok';
        status.textContent = '✅ ' + (json.message || 'Datos recibidos. El extractor continúa…');
        status.style.display = 'block';
        btn.textContent = '✅ Enviado';
      }} else {{
        throw new Error(json.detail || 'Error desconocido');
      }}
    }} catch (err) {{
      status.className = 'err';
      status.textContent = '❌ ' + err.message;
      status.style.display = 'block';
      btn.disabled = false;
      btn.textContent = '▶ Reintentar';
    }}
  }});
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# Servidor async nativo — sin threads
# ──────────────────────────────────────────────────────────────────────────────

def _default_fields() -> list[FieldInfo]:
    """Campos por defecto cuando el inspector no detecta nada."""
    return [
        FieldInfo(
            id="email",
            label="Email",
            field_type="email",
            selector='input[type="email"]',
            placeholder="Introduce tu email de registro...",
        )
    ]


async def collect_form_data(fields: list[FieldInfo], url: str, port: int = 8000) -> dict:
    # Si no se detectaron campos, usar campos por defecto
    if not fields:
        print("  ⚠️  Sin campos detectados — mostrando campo email por defecto")
        fields = _default_fields()
    """
    Levanta uvicorn usando su API async nativa (server.serve()) y lo ejecuta
    en paralelo con un watcher mediante asyncio.gather().

    Cuando el usuario envía el formulario:
      1. El endpoint /submit guarda los datos y activa un asyncio.Event
      2. El watcher detecta el evento y llama a server.should_exit = True
      3. asyncio.gather() termina limpiamente
      4. Se devuelven los datos al llamador

    Sin threads, sin event loops anidados → funciona correctamente en Docker.
    """
    app = FastAPI()
    html = _build_html(fields, url)
    submit_event = asyncio.Event()
    result: dict = {}

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(content=html)

    @app.post("/submit")
    async def submit(request: Request):
        data = await request.json()
        result.update(data)
        submit_event.set()
        return JSONResponse({"message": "Datos recibidos. El extractor ya puede continuar."})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    print(f"\n{'='*60}")
    print(f"🌐 FORMULARIO DISPONIBLE EN:")
    print(f"   http://localhost:{port}")
    print(f"{'='*60}")
    print("⏳ Esperando que rellenes el formulario en el navegador…\n")

    async def watcher():
        """Espera el evento de submit y apaga el servidor."""
        await submit_event.wait()
        server.should_exit = True

    # server.serve() y watcher() corren en el mismo event loop, sin threads
    await asyncio.gather(server.serve(), watcher())

    print(f"✅ Formulario recibido: {result}")
    return result