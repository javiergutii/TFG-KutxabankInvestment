import os
import re
import json
import time
import asyncio
import subprocess
from datetime import datetime

import mysql.connector
from playwright.async_api import async_playwright
from faster_whisper import WhisperModel


# =========================
# Config por variables de entorno
# =========================
TARGET_URL = os.getenv("TARGET_URL", "https://edge.media-server.com/mmc/p/namtxtbr/")
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "45000"))

VIDEO_FILE = os.getenv("VIDEO_FILE", "output.mp4")
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio.wav")

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# Form (evita hardcodear tus datos personales en el repo)
FORM_FIRST_NAME = os.getenv("FORM_FIRST_NAME", "Javier")
FORM_LAST_NAME = os.getenv("FORM_LAST_NAME", "Gutiérrez")
FORM_EMAIL = os.getenv("FORM_EMAIL", "javier.g@opendeusto.es")
FORM_COMPANY = os.getenv("FORM_COMPANY", "Empresa A")
FORM_COUNTRY_TEXT = os.getenv("FORM_COUNTRY_TEXT", "sp")
FORM_OCCUPATION_TEXT = os.getenv("FORM_OCCUPATION_TEXT", "o")

# MySQL (en docker-compose el host suele ser el nombre del servicio: db)
MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")

# Metadata para insertar
EMPRESA = os.getenv("EMPRESA", "Telefónica")
FECHA = os.getenv("FECHA", "")  # opcional; si viene vacío usamos now()


# =========================
# Detección de streams
# =========================
M3U8_RE = re.compile(r"\.m3u8(\?|$)", re.I)
MPD_RE  = re.compile(r"\.mpd(\?|$)", re.I)
MP4_RE  = re.compile(r"\.mp4(\?|$)", re.I)
KEYWORDS = ["m3u8", "mpd", "manifest", "master", "playlist", "stream", ".mp4", "dash", "hls", "media"]

def looks_like_stream(u: str) -> bool:
    ul = (u or "").lower()
    return bool(M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u) or any(k in ul for k in KEYWORDS))

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

def choose_best_stream(stream_live, cands):
    for u in ([stream_live] if stream_live else []) + (cands or []):
        if not u:
            continue
        if M3U8_RE.search(u) or MPD_RE.search(u) or MP4_RE.search(u):
            return u
    return None


# =========================
# Playwright helpers (adaptados del notebook)
# =========================
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
    await click_if_exists(page, [
        'button:has-text("Accept All")',
        'button:has-text("Aceptar todo")',
        'button#onetrust-accept-btn-handler',
        'button[aria-label*="Accept" i]',
    ], timeout=4000)

async def fill_text_field_by_label(page, label_text: str, value: str) -> bool:
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

async def fill_text_field_by_any_label(page, label_texts, value: str) -> bool:
    for label_text in label_texts:
        ok = await fill_text_field_by_label(page, label_text, value)
        if ok:
            return True
    return False

async def type_in_dropdown_by_label(page, label_text: str, text: str, max_retries: int = 3) -> bool:
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
        loc2 = label.locator('xpath=following::*[@role="combobox" or self::button or self::input][1]').first
        if await loc2.count() > 0:
            return loc2
        return None

    async def find_overlay_search_input():
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

        try:
            await control.click(timeout=5000)
        except Exception:
            try:
                await control.locator(
                    'xpath=.//*[contains(@class,"arrow") or contains(@class,"indicator") or @role="button"]'
                ).first.click(timeout=5000)
            except Exception:
                pass

        ov_inp = await find_overlay_search_input()
        if ov_inp is not None:
            try:
                await ov_inp.fill(text)
                await page.keyboard.press("Enter")
                return True
            except Exception:
                pass

        try:
            await page.keyboard.type(text, delay=40)
            await page.keyboard.press("Enter")
            return True
        except Exception:
            await page.wait_for_timeout(300)

    return False

async def submit_form(page):
    submit = page.locator('button:has-text("Submit"), button[type="submit"], input[type="submit"]').first
    if await submit.count() == 0:
        return False

    await submit.wait_for(state="visible", timeout=15000)

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
    return await click_if_exists(page, [
        ".vjs-big-play-button",
        'button:has-text("Play")',
        '[aria-label*="Play" i]',
        '[title*="Play" i]',
    ], timeout=5000)

async def find_stream_url(url: str, timeout_ms: int = 45000) -> str | None:
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
                print("🎯 Stream (live):", req.url)

        page.on("request", on_request)

        print("🌐 Abriendo…", url)
        await page.goto(url, wait_until="domcontentloaded")

        await accept_cookies(page)

        # Espera (suave) a que cargue el form
        try:
            await page.locator('label:has-text("First name")').first.wait_for(timeout=15000)
        except Exception:
            pass

        # Rellenar
        ok_fn = await fill_text_field_by_label(page, "First name", FORM_FIRST_NAME)
        ok_ln = await fill_text_field_by_label(page, "Last name", FORM_LAST_NAME)
        ok_em = await fill_text_field_by_any_label(page, ["E-mail", "Email:"], FORM_EMAIL)
        ok_co = await fill_text_field_by_label(page, "Company", FORM_COMPANY)

        ok_country = await type_in_dropdown_by_label(page, "Country", FORM_COUNTRY_TEXT)
        ok_occ = await type_in_dropdown_by_label(page, "Occupation", FORM_OCCUPATION_TEXT)

        print("✅ First/Last/Email/Company:", ok_fn, ok_ln, ok_em, ok_co)
        print("✅ Country/Occupation:", ok_country, ok_occ)

        ok_submit = await submit_form(page)
        print("✅ Submit:", ok_submit)

        await click_play_if_any(page)

        print("⏳ Esperando tráfico…")
        await page.wait_for_timeout(timeout_ms)

        await page.screenshot(path="debug.png", full_page=True)
        print("🖼️ Guardé debug.png")

        await context.close()
        await browser.close()

    return found["stream"]


# =========================
# Multimedia
# =========================
def download_with_ffmpeg(url: str, output: str):
    print("⬇️ Descargando con ffmpeg…")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", url, "-c", "copy", output], check=True)
    print("✅ Descarga completada:", output)

def extract_audio(video_file: str, audio_file: str):
    print("🎧 Extrayendo audio…")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        audio_file
    ]
    subprocess.run(cmd, check=True)
    print("✅ Audio listo:", audio_file)

def transcribe(audio_file: str) -> str:
    print("🧠 Cargando modelo Whisper…")
    model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)

    print("📝 Transcribiendo…")
    segments, info = model.transcribe(
        audio_file,
        task="transcribe",
        language=None,
        temperature=0.0,
        beam_size=5,
        vad_filter=True,
        initial_prompt="The speech may contain in both english and spanish sentences. Focus on the enterprises names.",
    )

    out = []
    for s in segments:
        out.append(s.text.strip())
    text = "\n".join([t for t in out if t])
    return text


# =========================
# MySQL
# =========================
def mysql_conn(db: str | None = None):
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=db or MYSQL_DB,
    )

def wait_for_mysql(max_tries=30, sleep_s=2):
    for i in range(max_tries):
        try:
            c = mysql_conn()
            c.close()
            print("[app] MySQL OK")
            return
        except Exception as e:
            print(f"[app] esperando MySQL... ({i+1}/{max_tries}) {e}")
            time.sleep(sleep_s)
    raise SystemExit("MySQL no arrancó a tiempo")

def insert_report(texto: str, url: str):
    conn = mysql_conn()
    cur = conn.cursor()

    fecha_val = datetime.now() if not FECHA else datetime.fromisoformat(FECHA)

    cur.execute(
        """
        INSERT INTO reports (empresa, url, texto_transcrito, fecha)
        VALUES (%s, %s, %s, %s)
        """,
        (EMPRESA, url, texto, fecha_val)
    )
    conn.commit()
    cur.close()
    conn.close()
    print("[app] Insertado en reports ✅")


# =========================
# Main
# =========================
def main():
    wait_for_mysql()

    # 1) detectar stream
    stream_live = asyncio.run(find_stream_url(TARGET_URL, TIMEOUT_MS))
    print("\nSTREAM live:", stream_live)

    cands = extract_candidates_from_har("network.har", limit=200)
    best = choose_best_stream(stream_live, cands)
    if not best:
        raise SystemExit("❌ No encontré URL .m3u8/.mpd/.mp4. Revisa debug.png y network.har")

    print("\n✅ URL final:", best)

    # 2) descargar
    download_with_ffmpeg(best, VIDEO_FILE)

    # 3) audio + transcripción
    extract_audio(VIDEO_FILE, AUDIO_FILE)
    texto_final = transcribe(AUDIO_FILE)

    print("\n--------- TEXTO ---------")
    print(texto_final[:2000] + ("\n...(truncado)" if len(texto_final) > 2000 else ""))

    # 4) guardar en mysql
    insert_report(texto_final, TARGET_URL)


if __name__ == "__main__":
    main()
