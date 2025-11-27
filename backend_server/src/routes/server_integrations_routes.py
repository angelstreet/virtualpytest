from flask import Blueprint, jsonify, request
import os
import json
import requests
from pathlib import Path

server_integrations_bp = Blueprint('server_integrations_bp', __name__, url_prefix='/server/integrations')

# Path to integrations config
BACKEND_SERVER_ROOT = Path(__file__).parent.parent.parent
JIRA_CONFIG_PATH = BACKEND_SERVER_ROOT / 'config' / 'integrations' / 'jira_instances.json'

def load_jira_instances():
    """Load JIRA instances configuration from JSON file"""
    try:
        if not JIRA_CONFIG_PATH.exists():
            print(f"[@integrations_routes] JIRA config not found: {JIRA_CONFIG_PATH}")
            return []
        
        with open(JIRA_CONFIG_PATH, 'r') as f:
            instances = json.load(f)
        
        print(f"[@integrations_routes] Loaded {len(instances)} JIRA instance(s)")
        return instances
    except Exception as e:
        print(f"[@integrations_routes] Error loading JIRA config: {e}")
        return []

def save_jira_instances(instances):
    """Save JIRA instances configuration to JSON file"""
    try:
        JIRA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(JIRA_CONFIG_PATH, 'w') as f:
            json.dump(instances, f, indent=2)
        print(f"[@integrations_routes] Saved {len(instances)} JIRA instance(s)")
        return True
    except Exception as e:
        print(f"[@integrations_routes] Error saving JIRA config: {e}")
        return False

def get_jira_instance_by_id(instance_id):
    """Get JIRA instance config by ID"""
    instances = load_jira_instances()
    for instance in instances:
        if instance['id'] == instance_id:
            return instance
    return None

def call_jira_api(domain, endpoint, email, api_token, method='GET', data=None):
    """Call JIRA API (security layer - API tokens never exposed to frontend)"""
    try:
        from requests.auth import HTTPBasicAuth
        
        url = f"https://{domain}/rest/api/3{endpoint}"
        auth = HTTPBasicAuth(email, api_token)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        print(f"[@integrations_routes] Calling JIRA API: {url}")
        
        if method == 'GET':
            response = requests.get(url, headers=headers, auth=auth, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, auth=auth, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Log response details for debugging
        print(f"[@integrations_routes] Response status: {response.status_code}")
        if response.status_code >= 400:
            print(f"[@integrations_routes] Error response body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[@integrations_routes] JIRA API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[@integrations_routes] Error response: {e.response.text}")
        raise


# ============================================================================
# JIRA INSTANCES MANAGEMENT
# ============================================================================

@server_integrations_bp.route('/jira/instances', methods=['GET'])
def get_jira_instances():
    """Get list of configured JIRA instances"""
    try:
        instances = load_jira_instances()
        
        # Return sanitized data (no API tokens!)
        result = []
        for instance in instances:
            result.append({
                'id': instance['id'],
                'name': instance['name'],
                'domain': instance['domain'],
                'email': instance['email'],
                'projectKey': instance.get('projectKey', ''),
            })
        
        return jsonify({
            'success': True,
            'instances': result
        })
    except Exception as e:
        print(f"[@integrations_routes:get_jira_instances] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_integrations_bp.route('/jira/instances', methods=['POST'])
def create_jira_instance():
    """Create or update JIRA instance configuration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'domain', 'email', 'apiToken', 'projectKey']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        instances = load_jira_instances()
        
        # Generate new ID or use existing
        instance_id = data.get('id', f"jira-{len(instances) + 1}")
        
        # Check if updating existing instance
        existing_index = None
        for i, instance in enumerate(instances):
            if instance['id'] == instance_id:
                existing_index = i
                break
        
        new_instance = {
            'id': instance_id,
            'name': data['name'],
            'domain': data['domain'],
            'email': data['email'],
            'apiToken': data['apiToken'],
            'projectKey': data['projectKey']
        }
        
        if existing_index is not None:
            instances[existing_index] = new_instance
        else:
            instances.append(new_instance)
        
        if not save_jira_instances(instances):
            return jsonify({
                'success': False,
                'error': 'Failed to save configuration'
            }), 500
        
        return jsonify({
            'success': True,
            'instance': {
                'id': instance_id,
                'name': new_instance['name'],
                'domain': new_instance['domain'],
                'email': new_instance['email'],
                'projectKey': new_instance['projectKey']
            }
        })
    except Exception as e:
        print(f"[@integrations_routes:create_jira_instance] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_integrations_bp.route('/jira/instances/<instance_id>', methods=['DELETE'])
def delete_jira_instance(instance_id):
    """Delete JIRA instance configuration"""
    try:
        instances = load_jira_instances()
        instances = [i for i in instances if i['id'] != instance_id]
        
        if not save_jira_instances(instances):
            return jsonify({
                'success': False,
                'error': 'Failed to save configuration'
            }), 500
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        print(f"[@integrations_routes:delete_jira_instance] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# JIRA TICKETS/ISSUES
# ============================================================================

@server_integrations_bp.route('/jira/<instance_id>/tickets', methods=['GET'])
def get_jira_tickets(instance_id):
    """Get tickets/issues from JIRA instance"""
    try:
        instance = get_jira_instance_by_id(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'error': 'JIRA instance not found'
            }), 404
        
        # Get query parameters
        status_filter = request.args.get('status', '')
        max_results = int(request.args.get('maxResults', 100))
        
        # Build JQL query
        jql = f"project={instance['projectKey']}"
        if status_filter:
            jql += f" AND status='{status_filter}'"
        jql += " ORDER BY created DESC"
        
        # Call JIRA API - use new /search/jql endpoint (v3)
        import urllib.parse
        encoded_jql = urllib.parse.quote(jql)
        endpoint = f"/search/jql?jql={encoded_jql}&maxResults={max_results}&fields=summary,status,priority,assignee,created,updated,issuetype"
        
        result = call_jira_api(
            instance['domain'],
            endpoint,
            instance['email'],
            instance['apiToken']
        )
        
        # Extract and format tickets
        tickets = []
        for issue in result.get('issues', []):
            fields = issue.get('fields', {})
            tickets.append({
                'id': issue.get('id'),
                'key': issue.get('key'),
                'summary': fields.get('summary', ''),
                'status': fields.get('status', {}).get('name', '') if fields.get('status') else 'Unknown',
                'priority': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
                'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
                'created': fields.get('created', ''),
                'updated': fields.get('updated', ''),
                'issueType': fields.get('issuetype', {}).get('name', '') if fields.get('issuetype') else 'Unknown',
                'url': f"https://{instance['domain']}/browse/{issue.get('key')}"
            })
        
        # Get statistics - new API returns isLast instead of total
        total = len(tickets)
        if not result.get('isLast', True):
            # If there are more pages, get accurate count
            count_result = call_jira_api(
                instance['domain'],
                f"/search/jql?jql={encoded_jql}&maxResults=1000",
                instance['email'],
                instance['apiToken']
            )
            total = len(count_result.get('issues', []))
        
        return jsonify({
            'success': True,
            'total': total,
            'tickets': tickets
        })
    except requests.exceptions.HTTPError as e:
        error_msg = f"JIRA API error: {e.response.status_code}"
        if e.response.status_code == 401:
            error_msg = "Authentication failed. Check email and API token."
        elif e.response.status_code == 404:
            error_msg = "Project not found. Check project key."
        
        print(f"[@integrations_routes:get_jira_tickets] {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), e.response.status_code
    except Exception as e:
        print(f"[@integrations_routes:get_jira_tickets] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_integrations_bp.route('/jira/<instance_id>/stats', methods=['GET'])
def get_jira_stats(instance_id):
    """Get ticket statistics from JIRA instance"""
    try:
        instance = get_jira_instance_by_id(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'error': 'JIRA instance not found'
            }), 404
        
        project_key = instance['projectKey']
        import urllib.parse
        
        # Helper function to get count using new /search/jql endpoint
        def get_jira_count(jql):
            encoded_jql = urllib.parse.quote(jql)
            # Use new /search/jql endpoint
            result = call_jira_api(
                instance['domain'],
                f"/search/jql?jql={encoded_jql}&maxResults=1",
                instance['email'],
                instance['apiToken']
            )
            # Count total by checking if there are more issues
            total = len(result.get('issues', []))
            if not result.get('isLast', True):
                # If not last page, we need to get actual count
                # Make another call with higher maxResults to get total
                result_full = call_jira_api(
                    instance['domain'],
                    f"/search/jql?jql={encoded_jql}&maxResults=1000",
                    instance['email'],
                    instance['apiToken']
                )
                total = len(result_full.get('issues', []))
            return total
        
        # Get counts by status
        statuses = ['Open', 'In Progress', 'Done', 'To Do', 'Closed']
        stats = {
            'total': 0,
            'byStatus': {}
        }
        
        # Get total count
        stats['total'] = get_jira_count(f"project={project_key}")
        
        # Get counts by status
        for status in statuses:
            count = get_jira_count(f"project={project_key} AND status='{status}'")
            if count > 0:
                stats['byStatus'][status] = count
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"[@integrations_routes:get_jira_stats] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_integrations_bp.route('/jira/<instance_id>/test', methods=['POST'])
def test_jira_connection(instance_id):
    """Test JIRA connection with provided credentials"""
    try:
        data = request.get_json()
        
        # Use provided credentials or existing instance
        if 'domain' in data and 'email' in data and 'apiToken' in data:
            domain = data['domain']
            email = data['email']
            api_token = data['apiToken']
            project_key = data.get('projectKey', '')
        else:
            instance = get_jira_instance_by_id(instance_id)
            if not instance:
                return jsonify({
                    'success': False,
                    'error': 'JIRA instance not found'
                }), 404
            domain = instance['domain']
            email = instance['email']
            api_token = instance['apiToken']
            project_key = instance.get('projectKey', '')
        
        # Test connection by getting myself
        result = call_jira_api(domain, '/myself', email, api_token)
        
        # If project key provided, verify it exists
        if project_key:
            call_jira_api(domain, f"/project/{project_key}", email, api_token)
        
        return jsonify({
            'success': True,
            'user': result.get('displayName', 'Unknown'),
            'email': result.get('emailAddress', email)
        })
    except requests.exceptions.HTTPError as e:
        error_msg = "Connection failed"
        if e.response.status_code == 401:
            error_msg = "Authentication failed. Check email and API token."
        elif e.response.status_code == 404:
            error_msg = "Project not found. Check project key."
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400
    except Exception as e:
        print(f"[@integrations_routes:test_jira_connection] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

