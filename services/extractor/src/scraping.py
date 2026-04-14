"""
scraping.py — Rellena el formulario web y captura la URL del stream.

Cambio respecto a la versión anterior:
- Ya NO lee los datos del formulario de config.py / variables de entorno.
- Recibe `form_data` como diccionario {field_id: valor} desde form_server.
- Mapea cada FieldInfo detectada a su selector real y rellena el campo.
"""
from __future__ import annotations
import os
import re
import json

from playwright.async_api import async_playwright, Page
from config import M3U8_RE, MPD_RE, MP4_RE, KEYWORDS, HAR_PATH, DEBUG_PNG, ARTIFACTS_DIR
from form_inspector import FieldInfo


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de detección
# ──────────────────────────────────────────────────────────────────────────────

def looks_like_stream(u: str) -> bool:
    ul = (u or "").lower()
    return bool(M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u) or any(k in ul for k in KEYWORDS))


def extract_candidates_from_har(har_path: str = "network.har", limit: int = 200) -> list[str]:
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    entries = har.get("log", {}).get("entries", [])
    urls = []
    for e in entries:
        u = e.get("request", {}).get("url", "")
        if u and any(k in u.lower() for k in KEYWORDS):
            urls.append(u)

    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:limit]


def choose_best_stream(stream_live: str | None, cands: list[str]) -> str | None:
    for u in ([stream_live] if stream_live else []) + (cands or []):
        if not u:
            continue
        if M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u):
            return u
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de interacción con la página
# ──────────────────────────────────────────────────────────────────────────────

async def click_if_exists(page: Page, selectors: list[str], timeout: int = 2000) -> bool:
    for sel in selectors:
        loc = page.locator(sel)
        if await loc.count() > 0:
            try:
                await loc.first.click(timeout=timeout)
                return True
            except Exception:
                pass
    return False


async def accept_cookies(page: Page):
    await click_if_exists(page, [
        'button:has-text("Accept All")',
        'button:has-text("Aceptar todo")',
        'button#onetrust-accept-btn-handler',
        'button[aria-label*="Accept" i]',
    ], timeout=4000)


async def _fill_field(page: Page, field: FieldInfo, value: str):
    """
    Rellena un campo concreto usando el selector almacenado en FieldInfo.
    Gestiona texto, email, select nativo y dropdowns JS.
    """
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
                # Intentar seleccionar por texto visible
                await loc.select_option(label=value)
                print(f"   🔽 '{field.label}' → '{value}' (select)")
                return
        except Exception:
            pass
        # Fallback: seleccionar por valor
        try:
            await page.locator(field.selector).first.select_option(value=value)
        except Exception as e:
            print(f"   ⚠️  Select '{field.label}' falló: {e}")

    elif field.field_type == "dropdown":
        # Dropdown JS: clic + escribir + Enter
        await _fill_js_dropdown(page, field, value)

    elif field.field_type == "checkbox":
        should_check = value.lower() in ("true", "1", "yes", "sí", "si")
        try:
            loc = page.locator(field.selector).first
            if await loc.count() > 0:
                if should_check:
                    await loc.check()
                else:
                    await loc.uncheck()
                print(f"   ☑️  '{field.label}' → {should_check}")
        except Exception as e:
            print(f"   ⚠️  Checkbox '{field.label}': {e}")


async def _fill_js_dropdown(page: Page, field: FieldInfo, text: str):
    """Maneja dropdowns JS (ng-select, react-select, custom comboboxes)."""
    label_loc = page.locator(f'label:has-text("{field.label}")').first

    # Encontrar el control asociado
    control = None
    for sel in ['[role="combobox"]', 'button', '[class*="select"]', '[class*="dropdown"]']:
        try:
            c = label_loc.locator(f'xpath=following::*[self::{sel.strip("[role=]").strip()}][1]').first
        except Exception:
            pass
        # Selector CSS simple
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

        # Buscar input de búsqueda en overlay
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
    submit = page.locator(
        'button:has-text("Submit"), button[type="submit"], input[type="submit"]'
    ).first
    if await submit.count() == 0:
        return False

    await submit.wait_for(state="visible", timeout=15000)

    # Esperar a que el botón esté habilitado (hasta 10s)
    for _ in range(40):
        aria = await submit.get_attribute("aria-disabled")
        disabled = await submit.get_attribute("disabled")
        if aria in (None, "false") and disabled is None:
            break
        await page.wait_for_timeout(250)

    try:
        await submit.click(timeout=15000)
        return True
    except Exception:
        return False


async def _click_play(page: Page):
    await click_if_exists(page, [
        ".vjs-big-play-button",
        'button:has-text("Play")',
        '[aria-label*="Play" i]',
        '[title*="Play" i]',
    ], timeout=5000)


# ──────────────────────────────────────────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────────────────────────────────────────

async def fill_form_and_find_stream(
    url: str,
    fields: list[FieldInfo],
    form_data: dict,
    timeout_ms: int = 45000,
) -> str | None:
    """
    Abre la URL, rellena el formulario con los datos proporcionados por el usuario
    y captura la URL del stream.

    Args:
        url:        URL de la conferencia
        fields:     Lista de FieldInfo detectados por form_inspector
        form_data:  Diccionario {field_id: valor} devuelto por form_server
        timeout_ms: Tiempo de espera de red tras el submit

    Returns:
        URL del stream o None
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )

        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        context = await browser.new_context(
            record_har_path=HAR_PATH,
            record_har_content="attach"
        )
        page = await context.new_page()

        found = {"stream": None}

        def on_request(req):
            if found["stream"] is None and looks_like_stream(req.url):
                found["stream"] = req.url
                print(f"🎯 Stream (live): {req.url}")

        page.on("request", on_request)

        print(f"\n🌐 Abriendo: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await accept_cookies(page)

        # Esperar form
        try:
            await page.locator("form, input:visible").first.wait_for(
                state="visible", timeout=15000
            )
        except Exception:
            pass
        await page.wait_for_timeout(1000)

        # Rellenar cada campo
        print("\n📝 Rellenando formulario con datos del usuario:")
        field_map = {f.id: f for f in fields}
        for field_id, value in form_data.items():
            if field_id in field_map:
                await _fill_field(page, field_map[field_id], value)

        # Submit
        ok_submit = await _submit_form(page)
        print(f"\n✅ Submit: {ok_submit}")

        # Intentar play
        await _click_play(page)

        print(f"⏳ Esperando tráfico de red ({timeout_ms/1000:.0f}s)…")
        await page.wait_for_timeout(timeout_ms)

        await page.screenshot(path=DEBUG_PNG, full_page=True)
        print(f"🖼️  Screenshot guardado: {DEBUG_PNG}")

        await context.close()
        await browser.close()

    return found["stream"]