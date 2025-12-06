/**
 * Global Agent Badges
 * 
 * Floating badge system that displays all active agent tasks.
 * - Manual triggers stack on TOP
 * - Auto triggers stack BELOW
 * - Badges show agent nickname + task status
 * - Click to expand task details
 */

import React, { useState } from 'react';
import { Box, Paper, Typography, IconButton, Collapse, Tabs, Tab, Chip, LinearProgress, Fade, Tooltip } from '@mui/material';
import { Close, ExpandLess, ExpandMore, ThumbUp, ThumbDown, ArrowBack, CheckCircle, Error as ErrorIcon, Schedule, OpenInNew } from '@mui/icons-material';
import { useAgentActivity, AGENT_METADATA, AgentTask } from '../../contexts/AgentActivityContext';
import { useNavigate } from 'react-router-dom';

// Styles
const BADGE_WIDTH = 260;
const COLORS = {
  bg: '#1a1a1a',
  bgHover: '#242424',
  border: 'rgba(212, 175, 55, 0.4)', // Gold tint border by default
  borderActive: '#d4af37',
  text: '#f0f0f0',
  textMuted: '#888',
  accent: '#d4af37',
  success: '#22c55e',
  error: '#ef4444',
};

interface AgentBadgeProps {
  agentId: string;
  tasks: AgentTask[];
  isExpanded: boolean;
  onToggle: () => void;
  onDismiss: (taskId: string) => void;
  onFeedback: (taskId: string, rating: number, comment?: string) => void;
}

const AgentBadge: React.FC<AgentBadgeProps> = ({ 
  agentId, 
  tasks, 
  isExpanded, 
  onToggle, 
  onDismiss,
  onFeedback 
}) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  
  const meta = AGENT_METADATA[agentId] || { name: agentId, nickname: agentId, icon: '🤖' };
  const runningTasks = tasks.filter(t => t.status === 'running');
  const completedTasks = tasks.filter(t => t.status === 'completed');
  const failedTasks = tasks.filter(t => t.status === 'failed');
  
  const currentTask = tasks[activeTab] || tasks[0];
  const isComplete = currentTask?.status === 'completed';
  const isFailed = currentTask?.status === 'failed';
  const isManual = currentTask?.triggerType === 'manual';

  const getStatusIcon = () => {
    if (failedTasks.length > 0) return <ErrorIcon sx={{ fontSize: 14, color: COLORS.error }} />;
    if (completedTasks.length > 0 && runningTasks.length === 0) return <CheckCircle sx={{ fontSize: 14, color: COLORS.success }} />;
    return <Schedule sx={{ fontSize: 14, color: COLORS.accent, animation: 'pulse 1.5s infinite' }} />;
  };

  const getProgressDots = () => {
    const total = currentTask?.steps?.length || 4;
    const done = currentTask?.steps?.filter(s => s.status === 'done').length || 0;
    return (
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        {Array.from({ length: Math.min(total, 5) }).map((_, i) => (
          <Box 
            key={i} 
            sx={{ 
              width: 6, 
              height: 6, 
              borderRadius: '50%', 
              bgcolor: i < done ? COLORS.accent : '#444',
              transition: 'background-color 0.3s',
            }} 
          />
        ))}
      </Box>
    );
  };

  const handleBack = () => {
    if (currentTask?.redirectedFrom) {
      navigate(currentTask.redirectedFrom);
    } else {
      navigate('/ai-agent');
    }
  };

  return (
    <Paper
      elevation={8}
      sx={{
        width: BADGE_WIDTH,
        bgcolor: COLORS.bg,
        border: `1px solid ${isExpanded ? COLORS.borderActive : COLORS.border}`,
        borderRadius: 2,
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        boxShadow: isExpanded 
          ? '0 4px 24px rgba(212, 175, 55, 0.25)' 
          : '0 4px 20px rgba(0, 0, 0, 0.4)',
        '&:hover': { 
          borderColor: COLORS.borderActive,
          boxShadow: '0 4px 24px rgba(212, 175, 55, 0.2)',
        },
      }}
    >
      {/* Header - Always visible */}
      <Box
        onClick={onToggle}
        sx={{
          py: 0.75,
          px: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          cursor: 'pointer',
          '&:hover': { bgcolor: COLORS.bgHover },
        }}
      >
        <Typography sx={{ fontSize: 16 }}>{meta.icon}</Typography>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Typography sx={{ fontWeight: 600, color: COLORS.text, fontSize: '0.85rem' }}>
              {meta.nickname}
            </Typography>
            {tasks.length > 1 && (
              <Chip label={tasks.length} size="small" sx={{ height: 16, fontSize: '0.65rem', bgcolor: '#333', color: COLORS.textMuted }} />
            )}
            {getStatusIcon()}
          </Box>
          <Typography sx={{ color: COLORS.textMuted, fontSize: '0.7rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {currentTask?.prompt || 'Processing...'}
          </Typography>
        </Box>
        {!isExpanded && runningTasks.length > 0 && getProgressDots()}
        <IconButton size="small" sx={{ color: COLORS.textMuted, p: 0.25 }}>
          {isExpanded ? <ExpandMore sx={{ fontSize: 18 }} /> : <ExpandLess sx={{ fontSize: 18 }} />}
        </IconButton>
      </Box>

      {/* Progress bar for running tasks */}
      {runningTasks.length > 0 && !isExpanded && (
        <LinearProgress 
          variant="indeterminate" 
          sx={{ 
            height: 2, 
            bgcolor: '#333', 
            '& .MuiLinearProgress-bar': { bgcolor: COLORS.accent } 
          }} 
        />
      )}

      {/* Expanded Content */}
      <Collapse in={isExpanded}>
        <Box sx={{ borderTop: `1px solid ${COLORS.border}` }}>
          {/* Tabs for multiple tasks */}
          {tasks.length > 1 && (
            <Tabs 
              value={activeTab} 
              onChange={(_, v) => setActiveTab(v)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{ 
                minHeight: 24,
                '& .MuiTab-root': { minHeight: 24, py: 0, px: 1, fontSize: '0.7rem', color: COLORS.textMuted, minWidth: 'auto' },
                '& .Mui-selected': { color: COLORS.accent },
                '& .MuiTabs-indicator': { bgcolor: COLORS.accent, height: 1 },
              }}
            >
              {tasks.map((t, i) => (
                <Tab key={t.id} label={`#${i + 1}`} />
              ))}
            </Tabs>
          )}

          {/* Task Details */}
          {currentTask && (
            <Box sx={{ px: 1, py: 0.75 }}>
              {/* Steps - filter out generic "Starting"/"Processing" labels */}
              {(() => {
                const filteredSteps = currentTask.steps
                  .filter(s => !['starting', 'processing'].includes(s.label.toLowerCase()))
                  .slice(-4);
                return filteredSteps.length > 0 && (
                  <Box sx={{ mb: 0.75 }}>
                    {filteredSteps.map((step) => (
                      <Box key={step.id} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
                        <Box sx={{ 
                          width: 5, 
                          height: 5, 
                          borderRadius: '50%', 
                          bgcolor: step.status === 'done' ? COLORS.success : step.status === 'error' ? COLORS.error : step.status === 'active' ? COLORS.accent : '#444',
                          animation: step.status === 'active' ? 'pulse 1s infinite' : 'none',
                          flexShrink: 0,
                        }} />
                        <Typography sx={{ fontSize: '0.7rem', color: step.status === 'active' ? COLORS.text : COLORS.textMuted }}>
                          {step.label}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                );
              })()}

              {/* Summary (for completed tasks) */}
              {isComplete && currentTask.summary && (
                <Box sx={{ px: 0.75, py: 0.5, mb: 0.75, bgcolor: '#242424', borderRadius: 1, border: `1px solid ${COLORS.border}` }}>
                  <Typography sx={{ fontWeight: 600, fontSize: '0.75rem', color: COLORS.text, mb: 0.25 }}>
                    {currentTask.summary.title}
                  </Typography>
                  {Object.entries(currentTask.summary.data).map(([key, value]) => (
                    <Typography key={key} sx={{ fontSize: '0.7rem', color: COLORS.textMuted, lineHeight: 1.3 }}>
                      • {key}: <span style={{ color: COLORS.text }}>{String(value)}</span>
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Response preview */}
              {isComplete && currentTask.response && !currentTask.summary && (
                <Typography sx={{ fontSize: '0.7rem', color: COLORS.textMuted, mb: 0.75, lineHeight: 1.3 }}>
                  {currentTask.response.slice(0, 120)}
                  {currentTask.response.length > 120 && '...'}
                </Typography>
              )}

              {/* Error message */}
              {isFailed && currentTask.error && (
                <Box sx={{ px: 0.75, py: 0.5, mb: 0.75, bgcolor: 'rgba(239, 68, 68, 0.1)', borderRadius: 1, border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                  <Typography sx={{ fontSize: '0.7rem', color: COLORS.error }}>
                    {currentTask.error}
                  </Typography>
                </Box>
              )}

              {/* Feedback + Actions Row */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pt: 0.5, borderTop: `1px solid ${COLORS.border}` }}>
                {isComplete && isManual && !currentTask.feedback && (
                  <>
                    <Typography sx={{ fontSize: '0.7rem', color: COLORS.textMuted }}>Helpful?</Typography>
                    <IconButton size="small" onClick={() => onFeedback(currentTask.id, 5)} sx={{ p: 0.25, color: COLORS.textMuted, '&:hover': { color: COLORS.success } }}>
                      <ThumbUp sx={{ fontSize: 14 }} />
                    </IconButton>
                    <IconButton size="small" onClick={() => onFeedback(currentTask.id, 1)} sx={{ p: 0.25, color: COLORS.textMuted, '&:hover': { color: COLORS.error } }}>
                      <ThumbDown sx={{ fontSize: 14 }} />
                    </IconButton>
                  </>
                )}
                <Box sx={{ flex: 1 }} />
                {/* View full details in AI Agent page */}
                <Tooltip title="View full logs & reasoning">
                  <IconButton 
                    size="small" 
                    onClick={() => navigate('/ai-agent')} 
                    sx={{ p: 0.25, color: COLORS.accent, '&:hover': { color: COLORS.text } }}
                  >
                    <OpenInNew sx={{ fontSize: 14 }} />
                  </IconButton>
                </Tooltip>
                {isComplete && currentTask.redirectedFrom && (
                  <Tooltip title="Back">
                    <IconButton size="small" onClick={handleBack} sx={{ p: 0.25, color: COLORS.textMuted, '&:hover': { color: COLORS.accent } }}>
                      <ArrowBack sx={{ fontSize: 14 }} />
                    </IconButton>
                  </Tooltip>
                )}
                <Tooltip title="Dismiss">
                  <IconButton size="small" onClick={() => onDismiss(currentTask.id)} sx={{ p: 0.25, color: COLORS.textMuted, '&:hover': { color: COLORS.text } }}>
                    <Close sx={{ fontSize: 14 }} />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

// Main Component
export const GlobalAgentBadges: React.FC = () => {
  const { 
    activities, 
    toggleExpanded, 
    dismissTask, 
    submitFeedback,
    getManualTasks,
    getAutoTasks,
  } = useAgentActivity();

  const manualTasks = getManualTasks();
  const autoTasks = getAutoTasks();
  
  // Group by agent
  const manualAgents = new Set(manualTasks.map(t => t.agentId));
  const autoAgents = new Set(autoTasks.filter(t => !manualAgents.has(t.agentId)).map(t => t.agentId));

  if (Object.keys(activities).length === 0) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 1300, // Below modals (1400+) but above most content
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        pointerEvents: 'none',
        '& > *': { pointerEvents: 'auto' },
        // Ensure tooltips appear above
        '& .MuiTooltip-popper': { zIndex: 1500 },
      }}
    >
      {/* Manual tasks on TOP (reverse order so newest is at top) */}
      {Array.from(manualAgents).reverse().map(agentId => {
        const activity = activities[agentId];
        if (!activity) return null;
        const agentManualTasks = activity.tasks.filter(t => t.triggerType === 'manual');
        if (agentManualTasks.length === 0) return null;
        
        return (
          <Fade in key={`manual-${agentId}`}>
            <Box>
              <AgentBadge
                agentId={agentId}
                tasks={agentManualTasks}
                isExpanded={activity.isExpanded}
                onToggle={() => toggleExpanded(agentId)}
                onDismiss={(taskId) => dismissTask(agentId, taskId)}
                onFeedback={(taskId, rating, comment) => submitFeedback(agentId, taskId, rating, comment)}
              />
            </Box>
          </Fade>
        );
      })}

      {/* Auto tasks BELOW */}
      {Array.from(autoAgents).reverse().map(agentId => {
        const activity = activities[agentId];
        if (!activity) return null;
        const agentAutoTasks = activity.tasks.filter(t => t.triggerType !== 'manual');
        if (agentAutoTasks.length === 0) return null;
        
        return (
          <Fade in key={`auto-${agentId}`}>
            <Box>
              <AgentBadge
                agentId={agentId}
                tasks={agentAutoTasks}
                isExpanded={activity.isExpanded}
                onToggle={() => toggleExpanded(agentId)}
                onDismiss={(taskId) => dismissTask(agentId, taskId)}
                onFeedback={(taskId, rating, comment) => submitFeedback(agentId, taskId, rating, comment)}
              />
            </Box>
          </Fade>
        );
      })}

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </Box>
  );
};

export default GlobalAgentBadges;

