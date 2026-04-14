"""
api.py — Endpoints REST del backend con validación de token Microsoft.

Reemplaza a form_server.py como punto de entrada HTTP.
El extractor ya no se lanza como script standalone sino como API.
"""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from auth import verify_token, TokenData
from db import wait_for_mysql, insert_report
from config import SHAREPOINT_ENABLED

app = FastAPI(title="Transcriptor API", version="1.0.0")

# ── CORS — permite llamadas desde el frontend React ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Jobs en memoria (en producción se puede mover a una tabla MySQL)
_jobs: dict[str, dict] = {}


# ── Modelos ───────────────────────────────────────────────────────────────────

class LaunchJobRequest(BaseModel):
    url: str
    empresa: str
    form_data: dict = {}


class JobResponse(BaseModel):
    id: str
    url: str
    empresa: str
    status: str
    created_at: str
    user_name: Optional[str] = None
    sharepoint_url: Optional[str] = None
    resumen: Optional[str] = None
    error_msg: Optional[str] = None


# ── Auth helper ───────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    token = credentials.credentials
    user = await verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/me")
async def get_me(user: TokenData = Depends(get_current_user)):
    return {"name": user.name, "email": user.email, "user_id": user.user_id}


@app.post("/api/jobs", response_model=JobResponse)
async def launch_job(
    request: LaunchJobRequest,
    user: TokenData = Depends(get_current_user),
):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "url": request.url,
        "empresa": request.empresa,
        "form_data": request.form_data,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "user_name": user.name,
        "user_email": user.email,
        "user_token": user.access_token,
        "sharepoint_url": None,
        "resumen": None,
        "error_msg": None,
    }
    _jobs[job_id] = job

    # Lanzar proceso en background sin bloquear la respuesta
    asyncio.create_task(_run_job(job_id))

    return JobResponse(**{k: v for k, v in job.items() if k not in ("form_data", "user_token")})


@app.get("/api/jobs", response_model=list[JobResponse])
async def list_jobs(user: TokenData = Depends(get_current_user)):
    user_jobs = [
        j for j in _jobs.values()
        if j.get("user_email") == user.email
    ]
    user_jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return [
        JobResponse(**{k: v for k, v in j.items() if k not in ("form_data", "user_token")})
        for j in user_jobs
    ]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, user: TokenData = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    if job.get("user_email") != user.email:
        raise HTTPException(status_code=403, detail="Sin acceso a este trabajo")
    return JobResponse(**{k: v for k, v in job.items() if k not in ("form_data", "user_token")})


# ── Background job runner ─────────────────────────────────────────────────────

async def _run_job(job_id: str):
    """Ejecuta el proceso completo en background y actualiza el estado del job."""
    job = _jobs[job_id]
    job["status"] = "running"

    try:
        from session_manager import run_session, extract_candidates_from_har, choose_best_stream
        from video import (
            download_with_ffmpeg, download_with_ytdlp,
            extract_audio, transcribe, AUDIO_COMPRESSED, _needs_ytdlp,
        )
        from config import TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, HAR_PATH, ARTIFACTS_DIR
        from db import save_transcription_to_file
        import glob, os

        # Limpiar artefactos previos
        for f in (
            glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp4")) +
            glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp3")) +
            glob.glob(os.path.join(ARTIFACTS_DIR, "*.wav"))
        ):
            os.remove(f)

        url = job["url"]
        empresa = job["empresa"]
        form_data = job["form_data"]

        # 1) Detectar stream
        if _needs_ytdlp(url):
            best = url
        else:
            stream_live = await run_session(
                url=url,
                timeout_ms=TIMEOUT_MS,
                form_server_port=None,
                form_data_override=form_data,
            )
            cands = extract_candidates_from_har(HAR_PATH, limit=200)
            best = stream_live or choose_best_stream(None, cands)

        if not best:
            raise Exception("No se encontró URL de stream válida")

        # 2) Descargar
        if _needs_ytdlp(url):
            await asyncio.to_thread(download_with_ytdlp, url, AUDIO_COMPRESSED)
        else:
            await asyncio.to_thread(download_with_ffmpeg, best, VIDEO_FILE)
            await asyncio.to_thread(extract_audio, VIDEO_FILE, AUDIO_FILE)

        # 3) Transcribir
        texto_final = await asyncio.to_thread(transcribe, AUDIO_COMPRESSED)

        # 4) Guardar en MySQL
        await asyncio.to_thread(insert_report, texto_final, url, empresa)

        # 5) Guardar .txt local
        filepath = await asyncio.to_thread(save_transcription_to_file, texto_final, empresa)

        # 6) Subir a SharePoint (con token del usuario logueado)
        sp_url = None
        if SHAREPOINT_ENABLED:
            from sharepoint_uploader import SharePointUploader
            uploader = SharePointUploader.from_user_token(job["user_token"])
            resultado = await asyncio.to_thread(uploader.upload_file, filepath)
            sp_url = resultado.get("webUrl")

        job["status"] = "done"
        job["sharepoint_url"] = sp_url

    except Exception as e:
        import traceback
        traceback.print_exc()
        job["status"] = "error"
        job["error_msg"] = str(e)


# ── Arranque ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    wait_for_mysql()
    print("✅ API arrancada y MySQL conectado")