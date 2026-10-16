import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow the grader's browser to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def normalize_key(key):
    key = key.strip().lower()

    # NUM_WORKERS is an alias for workers.
    if key in ("num_workers", "app_num_workers"):
        return "workers"

    # Remove APP_ prefix from OS environment variable names.
    if key.startswith("app_"):
        key = key[4:]

    return key


def convert_value(key, value):
    value = str(value)

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return value.strip().lower() in ("true", "1", "yes", "on")

    return value


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML file.
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}

        for key, value in yaml_config.items():
            normalized = normalize_key(key)
            config[normalized] = convert_value(normalized, value)

    # Layer 3: .env file.
    env_file = dotenv_values(".env")
    for key, value in env_file.items():
        if value is None:
            continue

        normalized = normalize_key(key)
        config[normalized] = convert_value(normalized, value)

    # Layer 4: actual OS environment variables with APP_ prefix.
    for key, value in os.environ.items():
        if key.upper().startswith("APP_"):
            normalized = normalize_key(key)
            config[normalized] = convert_value(normalized, value)

    # Highest precedence: query parameters such as ?set=port=9000.
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        normalized = normalize_key(key)

        if normalized:
            config[normalized] = convert_value(normalized, value)

    # Never expose the real API key.
    config["api_key"] = "****"

    return config
