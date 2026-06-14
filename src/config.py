"""Configuration loader."""

import os
import yaml
from pathlib import Path


def load_config(path: str = "config/default.yaml") -> dict:
    """Load configuration from YAML file with environment variable substitution."""
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Substitute environment variables
    config = _substitute_env_vars(config)

    # Apply defaults
    config = _apply_defaults(config)

    return config


def _substitute_env_vars(obj):
    """Recursively substitute ${VAR} with environment variable values."""
    if isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            return os.environ.get(var_name, obj)
        return obj
    elif isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


def _apply_defaults(config: dict) -> dict:
    """Apply default values for missing configuration."""
    defaults = {
        "miner": {
            "wallet": "",
            "worker": "rig-01",
            "algorithms": ["kawpow"],
        },
        "gpu": {
            "devices": [-1],
            "power_limit": 250,
            "temp_limit": 85,
            "fan_curve": "auto",
            "auto_tune": True,
        },
        "pools": {
            "primary": {
                "url": "stratum+tcp://pool.example.com:3636",
                "algorithm": "kawpow",
            },
            "failover": [],
        },
        "monitoring": {
            "dashboard_port": 8080,
            "api_port": 8081,
            "prometheus_port": 9090,
            "telegram": {"enabled": False},
        },
        "logging": {
            "level": "INFO",
            "file": "logs/miner.log",
        },
    }

    for key, value in defaults.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key not in config[key]:
                    config[key][sub_key] = sub_value

    return config
