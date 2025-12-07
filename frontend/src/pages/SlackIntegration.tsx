import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Link as LinkIcon,
  Send as SendIcon,
  Settings as SettingsIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  OpenInNew as OpenInNewIcon,
  ChatBubbleOutline as ChatIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputAdornment,
  Paper,
  Switch,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { buildServerUrl } from '../utils/buildUrlUtils';

interface SlackConfig {
  enabled: boolean;
  channel_id: string;
  sync_tool_calls: boolean;
  sync_thinking: boolean;
  has_token: boolean;
}

interface SlackStatus {
  enabled: boolean;
  configured: boolean;
  channel_id: string;
  conversations_synced: number;
  last_sync: string | null;
  sync_tool_calls: boolean;
  sync_thinking: boolean;
}

const SlackIntegration: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  const [config, setConfig] = useState<SlackConfig | null>(null);
  const [status, setStatus] = useState<SlackStatus | null>(null);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  
  // Form state
  const [botToken, setBotToken] = useState('');
  const [channelId, setChannelId] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [syncToolCalls, setSyncToolCalls] = useState(false);
  const [syncThinking, setSyncThinking] = useState(false);
  const [showToken, setShowToken] = useState(false);
  
  // Loading states
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Slack workspace URL from env
  const workspaceUrl = (import.meta as any).env?.VITE_SLACK_WORKSPACE_URL || 'https://slack.com';

  // Load config and status on mount
  useEffect(() => {
    loadConfig();
    loadStatus();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch(buildServerUrl('/server/integrations/slack/config'));
      const data = await response.json();
      
      if (data.success) {
        setConfig(data.config);
        setChannelId(data.config.channel_id || '');
        setEnabled(data.config.enabled || false);
        setSyncToolCalls(data.config.sync_tool_calls || false);
        setSyncThinking(data.config.sync_thinking || false);
      }
    } catch (err) {
      console.error('Error loading Slack config:', err);
      setError('Failed to load Slack configuration');
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch(buildServerUrl('/server/integrations/slack/status'));
      const data = await response.json();
      
      if (data.success) {
        setStatus(data.status);
      }
    } catch (err) {
      console.error('Error loading Slack status:', err);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setError('');
    
    try {
      const response = await fetch(buildServerUrl('/server/integrations/slack/test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_token: botToken || undefined }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setTestResult({
          success: true,
          message: `✅ Connected to ${data.team} as ${data.user}`,
        });
      } else {
        setTestResult({
          success: false,
          message: data.error || 'Connection test failed',
        });
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: 'Failed to test connection',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    
    try {
      const payload: any = {
        channel_id: channelId,
        enabled: enabled,
        sync_tool_calls: syncToolCalls,
        sync_thinking: syncThinking,
      };
      
      // Only include token if it's been entered
      if (botToken) {
        payload.bot_token = botToken;
      }
      
      const response = await fetch(buildServerUrl('/server/integrations/slack/config'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Configuration saved successfully');
        setBotToken(''); // Clear token input after save
        await loadConfig();
        await loadStatus();
      } else {
        setError(data.error || 'Failed to save configuration');
      }
    } catch (err) {
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleSendTest = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await fetch(buildServerUrl('/server/integrations/slack/send-test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Test message sent! Check your Slack channel.');
      } else {
        setError(data.error || 'Failed to send test message');
      }
    } catch (err) {
      setError('Failed to send test message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <ChatIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Box>
          <Typography variant="h4" fontWeight={600}>
            Slack Integration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Sync AI agent conversations to your Slack workspace
          </Typography>
        </Box>
      </Box>

      {/* Messages */}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Status Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsIcon fontSize="small" />
                Status
              </Typography>
              
              <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Integration
                  </Typography>
                  <Chip
                    size="small"
                    icon={status?.enabled ? <CheckCircleIcon /> : <ErrorIcon />}
                    label={status?.enabled ? 'Enabled' : 'Disabled'}
                    color={status?.enabled ? 'success' : 'default'}
                  />
                </Box>
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Configuration
                  </Typography>
                  <Chip
                    size="small"
                    icon={status?.configured ? <CheckCircleIcon /> : <ErrorIcon />}
                    label={status?.configured ? 'Complete' : 'Incomplete'}
                    color={status?.configured ? 'success' : 'warning'}
                  />
                </Box>
                
                {status && (
                  <>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Conversations Synced
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {status.conversations_synced}
                      </Typography>
                    </Box>
                    
                    {status.last_sync && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                          Last Sync
                        </Typography>
                        <Typography variant="caption">
                          {new Date(status.last_sync).toLocaleString()}
                        </Typography>
                      </Box>
                    )}
                  </>
                )}
              </Box>

              {/* Workspace Link */}
              {status?.channel_id && (
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<OpenInNewIcon />}
                  onClick={() => window.open(workspaceUrl, '_blank')}
                  sx={{ mt: 3 }}
                >
                  Open Slack Workspace
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration Card */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsIcon fontSize="small" />
                Configuration
              </Typography>

              <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                {/* Bot Token */}
                <TextField
                  fullWidth
                  label="Bot Token"
                  placeholder="xoxb-..."
                  value={botToken}
                  onChange={(e) => setBotToken(e.target.value)}
                  type={showToken ? 'text' : 'password'}
                  helperText={config?.has_token ? '✅ Token saved (enter new token to update)' : 'Enter your Slack bot token'}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowToken(!showToken)} edge="end">
                          {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                {/* Channel ID */}
                <TextField
                  fullWidth
                  label="Channel ID"
                  placeholder="C1234567890"
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  helperText="Slack channel ID where messages will be posted"
                />

                {/* Test Connection */}
                <Box>
                  <Button
                    variant="outlined"
                    onClick={handleTestConnection}
                    disabled={!botToken && !config?.has_token}
                    startIcon={testing ? <CircularProgress size={16} /> : <LinkIcon />}
                  >
                    Test Connection
                  </Button>
                  {testResult && (
                    <Alert
                      severity={testResult.success ? 'success' : 'error'}
                      sx={{ mt: 1 }}
                    >
                      {testResult.message}
                    </Alert>
                  )}
                </Box>

                {/* Divider */}
                <Box sx={{ borderTop: '1px solid', borderColor: 'divider', my: 1 }} />

                {/* Enable Integration */}
                <FormControlLabel
                  control={
                    <Switch
                      checked={enabled}
                      onChange={(e) => setEnabled(e.target.checked)}
                      color="primary"
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        Enable Integration
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Start syncing conversations to Slack
                      </Typography>
                    </Box>
                  }
                />

                {/* Sync Options */}
                <Paper variant="outlined" sx={{ p: 2, bgcolor: isDarkMode ? 'rgba(255,255,255,0.02)' : 'grey.50' }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Sync Options (Recommended: Keep disabled)
                  </Typography>
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={syncToolCalls}
                        onChange={(e) => setSyncToolCalls(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" color="text.secondary">
                        Sync tool calls (verbose - not recommended)
                      </Typography>
                    }
                  />
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={syncThinking}
                        onChange={(e) => setSyncThinking(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" color="text.secondary">
                        Sync reasoning (verbose - not recommended)
                      </Typography>
                    }
                  />
                </Paper>

                {/* Action Buttons */}
                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Button
                    variant="contained"
                    onClick={handleSaveConfig}
                    disabled={saving}
                    startIcon={saving ? <CircularProgress size={16} /> : undefined}
                  >
                    Save Configuration
                  </Button>
                  
                  {status?.configured && status?.enabled && (
                    <Button
                      variant="outlined"
                      onClick={handleSendTest}
                      disabled={loading}
                      startIcon={loading ? <CircularProgress size={16} /> : <SendIcon />}
                    >
                      Send Test Message
                    </Button>
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Setup Instructions */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Setup Instructions
          </Typography>
          
          <Typography variant="body2" color="text.secondary" paragraph>
            Follow these steps to configure Slack integration:
          </Typography>

          <Box component="ol" sx={{ pl: 2, '& li': { mb: 1 } }}>
            <Typography component="li" variant="body2">
              Go to <a href="https://api.slack.com/apps" target="_blank" rel="noopener noreferrer" style={{ color: theme.palette.primary.main }}>https://api.slack.com/apps</a> and create a new Slack app
            </Typography>
            <Typography component="li" variant="body2">
              Under <strong>OAuth & Permissions</strong>, add these bot token scopes:
              <Box component="ul" sx={{ mt: 0.5, mb: 0.5 }}>
                <li><code>chat:write</code> - Post messages</li>
                <li><code>channels:read</code> - View channels</li>
                <li><code>channels:history</code> - Read channel history</li>
              </Box>
            </Typography>
            <Typography component="li" variant="body2">
              Install the app to your workspace
            </Typography>
            <Typography component="li" variant="body2">
              Copy the <strong>Bot User OAuth Token</strong> (starts with <code>xoxb-</code>) and paste it above
            </Typography>
            <Typography component="li" variant="body2">
              Create or select a channel in Slack, open channel details, and copy the <strong>Channel ID</strong>
            </Typography>
            <Typography component="li" variant="body2">
              Invite the bot to your channel: <code>/invite @YourBotName</code>
            </Typography>
            <Typography component="li" variant="body2">
              Save the configuration and test the connection
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default SlackIntegration;

