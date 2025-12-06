/**
 * Agent Dashboard Page
 * 
 * Main dashboard for managing and monitoring autonomous agents
 */

import React, { useState } from 'react';
import { Box, Container, Grid, Paper, Typography, Button, Divider } from '@mui/material';
import { AgentSelector } from '../components/agent/AgentSelector';
import { AgentStatus } from '../components/agent/AgentStatus';
import { PlayCircle, Settings, TrendingUp, Activity } from 'lucide-react';

export const AgentDashboard: React.FC = () => {
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [showStartDialog, setShowStartDialog] = useState(false);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Activity className="w-8 h-8" />
          Agent Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage and monitor autonomous agents in real-time
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, bgcolor: 'primary.main', color: 'white' }}>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>--</Typography>
            <Typography variant="body2">Active Agents</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, bgcolor: 'success.main', color: 'white' }}>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>--</Typography>
            <Typography variant="body2">Tasks Completed (24h)</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, bgcolor: 'warning.main', color: 'white' }}>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>--</Typography>
            <Typography variant="body2">Avg. Response Time</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, bgcolor: 'info.main', color: 'white' }}>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>$--</Typography>
            <Typography variant="body2">Cost (30d)</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Left Panel - Agent Selector */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Agent Instances</Typography>
              <Button
                variant="contained"
                size="small"
                startIcon={<PlayCircle className="w-4 h-4" />}
                onClick={() => setShowStartDialog(true)}
              >
                Start Agent
              </Button>
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            <AgentSelector
              onAgentSelect={setSelectedInstanceId}
              selectedInstanceId={selectedInstanceId}
            />
          </Paper>
        </Grid>

        {/* Right Panel - Agent Status */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Agent Details</Typography>
              {selectedInstanceId && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Settings className="w-4 h-4" />}
                >
                  Configure
                </Button>
              )}
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            <AgentStatus instanceId={selectedInstanceId} />
          </Paper>
        </Grid>
      </Grid>

      {/* Start Agent Dialog - Placeholder */}
      {showStartDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Start New Agent</h3>
            <p className="text-sm text-gray-600 mb-4">
              Select an agent configuration to start:
            </p>
            
            <div className="space-y-2 mb-4">
              <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer">
                <p className="font-medium">QA Web Manager</p>
                <p className="text-xs text-gray-500">Web testing and monitoring</p>
              </div>
              <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer">
                <p className="font-medium">QA Mobile Manager</p>
                <p className="text-xs text-gray-500">Mobile app testing</p>
              </div>
              <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer">
                <p className="font-medium">QA STB Manager</p>
                <p className="text-xs text-gray-500">Set-top box validation</p>
              </div>
              <div className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer">
                <p className="font-medium">Monitoring Manager</p>
                <p className="text-xs text-gray-500">System health monitoring</p>
              </div>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => setShowStartDialog(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert('Agent start functionality coming soon!');
                  setShowStartDialog(false);
                }}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Start Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </Container>
  );
};

export default AgentDashboard;

