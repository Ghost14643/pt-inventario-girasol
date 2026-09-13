"""Gestiones administrativas sobre usuarios, roles y descuentos."""
from __future__ import annotations

from backend.db.conexion import conectar_db
from backend.logica.user import hashear_contraseña
import sqlite3

# Usar conectar_db() que maneja la conexión SQLite unificada del proyecto
def _db():
    return conectar_db()


def listar_usuarios():
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.rut, u.digito_ver, u.nombre, u.id_rol, r.roles AS rol
            FROM usuario u JOIN rol r ON r.id = u.id_rol
            ORDER BY u.nombre, u.rut
        """)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def listar_roles():
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, roles AS nombre FROM rol ORDER BY id")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
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
        cursor.execute("SELECT id FROM rol WHERE LOWER(roles) IN ('empleado', 'employee') ORDER BY id LIMIT 1")
        role = cursor.fetchone()
        if role is None:
            raise ValueError("No existe un rol empleado configurado")
        
        cursor.execute(
            "INSERT INTO usuario (rut, digito_ver, nombre, id_rol, password) VALUES (?, ?, ?, ?, ?)",
            (int(number_text), dv.upper(), nombre, int(role[0]), hashear_contraseña(clave))
        )
        conn.commit()
        return {
            "rut": int(number_text), 
            "digito_ver": dv.upper(), 
            "nombre": nombre,
            "id_rol": int(role[0]), 
            "rol": "empleado"
        }
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Ya existe un usuario con ese RUT") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_empleado(rut: str):
    raw = str(rut).strip().replace(".", "").split("-", 1)[0]
    if not raw.isdigit():
        raise ValueError("El RUT ingresado no es válido")
    
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.nombre, LOWER(r.roles) FROM usuario u
            JOIN rol r ON r.id=u.id_rol WHERE u.rut=?
        """, (int(raw),))
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Usuario no encontrado")
        if row[1] not in ("empleado", "employee"):
            raise PermissionError("Solo se pueden eliminar usuarios con rol empleado")
            
        cursor.execute("DELETE FROM usuario WHERE rut=?", (int(raw),))
        conn.commit()
        return {"rut": int(raw), "nombre": row[0], "deleted": True}
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("No se puede eliminar: el empleado tiene movimientos asociados") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def actualizar_rol(rut: str, id_rol: int):
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT LOWER(roles) FROM rol WHERE id=?", (id_rol,))
        target = cursor.fetchone()
        if target is None:
            raise ValueError("El rol seleccionado no existe")
            
        cursor.execute("""
            SELECT LOWER(r.roles) FROM usuario u JOIN rol r ON r.id=u.id_rol
            WHERE u.rut=?
        """, (rut,))
        current = cursor.fetchone()
        if current is None:
            raise LookupError("Usuario no encontrado")
            
        protected = {"admin", "administrador", "developer", "desarrollador"}
        if current[0] in protected and target[0] != current[0]:
            raise PermissionError("Los roles admin y developer están protegidos y no pueden degradarse")
            
        cursor.execute("UPDATE usuario SET id_rol=? WHERE rut=?", (id_rol, rut))
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
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuario SET password=? WHERE rut=?",
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
        conn.close()


def listar_descuentos():
    conn = _db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipoDescuento, valorDescuento FROM descuento ORDER BY tipoDescuento")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
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
        if descuento_id is None:
            cursor.execute(
                "INSERT INTO descuento (tipoDescuento, valorDescuento) VALUES (?, ?)",
                (tipo, valor),
            )
            descuento_id = cursor.lastrowid
        else:
            cursor.execute(
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