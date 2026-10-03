import sqlite3
import re
import os

os.makedirs("data", exist_ok=True)

db_path = "data/girasol.db"
sql_path = "backend/db/girasol.sql"

print(f"Buscando archivo SQL en: {os.path.abspath(sql_path)}")
print(f"Creando base de datos SQLite en: {os.path.abspath(db_path)}")

with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Habilitar claves foráneas
cursor.execute("PRAGMA foreign_keys = ON;")

statements = sql_content.split(';')

success_count = 0
for statement in statements:
    stmt = statement.strip()
    if not stmt:
        continue
        
    upper_stmt = stmt.upper()
    
    # Ignorar comandos de configuración de MySQL
    if upper_stmt.startswith("LOCK TABLES") or upper_stmt.startswith("UNLOCK TABLES") or \
       upper_stmt.startswith("SET ") or upper_stmt.startswith("/*!") or \
       upper_stmt.startswith("DROP TABLE") or upper_stmt.startswith("USE"):
        continue

    # Procesar CREATE TABLE
    if upper_stmt.startswith("CREATE TABLE"):
        # Extraer nombre de la tabla para hacer DROP previo si ya existe y evitar errores
        table_match = re.search(r'CREATE\s+TABLE\s+`?([a-zA-Z0-9_]+)`?', stmt, re.IGNORECASE)
        if table_match:
            t_name = table_match.group(1)
            try:
                cursor.execute(f"DROP TABLE IF EXISTS `{t_name}`;")
            except Exception:
                pass

        lines = stmt.split('\n')
        cleaned_table_lines = []
        for line in lines:
            cl_line = re.sub(r'\bAUTO_INCREMENT\b', '', line, flags=re.IGNORECASE)
            cl_line = re.sub(r'ENGINE=InnoDB.*$', '', cl_line, flags=re.IGNORECASE)
            # Reemplazar ENUM(...) de MySQL por TEXT de SQLite
            cl_line = re.sub(r"enum\([^)]+\)", "TEXT", cl_line, flags=re.IGNORECASE)
            
            # Omitir líneas que sean solo índices o llaves secundarias de MySQL
            if re.search(r'^\s*(KEY|INDEX|CONSTRAINT)\s+', cl_line, re.IGNORECASE):
                continue
                
            cleaned_table_lines.append(cl_line)
            
        final_stmt = "\n".join(cleaned_table_lines)
        # Quitar coma sobrante antes del paréntesis de cierre final
        final_stmt = re.sub(r',\s*\)\s*$', '\n)', final_stmt)
        
        try:
            cursor.execute(final_stmt)
            success_count += 1
        except Exception as e:
            print(f"Error en CREATE TABLE: {e}\nEn sentencia:\n{final_stmt}")

    # Procesar INSERT INTO
    elif upper_stmt.startswith("INSERT INTO"):
        # Usar INSERT OR IGNORE para evitar duplicados si se vuelve a ejecutar
        clean_insert = re.sub(r'^INSERT INTO', 'INSERT OR IGNORE INTO', stmt, flags=re.IGNORECASE)
        clean_insert = re.sub(r'ON\s+DUPLICATE\s+KEY\s+UPDATE.*$', '', clean_insert, flags=re.IGNORECASE)
        try:
            cursor.execute(clean_insert)
            success_count += 1
        except Exception as e:
            print(f"Error en INSERT: {e}")

conn.commit()

# Verificación final
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario';")
if cursor.fetchone():
    print(f"¡Base de datos SQLite creada y poblada con éxito! ({success_count} sentencias ejecutadas)")
    print("Verificación exitosa: La tabla 'usuario' existe en la base de datos.")
else:
    print("Advertencia: La tabla 'usuario' no se pudo verificar en la base de datos.")

conn.close()