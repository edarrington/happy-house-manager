"""Azure Key Vault client for secrets management."""

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """
    Azure Key Vault client.
    Uses DefaultAzureCredential in production (managed identity),
    ClientSecretCredential for local dev when env vars are set.
    """

    def __init__(self):
        self._client: Optional[SecretClient] = None

    def _get_client(self) -> SecretClient:
        if self._client is None:
            if settings.azure_client_id and settings.azure_client_secret and settings.azure_tenant_id:
                credential = ClientSecretCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret,
                )
                logger.info("KeyVault: using ClientSecretCredential (local dev)")
            else:
                credential = DefaultAzureCredential()
                logger.info("KeyVault: using DefaultAzureCredential (managed identity)")

            self._client = SecretClient(
                vault_url=settings.key_vault_url,
                credential=credential,
            )
        return self._client

    def get_secret(self, secret_name: str) -> str:
        if not settings.key_vault_url:
            logger.warning(f"KEY_VAULT_URL not set; cannot fetch secret '{secret_name}'")
            return ""
        try:
            client = self._get_client()
            secret = client.get_secret(secret_name)
            return secret.value or ""
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}': {e}")
            raise

    def set_secret(self, secret_name: str, value: str) -> None:
        if not settings.key_vault_url:
            logger.warning("KEY_VAULT_URL not set; skipping Key Vault write")
            return
        try:
            client = self._get_client()
            client.set_secret(secret_name, value)
        except Exception as e:
            logger.error(f"Failed to set secret '{secret_name}': {e}")
            raise


keyvault_client = KeyVaultClient()
