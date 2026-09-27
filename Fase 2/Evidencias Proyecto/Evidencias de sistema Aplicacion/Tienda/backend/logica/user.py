import hashlib
import hmac

from backend.db.conexion import conectar_mydb


def _rut_numero(rut: str | int) -> int:
    raw = str(rut).strip().replace(".", "").replace(" ", "")
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    return int(raw)


def hashear_contraseña(contraseña):
    hash_obj = hashlib.sha256(contraseña.encode("utf-8"))
    return hash_obj.hexdigest()


def verificar_contraseña(rut_empleado, contraseña):
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM usuario WHERE rut_usuario = %s", (_rut_numero(rut_empleado),))
        resultado = cursor.fetchone()
        if resultado is None:
            return False
        stored = str(resultado[0])
        hashed = hashear_contraseña(contraseña)
        if hmac.compare_digest(stored, hashed):
            return True
        return hmac.compare_digest(stored, contraseña)
    finally:
        cursor.close()
        conn.close()


def verificacion_admin(rut_empleado):
    conn = conectar_mydb()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT LOWER(r.nombre_rol) FROM usuario u JOIN rol r ON r.id_rol = u.id_rol WHERE u.rut_usuario = %s",
            (_rut_numero(rut_empleado),),
        )
        resultado = cursor.fetchone()
        return bool(resultado and resultado[0] in ("admin", "administrador", "developer", "desarrollador"))
    finally:
        cursor.close()
        conn.close()
