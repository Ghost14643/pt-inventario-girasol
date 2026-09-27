from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from backend.db.mariadb import conectar_mariadb


CENTAVO = Decimal("0.01")


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _normalizar_items(items: list[dict[str, Any]]) -> list[dict[str, int]]:
    if not items:
        raise ValueError("La venta debe contener al menos un producto")

    cantidades: dict[int, int] = {}

    for item in items:
        try:
            id_variante = int(item["id_variante"])
            cantidad = int(item["cantidad"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Cada producto debe tener id_variante y cantidad válidos"
            ) from exc

        if id_variante <= 0:
            raise ValueError("El id_variante debe ser mayor que cero")

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")

        cantidades[id_variante] = cantidades.get(id_variante, 0) + cantidad

    return [
        {"id_variante": id_variante, "cantidad": cantidad}
        for id_variante, cantidad in sorted(cantidades.items())
    ]


def registrar_venta(
    *,
    id_usuario: int,
    id_metodo_pago: int,
    items: list[dict[str, Any]],
    descuento: Decimal | int | float | str = Decimal("0"),
    rut_cliente: int | None = None,
) -> dict[str, Any]:
    """Registra una venta completa en una única transacción MariaDB."""

    try:
        id_usuario = int(id_usuario)
        id_metodo_pago = int(id_metodo_pago)
    except (TypeError, ValueError) as exc:
        raise ValueError("El usuario y el método de pago deben ser válidos") from exc

    if id_usuario <= 0:
        raise ValueError("El id_usuario debe ser mayor que cero")

    if id_metodo_pago <= 0:
        raise ValueError("El id_metodo_pago debe ser mayor que cero")

    items_normalizados = _normalizar_items(items)
    descuento = _decimal(descuento)

    if descuento < 0 or descuento > 100:
        raise ValueError("El descuento debe estar entre 0 y 100")

    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT id_usuario
            FROM usuario
            WHERE id_usuario = %s
              AND activo = 1
            FOR UPDATE
            """,
            (id_usuario,),
        )
        if cursor.fetchone() is None:
            raise ValueError("El usuario no existe o está inactivo")

        cursor.execute(
            """
            SELECT id_metodo_pago
            FROM metodo_pago
            WHERE id_metodo_pago = %s
              AND activo = 1
            FOR UPDATE
            """,
            (id_metodo_pago,),
        )
        if cursor.fetchone() is None:
            raise ValueError("El método de pago no existe o está inactivo")

        if rut_cliente is not None:
            try:
                rut_cliente = int(rut_cliente)
            except (TypeError, ValueError) as exc:
                raise ValueError("El RUT del cliente no es válido") from exc

            cursor.execute(
                """
                SELECT rut_cliente
                FROM cliente
                WHERE rut_cliente = %s
                """,
                (rut_cliente,),
            )
            if cursor.fetchone() is None:
                raise ValueError("El cliente no existe")

        productos: list[dict[str, Any]] = []
        subtotal = Decimal("0")

        for item in items_normalizados:
            cursor.execute(
                """
                SELECT
                    vp.id_variante,
                    vp.stock_actual,
                    p.nombre,
                    p.precio_venta
                FROM variante_producto vp
                INNER JOIN producto p
                    ON p.id_producto = vp.id_producto
                WHERE vp.id_variante = %s
                FOR UPDATE
                """,
                (item["id_variante"],),
            )
            producto = cursor.fetchone()

            if producto is None:
                raise ValueError(
                    f"La variante {item['id_variante']} no existe"
                )

            stock_actual = int(producto["stock_actual"])
            cantidad = item["cantidad"]

            if stock_actual < cantidad:
                raise ValueError(
                    f"Stock insuficiente para la variante "
                    f"{item['id_variante']}: disponible {stock_actual}"
                )

            precio_unitario = _decimal(producto["precio_venta"])
            subtotal_linea = _decimal(precio_unitario * cantidad)
            subtotal += subtotal_linea

            productos.append(
                {
                    "id_variante": item["id_variante"],
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "nombre": producto["nombre"],
                }
            )

        subtotal = _decimal(subtotal)
        total = _decimal(subtotal * (Decimal("1") - descuento / Decimal("100")))

        cursor.execute(
            """
            INSERT INTO venta (
                id_usuario,
                rut_cliente,
                id_metodo_pago,
                subtotal,
                descuento,
                total
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                id_usuario,
                rut_cliente,
                id_metodo_pago,
                subtotal,
                descuento,
                total,
            ),
        )
        id_venta = cursor.lastrowid

        for producto in productos:
            cursor.execute(
                """
                INSERT INTO detalle_venta (
                    id_venta,
                    id_variante,
                    cantidad,
                    precio_unitario
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    id_venta,
                    producto["id_variante"],
                    producto["cantidad"],
                    producto["precio_unitario"],
                ),
            )

            cursor.execute(
                """
                UPDATE variante_producto
                SET stock_actual = stock_actual - %s
                WHERE id_variante = %s
                  AND stock_actual >= %s
                """,
                (
                    producto["cantidad"],
                    producto["id_variante"],
                    producto["cantidad"],
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"No fue posible actualizar el stock de la variante "
                    f"{producto['id_variante']}"
                )

            cursor.execute(
                """
                INSERT INTO movimiento_stock (
                    id_variante,
                    tipo,
                    cantidad,
                    fecha,
                    referencia,
                    id_usuario
                )
                VALUES (%s, 'Salida', %s, NOW(), %s, %s)
                """,
                (
                    producto["id_variante"],
                    producto["cantidad"],
                    f"venta:{id_venta}",
                    id_usuario,
                ),
            )

        connection.commit()

        return {
            "id_venta": int(id_venta),
            "subtotal": subtotal,
            "descuento": descuento,
            "total": total,
            "items": productos,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()