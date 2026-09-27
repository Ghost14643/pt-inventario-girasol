"""Gestión de marcas en MariaDB."""
from __future__ import annotations

import mysql.connector
from typing import Any

from backend.db.conexion import conectar_mydb


def obtener_marcas() -> list[dict[str, Any]]:
    conn = conectar_mydb()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_marca AS id, TRIM(nombre) AS nombre FROM marca ORDER BY nombre")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def agregar_nueva_marca(nombre: str) -> dict[str, Any]:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la marca es obligatorio")
    conn = conectar_mydb()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_marca AS id, TRIM(nombre) AS nombre FROM marca WHERE LOWER(TRIM(nombre))=LOWER(%s)",
            (nombre,),
        )
        existente = cursor.fetchone()
        if existente:
            raise ValueError("La marca ya existe")
        cursor.execute("INSERT INTO marca (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        return {"id": cursor.lastrowid, "nombre": nombre}
    except mysql.connector.IntegrityError as exc:
        conn.rollback()
        raise ValueError("La marca ya existe") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
