# Cloudflare API configuration
import os


ACCOUNT_ID = os.environ.get("ACCOUNT_ID")
CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
PLACEHOLDER_EMAIL_DOMAIN = os.environ.get("PLACEHOLDER_EMAIL_DOMAIN")
DESTINATION_EMAIL = os.environ.get("DESTINATION_EMAIL")
MY_USER = os.environ.get("MY_USER")
EMAIL_LIST = os.environ.get("EMAIL_LIST", "")
ROUTING_URL = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/email/routing/rules"

# Read user credentials from environment variables
USER_CREDENTIALS = {
    MY_USER: os.environ.get(
        "ADMIN_PASSWORD_HASH"
    )  # Set the encrypted password hash as an environment variable
}
