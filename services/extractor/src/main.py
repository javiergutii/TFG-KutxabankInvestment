import mysql.connector
import os
import time
import re
import json
import subprocess
from playwright.async_api import async_playwright
import asyncio



# DESCARGAR Y OPERAR CON EL VIDEO #

# ==============================
# CONSTANTES / CONFIGURACIÓN
# ==============================
TARGET_URL = "https://urldefense.com/v3/__https:/connectstudio-portal.world-television.com/65830f2debbc4462728ab623/login__;!!Jkho33Y!gSO_GCGNk0DD6REGG_ZEAleWG9bmudogWrHzXFAI8SCNE75OT7zQ7_RBgbjBxJxco1sh12Y_rc-eERNuKJTwhkL3zBX0Rf0$"
TIMEOUT_MS = 45000

M3U8_RE = re.compile(r"\.m3u8(\?|$)", re.I)
MPD_RE  = re.compile(r"\.mpd(\?|$)", re.I)
MP4_RE  = re.compile(r"\.mp4(\?|$)", re.I)

KEYWORDS = ["m3u8", "mpd", "manifest", "master", "playlist", "stream", ".mp4", "dash", "hls", "media"]





# ==============================
# UTILIDADES DE DETECCIÓN (URLS/STREAMS)
# ==============================
def looks_like_stream(u: str) -> bool:
    ul = u.lower()
    return bool(
        M3U8_RE.search(u)
        or MPD_RE.search(u)
        or MP4_RE.search(u)
        or any(k in ul for k in KEYWORDS)
    )


def extract_candidates_from_har(har_path="network.har", limit=200):
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





# ==============================
# DESCARGA CON FFMPEG
# ==============================
def download_with_ffmpeg(url: str, output: str = "output.mp4"):
    print("⬇️ Descargando con ffmpeg…")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", url, "-c", "copy", output],
        check=True
    )
    print("✅ Descarga completada:", output)





# ==============================
# HELPERS UI (CLICK / COOKIES)
# ==============================
async def click_if_exists(page, selectors, timeout=2000):
    for sel in selectors:
        loc = page.locator(sel)
        if await loc.count() > 0:
            try:
                await loc.first.click(timeout=timeout)
                return True
            except Exception:
                pass
    return False


async def accept_cookies(page):
    # OneTrust típicamente usa estos textos/botones
    await click_if_exists(
        page,
        [
            'button:has-text("Accept All")',
            'button:has-text("Aceptar todo")',
            'button#onetrust-accept-btn-handler',
            'button[aria-label*="Accept" i]',
        ],
        timeout=4000
    )





# ========================================
# HELPERS FORMULARIO (INPUTS POR LABEL)
# ========================================
async def fill_text_field_by_label(page, label_text: str, value: str) -> bool:
    # 1) Rellena por label visible exacto
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

    # 2) Fallback
    try:
        inp = page.locator(
            f'label:has-text("{label_text}") >> xpath=following::input[1]'
        ).first
        if await inp.count() > 0:
            await inp.fill(value)
            return True
    except Exception:
        pass

    return False


async def fill_text_field_by_any_label(page, label_texts, value: str) -> bool:
    """
    Intenta rellenar un input usando cualquiera de los labels indicados.
    label_texts puede ser una lista: ["E-mail", "Email"]
    """
    for label_text in label_texts:
        ok = await fill_text_field_by_label(page, label_text, value)
        if ok:
            return True
    return False





# =================================
# WRAPPERS ESPECÍFICOS DE CAMPOS
# =================================
async def fill_first_name(page):
    return await fill_text_field_by_label(page, "First name", "Javier")


async def fill_last_name(page):
    return await fill_text_field_by_label(page, "Last name", "Gutiérrez")


async def fill_email(page):
    return await fill_text_field_by_any_label(
        page,
        ["E-mail", "Email:"],
        "javier.g@opendeusto.es"
    )


async def fill_company(page):
    return await fill_text_field_by_label(page, "Company", "Empresa A")





# ======================================
# HELPERS DESPLEGABLES (DROPDOWN CUSTOM)
# ======================================
async def type_in_dropdown_by_label(page, label_text: str, text: str, max_retries: int = 3) -> bool:

    # localiza label
    label = page.locator(f'label:has-text("{label_text}")').first
    if await label.count() == 0:
        return False

    # sube a un contenedor razonable del campo (ajusta si hiciera falta)
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
        container = label  # último recurso

    async def find_control_in_container():
        selectors = [
            '[role="combobox"]',
            'button',
            'input',
            '[class*="select"]',
            '[class*="dropdown"]',
            '[class*="ng-select"]',
        ]
        for s in selectors:
            loc = container.locator(s).first
            if await loc.count() > 0:
                try:
                    await loc.scroll_into_view_if_needed()
                except Exception:
                    pass
                return loc

        # fallback
        loc2 = label.locator(
            'xpath=following::*[@role="combobox" or self::button or self::input][1]'
        ).first
        if await loc2.count() > 0:
            return loc2
        return None

    async def find_overlay_search_input():
        # inputs típicos cuando el dropdown abre un overlay/portal
        overlay_inputs = page.locator(
            ".cdk-overlay-container input:visible, "
            ".ng-dropdown-panel input:visible, "
            "[role='listbox'] input:visible"
        ).first
        if await overlay_inputs.count() > 0:
            return overlay_inputs
        return None

    for _ in range(max_retries):
        control = await find_control_in_container()
        if control is None:
            return False

        # abre / enfoca el desplegable
        try:
            await control.click(timeout=5000)
        except Exception:
            # a veces el click útil está en un hijo
            try:
                await control.locator(
                    'xpath=.//*[contains(@class,"arrow") or contains(@class,"indicator") or @role="button"]'
                ).first.click(timeout=5000)
            except Exception:
                pass

        # intenta escribir en input del overlay
        ov_inp = await find_overlay_search_input()
        if ov_inp is not None:
            try:
                await ov_inp.fill(text)
                await page.keyboard.press("Enter")
                return True
            except Exception:
                pass

        # si no hay input en overlay, teclea con el teclado
        try:
            await page.keyboard.type(text, delay=40)
            await page.keyboard.press("Enter")
            return True
        except Exception:
            await page.wait_for_timeout(300)

    return False





# ==============================
# SUBMIT / PLAY
# ==============================
async def submit_form(page):
    submit = page.locator('button:has-text("Submit"), button[type="submit"], input[type="submit"]').first
    if await submit.count() == 0:
        return False

    await submit.wait_for(state="visible", timeout=15000)

    # espera habilitado
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


async def click_play_if_any(page):
    return await click_if_exists(
        page,
        [
            ".vjs-big-play-button",
            'button:has-text("Play")',
            '[aria-label*="Play" i]',
            '[title*="Play" i]',
        ],
        timeout=5000
    )





# ==============================
# FUNCIÓN PRINCIPAL (PLAYWRIGHT)
# ==============================
async def run(url: str, timeout_ms: int = 45000):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )

        context = await browser.new_context(
            record_har_path="network.har",
            record_har_content="attach"
        )
        page = await context.new_page()

        found = {"stream": None}

        def on_request(req):
            if found["stream"] is None and looks_like_stream(req.url):
                found["stream"] = req.url
                print("Stream (live):", req.url)

        page.on("request", on_request)

        print("Abriendo Web…")
        await page.goto(url, wait_until="domcontentloaded")

        await accept_cookies(page)

        # Espera al form
        try:
            await page.locator('label:has-text("First name")').first.wait_for(timeout=15000)
        except Exception:
            pass



        # Rellenar campos
        ok_fn   = await fill_first_name(page)
        ok_ln   = await fill_last_name(page)
        ok_em   = await fill_email(page)
        ok_comp = await fill_company(page)

        # Desplegables
        ok_country = await type_in_dropdown_by_label(page, "Country", "sp")
        ok_occ     = await type_in_dropdown_by_label(page, "Occupation", "o")

        print("✅ First name:", ok_fn, "| ✅ Last name:", ok_ln, "| ✅ E-mail:", ok_em, "| ✅ Company:", ok_comp)
        print('✅ Country (type "sp"):', ok_country, ' | ✅ Occupation (type "o"):', ok_occ)

        # Submit
        ok_submit = await submit_form(page)
        print("✅ Submit:", ok_submit)

        await click_play_if_any(page)

        print("Esperando al video")
        await page.wait_for_timeout(timeout_ms)

        await page.screenshot(path="debug.png", full_page=True)
        print("🖼️ Foto debug.png")

        await context.close()
        await browser.close()

    return found["stream"]





# ==============================
# EJECUCIÓN (SCRIPT)
# ==============================
async def main():
    stream_live = await run(TARGET_URL, TIMEOUT_MS)
    print("\nSTREAM live:", stream_live)

    cands = extract_candidates_from_har("network.har", limit=200)
    print("\nCANDIDATAS HAR:")
    for u in cands[:80]:
        print(" -", u)

    # Mejor candidato descargable
    best = None
    for u in ([stream_live] if stream_live else []) + cands:
        if not u:
            continue
        if M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u):
            best = u
            break

    if best:
        print("\n URL final:", best)
        try:
            download_with_ffmpeg(best, "output.mp4")
        except Exception as e:
            print("⚠️ ffmpeg falló (posibles headers/cookies/DRM):", e)
    else:
        print("\n❌ No encontré .m3u8/.mpd/.mp4 directo aún. Revisa debug.png y la lista HAR.")


if __name__ == "__main__":
    asyncio.run(main())





# ==============================
# BBDD
# ==============================
def get_conn():
    return mysql.connector.connect(
        host = os.getenv("MYSQL_HOST", "db"),
        port = int(os.getenv("MYSQL_PORT", "3306")),
        user = os.getenv("MYSQL_USER", "reports_user"),
        password = os.getenv("MYSQL_PASSWORD", "reports_pass"),
        database = os.getenv("MYSQL_DATABASE", "reports"),
    )


for i in range(30):
    
    try:
        conn = get_conn()
        break
    
    except Exception as e:
        print("EXTRACTOR esperando a MySql...")
        time.sleep(2)
else:
    raise SystemExit("MySql no ha arrancado")


# Meter en la bbdd una noticia dummy.
# IMPORTANTE BORRARLA LUEGO

cur = conn.cursor()
cur.execute(
    """
    INSERT INTO reports (empresa, url, texto_transcrito, fecha)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE fetched_at=CURRENT_TIMESTAMP
    """,
    ("demo", "Noticia de prueba", "https://noticia.de/prueba", "Texto transcrito"),
)

conn.commit()
cur.close()
conn.close()

print("EXTRACTOR OK: funciona conexión a MySql e inserción de datos")