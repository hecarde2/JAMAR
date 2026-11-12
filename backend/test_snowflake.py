"""Prueba de conexión a Snowflake con snowflake-connector-python.

Uso:
    cd backend
    .venv/bin/python test_snowflake.py

Requiere las variables SNOWFLAKE_* definidas en el entorno o en backend/.env.
No imprime credenciales; solo metadatos de la sesión y conteos de las tablas.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from snowflake_client import get_snowflake_client


def main() -> int:
    settings = get_settings()
    client = get_snowflake_client()

    print(f"Modo de datos: {client.mode}")
    if not client.configured:
        print(
            "ERROR: Snowflake no está configurado. Define SNOWFLAKE_ACCOUNT, "
            "SNOWFLAKE_USER y SNOWFLAKE_PASSWORD/SNOWFLAKE_TOKEN en backend/.env."
        )
        return 2

    try:
        info = client.check_connection(
            probe_tables=(
                settings.snowflake_inventory_table,
                settings.snowflake_customer_table,
            )
        )
    except Exception as exc:
        print(f"ERROR: no se pudo conectar a Snowflake: {exc}")
        return 1
    finally:
        client.close()

    print("Conexión establecida correctamente:")
    for key in ("version", "account", "user", "database", "schema", "warehouse", "role"):
        print(f"  {key}: {info.get(key)}")
    for table, count in info.get("tables", {}).items():
        print(f"  {table}: {count} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
