"""
session_manager.py — Gestiona toda la interacción con el navegador en una única sesión.

Flujo:
  1. Abre el browser y navega a la URL (un solo viaje)
  2. Detecta los campos del formulario en el DOM ya cargado
  3. Espera a que el usuario rellene el formulario en localhost:8000
  4. Rellena el formulario real y captura el stream
  5. Cierra el browser

De esta forma la sesión/token generado en la primera visita no caduca.
"""
from __future__ import annotations
import asyncio
import os

from playwright.async_api import async_playwright, Page, BrowserContext

from config import M3U8_RE, MPD_RE, MP4_RE, KEYWORDS, HAR_PATH, DEBUG_PNG, ARTIFACTS_DIR
from form_inspector import FieldInfo, _accept_cookies, _wait_for_form, _extract_fields
from form_server import collect_form_data


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de stream
# ──────────────────────────────────────────────────────────────────────────────

def looks_like_stream(u: str) -> bool:
    ul = (u or "").lower()
    return bool(
        M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u)
        or any(k in ul for k in KEYWORDS)
    )


def extract_candidates_from_har(har_path: str = HAR_PATH, limit: int = 200) -> list[str]:
    import json
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    entries = har.get("log", {}).get("entries", [])
    seen, out = set(), []
    for e in entries:
        u = e.get("request", {}).get("url", "")
        if u and any(k in u.lower() for k in KEYWORDS) and u not in seen:
            seen.add(u)
            out.append(u)
    return out[:limit]


# Extensiones estáticas que nunca son un stream real
_EXCLUDE_DOMAINS = ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
_EXCLUDE_EXTS = (".js", ".css", ".woff", ".woff2", ".png", ".jpg", ".svg", ".ico", ".json", ".html")



def _is_real_stream(u: str) -> bool:
    """True solo si la URL es un stream real, no un asset estático o librería JS."""
    if not u:
        return False
    # Excluir CDNs de librerías JS
    from urllib.parse import urlparse
    domain = urlparse(u).netloc.lower()
    if any(d in domain for d in _EXCLUDE_DOMAINS):
        return False
    # Debe matchear patrón de stream
    if not (M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u)):
        return False
    # No debe tener extensión de asset estático
    path = u.split("?")[0].lower()
    if any(path.endswith(ext) for ext in _EXCLUDE_EXTS):
        return False
    return True


def choose_best_stream(stream_live: str | None, cands: list[str]) -> str | None:
    all_urls = ([stream_live] if stream_live else []) + (cands or [])
    # Prioridad 1: .m3u8 (HLS)
    for u in all_urls:
        if _is_real_stream(u) and M3U8_RE.search(u):
            return u
    # Prioridad 2: .mpd (DASH)
    for u in all_urls:
        if _is_real_stream(u) and MPD_RE.search(u):
            return u
    # Prioridad 3: .mp4 directo
    for u in all_urls:
        if _is_real_stream(u) and MP4_RE.search(u):
            return u
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Relleno de campos
# ──────────────────────────────────────────────────────────────────────────────

async def _fill_field(page, field: FieldInfo, value: str):
    """Rellena un campo en la page o frame indicado."""
    if not value:
        return

    if field.field_type in ("text", "email", "textarea"):
        try:
            loc = page.locator(field.selector).first
            if await loc.count() > 0:
                await loc.fill(value)
                print(f"   ✏️  '{field.label}' → '{value}'")
                return
        except Exception as e:
            print(f"   ⚠️  Error rellenando '{field.label}': {e}")

    elif field.field_type == "select":
        try:
            loc = page.locator(field.selector).first
            if await loc.count() > 0:
                await loc.select_option(label=value)
                print(f"   🔽 '{field.label}' → '{value}' (select)")
                return
        except Exception:
            pass
        try:
            await page.locator(field.selector).first.select_option(value=value)
        except Exception as e:
            print(f"   ⚠️  Select '{field.label}' falló: {e}")

    elif field.field_type == "dropdown":
        await _fill_js_dropdown(page, field, value)

    elif field.field_type == "checkbox":
        should_check = value.lower() in ("true", "1", "yes", "sí", "si")
        try:
            loc = page.locator(field.selector).first
            if await loc.count() > 0:
                await loc.check() if should_check else await loc.uncheck()
                print(f"   ☑️  '{field.label}' → {should_check}")
        except Exception as e:
            print(f"   ⚠️  Checkbox '{field.label}': {e}")


async def _fill_js_dropdown(page: Page, field: FieldInfo, text: str):
    """Maneja dropdowns JS (ng-select, react-select, custom comboboxes)."""
    # Buscar el control cerca del label
    control = None
    for sel in ['[role="combobox"]', 'button', '[class*="select"]', '[class*="dropdown"]']:
        c = page.locator(
            f'label:has-text("{field.label}") ~ {sel}, '
            f'label:has-text("{field.label}") + {sel}'
        ).first
        if await c.count() > 0:
            control = c
            break

    if not control:
        print(f"   ⚠️  No se encontró control para dropdown '{field.label}'")
        return

    try:
        await control.click(timeout=4000)
        await page.wait_for_timeout(400)

        ov_input = page.locator(
            ".cdk-overlay-container input:visible, "
            ".ng-dropdown-panel input:visible, "
            "[role='listbox'] input:visible"
        ).first
        if await ov_input.count() > 0:
            await ov_input.fill(text)
        else:
            await page.keyboard.type(text, delay=40)

        await page.wait_for_timeout(400)
        await page.keyboard.press("Enter")
        print(f"   🔽 '{field.label}' → '{text}' (dropdown JS)")
    except Exception as e:
        print(f"   ⚠️  Dropdown '{field.label}': {e}")


async def _submit_form(page: Page) -> bool:
    # Selectores en orden de prioridad — más específico primero
    submit_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("submit")',
        'button:has-text("Register")',
        'button:has-text("Continue")',
        'button:has-text("Next")',
        'button:visible',  # último recurso: cualquier botón visible
    ]
    submit = None
    for sel in submit_selectors:
        loc = page.locator(sel).first
        if await loc.count() > 0:
            submit = loc
            print(f"  🔘 Botón submit encontrado: '{sel}'")
            break

    if submit is None:
        print("  ⚠️  No se encontró botón submit")
        return False

    try:
        await submit.wait_for(state="visible", timeout=5000)
        for _ in range(20):
            aria = await submit.get_attribute("aria-disabled")
            disabled = await submit.get_attribute("disabled")
            if aria in (None, "false") and disabled is None:
                break
            await page.wait_for_timeout(250)
        await submit.click(timeout=10000)
        return True
    except Exception as e:
        print(f"  ⚠️  Error en click submit: {e}")
        return False


async def _click_play(page: Page):
    for sel in [
        ".vjs-big-play-button",
        'button:has-text("Play")',
        '[aria-label*="Play" i]',
        '[title*="Play" i]',
    ]:
        loc = page.locator(sel)
        if await loc.count() > 0:
            try:
                await loc.first.click(timeout=5000)
                return
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Sesión principal — todo en un único browser
# ──────────────────────────────────────────────────────────────────────────────

async def run_session(url: str, timeout_ms: int = 45000, form_server_port: int = 8000) -> str | None:
    """
    Gestiona todo el proceso en una única sesión de Playwright:
      1. Abre el browser y navega a la URL
      2. Detecta campos del formulario
      3. Muestra formulario web al usuario (localhost:8000)
      4. Rellena el formulario real con los datos del usuario
      5. Captura y devuelve la URL del stream

    Args:
        url:              URL de la conferencia
        timeout_ms:       Tiempo de espera de red tras el submit
        form_server_port: Puerto del servidor FastAPI

    Returns:
        URL del stream o None
    """
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    found = {"stream": None}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )
        context: BrowserContext = await browser.new_context(
            record_har_path=HAR_PATH,
            record_har_content="attach"
        )
        page = await context.new_page()

        # Listener de stream activo durante toda la sesión.
        # Se adjunta al contexto completo (no solo a la página principal)
        # para capturar requests de iframes y popups.
        def on_request(req):
            if found["stream"] is None and _is_real_stream(req.url):
                found["stream"] = req.url
                print(f"🎯 Stream (live): {req.url}")

        context.on("request", on_request)   # ← contexto, no page

        # ── PASO 1: Navegar ───────────────────────────────────────────────────
        print(f"\n🌐 Abriendo (sesión única): {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await _accept_cookies(page)
        await _wait_for_form(page, timeout_ms=15000)

        # ── PASO 2: Detectar campos (sobre el DOM ya cargado) ─────────────────
        print("\n📋 Detectando campos del formulario…")

        async def extract_fields_all_frames() -> list:
            """Busca campos en la página principal y en todos los iframes."""
            # Esperar a que los iframes carguen
            await page.wait_for_timeout(2000)
            frames = page.frames
            print(f"  🖼️  Buscando en {len(frames)} frame(s)…")

            all_fields = []
            seen_ids = set()

            for frame in frames:
                try:
                    frame_url = frame.url[:60] if frame.url else 'about:blank'
                    fields_in_frame = await _extract_fields(frame)
                    # Deduplicar por id
                    new_fields = [f for f in fields_in_frame if f.id not in seen_ids]
                    if new_fields:
                        print(f"  ✅ {len(new_fields)} campo(s) en '{frame_url}'")
                        for f in new_fields:
                            seen_ids.add(f.id)
                            # Guardar referencia al frame para rellenar después
                            f._frame = frame
                        all_fields.extend(new_fields)
                except Exception as e:
                    continue

            return all_fields

        # Primer intento
        fields = await extract_fields_all_frames()

        # Si no encontró nada, esperar 3s más y reintentar
        if not fields:
            print("  ⏳ Sin campos, esperando 3s más...")
            await page.wait_for_timeout(3000)
            fields = await extract_fields_all_frames()

        if fields:
            print(f"✅ {len(fields)} campo(s) detectado(s): {[f.label for f in fields]}")
        else:
            print("⚠️  No se detectaron campos. Se mostrará campo email por defecto.")

        # ── PASO 3: Formulario web para el usuario ────────────────────────────
        form_data: dict = {}
        # Levantar siempre el servidor, aunque no se hayan detectado campos.
        # Si la lista esta vacia, collect_form_data muestra campos por defecto (email).
        print(f"\n🖥️  Levantando formulario web en localhost:{form_server_port}…")

        # Esperar a que el usuario rellene el formulario
        form_data = await collect_form_data(fields=fields, url=url, port=form_server_port)

        # ── PASO 4: Rellenar formulario real ────────────────────────────────────
        if form_data:
            print("\n📝 Rellenando formulario real con datos del usuario:")
            field_map = {f.id: f for f in fields}
            submitted_frames = set()

            for field_id, value in form_data.items():
                if not value:
                    continue

                if field_id in field_map:
                    # Campo detectado por inspector — usar frame y selector exactos
                    f = field_map[field_id]
                    target_frame = getattr(f, '_frame', page)
                    await _fill_field(target_frame, f, value)
                else:
                    # Fallback para email sin FieldInfo
                    if field_id != 'email':
                        continue
                    for frame in page.frames:
                        for sel in [
                            'input[type="email"]',
                            'input[placeholder*="email" i]',
                            'input[placeholder*="address" i]',
                            'input:not([type="hidden"]):not([type="submit"])',
                        ]:
                            loc = frame.locator(sel).first
                            if await loc.count() > 0:
                                await loc.click()
                                await loc.fill(value)
                                actual = await loc.input_value()
                                if actual:
                                    print(f"   ✏️  email (fallback) en '{frame.url[:50]}' → '{value}'")
                                    submitted_frames.add(id(frame))
                                    break
                        else:
                            continue
                        break

            # Submit: en cada frame que tenga campos rellenados
            frames_to_submit = set()
            for f in fields:
                target_frame = getattr(f, '_frame', page)
                frames_to_submit.add(id(target_frame))
            frame_map = {id(fr): fr for fr in page.frames}
            # Si no hay fields detectados, buscar el frame con el formulario
            if not frames_to_submit:
                frames_to_submit = submitted_frames or {id(page.frames[-1])}

            for fid in frames_to_submit:
                target_frame = frame_map.get(fid, page)
                frame_url = target_frame.url[:50] if hasattr(target_frame, 'url') else 'main'
                for btn_sel in [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Register")',
                    'button:visible',
                ]:
                    btn = target_frame.locator(btn_sel).first
                    if await btn.count() > 0:
                        await btn.click(timeout=5000)
                        print(f"   ✅ Submit en '{frame_url}'")
                        break

        else:
            print("⚠️  Sin datos de formulario, intentando continuar…")

        # ── PASO 5: Intentar play y esperar tráfico ───────────────────────────
        await page.wait_for_timeout(5000)  # pausa para que el iframe cargue
        await _click_play(page)
        print(f"\n⏳ Esperando tráfico de red ({timeout_ms / 1000:.0f}s)…")
        await page.wait_for_timeout(timeout_ms)

        await page.screenshot(path=DEBUG_PNG, full_page=True)
        print(f"🖼️  Screenshot guardado: {DEBUG_PNG}")

        await context.close()
        await browser.close()

    return found["stream"]