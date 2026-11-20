from .base import CRMConnector
from .hubspot import HubSpotConnector


def get_crm_connector(provider: str, access_token: str | None = None) -> CRMConnector:
    provider = (provider or "").lower()
    if provider == "hubspot":
        return HubSpotConnector(access_token=access_token)
    raise ValueError(f"Unsupported CRM provider: {provider}")


__all__ = ["CRMConnector", "HubSpotConnector", "get_crm_connector"]
