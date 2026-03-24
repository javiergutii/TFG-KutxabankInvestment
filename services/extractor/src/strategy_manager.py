"""
StrategyManager: Orquesta las estrategias de scraping y aprende de los éxitos.

Flujo:
1. Extrae el dominio de la URL
2. Si ya existe una estrategia exitosa para ese dominio, la usa directamente
3. Si no, prueba todas las estrategias en orden hasta que una funcione
4. Guarda la estrategia exitosa para futuros usos del mismo dominio
"""
import json
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from config import ARTIFACTS_DIR, HAR_PATH, DEBUG_PNG
from strategies.base import StreamStrategy
from strategies.catalog import STRATEGY_CLASSES


STRATEGIES_DB_PATH = os.path.join(ARTIFACTS_DIR, "strategies.json")


def _load_strategies_db() -> dict:
    """Carga el historial de estrategias exitosas por dominio."""
    if os.path.exists(STRATEGIES_DB_PATH):
        with open(STRATEGIES_DB_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_strategies_db(db: dict):
    """Guarda el historial de estrategias exitosas por dominio."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(STRATEGIES_DB_PATH, "w") as f:
        json.dump(db, f, indent=2)
    print(f"  💾 Estrategia guardada en {STRATEGIES_DB_PATH}")


def _get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def _get_strategy_by_name(name: str) -> type[StreamStrategy] | None:
    for cls in STRATEGY_CLASSES:
        if cls.name == name:
            return cls
    return None


class StrategyManager:
    """
    Gestiona la selección y ejecución de estrategias de scraping.
    Aprende de los éxitos pasados guardando qué estrategia funcionó
    para cada dominio.
    """

    def __init__(self, form_data: dict, timeout_ms: int = 45000):
        """
        Args:
            form_data: Datos del formulario (first_name, last_name, email, etc.)
            timeout_ms: Timeout de espera de red por estrategia
        """
        self.form_data = form_data
        self.timeout_ms = timeout_ms
        self.strategies_db = _load_strategies_db()

    async def find_stream(self, url: str) -> str | None:
        """
        Encuentra la URL del stream para la URL dada.
        Prueba estrategias en orden inteligente y guarda el resultado.

        Args:
            url: URL de la conferencia/webcast

        Returns:
            URL del stream (.m3u8, .mpd, .mp4) o None si no se encuentra
        """
        domain = _get_domain(url)
        print(f"\n🌐 Dominio: {domain}")

        # Determinar el orden de estrategias a probar
        strategies_to_try = self._get_ordered_strategies(domain)

        os.makedirs(ARTIFACTS_DIR, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"]
            )
            context = await browser.new_context(
                record_har_path=HAR_PATH,
                record_har_content="attach"
            )
            page = await context.new_page()

            stream_url = None

            for strategy_cls in strategies_to_try:
                strategy = strategy_cls(self.form_data)
                print(f"\n📋 Probando estrategia: [{strategy.name}]")

                result = None
                try:
                    result = await strategy.execute(page, url, self.timeout_ms)

                    if result:
                        print(f"\n✅ Estrategia [{strategy.name}] exitosa!")
                        stream_url = result
                        # Guardar para el futuro
                        self._record_success(domain, strategy.name, url)
                        break
                    else:
                        print(f"  ↩️  [{strategy.name}] no encontró stream")

                except Exception as e:
                    print(f"  ❌ [{strategy.name}] error: {e}")

                # Si no funcionó, recargar la página para la siguiente estrategia
                if not result and strategy_cls != strategies_to_try[-1]:
                    try:
                        await page.goto("about:blank")
                    except Exception:
                        pass

            # Screenshot de debug siempre
            try:
                await page.screenshot(path=DEBUG_PNG, full_page=True)
                print(f"\n🖼️  Screenshot guardado: {DEBUG_PNG}")
            except Exception:
                pass

            await context.close()
            await browser.close()

        return stream_url

    def _get_ordered_strategies(self, domain: str) -> list[type[StreamStrategy]]:
        """
        Devuelve las estrategias en orden de prioridad.
        Si hay historial para el dominio, esa estrategia va primero.
        """
        known_strategy_name = self.strategies_db.get(domain, {}).get("strategy")
        
        if known_strategy_name:
            known_cls = _get_strategy_by_name(known_strategy_name)
            if known_cls:
                print(f"  📚 Historial: [{known_strategy_name}] funcionó antes para {domain}")
                # Mover la estrategia conocida al principio
                rest = [cls for cls in STRATEGY_CLASSES if cls.name != known_strategy_name]
                return [known_cls] + rest

        print(f"  🔍 Dominio nuevo, probando todas las estrategias...")
        return list(STRATEGY_CLASSES)

    def _record_success(self, domain: str, strategy_name: str, url: str):
        """Guarda la estrategia exitosa para el dominio."""
        from datetime import datetime
        self.strategies_db[domain] = {
            "strategy": strategy_name,
            "last_url": url,
            "last_success": datetime.now().isoformat(),
        }
        _save_strategies_db(self.strategies_db)

    def get_domain_stats(self) -> dict:
        """Devuelve estadísticas del historial de estrategias."""
        return {
            "total_domains": len(self.strategies_db),
            "domains": {
                domain: data.get("strategy")
                for domain, data in self.strategies_db.items()
            }
        }