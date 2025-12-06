/**
 * Agent Dashboard Page
 * 
 * Professional dark theme with gold accents
 * Tabs: Agents | Benchmarks | Leaderboard
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, Container, Paper, Typography, Button,
  IconButton, Tooltip, Chip, Switch, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Alert, Tabs, Tab,
  LinearProgress, Rating, Table, TableBody, TableCell, TableHead, TableRow
} from '@mui/material';
import { 
  PlayArrow, Stop, Description, CloudUpload, CloudDownload,
  Refresh, PowerSettingsNew, ExpandMore, ExpandLess,
  CheckCircle, Error as ErrorIcon, Warning, Schedule,
  EmojiEvents, Speed, Star
} from '@mui/icons-material';
import { buildServerUrl } from '../utils/buildUrlUtils';

// Types
interface AgentDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  status: 'active' | 'disabled' | 'running' | 'error';
  type: 'continuous' | 'on-demand';
  triggers: string[];
  lastRun?: string;
  instanceId?: string;
}

interface AgentLog {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  agentId: string;
}

interface BenchmarkRun {
  id: string;
  agent_id: string;
  agent_version: string;
  status: string;
  total_tests: number;
  completed_tests: number;
  passed_tests: number;
  failed_tests: number;
  score_percent: number;
  created_at: string;
}

interface LeaderboardEntry {
  agent_id: string;
  agent_version: string;
  overall_score: number;
  benchmark_score: number;
  user_rating_score: number;
  success_rate_score: number;
  avg_user_rating: number;
  total_executions: number;
  rank: number;
  score_trend?: string;
}

// Gold accent colors
const GOLD = '#D4AF37';
const GOLD_DARK = '#B8860B';

export const AgentDashboard: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState(0);
  
  // Agents tab state
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentDefinition | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importYaml, setImportYaml] = useState('');
  const [expandedLogs, setExpandedLogs] = useState(false);
  const [hasAutoStarted, setHasAutoStarted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Benchmarks tab state
  const [benchmarkRuns, setBenchmarkRuns] = useState<BenchmarkRun[]>([]);
  const [runningBenchmark, setRunningBenchmark] = useState(false);
  const [selectedBenchmarkAgent, setSelectedBenchmarkAgent] = useState('');
  
  // Leaderboard tab state
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  
  // Feedback state
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackAgentId, setFeedbackAgentId] = useState('');

  // Load data on mount
  useEffect(() => {
    loadAgents();
    loadBenchmarkRuns();
    loadLeaderboard();
    const interval = setInterval(() => {
      loadAgents();
      if (activeTab === 1) loadBenchmarkRuns();
      if (activeTab === 2) loadLeaderboard();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab]);

  // Auto-start agents
  useEffect(() => {
    if (!hasAutoStarted && agents.length > 0) {
      autoStartAgents(agents.filter(a => a.status === 'active'));
      setHasAutoStarted(true);
    }
  }, [agents, hasAutoStarted]);

  const loadAgents = async () => {
    try {
      const response = await fetch(buildServerUrl('/api/agents'));
      if (!response.ok) {
        setAgents(getDefaultAgents());
        return;
      }
      const data = await response.json();
      setAgents(data.agents || getDefaultAgents());
      setError(null);
    } catch (err) {
      setAgents(getDefaultAgents());
      setError('API not available - showing predefined agents');
    }
  };

  const loadBenchmarkRuns = async () => {
    try {
      const response = await fetch(buildServerUrl('/api/benchmarks/runs'));
      if (response.ok) {
        const data = await response.json();
        setBenchmarkRuns(data.runs || []);
      }
    } catch (err) {
      console.error('Failed to load benchmark runs:', err);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const response = await fetch(buildServerUrl('/api/benchmarks/leaderboard'));
      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data.leaderboard || []);
      }
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  };

  const getDefaultAgents = (): AgentDefinition[] => [
    {
      id: 'qa-web-manager',
      name: 'QA Web Manager',
      version: '1.0.0',
      description: 'Web testing and browser automation specialist',
      status: 'active',
      type: 'continuous',
      triggers: ['alert.blackscreen', 'build.deployed', 'schedule.web_regression']
    },
    {
      id: 'qa-mobile-manager',
      name: 'QA Mobile Manager',
      version: '1.0.0',
      description: 'Mobile app testing for Android/iOS',
      status: 'active',
      type: 'continuous',
      triggers: ['alert.app_crash', 'alert.device_offline', 'build.deployed']
    },
    {
      id: 'qa-stb-manager',
      name: 'QA STB Manager',
      version: '1.0.0',
      description: 'Set-top box and TV device validation',
      status: 'active',
      type: 'continuous',
      triggers: ['alert.blackscreen', 'alert.video_playback_failed', 'schedule.stb_regression']
    },
    {
      id: 'monitoring-manager',
      name: 'Monitoring Manager',
      version: '1.0.0',
      description: 'System health monitoring and incident detection',
      status: 'active',
      type: 'continuous',
      triggers: ['schedule.health_check', 'alert.device_offline', 'alert.service_down']
    }
  ];

  const autoStartAgents = async (agentsToStart: AgentDefinition[]) => {
    if (agentsToStart.length === 0) return;
    addLog('info', `Auto-starting ${agentsToStart.length} agents...`, 'system');
    for (const agent of agentsToStart) {
      try {
        await handleStartAgent(agent);
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (err) {
        console.error(`Failed to auto-start ${agent.name}:`, err);
      }
    }
  };

  const handleStartAgent = async (agent: AgentDefinition) => {
    try {
      const response = await fetch(buildServerUrl('/api/runtime/instances/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agent.id, version: agent.version })
      });
      if (!response.ok) throw new Error('Failed to start agent');
      const data = await response.json();
      setAgents(prev => prev.map(a => 
        a.id === agent.id ? { ...a, status: 'running', instanceId: data.instance_id } : a
      ));
      addLog('success', `Agent ${agent.name} started successfully`, agent.id);
    } catch (err) {
      addLog('error', `Failed to start ${agent.name}: ${err}`, agent.id);
    }
  };

  const handleStopAgent = async (agent: AgentDefinition) => {
    if (!agent.instanceId) return;
    try {
      const response = await fetch(buildServerUrl(`/api/runtime/instances/${agent.instanceId}/stop`), {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to stop agent');
      setAgents(prev => prev.map(a => 
        a.id === agent.id ? { ...a, status: 'active', instanceId: undefined } : a
      ));
      addLog('info', `Agent ${agent.name} stopped`, agent.id);
    } catch (err) {
      addLog('error', `Failed to stop ${agent.name}: ${err}`, agent.id);
    }
  };

  const handleToggleAgent = (agent: AgentDefinition) => {
    setAgents(prev => prev.map(a => 
      a.id === agent.id ? { ...a, status: a.status === 'disabled' ? 'active' : 'disabled' } : a
    ));
    addLog('info', `Agent ${agent.name} ${agent.status === 'disabled' ? 'enabled' : 'disabled'}`, agent.id);
  };

  const handleExportAgent = (agent: AgentDefinition) => {
    const yaml = generateYaml(agent);
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${agent.id}-v${agent.version}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
    addLog('info', `Exported ${agent.name} configuration`, agent.id);
  };

  const handleImportAgent = async () => {
    try {
      const response = await fetch(buildServerUrl('/api/agents/import'), {
        method: 'POST',
        headers: { 'Content-Type': 'text/yaml' },
        body: importYaml
      });
      if (!response.ok) throw new Error('Failed to import agent');
      setShowImportDialog(false);
      setImportYaml('');
      loadAgents();
      addLog('success', 'Agent imported successfully', 'system');
    } catch (err) {
      addLog('error', `Import failed: ${err}`, 'system');
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setImportYaml(e.target?.result as string);
        setShowImportDialog(true);
      };
      reader.readAsText(file);
    }
  };

  const handleRunBenchmark = async (agentId: string, version: string = '1.0.0') => {
    setRunningBenchmark(true);
    try {
      // Create run
      const createResponse = await fetch(buildServerUrl('/api/benchmarks/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, version })
      });
      if (!createResponse.ok) throw new Error('Failed to create benchmark run');
      const createData = await createResponse.json();
      
      // Execute run
      const executeResponse = await fetch(buildServerUrl(`/api/benchmarks/run/${createData.run_id}/execute`), {
        method: 'POST'
      });
      if (!executeResponse.ok) throw new Error('Failed to execute benchmark');
      
      addLog('success', `Benchmark completed for ${agentId}`, agentId);
      loadBenchmarkRuns();
      loadLeaderboard();
    } catch (err) {
      addLog('error', `Benchmark failed: ${err}`, agentId);
    } finally {
      setRunningBenchmark(false);
    }
  };

  const handleSubmitFeedback = async () => {
    try {
      const response = await fetch(buildServerUrl('/api/benchmarks/feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: feedbackAgentId,
          version: '1.0.0',
          rating: feedbackRating,
          comment: feedbackComment
        })
      });
      if (!response.ok) throw new Error('Failed to submit feedback');
      setShowFeedbackDialog(false);
      setFeedbackRating(0);
      setFeedbackComment('');
      addLog('success', 'Feedback submitted', feedbackAgentId);
      loadLeaderboard();
    } catch (err) {
      addLog('error', `Feedback failed: ${err}`, feedbackAgentId);
    }
  };

  const addLog = (level: AgentLog['level'], message: string, agentId: string) => {
    setLogs(prev => [{
      timestamp: new Date().toISOString(),
      level,
      message,
      agentId
    }, ...prev].slice(0, 100));
  };

  const generateYaml = (agent: AgentDefinition): string => {
    return `# Agent Configuration: ${agent.name}
# Version: ${agent.version}
---
metadata:
  id: ${agent.id}
  name: ${agent.name}
  version: ${agent.version}
  description: ${agent.description}
goal:
  type: ${agent.type}
triggers:
${agent.triggers.map(t => `  - type: ${t}`).join('\n')}
`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <CheckCircle sx={{ color: '#22c55e', fontSize: 18 }} />;
      case 'error': return <ErrorIcon sx={{ color: '#ef4444', fontSize: 18 }} />;
      case 'disabled': return <PowerSettingsNew sx={{ color: '#6b7280', fontSize: 18 }} />;
      default: return <Schedule sx={{ color: GOLD, fontSize: 18 }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return '#22c55e';
      case 'error': return '#ef4444';
      case 'disabled': return '#6b7280';
      default: return GOLD;
    }
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error': return <ErrorIcon sx={{ color: '#ef4444', fontSize: 14 }} />;
      case 'warning': return <Warning sx={{ color: '#eab308', fontSize: 14 }} />;
      case 'success': return <CheckCircle sx={{ color: '#22c55e', fontSize: 14 }} />;
      default: return <Description sx={{ color: GOLD, fontSize: 14 }} />;
    }
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <EmojiEvents sx={{ color: '#FFD700', fontSize: 20 }} />;
    if (rank === 2) return <EmojiEvents sx={{ color: '#C0C0C0', fontSize: 20 }} />;
    if (rank === 3) return <EmojiEvents sx={{ color: '#CD7F32', fontSize: 20 }} />;
    return <Typography sx={{ color: '#888', fontWeight: 'bold' }}>{rank}</Typography>;
  };

  // =====================================================
  // RENDER
  // =====================================================

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#0d0d0d', color: '#e5e5e5', py: 4 }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600, color: '#F4E4BC', letterSpacing: '-0.02em' }}>
              Agent Management
            </Typography>
            <Typography variant="body2" sx={{ color: '#888', mt: 0.5 }}>
              Configure, benchmark, and compare autonomous agents
            </Typography>
          </Box>
          <IconButton onClick={() => { loadAgents(); loadBenchmarkRuns(); loadLeaderboard(); }} sx={{ color: GOLD }}>
            <Refresh />
          </IconButton>
        </Box>

        {/* Tabs */}
        <Tabs 
          value={activeTab} 
          onChange={(_, v) => setActiveTab(v)}
          sx={{ 
            mb: 3,
            '& .MuiTab-root': { color: '#888', textTransform: 'none', fontSize: '0.95rem' },
            '& .Mui-selected': { color: GOLD },
            '& .MuiTabs-indicator': { bgcolor: GOLD }
          }}
        >
          <Tab label="Agents" icon={<PowerSettingsNew />} iconPosition="start" />
          <Tab label="Benchmarks" icon={<Speed />} iconPosition="start" />
          <Tab label="Leaderboard" icon={<EmojiEvents />} iconPosition="start" />
        </Tabs>

        {/* Error Alert */}
        {error && (
          <Alert severity="warning" sx={{ mb: 3, bgcolor: 'rgba(234, 179, 8, 0.1)', color: '#eab308', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
            {error}
          </Alert>
        )}

        {/* ================= AGENTS TAB ================= */}
        {activeTab === 0 && (
          <>
            {/* Import Button */}
            <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
              <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept=".yaml,.yml" style={{ display: 'none' }} />
              <Button variant="outlined" size="small" startIcon={<CloudUpload />} onClick={() => fileInputRef.current?.click()}
                sx={{ borderColor: GOLD_DARK, color: GOLD, '&:hover': { borderColor: GOLD, bgcolor: 'rgba(212, 175, 55, 0.1)' } }}>
                Import
              </Button>
            </Box>

            {/* Agent Cards */}
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 2, mb: 4 }}>
              {agents.map(agent => (
                <Paper key={agent.id} sx={{
                  p: 2.5, bgcolor: '#1a1a1a', border: selectedAgent?.id === agent.id ? `1px solid ${GOLD}` : '1px solid #2a2a2a',
                  borderRadius: 2, cursor: 'pointer', transition: 'all 0.2s ease',
                  '&:hover': { borderColor: GOLD_DARK, bgcolor: '#1f1f1f' },
                  opacity: agent.status === 'disabled' ? 0.6 : 1
                }} onClick={() => setSelectedAgent(agent)}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      {getStatusIcon(agent.status)}
                      <Box>
                        <Typography sx={{ fontWeight: 600, color: '#fff', fontSize: '0.95rem' }}>{agent.name}</Typography>
                        <Typography sx={{ color: '#666', fontSize: '0.75rem' }}>v{agent.version} • {agent.type}</Typography>
                      </Box>
                    </Box>
                    <Chip label={agent.status} size="small" sx={{ bgcolor: 'transparent', border: `1px solid ${getStatusColor(agent.status)}`, color: getStatusColor(agent.status), fontSize: '0.7rem', height: 22 }} />
                  </Box>
                  <Typography sx={{ color: '#888', fontSize: '0.85rem', mb: 2, lineHeight: 1.5 }}>{agent.description}</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                    {agent.triggers.slice(0, 3).map(trigger => (
                      <Chip key={trigger} label={trigger.split('.')[1] || trigger} size="small" sx={{ bgcolor: '#2a2a2a', color: '#888', fontSize: '0.65rem', height: 20 }} />
                    ))}
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 1, borderTop: '1px solid #2a2a2a' }}>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {agent.status === 'running' ? (
                        <Tooltip title="Stop"><IconButton size="small" onClick={(e) => { e.stopPropagation(); handleStopAgent(agent); }} sx={{ color: '#ef4444' }}><Stop fontSize="small" /></IconButton></Tooltip>
                      ) : agent.status !== 'disabled' && (
                        <Tooltip title="Start"><IconButton size="small" onClick={(e) => { e.stopPropagation(); handleStartAgent(agent); }} sx={{ color: '#22c55e' }}><PlayArrow fontSize="small" /></IconButton></Tooltip>
                      )}
                      <Tooltip title="Export"><IconButton size="small" onClick={(e) => { e.stopPropagation(); handleExportAgent(agent); }} sx={{ color: '#888' }}><CloudDownload fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="Rate"><IconButton size="small" onClick={(e) => { e.stopPropagation(); setFeedbackAgentId(agent.id); setShowFeedbackDialog(true); }} sx={{ color: GOLD }}><Star fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="Benchmark"><IconButton size="small" onClick={(e) => { e.stopPropagation(); handleRunBenchmark(agent.id, agent.version); }} sx={{ color: '#3b82f6' }}><Speed fontSize="small" /></IconButton></Tooltip>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography sx={{ color: '#666', fontSize: '0.7rem' }}>{agent.status === 'disabled' ? 'Disabled' : 'Enabled'}</Typography>
                      <Switch size="small" checked={agent.status !== 'disabled'} onChange={(e) => { e.stopPropagation(); handleToggleAgent(agent); }}
                        sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: GOLD }, '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: GOLD_DARK } }} />
                    </Box>
                  </Box>
                </Paper>
              ))}
            </Box>

            {/* Activity Log */}
            <Paper sx={{ bgcolor: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 2 }}>
              <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', '&:hover': { bgcolor: '#1f1f1f' } }} onClick={() => setExpandedLogs(!expandedLogs)}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Description sx={{ color: GOLD, fontSize: 20 }} />
                  <Typography sx={{ fontWeight: 600, color: '#fff' }}>Activity Log</Typography>
                  <Chip label={logs.length} size="small" sx={{ bgcolor: '#2a2a2a', color: '#888', fontSize: '0.7rem', height: 20 }} />
                </Box>
                {expandedLogs ? <ExpandLess sx={{ color: '#888' }} /> : <ExpandMore sx={{ color: '#888' }} />}
              </Box>
              {expandedLogs && (
                <Box sx={{ maxHeight: 300, overflow: 'auto', borderTop: '1px solid #2a2a2a' }}>
                  {logs.length === 0 ? (
                    <Box sx={{ p: 4, textAlign: 'center' }}><Typography sx={{ color: '#666' }}>No activity yet</Typography></Box>
                  ) : logs.map((log, index) => (
                    <Box key={index} sx={{ p: 1.5, borderBottom: '1px solid #2a2a2a', display: 'flex', alignItems: 'center', gap: 1.5, '&:hover': { bgcolor: '#1f1f1f' } }}>
                      {getLogIcon(log.level)}
                      <Typography sx={{ color: '#666', fontSize: '0.75rem', minWidth: 80 }}>{new Date(log.timestamp).toLocaleTimeString()}</Typography>
                      <Chip label={log.agentId} size="small" sx={{ bgcolor: '#2a2a2a', color: '#888', fontSize: '0.65rem', height: 18 }} />
                      <Typography sx={{ color: '#ccc', fontSize: '0.85rem', flex: 1 }}>{log.message}</Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>
          </>
        )}

        {/* ================= BENCHMARKS TAB ================= */}
        {activeTab === 1 && (
          <>
            <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
              <TextField 
                select 
                size="small" 
                value={selectedBenchmarkAgent} 
                onChange={(e) => setSelectedBenchmarkAgent(e.target.value)}
                SelectProps={{ native: true, displayEmpty: true }}
                sx={{ 
                  minWidth: 220, 
                  '& .MuiOutlinedInput-root': { bgcolor: '#1a1a1a', color: '#fff', '& fieldset': { borderColor: '#3a3a3a' } },
                  '& .MuiSelect-select': { color: selectedBenchmarkAgent ? '#fff' : '#888' }
                }}>
                <option value="" style={{ color: '#888' }}>Select agent...</option>
                {agents.map(a => <option key={a.id} value={a.id} style={{ color: '#fff', backgroundColor: '#1a1a1a' }}>{a.name}</option>)}
              </TextField>
              <Button variant="contained" disabled={!selectedBenchmarkAgent || runningBenchmark} onClick={() => handleRunBenchmark(selectedBenchmarkAgent)}
                sx={{ bgcolor: GOLD, color: '#000', '&:hover': { bgcolor: GOLD_DARK }, '&:disabled': { bgcolor: '#3a3a3a' } }}>
                {runningBenchmark ? 'Running...' : 'Run Benchmark'}
              </Button>
            </Box>

            {runningBenchmark && <LinearProgress sx={{ mb: 2, bgcolor: '#2a2a2a', '& .MuiLinearProgress-bar': { bgcolor: GOLD } }} />}

            <Paper sx={{ bgcolor: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 2, overflow: 'hidden' }}>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#0d0d0d' }}>
                    <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Agent</TableCell>
                    <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Status</TableCell>
                    <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Tests</TableCell>
                    <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Score</TableCell>
                    <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Date</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {benchmarkRuns.length === 0 ? (
                    <TableRow><TableCell colSpan={5} sx={{ textAlign: 'center', color: '#666', py: 4 }}>No benchmark runs yet</TableCell></TableRow>
                  ) : benchmarkRuns.map(run => (
                    <TableRow key={run.id} sx={{ '&:hover': { bgcolor: '#1f1f1f' } }}>
                      <TableCell sx={{ color: '#fff', borderBottom: '1px solid #2a2a2a' }}>
                        <Typography>{run.agent_id}</Typography>
                        <Typography sx={{ fontSize: '0.75rem', color: '#666' }}>v{run.agent_version}</Typography>
                      </TableCell>
                      <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>
                        <Chip label={run.status} size="small" sx={{ bgcolor: run.status === 'completed' ? '#22c55e22' : '#2a2a2a', color: run.status === 'completed' ? '#22c55e' : '#888' }} />
                      </TableCell>
                      <TableCell sx={{ color: '#888', borderBottom: '1px solid #2a2a2a' }}>
                        {run.passed_tests}/{run.total_tests} passed
                      </TableCell>
                      <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>
                        <Typography sx={{ color: GOLD, fontWeight: 'bold' }}>{run.score_percent?.toFixed(1) || '-'}%</Typography>
                      </TableCell>
                      <TableCell sx={{ color: '#666', borderBottom: '1px solid #2a2a2a' }}>
                        {run.created_at ? new Date(run.created_at).toLocaleDateString() : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          </>
        )}

        {/* ================= LEADERBOARD TAB ================= */}
        {activeTab === 2 && (
          <Paper sx={{ bgcolor: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 2, overflow: 'hidden' }}>
            <Box sx={{ p: 2, borderBottom: '1px solid #2a2a2a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography sx={{ fontWeight: 600, color: '#fff' }}>Agent Leaderboard</Typography>
              <Typography sx={{ color: '#666', fontSize: '0.8rem' }}>Score = 40% Benchmark + 30% User Rating + 20% Success Rate + 10% Cost</Typography>
            </Box>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#0d0d0d' }}>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a', width: 60 }}>Rank</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Agent</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Overall</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Benchmark</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>User Rating</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Success Rate</TableCell>
                  <TableCell sx={{ color: GOLD, borderBottom: '1px solid #2a2a2a' }}>Executions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {leaderboard.length === 0 ? (
                  <TableRow><TableCell colSpan={7} sx={{ textAlign: 'center', color: '#666', py: 4 }}>No scores yet. Run benchmarks and submit feedback to populate the leaderboard.</TableCell></TableRow>
                ) : leaderboard.map((entry, idx) => (
                  <TableRow key={`${entry.agent_id}-${entry.agent_version}`} sx={{ '&:hover': { bgcolor: '#1f1f1f' } }}>
                    <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>{getRankIcon(idx + 1)}</TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>
                      <Typography sx={{ color: '#fff', fontWeight: 500 }}>{entry.agent_id}</Typography>
                      <Typography sx={{ fontSize: '0.75rem', color: '#666' }}>v{entry.agent_version}</Typography>
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>
                      <Typography sx={{ color: GOLD, fontWeight: 'bold', fontSize: '1.1rem' }}>{entry.overall_score?.toFixed(1) || 0}</Typography>
                    </TableCell>
                    <TableCell sx={{ color: '#888', borderBottom: '1px solid #2a2a2a' }}>{entry.benchmark_score?.toFixed(1) || 0}</TableCell>
                    <TableCell sx={{ borderBottom: '1px solid #2a2a2a' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Rating value={entry.avg_user_rating || 0} readOnly size="small" sx={{ '& .MuiRating-iconFilled': { color: GOLD } }} />
                        <Typography sx={{ color: '#666', fontSize: '0.8rem' }}>({entry.avg_user_rating?.toFixed(1) || 0})</Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ color: '#888', borderBottom: '1px solid #2a2a2a' }}>{entry.success_rate_score?.toFixed(0) || 0}%</TableCell>
                    <TableCell sx={{ color: '#666', borderBottom: '1px solid #2a2a2a' }}>{entry.total_executions || 0}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        )}

        {/* Import Dialog */}
        <Dialog open={showImportDialog} onClose={() => setShowImportDialog(false)} maxWidth="md" fullWidth PaperProps={{ sx: { bgcolor: '#1a1a1a', color: '#e5e5e5' } }}>
          <DialogTitle sx={{ borderBottom: '1px solid #2a2a2a' }}>Import Agent Configuration</DialogTitle>
          <DialogContent sx={{ mt: 2 }}>
            <TextField fullWidth multiline rows={15} value={importYaml} onChange={(e) => setImportYaml(e.target.value)} placeholder="Paste YAML configuration here..."
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: '#0d0d0d', color: '#e5e5e5', fontFamily: 'monospace', fontSize: '0.85rem', '& fieldset': { borderColor: '#2a2a2a' }, '&:hover fieldset': { borderColor: GOLD_DARK }, '&.Mui-focused fieldset': { borderColor: GOLD } } }} />
          </DialogContent>
          <DialogActions sx={{ borderTop: '1px solid #2a2a2a', p: 2 }}>
            <Button onClick={() => setShowImportDialog(false)} sx={{ color: '#888' }}>Cancel</Button>
            <Button onClick={handleImportAgent} variant="contained" sx={{ bgcolor: GOLD, color: '#000', '&:hover': { bgcolor: GOLD_DARK } }}>Import Agent</Button>
          </DialogActions>
        </Dialog>

        {/* Feedback Dialog */}
        <Dialog open={showFeedbackDialog} onClose={() => setShowFeedbackDialog(false)} PaperProps={{ sx: { bgcolor: '#1a1a1a', color: '#e5e5e5', minWidth: 400 } }}>
          <DialogTitle sx={{ borderBottom: '1px solid #2a2a2a' }}>Rate Agent: {feedbackAgentId}</DialogTitle>
          <DialogContent sx={{ mt: 2, textAlign: 'center' }}>
            <Typography sx={{ mb: 2, color: '#888' }}>How was your experience?</Typography>
            <Rating value={feedbackRating} onChange={(_, v) => setFeedbackRating(v || 0)} size="large" sx={{ '& .MuiRating-iconFilled': { color: GOLD }, mb: 2 }} />
            <TextField fullWidth multiline rows={3} value={feedbackComment} onChange={(e) => setFeedbackComment(e.target.value)} placeholder="Optional feedback..."
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: '#0d0d0d', color: '#e5e5e5', '& fieldset': { borderColor: '#2a2a2a' } } }} />
          </DialogContent>
          <DialogActions sx={{ borderTop: '1px solid #2a2a2a', p: 2 }}>
            <Button onClick={() => setShowFeedbackDialog(false)} sx={{ color: '#888' }}>Skip</Button>
            <Button onClick={handleSubmitFeedback} variant="contained" disabled={feedbackRating === 0} sx={{ bgcolor: GOLD, color: '#000', '&:hover': { bgcolor: GOLD_DARK } }}>Submit</Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
};

export default AgentDashboard;
