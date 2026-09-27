"""Lógica de negocio para clientas y sus hojas de crédito."""
from __future__ import annotations

from typing import Any
from mysql.connector import Error, IntegrityError
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


def listar_clientas(search: str = "") -> list[dict[str, Any]]:
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        term = f"%{search.strip()}%"
        cursor.execute("""
            SELECT rut, digito_ver, nombre, celular, direccion,
                   actividad_economica, descripcion, fono
            FROM cliente
            WHERE %s = '' OR nombre LIKE %s
               OR CAST(rut AS CHAR) LIKE %s
               OR CAST(celular AS CHAR) LIKE %s
               OR CAST(fono AS CHAR) LIKE %s
            ORDER BY nombre ASC
        """, (search.strip(), term, term, term, term))
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
        like = f"%{term}%"
        cursor.execute("""
            SELECT c.rut, c.digito_ver, c.nombre, COALESCE(c.tope_credito, 0) AS tope_credito,
                   COALESCE(SUM(CASE WHEN h.estado <> 3 THEN
                       CASE WHEN h.precio_cuota IS NULL THEN h.cuotas_por_pagar
                            ELSE h.precio_cuota * h.cuotas_por_pagar END ELSE 0 END), 0) AS credito_usado
            FROM cliente c
            LEFT JOIN hoja_credito h ON h.cliente = c.rut
            WHERE c.nombre LIKE %s OR CAST(c.rut AS CHAR) LIKE %s
               OR CONCAT(c.rut, '-', c.digito_ver) LIKE %s
            GROUP BY c.rut, c.digito_ver, c.nombre, c.tope_credito
            ORDER BY c.nombre LIMIT 12
        """, (like, like, like))
        rows = cursor.fetchall()
        return [{**row, "rut": f"{row['rut']}-{row['digito_ver']}",
                 "tope_credito": int(row["tope_credito"] or 0),
                 "credito_usado": int(row["credito_usado"] or 0),
                 "credito_disponible": max(int(row["tope_credito"] or 0) - int(row["credito_usado"] or 0), 0)} for row in rows]
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
        cursor.execute("""
            INSERT INTO cliente
                (rut, digito_ver, nombre, celular, direccion,
                 actividad_economica, descripcion, fono)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (number, dv, nombre.strip(), int(celular), direccion or None,
              actividad_economica or None, descripcion or None,
              int(fono) if fono not in (None, "") else None))
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
        cursor.execute("""
            SELECT rut, digito_ver, nombre, celular, direccion,
                   actividad_economica, descripcion, fono
            FROM cliente WHERE rut = %s
        """, (number,))
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
        cursor.execute("""
            SELECT h.id, h.cliente, h.id_boleta, h.fecha_pago, h.cuotas_por_pagar,
                   h.estado, e.estado AS estado_nombre, h.precio_cuota, h.pie
            FROM hoja_credito h
            JOIN estado_credito e ON e.id = h.estado
            WHERE h.cliente = %s
            ORDER BY h.fecha_pago DESC, h.id DESC
        """, (number,))
        rows = cursor.fetchall()
        for row in rows:
            if row.get("fecha_pago") is not None:
                row["fecha_pago"] = row["fecha_pago"].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def resumen_clientas() -> dict[str, int]:
    """Devuelve métricas globales sin cargar una hoja por cada clienta."""
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM cliente) AS total_clientas,
                COUNT(DISTINCT CASE WHEN h.estado <> 3 THEN h.cliente END) AS creditos_activos,
                COALESCE(SUM(CASE WHEN h.estado <> 3
                    THEN COALESCE(h.precio_cuota, 0) * COALESCE(h.cuotas_por_pagar, 0)
                    ELSE 0 END), 0) AS saldo_pendiente
            FROM hoja_credito h
        """)
        row = cursor.fetchone()
        return {key: int(value or 0) for key, value in row.items()}
    finally:
        cursor.close()
        conn.close()
