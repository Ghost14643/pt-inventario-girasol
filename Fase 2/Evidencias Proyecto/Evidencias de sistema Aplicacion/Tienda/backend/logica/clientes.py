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
        raise ConnectionError("No fue posible conectar con MySQL")
    return conn


def _cliente_table_exists(conn) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'cliente'")
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def listar_clientas(search: str = "") -> list[dict[str, Any]]:
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if not _cliente_table_exists(conn):
            return []
        search_term = str(search or "").strip()
        term = f"%{search_term}%"
        cursor.execute(
            """
            SELECT
                rut_cliente AS rut,
                dvrut_cliente AS digito_ver,
                nombre,
                celular,
                direccion,
                actividad_economica,
                descripcion,
                fono
            FROM cliente
            WHERE %s = '' OR nombre LIKE %s
                OR CAST(rut_cliente AS CHAR) LIKE %s
                OR CAST(celular AS CHAR) LIKE %s
                OR CAST(fono AS CHAR) LIKE %s
            ORDER BY nombre ASC
            """,
            (search_term, term, term, term, term),
        )
        rows = cursor.fetchall()
        return [{**row, "rut": f"{row['rut']}-{row['digito_ver']}"} for row in rows]
    finally:
        cursor.close()
        conn.close()


def buscar_clientas_credito(search: str = "") -> list[dict[str, Any]]:
    """Busca por nombre/RUT y calcula deuda activa y crédito disponible."""
    term = search.strip().replace(".", "")
    if len(term) < 2:
        return []
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if not _cliente_table_exists(conn):
            return []
        cursor.execute(
            "SHOW TABLES LIKE 'credito'"
        )
        if cursor.fetchone() is None:
            return []
        like = f"%{term}%"
        cursor.execute(
            """
            SELECT
                c.rut_cliente AS rut,
                c.dvrut_cliente AS digito_ver,
                c.nombre,
                COALESCE(c.tope_credito, 0) AS tope_credito,
                0 AS credito_usado
            FROM cliente c
            WHERE c.nombre LIKE %s
               OR CAST(c.rut_cliente AS CHAR) LIKE %s
               OR CONCAT(c.rut_cliente, '-', c.dvrut_cliente) LIKE %s
            ORDER BY c.nombre
            LIMIT 12
            """,
            (like, like, like),
        )
        rows = cursor.fetchall()
        return [{**row, "rut": f"{row['rut']}-{row['digito_ver']}", "tope_credito": int(row["tope_credito"] or 0), "credito_usado": int(row["credito_usado"] or 0), "credito_disponible": max(int(row["tope_credito"] or 0) - int(row["credito_usado"] or 0), 0)} for row in rows]
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
            (number, dv, nombre.strip(), int(celular), direccion or None, actividad_economica or None, descripcion or None, int(fono) if fono not in (None, "") else None),
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
            SELECT
                rut_cliente AS rut,
                dvrut_cliente AS digito_ver,
                nombre,
                celular,
                direccion,
                actividad_economica,
                descripcion,
                fono
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
    number, _ = _rut_parts(rut)
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW TABLES LIKE 'credito'")
        if cursor.fetchone() is None:
            return []
        cursor.execute(
            """
            SELECT
                c.id_credito AS id,
                c.id_venta,
                c.cantidad_cuotas,
                c.pie,
                e.estado AS estado_nombre
            FROM credito c
            JOIN estado_credito e ON e.id_estado_credito = c.id_estado_credito
            JOIN venta v ON v.id_venta = c.id_venta
            WHERE v.rut_cliente = %s
            ORDER BY c.id_credito DESC
            """,
            (number,),
        )
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()


def resumen_clientas() -> dict[str, int]:
    """Devuelve métricas globales sin cargar una hoja por cada clienta."""
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW TABLES LIKE 'cliente'")
        if cursor.fetchone() is None:
            return {"total_clientas": 0, "creditos_activos": 0, "saldo_pendiente": 0}

        cursor.execute("SELECT COUNT(*) AS total_clientas FROM cliente")
        row = cursor.fetchone()
        return {
            "total_clientas": int((row or {}).get("total_clientas") or 0),
            "creditos_activos": 0,
            "saldo_pendiente": 0,
        }
    finally:
        cursor.close()
        conn.close()
