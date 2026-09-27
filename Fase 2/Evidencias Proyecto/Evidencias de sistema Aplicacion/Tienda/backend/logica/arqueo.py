"""Estado de caja compatible con el esquema MariaDB del proyecto."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.db.conexion import conectar_mydb


def asegurar_esquema() -> None:
    """No crea tablas adicionales; el esquema obligatorio vive en 01-create-db.sql y 02-new-schema.sql."""
    return None


def _primera_venta_fecha(fecha: str) -> int:
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_usuario FROM usuario ORDER BY id_usuario LIMIT 1")
        row = cursor.fetchone()
        return int(row[0]) if row else 1
    finally:
        cursor.close(); conn.close()


def estado_caja(fecha: str) -> dict[str, Any]:
    conn = conectar_mydb()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_arqueo, id_usuario, fecha, hora_apertura, hora_cierre, monto_inicial, monto_final, gastos, usuario_caja_abierta FROM arqueo_caja WHERE fecha = %s ORDER BY id_arqueo DESC LIMIT 1",
            (fecha,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"fecha": fecha, "existe": False, "abierta": False, "cerrada": False}
        return {
            "fecha": str(row["fecha"]),
            "existe": True,
            "abierta": row["hora_cierre"] is None,
            "cerrada": row["hora_cierre"] is not None,
            "apertura_at": row["hora_apertura"],
            "cierre_at": row["hora_cierre"],
        }
    finally:
        cursor.close(); conn.close()


def abrir_caja(fecha: str) -> dict[str, Any]:
    status = estado_caja(fecha)
    if status["existe"] and status["cerrada"]:
        raise ValueError("La caja de esta fecha ya fue cerrada")
    if status["existe"] and status["abierta"]:
        return status
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        id_usuario = _primera_venta_fecha(fecha)
        apertura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO arqueo_caja (id_usuario, fecha, hora_apertura, hora_cierre, monto_inicial, monto_final, gastos, usuario_caja_abierta) VALUES (%s, %s, %s, NULL, 0, NULL, 0, %s)",
            (id_usuario, fecha, apertura, id_usuario),
        )
        conn.commit()
        return {"fecha": fecha, "existe": True, "abierta": True, "cerrada": False, "apertura_at": apertura, "cierre_at": None}
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()


def _ventas_del_turno(fecha: str, apertura_at: str | None) -> dict[str, Any]:
    """Suma ventas del día desde la tabla `venta` del esquema actual."""
    conn = conectar_mydb()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT LOWER(mp.nombre) AS metodo, COUNT(*) AS cantidad, COALESCE(SUM(v.total), 0) AS total
            FROM venta v
            JOIN metodo_pago mp ON mp.id_metodo_pago = v.id_metodo_pago
            WHERE DATE(v.fecha) = %s
            GROUP BY LOWER(mp.nombre)
            """,
            (fecha,),
        )
        rows = cursor.fetchall()
        totals = {key: 0.0 for key in ("efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro")}
        cantidad_total = 0
        for row in rows:
            metodo = (row["metodo"] or "otro").strip().lower().replace(" ", "_")
            if metodo not in totals:
                metodo = "otro"
            totals[metodo] += float(row["total"] or 0)
            cantidad_total += int(row["cantidad"] or 0)
        return {
            "ventas_cantidad": cantidad_total,
            "total_efectivo": float(totals["efectivo"]),
            "total_debito": float(totals["debito"]),
            "total_credito": float(totals["credito"]),
            "total_credito_girasol": float(totals["credito_girasol"]),
            "total_transferencia": float(totals["transferencia"]),
            "total_otro": float(totals["otro"]),
            "total_ventas": float(sum(totals.values())),
        }
    finally:
        cursor.close(); conn.close()


def consultar_arqueo_fecha(fecha: str) -> dict[str, Any]:
    status = estado_caja(fecha)
    if not status["existe"]:
        return {"fecha": fecha, "existe": False, "abierta": False, "cerrada": False, "aviso": "No existe una caja abierta para la fecha indicada.", "puede_abrir": True}

    conn = conectar_mydb()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM arqueo_caja WHERE fecha = %s ORDER BY id_arqueo DESC LIMIT 1",
            (fecha,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close(); conn.close()
    if row is None:
        return {"fecha": fecha, "existe": False, "abierta": False, "cerrada": False}
    result = dict(row)
    sales = _ventas_del_turno(fecha, status.get("apertura_at")) if not status["cerrada"] else {
        "ventas_cantidad": 0,
        "total_efectivo": 0.0,
        "total_debito": 0.0,
        "total_credito": 0.0,
        "total_credito_girasol": 0.0,
        "total_transferencia": 0.0,
        "total_otro": 0.0,
        "total_ventas": 0.0,
    }
    result.update(sales)
    result.update({"abierta": status["abierta"], "cerrada": status["cerrada"]})
    result["gastos_turno"] = float(result.get("gastos") or 0)
    result["efectivo_esperado"] = float(result.get("monto_final") or sales["total_efectivo"] - result["gastos_turno"])
    return result


def cerrar_caja(fecha: str, efectivo_contado: float, gastos_turno: float) -> dict[str, Any]:
    if efectivo_contado < 0 or gastos_turno < 0:
        raise ValueError("Los montos de caja no pueden ser negativos")
    status = estado_caja(fecha)
    if not status["existe"]:
        raise LookupError("No existe una caja abierta para esta fecha")
    if status["cerrada"]:
        raise ValueError("La caja de esta fecha ya está cerrada")
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        sales = _ventas_del_turno(fecha, status.get("apertura_at"))
        expected = float(sales["total_efectivo"]) - float(gastos_turno)
        difference = float(efectivo_contado) - expected
        cursor.execute(
            "UPDATE arqueo_caja SET hora_cierre = %s, monto_final = %s, gastos = %s, usuario_caja_abierta = NULL WHERE fecha = %s AND hora_cierre IS NULL",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), efectivo_contado, gastos_turno, fecha),
        )
        if cursor.rowcount == 0:
            raise LookupError("No existe una caja abierta para esta fecha")
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()
    return consultar_arqueo_fecha(fecha)
