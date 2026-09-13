import sqlite3
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from pathlib import Path
import sys


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


def conectar_db():
    """Conecta con la base SQLite de Girasol sin crear una base vacía por error."""
    configured = os.getenv("GIRASOL_DB_PATH")
    candidates = [
        configured,
        "/data/girasol.db",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "girasol.db")),
    ]
    db_path = next((path for path in candidates if path and os.path.isfile(path)), None)
    if db_path is None:
        raise FileNotFoundError("No se encontró girasol.db en /data ni en el directorio data del proyecto")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def conectar_mydb():
    """Redirige todas las consultas a la base de datos SQLite local."""
    try:
        return conectar_db()
    except Exception as e:
        print(f"Error conectando a SQLite local: {e}")
        return None