from datetime import datetime
from decimal import Decimal, ROUND_CEILING

from backend.db.conexion import conectar_mydb
from backend.logica.credito import _dinero, _perfil, asegurar_esquema_credito, registrar_credito_venta


def _rut_numero(rut):
    raw = str(rut).strip().replace(".", "").replace(" ", "")
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    return int(raw)


def estimar_pie_credito(productos, cliente_rut):
    if not productos:
        raise ValueError("Agrega al menos un producto para calcular el pie")

    cantidades = {}
    for producto in productos:
        sku = str(producto.get("sku") or producto.get("barcode") or "").strip()
        cantidad = int(producto.get("cantidad", 0))
        if not sku or cantidad <= 0:
            raise ValueError("Cada producto debe tener SKU y cantidad válida")
        cantidades[sku] = cantidades.get(sku, 0) + cantidad

    cliente_rut_num = _rut_numero(cliente_rut)
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.commit()
        skus = tuple(cantidades)
        placeholders = ", ".join(["%s"] * len(skus))
        cursor.execute(
            f"""
            SELECT vp.sku, vp.stock_actual, p.nombre, p.precio_venta,
                   p.costo_adquisicion
            FROM variante_producto vp
            JOIN producto p ON p.id_producto = vp.id_producto
            WHERE vp.sku IN ({placeholders})
            """,
            skus,
        )
        catalog = {str(row["sku"]): row for row in cursor.fetchall()}
        subtotal = 0
        acquisition_cost = Decimal("0")
        for sku, cantidad in cantidades.items():
            row = catalog.get(sku)
            if row is None:
                raise ValueError(f"Producto/variante {sku} no encontrado")
            if cantidad > int(row["stock_actual"] or 0):
                raise ValueError(
                    f"Stock insuficiente para {row['nombre']}: disponible {row['stock_actual']}"
                )
            if row["costo_adquisicion"] is None:
                raise ValueError(
                    f"Configura el costo de adquisición de {row['nombre']} antes de vender a crédito"
                )
            subtotal += int(float(row["precio_venta"])) * cantidad
            acquisition_cost += Decimal(str(row["costo_adquisicion"])) * cantidad

        profile = _perfil(cursor, cliente_rut_num)
        percentage_minimum = _dinero(
            Decimal(subtotal) * Decimal(profile["minimo_pie_porcentaje"]) / 100
        )
        credit_limit_minimum = max(
            _dinero(Decimal(subtotal) - Decimal(profile["credito_disponible"])),
            Decimal("0.00"),
        )
        required_down = max(
            percentage_minimum,
            _dinero(acquisition_cost),
            credit_limit_minimum,
        )
        required_down_pesos = int(
            required_down.to_integral_value(rounding=ROUND_CEILING)
        )
        return {
            "total": subtotal,
            "pie_requerido": required_down_pesos,
            "saldo_financiado": max(subtotal - required_down_pesos, 0),
            "credito_disponible": int(profile["credito_disponible"]),
            "nivel_credito": profile["nivel_credito"],
            "minimo_pie_porcentaje": profile["minimo_pie_porcentaje"],
            "maximo_cuotas": profile["maximo_cuotas"],
            "bloqueada": profile["bloqueada"],
            "cuotas_vencidas": profile["cuotas_vencidas"],
            "puede_financiar": not profile["bloqueada"] and required_down_pesos < subtotal,
        }
    finally:
        cursor.close()
        conn.close()


def registrar_venta(
    subtotal,
    productos,
    descuento_total,
    metodo_pago,
    rut_empleado,
    cliente_rut=None,
    ultimos_4_digitos=None,
    codigo_autorizacion=None,
    numero_comprobante=None,
    cantidad_cuotas=1,
    marca_tarjeta=None,
    pie_credito=None,
    cuotas_credito=3,
    metodo_pago_pie="efectivo",
):
    """Registra una venta usando el esquema MariaDB definido en los SQL de Docker."""
    if not productos:
        raise ValueError("La venta debe contener al menos un producto")

    rut_empleado = str(rut_empleado or "").strip()
    if not rut_empleado:
        raise ValueError("La venta requiere un empleado autenticado")

    if metodo_pago not in {"efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro"}:
        raise ValueError("Método de pago inválido")

    if metodo_pago_pie not in {"efectivo", "debito"}:
        raise ValueError("El método de pago del pie debe ser efectivo o débito")
    if metodo_pago != "credito_girasol" and metodo_pago_pie != "efectivo":
        raise ValueError("El método de pago del pie solo aplica a Crédito Girasol")

    es_pago_tarjeta = metodo_pago in {"debito", "credito"} or (
        metodo_pago == "credito_girasol" and metodo_pago_pie == "debito"
    )
    metodo_pago_tarjeta = (
        metodo_pago if metodo_pago in {"debito", "credito"} else metodo_pago_pie
    )

    if es_pago_tarjeta:
        ultimos_4_digitos = str(ultimos_4_digitos or "").strip()
        codigo_autorizacion = str(codigo_autorizacion or "").strip()
        numero_comprobante = str(numero_comprobante or "").strip()

        if (
            len(ultimos_4_digitos) != 4
            or not ultimos_4_digitos.isascii()
            or not ultimos_4_digitos.isdigit()
        ):
            raise ValueError("Los últimos 4 dígitos de la tarjeta son obligatorios y deben ser numéricos")

        if not codigo_autorizacion or len(codigo_autorizacion) > 20:
            raise ValueError("El código de autorización es obligatorio y no debe superar 20 caracteres")

        if not numero_comprobante or len(numero_comprobante) > 30:
            raise ValueError("El número de comprobante es obligatorio y no debe superar 30 caracteres")

        try:
            cantidad_cuotas = int(cantidad_cuotas)
        except (TypeError, ValueError) as exc:
            raise ValueError("La cantidad de cuotas debe ser válida") from exc

        if cantidad_cuotas < 1:
            raise ValueError("La cantidad de cuotas debe ser mayor que cero")

        if metodo_pago_tarjeta == "debito":
            cantidad_cuotas = 1

        marca_tarjeta = str(marca_tarjeta or "").strip() or None
        if marca_tarjeta is not None and len(marca_tarjeta) > 30:
            raise ValueError("La marca de tarjeta no debe superar 30 caracteres")

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
    if mysql_conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    mysql_cursor = mysql_conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(mysql_cursor)
        mysql_conn.commit()
        mysql_conn.start_transaction()
        ids = tuple(cantidades.keys())
        if not ids:
            raise ValueError("La venta debe contener al menos un producto")

        placeholders = ", ".join(["%s"] * len(ids))
        mysql_cursor.execute(
            f"""
                 SELECT vp.id_variante, vp.id_producto, p.nombre, p.precio_venta,
                     p.costo_adquisicion,
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
        costo_total = Decimal("0")
        costo_configurado = True
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
            if row["costo_adquisicion"] is None:
                costo_configurado = False
            else:
                costo_total += Decimal(str(row["costo_adquisicion"])) * cantidad
            items.append((int(row["id_producto"]), int(row["id_variante"]), row["nombre"], cantidad, precio_unitario, total_item))

        if int(subtotal) != subtotal_calculado:
            raise ValueError(f"El subtotal no coincide con los precios vigentes: esperado {subtotal_calculado}")

        try:
            descuento = int(descuento_total)
        except (TypeError, ValueError) as exc:
            raise ValueError("El descuento debe ser un porcentaje válido") from exc

        if descuento < 0 or descuento > 100:
            raise ValueError("El descuento debe estar entre 0 y 100 por ciento")

        monto_descuento = (subtotal_calculado * descuento + 50) // 100

        empleado_rut = _rut_numero(rut_empleado)
        mysql_cursor.execute("SELECT id_usuario FROM usuario WHERE rut_usuario = %s", (empleado_rut,))
        empleado = mysql_cursor.fetchone()
        if empleado is None:
            raise ValueError(f"El empleado {rut_empleado} no existe")

        if metodo_pago == "credito_girasol":
            if not costo_configurado:
                raise ValueError("Configura el costo de adquisición de todos los productos antes de vender a crédito")
            raw_rut = str(cliente_rut or "").strip().replace(".", "")
            if not raw_rut:
                raise ValueError("Selecciona una clienta para usar Crédito Girasol")
            try:
                cliente_rut_num = _rut_numero(raw_rut)
            except ValueError as exc:
                raise ValueError("El RUT de la clienta no es válido") from exc
            mysql_cursor.execute("SELECT rut_cliente, dvrut_cliente FROM cliente WHERE rut_cliente = %s FOR UPDATE", (cliente_rut_num,))
            cliente_row = mysql_cursor.fetchone()
            if cliente_row is None:
                raise ValueError("La clienta seleccionada no existe")

        nombres_metodo = {
            "efectivo": "efectivo",
            "debito": "débito",
            "credito": "crédito",
            "credito_girasol": "crédito girasol",
            "transferencia": "transferencia",
            "otro": "otro",
        }
        mysql_cursor.execute(
        "SELECT id_metodo_pago FROM metodo_pago WHERE LOWER(nombre) = %s LIMIT 1",
        (nombres_metodo[metodo_pago],),
)
        metodo = mysql_cursor.fetchone()
        if metodo is None:
            raise ValueError(f"El método de pago {metodo_pago} no existe")

        total = subtotal_calculado - monto_descuento
        mysql_cursor.execute(
            "INSERT INTO venta (fecha, id_usuario, rut_cliente, id_metodo_pago, subtotal, descuento, total) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (datetime.now(), empleado["id_usuario"], None if metodo_pago != "credito_girasol" else cliente_rut_num, metodo["id_metodo_pago"], subtotal_calculado, descuento, total),
        )
        id_venta = mysql_cursor.lastrowid

        credito_result = None
        if metodo_pago == "credito_girasol":
            credito_result = registrar_credito_venta(
                mysql_cursor,
                id_venta=int(id_venta),
                rut_cliente=cliente_rut_num,
                total=total,
                costo_total=costo_total,
                pie=pie_credito,
                cantidad_cuotas=cuotas_credito,
                fecha_venta=datetime.now(),
            )
            mysql_cursor.execute(
                "UPDATE venta SET pie_credito = %s, metodo_pago_pie = %s WHERE id_venta = %s",
                (credito_result["pie"], metodo_pago_pie, id_venta),
            )

        if es_pago_tarjeta:
            mysql_cursor.execute(
                """
                INSERT INTO pago_tarjeta (
                    id_venta,
                    ultimos_4_digitos,
                    codigo_autorizacion,
                    numero_comprobante,
                    cantidad_cuotas,
                    marca_tarjeta
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    id_venta,
                    ultimos_4_digitos,
                    codigo_autorizacion,
                    numero_comprobante,
                    cantidad_cuotas,
                    marca_tarjeta,
                ),
            )

        for producto_id, id_variante, nombre_producto, cantidad, precio_unitario, _total_producto in items:
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
            result["credito"] = credito_result
        return result
    except Exception:
        mysql_conn.rollback()
        raise
    finally:
        mysql_cursor.close()
        mysql_conn.close()