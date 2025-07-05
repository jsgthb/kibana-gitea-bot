import logging
import yaml
from typing import Dict, Any

CONFIG_PATH = "config.yml"

def load_config(path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Load config values from a YAML file"""
    try:
        with open(path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Config file not found at: {path}")
        raise
    except yaml.YAMLError as error:
        logging.error(f"Error parsing YAML file: {error}")
        raise

if __name__ == "__main__":
    try:
        config = load_config()
        logging.basicConfig(
            level=config["logging"]["level"].upper(),
            format=config["logging"]["format"],
        )
        logging.info("Config successfully loaded!")
    except Exception as error:
        logging.critical(f"Failed to execute script: {error}", exc_info=True)
    except KeyboardInterrupt:
        logging.info("Script stopped by user")
        