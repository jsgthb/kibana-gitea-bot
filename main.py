import logging
import yaml
import urllib3
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

class KibanaClient:
    """Responsible for all interactions with the Kibana API"""
    def __init__(self, base_url: str, api_key: str, ssl_verification: bool = True):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"ApiKey {api_key}",
            "kbn-xsrf": "true",
            "Content-Type": "application/json"
        }
        self.ssl_verification = ssl_verification

        if not self.ssl_verification:
            # Disable unsecure SSL warnings
            logging.warning(f"SSL verification disabled for Kibana requests (verify_ssl = False)")
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    try:
        config = load_config()
        logging.basicConfig(
            level=config["logging"]["level"].upper(),
            format=config["logging"]["format"],
        )
        logging.info("Config successfully loaded!")

        client = KibanaClient(
            base_url = config["kibana"]["url"],
            api_key = config["kibana"]["api_key"],
            ssl_verification = config["kibana"]["verify_ssl"],
        )

    except Exception as error:
        logging.critical(f"Failed to execute script: {error}", exc_info=True)
    except KeyboardInterrupt:
        logging.info("Script stopped by user")
        