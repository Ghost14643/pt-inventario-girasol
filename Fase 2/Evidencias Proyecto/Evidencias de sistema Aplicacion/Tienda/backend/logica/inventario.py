"""Consultas de inventario sobre MariaDB."""
from __future__ import annotations

from typing import Any

from backend.db.conexion import conectar_mydb
from backend.logica.credito import asegurar_esquema_credito

STOCK_BAJO_MAXIMO = 5


def _connection():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    return conn


def consultar_inventario_ropa(search: str = "", marca: str = "") -> list[dict[str, Any]]:
    """Lista variantes de producto con su stock real en MariaDB."""
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        search_term = (search or "").strip()
        marca_term = (marca or "").strip()
        search_like = f"%{search_term}%"
        marca_like = f"%{marca_term}%"

        cursor.execute(
            """
            SELECT
                vp.id_variante AS id,
                TRIM(p.nombre) AS nombre,
                TRIM(m.nombre) AS marca,
                p.precio_venta AS precio,
                vp.stock_actual AS stock,
                TRIM(vp.sku) AS barcode
            FROM variante_producto vp
            JOIN producto p ON p.id_producto = vp.id_producto
            LEFT JOIN marca m ON m.id_marca = p.id_marca
            WHERE (%s = '' OR LOWER(TRIM(p.nombre)) LIKE LOWER(%s) OR LOWER(TRIM(vp.sku)) LIKE LOWER(%s))
              AND (%s = '' OR LOWER(TRIM(m.nombre)) LIKE LOWER(%s))
            ORDER BY p.nombre, vp.id_variante
            """,
            (search_term, search_like, search_like, marca_term, marca_like),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "Prenda": row["nombre"],
                "tipo": "Sin categoría",
                "Marca": row["marca"] or "Sin marca",
                "Precio": float(row["precio"] or 0),
                "Total Stock": int(row["stock"] or 0),
                "barcode": row["barcode"] or "",
            }
            for row in rows
        ]
    finally:
        cursor.close()
        conn.close()


def obtener_resumen_inventario(stock_bajo_maximo: int = STOCK_BAJO_MAXIMO) -> dict[str, int]:
    """Resume inventario usando las tablas reales del catálogo."""
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS prendas_registradas FROM producto")
        prendas = int((cursor.fetchone() or {}).get("prendas_registradas") or 0)

        cursor.execute("SELECT COALESCE(SUM(stock_actual), 0) AS unidades_disponibles FROM variante_producto")
        unidades = int((cursor.fetchone() or {}).get("unidades_disponibles") or 0)

        cursor.execute("SELECT COUNT(*) AS marcas FROM marca")
        marcas = int((cursor.fetchone() or {}).get("marcas") or 0)

        cursor.execute("SELECT COUNT(*) AS stock_bajo FROM variante_producto WHERE stock_actual <= %s", (stock_bajo_maximo,))
        stock_bajo = int((cursor.fetchone() or {}).get("stock_bajo") or 0)

        return {
            "prendas_registradas": prendas,
            "unidades_disponibles": unidades,
            "marcas": marcas,
            "stock_bajo": stock_bajo,
            "umbral_stock_bajo": int(stock_bajo_maximo),
        }
    finally:
        cursor.close()
        conn.close()


def obtener_categorias() -> list[dict[str, Any]]:
    """La base actual no tiene categorías de producto; devuelve vacío para no romper la UI."""
    return []


def obtener_producto_por_codigo(codigo_barra: str) -> dict[str, Any] | None:
    codigo_barra = str(codigo_barra or "").strip()
    if not codigo_barra:
        return None

    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                vp.id_variante AS id,
                vp.id_producto AS id_producto,
                TRIM(p.nombre) AS nombre,
                p.precio_venta AS precio,
                vp.stock_actual AS stock,
                TRIM(vp.sku) AS sku,
                vp.talla AS talla,
                vp.color AS color,
                TRIM(m.nombre) AS marca
            FROM variante_producto vp
            JOIN producto p ON p.id_producto = vp.id_producto
            LEFT JOIN marca m ON m.id_marca = p.id_marca
            WHERE TRIM(vp.sku) = TRIM(%s)
            LIMIT 1
            """,
            (codigo_barra,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return {
            "id": int(row["id"]),
            "id_producto": int(row["id_producto"]),
            "nombre": row["nombre"],
            "precio": float(row["precio"] or 0),
            "stock": int(row["stock"] or 0),
            "sku": row["sku"] or "",
            "barcode": row["sku"] or "",
            "talla": row["talla"] or "",
            "color": row["color"] or "",
            "marca": row["marca"] or "",
        }
    finally:
        cursor.close()
        conn.close()

def registrar_ingreso_mixto(
    items: list[dict[str, Any]],
    id_usuario: int,
) -> dict[str, Any]:
    if not items:
        raise ValueError("Agrega al menos un producto al ingreso")
    if len(items) > 100:
        raise ValueError("El ingreso no puede superar las 100 líneas")

    conn = _connection()
    cursor = conn.cursor(dictionary=True)

    try:
        resultados: list[dict[str, Any]] = []
        variantes_en_lote: set[int] = set()
        codigos_nuevos_en_lote: set[str] = set()

        for index, item in enumerate(items, start=1):
            tipo = item.get("tipo")
            cantidad = item.get("cantidad")

            if isinstance(cantidad, bool) or not isinstance(cantidad, int):
                raise ValueError(f"Línea {index}: la cantidad debe ser un entero")
            if cantidad < 1 or cantidad > 10_000:
                raise ValueError(f"Línea {index}: la cantidad debe estar entre 1 y 10.000")

            referencia = str(item.get("referencia") or "").strip()
            if len(referencia) > 100:
                raise ValueError(f"Línea {index}: la referencia supera los 100 caracteres")

            if tipo == "existente":
                try:
                    id_variante = int(item["id_variante"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Línea {index}: falta una variante válida") from exc

                if id_variante in variantes_en_lote:
                    raise ValueError(
                        f"Línea {index}: la variante está repetida en el ingreso"
                    )
                variantes_en_lote.add(id_variante)

                cursor.execute(
                    """
                    UPDATE variante_producto
                    SET stock_actual = stock_actual + %s
                    WHERE id_variante = %s
                    """,
                    (cantidad, id_variante),
                )
                if cursor.rowcount != 1:
                    raise LookupError(
                        f"Línea {index}: la variante {id_variante} no existe"
                    )

                cursor.execute(
                    """
                    INSERT INTO movimiento_stock (
                        id_variante, tipo, cantidad, fecha, referencia, id_usuario
                    )
                    VALUES (%s, 'Entrada', %s, NOW(), %s, %s)
                    """,
                    (id_variante, cantidad, referencia or None, id_usuario),
                )

                cursor.execute(
                    """
                    SELECT stock_actual
                    FROM variante_producto
                    WHERE id_variante = %s
                    """,
                    (id_variante,),
                )
                stock_actualizado = int(cursor.fetchone()["stock_actual"])

                resultados.append(
                    {
                        "tipo": "existente",
                        "id_variante": id_variante,
                        "stock_actual": stock_actualizado,
                    }
                )
                continue

            if tipo != "nueva":
                raise ValueError(f"Línea {index}: tipo de ingreso no válido")

            nombre = str(item.get("nombre") or "").strip()
            barcode = str(item.get("barcode") or "").strip()
            marca = str(item.get("marca") or "").strip()
            talla = str(item.get("talla") or "").strip() or None
            color = str(item.get("color") or "").strip() or None
            precio = item.get("precio")

            if not nombre or len(nombre) > 100:
                raise ValueError(f"Línea {index}: el nombre es obligatorio y admite hasta 100 caracteres")
            if not barcode or len(barcode) > 50:
                raise ValueError(f"Línea {index}: el código/SKU es obligatorio y admite hasta 50 caracteres")
            if not marca or len(marca) > 50:
                raise ValueError(f"Línea {index}: la marca es obligatoria y admite hasta 50 caracteres")
            if talla and len(talla) > 10:
                raise ValueError(f"Línea {index}: la talla admite hasta 10 caracteres")
            if color and len(color) > 30:
                raise ValueError(f"Línea {index}: el color admite hasta 30 caracteres")
            if isinstance(precio, bool) or not isinstance(precio, int) or precio < 0:
                raise ValueError(f"Línea {index}: el precio debe ser un entero igual o mayor que cero")

            codigo_normalizado = barcode.casefold()
            if codigo_normalizado in codigos_nuevos_en_lote:
                raise ValueError(f"Línea {index}: el código está repetido en el ingreso")
            codigos_nuevos_en_lote.add(codigo_normalizado)

            cursor.execute(
                """
                SELECT id_variante
                FROM variante_producto
                WHERE LOWER(TRIM(sku)) = LOWER(%s)
                LIMIT 1
                """,
                (barcode,),
            )
            if cursor.fetchone():
                raise ValueError(
                    f"Línea {index}: ya existe una variante con el código {barcode}"
                )

            cursor.execute(
                """
                SELECT id_producto
                FROM producto
                WHERE codigo_base = %s
                   OR LOWER(TRIM(nombre)) = LOWER(%s)
                LIMIT 1
                """,
                (barcode, nombre),
            )
            if cursor.fetchone():
                raise ValueError(
                    f"Línea {index}: ya existe una prenda con ese código o nombre"
                )

            cursor.execute(
                """
                SELECT id_marca
                FROM marca
                WHERE LOWER(TRIM(nombre)) = LOWER(%s)
                LIMIT 1
                """,
                (marca,),
            )
            marca_row = cursor.fetchone()
            if marca_row:
                id_marca = int(marca_row["id_marca"])
            else:
                cursor.execute(
                    "INSERT INTO marca (nombre) VALUES (%s)",
                    (marca,),
                )
                id_marca = int(cursor.lastrowid)

            cursor.execute(
                """
                INSERT INTO producto (
                    id_marca, codigo_base, nombre, descripcion, precio_venta
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_marca, barcode, nombre, "Inventario", precio),
            )
            id_producto = int(cursor.lastrowid)

            cursor.execute(
                """
                INSERT INTO variante_producto (
                    id_producto, sku, talla, color, stock_actual
                )
                VALUES (%s, %s, %s, %s, 0)
                """,
                (id_producto, barcode, talla, color),
            )
            id_variante = int(cursor.lastrowid)

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
                INSERT INTO movimiento_stock (
                    id_variante, tipo, cantidad, fecha, referencia, id_usuario
                )
                VALUES (%s, 'Entrada', %s, NOW(), %s, %s)
                """,
                (id_variante, cantidad, referencia or None, id_usuario),
            )

            resultados.append(
                {
                    "tipo": "nueva",
                    "id_variante": id_variante,
                    "nombre": nombre,
                    "sku": barcode,
                    "stock_actual": cantidad,
                }
            )

        conn.commit()
        return {"items": resultados}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def obtener_producto_por_sku(sku: str) -> dict[str, Any] | None:
    sku = str(sku or "").strip()
    if not sku:
        return None

    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.id_producto AS id,
                   TRIM(p.nombre) AS nombre,
                   p.precio_venta AS precio,
                   vp.stock_actual AS stock,
                   TRIM(vp.sku) AS sku,
                   TRIM(m.nombre) AS marca
            FROM variante_producto vp
            JOIN producto p ON p.id_producto = vp.id_producto
            LEFT JOIN marca m ON m.id_marca = p.id_marca
            WHERE TRIM(vp.sku) = TRIM(%s)
            LIMIT 1
            """,
            (sku,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "sku": row["sku"],
            "nombre": row["nombre"],
            "precio": row["precio"],
            "stock": int(row["stock"] or 0),
            "barcode": row["sku"],
            "marca": row["marca"],
        }
    finally:
        cursor.close()
        conn.close()


def crear_prenda(*, nombre: str, marca: str | None, precio: int, stock: int,
                  barcode: str | None = None, tipo: str | None = None) -> dict[str, Any]:
    """Alta de producto usando el esquema real con producto + variante."""
    nombre = nombre.strip()
    marca = (marca or "").strip()
    barcode = (barcode or "").strip()
    if not nombre or not marca or not barcode:
        raise ValueError("Nombre, marca y código de barra son obligatorios")

    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_marca AS id FROM marca WHERE LOWER(TRIM(nombre)) = LOWER(%s)", (marca,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO marca (nombre) VALUES (%s)", (marca,))
            marca_id = int(cursor.lastrowid)
        else:
            marca_id = int(row["id"])

        cursor.execute(
            "SELECT id_producto AS id FROM producto WHERE codigo_base = %s OR LOWER(TRIM(nombre)) = LOWER(%s)",
            (barcode, nombre),
        )
        existing = cursor.fetchone()
        if existing is not None:
            raise ValueError("Ya existe una prenda con ese código o nombre")

        cursor.execute(
            "INSERT INTO producto (id_marca, codigo_base, nombre, descripcion, precio_venta) VALUES (%s, %s, %s, %s, %s)",
            (marca_id, barcode, nombre, tipo or 'Inventario', int(precio)),
        )
        producto_id = int(cursor.lastrowid)
        cursor.execute(
            "INSERT INTO variante_producto (id_producto, sku, talla, color, stock_actual) VALUES (%s, %s, NULL, NULL, %s)",
            (producto_id, barcode, int(stock)),
        )
        conn.commit()
        return {
            "id": producto_id,
            "nombre": nombre,
            "marca": marca,
            "precio": int(precio),
            "stock": int(stock),
            "barcode": barcode,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_costo_adquisicion(codigo_base: str, costo: int | float) -> dict[str, Any]:
    codigo_base = codigo_base.strip()
    if not codigo_base or costo < 0:
        raise ValueError("El código y un costo no negativo son obligatorios")
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    cursor = conn.cursor(dictionary=True)
    try:
        asegurar_esquema_credito(cursor)
        conn.commit()
        cursor.execute(
            "UPDATE producto SET costo_adquisicion = %s WHERE codigo_base = %s",
            (costo, codigo_base),
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT codigo_base FROM producto WHERE codigo_base = %s", (codigo_base,))
            if cursor.fetchone() is None:
                raise LookupError("Producto no encontrado")
        conn.commit()
        return {"codigo_base": codigo_base, "costo_adquisicion": float(costo)}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
