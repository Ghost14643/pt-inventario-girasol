import sqlite3
import os
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from pathlib import Path


def _cargar_entorno() -> Path | None:
    """Carga credenciales sin sobrescribir variables ya exportadas por el sistema."""
    configured = os.getenv("DB_ENV_FILE")
    executable_dir = Path(sys.executable).resolve().parent
    module_dir = Path(__file__).resolve().parent
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path.cwd() / "backend" / ".env",
        Path.cwd() / ".env",
        executable_dir / "database.env",
        executable_dir / ".env",
        module_dir.parent / ".env",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate
    return None


_ENV_FILE = _cargar_entorno()


def _mysql_config():
    """Configuración única para Compose y ejecución local."""
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("Configura DB_PASSWORD para conectar con MariaDB")
    return {
        "host": os.getenv("DB_HOST", "host.docker.internal"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "app_user"),
        "password": password,
        "database": os.getenv("DB_DATABASE", "tienda_online"),
        "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "use_pure": True,
    }


def _crear_db_sqlite_si_falta() -> str:
    """Crea la base histórica de SQLite si en este entorno aún no existe."""
    root_dir = Path(__file__).resolve().parents[2]
    data_dir = root_dir / "data"
    db_path = data_dir / "girasol.db"

    if not db_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        script = root_dir / "cargar_db.py"
        if script.exists():
            subprocess.run([sys.executable, str(script)], cwd=root_dir, check=True, capture_output=True, text=True)
        else:
            sqlite3.connect(db_path).close()

    return str(db_path)


def _asegurar_esquema_legacy(conn: sqlite3.Connection) -> None:
    """Crea las tablas históricas que usa la capa legacy SQLite del inventario."""
    conn.execute("CREATE TABLE IF NOT EXISTS marcas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE)")
    conn.execute("CREATE TABLE IF NOT EXISTS prenda (id_prenda INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, marca TEXT NOT NULL, precio REAL NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0, barcode TEXT UNIQUE)")
    conn.execute("CREATE TABLE IF NOT EXISTS familiaRopa (idFamiliaRopa INTEGER PRIMARY KEY AUTOINCREMENT, nombreFamilia TEXT NOT NULL UNIQUE)")
    conn.execute("CREATE TABLE IF NOT EXISTS seccionRopa (idSeccionRopa INTEGER PRIMARY KEY AUTOINCREMENT, idFamiliaRopa INTEGER NOT NULL, nombreSeccionRopa TEXT NOT NULL, FOREIGN KEY(idFamiliaRopa) REFERENCES familiaRopa(idFamiliaRopa))")
    conn.execute("CREATE TABLE IF NOT EXISTS arqueo_diario (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, apertura_at TEXT, cierre_at TEXT, ventas_cantidad INTEGER, total_efectivo REAL, total_debito REAL, total_credito REAL, total_transferencia REAL, total_otro REAL, total_ventas REAL, gastos_turno REAL, efectivo_esperado REAL, efectivo_contado REAL, diferencia REAL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_arqueo_diario_fecha ON arqueo_diario(fecha)")
    conn.commit()


def conectar_db():
    """Conecta con la base SQLite de Girasol y la genera si falta."""
    configured = os.getenv("GIRASOL_DB_PATH")
    candidates = [
        configured,
        "/data/girasol.db",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "girasol.db")),
    ]
    db_path = next((path for path in candidates if path and os.path.isfile(path)), None)
    if db_path is None:
        db_path = _crear_db_sqlite_si_falta()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _asegurar_esquema_legacy(conn)
    return conn



def conectar_mydb():
    """Conecta a la MariaDB del proyecto (contenedor Docker)."""
    try:
        from backend.db.mariadb import conectar_mariadb
        return conectar_mariadb()
    except Exception as e:
        print(f"Error conectando a MariaDB: {e}")
        return None