"""
auth.py — Validación de tokens Microsoft en el backend Python.

Cuando el usuario hace login en el frontend React con MSAL,
Microsoft devuelve un JWT. Este módulo lo valida usando las
claves públicas de Microsoft (JWKS) sin necesidad de Client Secret.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

import httpx
from jose import jwt, JWTError

TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")

JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER   = f"https://sts.windows.net/{TENANT_ID}/"

_jwks_cache: dict = {}


@dataclass
class TokenData:
    user_id: str
    name: str
    email: str
    access_token: str   # token original para usarlo con Graph API / SharePoint


async def _get_jwks() -> dict:
    """Descarga y cachea las claves públicas de Microsoft."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


async def verify_token(token: str) -> Optional[TokenData]:
    """
    Valida el token JWT de Microsoft y devuelve los datos del usuario.
    Devuelve None si el token es inválido o expirado.

    Modo desarrollo: si AZURE_TENANT_ID no está configurado, acepta
    cualquier token y devuelve un usuario de prueba. Útil para
    desarrollar sin credenciales del admin todavía.
    """
    if not TENANT_ID or not CLIENT_ID:
        print("⚠️  AZURE_TENANT_ID o AZURE_CLIENT_ID no configurados — modo dev sin auth")
        return TokenData(
            user_id="dev-user",
            name="Developer",
            email="dev@localhost",
            access_token=token,
        )

    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER,
        )
        return TokenData(
            user_id=payload.get("oid") or payload.get("sub", ""),
            name=payload.get("name", ""),
            email=payload.get("preferred_username") or payload.get("email", ""),
            access_token=token,
        )
    except JWTError as e:
        print(f"[auth] Token inválido: {e}")
        return None
    except Exception as e:
        print(f"[auth] Error verificando token: {e}")
        return None