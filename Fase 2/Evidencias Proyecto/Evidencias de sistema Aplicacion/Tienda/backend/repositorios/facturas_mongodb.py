from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from bson import ObjectId
from gridfs import GridFSBucket
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

ESTADO_PENDIENTE = "PENDIENTE_APROBACION"
ESTADO_PROCESANDO = "EN_PROCESO_APROBACION"
ESTADO_APROBADA = "APROBADA"

_logger = logging.getLogger(__name__)
_client: MongoClient[dict[str, Any]] | None = None
_facturas: Collection[dict[str, Any]] | None = None
_archivos: GridFSBucket | None = None
_resource_lock = Lock()


def _recursos() -> tuple[Collection[dict[str, Any]], GridFSBucket]:
    global _client, _facturas, _archivos
    with _resource_lock:
        if _client is None:
            client: MongoClient[dict[str, Any]] = MongoClient(
                os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                serverSelectionTimeoutMS=5000,
                tz_aware=True,
            )
            try:
                client.admin.command("ping")
                database = client[os.getenv("MONGO_DATABASE", "girasol")]
                collection = database["facturas"]
                collection.create_index([("estado", 1), ("fecha_creacion", -1)])
            except PyMongoError:
                client.close()
                raise
            _client = client
            _facturas = collection
            _archivos = GridFSBucket(database, bucket_name="facturas_archivos")

    assert _facturas is not None and _archivos is not None
    return _facturas, _archivos


def _object_id(factura_id: str) -> ObjectId | None:
    return ObjectId(factura_id) if ObjectId.is_valid(factura_id) else None


def _publicar(documento: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(documento["_id"]),
        "nombre_archivo": documento["nombre_archivo"],
        "content_type": documento["content_type"],
        "estado": documento["estado"],
        "estado_ocr": documento["estado_ocr"],
        "items": documento["items"],
        "fecha_creacion": documento["fecha_creacion"].isoformat(),
        "fecha_actualizacion": documento["fecha_actualizacion"].isoformat(),
        "aprobada_por": documento.get("aprobada_por"),
        "fecha_aprobacion": (
            documento["fecha_aprobacion"].isoformat()
            if documento.get("fecha_aprobacion")
            else None
        ),
    }


def guardar_factura(
    contenido: bytes,
    nombre_archivo: str,
    content_type: str,
    id_usuario: int,
    items: list[dict[str, Any]],
    extraction_method: str,
) -> dict[str, Any]:
    facturas, archivos = _recursos()
    ahora = datetime.now(timezone.utc)
    archivo_id = archivos.upload_from_stream(
        nombre_archivo,
        contenido,
        metadata={"content_type": content_type},
    )
    documento = {
        "nombre_archivo": nombre_archivo,
        "content_type": content_type,
        "archivo_id": archivo_id,
        "estado": ESTADO_PENDIENTE,
        "estado_ocr": extraction_method,
        "items": items,
        "creada_por": id_usuario,
        "fecha_creacion": ahora,
        "fecha_actualizacion": ahora,
    }
    try:
        facturas.insert_one(documento)
    except Exception:
        try:
            archivos.delete(archivo_id)
        except PyMongoError:
            _logger.exception("No se pudo eliminar un archivo de factura huérfano")
        raise
    return _publicar(documento)


def listar_pendientes() -> list[dict[str, Any]]:
    facturas, _ = _recursos()
    documentos = facturas.find(
        {"estado": {"$in": [ESTADO_PENDIENTE, ESTADO_PROCESANDO]}}
    ).sort("fecha_creacion", -1).limit(200)
    return [_publicar(documento) for documento in documentos]


def obtener_factura(factura_id: str) -> dict[str, Any] | None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return None
    facturas, _ = _recursos()
    documento = facturas.find_one({"_id": object_id})
    return _publicar(documento) if documento else None


def obtener_archivo(factura_id: str) -> tuple[bytes, str, str] | None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return None
    facturas, archivos = _recursos()
    documento = facturas.find_one({"_id": object_id})
    if documento is None:
        return None
    archivo = archivos.open_download_stream(documento["archivo_id"])
    try:
        contenido = archivo.read()
    finally:
        archivo.close()
    return contenido, documento["content_type"], documento["nombre_archivo"]


def actualizar_items(
    factura_id: str,
    items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return None
    facturas, _ = _recursos()
    documento = facturas.find_one_and_update(
        {"_id": object_id, "estado": ESTADO_PENDIENTE},
        {
            "$set": {
                "items": items,
                "fecha_actualizacion": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _publicar(documento) if documento else None


def reclamar_para_aprobacion(factura_id: str) -> dict[str, Any] | None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return None
    facturas, _ = _recursos()
    documento = facturas.find_one_and_update(
        {
            "_id": object_id,
            "estado": {"$in": [ESTADO_PENDIENTE, ESTADO_PROCESANDO]},
        },
        {
            "$set": {
                "estado": ESTADO_PROCESANDO,
                "fecha_actualizacion": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _publicar(documento) if documento else None


def devolver_a_pendiente(factura_id: str) -> None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return
    facturas, _ = _recursos()
    facturas.update_one(
        {"_id": object_id, "estado": ESTADO_PROCESANDO},
        {
            "$set": {
                "estado": ESTADO_PENDIENTE,
                "fecha_actualizacion": datetime.now(timezone.utc),
            }
        },
    )


def marcar_aprobada(factura_id: str, id_usuario: int) -> dict[str, Any] | None:
    object_id = _object_id(factura_id)
    if object_id is None:
        return None
    facturas, _ = _recursos()
    ahora = datetime.now(timezone.utc)
    documento = facturas.find_one_and_update(
        {"_id": object_id, "estado": ESTADO_PROCESANDO},
        {
            "$set": {
                "estado": ESTADO_APROBADA,
                "aprobada_por": id_usuario,
                "fecha_aprobacion": ahora,
                "fecha_actualizacion": ahora,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if documento is None:
        documento = facturas.find_one({"_id": object_id, "estado": ESTADO_APROBADA})
    return _publicar(documento) if documento else None
