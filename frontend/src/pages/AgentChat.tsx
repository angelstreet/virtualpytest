/**
 * AI Agent Chat Page - 3-Column Layout
 * 
 * Layout:
 * - Left: Conversation history sidebar (collapsible)
 * - Center: Main chat area
 * - Right: Device execution panel (collapsible, prepared for future)
 */

import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Button,
  Alert,
  Avatar,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  Fade,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  Tabs,
  Tab,
} from '@mui/material';
import {
  ArrowUpward as SendIcon,
  AutoAwesome as SparkleIcon,
  Terminal as ConsoleIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandIcon,
  Psychology as ThinkingIcon,
  Stop as StopIcon,
  Visibility,
  VisibilityOff,
  ContentCopy as CopyIcon,
  FileDownload as ExportIcon,
  DeleteOutline as ClearIcon,
  AccessTime as TimeIcon,
  DataUsage as TokenIcon,
  Person as PersonIcon,
  Add as AddIcon,
  ChatBubbleOutline as ChatIcon,
  Devices as DevicesIcon,
  ViewSidebar as SidebarIcon,
  Chat as ChatPanelIcon,
  PhoneAndroid as DevicePanelIcon,
  OpenInNew as RedirectIcon,
  ThumbUp,
  ThumbDown,
  Refresh as ReloadIcon,
} from '@mui/icons-material';
import { useSearchParams, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { useAgentChat, type AgentEvent, type BackgroundTask, type BackgroundAgentInfo } from '../hooks/aiagent';
import { useProfile } from '../hooks/auth/useProfile';
import { useAIContext } from '../contexts/AIContext';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { APP_CONFIG } from '../config/constants';
import { AGENT_CHAT_PALETTE as PALETTE, AGENT_CHAT_LAYOUT, AGENT_COLORS } from '../constants/agentChatTheme';
import { getInitials, mergeToolEvents, groupConversationsByTime } from '../utils/agentChatUtils';
import { useToolExecutionTiming } from '../hooks/aiagent/useToolExecutionTiming';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { DeviceControlPanels } from '../components/common/DeviceControlPanels';
import { useDevicePanels } from '../hooks/useDevicePanels';
import { useHostManager } from '../contexts/index';

const { 
  sidebarWidth: SIDEBAR_WIDTH, 
  rightPanelWidth: RIGHT_PANEL_WIDTH,
  maxRecentBackgroundTasks: MAX_RECENT_TASKS 
} = AGENT_CHAT_LAYOUT;

// Colorize PASSED (green) and FAILED (red) in agent responses
// Handles both strings and React node arrays from ReactMarkdown
const colorizeStatus = (node: React.ReactNode): React.ReactNode => {
  // Handle strings - split and colorize PASSED/FAILED
  if (typeof node === 'string') {
    const parts = node.split(/(PASSED|FAILED)/g);
    return parts.map((part, i) => {
      if (part === 'PASSED') return <span key={i} style={{ color: '#22c55e', fontWeight: 600 }}>PASSED</span>;
      if (part === 'FAILED') return <span key={i} style={{ color: '#ef4444', fontWeight: 600 }}>FAILED</span>;
      return part;
    });
  }
  
  // Handle arrays (mixed content from ReactMarkdown like text + links)
  if (Array.isArray(node)) {
    return node.map((child, i) => (
      <React.Fragment key={i}>{colorizeStatus(child)}</React.Fragment>
    ));
  }
  
  // Handle React elements (like <a>, <strong>, etc.) - return as-is
  return node;
};

// --- Components ---

const AgentChat: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  const { profile } = useProfile();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const { allowAutoNavigation, setAllowAutoNavigation } = useAIContext();
  
  // Layout state - each section can be shown/hidden
  const [showHistory, setShowHistory] = useState(true);
  const [showChat, setShowChat] = useState(true);
  const [showDevice, setShowDevice] = useState(false);

  // Device selection state for manual control
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [showDevicePanel, setShowDevicePanel] = useState(false);

  // Get HostManager for device selection
  const { getAllHosts, handleDeviceSelect, handleControlStateChange } = useHostManager();

  // Device control panels - manual control
  const devicePanels = useDevicePanels({
    sessionId: 'agent-chat-session',
    requireTreeId: false, // AgentChat doesn't require tree_id
    autoCleanup: true,
  });

  // Override panel visibility: AgentChat only shows device screen (HDMI/VNC), not remote control
  const agentChatPanelProps = {
    ...devicePanels.panelProps,
    showRemotePanel: false, // ❌ Hide remote control in AgentChat
    showAVPanel: showDevicePanel, // Manual control via show/hide button
    // Custom positioning - position device screen in AgentChat layout
    customPosition: {
      left: '20px', // Account for sidebar width (280px + 10px margin)
      bottom: '22px', // 10px from bottom (no footer in AgentChat)
      // You can also use: right, top
    },
    // Note: Border styling is now default in HDMIStream/VNCStream components
  };
  
  // Sidebar tab state: 'system' for background agents, 'chats' for conversations
  const [sidebarTab, setSidebarTab] = useState<'system' | 'chats'>('chats');
  
  // Handle sidebar tab change - clear bg_ conversation when switching to chats
  const handleSidebarTabChange = (newTab: 'system' | 'chats') => {
    setSidebarTab(newTab);
    // When switching to chats tab, if current conversation is a system one, clear it
    if (newTab === 'chats' && activeConversationId?.startsWith('bg_')) {
      switchConversation(''); // Clear to show empty state
    }
  };
  
  // Track if we've processed URL params
  const [urlParamsProcessed, setUrlParamsProcessed] = useState(false);
  
  // Background agents expanded state (keyed by agent ID)
  const [backgroundExpanded, setBackgroundExpanded] = useState<Record<string, boolean>>({});
  
  // Tool accordion expanded state (keyed by tool event key)
  const [toolExpanded, setToolExpanded] = useState<Record<string, boolean>>({});
  
  // Background agents info (agents with background_queues)
  const [backgroundAgents, setBackgroundAgentsState] = useState<BackgroundAgentInfo[]>([]);
  
// Selected agent - will be set from API (looks for agent with default: true)
// Start empty to avoid MUI out-of-range while agents load
const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  
  // Available agents for dropdown (selectable only) + all agents for nickname lookup
  const [availableAgents, setAvailableAgents] = useState<any[]>([]);
  const [allAgentsMap, setAllAgentsMap] = useState<Record<string, { nickname: string; icon?: string; color?: string }>>({});
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  
  // Load agents from API (ONLY source of truth)
  useEffect(() => {
    const loadAgents = async () => {
      try {
        setAgentsLoading(true);
        setAgentsError(null);
        const response = await fetch(buildServerUrl('/server/agents/'));
        
        if (!response.ok) {
          throw new Error('Failed to load agents from backend');
        }
        
        const data = await response.json();
        
        if (!data.agents?.length) {
          throw new Error('No agents configured in backend');
        }
        
        // Build lookup map for ALL agents (including sub-agents)
        const agentMap: Record<string, { nickname: string; icon?: string; color?: string }> = {};
        data.agents.forEach((a: any) => {
          const id = a.metadata?.id || a.id;
          const nickname = a.metadata?.nickname || a.nickname || a.name || id;
          const icon = a.metadata?.icon || a.icon;
          const color = AGENT_COLORS[id] || PALETTE.accent;
          
          // Index by all possible keys
          agentMap[id] = { nickname, icon, color };
          agentMap[a.name] = { nickname, icon, color };
          agentMap[a.metadata?.id] = { nickname, icon, color };
          agentMap[a.metadata?.name] = { nickname, icon, color };
          if (nickname) agentMap[nickname] = { nickname, icon, color };
        });
        setAllAgentsMap(agentMap);
        
        // Filter to selectable agents only (for dropdown)
        const selectableAgents = data.agents
          .filter((a: any) => a.metadata?.selectable !== false)
          .map((a: any) => {
            const id = a.metadata?.id || a.id;
            return {
              id,
              name: a.metadata?.name || a.name,
              nickname: a.metadata?.nickname || a.nickname || a.name,
              icon: a.metadata?.icon || a.icon || '🤖',
              description: a.metadata?.description || a.description || '',
              color: AGENT_COLORS[id] || PALETTE.accent,
              tips: a.metadata?.suggestions || [], // Load from YAML suggestions
              isDefault: a.metadata?.default === true, // Track default for sorting
            };
          });
        
        if (selectableAgents.length === 0) {
          throw new Error('No selectable agents found');
        }
        
        // Sort agents: default agent first, then others
        selectableAgents.sort((a: any, b: any) => {
          if (a.isDefault) return -1;
          if (b.isDefault) return 1;
          return 0;
        });
        
        setAvailableAgents(selectableAgents);
        
        // Set default agent from YAML (looks for default: true)
        const defaultAgent = selectableAgents.find((a: any) => a.isDefault);
        const defaultId = defaultAgent?.id || selectableAgents[0]?.id || 'assistant';
        setSelectedAgentId(defaultId);
        
        // Identify background agents (those with background_queues config AND enabled)
        const bgAgents: BackgroundAgentInfo[] = data.agents
          .filter((a: any) => a.config?.background_queues?.length > 0 && a.config?.enabled !== false)
          .map((a: any) => ({
            id: a.metadata?.id || a.id,
            nickname: a.metadata?.nickname || a.nickname || a.name,
            queues: a.config.background_queues,
            dryRun: a.config.dry_run || false,
            color: AGENT_COLORS[a.metadata?.id || a.id] || PALETTE.accent,
          }));
        
        if (bgAgents.length > 0) {
          console.log(`[AgentChat] Found ${bgAgents.length} background agents:`, bgAgents.map(a => `${a.id}/${a.nickname}`));
          console.log(`[AgentChat] Background agents full details:`, JSON.stringify(bgAgents, null, 2));
          setBackgroundAgentsState(bgAgents);
          setBackgroundAgents(bgAgents); // Pass to hook
        } else {
          console.warn('[AgentChat] No background agents found - check agent YAML config for background_queues');
        }
        
        setAgentsLoading(false);
      } catch (err) {
        console.error('Failed to load agents:', err);
        setAgentsError(err instanceof Error ? err.message : 'Failed to load agents');
        setAgentsLoading(false);
      }
    };
    loadAgents();
  }, []);
  
  // Agent nickname lookup (from all loaded agents, including sub-agents)
  const getAgentNickname = (agentName: string | undefined) => {
    if (!agentName) return 'Agent';
    // Check loaded agents map first
    const mapped = allAgentsMap[agentName];
    if (mapped?.nickname) return mapped.nickname;
    // Check selectable agents
    const agent = availableAgents.find(a => a.name === agentName || a.id === agentName || a.nickname === agentName);
    return agent?.nickname || agentName;
  };
  
  // Get agent color (from loaded agents or fallback)
  const getAgentColor = (agentName: string | undefined) => {
    if (!agentName) return PALETTE.accent;
    const mapped = allAgentsMap[agentName];
    if (mapped?.color) return mapped.color;
    const agent = availableAgents.find(a => a.name === agentName || a.id === agentName);
    return agent?.color || AGENT_COLORS[agentName] || PALETTE.accent;
  };
  
  // Feedback state - tracks ratings per message ID (shared concept with badge)
  const [messageFeedback, setMessageFeedback] = useState<Record<string, number>>({});
  
  // Confirm dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });
  
  // Submit feedback for a message
  const submitMessageFeedback = async (messageId: string, rating: number, agentId: string, prompt?: string) => {
    // If clicking same rating, remove it (toggle off)
    if (messageFeedback[messageId] === rating) {
      setMessageFeedback(prev => {
        const newState = { ...prev };
        delete newState[messageId];
        return newState;
      });
      return;
    }
    
    // Update local state immediately
    setMessageFeedback(prev => ({ ...prev, [messageId]: rating }));
    
    // Send to backend
    try {
      const response = await fetch(buildServerUrl(`/server/benchmarks/feedback?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId || selectedAgentId,
          rating: rating,
          task_description: prompt,
        }),
      });
      
      if (response.ok) {
        console.log('✅ Chat feedback submitted');
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };
  
  const {
    status,
    session,
    messages,
    input,
    isProcessing,
    currentEvents,
    error,
    apiKeyInput,
    showApiKey,
    isValidating,
    conversations,
    activeConversationId,
    pendingConversationId,
    backgroundTasks,
    setBackgroundAgents,
    setInput,
    setShowApiKey,
    setApiKeyInput,
    setError,
    sendMessage,
    saveApiKey,
    handleApproval,
    stopGeneration,
    clearHistory,
    createNewConversation,
    switchConversation,
    deleteConversation,
    clearBackgroundHistory,
    setAgentId,
    setNavigationContext,
    reloadSkills, // 🆕 NEW: Skills reload for development
  } = useAgentChat();
  
// Sync selected agent with hook once we have a real value
useEffect(() => {
  if (selectedAgentId) {
    setAgentId(selectedAgentId);
  }
}, [selectedAgentId, setAgentId]);
  
  // Sync navigation context with hook (for 2-step workflow)
  useEffect(() => {
    setNavigationContext(allowAutoNavigation, location.pathname);
  }, [allowAutoNavigation, location.pathname, setNavigationContext]);
  
  // Manual device selection handler
  const handleDeviceSelection = (deviceId: string) => {
    setSelectedDevice(deviceId);

    // Find the host and device to update the device panels
    const hosts = getAllHosts();
    for (const host of hosts) {
      const device = host.devices.find(d => d.device_id === deviceId);
      if (device) {
        handleDeviceSelect(host, deviceId);
        break;
      }
    }
  };

  // Handle device panel show/hide
  const handleDevicePanelToggle = () => {
    if (showDevicePanel) {
      // Hide panel
      setShowDevicePanel(false);
      handleControlStateChange(false);
    } else if (selectedDevice) {
      // Show panel for selected device
      setShowDevicePanel(true);
      handleControlStateChange(true);
    }
  };
  
  // Only show processing state if viewing the conversation that's being processed
  const showProcessing = isProcessing && activeConversationId === pendingConversationId;
  
  // Reset scroll state and tool expanded state when conversation changes
  useEffect(() => {
    isUserScrolledUp.current = false;
    lastMessageCount.current = 0;
    lastToolEventCount.current = 0;
    setToolExpanded({}); // Clear tool expanded state for new conversation
  }, [activeConversationId]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUp = useRef(false);
  const lastMessageCount = useRef(0);
  const lastToolEventCount = useRef(0);
  
  // Tool execution timing hook (5-second delay for animations)
  const { shouldShowExecutingAnimation } = useToolExecutionTiming();

  // Track if user has scrolled up manually
  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
    isUserScrolledUp.current = !isAtBottom;
  };

  // Only scroll on actual new content (new messages or completed tool calls)
  useEffect(() => {
    // Count completed tool events (those with results)
    const completedToolCount = currentEvents.filter(e => 
      e.type === 'tool_call' && (e.tool_result !== undefined || e.success !== undefined)
    ).length;
    
    const hasNewMessage = messages.length > lastMessageCount.current;
    const hasNewToolResult = completedToolCount > lastToolEventCount.current;
    
    // Only scroll if user hasn't scrolled up AND there's actual new content
    if (!isUserScrolledUp.current && (hasNewMessage || hasNewToolResult)) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Update tracking refs
    lastMessageCount.current = messages.length;
    lastToolEventCount.current = completedToolCount;
  }, [messages.length, currentEvents]);
  
  // Handle URL params from command bar (prompt & agent)
  useEffect(() => {
    if (urlParamsProcessed) return;
    
    const prompt = searchParams.get('prompt');
    const agentParam = searchParams.get('agent');
    
    if (prompt && status === 'ready') {
      // Set agent if provided
      if (agentParam) {
        setSelectedAgentId(agentParam);
        setAgentId(agentParam);
      }
      
      // Clear URL params
      setSearchParams({}, { replace: true });
      setUrlParamsProcessed(true);
      
      // Set input and trigger send after a brief delay
      setInput(prompt);
      setTimeout(() => {
        sendMessage();
      }, 150);
    }
  }, [searchParams, status, urlParamsProcessed, setSearchParams, setAgentId, setInput, sendMessage]);

  // Handle incoming Slack messages (bidirectional chat)
  useEffect(() => {
    const handleSlackMessage = (event: CustomEvent) => {
      const { content } = event.detail;
      if (content && status === 'ready') {
        console.log('💬 Processing Slack message:', content);
        // Set input and auto-send
        setInput(content);
        setTimeout(() => {
          sendMessage();
        }, 150);
      }
    };

    window.addEventListener('slack-message-received', handleSlackMessage as EventListener);
    return () => {
      window.removeEventListener('slack-message-received', handleSlackMessage as EventListener);
    };
  }, [status, setInput, sendMessage]);
  
  // Group conversations (exclude background agent conversations - they show in their sections)
  const regularConversations = conversations.filter(c => !c.id.startsWith('bg_'));
  const groupedConversations = groupConversationsByTime(regularConversations);

  // --- Renderers ---

  const renderToolActivity = (event: AgentEvent, idx: number) => {
    // Extract error information from multiple possible sources
    const hasError = event.success === false;
    const isExecuting = event.tool_result === undefined && event.success === undefined;
    
    // Use hook to determine if we should show executing animation (5-second delay)
    const toolKey = `${event.tool_name}-${idx}`;
    const showExecutingAnimation = shouldShowExecutingAnimation(toolKey, isExecuting);
    
    let errorMessage = '';
    
    if (hasError) {
      // Try to extract error from various sources
      if (event.tool_result) {
        if (typeof event.tool_result === 'string') {
          errorMessage = event.tool_result;
        } else if (typeof event.tool_result === 'object') {
          errorMessage = (event.tool_result as any).error || JSON.stringify(event.tool_result, null, 2);
        }
      } else if ((event as any).error) {
        // Check if error is directly on the event object
        errorMessage = typeof (event as any).error === 'string' 
          ? (event as any).error 
          : JSON.stringify((event as any).error, null, 2);
      } else if (event.content) {
        // Check if error is in content field
        errorMessage = event.content;
      } else {
        errorMessage = 'Tool failed with no error details';
      }
    }
    
    // Initialize expanded state for this tool if not set
    const shouldAutoExpand = hasError || showExecutingAnimation;
    if (toolExpanded[toolKey] === undefined && shouldAutoExpand) {
      setToolExpanded(prev => ({ ...prev, [toolKey]: true }));
    }
    
    return (
      <Accordion 
        key={`${event.tool_name}-${idx}-${event.success ?? 'pending'}-${event.tool_result ? 'done' : 'waiting'}`} 
        disableGutters 
        elevation={0}
        expanded={toolExpanded[toolKey] ?? shouldAutoExpand}
        onChange={(_, isExpanded) => setToolExpanded(prev => ({ ...prev, [toolKey]: isExpanded }))}
        sx={{ 
          bgcolor: showExecutingAnimation ? 'rgba(212, 165, 116, 0.05)' : 'transparent',
          border: showExecutingAnimation ? '1px solid' : 'none',
          borderColor: showExecutingAnimation ? `${PALETTE.accent}30` : 'transparent',
          '&:before': { display: 'none' },
          mb: 0.5,
          borderRadius: 1,
          transition: 'all 0.3s',
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandIcon sx={{ fontSize: 14, color: hasError ? 'error.main' : showExecutingAnimation ? PALETTE.accent : 'text.disabled' }} />}
          sx={{ 
            minHeight: 24, 
            p: 0, 
            '& .MuiAccordionSummary-content': { my: 0 },
            flexDirection: 'row-reverse',
            gap: 1,
            bgcolor: hasError ? 'rgba(239, 68, 68, 0.08)' : 'transparent',
            borderRadius: 1,
            px: 0.5,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
            <ConsoleIcon sx={{ 
              fontSize: 12, 
              color: hasError ? 'error.main' : showExecutingAnimation ? PALETTE.accent : 'text.disabled',
            }} />
            <Typography variant="caption" sx={{ 
              fontFamily: 'monospace', 
              color: hasError ? 'error.main' : showExecutingAnimation ? PALETTE.accent : 'text.secondary', 
              flex: 1, 
              fontWeight: hasError ? 600 : showExecutingAnimation ? 500 : 400 
            }}>
              {event.tool_name}
            </Typography>
            <Tooltip title="Copy tool name, input, and result">
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  const inputText = event.tool_params 
                    ? JSON.stringify(event.tool_params, null, 2) 
                    : 'No input parameters';
                  const resultText = hasError && errorMessage
                    ? errorMessage
                    : event.tool_result === undefined || event.tool_result === null
                      ? (hasError ? errorMessage || 'No error details provided' : 'Executing...')
                      : typeof event.tool_result === 'string'
                        ? event.tool_result
                        : JSON.stringify(event.tool_result, null, 2);
                  const fullText = `Tool: ${event.tool_name}\n\nInput:\n${inputText}\n\nResult:\n${resultText}`;
                  navigator.clipboard.writeText(fullText);
                }}
                sx={{
                  p: 0.25,
                  opacity: 0.4,
                  '&:hover': { opacity: 1, color: PALETTE.accent },
                }}
              >
                <CopyIcon sx={{ fontSize: 11 }} />
              </IconButton>
            </Tooltip>
            {showExecutingAnimation ? (
              <Box sx={{ 
                width: 12, 
                height: 12, 
                borderRadius: '50%',
                border: '2px solid',
                borderColor: `${PALETTE.accent}40`,
                borderTopColor: PALETTE.accent,
                animation: 'spin 1s linear infinite',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' },
                },
              }} />
            ) : isExecuting ? null : hasError ? 
              <ErrorIcon sx={{ fontSize: 12, color: 'error.main' }} /> : 
              <SuccessIcon sx={{ fontSize: 12, color: 'success.main' }} />
            }
          </Box>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0, pl: 3 }}>
          {hasError && (
            <Alert 
              severity="error" 
              sx={{ 
                mb: 1.5, 
                fontSize: '0.75rem',
                '& .MuiAlert-message': { fontSize: '0.75rem' }
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                Tool Execution Failed
              </Typography>
              <Typography variant="caption" component="pre" sx={{ m: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace' }}>
                {errorMessage}
              </Typography>
            </Alert>
          )}
          
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1.5, 
              bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.50',
              borderColor: hasError 
                ? 'error.main' 
                : showExecutingAnimation 
                  ? `${PALETTE.accent}40`
                  : (isDarkMode ? 'rgba(255,255,255,0.1)' : 'grey.300'),
              borderRadius: 2
            }}
          >
            <Typography variant="caption" display="block" color="text.secondary" gutterBottom>Input</Typography>
            <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary', maxHeight: 150 }}>
              {event.tool_params ? JSON.stringify(event.tool_params, null, 2) : '{}'}
            </Box>
            
            {/* Only show Result section when there's no error (error already shown in alert above) */}
            {!hasError && !isExecuting && (
              <>
                <Typography variant="caption" display="block" color="text.secondary" gutterBottom sx={{ mt: 1.5 }}>
                  Result
                </Typography>
                <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary', maxHeight: 300 }}>
                  {event.tool_result === undefined || event.tool_result === null 
                    ? <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                        No result data
                      </Typography>
                    : typeof event.tool_result === 'string' 
                      ? event.tool_result 
                      : JSON.stringify(event.tool_result, null, 2)
                  }
                </Box>
              </>
            )}
            
            {showExecutingAnimation && (
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1, 
                p: 1.5, 
                mt: 1.5,
                bgcolor: isDarkMode ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.02)',
                borderRadius: 1,
                border: '1px dashed',
                borderColor: PALETTE.accent,
              }}>
                <Box sx={{ 
                  width: 16, 
                  height: 16, 
                  borderRadius: '50%',
                  border: '2px solid',
                  borderColor: `${PALETTE.accent}40`,
                  borderTopColor: PALETTE.accent,
                  animation: 'spin 1s linear infinite',
                  '@keyframes spin': {
                    '0%': { transform: 'rotate(0deg)' },
                    '100%': { transform: 'rotate(360deg)' },
                  },
                }} />
                <Typography variant="caption" sx={{ color: PALETTE.accent, fontWeight: 500 }}>
                  Waiting for response...
                </Typography>
              </Box>
            )}
          </Paper>
        </AccordionDetails>
      </Accordion>
    );
  };

  // --- Generic Background Agent Section ---
  // Renders a section for any agent with background_queues config
  const renderBackgroundAgentSection = (agent: BackgroundAgentInfo) => {
    const agentTasks = backgroundTasks[agent.id] || { inProgress: [], recent: [] };
    
    // Combine in-progress and recent tasks
    const allTasks = [
      ...agentTasks.inProgress.map(t => ({ ...t, isInProgress: true })),
      ...agentTasks.recent.slice(0, MAX_RECENT_TASKS).map(t => ({ ...t, isInProgress: false }))
    ];
    
    const totalActive = allTasks.length;
    const isExpanded = backgroundExpanded[agent.id] || false;
    
    // Get status icon - simplified to tick or cross
    const getTaskIcon = (task: BackgroundTask & { isInProgress?: boolean }) => {
      if (task.isInProgress) return null; // Will show pulsing dot
      
      // Check for failure indicators
      const isFailed = task.classification && [
        'VALID_FAIL', 'BUG', 'SCRIPT_ISSUE', 'SYSTEM_ISSUE'
      ].includes(task.classification);
      
      return isFailed ? '✗' : '✓';
    };
    
    return (
      <Box key={agent.id} sx={{ px: 1, mb: 1 }}>
        {/* Agent Section Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            px: 1.5,
            py: 0.75,
            borderRadius: 1.5,
          }}
        >
          <ExpandIcon 
            onClick={() => setBackgroundExpanded(prev => ({ ...prev, [agent.id]: !isExpanded }))}
            sx={{ 
              fontSize: 16, 
              color: PALETTE.textMuted,
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
              cursor: 'pointer',
              '&:hover': { color: 'text.primary' },
            }} 
          />
          
          <Typography 
            onClick={() => setBackgroundExpanded(prev => ({ ...prev, [agent.id]: !isExpanded }))}
            variant="body2" 
            sx={{ 
              flex: 1,
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              '&:hover': { color: 'text.primary' },
            }}
          >
            # {agent.nickname}
          </Typography>
          
          {totalActive > 0 ? (
            <Chip 
              label={totalActive} 
              size="small"
              sx={{ 
                height: 18,
                minWidth: 18,
                fontSize: '0.7rem',
                bgcolor: agent.color || PALETTE.accent,
                color: '#fff',
                '& .MuiChip-label': { px: 0.75 },
              }} 
            />
          ) : (
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.75rem' }}>
              (0)
            </Typography>
          )}
          
          {/* Clear history button */}
          {totalActive > 0 && (
            <Tooltip title={`Clear ${agent.nickname} history`}>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDialog({
                    open: true,
                    title: 'Clear History',
                    message: `Clear all ${agent.nickname} alert history?`,
                    onConfirm: () => {
                      clearBackgroundHistory(agent.id);
                      setConfirmDialog(prev => ({ ...prev, open: false }));
                    },
                  });
                }}
                sx={{
                  p: 0.25,
                  opacity: 0.4,
                  '&:hover': { opacity: 1, color: 'error.main' },
                }}
              >
                <ClearIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          )}
        </Box>
        
        {/* Expandable Task List */}
        {totalActive > 0 && (
          <Fade in={isExpanded}>
            <Box sx={{ pl: 2, pr: 1, mt: 0.5 }}>
              {allTasks.map(task => {
                const icon = getTaskIcon(task);
                
                return (
                  <Box
                    key={task.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      console.log('[AgentChat] Task clicked:', task.id, task.title, task.conversationId);
                      setSidebarTab('system'); // Ensure we're on system tab when viewing system task
                      switchConversation(task.conversationId);
                    }}
                    sx={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 1,
                      px: 1.5,
                      py: 1,
                      borderRadius: 1.5,
                      cursor: 'pointer',
                      bgcolor: task.conversationId === activeConversationId && sidebarTab === 'system'
                        ? (isDarkMode ? PALETTE.hoverBg : 'grey.200')
                        : 'transparent',
                      '&:hover': {
                        bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100',
                      },
                      transition: 'background-color 0.15s',
                    }}
                  >
                    {task.isInProgress ? (
                      <Box sx={{ 
                        width: 14, 
                        height: 14,
                        mt: 0.3,
                        borderRadius: '50%',
                        bgcolor: agent.color || PALETTE.accent,
                        flexShrink: 0,
                        animation: 'pulse 2s ease-in-out infinite',
                        '@keyframes pulse': {
                          '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                          '50%': { opacity: 0.5, transform: 'scale(0.8)' },
                        },
                      }} />
                    ) : (
                      <Box sx={{ 
                        fontSize: 14, 
                        minWidth: 14, 
                        height: 14,
                        mt: 0.3,
                        textAlign: 'center', 
                        flexShrink: 0,
                        fontWeight: 700,
                        lineHeight: 1,
                        color: icon === '✗' ? '#ef4444' : '#22c55e'
                      }}>
                        {icon}
                      </Box>
                    )}
                    
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      {/* Script name */}
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          color: task.conversationId === activeConversationId ? 'text.primary' : 'text.secondary',
                          fontSize: '0.85rem',
                        }}
                      >
                        {task.subtitle ? `${task.title}-${task.subtitle}` : task.title}
                      </Typography>
                      {/* Date/time - same format as Chats tab */}
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          color: PALETTE.textMuted,
                          fontSize: '0.65rem',
                          opacity: 0.7,
                          mt: -0.25,
                        }}
                      >
                        {(() => {
                          const d = new Date(task.startedAt);
                          const time = `${d.getHours().toString().padStart(2, '0')}h${d.getMinutes().toString().padStart(2, '0')}m${d.getSeconds().toString().padStart(2, '0')}s`;
                          const date = `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear().toString().slice(-2)}`;
                          return `${time} - ${date}`;
                        })()}
                      </Typography>
                    </Box>
                  </Box>
                );
              })}
            </Box>
          </Fade>
        )}
      </Box>
    );
  };

  // Count total tasks for System tab badge
  const totalSystemTasks = backgroundAgents.reduce((sum, agent) => {
    const agentTasks = backgroundTasks[agent.id] || { inProgress: [], recent: [] };
    return sum + agentTasks.inProgress.length + agentTasks.recent.length;
  }, 0);

  // --- Left Sidebar ---
  const renderLeftSidebar = () => (
    <Box
      sx={{
        width: showHistory ? SIDEBAR_WIDTH : 0,
        minWidth: showHistory ? SIDEBAR_WIDTH : 0,
        height: '100%',
        bgcolor: isDarkMode ? PALETTE.sidebarBg : 'grey.50',
        borderRight: showHistory ? '1px solid' : 'none',
        borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'width 0.2s, min-width 0.2s',
      }}
    >
      {showHistory && (
        <>
          {/* New Chat Button */}
          <Box sx={{ p: 1.5, pb: 1 }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                fullWidth
                startIcon={<AddIcon />}
                onClick={() => {
                  createNewConversation();
                  setSidebarTab('chats'); // Switch to chats tab when creating new
                }}
                sx={{
                  flex: 1,
                  justifyContent: 'flex-start',
                  color: 'text.primary',
                  bgcolor: isDarkMode ? PALETTE.inputBg : 'grey.100',
                  border: '1px solid',
                  borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 500,
                  py: 1,
                  '&:hover': {
                    bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.200',
                    borderColor: PALETTE.accent,
                  },
                }}
              >
                New Chat
              </Button>

              {/* Development: Skills Reload Button */}
              {APP_CONFIG.IS_DEVELOPMENT && (
                <Tooltip title="Reload Skills (Dev Only)">
                  <IconButton
                    onClick={async () => {
                      try {
                        await reloadSkills();
                        console.log('✅ Skills reloaded successfully');
                      } catch (error) {
                        console.error('❌ Failed to reload skills:', error);
                      }
                    }}
                    sx={{
                      color: PALETTE.accent,
                      bgcolor: isDarkMode ? PALETTE.inputBg : 'grey.100',
                      border: '1px solid',
                      borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
                      borderRadius: 2,
                      width: 48,
                      height: 48,
                      '&:hover': {
                        bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.200',
                        borderColor: PALETTE.accent,
                      },
                    }}
                  >
                    <ReloadIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>

          {/* Tabs for System vs Chats */}
          {backgroundAgents.length > 0 && (
            <Tabs
              value={sidebarTab}
              onChange={(_, newValue) => handleSidebarTabChange(newValue)}
              sx={{
                minHeight: 36,
                px: 1,
                mb: 0.5,
                '& .MuiTabs-indicator': {
                  backgroundColor: PALETTE.accent,
                  height: 2,
                },
              }}
            >
              <Tab
                value="chats"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <ChatIcon sx={{ fontSize: 14 }} />
                    <span>Chats</span>
                    {regularConversations.length > 0 && (
                      <Chip
                        label={regularConversations.length}
                        size="small"
                        sx={{
                          height: 16,
                          minWidth: 16,
                          fontSize: '0.65rem',
                          bgcolor: sidebarTab === 'chats' ? PALETTE.accent : (isDarkMode ? 'rgba(255,255,255,0.1)' : 'grey.300'),
                          color: sidebarTab === 'chats' ? '#fff' : 'text.secondary',
                          '& .MuiChip-label': { px: 0.5 },
                        }}
                      />
                    )}
                  </Box>
                }
                sx={{
                  minHeight: 36,
                  py: 0.5,
                  px: 1.5,
                  textTransform: 'none',
                  fontSize: '0.8rem',
                  fontWeight: sidebarTab === 'chats' ? 600 : 400,
                  color: sidebarTab === 'chats' ? 'text.primary' : 'text.secondary',
                  minWidth: 0,
                  flex: 1,
                }}
              />
              <Tab
                value="system"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <DevicesIcon sx={{ fontSize: 14 }} />
                    <span>System</span>
                    {totalSystemTasks > 0 && (
                      <Chip
                        label={totalSystemTasks}
                        size="small"
                        sx={{
                          height: 16,
                          minWidth: 16,
                          fontSize: '0.65rem',
                          bgcolor: sidebarTab === 'system' ? PALETTE.accent : (isDarkMode ? 'rgba(255,255,255,0.1)' : 'grey.300'),
                          color: sidebarTab === 'system' ? '#fff' : 'text.secondary',
                          '& .MuiChip-label': { px: 0.5 },
                        }}
                      />
                    )}
                  </Box>
                }
                sx={{
                  minHeight: 36,
                  py: 0.5,
                  px: 1.5,
                  textTransform: 'none',
                  fontSize: '0.8rem',
                  fontWeight: sidebarTab === 'system' ? 600 : 400,
                  color: sidebarTab === 'system' ? 'text.primary' : 'text.secondary',
                  minWidth: 0,
                  flex: 1,
                }}
              />
            </Tabs>
          )}

          {/* Tab Content */}
          <Box
            sx={{
              flex: 1,
              overflowY: 'auto',
              overflowX: 'hidden',
              px: 1,
              pb: 2,
              scrollbarWidth: 'thin',
              scrollbarColor: isDarkMode ? `${PALETTE.borderColor} transparent` : '#c1c1c1 transparent',
              '&::-webkit-scrollbar': { width: 4 },
              '&::-webkit-scrollbar-track': { background: 'transparent' },
              '&::-webkit-scrollbar-thumb': {
                background: isDarkMode ? PALETTE.borderColor : '#c1c1c1',
                borderRadius: 2,
              },
            }}
          >
            {/* System Tab Content */}
            {sidebarTab === 'system' && backgroundAgents.length > 0 && (
              <Box sx={{ pt: 1 }}>
                {backgroundAgents.map(agent => renderBackgroundAgentSection(agent))}
              </Box>
            )}

            {/* Chats Tab Content */}
            {(sidebarTab === 'chats' || backgroundAgents.length === 0) && (
              <>
                {groupedConversations.map((group) => (
                  <Box key={group.label} sx={{ mb: 1 }}>
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'block',
                        px: 1,
                        pt: 0.5,
                        pb: 0,
                        color: PALETTE.textMuted,
                        fontWeight: 600,
                        fontSize: '0.7rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}
                    >
                      {group.label}
                    </Typography>
                    {group.items.map((conv) => (
                      <Box
                        key={conv.id}
                        onClick={() => {
                          setSidebarTab('chats'); // Ensure we stay on chats tab
                          switchConversation(conv.id);
                        }}
                        sx={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 1,
                          px: 1.5,
                          py: 1,
                          borderRadius: 1.5,
                          cursor: 'pointer',
                          bgcolor: conv.id === activeConversationId && sidebarTab === 'chats'
                            ? (isDarkMode ? PALETTE.hoverBg : 'grey.200')
                            : 'transparent',
                          '&:hover': {
                            bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100',
                          },
                          transition: 'background-color 0.15s',
                        }}
                      >
                        <ChatIcon sx={{ fontSize: 14, color: PALETTE.textMuted, flexShrink: 0, mt: 0.3 }} />
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              color: conv.id === activeConversationId ? 'text.primary' : 'text.secondary',
                              fontSize: '0.85rem',
                            }}
                          >
                            {conv.title}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              display: 'block',
                              color: PALETTE.textMuted,
                              fontSize: '0.65rem',
                              opacity: 0.7,
                              mt: -0.25,
                            }}
                          >
                            {(() => {
                              const d = new Date(conv.createdAt);
                              const time = `${d.getHours().toString().padStart(2, '0')}h${d.getMinutes().toString().padStart(2, '0')}m${d.getSeconds().toString().padStart(2, '0')}s`;
                              const date = `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear().toString().slice(-2)}`;
                              return `${time} - ${date}`;
                            })()}
                          </Typography>
                        </Box>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteConversation(conv.id);
                            }}
                            sx={{
                              p: 0.25,
                              opacity: 0.5,
                              '&:hover': { opacity: 1, color: 'error.main' },
                            }}
                          >
                            <ClearIcon sx={{ fontSize: 14 }} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    ))}
                  </Box>
                ))}

                {regularConversations.length === 0 && (
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      textAlign: 'center',
                      color: PALETTE.textMuted,
                      py: 4,
                    }}
                  >
                    No conversations yet
                  </Typography>
                )}
              </>
            )}
          </Box>
        </>
      )}
    </Box>
  );

  // --- Right Panel (Device Execution - Placeholder) ---
  const renderRightPanel = () => (
    <Box
      sx={{
        width: showDevice ? RIGHT_PANEL_WIDTH : 0,
        minWidth: showDevice ? RIGHT_PANEL_WIDTH : 0,
        height: '100%',
        bgcolor: isDarkMode ? PALETTE.sidebarBg : 'grey.50',
        borderLeft: showDevice ? '1px solid' : 'none',
        borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'width 0.2s, min-width 0.2s',
      }}
    >
      {showDevice && (
        <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <DevicesIcon sx={{ fontSize: 18, color: PALETTE.accent }} />
            <Typography variant="subtitle2" fontWeight={600}>
              Device Execution
            </Typography>
          </Box>
          
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 2,
              border: '1px dashed',
              borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
            }}
          >
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', px: 2 }}>
              Device execution panel
              <br />
              <Typography variant="caption" color="text.disabled">
                Coming soon
              </Typography>
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );

  // --- Empty State / Focus Mode ---
  const renderEmptyState = () => (
    <Box sx={{ 
      flex: 1,
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      p: 4,
    }}>
      <Fade in timeout={800}>
        <Box sx={{ textAlign: 'center', maxWidth: 640, width: '100%' }}>
          <Box sx={{ 
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 64,
            height: 64,
            borderRadius: '50%',
            bgcolor: `${PALETTE.accent}15`,
            mb: 3
          }}>
            <SparkleIcon sx={{ fontSize: 32, color: PALETTE.accent }} />
          </Box>
          
          <Typography 
            variant="h5" 
            sx={{ fontWeight: 500, mb: 1, color: 'text.primary', letterSpacing: '-0.01em' }}
          >
            AI Agent
          </Typography>
          <Typography variant="body2" sx={{ mb: 4, color: 'text.secondary', maxWidth: 360, mx: 'auto' }}>
            Automate tests, run regressions, and analyze failures.
          </Typography>
          
          {/* Input Card */}
          <Paper
            elevation={0}
            sx={{
              p: 1,
              display: 'flex',
              alignItems: 'center',
              bgcolor: isDarkMode ? PALETTE.inputBg : '#fff',
              border: '1px solid',
              borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
              borderRadius: 3,
              boxShadow: isDarkMode ? PALETTE.cardShadow : '0 2px 8px rgba(0,0,0,0.08)',
              transition: 'all 0.2s',
              '&:hover': { borderColor: PALETTE.accent },
              '&:focus-within': { borderColor: PALETTE.accent },
            }}
          >
            <TextField
              autoFocus
              fullWidth
              placeholder="How can I help you?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              sx={{ ml: 1.5, flex: 1 }}
              variant="standard"
              autoComplete="off"
              InputProps={{ disableUnderline: true, sx: { fontSize: '0.95rem' } }}
            />
            <IconButton 
              onClick={sendMessage}
              disabled={!input.trim()}
              sx={{ 
                m: 0.5, width: 36, height: 36,
                bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                color: input.trim() ? '#fff' : 'text.disabled',
                '&:hover': { bgcolor: input.trim() ? PALETTE.accentHover : 'transparent' },
              }}
            >
              <SendIcon fontSize="small" />
            </IconButton>
          </Paper>
          
          {/* Suggestion Chips - Loaded from YAML metadata.suggestions */}
          {!agentsLoading && availableAgents.length > 0 && availableAgents.find(a => a.id === selectedAgentId)?.tips?.length > 0 && (
            <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
              {availableAgents.find(a => a.id === selectedAgentId)?.tips.map((suggestion: string) => (
                <Chip 
                  key={suggestion} 
                  label={suggestion} 
                  onClick={() => setInput(suggestion)}
                  size="small"
                  sx={{ 
                    bgcolor: isDarkMode ? PALETTE.surface : 'grey.100', 
                    border: '1px solid', 
                    borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
                    borderRadius: 2,
                    fontSize: '0.8rem',
                    '&:hover': { borderColor: PALETTE.accent, cursor: 'pointer' },
                  }} 
                />
              ))}
            </Box>
          )}
        </Box>
      </Fade>
    </Box>
  );

  // --- Main Chat Content ---
  const renderChatContent = () => (
    <>
      {/* Chat Stream */}
      <Box 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        sx={{ 
          flex: 1, 
          overflowY: 'auto',
          overflowX: 'hidden',
          px: 2,
          py: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          scrollbarWidth: 'thin',
          scrollbarColor: isDarkMode ? `${PALETTE.borderColor} transparent` : '#c1c1c1 transparent',
          '&::-webkit-scrollbar': { width: 6 },
          '&::-webkit-scrollbar-track': { background: 'transparent' },
          '&::-webkit-scrollbar-thumb': {
            background: isDarkMode ? PALETTE.borderColor : '#c1c1c1',
            borderRadius: 3,
          },
        }}>
        <Box sx={{ width: '100%' }}>
          
          {agentsLoading && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body2" color="text.secondary">
                Loading agents...
              </Typography>
            </Box>
          )}
          
          {agentsError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Failed to load agents</Typography>
              <Typography variant="caption">{agentsError}</Typography>
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                Make sure the backend is running and agents are configured in YAML templates.
              </Typography>
            </Alert>
          )}
          
          {status === 'needs_key' && (
            <Box sx={{ textAlign: 'center', mb: 2 }}>
              <Alert severity="info" sx={{ mb: 2 }}>Please configure your Anthropic API Key.</Alert>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                <TextField 
                  size="small" 
                  placeholder="sk-ant-..." 
                  value={apiKeyInput} 
                  onChange={(e) => setApiKeyInput(e.target.value)} 
                  type={showApiKey ? "text" : "password"}
                  autoComplete="off"
                />
                <Button variant="contained" onClick={() => saveApiKey()} disabled={isValidating}>Save</Button>
                <IconButton onClick={() => setShowApiKey(!showApiKey)} size="small">
                  {showApiKey ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </Box>
              {error && <Typography color="error" variant="caption">{error}</Typography>}
            </Box>
          )}

          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            const agentColor = getAgentColor(msg.agent);
            
            return (
              <Box 
                key={msg.id} 
                sx={{ 
                  display: 'flex', 
                  gap: 1.5,
                  flexDirection: isUser ? 'row-reverse' : 'row',
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '100%',
                  mb: 1
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 0.5 }}>
                  {isUser ? (
                    <Avatar 
                      src={profile?.avatar_url || undefined}
                      alt={profile?.full_name || 'You'}
                      sx={{ width: 28, height: 28, fontSize: 12, bgcolor: isDarkMode ? '#5c6bc0' : '#3f51b5', fontWeight: 600 }}
                    >
                      {!profile?.avatar_url && (profile?.full_name ? getInitials(profile.full_name) : <PersonIcon sx={{ fontSize: 16 }} />)}
                    </Avatar>
                  ) : (
                    <Avatar sx={{ width: 28, height: 28, fontSize: 12, bgcolor: agentColor, fontWeight: 600 }}>
                      {getInitials(msg.agent || 'QA')}
                    </Avatar>
                  )}
                </Box>

                <Paper 
                  elevation={0}
                  sx={{ 
                    p: 1.5,
                    flex: 1,
                    bgcolor: isDarkMode  
                      ? (isUser ? PALETTE.userBubble : PALETTE.agentBubble)
                      : (isUser ? 'grey.100' : 'grey.50'),
                    border: isUser 
                      ? `1px solid ${isDarkMode ? `${PALETTE.accent}50` : `${PALETTE.accent}40`}` 
                      : `1px solid ${isDarkMode ? PALETTE.agentBorder : 'grey.200'}`,
                    borderRadius: 2.5,
                    borderTopRightRadius: isUser ? 4 : 10,
                    borderTopLeftRadius: !isUser ? 4 : 10,
                    minWidth: 0,
                  }}
                >
                  {!isUser && (() => {
                    // Extract all unique agents from events
                    const agentChain = msg.events
                      ? [...new Set(msg.events.map(e => e.agent).filter(Boolean))]
                      : [];
                    const mainAgent = msg.agent || agentChain[0];
                    const delegatedAgents = agentChain.filter(a => a !== mainAgent && a !== 'System');

                    // Extract skill name from skill_loaded event
                    const skillLoadedEvent = msg.events?.find(e => e.type === 'skill_loaded');
                    const skillName = skillLoadedEvent?.content || null;

                      return (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                          <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ fontSize: '0.8rem' }}>
                      {getAgentNickname(msg.agent)}
                    </Typography>
                          {skillName && (
                            <Chip
                              label={skillName}
                              size="small"
                              variant="outlined"
                              sx={{
                                height: 18,
                                fontSize: '0.65rem',
                                borderColor: PALETTE.accent,
                                color: PALETTE.accent,
                                fontWeight: 600,
                                '& .MuiChip-label': { px: 0.75 }
                              }}
                            />
                          )}
                        {delegatedAgents.length > 0 && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Typography variant="caption" sx={{ color: 'text.disabled' }}>→</Typography>
                            {delegatedAgents.map((agent) => (
                              <Chip
                                key={agent}
                                label={agent}
                                size="small"
                                sx={{
                                  height: 18,
                                  fontSize: '0.65rem',
                                  bgcolor: getAgentColor(agent),
                                  color: '#fff',
                                  '& .MuiChip-label': { px: 0.75 }
                                }}
                              />
                            ))}
                          </Box>
                        )}
                      </Box>
                    );
                  })()}

                  {!isUser && msg.events && msg.events.filter(e => e.type === 'tool_call').length > 0 && (
                    <Box sx={{ mb: 1, p: 1, bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.100', borderRadius: 1.5 }}>
                      {mergeToolEvents(msg.events).map(renderToolActivity)}
                    </Box>
                  )}
                  
                  {!isUser && msg.events ? (
                    <Box>
                      {/* Show thinking/reasoning accordion only if meaningful content exists */}
                      {(() => {
                        // Filter out internal routing/analysis messages that aren't real reasoning
                        const internalPatterns = [
                          /^Analyzing\.{0,3}\s*\[[\w-]+\]$/i,  // "Analyzing... [router]", "Analyzing... [run-script]"
                          /^Analyzing your request\.{0,3}$/i,  // "Analyzing your request..."
                          /^Processing\.{0,3}$/i,              // "Processing..."
                          /^Routing\.{0,3}$/i,                 // "Routing..."
                          /^Delegating\.{0,3}$/i,              // "Delegating..."
                        ];
                        
                        const thinkingContent = msg.events
                          .filter(e => e.type === 'thinking')
                          .map(e => e.content)
                          .filter(content => {
                            // Filter out internal routing messages
                            const trimmed = content?.trim() || '';
                            return !internalPatterns.some(pattern => pattern.test(trimmed));
                          })
                          .join('\n\n')
                          .replace(/\n{3,}/g, '\n\n')
                          .trim();
                        
                        // Only show if there's meaningful reasoning content
                        const hasRealThinking = thinkingContent.length > 50;
                        
                        if (!hasRealThinking) return null;
                        
                        return (
                          <Accordion elevation={0} disableGutters sx={{ bgcolor: 'transparent', '&:before': { display: 'none' }, mb: 1 }}>
                            <AccordionSummary 
                              expandIcon={<ExpandIcon sx={{ color: 'text.secondary' }} />}
                              sx={{ minHeight: 'auto', p: 0, '& .MuiAccordionSummary-content': { m: 0, alignItems: 'center', gap: 1 } }}
                            >
                              <ThinkingIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', fontSize: '0.85rem' }}>
                                View Reasoning
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ p: 0, pt: 1 }}>
                              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.5, color: 'text.secondary', fontSize: '0.85rem' }}>
                                {thinkingContent}
                              </Typography>
                            </AccordionDetails>
                          </Accordion>
                        );
                      })()}
                      {/* Errors now shown inline with their tool calls via mergeToolEvents */}
                      {/* Show actual response - message/result events */}
                      {msg.events.filter(e => e.type === 'message' || e.type === 'result').length > 0 && (
                        <Box sx={{ 
                          '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 } },
                          '& a': { color: PALETTE.accent, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } },
                          '& strong': { fontWeight: 600 },
                          '& code': { 
                            bgcolor: isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)', 
                            px: 0.5, 
                            py: 0.15,
                            borderRadius: 0.5, 
                            fontFamily: 'monospace', 
                            fontSize: '0.85em',
                            border: '1px solid',
                            borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                          },
                          '& pre': {
                            bgcolor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                            p: 1.5,
                            borderRadius: 1,
                            overflow: 'auto',
                            border: '1px solid',
                            borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                            '& code': { 
                              bgcolor: 'transparent', 
                              p: 0, 
                              border: 'none',
                              fontSize: '0.8em',
                            },
                          },
                          '& h1, & h2, & h3, & h4, & h5, & h6': { fontSize: '0.95rem', fontWeight: 600, m: 0, mt: 1, mb: 0.5 },
                          '& ul, & ol': { m: 0, pl: 2, '& li': { mb: 0.25 } },
                          fontSize: '0.9rem', lineHeight: 1.6, color: 'text.primary',
                        }}>
                        <ReactMarkdown
                          rehypePlugins={[rehypeRaw]}
                          components={{
                            a: ({ href, children }) => (
                              <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                            ),
                            p: ({ children }) => <p>{colorizeStatus(children)}</p>,
                          }}
                        >
                            {msg.events.filter(e => e.type === 'message' || e.type === 'result').map(e => e.content).join('\n\n').replace(/\n{3,}/g, '\n\n').trim()}
                          </ReactMarkdown>
                        </Box>
                      )}
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, justifyContent: 'space-between' }}>
                      <Box sx={{ 
                        flex: 1, minWidth: 0,
                        '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 } },
                        '& a': { color: PALETTE.accent, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } },
                        '& strong': { fontWeight: 600 },
                        '& code': { 
                          bgcolor: isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)', 
                          px: 0.5, 
                          py: 0.15,
                          borderRadius: 0.5, 
                          fontFamily: 'monospace', 
                          fontSize: '0.85em',
                          border: '1px solid',
                          borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                        },
                        '& pre': {
                          bgcolor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                          p: 1.5,
                          borderRadius: 1,
                          overflow: 'auto',
                          border: '1px solid',
                          borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                          '& code': { 
                            bgcolor: 'transparent', 
                            p: 0, 
                            border: 'none',
                            fontSize: '0.8em',
                          },
                        },
                        '& h1, & h2, & h3, & h4, & h5, & h6': { fontSize: '0.95rem', fontWeight: 600, m: 0, mt: 1, mb: 0.5 },
                        '& ul, & ol': { m: 0, pl: 2, '& li': { mb: 0.25 } },
                        fontSize: '0.9rem', lineHeight: 1.6, color: 'text.primary',
                      }}>
                        <ReactMarkdown
                          rehypePlugins={[rehypeRaw]}
                          components={{
                            a: ({ href, children }) => (
                              <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                            ),
                            p: ({ children }) => <p>{colorizeStatus(children)}</p>,
                          }}
                        >
                          {(msg.content || '').replace(/\n{3,}/g, '\n\n').trim()}
                        </ReactMarkdown>
                      </Box>
                      <Tooltip title="Copy message">
                        <IconButton 
                          size="small" 
                          onClick={() => navigator.clipboard.writeText(msg.content || '')}
                          sx={{ p: 0.25, opacity: 0.3, '&:hover': { opacity: 1, color: PALETTE.accent }, flexShrink: 0, mt: -0.5 }}
                        >
                          <CopyIcon sx={{ fontSize: 12 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  )}

                  {!isUser && (() => {
                    const metrics = msg.events?.reduce((acc, e) => {
                      if (e.metrics) {
                        acc.duration += e.metrics.duration_ms;
                        acc.input += e.metrics.input_tokens;
                        acc.output += e.metrics.output_tokens;
                      }
                      return acc;
                    }, { duration: 0, input: 0, output: 0 }) || { duration: 0, input: 0, output: 0 };
                    
                    const hasMetrics = metrics.duration > 0 || metrics.input > 0;
                    
                    const copyMessage = () => {
                      const parts: string[] = [`${msg.agent || 'Assistant'}:`];
                      const toolCalls = msg.events?.filter(e => e.type === 'tool_call') || [];
                      const toolResults = msg.events?.filter(e => e.type === 'tool_result') || [];
                      
                      toolCalls.forEach(tool => {
                        const result = toolResults.find(r => r.tool_name === tool.tool_name);
                        parts.push(`\n  [Tool: ${tool.tool_name}]`);
                        if (tool.tool_params) {
                          parts.push(`  Input: ${JSON.stringify(tool.tool_params, null, 2).split('\n').join('\n  ')}`);
                        }
                        if (result?.tool_result) {
                          const resultStr = typeof result.tool_result === 'string' 
                            ? result.tool_result 
                            : JSON.stringify(result.tool_result, null, 2);
                          parts.push(`  Result: ${resultStr.split('\n').join('\n  ')}`);
                        }
                      });
                      
                      const content = msg.events
                        ?.filter(e => e.type === 'message' || e.type === 'result')
                        .map(e => e.content)
                        .join('\n')
                        .trim();
                      if (content) parts.push(`\n${content}`);
                      
                      navigator.clipboard.writeText(parts.join('\n'));
                    };
                    
                    const currentFeedback = messageFeedback[msg.id];
                    const isPositive = currentFeedback === 5;
                    const isNegative = currentFeedback === 1;
                    
                    // Get first user message for context
                    const userMsgIndex = messages.findIndex(m => m.id === msg.id) - 1;
                    const userPrompt = userMsgIndex >= 0 ? messages[userMsgIndex]?.content : undefined;
                    
                    return (
                      <Box sx={{ mt: 1, pt: 0.75, borderTop: '1px solid', borderColor: isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)', display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'nowrap' }}>
                        {/* Feedback buttons */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                          <Tooltip title={isPositive ? "Remove helpful rating" : "Mark as helpful"}>
                            <IconButton
                              size="small"
                              onClick={() => submitMessageFeedback(msg.id, 5, msg.agent || selectedAgentId, userPrompt)}
                              sx={{
                                p: 0.25,
                                color: isPositive ? '#22c55e' : 'text.disabled',
                                bgcolor: isPositive ? 'rgba(34, 197, 94, 0.15)' : 'transparent',
                                borderRadius: 1,
                                transition: 'all 0.2s',
                                '&:hover': { 
                                  color: '#22c55e',
                                  bgcolor: 'rgba(34, 197, 94, 0.1)',
                                },
                              }}
                            >
                              <ThumbUp sx={{ fontSize: 13 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={isNegative ? "Remove not helpful rating" : "Mark as not helpful"}>
                            <IconButton
                              size="small"
                              onClick={() => submitMessageFeedback(msg.id, 1, msg.agent || selectedAgentId, userPrompt)}
                              sx={{
                                p: 0.25,
                                color: isNegative ? '#ef4444' : 'text.disabled',
                                bgcolor: isNegative ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                                borderRadius: 1,
                                transition: 'all 0.2s',
                                '&:hover': { 
                                  color: '#ef4444',
                                  bgcolor: 'rgba(239, 68, 68, 0.1)',
                                },
                              }}
                            >
                              <ThumbDown sx={{ fontSize: 13 }} />
                            </IconButton>
                          </Tooltip>
                        </Box>
                        
                        {hasMetrics && (
                          <>
                            <Box sx={{ width: '1px', height: 12, bgcolor: isDarkMode ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)', flexShrink: 0 }} />
                            
                            <Tooltip title="Processing time">
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, opacity: 0.5, flexShrink: 0 }}>
                                <TimeIcon sx={{ fontSize: 10 }} />
                                <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                                  {(metrics.duration / 1000).toFixed(1)}s
                                </Typography>
                              </Box>
                            </Tooltip>
                            <Tooltip title={`Input: ${metrics.input.toLocaleString()} tokens (read) / Output: ${metrics.output.toLocaleString()} tokens (generated)`}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, opacity: 0.5, flexShrink: 0 }}>
                                <TokenIcon sx={{ fontSize: 10 }} />
                                <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                                  ↓{metrics.input.toLocaleString()} ↑{metrics.output.toLocaleString()}
                                </Typography>
                              </Box>
                            </Tooltip>
                            <Tooltip title="Copy message">
                              <IconButton 
                                size="small" 
                                onClick={copyMessage}
                                sx={{ p: 0, opacity: 0.5, '&:hover': { opacity: 1, color: PALETTE.accent }, flexShrink: 0 }}
                              >
                                <CopyIcon sx={{ fontSize: 12 }} />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                      </Box>
                    );
                  })()}
                </Paper>
              </Box>
            );
          })}

          {/* Processing State - only show when viewing the pending conversation */}
          {showProcessing && (
            <Paper 
              elevation={0}
              sx={{ 
                p: 2,
                bgcolor: isDarkMode ? PALETTE.agentBubble : 'grey.50',
                border: '1px solid',
                borderColor: isDarkMode ? PALETTE.agentBorder : 'grey.200',
                borderRadius: 2.5,
                maxWidth: '85%',
              }}
            >
              {/* Active Agent Badge - shows delegated agent when active */}
              {(() => {
                const activeAgent = session?.active_agent || selectedAgentId;
                const hasToolEvents = currentEvents.some(e => e.type === 'tool_call');
                return (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: hasToolEvents ? 1.5 : 0 }}>
                    <Avatar 
                      sx={{ 
                        width: 28, 
                        height: 28, 
                        fontSize: 11, 
                        fontWeight: 600,
                        bgcolor: getAgentColor(activeAgent),
                        animation: 'pulse 1.5s infinite',
                      }}
                    >
                      {getInitials(getAgentNickname(activeAgent))}
                    </Avatar>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ lineHeight: 1.2 }}>
                        {getAgentNickname(activeAgent)}
                      </Typography>
                      {/* Inline bouncing dots - always visible during processing */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 0.5 }}>
                        {[0, 1, 2].map((i) => (
                          <Box 
                            key={i}
                            sx={{ 
                              width: 4, height: 4, borderRadius: '50%', bgcolor: PALETTE.accent,
                              animation: 'bounce 1.4s ease-in-out infinite',
                              animationDelay: `${i * 0.16}s`,
                              '@keyframes bounce': {
                                '0%, 80%, 100%': { transform: 'scale(0.6)', opacity: 0.4 },
                                '40%': { transform: 'scale(1)', opacity: 1 },
                              },
                            }} 
                          />
                        ))}
                      </Box>
                    </Box>
                  </Box>
                );
              })()}
                
              {currentEvents.some(e => e.type === 'tool_call') && (
                <Box sx={{ pl: 2, borderLeft: `2px solid ${session?.active_agent ? getAgentColor(session.active_agent) : PALETTE.accent}40` }}>
                  {/* Tool calls only - thinking messages hidden */}
                  {mergeToolEvents(currentEvents).map(renderToolActivity)}
                </Box>
              )}

              {currentEvents.some(e => e.type === 'approval_required') && (
                <Box sx={{ p: 1.5, mt: 1.5, border: '1px solid', borderColor: PALETTE.accent, borderRadius: 1.5, bgcolor: `${PALETTE.accent}10` }}>
                  <Typography variant="subtitle2" sx={{ color: PALETTE.accent, fontWeight: 600 }} gutterBottom>
                    🔐 Permission Request
                  </Typography>
                  <Typography variant="caption" sx={{ mb: 1.5, display: 'block', color: 'text.secondary' }}>
                    The agent wants to perform a critical action.
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button variant="contained" size="small" onClick={() => handleApproval(true)} sx={{ bgcolor: PALETTE.accent, '&:hover': { bgcolor: PALETTE.accentHover }, textTransform: 'none', fontWeight: 600 }}>
                      Approve
                    </Button>
                    <Button variant="outlined" size="small" color="inherit" onClick={() => handleApproval(false)} sx={{ textTransform: 'none' }}>
                      Deny
                    </Button>
                  </Box>
                </Box>
              )}
            </Paper>
          )}

          {error && (
            <Alert severity="error" sx={{ mt: 1 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          
          <div ref={messagesEndRef} />
        </Box>
      </Box>

      {/* Input Area */}
      <Box sx={{ px: 2, py: 1.5, flexShrink: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Paper
            elevation={0}
            sx={{
              p: 0.75,
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              bgcolor: isDarkMode ? PALETTE.inputBg : '#fff',
              border: '1px solid',
              borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
              borderRadius: 2.5,
              transition: 'all 0.2s',
              '&:focus-within': { borderColor: PALETTE.accent },
            }}
          >
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              sx={{ ml: 1.5, flex: 1, py: 0.25 }}
              variant="standard"
              autoComplete="off"
              InputProps={{ disableUnderline: true, sx: { fontSize: '0.9rem' } }}
            />
            <IconButton 
              onClick={showProcessing ? stopGeneration : sendMessage}
              disabled={!input.trim() && !showProcessing}
              sx={{  
                m: 0.25, 
                bgcolor: (input.trim() || showProcessing) ? PALETTE.accent : 'transparent',
                color: (input.trim() || showProcessing) ? '#fff' : 'text.disabled',
                width: 32, height: 32,
                '&:hover': { bgcolor: (input.trim() || showProcessing) ? PALETTE.accentHover : 'transparent' },
              }}
            >
              {showProcessing ? <StopIcon sx={{ fontSize: 18 }} /> : <SendIcon sx={{ fontSize: 18 }} />}
            </IconButton>
          </Paper>
          
          <Box sx={{ display: 'flex', gap: 0.25 }}>
            <Tooltip title="Copy messages">
              <span>
                <IconButton 
                  size="small" 
                  disabled={messages.length === 0} 
                  onClick={() => {
                    const text = messages.map(msg => {
                      const role = msg.role === 'user' ? 'You' : (msg.agent || 'Assistant');
                      
                      if (msg.role === 'user') {
                        return `${role}: ${msg.content || ''}`;
                      }
                      
                      // For assistant messages, include tools and response
                      const parts: string[] = [`${role}:`];
                      
                      // Add tool calls with results
                      if (msg.events) {
                        const toolCalls = msg.events.filter(e => e.type === 'tool_call');
                        const toolResults = msg.events.filter(e => e.type === 'tool_result');
                        
                        toolCalls.forEach(tool => {
                          const result = toolResults.find(r => r.tool_name === tool.tool_name);
                          parts.push(`\n  [Tool: ${tool.tool_name}]`);
                          if (tool.tool_params) {
                            parts.push(`  Input: ${JSON.stringify(tool.tool_params, null, 2).split('\n').join('\n  ')}`);
                          }
                          if (result?.tool_result) {
                            const resultStr = typeof result.tool_result === 'string' 
                              ? result.tool_result 
                              : JSON.stringify(result.tool_result, null, 2);
                            parts.push(`  Result: ${resultStr.split('\n').join('\n  ')}`);
                          }
                        });
                        
                        // Add message content
                        const content = msg.events
                          .filter(e => e.type === 'message' || e.type === 'result')
                          .map(e => e.content)
                          .join('\n')
                          .trim();
                        if (content) parts.push(`\n${content}`);
                      }
                      
                      return parts.join('\n');
                    }).join('\n\n');
                    navigator.clipboard.writeText(text);
                  }}
                  sx={{ opacity: messages.length > 0 ? 0.5 : 0.2, '&:hover': { opacity: 1 } }}
                >
                  <CopyIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Export">
              <span>
                <IconButton size="small" disabled={messages.length === 0} sx={{ opacity: messages.length > 0 ? 0.5 : 0.2, '&:hover': { opacity: 1 } }}>
                  <ExportIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Clear all">
              <span>
                <IconButton size="small" onClick={clearHistory} disabled={conversations.length === 0} sx={{ opacity: conversations.length > 0 ? 0.5 : 0.2, '&:hover': { opacity: 1, color: 'error.main' } }}>
                  <ClearIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </span>
            </Tooltip>
          </Box>
        </Box>
      </Box>
    </>
  );

  // --- Section Toggle Button ---
  const SectionToggle = ({ 
    active, 
    onClick, 
    icon: Icon, 
    tooltip 
  }: { 
    active: boolean; 
    onClick: () => void; 
    icon: React.ElementType; 
    tooltip: string;
  }) => (
    <Tooltip title={tooltip}>
      <IconButton
        size="small"
        onClick={onClick}
        sx={{
          width: 32,
          height: 32,
          borderRadius: 1.5,
          bgcolor: active 
            ? (isDarkMode ? PALETTE.surface : 'grey.200') 
            : 'transparent',
          color: active ? PALETTE.accent : 'text.disabled',
          border: '1px solid',
          borderColor: active 
            ? (isDarkMode ? PALETTE.borderColor : 'grey.300')
            : 'transparent',
          transition: 'all 0.15s',
          '&:hover': {
            bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100',
            color: active ? PALETTE.accent : 'text.secondary',
          },
        }}
      >
        <Icon sx={{ fontSize: 18 }} />
      </IconButton>
    </Tooltip>
  );

  // --- Main Render ---
  return (
    <Box sx={{ 
      height: 'calc(98vh - 64px)', 
      display: 'flex', 
      flexDirection: 'column',
      bgcolor: 'background.default',
      overflow: 'hidden',
    }}>
      {/* Top Bar with Section Toggles */}
      <Box sx={{ 
        py: 0.5, 
        px: 2, 
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid',
        borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
        flexShrink: 0,
        bgcolor: isDarkMode ? PALETTE.sidebarBg : 'grey.50',
      }}>
        {/* Left: Title + Agent Selector */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SparkleIcon sx={{ fontSize: 18, color: PALETTE.accent }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.primary' }}>
              AI Agent
            </Typography>
          </Box>
          
          {/* Agent Selector */}
          <FormControl size="small" sx={{ minWidth: 180 }} disabled={agentsLoading || agentsError !== null}>
            <Select
              value={availableAgents.length ? selectedAgentId : ''}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              sx={{
                height: 32,
                fontSize: '0.85rem',
                bgcolor: isDarkMode ? PALETTE.inputBg : '#fff',
                borderRadius: 1.5,
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: isDarkMode ? PALETTE.borderColor : 'grey.300',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: PALETTE.accent,
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: PALETTE.accent,
                },
                '& .MuiSelect-select': {
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  py: 0.5,
                },
              }}
              MenuProps={{
                PaperProps: {
                  sx: {
                    bgcolor: isDarkMode ? PALETTE.surface : '#fff',
                    border: '1px solid',
                    borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
                    boxShadow: PALETTE.cardShadow,
                  }
                }
              }}
            >
              {availableAgents.map((agent) => (
                <MenuItem 
                  key={agent.id} 
                  value={agent.id}
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    py: 1,
                    '&:hover': { bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100' },
                    '&.Mui-selected': { bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100' },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{agent.nickname}</Typography>
                  </Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', pl: 0.5, fontSize: '0.7rem' }}>
                    {agent.description}
                  </Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        
        {/* Right: Device Controls + Auto-redirect toggle + Section Toggles */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {/* Device Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Device Selection Dropdown */}
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="agent-chat-device-select-label">Device</InputLabel>
              <Select
                labelId="agent-chat-device-select-label"
                value={selectedDevice || ''}
                onChange={(e) => handleDeviceSelection(e.target.value)}
                label="Device"
                sx={{ height: 32, fontSize: '0.75rem' }}
              >
                {getAllHosts().flatMap((host) => {
                  const devices = host.devices || [];
                  return devices.map((device) => (
                    <MenuItem
                      key={`${host.host_name}:${device.device_id}`}
                      value={device.device_id}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                      }}
                    >
                      <span>
                        {device.device_name} ({host.host_name})
                      </span>
                    </MenuItem>
                  ));
                })}
              </Select>
            </FormControl>

            {/* Show/Hide Device Panel Button */}
            <Button
              variant={showDevicePanel ? 'contained' : 'outlined'}
              size="small"
              onClick={handleDevicePanelToggle}
              disabled={!selectedDevice}
              startIcon={<DevicesIcon />}
              color={showDevicePanel ? 'success' : 'primary'}
              sx={{
                height: 32,
                fontSize: '0.7rem',
                minWidth: 90,
                maxWidth: 90,
                whiteSpace: 'nowrap',
                px: 1.5,
              }}
              title={showDevicePanel ? 'Hide Device Screen' : 'Show Device Screen'}
            >
              {showDevicePanel ? 'Hide' : 'Show'}
            </Button>
          </Box>

          {/* Auto-redirect toggle */}
          <Tooltip title={allowAutoNavigation ? "Auto-redirect enabled" : "Auto-redirect disabled"}>
            <Box sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              opacity: 0.8,
            }}>
              <RedirectIcon sx={{ fontSize: 14, color: allowAutoNavigation ? PALETTE.accent : 'text.disabled' }} />
              <Switch
                size="small"
                checked={allowAutoNavigation}
                onChange={(e) => setAllowAutoNavigation(e.target.checked)}
                sx={{
                  width: 32,
                  height: 18,
                  padding: 0,
                  '& .MuiSwitch-switchBase': {
                    padding: 0,
                    margin: '2px',
                    transitionDuration: '200ms',
                    '&.Mui-checked': {
                      transform: 'translateX(14px)',
                      color: '#fff',
                      '& + .MuiSwitch-track': {
                        backgroundColor: PALETTE.accent,
                        opacity: 1,
                        border: 0,
                      },
                    },
                  },
                  '& .MuiSwitch-thumb': {
                    width: 14,
                    height: 14,
                  },
                  '& .MuiSwitch-track': {
                    borderRadius: 9,
                    backgroundColor: isDarkMode ? PALETTE.borderColor : 'grey.400',
                    opacity: 1,
                  },
                }}
              />
            </Box>
          </Tooltip>
          
          {/* Section Toggles */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 0.5,
            p: 0.5,
            borderRadius: 2,
            bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.05)',
          }}>
            <SectionToggle
              active={showHistory}
              onClick={() => setShowHistory(!showHistory)}
              icon={SidebarIcon}
              tooltip={showHistory ? "Hide history" : "Show history"}
            />
            <SectionToggle
              active={showChat}
              onClick={() => setShowChat(!showChat)}
              icon={ChatPanelIcon}
              tooltip={showChat ? "Hide chat" : "Show chat"}
            />
            <SectionToggle
              active={showDevice}
              onClick={() => setShowDevice(!showDevice)}
              icon={DevicePanelIcon}
              tooltip={showDevice ? "Hide device" : "Show device"}
            />
          </Box>
        </Box>
      </Box>

      {/* Main Content Area */}
      <Box sx={{ 
        flex: 1, 
        display: 'flex', 
        overflow: 'hidden',
      }}>
        {/* Left Sidebar */}
        {renderLeftSidebar()}

        {/* Center - Main Chat */}
        {showChat && (
          <Box sx={{ 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            minWidth: 0,
          }}>
            {(() => {
              // Determine if we should show empty state
              const isSystemConversation = activeConversationId?.startsWith('bg_');
              const hasNoMessages = messages.length === 0;
              const onChatsTabWithNoRegularConvo = sidebarTab === 'chats' && (!activeConversationId || isSystemConversation);
              // Show system placeholder only when on system tab AND (no conversation selected OR selected conversation is not a system one)
              const onSystemTabWithNoSelection = sidebarTab === 'system' && (!activeConversationId || !isSystemConversation);
              
              // Debug: Log render conditions
              console.log('[AgentChat] Render check:', {
                activeConversationId,
                sidebarTab,
                messagesLength: messages.length,
                isSystemConversation,
                hasNoMessages,
                onChatsTabWithNoRegularConvo,
                onSystemTabWithNoSelection,
                status
              });
              
              // Show system placeholder when on system tab with no incident selected
              if (status === 'ready' && onSystemTabWithNoSelection) {
                return (
                  <Box sx={{ 
                    flex: 1,
                    display: 'flex', 
                    flexDirection: 'column', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                  }}>
                    <Typography 
                      variant="body1" 
                      sx={{ 
                        color: PALETTE.textMuted,
                        fontWeight: 400,
                        opacity: 0.6,
                      }}
                    >
                      No incident
                    </Typography>
                  </Box>
                );
              }
              
              // Show empty state when ready AND (no messages OR on chats tab without a regular conversation)
              const showEmpty = status === 'ready' && (hasNoMessages || onChatsTabWithNoRegularConvo);
              
              return showEmpty ? renderEmptyState() : renderChatContent();
            })()}
          </Box>
        )}

        {/* Empty state when chat is hidden */}
        {!showChat && (
          <Box sx={{ 
            flex: 1, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            color: 'text.disabled',
          }}>
            <Box sx={{ textAlign: 'center' }}>
              <ChatPanelIcon sx={{ fontSize: 48, opacity: 0.3, mb: 1 }} />
              <Typography variant="body2" color="text.disabled">
                Chat panel hidden
              </Typography>
            </Box>
          </Box>
        )}

        {/* Right Panel */}
        {renderRightPanel()}
      </Box>

      {/* Confirm Dialog */}
      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        message={confirmDialog.message}
        confirmText="OK"
        cancelText="Cancel"
        confirmColor="error"
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
      />
      
      {/* 🆕 NEW: Device Control Panels - auto-mount when control is taken, auto-unmount when released */}
      {/* AgentChat only shows device screen (HDMI/VNC), not remote control */}
      <DeviceControlPanels
        {...agentChatPanelProps}
        isSidebarOpen={showHistory}
        footerHeight={0} // No footer in AgentChat
      />
    </Box>
  );
};

export default AgentChat;
