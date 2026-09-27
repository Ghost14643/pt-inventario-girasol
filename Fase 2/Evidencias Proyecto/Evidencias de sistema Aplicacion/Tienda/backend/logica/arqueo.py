"""Apertura, resumen y cierre diario de caja con migración aditiva."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from backend.db.conexion import conectar_db, conectar_mydb

_NEW_COLUMNS = {
    "apertura_at": "TEXT", "cierre_at": "TEXT", "ventas_cantidad": "INTEGER",
    "total_debito": "REAL", "total_credito": "REAL", "total_credito_girasol": "REAL", "total_otro": "REAL",
    "gastos_turno": "REAL", "efectivo_esperado": "REAL",
    "efectivo_contado": "REAL", "diferencia": "REAL",
}


def asegurar_esquema() -> None:
    """Crea la tabla o añade columnas sin borrar ni reconstruir datos existentes."""
    conn = conectar_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS arqueo_diario (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL,
                apertura_at TEXT, cierre_at TEXT, ventas_cantidad INTEGER,
                total_efectivo REAL, total_debito REAL, total_credito REAL,
                total_transferencia REAL, total_otro REAL, total_ventas REAL,
                gastos_turno REAL, efectivo_esperado REAL, efectivo_contado REAL,
                diferencia REAL
            )
        """)
        current = {row[1] for row in conn.execute("PRAGMA table_info(arqueo_diario)")}
        for name, sql_type in _NEW_COLUMNS.items():
            if name not in current:
                conn.execute(f"ALTER TABLE arqueo_diario ADD COLUMN {name} {sql_type}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_arqueo_diario_fecha ON arqueo_diario(fecha)")
        # Las filas anteriores a esta función eran cierres históricos, no aperturas pendientes.
        conn.execute("UPDATE arqueo_diario SET apertura_at=fecha || ' 00:00:00', cierre_at=fecha || ' 23:59:59' WHERE apertura_at IS NULL")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def estado_caja(fecha: str) -> dict[str, Any]:
    asegurar_esquema()
    conn = conectar_db()
    try:
        row = conn.execute("SELECT fecha, apertura_at, cierre_at FROM arqueo_diario WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
        if row is None:
            return {"fecha": fecha, "existe": False, "abierta": False, "cerrada": False}
        return {"fecha": row["fecha"], "existe": True, "abierta": row["cierre_at"] is None,
                "cerrada": row["cierre_at"] is not None, "apertura_at": row["apertura_at"], "cierre_at": row["cierre_at"]}
    finally:
        conn.close()


def abrir_caja(fecha: str) -> dict[str, Any]:
    asegurar_esquema()
    conn = conectar_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        actual = conn.execute("SELECT apertura_at, cierre_at FROM arqueo_diario WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
        if actual:
            if actual["cierre_at"] is not None:
                raise ValueError("La caja de esta fecha ya fue cerrada")
            conn.rollback()
            return estado_caja(fecha)
        columns = {row[1]: row for row in conn.execute("PRAGMA table_info(arqueo_diario)")}
        values: dict[str, Any] = {"fecha": fecha, "apertura_at": datetime.now().isoformat(sep=" ", timespec="seconds")}
        # Compatibilidad: columnas financieras heredadas eran NOT NULL; quedan en cero hasta el cierre.
        for name in ("subtotal_ventas", "total_efectivo", "total_tarjeta", "total_transferencia", "total_gastos", "gastos_dia", "total_ventas"):
            if name in columns and columns[name][3] and name not in values:
                values[name] = 0
        names = list(values)
        conn.execute(f"INSERT INTO arqueo_diario ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})", tuple(values[n] for n in names))
        conn.commit()
        return {"fecha": fecha, "existe": True, "abierta": True, "cerrada": False, "apertura_at": values["apertura_at"], "cierre_at": None}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ventas_del_turno(fecha: str, apertura_at: str | None) -> dict[str, Any]:
    inicio = apertura_at or f"{fecha} 00:00:00"
    fin = (date.fromisoformat(fecha) + timedelta(days=1)).isoformat() + " 00:00:00"
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB para recopilar las ventas")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT LOWER(metodo_pago) metodo, COUNT(*) cantidad, COALESCE(SUM(total),0) total
            FROM ventas WHERE fecha >= %s AND fecha < %s GROUP BY LOWER(metodo_pago)""", (inicio, fin))
        rows = cursor.fetchall()
    finally:
        cursor.close(); conn.close()
    totals = {key: 0.0 for key in ("efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro")}
    count = 0
    for row in rows:
        method = row["metodo"] if row["metodo"] in totals else "otro"
        totals[method] += float(row["total"] or 0); count += int(row["cantidad"] or 0)
    return {"ventas_cantidad": count, **{f"total_{key}": value for key, value in totals.items()}, "total_ventas": sum(totals.values())}


def consultar_arqueo_fecha(fecha: str) -> dict[str, Any]:
    status = estado_caja(fecha)
    if not status["existe"]:
        return {
            "fecha": fecha,
            "existe": False,
            "abierta": False,
            "cerrada": False,
            "aviso": "No existe una caja abierta para la fecha indicada.",
            "puede_abrir": True,
        }
    conn = conectar_db()
    try:
        row = conn.execute("SELECT * FROM arqueo_diario WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
        result = dict(row)
    finally:
        conn.close()
    if status["cerrada"]:
        sales = {name: float(result.get(name) or 0) for name in ("total_efectivo", "total_debito", "total_credito", "total_credito_girasol", "total_transferencia", "total_otro", "total_ventas")}
        sales["ventas_cantidad"] = int(result.get("ventas_cantidad") or 0)
    else:
        sales = _ventas_del_turno(fecha, status.get("apertura_at"))
    result.update(sales); result.update({"abierta": status["abierta"], "cerrada": status["cerrada"]})
    result["gastos_turno"] = float(result.get("gastos_turno") or result.get("gastos_dia") or 0)
    result["efectivo_esperado"] = sales["total_efectivo"] - result["gastos_turno"]
    return result


def cerrar_caja(fecha: str, efectivo_contado: float, gastos_turno: float) -> dict[str, Any]:
    if efectivo_contado < 0 or gastos_turno < 0:
        raise ValueError("Los montos de caja no pueden ser negativos")
    status = estado_caja(fecha)
    if not status["existe"]: raise LookupError("No existe una caja abierta para esta fecha")
    if status["cerrada"]: raise ValueError("La caja de esta fecha ya está cerrada")
    sales = _ventas_del_turno(fecha, status.get("apertura_at"))
    expected = sales["total_efectivo"] - gastos_turno
    difference = efectivo_contado - expected
    conn = conectar_db()
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(arqueo_diario)")}
        values = {"cierre_at": datetime.now().isoformat(sep=" ", timespec="seconds"), **sales,
                  "gastos_turno": gastos_turno, "efectivo_esperado": expected,
                  "efectivo_contado": efectivo_contado, "diferencia": difference}
        legacy = {"subtotal_ventas": sales["total_ventas"], "total_tarjeta": sales["total_debito"] + sales["total_credito"],
                  "total_gastos": gastos_turno, "gastos_dia": gastos_turno}
        values.update({k: v for k, v in legacy.items() if k in columns})
        assignments = ", ".join(f"{name}=?" for name in values if name in columns)
        conn.execute(f"UPDATE arqueo_diario SET {assignments} WHERE id=(SELECT id FROM arqueo_diario WHERE fecha=? ORDER BY id DESC LIMIT 1)",
                     tuple(values[name] for name in values if name in columns) + (fecha,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
    return consultar_arqueo_fecha(fecha)
