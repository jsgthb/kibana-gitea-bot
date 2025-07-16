# Kibana Security to Gitea Bot

A Python script that automatically forwards Kibana Security cases to Gitea as issues to provide integration between security incident management and issue tracking workflows.

## Overview

This script monitors Kibana Security cases for a specified tag and automatically creates corresponding issues in a specific Gitea repository. Once an issue is successfully created, the original Kibana case is updated with a success tag and a comment containing the Gitea issue link.

## Prerequisites

- Python 3.7+
- Kibana instance with Security app enabled
- Gitea instance with API access
- API keys with appropriate permissions for both services

### Required Permissions

**Kibana API Key:**
- All privileges for the Cases feature in Management, Observability, or Security section

**Gitea API Key:**
- Read and write access to issues
- Read access to organizations and repositories

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd kibana-gitea-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and configure the configuration file:
```bash
vim config.yml
# Edit config.yml with your settings
```

## Configuration

### Kibana Settings
- `url`: Your Kibana instance URL
- `api_key`: API key with Cases management permissions
- `verify_ssl`: Whether to verify SSL certificates (set to `false` for self-signed certs)
- `search_tag`: Tag to identify cases for processing
- `search_interval`: Polling interval in seconds
- `success_tag`: Tag applied to successfully processed cases

### Gitea Settings
- `url`: Your Gitea instance URL
- `api_key`: API key with issue management permissions
- `organization`: Gitea organization name
- `issue_repo`: Repository name for creating issues
- `label_ids`: Mapping of severity levels to Gitea label IDs

## Usage

### Basic Usage

Run the service:
```bash
python main.py
```

The service will:
1. Connect to both Kibana and Gitea APIs
2. Start monitoring for cases tagged with `search_tag`
3. Create Gitea issues for new cases
4. Update processed cases with the `success_tag` and remove the `search_tag`
5. Add comments to Kibana cases with Gitea issue links

### Workflow

1. **Case Creation**: Create a Kibana Security case and add the configured `search_tag`
2. **Automatic Processing**: The service detects the tagged case during its next polling cycle
3. **Issue Creation**: A corresponding Gitea issue is created with:
   - Case title and description
   - Severity based labels
   - Link back to the original Kibana case
4. **Case Update**: The original Kibana case is updated with:
   - Success tag replacing the search tag
   - Comment containing the Gitea issue URL
   - Status changed to "in-progress"

## Testing with Docker Compose

A complete testing environment is provided via Docker Compose, including Elasticsearch, Kibana, and Gitea instances.

### Setup Test Environment

1. Start the services:
```bash
docker-compose up -d
```

2. Wait for all services to be healthy (this may take a few minutes)

3. Access the services:
   - **Kibana**: http://localhost:5601
     - Username: `elastic`
     - Password: `changeme`
   - **Gitea**: http://localhost:3000
   - **Elasticsearch**: https://localhost:9200

## Gitea Label IDs

Labels must already exist in Gitea before they can be synchronized with Kibana tags. The script does not create new labels automatically.

To find Gitea label IDs for configuration:
```bash
curl -H "Authorization: token YOUR_API_KEY" \
     https://your-gitea-instance.com/api/v1/orgs/your-org/labels
```

## License

This project is licensed under the GNU General Public License v2.0. See the [LICENSE](LICENSE) file for details.