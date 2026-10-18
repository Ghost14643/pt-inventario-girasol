import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import MySQLConnection
from mysql.connector import Error


def _load_environment() -> None:
    """Carga las variables del archivo .env sin sobrescribir el entorno."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)


def _connection_config() -> dict[str, object]:
    _load_environment()

    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("Falta configurar DB_PASSWORD")

    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3307")),
        "user": os.getenv("DB_USER", "app_user"),
        "password": password,
        "database": os.getenv("DB_DATABASE", "tienda_online"),
        "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "use_pure": True,
        "autocommit": False,
    }


def conectar_mariadb() -> MySQLConnection:
    """Abre una conexión independiente hacia la nueva base MariaDB."""
    try:
        return mysql.connector.connect(**_connection_config())
    except Error as exc:
        raise ConnectionError(
            "No fue posible conectar con la base MariaDB nueva"
        ) from exc