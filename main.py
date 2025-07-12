import logging
import yaml
import urllib3
import requests
import time
from typing import Dict, Any, List

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

    def test_connection(self) -> bool:
        """Test Kibana Cases connection by fetching a random case"""
        # TODO better test for checking case update permissions
        try:
            # Non existent case ID to check Kibana case permissions
            test_case_id = "00000000-0000-0000-0000-000000000000"
            response = requests.get(
                f"{self.base_url}/api/cases/{test_case_id}",
                headers = self.headers,
                verify = self.ssl_verification
            )
            response.raise_for_status()
            # Code shouldn't be reached as case most likely doesn't exist
            logging.info("Successfully connected to Kibana Security!")
            return True
        except requests.exceptions.HTTPError as error:
            # 404 means request is authenticated and has permission to retireve cases
            if error.response.status_code == 404:
                logging.info("Successfully connected to Kibana Security!")
                return True
            # Specific failures
            elif error.response.status_code == 401:
                logging.error("Kibana authentication failed: Unauthorized (401). Check API key")
            elif error.response.status_code == 403:
                logging.error("Kibana authentication failed: Forbidden (403). API key is valid but lacks permissions for security cases")
            else:
                logging.error(f"Kibana connection failed with an HTTP error: {error}")
            return False
        except requests.exceptions.RequestException as error:
            # Other errors such as connection timeouts or DNS errors
            logging.error(f"Kibana connection failure: {error}")
            return False
    
    def get_cases_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Retrieves all (up to 100) Kibana cases with the specificied tag"""
        try:
            response = requests.get(
                f"{self.base_url}/api/cases/_find",
                headers = self.headers,
                params = {
                    "tags": [
                        tag,
                        tag.lower(),
                        tag.title(),
                        tag.upper()
                    ],
                    "perPage": 100
                },
                verify = self.ssl_verification
            )
            response.raise_for_status()
            data = response.json()
            return data.get("cases", [])
        except requests.exceptions.RequestException as error:
            logging.error(f"Failed to get Kibana security cases by tag '{tag}': {error}")

class GiteaClient:
    """Responsible for all interactions with the Gitea API"""
    def __init__(self, base_url: str, api_key: str, org_name: str, repo_name: str):
        self.base_url = base_url.rstrip("/")
        self.org_name = org_name
        self.repo_name = repo_name
        self.repo_path = f"{org_name}/{repo_name}"
        self.headers = {
            "Authorization": f"token {api_key}",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> bool:
        """Test Gitea connection by checking config repository"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/repos/{self.repo_path}",
                headers = self.headers
            )
            response.raise_for_status()
            logging.info("Successfully connected to Gitea!")
            return True
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401 or status == 403:
                response_json = e.response.json()
                message = response_json.get("message", "No message provided")
                logging.error(f"Gitea authentication failed ({status}). Check API key and permissions for repo '{self.repo_path}' ({message})")
            elif status == 404:
                logging.error(f"Gitea repository '{self.repo_path}' not found (404)")
            else:
                logging.error(f"Gitea connection failed with HTTP error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Gitea connection failure: {e}")
            return False

def process_cases(kibana_client: KibanaClient, gitea_client: GiteaClient, config: Dict[str, Any]):
    """Fetch cases from Kibana security, post them to Gitea, and update the original cases"""
    search_tag = config["kibana"]["search_tag"] 
    logging.info(f"Checking for Kibana Security cases with tag '{search_tag}'")        

    cases_to_process = kibana_client.get_cases_by_tag(search_tag)

    if not cases_to_process:
        logging.info("No new cases to process")
        return
    
    logging.info(f"Found {len(cases_to_process)} case(s) to process")

if __name__ == "__main__":
    try:
        config = load_config()
        logging.basicConfig(
            level=config["logging"]["level"].upper(),
            format=config["logging"]["format"],
        )
        logging.info(f"Config successfully loaded from {CONFIG_PATH}!")

        kibana_client = KibanaClient(
            base_url = config["kibana"]["url"],
            api_key = config["kibana"]["api_key"],
            ssl_verification = config["kibana"]["verify_ssl"],
        )
        kibana_connected = kibana_client.test_connection()

        gitea_client = GiteaClient(
            base_url = config["gitea"]["url"],
            api_key = config["gitea"]["api_key"],
            org_name = config["gitea"]["organization"],
            repo_name = config["gitea"]["issue_repo"]
        )
        gitea_connected = gitea_client.test_connection()

        if not kibana_connected or not gitea_connected:
            logging.critical("One or more API connection tests failed. Exiting")
            exit(1)

        search_interval = config["kibana"]["search_interval"]
        logging.info(f"All connections successful! Starting monitoring loop with {search_interval} second interval")
        while True:
            process_cases(kibana_client, gitea_client, config)
            time.sleep(search_interval)

    except Exception as error:
        logging.critical(f"Failed to execute script: {error}", exc_info=True)
    except KeyboardInterrupt:
        logging.info("Script stopped by user")
        