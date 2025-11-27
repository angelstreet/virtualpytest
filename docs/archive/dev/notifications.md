# Notification System Documentation

## Overview

The notification system allows users to configure integrations with external services (Email, Slack, Teams, Jira) and define rules for when notifications should be sent based on system events like script executions, campaign completions, system alerts, and monitoring incidents.

## Architecture

The notification system follows the existing VirtualPyTest architecture patterns:
- **Frontend**: React TypeScript UI for configuration and monitoring
- **Backend**: API endpoints for CRUD operations and notification sending
- **Database**: Secure storage of integration credentials and notification history

## Frontend Implementation ✅ COMPLETED

### Files Created

```
frontend/src/
├── types/pages/Notifications_Types.ts     # TypeScript type definitions
├── hooks/pages/useNotifications.ts        # React hook for API operations
├── pages/Notifications.tsx                # Main notification configuration page
├── components/common/Navigation_Bar.tsx   # Updated with notifications menu
└── App.tsx                                # Updated with notification route
```

### Features Implemented

#### 1. **Notification Integrations Management**
- **Location**: `/configuration/notifications` → Integrations tab
- **Functionality**:
  - View all configured integrations
  - Add new integrations (Email, Slack, Teams, Jira)
  - Edit existing integrations
  - Delete integrations
  - Test integrations (sends test message)
  - Enable/disable integrations

#### 2. **Notification Rules Management**
- **Location**: `/configuration/notifications` → Rules tab
- **Functionality**:
  - View all notification rules
  - Create rules linking events to integrations
  - Edit existing rules
  - Delete rules
  - Enable/disable rules

#### 3. **Notification History**
- **Location**: `/configuration/notifications` → History tab
- **Functionality**:
  - View sent notification history
  - Basic information: timestamp, event type, integration, recipient, status
  - Message preview with click-to-expand (ready for implementation)
  - Status tracking (sent, failed, pending)

#### 4. **Integration Types Supported**

##### Email (SMTP)
```typescript
interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string; // Securely stored in backend
  from_email: string;
  from_name?: string;
  use_tls: boolean;
}
```

##### Slack
```typescript
interface SlackConfig {
  webhook_url: string; // Securely stored in backend
  channel?: string;
  username?: string;
}
```

##### Microsoft Teams
```typescript
interface TeamsConfig {
  webhook_url: string; // Securely stored in backend
}
```

##### Jira
```typescript
interface JiraConfig {
  server_url: string;
  username: string;
  api_token: string; // Securely stored in backend
  project_key: string;
  issue_type: string;
}
```

#### 5. **Event Types Supported**
- `script_execution_complete` - When a script finishes successfully
- `script_execution_failed` - When a script fails
- `campaign_execution_complete` - When a campaign finishes successfully
- `campaign_execution_failed` - When a campaign fails
- `system_alert` - System-level alerts
- `monitoring_incident` - Monitoring system incidents

#### 6. **UI Components**
- **Quick Stats**: Shows integration count, active rules, notifications sent today
- **Tabbed Interface**: Clean separation of integrations, rules, and history
- **Table Views**: Consistent with existing pages (TestReports.tsx pattern)
- **Action Buttons**: Test, Edit, Delete with proper icons and tooltips
- **Status Chips**: Visual status indicators for integrations and notifications

### API Integration Ready

The frontend hook (`useNotifications.ts`) is configured to make API calls to:

```typescript
const NOTIFICATIONS_API_BASE_URL = '/server/notifications';

// Expected endpoints:
GET    /server/notifications/integrations
POST   /server/notifications/integrations
PUT    /server/notifications/integrations/:id
DELETE /server/notifications/integrations/:id
POST   /server/notifications/integrations/:id/test

GET    /server/notifications/rules
POST   /server/notifications/rules
PUT    /server/notifications/rules/:id
DELETE /server/notifications/rules/:id

GET    /server/notifications/history
```

## Backend Implementation 🚧 TODO

### Required API Endpoints

#### 1. **Integration Management Endpoints**

```python
# GET /server/notifications/integrations
# Returns: List[NotificationIntegration]
@app.route('/server/notifications/integrations', methods=['GET'])
def get_integrations():
    """Get all notification integrations"""
    pass

# POST /server/notifications/integrations
# Body: NotificationIntegrationCreatePayload
# Returns: NotificationIntegration
@app.route('/server/notifications/integrations', methods=['POST'])
def create_integration():
    """Create new notification integration"""
    pass

# PUT /server/notifications/integrations/<id>
# Body: NotificationIntegrationCreatePayload
# Returns: NotificationIntegration
@app.route('/server/notifications/integrations/<id>', methods=['PUT'])
def update_integration(id):
    """Update notification integration"""
    pass

# DELETE /server/notifications/integrations/<id>
@app.route('/server/notifications/integrations/<id>', methods=['DELETE'])
def delete_integration(id):
    """Delete notification integration"""
    pass

# POST /server/notifications/integrations/<id>/test
# Returns: {"success": bool, "message": str}
@app.route('/server/notifications/integrations/<id>/test', methods=['POST'])
def test_integration(id):
    """Send test notification to verify integration works"""
    pass
```

#### 2. **Rules Management Endpoints**

```python
# GET /server/notifications/rules
@app.route('/server/notifications/rules', methods=['GET'])
def get_rules():
    """Get all notification rules"""
    pass

# POST /server/notifications/rules
@app.route('/server/notifications/rules', methods=['POST'])
def create_rule():
    """Create new notification rule"""
    pass

# PUT /server/notifications/rules/<id>
@app.route('/server/notifications/rules/<id>', methods=['PUT'])
def update_rule(id):
    """Update notification rule"""
    pass

# DELETE /server/notifications/rules/<id>
@app.route('/server/notifications/rules/<id>', methods=['DELETE'])
def delete_rule(id):
    """Delete notification rule"""
    pass
```

#### 3. **History Endpoint**

```python
# GET /server/notifications/history
@app.route('/server/notifications/history', methods=['GET'])
def get_notification_history():
    """Get notification history with pagination"""
    pass
```

### Database Schema

#### Tables Required

```sql
-- Notification integrations table
CREATE TABLE notification_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'email', 'slack', 'teams', 'jira'
    enabled BOOLEAN DEFAULT true,
    config JSONB NOT NULL, -- Encrypted sensitive data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification rules table
CREATE TABLE notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    event_type VARCHAR(100) NOT NULL,
    integration_ids UUID[] NOT NULL, -- Array of integration IDs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification history table
CREATE TABLE notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    integration_type VARCHAR(50) NOT NULL,
    integration_name VARCHAR(255) NOT NULL,
    recipient VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'sent', 'failed', 'pending'
    message_preview TEXT,
    error_message TEXT,
    event_data JSONB, -- Context data (script_name, host, etc.)
    sent_at TIMESTAMP DEFAULT NOW()
);
```

### Security Requirements

#### 1. **Credential Encryption**
- All sensitive data (passwords, API tokens, webhook URLs) must be encrypted before storage
- Use application-level encryption with a secure key management system
- Never return decrypted credentials to the frontend

#### 2. **API Security**
- Validate all input data
- Sanitize configuration data before storage
- Rate limiting for test endpoints to prevent abuse

### Notification Sending Logic

#### 1. **Event Triggers**
Integrate notification sending into existing event handlers:

```python
# Example: After script execution completes
def handle_script_completion(script_result):
    # Existing logic...
    
    # Trigger notifications
    event_type = 'script_execution_complete' if script_result.success else 'script_execution_failed'
    event_data = {
        'script_name': script_result.script_name,
        'host_name': script_result.host_name,
        'device_name': script_result.device_name,
        'success': script_result.success,
        'duration': script_result.execution_time_ms
    }
    
    send_notifications(event_type, event_data)
```

#### 2. **Notification Dispatcher**

```python
def send_notifications(event_type: str, event_data: dict):
    """Send notifications for a specific event"""
    # Get active rules for this event type
    rules = get_active_rules_for_event(event_type)
    
    for rule in rules:
        for integration_id in rule.integration_ids:
            integration = get_integration(integration_id)
            if integration and integration.enabled:
                send_notification_async(integration, event_type, event_data)

async def send_notification_async(integration, event_type, event_data):
    """Send notification asynchronously"""
    try:
        if integration.type == 'email':
            await send_email_notification(integration, event_type, event_data)
        elif integration.type == 'slack':
            await send_slack_notification(integration, event_type, event_data)
        elif integration.type == 'teams':
            await send_teams_notification(integration, event_type, event_data)
        elif integration.type == 'jira':
            await send_jira_notification(integration, event_type, event_data)
        
        # Log success
        log_notification_history(integration, event_type, event_data, 'sent')
        
    except Exception as e:
        # Log failure
        log_notification_history(integration, event_type, event_data, 'failed', str(e))
```

#### 3. **Integration Implementations**

```python
async def send_email_notification(integration, event_type, event_data):
    """Send email notification via SMTP"""
    config = decrypt_config(integration.config)
    # SMTP implementation
    pass

async def send_slack_notification(integration, event_type, event_data):
    """Send Slack notification via webhook"""
    config = decrypt_config(integration.config)
    # Slack webhook implementation
    pass

async def send_teams_notification(integration, event_type, event_data):
    """Send Teams notification via webhook"""
    config = decrypt_config(integration.config)
    # Teams webhook implementation
    pass

async def send_jira_notification(integration, event_type, event_data):
    """Create Jira ticket"""
    config = decrypt_config(integration.config)
    # Jira API implementation
    pass
```

## Usage Examples

### Frontend Usage

```typescript
// In a React component
const {
  integrations,
  rules,
  history,
  createIntegration,
  testIntegration,
  isLoading,
  error
} = useNotifications();

// Create email integration
const emailConfig = {
  name: "Production Alerts",
  type: "email",
  enabled: true,
  config: {
    smtp_host: "smtp.gmail.com",
    smtp_port: 587,
    smtp_username: "alerts@company.com",
    smtp_password: "app-password",
    from_email: "alerts@company.com",
    from_name: "VirtualPyTest Alerts",
    use_tls: true
  }
};

await createIntegration(emailConfig);
```

### Backend Integration Points

```python
# In script execution handler
from notifications import send_notifications

def complete_script_execution(script_result):
    # Existing completion logic...
    
    # Send notifications
    event_type = 'script_execution_complete' if script_result.success else 'script_execution_failed'
    event_data = {
        'script_name': script_result.script_name,
        'host_name': script_result.host_name,
        'device_name': script_result.device_name,
        'success': script_result.success,
        'duration': script_result.execution_time_ms
    }
    
    send_notifications(event_type, event_data)
```

## Future Enhancements

### Phase 2 Features (Not Currently Implemented)
- **Severity Levels**: Error, Warning, Info notification levels
- **Message Templates**: Customizable notification message templates
- **Filtering**: Advanced filtering in notification history
- **Retry Logic**: Automatic retry for failed notifications
- **Notification Channels**: Per-host or per-device notification rules
- **Escalation**: Escalation rules for critical failures
- **Digest Notifications**: Batch notifications for high-frequency events

### Integration Enhancements
- **Email**: Support for HTML templates, attachments
- **Slack**: Support for Slack apps, interactive messages
- **Teams**: Support for adaptive cards, mentions
- **Jira**: Support for custom fields, issue linking
- **Additional Integrations**: Discord, PagerDuty, Webhook generic

## Testing

### Frontend Testing
The frontend is ready for testing once backend endpoints are implemented:
1. Navigate to `/configuration/notifications`
2. Test all CRUD operations for integrations and rules
3. Verify notification history display
4. Test integration test functionality

### Backend Testing
Required test coverage:
- API endpoint functionality
- Database operations
- Notification sending logic
- Error handling and logging
- Security (credential encryption/decryption)

## Deployment Considerations

1. **Environment Variables**: Configure SMTP settings, encryption keys
2. **Database Migrations**: Run schema creation scripts
3. **Background Tasks**: Set up async task processing for notifications
4. **Monitoring**: Monitor notification success/failure rates
5. **Backup**: Ensure notification history is included in backups

---

**Status**: Frontend ✅ Complete | Backend 🚧 Pending Implementation
