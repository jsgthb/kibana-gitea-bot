import logging
import yaml
import urllib3
import requests
import time
from typing import Dict, Any, List, Tuple

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
            return []
    
    def update_case_tags_and_status(self, case: Dict[str, Any], search_tag: str, new_tag: str) -> Tuple[bool, Dict[str, Any]]:
        """Replaces the search tag with a success tag and sets the case status to in-progress"""
        try:
            original_tags = case.get("tags")
            updated_tags = [tag for tag in original_tags if tag.lower() != search_tag.lower()]

            # Add new tag if not already present
            if not any(tag.lower() == new_tag.lower() for tag in updated_tags):
                updated_tags.append(new_tag)

            payload = {
                "cases": [
                    {
                        "id": case.get("id"),
                        "version": case.get("version"),
                        "tags": updated_tags,
                        "status": "in-progress"
                    }
                ]
            }
            response = requests.patch(
                f"{self.base_url}/api/cases",
                headers = self.headers,
                json = payload,
                verify = self.ssl_verification
            )
            response.raise_for_status()
            updated_case_data = response.json()
            return True, updated_case_data
        except requests.exceptions.RequestException as error:
            logging.error(f"Kibana case update failure for case '{case.get('title')}' : {error}")
            return False, {}
    
    def get_case_info(self, case_id: str) -> Dict[str, Any]:
        """Retrieves details of a single Kibana security case"""
        try:
            response = requests.get(
                f"{self.base_url}/api/cases/{case_id}",
                headers = self.headers,
                verify = self.ssl_verification
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logging.error(f"Failed to get info for case {case_id}: {error}")
            return {}
    
    def add_comment_to_case(self, case_id: str, comment: str) -> bool:
        """Adds a comment to a Kibana Security case"""
        try:
            response = requests.post(
                f"{self.base_url}/api/cases/{case_id}/comments",
                headers = self.headers,
                json = {
                    "type": "user",
                    "owner": "securitySolution",
                    "comment": comment
                },
                verify = self.ssl_verification
            )
            response.raise_for_status()
            logging.debug(f"Comment successfully posted to Kibana Security case '{case_id}'")
            return True
        except requests.exceptions.RequestException as error:
            logging.error(f"Failed to post Kibana comment to case '{case_id}' : {error}")
            return False

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
        
    def get_org_labels(self) -> List[Dict[str, Any]]:
        """Retrieves all labels for the oragnization listed in the config"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/orgs/{self.org_name}/labels",
                headers = self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logging.error(f"Failed to get Gitea org labels for '{self.org_name}': {error}")
            return []

    def create_issue(self, case: Dict[str, Any], priority_labels: Dict[str, Any], kibana_base_url: str) -> Tuple[bool, str]:
        """Creates an issue in the Gitea repository from a Kibana security case with Kibana tags converted to (pre-existing) Gitea labels"""
        issue_url = ""
        try:
            # Prepare labels
            org_labels = self.get_org_labels()
            if not org_labels:
                logging.warning("No Gitea organisation labels found. Proceeding without labels")

            label_map = {label["name"].lower(): label["id"] for label in org_labels}
            kibana_tags = case.get("tags", [])
            label_ids = {label_map[tag.lower()] for tag in kibana_tags if tag.lower() in label_map}

            # Add priority labels
            priority = case.get("severity", "low").lower()
            priority_label_id = priority_labels.get(priority, priority_labels["low"])
            label_ids.add(priority_label_id)

            # Create issue
            original_description = case.get("description")
            case_link = f"{kibana_base_url}/app/security/cases/{case.get('id')}"
            creator = case.get("created_by", {}).get("full_name", "N/A")
            description = f"{original_description}\n\n---\n*Kibana Case [{case.get('id')}]({case_link}) created by {creator}*"
            response = requests.post(
                f"{self.base_url}/api/v1/repos/{self.repo_path}/issues",
                headers = self.headers,
                json = {
                    "title": case.get("title"),
                    "body": description,
                    "labels": list(label_ids)
                }                
            )
            response.raise_for_status()
            response_data = response.json()
            issue_url = response_data.get("html_url", "")
            logging.debug(f"Successfully created Gitea issue for case '{case.get('title')}' ({issue_url})")
            return True, issue_url
        except requests.exceptions.RequestException as error:
            logging.error(f"Gitea issue creation failed for case '{case.get('title')}' : {error}")
            return False, issue_url

def process_cases(kibana_client: KibanaClient, gitea_client: GiteaClient, config: Dict[str, Any]):
    """Fetch cases from Kibana security, post them to Gitea, and update the original cases"""
    search_tag = config["kibana"]["search_tag"]
    success_tag = config["kibana"]["success_tag"]  
    logging.info(f"Checking for Kibana Security cases with tag '{search_tag}'...")        

    cases_to_process = kibana_client.get_cases_by_tag(search_tag)

    if not cases_to_process:
        logging.info("No new cases to process")
        return
    
    logging.info(f"Found {len(cases_to_process)} case(s) to process")
    for case in cases_to_process:
        case_id = case.get("id")
        case_title = case.get("title")

        if success_tag in case.get("tags"):
            logging.info(f"Skipping case '{case_title}' ({case_id}) as it has already been posted")
        
        # Create gitea issue
        issue_created, issue_url = gitea_client.create_issue(case, config["gitea"]["label_ids"]["severity"], config["kibana"]["url"])

        if issue_created:
            logging.info(f"Successfully posted '{case_title}' to Gitea")
            update_success, _ = kibana_client.update_case_tags_and_status(case, search_tag, success_tag)
            comment = f"Successfully forwarded to Gitea. Issue URL: [{issue_url}]({issue_url})"

            if update_success:
                kibana_client.add_comment_to_case(case_id, comment)
                logging.debug(f"Successfully updated tags and commented on Kibana case '{case_title}'")
            else:
                # Retry case update if it fails due to version conflict
                logging.warning(f"Failed to update case '{case_title}' after posting, attempting retry...")
                fresh_case_data = kibana_client.get_cases_by_tag
                if fresh_case_data:
                    retry_success, _ = kibana_client.update_case_tags_and_status(fresh_case_data, search_tag, success_tag)
                    if retry_success:
                        logging.debug(f"Successfully updated case '{case_title}' on retry")
                        kibana_client.add_comment_to_case(case_id, comment)
                    else:
                        logging.error(f"Case update for '{case_title}' failed on retry")

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
        