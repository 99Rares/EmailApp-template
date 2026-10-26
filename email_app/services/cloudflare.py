"""Small, retrying client for the Cloudflare Email Routing API."""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from email_app.config import CLOUDFLARE_API_TOKEN, ROUTING_URL

REQUEST_TIMEOUT_SECONDS = 10
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


class CloudflareAPIError(RuntimeError):
    """Raised when Cloudflare cannot complete a routing operation."""


class CloudflareClient:
    def __init__(self):
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=frozenset({"GET", "POST", "PUT", "DELETE"}),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        }

    def request(self, method, url, **kwargs):
        try:
            response = self.session.request(
                method, url, headers=self.headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
            )
            response.raise_for_status()
            return response.json().get("result", {})
        except (requests.RequestException, ValueError) as error:
            logging.error("Cloudflare %s request failed: %s", method, error)
            raise CloudflareAPIError("Cloudflare request failed") from error

    def list_rules(self, page, per_page):
        return self.request("GET", ROUTING_URL, params={"page": page, "per_page": per_page})

    def get_rule(self, rule_id):
        return self.request("GET", f"{ROUTING_URL}/{rule_id}")

    def create_rule(self, data):
        return self.request("POST", ROUTING_URL, json=data)

    def update_rule(self, rule_id, data):
        return self.request("PUT", f"{ROUTING_URL}/{rule_id}", json=data)

    def delete_rule(self, rule_id):
        return self.request("DELETE", f"{ROUTING_URL}/{rule_id}")


cloudflare_client = CloudflareClient()
