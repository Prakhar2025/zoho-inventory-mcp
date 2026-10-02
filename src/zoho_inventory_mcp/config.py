"""Connector configuration, loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Data-center-aware base URLs. Zoho documentation examples often show the US domains, but
# organizations live on region-specific hosts, so both halves are derived from ZOHO_DC.
_ACCOUNTS_HOSTS = {
    "in": "https://accounts.zoho.in",
    "us": "https://accounts.zoho.com",
    "eu": "https://accounts.zoho.eu",
}

# The Inventory API host differs per DC and is verified live in phase 1 (see
# docs/03-HANDOVER.md "Verified facts"). These are the documented defaults.
_API_HOSTS = {
    "in": "https://www.zohoapis.in/inventory/v1",
    "us": "https://inventory.zoho.com/api/v1",
    "eu": "https://www.zohoapis.eu/inventory/v1",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    zoho_client_id: str = ""
    zoho_client_secret: str = ""
    zoho_refresh_token: str = ""
    zoho_org_id: str = ""
    zoho_dc: str = "in"

    log_level: str = "INFO"
    audit_log_path: str = "logs/audit.jsonl"

    @property
    def accounts_base(self) -> str:
        return _ACCOUNTS_HOSTS[self.zoho_dc]

    @property
    def api_base(self) -> str:
        return _API_HOSTS[self.zoho_dc]

    @property
    def is_configured(self) -> bool:
        return all(
            [
                self.zoho_client_id,
                self.zoho_client_secret,
                self.zoho_refresh_token,
                self.zoho_org_id,
            ]
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
