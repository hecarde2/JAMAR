"""Configuración central del backend.

Todas las variables se cargan desde el entorno o desde un archivo `.env`.
El uso de pydantic-settings permite tipado estricto y valores por defecto
seguros para que la aplicación pueda ejecutarse en modo demostración.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---
    app_name: str = "Jamar AI Assistant"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,"
        "http://127.0.0.1:5173"
    )

    # --- Snowflake ---
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_token: str = ""
    snowflake_password: str = ""
    snowflake_authenticator: str = ""
    snowflake_private_key_path: str = ""
    snowflake_private_key_b64: str = ""
    snowflake_private_key_passphrase: str = ""
    snowflake_client_store_temporary_credential: bool = False
    snowflake_database: str = "JAMAR_DW"
    snowflake_schema: str = "PUBLIC"
    snowflake_warehouse: str = "JAMAR_WH"
    snowflake_role: str = ""
    snowflake_inventory_table: str = "INVENTARIO_PRODUCTOS"
    snowflake_customer_table: str = "CUSTOMER_360"
    snowflake_fallback_demo: bool = False

    # --- Inteligencia artificial (Google Gemini) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_vision_model: str = "gemini-2.5-flash-lite"
    gemini_timeout_seconds: float = 40.0

    # --- Telegram ---
    telegram_bot_token: str = ""
    public_webapp_url: str = "http://localhost:3000"
    asset_base_url: str = "http://localhost:3000/products"
    backend_internal_url: str = "http://backend:8000"

    # --- CrediJamar ---
    credit_weekly_rate: float = 0.0045
    credit_max_term_weeks: int = 52
    credit_min_down_payment_pct: float = 0.10

    # --- Asesoría ---
    advisor_timezone: str = "America/Bogota"
    advisor_weekday_start: str = "08:00"
    advisor_weekday_end: str = "18:00"
    advisor_saturday_start: str = "09:00"
    advisor_saturday_end: str = "13:00"
    advisor_sunday_enabled: bool = False
    advisor_sunday_start: str = "09:00"
    advisor_sunday_end: str = "13:00"

    @property
    def cors_origin_list(self) -> List[str]:
        """Lista de orígenes permitidos para CORS."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def snowflake_configured(self) -> bool:
        """Indica si existen credenciales completas de Snowflake."""
        if not self.snowflake_account.strip() or not self.snowflake_user.strip():
            return False
        authenticator = self.snowflake_authenticator.strip().lower()
        if authenticator in {"snowflake_jwt", "jwt", "keypair"}:
            return bool(
                self.snowflake_private_key_path.strip()
                or self.snowflake_private_key_b64.strip()
            )
        if authenticator:
            return True
        return bool(self.snowflake_token.strip() or self.snowflake_password.strip())

    @property
    def ai_enabled(self) -> bool:
        """Indica si el motor generativo de Gemini está habilitado."""
        return bool(self.gemini_api_key.strip())

    @property
    def telegram_enabled(self) -> bool:
        """Indica si el bot de Telegram tiene token configurado."""
        return bool(self.telegram_bot_token.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve una instancia única de la configuración."""
    return Settings()
