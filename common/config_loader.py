"""
Configuration loader for the project.
Provides easy access to config values with defaults.
"""

import json
from pathlib import Path
from typing import Any, Dict


_CONFIG_CACHE = None


def _load_config() -> Dict[str, Any]:
    """Load config from json/config.json."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        config_path = Path(__file__).parent.parent / "json" / "config.json"
        with open(config_path, 'r') as f:
            _CONFIG_CACHE = json.load(f)
    return _CONFIG_CACHE


def get(key: str, default: Any = None) -> Any:
    """
    Get a configuration value using dot notation.
    
    Args:
        key: Dot-notation key (e.g., "onlyfiles.upload_url", "scraper.headless")
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    config = _load_config()
    keys = key.split('.')
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


def get_error_screenshot_path() -> str:
    """Get the path for error screenshots."""
    return str(Path(__file__).parent.parent / "error" / "error_screenshot.png")


def ensure_directories():
    """Ensure all required directories exist."""
    base = Path(__file__).parent.parent
    for dir_name in ["json", "common", "locators", "error"]:
        (base / dir_name).mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test
    ensure_directories()
    print("onlyfiles.upload_url:", get("onlyfiles.upload_url"))
    print("onlyfiles.expire_seconds:", get("onlyfiles.expire_seconds"))
    print("scraper.headless:", get("scraper.headless"))
    print("error.screenshot_path:", get("error.screenshot_path"))