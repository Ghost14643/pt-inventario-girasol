import hashlib

from backend.db.conexion import conectar_mydb

# Insertar con el esquema real de MariaDB definido por 01-create-db.sql y 02-new-schema.sql.
conn = conectar_mydb()
cursor = conn.cursor()

rut = 21153893
digito_ver = "7"
nombre = "Isa"
password_plana = "1630"

cursor.execute("SELECT id_rol FROM rol WHERE LOWER(nombre_rol) IN ('admin', 'administrador', 'developer', 'desarrollador') ORDER BY id_rol LIMIT 1")
row = cursor.fetchone()
if row is None:
    raise RuntimeError("No existe ningún rol administrativo en la base de datos actual.")
id_rol = row[0]
password_hash = hashlib.sha256(password_plana.encode("utf-8")).hexdigest()

try:
    cursor.execute(
        """
        INSERT INTO usuario (rut_usuario, dvrut_usuario, nombre, id_rol, password)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE nombre = VALUES(nombre), id_rol = VALUES(id_rol), password = VALUES(password)
        """,
        (rut, digito_ver, nombre, id_rol, password_hash),
    )
    conn.commit()
    print(f"¡Usuario administrador '{nombre}' (RUT: {rut}-{digito_ver}) creado/actualizado con éxito!")
except Exception as exc:
    conn.rollback()
    print(f"Error al crear el usuario: {exc}")
finally:
    cursor.close()
    conn.close()