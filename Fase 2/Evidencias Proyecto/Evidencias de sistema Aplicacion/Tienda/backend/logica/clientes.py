"""Lógica de negocio para clientas y sus hojas de crédito."""
from __future__ import annotations

from typing import Any
from mysql.connector import IntegrityError

from backend.db.conexion import conectar_mydb


def _rut_parts(rut: str | int) -> tuple[int, str | None]:
    value = str(rut).strip().replace(".", "")
    if "-" in value:
        number, dv = value.rsplit("-", 1)
        return int(number), dv.upper()
    return int(value), None


def _connection():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con la base de datos")
    return conn


def listar_clientas(search: str = "") -> list[dict[str, Any]]:
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        term = (search or "").strip()
        if term:
            normalized = term.replace(".", "").replace("-", "")
            like_term = f"%{term}%"
            like_digits = f"%{normalized}%"
            cursor.execute(
                """
                SELECT rut_cliente AS rut, dvrut_cliente AS digito_ver, nombre, celular, direccion,
                       actividad_economica, descripcion, fono
                FROM cliente
                WHERE nombre LIKE %s
                   OR CAST(rut_cliente AS CHAR) LIKE %s
                   OR CONCAT(rut_cliente, '-', dvrut_cliente) LIKE %s
                   OR CAST(celular AS CHAR) LIKE %s
                   OR CAST(fono AS CHAR) LIKE %s
                ORDER BY nombre ASC
                """,
                (like_term, like_digits, like_term, like_digits, like_digits),
            )
        else:
            cursor.execute(
                """
                SELECT rut_cliente AS rut, dvrut_cliente AS digito_ver, nombre, celular, direccion,
                       actividad_economica, descripcion, fono
                FROM cliente
                ORDER BY nombre ASC
                """
            )
        rows = cursor.fetchall()
        return [{**row, "rut": f"{row['rut']}-{row['digito_ver']}"} for row in rows]
    finally:
        cursor.close()
        conn.close()


def buscar_clientas_credito(search: str = "") -> list[dict[str, Any]]:
    """Busca clientas por nombre/RUT usando el esquema actual de MariaDB."""
    term = (search or "").strip().replace(".", "")
    if len(term) < 2:
        return []
    normalized = term.replace("-", "")
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        like = f"%{term}%"
        like_digits = f"%{normalized}%"
        cursor.execute(
            """
                SELECT rut_cliente AS rut, dvrut_cliente AS digito_ver, nombre
                FROM cliente
                WHERE nombre LIKE %s
                   OR CAST(rut_cliente AS CHAR) LIKE %s
                   OR CONCAT(rut_cliente, '-', dvrut_cliente) LIKE %s
                ORDER BY nombre ASC
                LIMIT 12
            """,
            (like, like_digits, like),
        )
        rows = cursor.fetchall()
        return [{
            **row,
            "rut": f"{row['rut']}-{row['digito_ver']}",
            "tope_credito": 0,
            "credito_usado": 0,
            "credito_disponible": 0,
        } for row in rows]
    finally:
        cursor.close()
        conn.close()


def crear_clienta(*, nombre: str, rut: str, celular: str | int,
                 direccion: str | None = None,
                 actividad_economica: str | None = None,
                 descripcion: str | None = None,
                 fono: str | int | None = None) -> dict[str, Any]:
    number, dv = _rut_parts(rut)
    if not dv:
        raise ValueError("El RUT debe incluir dígito verificador")
    conn = _connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
                INSERT INTO cliente
                    (rut_cliente, dvrut_cliente, nombre, celular, direccion,
                     actividad_economica, descripcion, fono)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                number,
                dv,
                nombre.strip(),
                str(celular) if celular is not None else None,
                direccion or None,
                actividad_economica or None,
                descripcion or None,
                str(fono) if fono not in (None, "") else None,
            ),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Ya existe una clienta con ese RUT") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return obtener_clienta(rut)


def obtener_clienta(rut: str | int) -> dict[str, Any]:
    number, _ = _rut_parts(rut)
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
                SELECT rut_cliente AS rut, dvrut_cliente AS digito_ver, nombre, celular, direccion,
                       actividad_economica, descripcion, fono
                FROM cliente WHERE rut_cliente = %s
            """,
            (number,),
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Clienta no encontrada")
        return {**row, "rut": f"{row['rut']}-{row['digito_ver']}"}
    finally:
        cursor.close()
        conn.close()


def obtener_hoja_credito(rut: str | int) -> list[dict[str, Any]]:
    return []


def resumen_clientas() -> dict[str, int]:
    return {"total_clientas": 0, "creditos_activos": 0, "saldo_pendiente": 0}
