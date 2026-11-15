"""
Common utilities for the project.
Provides configuration loading and shared helper functions.
"""

import json
from pathlib import Path
from typing import Any, Dict, List


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to config file. Defaults to json/config.json
        
    Returns:
        Dictionary containing configuration
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "json" / "config.json"
    
    with open(config_path, 'r') as f:
        return json.load(f)


def load_locators(locator_file: str) -> Dict[str, List[str]]:
    """
    Load locators from a text file.
    Multiple lines with the same key are treated as fallbacks (returned as list in order).
    
    Args:
        locator_file: Name of locator file in locators folder (e.g., 'youtube_locators.txt')
        
    Returns:
        Dictionary mapping locator names to list of selector strings (primary first, then fallbacks)
    """
    locator_path = Path(__file__).parent.parent / "locators" / locator_file
    locators = {}
    
    with open(locator_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if key not in locators:
                    locators[key] = []
                locators[key].append(value)
    
    return locators


def ensure_directories():
    """Ensure all required directories exist."""
    base = Path(__file__).parent.parent
    for dir_name in ["json", "common", "locators", "error"]:
        (base / dir_name).mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test the utilities
    ensure_directories()
    config = load_config()
    print("Config loaded successfully:", json.dumps(config, indent=2))
    
    locators = load_locators("youtube_locators.txt")
    print("\nLocators loaded:", locators)