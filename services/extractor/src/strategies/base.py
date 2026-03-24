"""
Clase base para las estrategias de extracción de streams.
Cada estrategia encapsula un flujo de interacción diferente con la web.
"""
from abc import ABC, abstractmethod
from playwright.async_api import Page
import re

M3U8_RE = re.compile(r"\.m3u8(\?|$)", re.I)
MPD_RE  = re.compile(r"\.mpd(\?|$)", re.I)
MP4_RE  = re.compile(r"\.mp4(\?|$)", re.I)
KEYWORDS = ["m3u8", "mpd", "master", "playlist", ".mp4", "dash", "hls"]

def looks_like_stream(u: str) -> bool:
    if not u:
        return False
    if M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u):
        return True
    from urllib.parse import urlparse
    path = urlparse(u).path.lower()
    query = urlparse(u).query.lower()
    return any(k in path or k in query for k in KEYWORDS)


class StreamStrategy(ABC):
    """
    Clase base para las estrategias de extracción.
    Cada subclase implementa un flujo diferente de interacción.
    """
    name: str = "base"

    def __init__(self, form_data: dict):
        """
        Args:
            form_data: Diccionario con los datos del formulario
                       (first_name, last_name, email, company, country_text, occupation_text)
        """
        self.form_data = form_data
        self.found_stream = None

    def _attach_listener(self, page: Page):
        """Adjunta el listener de red para capturar streams en tiempo real."""
        def on_request(req):
            if self.found_stream is None and looks_like_stream(req.url):
                self.found_stream = req.url
                print(f"  🎯 Stream detectado (live): {req.url[:80]}...")
        page.on("request", on_request)

    @abstractmethod
    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        """
        Ejecuta la estrategia de scraping.

        Args:
            page: Página de Playwright
            url: URL objetivo
            timeout_ms: Timeout en milisegundos para esperar tráfico de red

        Returns:
            URL del stream encontrado o None si falla
        """
        pass

    # ------------------------------------------------------------------ #
    #  Helpers reutilizables por todas las estrategias                    #
    # ------------------------------------------------------------------ #

    async def _accept_cookies(self, page: Page):
        selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Aceptar todo")',
            'button#onetrust-accept-btn-handler',
            'button[aria-label*="Accept" i]',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Accept")',
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                try:
                    await loc.first.click(timeout=4000)
                    print("  🍪 Cookies aceptadas")
                    return
                except Exception:
                    pass

    async def _fill_text_field_by_label(self, page: Page, label_text: str, value: str) -> bool:
        label = page.locator(f'label:has-text("{label_text}")').first
        if await label.count() > 0:
            try:
                for_attr = await label.get_attribute("for")
                if for_attr:
                    inp = page.locator(f"#{for_attr}")
                    if await inp.count() > 0:
                        await inp.fill(value)
                        return True
            except Exception:
                pass
        try:
            inp = page.locator(f'label:has-text("{label_text}") >> xpath=following::input[1]').first
            if await inp.count() > 0:
                await inp.fill(value)
                return True
        except Exception:
            pass
        return False

    async def _fill_text_field_by_any_label(self, page: Page, label_texts: list, value: str) -> bool:
        for label_text in label_texts:
            ok = await self._fill_text_field_by_label(page, label_text, value)
            if ok:
                return True
        return False

    async def _type_in_dropdown_by_label(self, page: Page, label_text: str, text: str) -> bool:
        label = page.locator(f'label:has-text("{label_text}")').first
        if await label.count() == 0:
            return False

        container_candidates = [
            "xpath=ancestor::*[self::div or self::section][.//label][1]",
            "xpath=ancestor::*[contains(@class,'form-group')][1]",
            "xpath=ancestor::*[contains(@class,'form-row')][1]",
            "xpath=ancestor::*[contains(@class,'field')][1]",
        ]
        container = None
        for cc in container_candidates:
            c = label.locator(cc)
            if await c.count() > 0:
                container = c.first
                break
        if container is None:
            container = label

        selectors = [
            '[role="combobox"]', 'button', 'input',
            '[class*="select"]', '[class*="dropdown"]', '[class*="ng-select"]',
        ]
        for s in selectors:
            loc = container.locator(s).first
            if await loc.count() > 0:
                try:
                    await loc.click(timeout=5000)
                    overlay_inp = page.locator(
                        ".cdk-overlay-container input:visible, "
                        ".ng-dropdown-panel input:visible, "
                        "[role='listbox'] input:visible"
                    ).first
                    if await overlay_inp.count() > 0:
                        await overlay_inp.fill(text)
                        await page.keyboard.press("Enter")
                    else:
                        await page.keyboard.type(text, delay=40)
                        await page.keyboard.press("Enter")
                    return True
                except Exception:
                    pass
        return False

    async def _fill_form(self, page: Page):
        """Rellena los campos del formulario con los datos disponibles."""
        fd = self.form_data
        results = {}
        results["first_name"] = await self._fill_text_field_by_label(page, "First name", fd.get("first_name", ""))
        results["last_name"]  = await self._fill_text_field_by_label(page, "Last name",  fd.get("last_name", ""))
        results["email"]      = await self._fill_text_field_by_any_label(page, ["E-mail", "Email:", "Email"], fd.get("email", ""))
        results["company"]    = await self._fill_text_field_by_label(page, "Company", fd.get("company", ""))
        results["country"]    = await self._type_in_dropdown_by_label(page, "Country",     fd.get("country_text", ""))
        results["occupation"] = await self._type_in_dropdown_by_label(page, "Occupation",  fd.get("occupation_text", ""))
        filled = [k for k, v in results.items() if v]
        print(f"  📝 Campos rellenados: {filled}")
        return any(results.values())

    async def _submit_form(self, page: Page) -> bool:
        submit = page.locator('button:has-text("Submit"), button[type="submit"], input[type="submit"]').first
        if await submit.count() == 0:
            return False
        try:
            await submit.wait_for(state="visible", timeout=15000)
            for _ in range(40):
                aria = await submit.get_attribute("aria-disabled")
                disabled = await submit.get_attribute("disabled")
                if aria in (None, "false") and disabled is None:
                    break
                await page.wait_for_timeout(250)
            await submit.click(timeout=15000)
            return True
        except Exception:
            return False

    async def _click_play(self, page: Page):
        selectors = [
            ".vjs-big-play-button",
            'button:has-text("Play")',
            '[aria-label*="Play" i]',
            '[title*="Play" i]',
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                try:
                    await loc.first.click(timeout=5000)
                    return True
                except Exception:
                    pass
        return False

    async def _wait_for_login_form(self, page: Page):
        """Espera a que aparezca un formulario de login."""
        login_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[autocomplete="current-password"]',
        ]
        for sel in login_selectors:
            try:
                await page.locator(sel).first.wait_for(state="visible", timeout=8000)
                return True
            except Exception:
                pass
        return False

    async def _fill_login(self, page: Page) -> bool:
        """Rellena el formulario de login con email y envía."""
        email = self.form_data.get("email", "")
        try:
            # Intentar rellenar campo de email/username
            for sel in ['input[type="email"]', 'input[name="email"]', 'input[name="username"]', 'input[type="text"]']:
                inp = page.locator(sel).first
                if await inp.count() > 0:
                    await inp.fill(email)
                    break

            # Intentar rellenar contraseña si existe
            pwd_inp = page.locator('input[type="password"]').first
            if await pwd_inp.count() > 0:
                password = self.form_data.get("password", "")
                if password:
                    await pwd_inp.fill(password)

            # Submit
            await self._submit_form(page)
            return True
        except Exception as e:
            print(f"  ⚠️  Error en login: {e}")
            return False
    
    def _on_request(self, req):
        if self.found_stream is None and looks_like_stream(req.url):
            self.found_stream = req.url
            print(f"  🎯 Stream detectado (iframe): {req.url[:80]}...")
    
    def _attach_listener(self, page: Page):
        page.on("request", self._on_request)