"""Connector configuration, loaded from environment variables or a local .env file."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Data-center-aware base URLs. Zoho documentation examples often show the US
# domains, but organizations live on region-specific hosts, so both halves are
# derived from ZOHO_DC. The IN and EU hosts were verified live in phase 1
# (docs/03-HANDOVER.md "Verified facts").
_ACCOUNTS_HOSTS = {
    "in": "https://accounts.zoho.in",
    "us": "https://accounts.zoho.com",
    "eu": "https://accounts.zoho.eu",
}

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
    zoho_dc: Literal["in", "us", "eu"] = "in"

    # Minimum spacing between API calls: the free plan allows 5 concurrent
    # calls and 1,000 per day, so we pace calls conservatively.
    call_spacing_seconds: float = 0.5

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    audit_log_path: str = "logs/audit.jsonl"

    # Demo agent (agent/demo.py): Bedrock model id used for the merchant walkthrough.
    bedrock_model_id: str = ""

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
