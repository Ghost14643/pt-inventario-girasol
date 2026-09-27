"""Consultas de inventario sobre la base SQLite local de Girasol."""
from __future__ import annotations
from typing import Any
from backend.db.conexion import conectar_db

STOCK_BAJO_MAXIMO = 5


def _existe_tabla(conn, nombre: str) -> bool:
    return conn.execute(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?)",
        (nombre,),
    ).fetchone()[0] == 1


def _categoria_sql(conn) -> str:
    if not _existe_tabla(conn, "seccionRopa"):
        return "'Sin categoría'"
    return """COALESCE((
        SELECT TRIM(s.nombreSeccionRopa)
        FROM seccionRopa s
        WHERE LOWER(TRIM(p.nombre)) LIKE '%' || LOWER(TRIM(s.nombreSeccionRopa)) || '%'
        ORDER BY LENGTH(TRIM(s.nombreSeccionRopa)) DESC LIMIT 1
    ), 'Sin categoría')"""


def consultar_inventario_ropa(search: str = "", marca: str = "") -> list[dict[str, Any]]:
    """Lista prendas y busca por nombre o código de barras, solo mediante SELECT."""
    conn = conectar_db()
    try:
        categoria_sql = _categoria_sql(conn)
        rows = conn.execute(f"""
            SELECT p.id_prenda AS id, TRIM(p.nombre) AS nombre,
                   TRIM(p.marca) AS marca, p.precio, p.stock,
                   TRIM(p.barcode) AS barcode, {categoria_sql} AS categoria
            FROM prenda p
            WHERE (LOWER(TRIM(p.nombre)) LIKE LOWER(?)
               OR LOWER(TRIM(p.barcode)) LIKE LOWER(?))
              AND (? = '' OR LOWER(TRIM(p.marca)) LIKE LOWER(?))
            ORDER BY TRIM(p.nombre), p.id_prenda
        """, (f"%{search.strip()}%", f"%{search.strip()}%",
              marca.strip(), f"%{marca.strip()}%")).fetchall()
        return [{"id": r["id"], "Prenda": r["nombre"], "tipo": r["categoria"],
                 "Marca": r["marca"], "Precio": r["precio"],
                 "Total Stock": r["stock"], "barcode": r["barcode"]} for r in rows]
    finally:
        conn.close()


def obtener_resumen_inventario(stock_bajo_maximo: int = STOCK_BAJO_MAXIMO) -> dict[str, int]:
    """Obtiene las cuatro métricas con SELECT agregados independientes del listado."""
    conn = conectar_db()
    try:
        row = conn.execute("""
            SELECT COUNT(*) AS prendas_registradas,
                   COALESCE(SUM(CASE WHEN stock > 0 THEN stock ELSE 0 END), 0) AS unidades_disponibles,
                   COALESCE(SUM(CASE WHEN stock <= ? THEN 1 ELSE 0 END), 0) AS stock_bajo
            FROM prenda
        """, (stock_bajo_maximo,)).fetchone()
        marcas = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
        return {"prendas_registradas": int(row["prendas_registradas"] or 0),
                "unidades_disponibles": int(row["unidades_disponibles"] or 0),
                "marcas": int(marcas or 0),
                "stock_bajo": int(row["stock_bajo"] or 0),
                "umbral_stock_bajo": int(stock_bajo_maximo)}
    finally:
        conn.close()


def obtener_categorias() -> list[dict[str, Any]]:
    """Lista secciones si existen; en el esquema reducido usa familiaRopa."""
    conn = conectar_db()
    try:
        if _existe_tabla(conn, "seccionRopa"):
            rows = conn.execute("""
                SELECT s.idSeccionRopa AS id, TRIM(s.nombreSeccionRopa) AS nombre,
                       TRIM(f.nombreFamilia) AS familia
                FROM seccionRopa s JOIN familiaRopa f ON f.idFamiliaRopa=s.idFamiliaRopa
                ORDER BY f.nombreFamilia, s.nombreSeccionRopa
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT idFamiliaRopa AS id, TRIM(nombreFamilia) AS nombre,
                       TRIM(nombreFamilia) AS familia
                FROM familiaRopa ORDER BY nombreFamilia
            """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def obtener_producto_por_codigo(codigo_barra: str) -> dict[str, Any] | None:
    conn = conectar_db()
    try:
        row = conn.execute("""
            SELECT id_prenda AS id, TRIM(nombre) AS nombre, precio, stock,
                   TRIM(barcode) AS barcode, TRIM(marca) AS marca
            FROM prenda WHERE TRIM(barcode)=TRIM(?) LIMIT 1
        """, (codigo_barra,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def crear_prenda(*, nombre: str, marca: str | None, precio: int, stock: int,
                  barcode: str | None = None, tipo: str | None = None) -> dict[str, Any]:
    """Alta usada por el API al confirmar un ingreso de mercadería."""
    nombre, marca, barcode = nombre.strip(), (marca or '').strip(), (barcode or '').strip()
    if not nombre or not marca or not barcode:
        raise ValueError("Nombre, marca y código de barra son obligatorios")
    conn = conectar_db()
    try:
        if conn.execute("SELECT 1 FROM prenda WHERE TRIM(barcode)=TRIM(?)", (barcode,)).fetchone():
            raise ValueError("Ya existe una prenda con ese código de barra")
        cursor = conn.execute(
            "INSERT INTO prenda (nombre, marca, precio, stock, barcode) VALUES (?, ?, ?, ?, ?)",
            (nombre, marca, int(precio), int(stock), barcode),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "nombre": nombre, "marca": marca,
                "precio": int(precio), "stock": int(stock), "barcode": barcode}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
