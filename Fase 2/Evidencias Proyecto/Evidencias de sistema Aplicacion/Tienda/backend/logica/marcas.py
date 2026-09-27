"""Gestión de marcas en la base SQLite local de Girasol."""
from __future__ import annotations
import sqlite3
from typing import Any
from backend.db.conexion import conectar_db


def obtener_marcas() -> list[dict[str, Any]]:
    conn = conectar_db()
    try:
        return [dict(row) for row in conn.execute(
            "SELECT id, TRIM(nombre) AS nombre FROM marcas ORDER BY nombre COLLATE NOCASE"
        ).fetchall()]
    finally:
        conn.close()


def agregar_nueva_marca(nombre: str) -> dict[str, Any]:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la marca es obligatorio")
    conn = conectar_db()
    try:
        existente = conn.execute(
            "SELECT id, TRIM(nombre) AS nombre FROM marcas WHERE LOWER(TRIM(nombre))=LOWER(?)",
            (nombre,),
        ).fetchone()
        if existente:
            raise ValueError("La marca ya existe")
        cursor = conn.execute("INSERT INTO marcas (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return {"id": cursor.lastrowid, "nombre": nombre}
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("La marca ya existe") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
