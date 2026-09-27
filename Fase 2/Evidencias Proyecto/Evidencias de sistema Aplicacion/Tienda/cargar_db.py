"""Verificador de esquema para la base de datos real del proyecto."""
from __future__ import annotations

from backend.db.conexion import conectar_mydb


REQUIRED_TABLES = (
    "rol",
    "usuario",
    "marca",
    "producto",
    "variante_producto",
    "metodo_pago",
    "cliente",
    "venta",
    "detalle_venta",
    "estado_credito",
    "credito",
    "cuota_credito",
    "movimiento_stock",
    "arqueo_caja",
    "arqueo_detalle_pago",
)


def verificar_esquema_mariadb() -> dict[str, bool]:
    conn = conectar_mydb()
    cursor = conn.cursor()
    try:
        result = {}
        for table in REQUIRED_TABLES:
            cursor.execute("SHOW TABLES LIKE %s", (table,))
            result[table] = cursor.fetchone() is not None
        return result
    finally:
        cursor.close(); conn.close()


if __name__ == "__main__":
    tables = verificar_esquema_mariadb()
    missing = [name for name, exists in tables.items() if not exists]
    if missing:
        raise SystemExit(f"Faltan tablas en MariaDB: {missing}")
    print("Esquema MariaDB validado con los scripts 01-create-db.sql y 02-new-schema.sql.")
    print(tables)