import os
import mysql.connector
from pathlib import Path
import sys


def _cargar_entorno() -> Path | None:
    """Carga credenciales desde el .env del proyecto."""
    configured = os.getenv("DB_ENV_FILE")
    executable_dir = Path(sys.executable).resolve().parent
    module_dir = Path(__file__).resolve().parent
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        module_dir.parent.parent / ".env",
        executable_dir / "database.env",
        executable_dir / ".env",
        module_dir.parent / ".env",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            from dotenv import load_dotenv
            load_dotenv(candidate, override=True)
            return candidate
    return None


_ENV_FILE = _cargar_entorno()


def _mysql_config():
    """Configuración única para MariaDB en Docker."""
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD")
    if not password:
        raise RuntimeError("Configura DB_PASSWORD o MYSQL_PASSWORD para conectar con MariaDB")
    host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST") or os.getenv("MARIADB_HOST") or "127.0.0.1"
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or "3307")
    return {
        "host": host,
        "port": port,
        "user": os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "app_user",
        "password": password,
        "database": os.getenv("DB_DATABASE") or os.getenv("MYSQL_DATABASE") or "tienda_online",
        "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "use_pure": True,
    }


def conectar_db():
    """Compatibilidad con módulos antiguos: ahora apunta siempre a MariaDB en Docker."""
    return conectar_mydb()


def conectar_mydb():
    """Conecta siempre a MariaDB de Docker."""
    try:
        return mysql.connector.connect(**_mysql_config())
    except Exception as e:
        raise ConnectionError(f"No se pudo conectar a MariaDB en Docker: {e}") from e