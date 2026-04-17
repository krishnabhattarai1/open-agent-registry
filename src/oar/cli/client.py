"""HTTP client wrapper for the OAR API."""

import json
from pathlib import Path

import httpx
import tomllib

CONFIG_PATH = Path.home() / ".config" / "oar" / "config.toml"
DEFAULT_REGISTRY_URL = "http://localhost:8000"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f).get("default", {})
    return {}


def save_config(key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
    config.setdefault("default", {})[key] = value
    with open(CONFIG_PATH, "w") as f:
        f.write("[default]\n")
        for k, v in config.get("default", {}).items():
            f.write(f'{k} = "{v}"\n')


def get_client(api_key: str | None = None) -> httpx.Client:
    cfg = load_config()
    base_url = cfg.get("registry_url", DEFAULT_REGISTRY_URL)
    key = api_key or cfg.get("api_key")
    headers = {"Accept": "application/vnd.oar.compact+json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
