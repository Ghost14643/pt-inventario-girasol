from datetime import datetime

from backend.db.conexion import conectar_mydb


def _rut_numero(rut):
    raw = str(rut).strip().replace(".", "").replace(" ", "")
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    return int(raw)


def registrar_venta(subtotal, productos, descuento_total, metodo_pago, rut_empleado, cliente_rut=None):
    """Registra una venta usando el esquema MariaDB definido en los SQL de Docker."""
    if not productos:
        raise ValueError("La venta debe contener al menos un producto")

    rut_empleado = str(rut_empleado or "").strip()
    if not rut_empleado:
        raise ValueError("La venta requiere un empleado autenticado")

    if metodo_pago not in {"efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro"}:
        raise ValueError("Método de pago inválido")

    cantidades = {}
    for producto in productos:
        producto_id = producto.get("id")
        sku = producto.get("sku") or producto.get("barcode")
        if producto_id is None and sku is None:
            raise ValueError("Todos los productos deben tener identificador o SKU")
        if sku is not None:
            producto_id = sku
        cantidad = int(producto.get("cantidad", 0))
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        cantidades[str(producto_id)] = cantidades.get(str(producto_id), 0) + cantidad

    mysql_conn = conectar_mydb()
    mysql_cursor = mysql_conn.cursor(dictionary=True)
    try:
        ids = tuple(cantidades.keys())
        if not ids:
            raise ValueError("La venta debe contener al menos un producto")

        placeholders = ", ".join(["%s"] * len(ids))
        mysql_cursor.execute(
            f"""
            SELECT vp.id_variante, vp.id_producto, p.nombre, p.precio_venta,
                   vp.stock_actual AS stock_disponible, vp.sku
            FROM variante_producto vp
            JOIN producto p ON p.id_producto = vp.id_producto
            WHERE vp.sku IN ({placeholders})
            """,
            ids,
        )
        productos_db = mysql_cursor.fetchall()
        productos_map = {str(row["sku"]): row for row in productos_db}

        items = []
        subtotal_calculado = 0
        for clave, cantidad in cantidades.items():
            row = productos_map.get(str(clave))
            if row is None:
                raise ValueError(f"Producto/variante {clave} no encontrado")

            stock_disponible = int(row["stock_disponible"] or 0)
            if cantidad > stock_disponible:
                raise ValueError(f"Stock insuficiente para {row['nombre']}: disponible {stock_disponible}")

            precio_unitario = int(float(row["precio_venta"]))
            total_item = cantidad * precio_unitario
            subtotal_calculado += total_item
            items.append((int(row["id_producto"]), int(row["id_variante"]), row["nombre"], cantidad, precio_unitario, total_item))

        if int(subtotal) != subtotal_calculado:
            raise ValueError(f"El subtotal no coincide con los precios vigentes: esperado {subtotal_calculado}")

        descuento = int(descuento_total)
        if descuento < 0 or descuento > subtotal_calculado:
            raise ValueError("El descuento debe estar entre cero y el subtotal")

        empleado_rut = _rut_numero(rut_empleado)
        mysql_cursor.execute("SELECT id_usuario FROM usuario WHERE rut_usuario = %s", (empleado_rut,))
        empleado = mysql_cursor.fetchone()
        if empleado is None:
            raise ValueError(f"El empleado {rut_empleado} no existe")

        if metodo_pago == "credito_girasol":
            raw_rut = str(cliente_rut or "").strip().replace(".", "")
            if not raw_rut:
                raise ValueError("Selecciona una clienta para usar Crédito Girasol")
            try:
                cliente_rut_num = _rut_numero(raw_rut)
            except ValueError as exc:
                raise ValueError("El RUT de la clienta no es válido") from exc
            mysql_cursor.execute("SELECT rut_cliente, dvrut_cliente FROM cliente WHERE rut_cliente = %s", (cliente_rut_num,))
            cliente_row = mysql_cursor.fetchone()
            if cliente_row is None:
                raise ValueError("La clienta seleccionada no existe")

        mysql_cursor.execute(
        "SELECT id_metodo_pago FROM metodo_pago WHERE LOWER(nombre) = %s LIMIT 1",
        (metodo_pago,),
)
        metodo = mysql_cursor.fetchone()
        if metodo is None:
            raise ValueError(f"El método de pago {metodo_pago} no existe")

        total = subtotal_calculado - descuento
        mysql_cursor.execute(
            "INSERT INTO venta (fecha, id_usuario, rut_cliente, id_metodo_pago, subtotal, descuento, total) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (datetime.now(), empleado["id_usuario"], None if metodo_pago != "credito_girasol" else cliente_rut_num, metodo["id_metodo_pago"], subtotal_calculado, descuento, total),
        )
        id_venta = mysql_cursor.lastrowid

        for producto_id, id_variante, nombre_producto, cantidad, precio_unitario, total_producto in items:
            mysql_cursor.execute(
                "INSERT INTO detalle_venta (id_venta, id_variante, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
                (id_venta, id_variante, cantidad, precio_unitario),
            )
            mysql_cursor.execute(
                "UPDATE variante_producto SET stock_actual = stock_actual - %s WHERE id_variante = %s AND stock_actual >= %s LIMIT 1",
                (cantidad, id_variante, cantidad),
            )
            if mysql_cursor.rowcount != 1:
                raise ValueError(f"No se pudo descontar stock del producto {nombre_producto}")

            mysql_cursor.execute(
                """
                INSERT INTO movimiento_stock
                    (id_variante, tipo, cantidad, referencia, id_usuario)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    id_variante,
                    "Salida",
                    cantidad,
                    f"Venta {id_venta}",
                    empleado["id_usuario"],
                ),
            )
            

        mysql_conn.commit()
        result = {"id": int(id_venta), "subtotal": subtotal_calculado, "descuento": descuento, "total": total}
        if metodo_pago == "credito_girasol":
            result["credito"] = {"disponible": 0.0}
        return result
    except Exception:
        mysql_conn.rollback()
        raise
    finally:
        mysql_cursor.close()
        mysql_conn.close()