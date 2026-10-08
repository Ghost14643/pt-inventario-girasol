"""Lógica de negocio para clientas y sus hojas de crédito."""
from __future__ import annotations

from typing import Any

from mysql.connector import IntegrityError

from backend.db.conexion import conectar_mydb
from backend.logica.credito import _perfil, asegurar_esquema_credito


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
        asegurar_esquema_credito(cursor)
        conn.commit()
        if not _cliente_table_exists(conn):
            return []
        like = f"%{term}%"
        cursor.execute(
            """
            SELECT
                c.rut_cliente AS rut,
                c.dvrut_cliente AS digito_ver,
                c.nombre
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
        result = []
        for row in rows:
            profile = _perfil(cursor, int(row["rut"]))
            result.append({**row, **profile, "rut": f"{row['rut']}-{row['digito_ver']}"})
        return result
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
                e.estado AS estado_nombre,
                v.fecha AS fecha_venta,
                v.total AS total_venta,
                COALESCE(SUM(q.monto_cuota), 0) AS saldo_original,
                COALESCE(SUM(GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0)), 0) AS saldo_pendiente,
                SUM(CASE WHEN q.monto_cuota > COALESCE(p.pagado, 0) THEN 1 ELSE 0 END) AS cuotas_por_pagar,
                MIN(CASE WHEN q.monto_cuota > COALESCE(p.pagado, 0) THEN q.fecha_vencimiento END) AS proximo_vencimiento
            FROM credito c
            JOIN estado_credito e ON e.id_estado_credito = c.id_estado_credito
            JOIN venta v ON v.id_venta = c.id_venta
            LEFT JOIN cuota_credito q ON q.id_credito = c.id_credito
            LEFT JOIN (
                SELECT id_cuota_credito, SUM(monto) AS pagado
                FROM detalle_abono_credito GROUP BY id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            WHERE v.rut_cliente = %s
            GROUP BY c.id_credito, c.id_venta, c.cantidad_cuotas, c.pie, e.estado, v.fecha, v.total
            ORDER BY c.id_credito DESC
            """,
            (number,),
        )
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()


def obtener_detalle_credito(rut: str | int, id_credito: int) -> dict[str, Any]:
    number, _ = _rut_parts(rut)
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                c.id_credito,
                c.id_venta,
                c.cantidad_cuotas,
                c.pie,
                v.fecha AS fecha_venta,
                v.total AS total_venta
            FROM credito c
            JOIN venta v ON v.id_venta = c.id_venta
            WHERE c.id_credito = %s AND v.rut_cliente = %s
            """,
            (id_credito, number),
        )
        compra = cursor.fetchone()
        if compra is None:
            raise LookupError("Crédito no encontrado para esta clienta")

        cursor.execute(
            """
            SELECT
                p.nombre,
                p.codigo_base,
                vp.sku,
                vp.talla,
                vp.color,
                dv.cantidad,
                dv.precio_unitario,
                dv.cantidad * dv.precio_unitario AS subtotal
            FROM detalle_venta dv
            JOIN variante_producto vp ON vp.id_variante = dv.id_variante
            JOIN producto p ON p.id_producto = vp.id_producto
            WHERE dv.id_venta = %s
            ORDER BY p.nombre, vp.talla, vp.color
            """,
            (compra["id_venta"],),
        )
        compra["productos"] = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                q.numero_cuota,
                q.monto_cuota,
                q.fecha_vencimiento,
                q.fecha_pago,
                COALESCE(p.pagado, 0) AS monto_pagado,
                GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0) AS saldo_pendiente,
                CASE WHEN COALESCE(p.pagado, 0) >= q.monto_cuota THEN 1 ELSE 0 END AS pagada
            FROM cuota_credito q
            LEFT JOIN (
                SELECT da.id_cuota_credito, SUM(da.monto) AS pagado
                FROM detalle_abono_credito da
                GROUP BY da.id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            WHERE q.id_credito = %s
            ORDER BY q.numero_cuota
            """,
            (id_credito,),
        )
        compra["cuotas"] = cursor.fetchall()
        return compra
    finally:
        cursor.close()
        conn.close()


def resumen_clientas() -> dict[str, int]:
    """Devuelve clientas, créditos vigentes y saldo de cartera."""
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.commit()
        cursor.execute("SHOW TABLES LIKE 'cliente'")
        if cursor.fetchone() is None:
            return {"total_clientas": 0, "creditos_activos": 0, "saldo_pendiente": 0}

        cursor.execute("SELECT COUNT(*) AS total_clientas FROM cliente")
        total_clients = int((cursor.fetchone() or {}).get("total_clientas") or 0)
        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT CASE WHEN q.monto_cuota > COALESCE(p.pagado, 0)
                    THEN cr.id_credito END) AS creditos_activos,
                COALESCE(SUM(GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0)), 0) AS saldo_pendiente
            FROM credito cr
            JOIN cuota_credito q ON q.id_credito = cr.id_credito
            LEFT JOIN (
                SELECT id_cuota_credito, SUM(monto) AS pagado
                FROM detalle_abono_credito GROUP BY id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            """
        )
        portfolio = cursor.fetchone() or {}
        return {
            "total_clientas": total_clients,
            "creditos_activos": int(portfolio.get("creditos_activos") or 0),
            "saldo_pendiente": int(portfolio.get("saldo_pendiente") or 0),
        }
    finally:
        cursor.close()
        conn.close()
