"""Almacenamiento seguro de facturas y referencia en MySQL."""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Any

from backend.db.conexion import conectar_mydb

MAX_FILE_SIZE = int(os.getenv("FACTURA_MAX_BYTES", str(15 * 1024 * 1024)))


def _upload_dir() -> Path:
    configured = os.getenv("FACTURAS_UPLOAD_DIR")
    if configured:
        return Path(configured)
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return data_dir / "facturas"
    return Path(__file__).resolve().parents[2] / "data" / "facturas"


def _extension_real(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return ".pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"mif1"):
        return ".heic"
    return None


def _safe_stem(filename: str) -> str:
    stem = Path(filename or "factura").stem
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-_")
    return (stem or "factura")[:60]


def guardar_factura(data: bytes, nombre_original: str) -> dict[str, Any]:
    if not data:
        raise ValueError("El archivo está vacío")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"El archivo supera el límite de {MAX_FILE_SIZE // (1024 * 1024)} MB")
    extension = _extension_real(data)
    if extension is None:
        raise ValueError("Solo se permiten imágenes o documentos PDF válidos")

    directory = _upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{datetime.now():%Y%m%d-%H%M%S}-{_safe_stem(nombre_original)}-{uuid4().hex[:8]}{extension}"
    destination = directory / stored_name
    destination.write_bytes(data)

    conn = conectar_mydb()
    if conn is None:
        destination.unlink(missing_ok=True)
        raise ConnectionError("No fue posible conectar con MySQL")
    cursor = conn.cursor()
    try:
        fecha = datetime.now()
        cursor.execute("INSERT INTO factura (imagen, fecha_subida) VALUES (%s, %s)", (stored_name, fecha))
        conn.commit()
        return {"id_factura": cursor.lastrowid, "archivo": stored_name,
                "nombre_original": nombre_original, "fecha_subida": fecha.isoformat(),
                "tamano": len(data), "tipo": extension.lstrip(".")}
    except Exception:
        conn.rollback()
        destination.unlink(missing_ok=True)
        raise
    finally:
        cursor.close()
        conn.close()
