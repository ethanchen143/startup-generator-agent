import os
import logging
from typing import Optional

logger = logging.getLogger("secrets_manager")

def get_secret(secret_name: str, default: str = "") -> str:
    """
    Fetches a secret securely from GCP Secret Manager if available,
    falling back to environment variables for secret management security compliance.
    
    Args:
        secret_name (str): Name of the secret / environment variable (e.g. 'GOOGLE_API_KEY').
        default (str): Fallback value if secret is not found.
        
    Returns:
        str: Secret string value.
    """
    # 1. Attempt to fetch from environment variable first
    val = os.getenv(secret_name)
    if val:
        return val

    # 2. Attempt GCP Secret Manager SDK lookup if running in cloud context
    gcp_project = os.getenv("GCP_PROJECT_ID", "startup-generator-agent-prod")
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{gcp_project}/secrets/{secret_name.lower().replace('_', '-')}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_val = response.payload.data.decode("UTF-8")
        if secret_val:
            return secret_val
    except Exception:
        pass

    return default

# Resolved system secrets
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY", get_secret("GEMINI_API_KEY", ""))
GOOGLE_SEARCH_API_KEY = get_secret("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_CX = get_secret("GOOGLE_SEARCH_CX", "")
