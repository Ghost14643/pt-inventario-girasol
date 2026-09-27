from __future__ import annotations

import hashlib
import hmac
from typing import Any

from backend.db.mariadb import conectar_mariadb


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def autenticar_usuario(
    rut_usuario: str,
    password: str,
) -> dict[str, Any] | None:
    try:
        rut = int(str(rut_usuario).strip().split("-", 1)[0].replace(".", ""))
    except ValueError as exc:
        raise ValueError("El RUT no es válido") from exc

    connection = conectar_mariadb()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                u.id_usuario,
                u.rut_usuario,
                u.nombre,
                u.password,
                u.id_rol,
                r.nombre_rol
            FROM usuario u
            INNER JOIN rol r
                ON r.id_rol = u.id_rol
            WHERE u.rut_usuario = %s
              AND u.activo = 1
            LIMIT 1
            """,
            (rut,),
        )

        user = cursor.fetchone()

        if user is None:
            return None

        password_hash = _hash_password(password)

        if not hmac.compare_digest(
            str(user["password"]),
            password_hash,
        ):
            return None

        role = str(user["nombre_rol"]).strip().lower()

        return {
            "id_usuario": int(user["id_usuario"]),
            "rut": str(user["rut_usuario"]),
            "nombre": user["nombre"],
            "is_admin": role in {
                "admin",
                "administrador",
                "developer",
                "desarrollador",
            },
        }
    finally:
        cursor.close()
        connection.close()