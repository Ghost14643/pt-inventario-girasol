"""Reglas de Crédito Girasol sobre MariaDB."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from backend.db.conexion import conectar_mydb

CENTAVO = Decimal("0.01")
TOPE_LEGADO_POR_DEFECTO = 100000
POLITICAS = {
    "Inicial": {"minimo_pie": Decimal("0.40"), "maximo_cuotas": 3, "tope_sugerido": 50000},
    "Recurrente": {"minimo_pie": Decimal("0.25"), "maximo_cuotas": 6, "tope_sugerido": 100000},
    "VIP": {"minimo_pie": Decimal("0.15"), "maximo_cuotas": 6, "tope_sugerido": 200000},
}


def _conexion():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    return conn


def _dinero(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _sumar_meses(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _nivel_credito(creditos_puntuales: int) -> str:
    if creditos_puntuales < 2:
        return "Inicial"
    if creditos_puntuales < 6:
        return "Recurrente"
    return "VIP"


def _tope_nivel_credito(nivel: str, tope_cliente: int | Decimal | None) -> int:
    cap = POLITICAS[nivel]["tope_sugerido"]
    client_cap = int(tope_cliente or 0)
    if client_cap and client_cap != TOPE_LEGADO_POR_DEFECTO:
        cap = min(cap, client_cap)
    return int(cap)


def asegurar_esquema_credito(cursor) -> None:
    """Crea las tablas nuevas de abonos también en volúmenes Docker existentes."""
    cursor.execute("SHOW COLUMNS FROM producto LIKE 'costo_adquisicion'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE producto ADD COLUMN costo_adquisicion DECIMAL(10,2) NULL")
    cursor.execute("SHOW COLUMNS FROM venta LIKE 'pie_credito'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE venta ADD COLUMN pie_credito DECIMAL(10,2) NOT NULL DEFAULT 0")
    cursor.execute("SHOW COLUMNS FROM venta LIKE 'metodo_pago_pie'")
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE venta ADD COLUMN metodo_pago_pie VARCHAR(20) NOT NULL DEFAULT 'efectivo'"
        )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS abono_credito (
            id_abono INT NOT NULL AUTO_INCREMENT,
            id_credito INT NOT NULL,
            id_usuario INT NOT NULL,
            monto DECIMAL(10,2) NOT NULL,
            fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id_abono),
            KEY idx_abono_credito_fecha (id_credito, fecha),
            CONSTRAINT fk_abono_credito_credito FOREIGN KEY (id_credito) REFERENCES credito (id_credito),
            CONSTRAINT fk_abono_credito_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario),
            CONSTRAINT ck_abono_credito_monto CHECK (monto > 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detalle_abono_credito (
            id_detalle_abono INT NOT NULL AUTO_INCREMENT,
            id_abono INT NOT NULL,
            id_cuota_credito INT NOT NULL,
            monto DECIMAL(10,2) NOT NULL,
            PRIMARY KEY (id_detalle_abono),
            KEY idx_detalle_abono_cuota (id_cuota_credito),
            CONSTRAINT fk_detalle_abono_abono FOREIGN KEY (id_abono) REFERENCES abono_credito (id_abono),
            CONSTRAINT fk_detalle_abono_cuota FOREIGN KEY (id_cuota_credito) REFERENCES cuota_credito (id_cuota_credito),
            CONSTRAINT ck_detalle_abono_monto CHECK (monto > 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for status in ("Vigente", "Pagado"):
        cursor.execute("INSERT IGNORE INTO estado_credito (estado) VALUES (%s)", (status,))


def _estado_id(cursor, status: str) -> int:
    cursor.execute("SELECT id_estado_credito FROM estado_credito WHERE LOWER(estado) = LOWER(%s) LIMIT 1", (status,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO estado_credito (estado) VALUES (%s)", (status,))
        return int(cursor.lastrowid)
    return int(row["id_estado_credito"] if isinstance(row, dict) else row[0])


def _saldo_pendiente(cursor, rut_cliente: int) -> Decimal:
    cursor.execute(
        """
        SELECT COALESCE(SUM(GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0)), 0) AS saldo
        FROM credito cr
        JOIN venta v ON v.id_venta = cr.id_venta
        JOIN cuota_credito q ON q.id_credito = cr.id_credito
        LEFT JOIN (
            SELECT id_cuota_credito, SUM(monto) AS pagado
            FROM detalle_abono_credito GROUP BY id_cuota_credito
        ) p ON p.id_cuota_credito = q.id_cuota_credito
        WHERE v.rut_cliente = %s
        """,
        (rut_cliente,),
    )
    row = cursor.fetchone()
    return _dinero((row or {}).get("saldo", 0))


def _perfil(cursor, rut_cliente: int, *, bloquear: bool = False) -> dict[str, Any]:
    lock = " FOR UPDATE" if bloquear else ""
    cursor.execute(
        f"SELECT rut_cliente, nombre, COALESCE(tope_credito, 0) AS tope_credito FROM cliente WHERE rut_cliente = %s{lock}",
        (rut_cliente,),
    )
    client = cursor.fetchone()
    if client is None:
        raise ValueError("La clienta seleccionada no existe")

    cursor.execute(
        """
        SELECT COUNT(*) AS creditos_puntuales
        FROM credito cr
        JOIN venta v ON v.id_venta = cr.id_venta
        JOIN estado_credito ec ON ec.id_estado_credito = cr.id_estado_credito
        WHERE v.rut_cliente = %s
          AND LOWER(ec.estado) = 'pagado'
          AND NOT EXISTS (
              SELECT 1 FROM cuota_credito q
              WHERE q.id_credito = cr.id_credito
                AND (q.fecha_pago IS NULL OR q.fecha_pago > q.fecha_vencimiento)
          )
        """,
        (rut_cliente,),
    )
    completed = int((cursor.fetchone() or {}).get("creditos_puntuales") or 0)
    level = _nivel_credito(completed)
    policy = POLITICAS[level]
    cap = _tope_nivel_credito(level, client.get("tope_credito"))

    balance = _saldo_pendiente(cursor, rut_cliente)
    cursor.execute(
        """
        SELECT COUNT(*) AS cuotas_vencidas
        FROM cuota_credito q
        JOIN credito cr ON cr.id_credito = q.id_credito
        JOIN venta v ON v.id_venta = cr.id_venta
        LEFT JOIN (
            SELECT id_cuota_credito, SUM(monto) AS pagado
            FROM detalle_abono_credito GROUP BY id_cuota_credito
        ) p ON p.id_cuota_credito = q.id_cuota_credito
        WHERE v.rut_cliente = %s
          AND q.fecha_vencimiento < CURRENT_DATE()
          AND q.monto_cuota > COALESCE(p.pagado, 0)
        """,
        (rut_cliente,),
    )
    overdue = int((cursor.fetchone() or {}).get("cuotas_vencidas") or 0)
    return {
        "nombre": client["nombre"],
        "nivel_credito": level,
        "creditos_puntuales_finalizados": completed,
        "minimo_pie_porcentaje": int(policy["minimo_pie"] * 100),
        "maximo_cuotas": policy["maximo_cuotas"],
        "tope_credito": int(cap),
        "credito_usado": int(balance),
        "credito_disponible": max(int(cap - balance), 0),
        "bloqueada": overdue > 0,
        "cuotas_vencidas": overdue,
    }


def perfil_clienta(rut_cliente: int) -> dict[str, Any]:
    conn = _conexion()
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.commit()
        return _perfil(cursor, int(rut_cliente))
    finally:
        cursor.close()
        conn.close()


def registrar_credito_venta(
    cursor,
    *,
    id_venta: int,
    rut_cliente: int,
    total: Decimal | int | float,
    costo_total: Decimal | int | float,
    pie: Decimal | int | float | None,
    cantidad_cuotas: int,
    fecha_venta: datetime,
) -> dict[str, Any]:
    profile = _perfil(cursor, int(rut_cliente), bloquear=True)
    if profile["bloqueada"]:
        raise ValueError("Crédito Girasol bloqueado: la clienta tiene cuotas vencidas pendientes")

    total_credito = _dinero(total)
    minimo_pie = _dinero(total_credito * Decimal(profile["minimo_pie_porcentaje"]) / 100)
    pie_pagado = _dinero(pie) if pie is not None else minimo_pie
    if pie_pagado < minimo_pie:
        raise ValueError(f"El pie mínimo para nivel {profile['nivel_credito']} es {int(minimo_pie)}")
    if pie_pagado < _dinero(costo_total):
        raise ValueError(f"El pie debe cubrir al menos el costo de adquisición de {int(_dinero(costo_total))}")
    if pie_pagado >= total_credito:
        raise ValueError("El pie debe ser menor que el total de la venta")
    if int(cantidad_cuotas) < 1 or int(cantidad_cuotas) > profile["maximo_cuotas"]:
        raise ValueError(f"El máximo de cuotas para nivel {profile['nivel_credito']} es {profile['maximo_cuotas']}")

    principal = _dinero(total_credito - pie_pagado)
    saldo_con_venta = _dinero(profile["credito_usado"] + principal)
    if saldo_con_venta > profile["tope_credito"]:
        raise ValueError(f"La venta supera el cupo disponible de {profile['credito_disponible']}")

    vigente_id = _estado_id(cursor, "Vigente")
    cursor.execute(
        "INSERT INTO credito (id_venta, id_estado_credito, cantidad_cuotas, pie) VALUES (%s, %s, %s, %s)",
        (id_venta, vigente_id, int(cantidad_cuotas), pie_pagado),
    )
    id_credito = int(cursor.lastrowid)

    base_amount = _dinero(principal / int(cantidad_cuotas))
    amounts = [base_amount] * int(cantidad_cuotas)
    amounts[-1] = _dinero(principal - sum(amounts[:-1]))
    first_due = fecha_venta.date()
    for index, amount in enumerate(amounts, start=1):
        due = _sumar_meses(first_due, index)
        cursor.execute(
            "INSERT INTO cuota_credito (id_credito, numero_cuota, monto_cuota, fecha_vencimiento) VALUES (%s, %s, %s, %s)",
            (id_credito, index, amount, due),
        )

    return {
        "id_credito": id_credito,
        "nivel": profile["nivel_credito"],
        "pie": float(pie_pagado),
        "saldo_financiado": float(principal),
        "cantidad_cuotas": int(cantidad_cuotas),
        "credito_disponible": int(profile["tope_credito"] - saldo_con_venta),
        "minimo_pie_porcentaje": profile["minimo_pie_porcentaje"],
    }


def registrar_abono(id_credito: int, *, monto: int | float | Decimal, id_usuario: int) -> dict[str, Any]:
    amount = _dinero(monto)
    if amount <= 0:
        raise ValueError("El abono debe ser mayor que cero")
    conn = _conexion()
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.start_transaction()
        cursor.execute("SELECT id_credito FROM credito WHERE id_credito = %s FOR UPDATE", (id_credito,))
        if cursor.fetchone() is None:
            raise LookupError("Crédito no encontrado")

        cursor.execute(
            """
            SELECT q.id_cuota_credito, q.numero_cuota, q.monto_cuota, q.fecha_vencimiento,
                   COALESCE(p.pagado, 0) AS pagado
            FROM cuota_credito q
            LEFT JOIN (
                SELECT id_cuota_credito, SUM(monto) AS pagado
                FROM detalle_abono_credito GROUP BY id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            WHERE q.id_credito = %s
            ORDER BY (q.fecha_vencimiento > CURRENT_DATE()), q.fecha_vencimiento, q.numero_cuota
            FOR UPDATE
            """,
            (id_credito,),
        )
        installments = cursor.fetchall()
        balances = []
        for row in installments:
            row["saldo"] = max(_dinero(row["monto_cuota"] - row["pagado"]), Decimal("0.00"))
            if row["saldo"] > 0:
                balances.append(row)
        outstanding = _dinero(sum((row["saldo"] for row in balances), Decimal("0.00")))
        if amount > outstanding:
            raise ValueError(f"El abono supera el saldo pendiente de {int(outstanding)}")

        cursor.execute("INSERT INTO abono_credito (id_credito, id_usuario, monto) VALUES (%s, %s, %s)", (id_credito, id_usuario, amount))
        id_abono = int(cursor.lastrowid)
        remaining = amount
        today = date.today()
        due = [row for row in balances if row["fecha_vencimiento"] <= today]
        future = [row for row in balances if row["fecha_vencimiento"] > today]
        allocation_order = due + list(reversed(future))
        allocations = []
        for row in allocation_order:
            if remaining <= 0:
                break
            applied = min(remaining, row["saldo"])
            cursor.execute(
                "INSERT INTO detalle_abono_credito (id_abono, id_cuota_credito, monto) VALUES (%s, %s, %s)",
                (id_abono, row["id_cuota_credito"], applied),
            )
            remaining = _dinero(remaining - applied)
            allocations.append({"cuota": row["numero_cuota"], "monto": float(applied)})
            if applied == row["saldo"]:
                cursor.execute("UPDATE cuota_credito SET fecha_pago = CURRENT_DATE() WHERE id_cuota_credito = %s", (row["id_cuota_credito"],))

        cursor.execute(
            """
            SELECT COUNT(*) AS pendientes
            FROM cuota_credito q
            LEFT JOIN (
                SELECT id_cuota_credito, SUM(monto) AS pagado
                FROM detalle_abono_credito GROUP BY id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            WHERE q.id_credito = %s AND q.monto_cuota > COALESCE(p.pagado, 0)
            """,
            (id_credito,),
        )
        if int(cursor.fetchone()["pendientes"]) == 0:
            pagado_id = _estado_id(cursor, "Pagado")
            cursor.execute("UPDATE credito SET id_estado_credito = %s WHERE id_credito = %s", (pagado_id, id_credito))
        conn.commit()
        return {"id_abono": id_abono, "monto": float(amount), "saldo_pendiente": float(outstanding - amount), "asignaciones": allocations}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def indicadores_credito() -> dict[str, float | int]:
    conn = _conexion()
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.commit()
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0)), 0) AS saldo_total,
                COALESCE(SUM(CASE WHEN q.fecha_vencimiento < CURRENT_DATE()
                    THEN GREATEST(q.monto_cuota - COALESCE(p.pagado, 0), 0) ELSE 0 END), 0) AS saldo_vencido,
                COALESCE(SUM(p.pagado), 0) AS total_abonado
            FROM cuota_credito q
            LEFT JOIN (
                SELECT id_cuota_credito, SUM(monto) AS pagado
                FROM detalle_abono_credito GROUP BY id_cuota_credito
            ) p ON p.id_cuota_credito = q.id_cuota_credito
            """
        )
        row = cursor.fetchone() or {}
        saldo = _dinero(row.get("saldo_total") or 0)
        vencido = _dinero(row.get("saldo_vencido") or 0)
        cursor.execute(
            """
            SELECT AVG(DATEDIFF(DATE(ab.ultima_fecha), DATE(v.fecha))) AS plazo_medio_dias
            FROM credito cr
            JOIN venta v ON v.id_venta = cr.id_venta
            JOIN (
                SELECT id_credito, MAX(a.fecha) AS ultima_fecha
                FROM abono_credito a GROUP BY id_credito
            ) ab ON ab.id_credito = cr.id_credito
            JOIN estado_credito ec ON ec.id_estado_credito = cr.id_estado_credito
            WHERE LOWER(ec.estado) = 'pagado'
            """
        )
        pmc = float((cursor.fetchone() or {}).get("plazo_medio_dias") or 0)
        cursor.execute("SELECT COALESCE(SUM(monto), 0) AS recuperado_mes FROM abono_credito WHERE MONTH(fecha) = MONTH(CURRENT_DATE()) AND YEAR(fecha) = YEAR(CURRENT_DATE())")
        recovered_month = _dinero((cursor.fetchone() or {}).get("recuperado_mes") or 0)
        cursor.execute("SELECT COALESCE(SUM(v.total - cr.pie), 0) AS otorgado_mes FROM credito cr JOIN venta v ON v.id_venta = cr.id_venta WHERE MONTH(v.fecha) = MONTH(CURRENT_DATE()) AND YEAR(v.fecha) = YEAR(CURRENT_DATE())")
        extended_month = _dinero((cursor.fetchone() or {}).get("otorgado_mes") or 0)
        return {
            "saldo_total_pendiente": float(saldo),
            "monto_cuotas_vencidas": float(vencido),
            "indice_morosidad_pct": float((vencido / saldo * 100) if saldo else 0),
            "total_abonado_historico": float(_dinero(row.get("total_abonado") or 0)),
            "plazo_medio_cobro_dias": round(pmc, 1),
            "rotacion_cartera_pct": float((recovered_month / extended_month * 100) if extended_month else 0),
        }
    finally:
        cursor.close()
        conn.close()
