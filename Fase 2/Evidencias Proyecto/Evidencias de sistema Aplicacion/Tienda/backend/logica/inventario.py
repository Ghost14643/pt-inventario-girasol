"""Consultas de inventario sobre MariaDB."""
from __future__ import annotations

from typing import Any

from backend.db.conexion import conectar_mydb

STOCK_BAJO_MAXIMO = 5


def _existe_tabla(conn, nombre: str) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE %s", (nombre,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def consultar_inventario_ropa(search: str = "", marca: str = "") -> list[dict[str, Any]]:
    """Lista productos y calcula stock total por producto usando variantes."""
    conn = conectar_mydb()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT p.id_producto AS id,
                   TRIM(p.nombre) AS nombre,
                   TRIM(m.nombre) AS marca,
                   p.precio_venta AS precio,
                   COALESCE(SUM(v.stock_actual), 0) AS stock,
                   TRIM(p.codigo_base) AS barcode,
                   'Sin categoría' AS categoria
            FROM producto p
            LEFT JOIN marca m ON m.id_marca = p.id_marca
            LEFT JOIN variante_producto v ON v.id_producto = p.id_producto
            WHERE 1=1
        """
        params: list[Any] = []
        term = (search or "").strip()
        marca_filter = (marca or "").strip()
        if term:
            like = f"%{term}%"
            sql += " AND (LOWER(TRIM(p.nombre)) LIKE LOWER(%s) OR LOWER(TRIM(p.codigo_base)) LIKE LOWER(%s)) "
            params.extend([like, like])
        if marca_filter:
            sql += " AND LOWER(TRIM(m.nombre)) LIKE LOWER(%s) "
            params.append(f"%{marca_filter}%")
        sql += " GROUP BY p.id_producto, p.nombre, m.nombre, p.precio_venta, p.codigo_base ORDER BY TRIM(p.nombre), p.id_producto"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [{
            "id": row["id"],
            "Prenda": row["nombre"],
            "tipo": row["categoria"],
            "Marca": row["marca"],
            "Precio": row["precio"],
            "Total Stock": int(row["stock"] or 0),
            "barcode": row["barcode"],
        } for row in rows]
    finally:
        cursor.close()
        conn.close()


def obtener_resumen_inventario(stock_bajo_maximo: int = STOCK_BAJO_MAXIMO) -> dict[str, int]:
    """Obtiene métricas del inventario usando variantes y marcas."""
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT p.id_producto) AS prendas_registradas,
                COALESCE(SUM(v.stock_actual), 0) AS unidades_disponibles,
                COUNT(DISTINCT CASE WHEN v.stock_actual <= %s THEN p.id_producto END) AS stock_bajo
            FROM producto p
            LEFT JOIN variante_producto v ON v.id_producto = p.id_producto
            """,
            (stock_bajo_maximo,),
        )
        row = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM marca")
        marcas = cursor.fetchone()[0]
        return {
            "prendas_registradas": int(row[0] or 0),
            "unidades_disponibles": int(row[1] or 0),
            "marcas": int(marcas or 0),
            "stock_bajo": int(row[2] or 0),
            "umbral_stock_bajo": int(stock_bajo_maximo),
        }
    finally:
        cursor.close()
        conn.close()


def obtener_categorias() -> list[dict[str, Any]]:
    """En este esquema no hay categorías definidas; devuelve vacío."""
    return []


def obtener_producto_por_codigo(codigo_barra: str) -> dict[str, Any] | None:
    conn = conectar_mydb()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.id_producto AS id,
                   TRIM(p.nombre) AS nombre,
                   p.precio_venta AS precio,
                   COALESCE(SUM(v.stock_actual), 0) AS stock,
                   TRIM(p.codigo_base) AS barcode,
                   TRIM(m.nombre) AS marca
            FROM producto p
            LEFT JOIN marca m ON m.id_marca = p.id_marca
            LEFT JOIN variante_producto v ON v.id_producto = p.id_producto
            WHERE TRIM(p.codigo_base) = TRIM(%s)
            GROUP BY p.id_producto, p.nombre, p.precio_venta, p.codigo_base, m.nombre
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
            "precio": row["precio"],
            "stock": int(row["stock"] or 0),
            "barcode": row["barcode"],
            "marca": row["marca"],
        }
    finally:
        cursor.close()
        conn.close()

def obtener_producto_por_sku(sku: str) -> dict[str, Any] | None:
    conn = conectar_mydb()
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
            # Compatibilidad con las propiedades que ya muestra el carrito.
            "barcode": row["sku"],
            "marca": row["marca"],
        }
    finally:
        cursor.close()
        conn.close()


def crear_prenda(*, nombre: str, marca: str | None, precio: int, stock: int,
                  barcode: str | None = None, tipo: str | None = None) -> dict[str, Any]:
    """Crea producto y su variante inicial usando la estructura MariaDB."""
    nombre = (nombre or "").strip()
    marca = (marca or "").strip()
    barcode = (barcode or "").strip()
    if not nombre or not marca or not barcode:
        raise ValueError("Nombre, marca y código de barra son obligatorios")
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_marca FROM marca WHERE LOWER(TRIM(nombre)) = LOWER(%s) LIMIT 1", (marca,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO marca (nombre) VALUES (%s)", (marca,))
            marca_id = cursor.lastrowid
        else:
            marca_id = row[0]

        cursor.execute(
            "SELECT 1 FROM producto WHERE TRIM(codigo_base) = TRIM(%s) LIMIT 1",
            (barcode,),
        )
        if cursor.fetchone():
            raise ValueError("Ya existe una prenda con ese código de barra")

        cursor.execute(
            "INSERT INTO producto (id_marca, codigo_base, nombre, descripcion, precio_venta) VALUES (%s, %s, %s, %s, %s)",
            (marca_id, barcode, nombre, f"Creado desde la app. {' / '.join(filter(None, [tipo])) or ''}", int(precio)),
        )
        producto_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO variante_producto (id_producto, sku, talla, color, stock_actual) VALUES (%s, %s, %s, %s, %s)",
            (producto_id, barcode, "UN", "GEN", int(stock)),
        )
        conn.commit()
        return {"id": producto_id, "nombre": nombre, "marca": marca, "precio": int(precio), "stock": int(stock), "barcode": barcode}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
