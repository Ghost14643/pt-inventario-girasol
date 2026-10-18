from __future__ import annotations

from typing import Any

from backend.db.mariadb import conectar_mariadb


def obtener_variante_por_codigo(codigo: str) -> dict[str, Any] | None:
    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                vp.id_variante,
                vp.sku,
                vp.stock_actual,
                p.id_producto,
                p.codigo_base,
                p.nombre,
                p.descripcion,
                p.precio_venta,
                m.id_marca,
                m.nombre AS marca
            FROM variante_producto vp
            INNER JOIN producto p
                ON p.id_producto = vp.id_producto
            INNER JOIN marca m
                ON m.id_marca = p.id_marca
            WHERE vp.sku = %s
               OR p.codigo_base = %s
            LIMIT 1
            """,
            (codigo, codigo),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def listar_metodos_pago_activos() -> list[dict[str, Any]]:
    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id_metodo_pago, nombre
            FROM metodo_pago
            WHERE activo = 1
            ORDER BY nombre
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def obtener_usuario_activo_por_rut(rut_usuario: int) -> dict[str, Any] | None:
    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id_usuario, rut_usuario, nombre, id_rol
            FROM usuario
            WHERE rut_usuario = %s
              AND activo = 1
            LIMIT 1
            """,
            (rut_usuario,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()