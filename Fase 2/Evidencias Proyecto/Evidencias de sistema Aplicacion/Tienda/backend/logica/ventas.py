from backend.db.conexion import conectar_db, conectar_mydb
from datetime import datetime, timedelta


def registrar_venta(subtotal, productos, descuento_total, metodo_pago, rut_empleado, cliente_rut=None):
    """Registra una venta usando precios/stock canónicos y devuelve su identificador."""
    if not productos:
        raise ValueError("La venta debe contener al menos un producto")
    rut_empleado = str(rut_empleado or "").strip()
    if not rut_empleado:
        raise ValueError("La venta requiere un empleado autenticado")
    if metodo_pago not in {"efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro"}:
        raise ValueError("Método de pago inválido")

    # Consolida productos repetidos para validar el stock total una sola vez.
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

    sqlite_conn = conectar_db()
    mysql_conn = conectar_mydb()
    if mysql_conn is None:
        sqlite_conn.close()
        raise ConnectionError("No fue posible conectar con MariaDB")
    mysql_cursor = mysql_conn.cursor()
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
            raise ValueError(
                f"El subtotal no coincide con los precios vigentes: esperado {subtotal_calculado}"
            )
        descuento = int(descuento_total)
        if descuento < 0 or descuento > subtotal_calculado:
            raise ValueError("El descuento debe estar entre cero y el subtotal")

        mysql_cursor.execute("SELECT 1 FROM usuario WHERE rut=%s", (rut_empleado,))
        if mysql_cursor.fetchone() is None:
            raise ValueError(f"El empleado {rut_empleado} no existe")

        total = subtotal_calculado - descuento
        credito_info = None
        cliente_numero = None
        if metodo_pago == "credito_girasol":
            raw_rut = str(cliente_rut or "").strip().replace(".", "")
            if not raw_rut:
                raise ValueError("Selecciona una clienta para usar Crédito Girasol")
            try:
                cliente_numero = int(raw_rut.split("-", 1)[0])
            except ValueError as exc:
                raise ValueError("El RUT de la clienta no es válido") from exc
            mysql_cursor.execute("SELECT nombre, COALESCE(tope_credito, 0) FROM cliente WHERE rut=%s FOR UPDATE", (cliente_numero,))
            client_row = mysql_cursor.fetchone()
            if client_row is None:
                raise ValueError("La clienta seleccionada no existe")
            mysql_cursor.execute("""
                SELECT COALESCE(SUM(CASE WHEN estado <> 3 THEN
                    CASE WHEN precio_cuota IS NULL THEN cuotas_por_pagar
                         ELSE precio_cuota * cuotas_por_pagar END ELSE 0 END), 0)
                FROM hoja_credito WHERE cliente=%s
            """, (cliente_numero,))
            usado = int(mysql_cursor.fetchone()[0] or 0)
            tope = int(client_row[1] or 0)
            disponible = max(tope - usado, 0)
            if total > disponible:
                raise ValueError(f"Crédito insuficiente: disponible ${disponible:,}".replace(",", "."))
            credito_info = {"cliente_rut": cliente_numero, "tope": tope, "usado_anterior": usado,
                            "disponible_anterior": disponible, "disponible": disponible - total}

        mysql_cursor.execute(
            "INSERT INTO ventas (fecha, rut_empleado, metodo_pago, subtotal, descuento, total) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (datetime.now(), rut_empleado, metodo_pago, subtotal_calculado, descuento, total),
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
            if actualizado.rowcount != 1:
                raise ValueError(f"Stock modificado durante la venta para {item[1]}")

        if metodo_pago == "credito_girasol":
            mysql_cursor.execute("""
                INSERT INTO hoja_credito
                    (cliente, id_boleta, fecha_pago, cuotas_por_pagar, estado, precio_cuota, pie)
                VALUES (%s, %s, %s, 1, 1, %s, 0)
            """, (cliente_numero, id_venta, (datetime.now() + timedelta(days=30)).date(), total))
        mysql_conn.commit()
        sqlite_conn.commit()
        result = {"id": int(id_venta), "subtotal": subtotal_calculado,
                  "descuento": descuento, "total": total}
        if credito_info is not None:
            result["credito"] = credito_info
        return result
    except Exception:
        mysql_conn.rollback()
        sqlite_conn.rollback()
        raise
    finally:
        mysql_cursor.close()
        mysql_conn.close()
        sqlite_conn.close()
