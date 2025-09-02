import {
  Notifications as NotificationsIcon,
  Email as EmailIcon,
  Chat as SlackIcon,
  Groups as TeamsIcon,
  BugReport as JiraIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as TestIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Settings as ConfigIcon,
  Rule as RuleIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
} from '@mui/material';
import React, { useState } from 'react';

import {
  NotificationIntegration,
  NotificationRule,
  NotificationHistory,
} from '../types/pages/Notifications_Types';

// Mock data for frontend preview
const mockIntegrations: NotificationIntegration[] = [
  {
    id: '1',
    name: 'Production Email Alerts',
    type: 'email',
    enabled: true,
    config: {
      smtp_host: 'smtp.gmail.com',
      smtp_port: 587,
      smtp_username: 'alerts@company.com',
      smtp_password: '***',
      from_email: 'alerts@company.com',
      from_name: 'VirtualPyTest',
      use_tls: true,
    },
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    name: 'Dev Team Slack',
    type: 'slack',
    enabled: true,
    config: {
      webhook_url: 'https://hooks.slack.com/services/***',
      channel: '#dev-alerts',
      username: 'VirtualPyTest Bot',
    },
    created_at: '2024-01-10T14:20:00Z',
    updated_at: '2024-01-10T14:20:00Z',
  },
  {
    id: '3',
    name: 'QA Team Teams',
    type: 'teams',
    enabled: false,
    config: {
      webhook_url: 'https://company.webhook.office.com/***',
    },
    created_at: '2024-01-08T09:15:00Z',
    updated_at: '2024-01-08T09:15:00Z',
  },
  {
    id: '4',
    name: 'Bug Tracking Jira',
    type: 'jira',
    enabled: true,
    config: {
      server_url: 'https://company.atlassian.net',
      username: 'automation@company.com',
      api_token: '***',
      project_key: 'TEST',
      issue_type: 'Bug',
    },
    created_at: '2024-01-05T12:00:00Z',
    updated_at: '2024-01-05T12:00:00Z',
  },
];

const mockRules: NotificationRule[] = [
  {
    id: '1',
    name: 'Script Failure Alerts',
    enabled: true,
    event_type: 'script_execution_failed',
    integration_ids: ['1', '2', '4'],
    created_at: '2024-01-15T11:00:00Z',
    updated_at: '2024-01-15T11:00:00Z',
  },
  {
    id: '2',
    name: 'Campaign Completion',
    enabled: true,
    event_type: 'campaign_execution_complete',
    integration_ids: ['1'],
    created_at: '2024-01-12T16:45:00Z',
    updated_at: '2024-01-12T16:45:00Z',
  },
  {
    id: '3',
    name: 'System Alerts',
    enabled: false,
    event_type: 'system_alert',
    integration_ids: ['2', '3'],
    created_at: '2024-01-10T08:30:00Z',
    updated_at: '2024-01-10T08:30:00Z',
  },
  {
    id: '4',
    name: 'Monitoring Incidents',
    enabled: true,
    event_type: 'monitoring_incident',
    integration_ids: ['1', '2'],
    created_at: '2024-01-08T14:30:00Z',
    updated_at: '2024-01-08T14:30:00Z',
  },
];

const mockHistory: NotificationHistory[] = [
  {
    id: '1',
    event_type: 'script_execution_failed',
    integration_type: 'email',
    integration_name: 'Production Email Alerts',
    recipient: 'team@company.com',
    status: 'sent',
    message_preview: 'Script "test_login_flow" failed on host-01 after 45s',
    sent_at: '2024-01-15T15:30:00Z',
    event_data: {
      script_name: 'test_login_flow',
      host_name: 'host-01',
      device_name: 'android_mobile_01',
      success: false,
      duration: 45000,
    },
  },
  {
    id: '2',
    event_type: 'script_execution_failed',
    integration_type: 'slack',
    integration_name: 'Dev Team Slack',
    recipient: '#dev-alerts',
    status: 'sent',
    message_preview: 'Script "test_login_flow" failed on host-01 after 45s',
    sent_at: '2024-01-15T15:30:05Z',
    event_data: {
      script_name: 'test_login_flow',
      host_name: 'host-01',
      device_name: 'android_mobile_01',
      success: false,
      duration: 45000,
    },
  },
  {
    id: '3',
    event_type: 'script_execution_failed',
    integration_type: 'jira',
    integration_name: 'Bug Tracking Jira',
    recipient: 'TEST-1234',
    status: 'sent',
    message_preview: 'Created ticket: Script test_login_flow failed',
    sent_at: '2024-01-15T15:30:10Z',
    event_data: {
      script_name: 'test_login_flow',
      host_name: 'host-01',
      device_name: 'android_mobile_01',
      success: false,
      duration: 45000,
    },
  },
  {
    id: '4',
    event_type: 'campaign_execution_complete',
    integration_type: 'email',
    integration_name: 'Production Email Alerts',
    recipient: 'team@company.com',
    status: 'sent',
    message_preview: 'Campaign "Nightly Regression" completed successfully (5/5 scripts passed)',
    sent_at: '2024-01-15T02:15:00Z',
    event_data: {
      campaign_name: 'Nightly Regression',
      success: true,
      duration: 1800000,
    },
  },
  {
    id: '5',
    event_type: 'system_alert',
    integration_type: 'teams',
    integration_name: 'QA Team Teams',
    recipient: 'QA Channel',
    status: 'failed',
    message_preview: 'High CPU usage detected on host-02',
    error_message: 'Webhook URL returned 404 - endpoint not found',
    sent_at: '2024-01-14T18:45:00Z',
  },
  {
    id: '6',
    event_type: 'monitoring_incident',
    integration_type: 'slack',
    integration_name: 'Dev Team Slack',
    recipient: '#dev-alerts',
    status: 'sent',
    message_preview: 'Host host-03 is unreachable - connection timeout',
    sent_at: '2024-01-14T12:20:00Z',
  },
  {
    id: '7',
    event_type: 'script_execution_complete',
    integration_type: 'email',
    integration_name: 'Production Email Alerts',
    recipient: 'team@company.com',
    status: 'pending',
    message_preview: 'Script "test_checkout_flow" completed successfully in 32s',
    sent_at: '2024-01-15T16:45:00Z',
    event_data: {
      script_name: 'test_checkout_flow',
      host_name: 'host-02',
      device_name: 'android_tv_01',
      success: true,
      duration: 32000,
    },
  },
];

const NotificationsMock: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  // Helper functions
  const getIntegrationIcon = (type: string) => {
    switch (type) {
      case 'email':
        return <EmailIcon fontSize="small" />;
      case 'slack':
        return <SlackIcon fontSize="small" />;
      case 'teams':
        return <TeamsIcon fontSize="small" />;
      case 'jira':
        return <JiraIcon fontSize="small" />;
      default:
        return <NotificationsIcon fontSize="small" />;
    }
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'sent':
        return (
          <Chip
            icon={<SuccessIcon />}
            label="Sent"
            color="success"
            size="small"
          />
        );
      case 'failed':
        return (
          <Chip
            icon={<ErrorIcon />}
            label="Failed"
            color="error"
            size="small"
          />
        );
      case 'pending':
        return (
          <Chip
            icon={<PendingIcon />}
            label="Pending"
            color="warning"
            size="small"
          />
        );
      default:
        return (
          <Chip
            label="Unknown"
            color="default"
            size="small"
          />
        );
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const handleTestIntegration = (id: string, name: string) => {
    console.log(`[MOCK] Testing integration: ${name} (${id})`);
    alert(`Testing integration "${name}" - this would send a test notification when backend is ready.`);
  };

  const handleDeleteIntegration = (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete the integration "${name}"?`)) {
      console.log(`[MOCK] Deleting integration: ${name} (${id})`);
      alert(`Integration "${name}" would be deleted when backend is ready.`);
    }
  };

  const handleDeleteRule = (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete the rule "${name}"?`)) {
      console.log(`[MOCK] Deleting rule: ${name} (${id})`);
      alert(`Rule "${name}" would be deleted when backend is ready.`);
    }
  };

  // Integrations Tab Content
  const IntegrationsTab = () => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Notification Integrations
          </Typography>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            size="small"
            onClick={() => {
              console.log('[MOCK] Create integration clicked');
              alert('Create integration dialog would open when backend is ready.');
            }}
          >
            Add Integration
          </Button>
        </Box>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Name</strong></TableCell>
                <TableCell><strong>Type</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>Created</strong></TableCell>
                <TableCell><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mockIntegrations.map((integration) => (
                <TableRow key={integration.id}>
                  <TableCell>{integration.name}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getIntegrationIcon(integration.type)}
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {integration.type}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={integration.enabled ? 'Enabled' : 'Disabled'}
                      color={integration.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatDate(integration.created_at)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Tooltip title="Test Integration">
                        <IconButton
                          size="small"
                          onClick={() => handleTestIntegration(integration.id, integration.name)}
                        >
                          <TestIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit Integration">
                        <IconButton
                          size="small"
                          onClick={() => {
                            console.log('[MOCK] Edit integration:', integration.id);
                            alert(`Edit integration "${integration.name}" dialog would open when backend is ready.`);
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Integration">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteIntegration(integration.id, integration.name)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );

  // Rules Tab Content
  const RulesTab = () => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Notification Rules
          </Typography>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            size="small"
            onClick={() => {
              console.log('[MOCK] Create rule clicked');
              alert('Create rule dialog would open when backend is ready.');
            }}
          >
            Add Rule
          </Button>
        </Box>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Name</strong></TableCell>
                <TableCell><strong>Event Type</strong></TableCell>
                <TableCell><strong>Integrations</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>Created</strong></TableCell>
                <TableCell><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mockRules.map((rule) => (
                <TableRow key={rule.id}>
                  <TableCell>{rule.name}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                      {rule.event_type.replace(/_/g, ' ')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {rule.integration_ids.length} integration(s)
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={rule.enabled ? 'Enabled' : 'Disabled'}
                      color={rule.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatDate(rule.created_at)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Tooltip title="Edit Rule">
                        <IconButton
                          size="small"
                          onClick={() => {
                            console.log('[MOCK] Edit rule:', rule.id);
                            alert(`Edit rule "${rule.name}" dialog would open when backend is ready.`);
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Rule">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteRule(rule.id, rule.name)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );

  // History Tab Content
  const HistoryTab = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Notification History
        </Typography>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Timestamp</strong></TableCell>
                <TableCell><strong>Event Type</strong></TableCell>
                <TableCell><strong>Integration</strong></TableCell>
                <TableCell><strong>Recipient</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>Message Preview</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mockHistory.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{formatDate(item.sent_at)}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                      {item.event_type.replace(/_/g, ' ')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getIntegrationIcon(item.integration_type)}
                      <Typography variant="body2">
                        {item.integration_name}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {item.recipient}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {getStatusChip(item.status)}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ 
                      maxWidth: 300, 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {item.message_preview}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Box sx={{ mb: 1 }}>
        <Typography variant="h4" gutterBottom>
          Notifications (Frontend Preview)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This is a frontend mockup showing what the notification system will look like. All data is mock data and no backend calls are made.
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Box sx={{ mb: 0.5 }}>
        <Card>
          <CardContent sx={{ py: 0.5 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" gap={1}>
                <NotificationsIcon color="primary" />
                <Typography variant="h6">Quick Stats</Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={4}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Integrations</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {mockIntegrations.length}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Active Rules</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {mockRules.filter(rule => rule.enabled).length}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">Sent Today</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {mockHistory.filter(item => {
                      const today = new Date();
                      const itemDate = new Date(item.sent_at);
                      return itemDate.toDateString() === today.toDateString();
                    }).length}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab 
            icon={<ConfigIcon />} 
            label="Integrations" 
            iconPosition="start"
          />
          <Tab 
            icon={<RuleIcon />} 
            label="Rules" 
            iconPosition="start"
          />
          <Tab 
            icon={<HistoryIcon />} 
            label="History" 
            iconPosition="start"
          />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && <IntegrationsTab />}
      {activeTab === 1 && <RulesTab />}
      {activeTab === 2 && <HistoryTab />}
    </Box>
  );
};

export default NotificationsMock;
