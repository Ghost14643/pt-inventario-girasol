import sqlite3
import hashlib

# Conectarse a la base de datos SQLite
conn = sqlite3.connect("data/girasol.db")
cursor = conn.cursor()

# Datos del nuevo administrador
rut = 21153893
digito_ver = "7"
nombre = "Isa"
id_rol = 3
password_plana = "1630"

# Generar el hash SHA-256 de la contraseña
password_hash = hashlib.sha256(password_plana.encode('utf-8')).hexdigest()

try:
    # Insertar el nuevo usuario (o actualizar si ya existe el RUT)
    cursor.execute("""
        INSERT OR REPLACE INTO usuario (rut, digito_ver, nombre, id_rol, password)
        VALUES (?, ?, ?, ?, ?)
    """, (rut, digito_ver, nombre, id_rol, password_hash))
    
    conn.commit()
    print(f"¡Usuario administrador '{nombre}' (RUT: {rut}-{digito_ver}) creado/actualizado con éxito!")
except Exception as e:
    print(f"Error al crear el usuario: {e}")
finally:
    conn.close()