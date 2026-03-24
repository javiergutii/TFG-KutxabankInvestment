"""
Catálogo de estrategias concretas.
Cada clase implementa un flujo diferente de interacción con la web.

Para añadir una nueva estrategia:
  1. Crea una clase que herede de StreamStrategy
  2. Implementa el método execute()
  3. Regístrala en STRATEGY_CLASSES al final del archivo
"""
import json
import os
from playwright.async_api import Page

from strategies.base import StreamStrategy


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 1: Stream directo (sin login ni formulario)
# ──────────────────────────────────────────────────────────────────────────────
class DirectStreamStrategy(StreamStrategy):
    """
    La web carga el stream directamente, sin login ni formulario previo.
    Ej: webcast público, reproductores embebidos.
    """
    name = "direct_stream"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [DirectStream] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)
        await self._click_play(page)

        print(f"  [DirectStream] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 2: Formulario → Stream
# ──────────────────────────────────────────────────────────────────────────────
class FormFirstStrategy(StreamStrategy):
    """
    La web muestra primero un formulario de registro, y tras enviarlo
    aparece el reproductor con el stream.
    Ej: webcasts de resultados de Telefónica, BBVA, Inditex...
    """
    name = "form_first"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [FormFirst] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

        # Esperar a que aparezca el formulario
        try:
            await page.locator('label:has-text("First name"), label:has-text("Email")').first.wait_for(timeout=15000)
            print("  [FormFirst] Formulario detectado")
        except Exception:
            print("  [FormFirst] ⚠️  No se detectó formulario estándar, intentando igualmente...")

        await self._fill_form(page)
        ok = await self._submit_form(page)
        print(f"  [FormFirst] Submit: {ok}")

        await self._click_play(page)

        print(f"  [FormFirst] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 3: Login → Formulario → Stream
# ──────────────────────────────────────────────────────────────────────────────
class LoginThenFormStrategy(StreamStrategy):
    """
    La web pide primero login, luego un formulario de registro
    y finalmente muestra el stream.
    """
    name = "login_then_form"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [LoginThenForm] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

        # Paso 1: Login
        has_login = await self._wait_for_login_form(page)
        if has_login:
            print("  [LoginThenForm] Login detectado, rellenando...")
            await self._fill_login(page)
            await page.wait_for_load_state("networkidle", timeout=15000)
        else:
            print("  [LoginThenForm] ⚠️  No se detectó login")

        # Paso 2: Formulario de registro
        try:
            await page.locator('label:has-text("First name"), label:has-text("Email")').first.wait_for(timeout=12000)
            await self._fill_form(page)
            await self._submit_form(page)
            print("  [LoginThenForm] Formulario enviado")
        except Exception:
            print("  [LoginThenForm] ⚠️  No se encontró formulario tras login")

        await self._click_play(page)

        print(f"  [LoginThenForm] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 4: Formulario → Login → Stream
# ──────────────────────────────────────────────────────────────────────────────
class FormThenLoginStrategy(StreamStrategy):
    """
    La web muestra primero un formulario de registro y luego
    redirige a una pantalla de login antes de mostrar el stream.
    """
    name = "form_then_login"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [FormThenLogin] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

        # Paso 1: Formulario
        try:
            await page.locator('label:has-text("First name"), label:has-text("Email")').first.wait_for(timeout=12000)
            await self._fill_form(page)
            await self._submit_form(page)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("  [FormThenLogin] Formulario enviado")
        except Exception:
            print("  [FormThenLogin] ⚠️  No se encontró formulario inicial")

        # Paso 2: Login si aparece tras el formulario
        has_login = await self._wait_for_login_form(page)
        if has_login:
            print("  [FormThenLogin] Login detectado tras formulario")
            await self._fill_login(page)
            await page.wait_for_load_state("networkidle", timeout=12000)

        await self._click_play(page)

        print(f"  [FormThenLogin] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 5: Navegar + extraer link → abrir video
# ──────────────────────────────────────────────────────────────────────────────
class NavigateThenStreamStrategy(StreamStrategy):
    """
    La web tiene una lista de eventos/webcasts y hay que navegar
    hasta el vídeo correcto antes de hacer login/formulario.
    Utiliza un prompt simple para encontrar el link del vídeo.
    """
    name = "navigate_then_stream"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [NavigateThenStream] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

        # Buscar links que parezcan webcasts/eventos/earnings
        event_keywords = ["webcast", "earnings", "results", "investor", "conference", "event", "live", "replay"]
        for kw in event_keywords:
            links = page.locator(f'a:has-text("{kw}")')
            count = await links.count()
            if count > 0:
                try:
                    print(f"  [NavigateThenStream] Encontrado link con '{kw}', haciendo click...")
                    await links.first.click(timeout=5000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    break
                except Exception:
                    pass

        # Tras la navegación intentar estrategia FormFirst
        form_strategy = FormFirstStrategy(self.form_data)
        form_strategy.found_stream = self.found_stream
        form_strategy._attach_listener(page)

        try:
            await page.locator('label:has-text("First name"), label:has-text("Email")').first.wait_for(timeout=10000)
            await form_strategy._fill_form(page)
            await form_strategy._submit_form(page)
        except Exception:
            pass

        await self._click_play(page)

        print(f"  [NavigateThenStream] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return form_strategy.found_stream or self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 6: Agente LLM (fallback)
# ──────────────────────────────────────────────────────────────────────────────
class LLMAgentStrategy(StreamStrategy):
    """
    Fallback inteligente: usa un LLM (Groq) para analizar el DOM
    y decidir qué acciones tomar. Se activa cuando todas las demás fallan.

    Requiere: GROQ_API_KEY en variables de entorno.
    """
    name = "llm_agent"

    MAX_STEPS = 8  # Máximo de pasos que puede dar el agente

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        import os
        import requests

        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            print("  [LLMAgent] ⚠️  Sin GROQ_API_KEY, saltando...")
            return None

        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        print(f"  [LLMAgent] Iniciando agente LLM para {url[:60]}...")
        self._attach_listener(page)
        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

        form_data_str = json.dumps({
            "first_name": self.form_data.get("first_name", ""),
            "last_name": self.form_data.get("last_name", ""),
            "email": self.form_data.get("email", ""),
            "company": self.form_data.get("company", ""),
        })

        for step in range(self.MAX_STEPS):
            if self.found_stream:
                print(f"  [LLMAgent] Stream encontrado en paso {step}")
                break

            # Capturar estado actual de la página
            page_text = await page.evaluate("() => document.body.innerText.slice(0, 3000)")
            page_url  = page.url
            buttons   = await page.evaluate("""
                () => Array.from(document.querySelectorAll('button, input[type=submit]'))
                         .slice(0, 10)
                         .map(b => b.innerText || b.value || b.type)
            """)
            inputs = await page.evaluate("""
                () => Array.from(document.querySelectorAll('input:not([type=hidden]), select'))
                         .slice(0, 10)
                         .map(i => ({type: i.type, name: i.name, placeholder: i.placeholder, label: i.labels?.[0]?.innerText}))
            """)

            prompt = f"""Eres un asistente que ayuda a navegar webs de resultados empresariales para encontrar un stream de vídeo (.m3u8, .mpd, .mp4).

URL actual: {page_url}
Texto visible en la página (primeros 3000 chars):
{page_text}

Botones disponibles: {buttons}
Inputs disponibles: {inputs}

Datos del formulario a usar si se necesitan:
{form_data_str}

Tu tarea: Decide la ÚNICA acción más útil para avanzar hacia encontrar el stream de vídeo.
Responde SÓLO con un JSON en este formato exacto (sin markdown, sin explicación):
{{
  "action": "click" | "fill" | "submit" | "wait" | "done",
  "selector": "selector CSS del elemento",
  "value": "valor a introducir (sólo para fill)",
  "reason": "explicación corta en español"
}}

Si la página ya muestra un reproductor de vídeo o el stream ya debería estar cargado, usa action="wait".
Si no hay nada más que hacer, usa action="done".
"""
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                # Limpiar posibles bloques markdown
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                action_data = json.loads(raw)
            except Exception as e:
                print(f"  [LLMAgent] Error consultando LLM: {e}")
                break

            action = action_data.get("action", "done")
            selector = action_data.get("selector", "")
            value = action_data.get("value", "")
            reason = action_data.get("reason", "")

            print(f"  [LLMAgent] Paso {step+1}: {action} | {reason}")

            try:
                if action == "click" and selector:
                    await page.locator(selector).first.click(timeout=8000)
                    await page.wait_for_load_state("networkidle", timeout=10000)

                elif action == "fill" and selector and value:
                    await page.locator(selector).first.fill(value)

                elif action == "submit":
                    if selector:
                        await page.locator(selector).first.click(timeout=8000)
                    else:
                        await self._submit_form(page)
                    await page.wait_for_load_state("networkidle", timeout=10000)

                elif action == "wait":
                    await page.wait_for_timeout(min(timeout_ms, 15000))

                elif action == "done":
                    break

            except Exception as e:
                print(f"  [LLMAgent] Error ejecutando acción: {e}")
                await page.wait_for_timeout(2000)

        # Espera final por si el stream llega con retraso
        if not self.found_stream:
            await page.wait_for_timeout(min(timeout_ms, 20000))

        return self.found_stream
    
# ──────────────────────────────────────────────────────────────────────────────
# Estrategia 7: Email only
# ──────────────────────────────────────────────────────────────────────────────
class EmailOnlyFormStrategy(StreamStrategy):
    """
    La web solo pide email para registrarse, sin más campos.
    Ej: world-television.com (Tubacex, etc.)
    """
    name = "email_only_form"

    async def execute(self, page: Page, url: str, timeout_ms: int) -> str | None:
        print(f"  [EmailOnlyForm] Navegando a {url[:60]}...")
        self._attach_listener(page)

        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)
        await page.wait_for_timeout(3000)  # dar tiempo a que carguen los iframes

        email = self.form_data.get("email", "")
        filled = False

        # Buscar primero en la página principal
        for sel in ['input[type="email"]', 'input[placeholder*="email" i]', 'input[id="email"]']:
            inp = page.locator(sel).first
            if await inp.count() > 0:
                await inp.fill(email)
                filled = True
                print(f"  [EmailOnlyForm] Email rellenado (página principal)")
                break

        # Si no, buscar dentro de cada iframe
        if not filled:
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                for sel in ['input[type="email"]', 'input[placeholder*="email" i]', 'input[id="email"]']:
                    try:
                        inp = frame.locator(sel).first
                        if await inp.count() > 0:
                            await inp.fill(email)
                            filled = True
                            print(f"  [EmailOnlyForm] Email rellenado (iframe: {frame.url[:60]})")
                            # También adjuntar listener al frame
                            frame.on("request", lambda req: self._on_request(req))
                            break
                    except Exception:
                        pass
                if filled:
                    break

        if not filled:
            print("  [EmailOnlyForm] ⚠️  No se encontró campo de email")
            return None

        # Submit — intentar en página principal y en iframes
        ok = await self._submit_form(page)
        if not ok:
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                try:
                    submit = frame.locator('button:has-text("Submit"), button[type="submit"], input[type="submit"]').first
                    if await submit.count() > 0:
                        await submit.click(timeout=10000)
                        ok = True
                        print(f"  [EmailOnlyForm] Submit en iframe")
                        break
                except Exception:
                    pass

        print(f"  [EmailOnlyForm] Submit: {ok}")
        await self._click_play(page)

        print(f"  [EmailOnlyForm] Esperando tráfico ({timeout_ms}ms)...")
        await page.wait_for_timeout(timeout_ms)
        return self.found_stream


# ──────────────────────────────────────────────────────────────────────────────
# Registro de estrategias (orden de prueba cuando no hay historial)
# ──────────────────────────────────────────────────────────────────────────────
STRATEGY_CLASSES = [
    DirectStreamStrategy,
    FormFirstStrategy,
    EmailOnlyFormStrategy,
    LoginThenFormStrategy,
    FormThenLoginStrategy,
    NavigateThenStreamStrategy,
    LLMAgentStrategy,          # Siempre el último
]