"""Consultas de inventario sobre MariaDB."""
from __future__ import annotations

from typing import Any

from backend.db.conexion import conectar_mydb

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
    conn = _connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                vp.id_variante AS id,
                TRIM(p.nombre) AS nombre,
                p.precio_venta AS precio,
                vp.stock_actual AS stock,
                TRIM(vp.sku) AS barcode,
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
            "id": row["id"],
            "nombre": row["nombre"],
            "precio": float(row["precio"] or 0),
            "stock": int(row["stock"] or 0),
            "barcode": row["barcode"],
            "marca": row["marca"],
        }
    finally:
        cursor.close()
        conn.close()


def obtener_producto_por_sku(sku: str) -> dict[str, Any] | None:
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
