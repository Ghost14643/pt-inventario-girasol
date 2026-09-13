"""Gestiones administrativas sobre usuarios, roles y descuentos."""
from __future__ import annotations

from backend.db.conexion import conectar_db, conectar_mydb
from backend.logica.user import hashear_contraseña
from mysql.connector import IntegrityError


def _mysql():
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    return conn


def listar_usuarios():
    conn = _mysql()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.rut, u.digito_ver, u.nombre, u.id_rol, r.roles AS rol
            FROM usuario u JOIN rol r ON r.id = u.id_rol
            ORDER BY u.nombre, u.rut
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def listar_roles():
    conn = _mysql()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, roles AS nombre FROM rol ORDER BY id")
        return cursor.fetchall()
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
    conn = _mysql()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM rol WHERE LOWER(roles) IN ('empleado', 'employee') ORDER BY id LIMIT 1")
        role = cursor.fetchone()
        if role is None:
            raise ValueError("No existe un rol empleado configurado")
        cursor.execute("INSERT INTO usuario (rut, digito_ver, nombre, id_rol, password) VALUES (%s,%s,%s,%s,%s)",
                       (int(number_text), dv.upper(), nombre, int(role[0]), hashear_contraseña(clave)))
        conn.commit()
        return {"rut": int(number_text), "digito_ver": dv.upper(), "nombre": nombre,
                "id_rol": int(role[0]), "rol": "empleado"}
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Ya existe un usuario con ese RUT") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close(); conn.close()


def eliminar_empleado(rut: str):
    raw = str(rut).strip().replace(".", "").split("-", 1)[0]
    if not raw.isdigit():
        raise ValueError("El RUT ingresado no es válido")
    conn = _mysql()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT u.nombre, LOWER(r.roles) FROM usuario u
            JOIN rol r ON r.id=u.id_rol WHERE u.rut=%s FOR UPDATE""", (int(raw),))
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Usuario no encontrado")
        if row[1] not in ("empleado", "employee"):
            raise PermissionError("Solo se pueden eliminar usuarios con rol empleado")
        cursor.execute("DELETE FROM usuario WHERE rut=%s", (int(raw),))
        conn.commit()
        return {"rut": int(raw), "nombre": row[0], "deleted": True}
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("No se puede eliminar: el empleado tiene movimientos asociados") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close(); conn.close()

def actualizar_rol(rut: str, id_rol: int):
    conn = _mysql()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT LOWER(roles) FROM rol WHERE id=%s", (id_rol,))
        target = cursor.fetchone()
        if target is None:
            raise ValueError("El rol seleccionado no existe")
        cursor.execute("""SELECT LOWER(r.roles) FROM usuario u JOIN rol r ON r.id=u.id_rol
            WHERE u.rut=%s FOR UPDATE""", (rut,))
        current = cursor.fetchone()
        if current is None:
            raise LookupError("Usuario no encontrado")
        protected = {"admin", "administrador", "developer", "desarrollador"}
        if current[0] in protected and target[0] != current[0]:
            raise PermissionError("Los roles admin y developer están protegidos y no pueden degradarse")
        cursor.execute("UPDATE usuario SET id_rol=%s WHERE rut=%s", (id_rol, rut))
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
    conn = _mysql()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE usuario SET password=%s WHERE rut=%s",
            (hashear_contraseña(nueva_clave), rut),
        )
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


def listar_descuentos():
    conn = conectar_db()
    try:
        rows = conn.execute(
            "SELECT id, tipoDescuento, valorDescuento FROM descuento ORDER BY tipoDescuento"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def guardar_descuento(tipo: str, valor: float, descuento_id: int | None = None):
    tipo = tipo.strip()
    if not tipo:
        raise ValueError("Indica un nombre para el descuento")
    if valor < 0 or valor > 1:
        raise ValueError("El descuento debe estar entre 0 y 100%")
    conn = conectar_db()
    try:
        if descuento_id is None:
            cursor = conn.execute(
                "INSERT INTO descuento (tipoDescuento, valorDescuento) VALUES (?, ?)",
                (tipo, valor),
            )
            descuento_id = cursor.lastrowid
        else:
            cursor = conn.execute(
                "UPDATE descuento SET tipoDescuento=?, valorDescuento=? WHERE id=?",
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
        conn.close()


def resumen():
    usuarios = listar_usuarios()
    roles = listar_roles()
    descuentos = listar_descuentos()
    return {"usuarios": len(usuarios), "roles": len(roles), "descuentos": len(descuentos)}
