from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from mysql.connector import IntegrityError

from backend.db.mariadb import asegurar_esquema_producto, conectar_mariadb


def aplicar_factura_aprobada(
    factura_id: str,
    items: list[dict[str, Any]],
    id_usuario: int,
) -> dict[str, Any]:
    cantidades: dict[str, int] = {}
    precios: dict[str, tuple[Decimal, Decimal | None]] = {}
    for item in items:
        sku = str(item.get("sku", "")).strip()
        cantidad = int(item.get("cantidad", 0))
        if not sku or cantidad <= 0:
            raise ValueError("Cada línea debe tener un código y una cantidad mayor que cero")
        try:
            precio_venta = Decimal(str(item.get("precio_venta")))
            precio_costo_value = item.get("precio_costo")
            precio_costo = (
                Decimal(str(precio_costo_value))
                if precio_costo_value is not None
                else None
            )
        except InvalidOperation as exc:
            raise ValueError(f"Los precios del producto {sku} no son válidos") from exc
        if not precio_venta.is_finite() or precio_venta < 0:
            raise ValueError(f"Ingresa un precio de venta válido para {sku}")
        if precio_costo is not None and (
            not precio_costo.is_finite() or precio_costo < 0
        ):
            raise ValueError(f"El costo de compra de {sku} no es válido")
        if sku in precios and precios[sku] != (precio_venta, precio_costo):
            raise ValueError(
                f"Las líneas de {sku} tienen precios distintos; "
                "usa el mismo precio por código"
            )
        cantidades[sku] = cantidades.get(sku, 0) + cantidad
        precios[sku] = (precio_venta, precio_costo)
    if not cantidades:
        raise ValueError("Agrega al menos un producto antes de aprobar la factura")

    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)
    try:
        asegurar_esquema_producto(cursor)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingreso_factura_aprobada (
                factura_id VARCHAR(24) NOT NULL,
                aprobada_por INT NOT NULL,
                fecha_aprobacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (factura_id),
                CONSTRAINT fk_ingreso_factura_usuario
                    FOREIGN KEY (aprobada_por) REFERENCES usuario (id_usuario)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        connection.commit()
        connection.start_transaction()
        try:
            cursor.execute(
                """
                INSERT INTO ingreso_factura_aprobada (factura_id, aprobada_por)
                VALUES (%s, %s)
                """,
                (factura_id, id_usuario),
            )
        except IntegrityError:
            connection.rollback()
            cursor.execute(
                "SELECT factura_id FROM ingreso_factura_aprobada WHERE factura_id = %s",
                (factura_id,),
            )
            if cursor.fetchone() is not None:
                return {"ya_aplicada": True, "items": []}
            raise

        movimientos: list[dict[str, Any]] = []
        productos: list[dict[str, Any]] = []
        for sku, cantidad in sorted(cantidades.items()):
            cursor.execute(
                """
                SELECT vp.id_variante, p.id_producto, p.nombre
                FROM variante_producto AS vp
                INNER JOIN producto AS p ON p.id_producto = vp.id_producto
                WHERE TRIM(vp.sku) = %s AND p.activo = 1
                FOR UPDATE
                """,
                (sku,),
            )
            producto = cursor.fetchone()
            if producto is None:
                raise LookupError(
                    f"No existe un producto activo con el código {sku}"
                )

            id_variante = int(producto["id_variante"])
            productos.append(
                {
                    "id_producto": int(producto["id_producto"]),
                    "nombre": producto["nombre"],
                    "precio_venta": precios[sku][0],
                    "precio_costo": precios[sku][1],
                }
            )
            cursor.execute(
                """
                UPDATE variante_producto
                SET stock_actual = stock_actual + %s
                WHERE id_variante = %s
                """,
                (cantidad, id_variante),
            )
            cursor.execute(
                """
                INSERT INTO movimiento_stock
                    (id_variante, tipo, cantidad, referencia, id_usuario)
                VALUES (%s, 'Entrada', %s, %s, %s)
                """,
                (id_variante, cantidad, f"Factura {factura_id}", id_usuario),
            )
            movimientos.append(
                {
                    "sku": sku,
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                }
            )

        precios_producto: dict[int, dict[str, Any]] = {}
        for producto in productos:
            id_producto = producto["id_producto"]
            previous = precios_producto.get(id_producto)
            current = (producto["precio_venta"], producto["precio_costo"])
            if previous is not None and (
                previous["precio_venta"] != current[0]
                or (
                    current[1] is not None
                    and previous["precio_costo"] is not None
                    and previous["precio_costo"] != current[1]
                )
            ):
                raise ValueError(
                    f"Las variantes de {producto['nombre']} tienen precios distintos"
                )
            precios_producto[id_producto] = {
                "nombre": producto["nombre"],
                "precio_venta": current[0],
                "precio_costo": current[1]
                if current[1] is not None
                else (previous or {}).get("precio_costo"),
            }

        for id_producto, precio in precios_producto.items():
            cursor.execute(
                """
                UPDATE producto
                SET precio_venta = %s,
                    costo_adquisicion = COALESCE(%s, costo_adquisicion)
                WHERE id_producto = %s
                """,
                (
                    precio["precio_venta"],
                    precio["precio_costo"],
                    id_producto,
                ),
            )

        connection.commit()
        return {"ya_aplicada": False, "items": movimientos}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
