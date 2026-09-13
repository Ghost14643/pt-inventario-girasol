import hashlib
import hmac
from backend.db.conexion import conectar_mydb




def hashear_contraseña(contraseña):
    hash_obj = hashlib.sha256(contraseña.encode('utf-8'))
    return hash_obj.hexdigest()



def verificar_contraseña(rut_empleado, contraseña):
    conn = conectar_mydb()
    if conn is None:
        raise ConnectionError("No fue posible conectar con MariaDB")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM usuario WHERE rut = %s", (rut_empleado,))
        resultado = cursor.fetchone()
        if resultado is None:
            return False
        return hmac.compare_digest(str(resultado[0]), hashear_contraseña(contraseña))
    finally:
        cursor.close()
        conn.close()

def verificacion_admin(rut_empleado):
    conn = conectar_mydb()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT LOWER(r.roles) FROM usuario u JOIN rol r ON r.id = u.id_rol WHERE u.rut = %s", (rut_empleado,))
        resultado = cursor.fetchone()
        return bool(resultado and resultado[0] in ("admin", "administrador", "developer", "desarrollador"))
    finally:
        cursor.close()
        conn.close()
