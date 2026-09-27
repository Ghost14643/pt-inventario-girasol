"""Gestiones administrativas sobre usuarios, roles y descuentos."""
from __future__ import annotations

import mysql.connector

from backend.db.conexion import conectar_db
from backend.logica.user import hashear_contraseña


def _db():
    return conectar_db()


def _rut_numero(rut: str | int) -> int:
    raw = str(rut).strip().replace(".", "").replace(" ", "")
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    return int(raw)


def listar_usuarios():
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT u.rut_usuario AS rut, u.dvrut_usuario AS digito_ver, u.nombre, u.id_rol,
                   r.nombre_rol AS rol
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            ORDER BY u.nombre, u.rut_usuario
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def listar_roles():
    conn = _db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_rol AS id, nombre_rol AS nombre FROM rol ORDER BY id_rol")
        return cursor.fetchall()
    finally:
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
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_rol FROM rol WHERE LOWER(nombre_rol) IN ('empleado', 'employee') ORDER BY id_rol LIMIT 1"
        )
        role = cursor.fetchone()
        if role is None:
            raise ValueError("No existe un rol empleado configurado")

        cursor.execute(
            "INSERT INTO usuario (rut_usuario, dvrut_usuario, nombre, id_rol, password) VALUES (%s, %s, %s, %s, %s)",
            (int(number_text), dv.upper(), nombre, int(role[0]), hashear_contraseña(clave)),
        )
        conn.commit()
        return {
            "rut": int(number_text),
            "digito_ver": dv.upper(),
            "nombre": nombre,
            "id_rol": int(role[0]),
            "rol": "empleado",
        }
    except mysql.connector.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Ya existe un usuario con ese RUT") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_empleado(rut: str):
    rut_num = _rut_numero(rut)
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.nombre, LOWER(r.nombre_rol)
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.rut_usuario = %s
            """,
            (rut_num,),
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Usuario no encontrado")
        if row[1] not in ("empleado", "employee"):
            raise PermissionError("Solo se pueden eliminar usuarios con rol empleado")

        cursor.execute("DELETE FROM usuario WHERE rut_usuario=%s", (rut_num,))
        conn.commit()
        return {"rut": rut_num, "nombre": row[0], "deleted": True}
    except mysql.connector.IntegrityError as exc:
        conn.rollback()
        raise ValueError("No se puede eliminar: el empleado tiene movimientos asociados") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def actualizar_rol(rut: str, id_rol: int):
    rut_num = _rut_numero(rut)
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT LOWER(nombre_rol) FROM rol WHERE id_rol=%s", (id_rol,))
        target = cursor.fetchone()
        if target is None:
            raise ValueError("El rol seleccionado no existe")

        cursor.execute(
            """
            SELECT LOWER(r.nombre_rol)
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.rut_usuario=%s
            """,
            (rut_num,),
        )
        current = cursor.fetchone()
        if current is None:
            raise LookupError("Usuario no encontrado")

        protected = {"admin", "administrador", "developer", "desarrollador"}
        if current[0] in protected and target[0] != current[0]:
            raise PermissionError("Los roles admin y developer están protegidos y no pueden degradarse")

        cursor.execute("UPDATE usuario SET id_rol=%s WHERE rut_usuario=%s", (id_rol, rut_num))
        if cursor.rowcount == 0:
            raise LookupError("Usuario no encontrado")
        conn.commit()
        return {"rut": str(rut), "id_rol": id_rol}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cambiar_clave(rut: str, nueva_clave: str):
    if len(nueva_clave) < 8:
        raise ValueError("La nueva clave debe tener al menos 8 caracteres")
    rut_num = _rut_numero(rut)
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET password=%s WHERE rut_usuario=%s", (hashear_contraseña(nueva_clave), rut_num))
        if cursor.rowcount == 0:
            raise LookupError("Usuario no encontrado")
        conn.commit()
        return {"rut": str(rut), "updated": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_descuentos():
    return []


def guardar_descuento(tipo: str, valor: float, descuento_id: int | None = None):
    raise ValueError("El esquema actual de MariaDB no define una tabla de descuentos")


def resumen():
    usuarios = listar_usuarios()
    roles = listar_roles()
    descuentos = listar_descuentos()
    return {"usuarios": len(usuarios), "roles": len(roles), "descuentos": len(descuentos)}