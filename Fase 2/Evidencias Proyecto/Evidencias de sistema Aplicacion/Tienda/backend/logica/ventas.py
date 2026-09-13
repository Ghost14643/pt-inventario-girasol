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
        if producto_id is None:
            raise ValueError("Todos los productos deben tener identificador")
        cantidad = int(producto.get("cantidad", 0))
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        cantidades[int(producto_id)] = cantidades.get(int(producto_id), 0) + cantidad

    sqlite_conn = conectar_db()
    mysql_conn = conectar_mydb()
    if mysql_conn is None:
        sqlite_conn.close()
        raise ConnectionError("No fue posible conectar con MariaDB")
    mysql_cursor = mysql_conn.cursor()
    try:
        sqlite_conn.execute("BEGIN IMMEDIATE")
        items = []
        subtotal_calculado = 0
        for producto_id, cantidad in cantidades.items():
            row = sqlite_conn.execute(
                "SELECT id_prenda, TRIM(nombre), precio, stock FROM prenda WHERE id_prenda=?",
                (producto_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Producto {producto_id} no encontrado")
            if cantidad > int(row[3]):
                raise ValueError(f"Stock insuficiente para {row[1]}: disponible {row[3]}")
            total_item = cantidad * int(row[2])
            subtotal_calculado += total_item
            items.append((int(row[0]), row[1], cantidad, int(row[2]), total_item))

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
        for item in items:
            mysql_cursor.execute(
                "INSERT INTO detalle_venta (id_venta, id_producto, nombre_producto, cantidad, "
                "precio_unitario, total_producto) VALUES (%s, %s, %s, %s, %s, %s)",
                (id_venta,) + item,
            )
            actualizado = sqlite_conn.execute(
                "UPDATE prenda SET stock=stock-? WHERE id_prenda=? AND stock>=?",
                (item[2], item[0], item[2]),
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
