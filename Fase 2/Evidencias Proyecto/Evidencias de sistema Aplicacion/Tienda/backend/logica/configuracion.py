"""Gestiones administrativas sobre usuarios, roles y descuentos."""
from __future__ import annotations

from typing import Any

import mysql.connector
from mysql.connector import Error, IntegrityError

from backend.db.conexion import conectar_mydb
from backend.logica.user import hashear_contraseña


def _db():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    return conn


def listar_usuarios() -> list[dict[str, Any]]:
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                u.id_usuario,
                u.rut_usuario AS rut,
                u.dvrut_usuario AS digito_ver,
                u.nombre,
                u.id_rol,
                r.nombre_rol AS rol
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            ORDER BY u.nombre, u.rut_usuario
            """
        )
        return [{**row, "rut": int(row["rut"]), "digito_ver": row["digito_ver"]} for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def listar_roles() -> list[dict[str, Any]]:
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_rol AS id, nombre_rol AS nombre FROM rol ORDER BY id_rol")
        return list(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


def crear_empleado(*, rut: str, nombre: str, clave: str):
    raw = str(rut).strip().replace(".", "")
    if "-" not in raw:
        raise ValueError("El RUT debe incluir dígito verificador")
    number_text, dv = raw.rsplit("-", 1)
    if not number_text.isdigit() or len(dv) != 1:
        raise ValueError("El RUT ingresado no es válido")
    nombre = nombre.strip()
    if len(nombre) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres")
    if len(clave) < 8:
        raise ValueError("La clave debe tener al menos 8 caracteres")

    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_rol FROM rol WHERE LOWER(nombre_rol) IN ('empleado', 'employee') ORDER BY id_rol LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            raise ValueError("No existe un rol empleado configurado")
        role_id = int(row["id_rol"])

        cursor.execute(
            "INSERT INTO usuario (rut_usuario, dvrut_usuario, nombre, id_rol, password) VALUES (%s, %s, %s, %s, %s)",
            (int(number_text), dv.upper(), nombre, role_id, hashear_contraseña(clave)),
        )
        conn.commit()
        return {"rut": int(number_text), "digito_ver": dv.upper(), "nombre": nombre, "id_rol": role_id, "rol": "empleado"}
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Ya existe un usuario con ese RUT") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def eliminar_empleado(rut: str):
    raw = str(rut).strip().replace(".", "").split("-", 1)[0]
    if not raw.isdigit():
        raise ValueError("El RUT ingresado no es válido")

    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT u.nombre, LOWER(r.nombre_rol) AS rol
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.rut_usuario = %s
            """,
            (int(raw),),
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Usuario no encontrado")
        if row["rol"] not in ("empleado", "employee"):
            raise PermissionError("Solo se pueden eliminar usuarios con rol empleado")

        cursor.execute("DELETE FROM usuario WHERE rut_usuario = %s", (int(raw),))
        conn.commit()
        return {"rut": int(raw), "nombre": row["nombre"], "deleted": True}
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("No se puede eliminar: el empleado tiene movimientos asociados") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_rol(rut: str, id_rol: int):
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT LOWER(nombre_rol) AS nombre_rol FROM rol WHERE id_rol = %s", (id_rol,))
        target = cursor.fetchone()
        if target is None:
            raise ValueError("El rol seleccionado no existe")

        cursor.execute(
            """
            SELECT LOWER(r.nombre_rol) AS nombre_rol
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.rut_usuario = %s
            """,
            (int(str(rut).split('-', 1)[0].strip().replace('.', '')),),
        )
        current = cursor.fetchone()
        if current is None:
            raise LookupError("Usuario no encontrado")

        protected = {"admin", "administrador", "developer", "desarrollador"}
        if current["nombre_rol"] in protected and target["nombre_rol"] != current["nombre_rol"]:
            raise PermissionError("Los roles admin y developer están protegidos y no pueden degradarse")

        cursor.execute("UPDATE usuario SET id_rol = %s WHERE rut_usuario = %s", (id_rol, int(str(rut).split('-', 1)[0].strip().replace('.', ''))))
        if cursor.rowcount == 0:
            raise LookupError("Usuario no encontrado")
        conn.commit()
        return {"rut": str(rut), "id_rol": id_rol}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def cambiar_clave(rut: str, nueva_clave: str):
    if len(nueva_clave) < 8:
        raise ValueError("La nueva clave debe tener al menos 8 caracteres")
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET password = %s WHERE rut_usuario = %s", (hashear_contraseña(nueva_clave), int(str(rut).split('-', 1)[0].strip().replace('.', ''))))
        if cursor.rowcount == 0:
            raise LookupError("Usuario no encontrado")
        conn.commit()
        return {"rut": str(rut), "updated": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def listar_descuentos() -> list[dict[str, Any]]:
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SHOW TABLES LIKE 'descuento'")
            if cursor.fetchone() is None:
                return []
            cursor.execute("SELECT id, tipoDescuento, valorDescuento FROM descuento ORDER BY tipoDescuento")
            return list(cursor.fetchall())
        except (Error, mysql.connector.ProgrammingError):
            return []
    finally:
        cursor.close()
        conn.close()


def guardar_descuento(tipo: str, valor: float, descuento_id: int | None = None):
    tipo = tipo.strip()
    if not tipo:
        raise ValueError("Indica un nombre para el descuento")
    if valor < 0 or valor > 1:
        raise ValueError("El descuento debe estar entre 0 y 100%")

    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE 'descuento'")
        if cursor.fetchone() is None:
            cursor.execute(
                "CREATE TABLE descuento (id INT NOT NULL AUTO_INCREMENT, tipoDescuento VARCHAR(100) NOT NULL, valorDescuento DECIMAL(10,4) NOT NULL, PRIMARY KEY (id))"
            )

        if descuento_id is None:
            cursor.execute(
                "INSERT INTO descuento (tipoDescuento, valorDescuento) VALUES (%s, %s)",
                (tipo, valor),
            )
            descuento_id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE descuento SET tipoDescuento=%s, valorDescuento=%s WHERE id=%s",
                (tipo, valor, descuento_id),
            )
            if cursor.rowcount == 0:
                raise LookupError("Descuento no encontrado")
        conn.commit()
        return {"id": descuento_id, "tipoDescuento": tipo, "valorDescuento": valor}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def resumen():
    usuarios = listar_usuarios()
    roles = listar_roles()
    descuentos = listar_descuentos()
    return {"usuarios": len(usuarios), "roles": len(roles), "descuentos": len(descuentos)}