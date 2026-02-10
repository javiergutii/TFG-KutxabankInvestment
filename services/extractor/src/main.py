import asyncio

from db import wait_for_mysql, insert_report, save_transcription_to_file
from scraping import find_stream_url, extract_candidates_from_har, choose_best_stream
from video import download_with_ffmpeg, extract_audio, transcribe
from config import (
    TARGET_URL, TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, EMPRESA, FECHA, HAR_PATH,
    SHAREPOINT_ENABLED
)

# Importar SharePoint solo si está habilitado
if SHAREPOINT_ENABLED:
    from sharepoint_uploader import create_uploader_from_env


async def main():
    wait_for_mysql()

    # 1) detectar stream
    stream_live = await find_stream_url(TARGET_URL, TIMEOUT_MS)
    print("\nSTREAM live:", stream_live)

    cands = extract_candidates_from_har(HAR_PATH, limit=200)
    best = choose_best_stream(stream_live, cands)
    if not best:
        raise SystemExit("❌ No se ha encontrado URL .m3u8/.mpd/.mp4. Mirar debug.png")

    print("\n✅ URL final:", best)

    # 2) descargar video
    download_with_ffmpeg(best, VIDEO_FILE)

    # 3) audio y transcripción
    extract_audio(VIDEO_FILE, AUDIO_FILE)
    texto_final = transcribe(AUDIO_FILE)

    print("\n--------- TEXTO ---------")
    print(texto_final[:2000])

    # 4) mysql (tu insert_report debe hacer UPSERT por empresa)
    insert_report(texto_final, TARGET_URL, EMPRESA)

    # 5) Guardar transcripción en archivo .txt
    filepath = save_transcription_to_file(texto_final, EMPRESA)
    
    # 6) Subir a SharePoint si está habilitado
    if SHAREPOINT_ENABLED:
        try:
            print("\n[SharePoint] Iniciando subida...")
            uploader = create_uploader_from_env()
            
            resultado = uploader.upload_file(
                file_path=filepath,
                sharepoint_folder=None,  # Usa la carpeta configurada en SHAREPOINT_FOLDER
                file_name=None  # Usa el nombre original del archivo
            )
            
            print(f"[SharePoint] ✅ Archivo subido exitosamente")
            print(f"[SharePoint] Nombre: {resultado.get('name', 'N/A')}")
            print(f"[SharePoint] URL: {resultado.get('webUrl', 'N/A')}")
            
        except Exception as e:
            print(f"[SharePoint] ❌ Error al subir archivo: {e}")
            print("[SharePoint] La transcripción está guardada localmente pero no se pudo subir a SharePoint")
            # No detenemos el proceso, solo reportamos el error
    else:
        print("\n[SharePoint] Deshabilitado (SHAREPOINT_ENABLED=false)")
        print(f"[SharePoint] Archivo disponible localmente en: {filepath}")


if __name__ == "__main__":
    asyncio.run(main())