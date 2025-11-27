# Integrations

**Connect VirtualPyTest to external tools and services.**

Integration guides for third-party tools, services, and platforms.

---

## Available Integrations

### 🎫 JIRA Integration

**[JIRA Integration Guide](./JIRA_INTEGRATION.md)**

Connect VirtualPyTest to Atlassian JIRA for:
- Test case synchronization
- Automated defect creation
- Requirement traceability
- Test execution tracking
- Sprint planning integration

**Features:**
- Bi-directional sync
- Multiple JIRA instances
- Custom field mapping
- Webhook notifications
- Issue linking

---

## Coming Soon

### Planned Integrations

**Test Management:**
- TestRail
- Zephyr
- qTest
- PractiTest

**CI/CD:**
- GitHub Actions ✅ (see [Examples](../examples/README.md))
- Jenkins ✅ (see [Examples](../examples/README.md))
- GitLab CI ✅ (see [Examples](../examples/README.md))
- Azure DevOps
- CircleCI

**Communication:**
- Slack ✅ (see [Features - Integrations](../features/integrations.md))
- Microsoft Teams
- Discord
- Mattermost

**Monitoring:**
- Grafana ✅ (built-in, see [Features - Analytics](../features/analytics.md))
- Datadog
- New Relic
- Prometheus

**Cloud Storage:**
- Cloudflare R2 ✅ (configured in setup)
- AWS S3 ✅ (see [Features - Integrations](../features/integrations.md))
- Google Cloud Storage ✅ (see [Features - Integrations](../features/integrations.md))
- Azure Blob Storage

---

## Integration Patterns

### REST API

All integrations can use the VirtualPyTest REST API:

**[API Reference](../api/README.md)**

```python
from shared.src.api.client import VirtualPyTestClient

client = VirtualPyTestClient(
    server_url="http://localhost:5109",
    api_key="YOUR_API_KEY"
)

# Use in your integration
results = client.get_test_results()
```

---

### Webhooks

Receive real-time events:

```json
{
  "webhooks": [
    {
      "url": "https://your-service.com/webhook",
      "events": ["test.completed", "device.offline"],
      "secret": "webhook_secret"
    }
  ]
}
```

---

### Database Access

Direct Supabase database access for custom integrations:

```python
from shared.src.supabase_manager import SupabaseManager

db = SupabaseManager()

# Query test results
results = db.table("test_results") \
    .select("*") \
    .eq("status", "failed") \
    .execute()

# Insert custom data
db.table("custom_metrics").insert({
    "metric_name": "custom_kpi",
    "value": 95.5
}).execute()
```

---

## Request an Integration

Want to integrate VirtualPyTest with a tool not listed here?

1. 📝 [Open a feature request](https://github.com/angelstreet/virtualpytest/issues/new?labels=integration)
2. Describe the tool and use case
3. We'll help you build it or add it to our roadmap!

---

## Build Your Own Integration

VirtualPyTest is designed to be extensible:

**[Technical Docs - Architecture](../technical/README.md)**

**Steps:**
1. Use the REST API for external integrations
2. Import VirtualPyTest modules for Python integrations
3. Use webhooks for event-driven integrations
4. Access the database for data integrations

**Example Custom Integration:**
```python
class CustomIntegration:
    """Example custom integration."""
    
    def __init__(self):
        self.vpt_client = VirtualPyTestClient()
        self.external_service = YourExternalService()
        
    def sync_results(self):
        """Sync test results to external service."""
        results = self.vpt_client.get_test_results()
        self.external_service.upload(results)
        
    def on_test_completed(self, webhook_data):
        """Handle test completion webhook."""
        test_id = webhook_data["data"]["test_case_id"]
        status = webhook_data["data"]["status"]
        
        # Do something with the result
        self.external_service.notify(test_id, status)
```

---

## Related Documentation

- **[Features - Integrations](../features/integrations.md)** - Integration capabilities
- **[API Reference](../api/README.md)** - REST API documentation
- **[User Guide](../user-guide/README.md)** - Using integrations
- **[Examples](../examples/README.md)** - Integration examples

---

**Ready to connect VirtualPyTest?**  
➡️ [JIRA Integration Guide](./JIRA_INTEGRATION.md)  
➡️ [API Reference](../api/README.md)

