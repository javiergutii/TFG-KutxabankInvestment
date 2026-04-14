"""
form_inspector.py — Detecta campos de formulario en una URL usando Playwright.

Devuelve una lista de FieldInfo con toda la info necesaria para:
  1. Renderizar el formulario dinámico en FastAPI/HTML
  2. Rellenar el formulario real con Playwright
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Literal
from playwright.async_api import async_playwright, Page


FieldType = Literal["text", "email", "select", "dropdown", "checkbox", "radio", "textarea"]


@dataclass
class FieldInfo:
    id: str                          # identificador único (slug del label o name)
    label: str                       # texto visible del label
    field_type: FieldType            # tipo de campo
    selector: str                    # selector CSS/Playwright para localizar el input
    options: list[str] = field(default_factory=list)   # para select/dropdown
    required: bool = False
    placeholder: str = ""


async def _accept_cookies(page: Page):
    for sel in [
        'button:has-text("Accept All")',
        'button:has-text("Aceptar todo")',
        'button#onetrust-accept-btn-handler',
        'button[aria-label*="Accept" i]',
    ]:
        loc = page.locator(sel)
        if await loc.count() > 0:
            try:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(800)
                break
            except Exception:
                pass


async def _wait_for_form(page: Page, timeout_ms: int = 15000):
    """
    Espera a que aparezca un formulario o input en la pagina.
    Primero espera a networkidle para que el JS haya inyectado el form.
    """
    # Esperar a que la red este tranquila (JS terminado de inyectar el DOM)
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass

    # Selectores en orden de prioridad
    selectors = [
        "input[type='email']:visible",
        "input[placeholder]:visible",
        "form input:visible",
        "form:visible",
        "input:visible",
    ]
    for sel in selectors:
        try:
            await page.locator(sel).first.wait_for(state="visible", timeout=timeout_ms)
            print(f"  OK Formulario detectado via: {sel}")
            break
        except Exception:
            continue

    # Pausa extra para dropdowns JS
    await page.wait_for_timeout(5000)


# Selectores de idioma típicos — los ignoramos, no son campos de registro
_LANG_SELECTOR_HINTS = [
    "english", "español", "french", "deutsch", "language", "lang", "idioma",
    "italiano", "português", "dutch", "japanese", "chinese", "korean",
    "traducir", "translate",
]

# Labels de ruido que no son campos de registro
_NOISE_LABELS = {
    "traducir del", "traducir a", "translate from", "translate to",
    "language", "idioma", "english", "español",
}

def _looks_like_lang_selector(options: list[str]) -> bool:
    """Devuelve True si el select parece un selector de idioma."""
    joined = " ".join(o.lower() for o in options)
    return sum(1 for hint in _LANG_SELECTOR_HINTS if hint in joined) >= 2

def _is_noise_label(label_text: str) -> bool:
    """Devuelve True si el label es ruido (selector de idioma, popup de browser, etc.)."""
    return label_text.lower().strip() in _NOISE_LABELS


async def _extract_fields(page: Page) -> list[FieldInfo]:
    """
    Extrae todos los campos visibles del formulario.
    Estrategia 1: iterar labels y encontrar su control asociado.
    Estrategia 2: buscar inputs por placeholder (sin label).
    Los selectores de idioma se filtran automáticamente.
    """
    fields: list[FieldInfo] = []
    seen_ids: set[str] = set()
    seen_selectors: set[str] = set()

    # ── Estrategia 1: via labels ──────────────────────────────────────────────
    labels = await page.locator("label:visible").all()

    for label in labels:
        try:
            label_text = (await label.inner_text()).strip()
            if not label_text or len(label_text) > 100:
                continue

            # Ignorar labels de ruido (popup de traducción, selectores de idioma del nav)
            if _is_noise_label(label_text):
                print(f"  🔇 Ignorando label de ruido: '{label_text}'")
                continue

            # Ignorar elementos dentro de nav, header o footer
            in_nav = await label.evaluate(
                "el => !!el.closest('nav, header, footer, [role=navigation]')"
            )
            if in_nav:
                print(f"  🔇 Ignorando campo en nav/header: '{label_text}'")
                continue

            slug = _slugify(label_text)
            if slug in seen_ids:
                continue

            field_info = await _resolve_field(page, label, label_text, slug)
            if field_info:
                # Filtrar selectores de idioma
                if field_info.field_type == "select" and _looks_like_lang_selector(field_info.options):
                    print(f"  🌐 Ignorando selector de idioma: '{label_text}'")
                    continue
                seen_ids.add(slug)
                seen_selectors.add(field_info.selector)
                fields.append(field_info)
        except Exception:
            continue

    # ── Estrategia 2: inputs por placeholder (sin label) ─────────────────────
    # Busca inputs que tengan placeholder pero no estén ya recogidos via label
    placeholder_inputs = await page.locator(
        "input[placeholder]:visible:not([type='hidden']):not([type='submit']):not([type='button'])"
    ).all()

    for inp in placeholder_inputs:
        try:
            placeholder = (await inp.get_attribute("placeholder") or "").strip()
            if not placeholder:
                continue

            input_type = (await inp.get_attribute("type") or "text").lower()
            if input_type in ("hidden", "submit", "button"):
                continue

            # Ignorar inputs dentro de nav/header/footer
            in_nav = await inp.evaluate(
                "el => !!el.closest('nav, header, footer, [role=navigation]')"
            )
            if in_nav:
                continue

            # Usar el placeholder como label visible
            slug = _slugify(placeholder)
            if slug in seen_ids:
                continue

            # Construir selector robusto
            name = await inp.get_attribute("name") or ""
            id_attr = await inp.get_attribute("id") or ""
            if id_attr:
                selector = f"#{id_attr}"
            elif name:
                selector = f'input[name="{name}"]'
            else:
                selector = f'input[placeholder="{placeholder}"]'

            if selector in seen_selectors:
                continue

            seen_ids.add(slug)
            seen_selectors.add(selector)
            fields.append(FieldInfo(
                id=slug,
                label=placeholder,          # el placeholder es el label visible
                field_type=_map_input_type(input_type),
                selector=selector,
                placeholder=placeholder,
            ))
            print(f"  📌 Campo por placeholder: '{placeholder}'")
        except Exception:
            continue

    # ── Fallback: inputs sin label ni placeholder ─────────────────────────────
    if not fields:
        fields = await _fallback_inputs(page)

    return fields


async def _resolve_field(page: Page, label, label_text: str, slug: str) -> FieldInfo | None:
    """Intenta resolver el tipo de campo y su selector a partir de un label."""

    # 1. Via atributo `for`
    for_attr = None
    try:
        for_attr = await label.get_attribute("for")
    except Exception:
        pass

    if for_attr:
        # Comprobar si es select nativo
        sel_el = page.locator(f"select#{for_attr}:visible")
        if await sel_el.count() > 0:
            options = await _get_select_options(sel_el.first)
            return FieldInfo(
                id=slug, label=label_text, field_type="select",
                selector=f"select#{for_attr}", options=options
            )

        # Input normal
        inp = page.locator(f"#{for_attr}:visible")
        if await inp.count() > 0:
            input_type = (await inp.first.get_attribute("type") or "text").lower()
            placeholder = await inp.first.get_attribute("placeholder") or ""
            ft = _map_input_type(input_type)
            return FieldInfo(
                id=slug, label=label_text, field_type=ft,
                selector=f"#{for_attr}", placeholder=placeholder
            )

    # 2. Input hijo del label
    child_input = label.locator("input:visible, select:visible, textarea:visible").first
    if await child_input.count() > 0:
        tag = await child_input.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            options = await _get_select_options(child_input)
            return FieldInfo(
                id=slug, label=label_text, field_type="select",
                selector=_make_nth_selector(label_text, "select"), options=options
            )
        input_type = (await child_input.get_attribute("type") or "text").lower()
        placeholder = await child_input.get_attribute("placeholder") or ""
        return FieldInfo(
            id=slug, label=label_text, field_type=_map_input_type(input_type),
            selector=_make_nth_selector(label_text, "input"), placeholder=placeholder
        )

    # 3. Detectar dropdowns JS (ng-select, react-select, custom combobox)
    sibling_dropdown = label.locator(
        'xpath=following::*[(@role="combobox" or contains(@class,"select") or contains(@class,"dropdown"))][1]'
    ).first
    if await sibling_dropdown.count() > 0:
        return FieldInfo(
            id=slug, label=label_text, field_type="dropdown",
            selector=f'label:has-text("{label_text}") ~ *[role="combobox"], '
                     f'label:has-text("{label_text}") + *[class*="select"]',
        )

    # 4. Input siguiente hermano
    next_input = label.locator('xpath=following::input[1]').first
    if await next_input.count() > 0:
        input_type = (await next_input.get_attribute("type") or "text").lower()
        if input_type not in ("hidden", "submit", "button"):
            placeholder = await next_input.get_attribute("placeholder") or ""
            name = await next_input.get_attribute("name") or slug
            return FieldInfo(
                id=slug, label=label_text, field_type=_map_input_type(input_type),
                selector=f'input[name="{name}"]', placeholder=placeholder
            )

    return None


async def _get_select_options(sel_locator) -> list[str]:
    try:
        options = await sel_locator.locator("option").all()
        texts = []
        for opt in options:
            t = (await opt.inner_text()).strip()
            if t:
                texts.append(t)
        return texts
    except Exception:
        return []


async def _fallback_inputs(page: Page) -> list[FieldInfo]:
    """Último recurso: recoger todos los inputs visibles sin label ni placeholder."""
    fields = []
    inputs = await page.locator(
        "input:visible:not([type='hidden']):not([type='submit']):not([type='button']), "
        "select:visible, textarea:visible"
    ).all()
    for i, inp in enumerate(inputs):
        try:
            tag = await inp.evaluate("el => el.tagName.toLowerCase()")
            name = await inp.get_attribute("name") or await inp.get_attribute("id") or f"field_{i}"
            placeholder = await inp.get_attribute("placeholder") or ""
            # Usar placeholder como label si está disponible, si no el name
            label = placeholder if placeholder else name
            slug = _slugify(label)
            if tag == "select":
                options = await _get_select_options(inp)
                # Ignorar selectores de idioma también en el fallback
                if _looks_like_lang_selector(options):
                    continue
                fields.append(FieldInfo(id=slug, label=label, field_type="select",
                                        selector=f'[name="{name}"]', options=options))
            else:
                input_type = (await inp.get_attribute("type") or "text").lower()
                fields.append(FieldInfo(id=slug, label=label,
                                        field_type=_map_input_type(input_type),
                                        selector=f'[name="{name}"]', placeholder=placeholder))
        except Exception:
            continue
    return fields


def _map_input_type(input_type: str) -> FieldType:
    mapping = {
        "email": "email",
        "checkbox": "checkbox",
        "radio": "radio",
        "textarea": "textarea",
    }
    return mapping.get(input_type, "text")


def _slugify(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9_]", "_", text.lower().strip())[:40]


def _make_nth_selector(label_text: str, tag: str) -> str:
    return f'label:has-text("{label_text}") {tag}'


async def inspect_form(url: str, timeout_ms: int = 20000) -> list[FieldInfo]:
    """
    Punto de entrada principal.
    Abre la URL, espera el formulario y devuelve los campos detectados.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )
        context = await browser.new_context()
        page = await context.new_page()

        print(f"🔍 Inspeccionando formulario en: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await _accept_cookies(page)
        await _wait_for_form(page, timeout_ms)

        fields = await _extract_fields(page)

        await context.close()
        await browser.close()

    print(f"✅ Detectados {len(fields)} campos: {[f.label for f in fields]}")
    return fields