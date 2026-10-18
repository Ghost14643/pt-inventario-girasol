"""Gestión de marcas en MariaDB."""
from __future__ import annotations

from typing import Any

from backend.db.conexion import conectar_mydb


def _connection():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    return conn


def obtener_marcas() -> list[dict[str, Any]]:
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_marca AS id, TRIM(nombre) AS nombre FROM marca ORDER BY nombre")
        return list(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


def agregar_nueva_marca(nombre: str) -> dict[str, Any]:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la marca es obligatorio")

    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_marca AS id FROM marca WHERE LOWER(TRIM(nombre)) = LOWER(%s)", (nombre,))
        existente = cursor.fetchone()
        if existente:
            raise ValueError("La marca ya existe")

        cursor.execute("INSERT INTO marca (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        return {"id": int(cursor.lastrowid), "nombre": nombre}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
