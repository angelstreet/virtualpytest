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
  useTheme,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Typography,
} from '@mui/material';
import {
  AutoAwesome as SparkleIcon,
  ViewSidebar as SidebarIcon,
  Chat as ChatPanelIcon,
  PhoneAndroid as DevicePanelIcon,
} from '@mui/icons-material';
import { useSearchParams, useLocation } from 'react-router-dom';
import { useAgentChat, type BackgroundAgentInfo } from '../hooks/aiagent';
import { buildServerUrl } from '../utils/buildUrlUtils';
import { APP_CONFIG } from '../config/constants';
import { AGENT_CHAT_PALETTE as PALETTE, AGENT_COLORS } from '../constants/agentChatTheme';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { UserinterfaceSelector } from '../components/common/UserinterfaceSelector';
import { useHostManager } from '../contexts/index';
import { ConversationList } from '../components/agent-chat/ConversationList';
import { ChatMessages } from '../components/agent-chat/ChatMessages';
import { DevicePanel } from '../components/agent-chat/DevicePanel';
import { ContentViewer, type ContentType, type ContentData, type ContentTab } from '../components/agent-chat/ContentViewer';
import { useStream } from '../hooks/controller';
import { io, Socket } from 'socket.io-client';


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
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';

  // Layout state - each section can be shown/hidden
  const [showHistory, setShowHistory] = useState(true);
  const [showContentViewer, setShowContentViewer] = useState(false);
  const [showDevice, setShowDevice] = useState(false);

  // Content panel state - controlled by AI agent or user selections
  const [contentType, setContentType] = useState<ContentType | null>(null);
  const [contentData, setContentData] = useState<ContentData | null>(null);
  const [contentTitle, setContentTitle] = useState<string | undefined>(undefined);
  const [contentLoading, setContentLoading] = useState(false);

  // Device selection state for manual control
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [selectedUserInterface, setSelectedUserInterface] = useState<string>('');
  
  // TestCase selection state
  const [selectedTestCase, setSelectedTestCase] = useState<string>('');
  const [testCaseList, setTestCaseList] = useState<Array<{ testcase_id: string; name: string }>>([]);
  const [isLoadingTestCases, setIsLoadingTestCases] = useState(false);
  
  // Content viewer active tab
  const [activeContentTab, setActiveContentTab] = useState<ContentTab>('navigation');
  // showDevicePanel is now controlled by showDevice - when device panel is shown, HDMI is shown

  // Get HostManager for device selection
  const { getAllHosts, handleDeviceSelect } = useHostManager();

  // Get selected device name for display
  const getSelectedDeviceName = () => {
    if (!selectedDevice) return '';
    const device = getAllHosts().flatMap(host => host.devices || []).find(d => d.device_id === selectedDevice);
    return device?.device_name || selectedDevice;
  };

  // Get selected host object for stream hook
  const getSelectedHost = () => {
    if (!selectedDevice) return null;
    const hosts = getAllHosts();
    for (const host of hosts) {
      const device = host.devices?.find(d => d.device_id === selectedDevice);
      if (device) return host;
    }
    return null;
  };

  const selectedHost = getSelectedHost();

  // Stream URL for embedded video in right panel
  const { streamUrl, isLoadingUrl } = useStream({
    host: selectedHost,
    device_id: selectedDevice || ''
  });
  
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
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  
  // Auto-select first available device when component loads
  useEffect(() => {
    if (!selectedDevice) {
      const hosts = getAllHosts();
      const allDevices = hosts.flatMap(host => host.devices || []);

      if (allDevices.length > 0) {
        console.log('[AgentChat] Auto-selecting first available device:', allDevices[0].device_name);
        handleDeviceSelection(allDevices[0].device_id);
      }
    }
  }, [selectedDevice, getAllHosts]); // Include dependencies

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
  
  // Socket connection for AI agent UI actions (show_content, etc.)
  useEffect(() => {
    const serverUrl = buildServerUrl('').replace('/api', '');
    const socket: Socket = io(`${serverUrl}/agent`, {
      transports: ['websocket', 'polling'],
    });
    
    socket.on('connect', () => {
      console.log('[AgentChat] Socket connected for UI actions');
    });
    
    // Listen for ui_action events from AI agent
    socket.on('ui_action', (data: any) => {
      console.log('[AgentChat] Received ui_action:', data);
      
      if (data.action === 'show_content') {
        const { content_type, content_data, title } = data.payload || {};
        
        if (content_type) {
          console.log('[AgentChat] Showing content panel:', content_type, title);
          setContentType(content_type as ContentType);
          setContentData(content_data || null);
          setContentTitle(title);
          setChatMode('minimized'); // Minimize chat when showing content
          setContentLoading(false);
        }
      } else if (data.action === 'hide_content') {
        console.log('[AgentChat] Hiding content panel');
        setContentType(null);
        setContentData(null);
        setContentTitle(undefined);
        setChatMode('full'); // Restore full chat
      } else if (data.action === 'sync_context') {
        // Sync UI dropdowns with agent's execution context
        const { device_id, userinterface_name, testcase_id } = data.payload || {};
        console.log('[AgentChat] Syncing UI context:', { device_id, userinterface_name, testcase_id });

        if (device_id) {
          setSelectedDevice(device_id);
        }
        if (userinterface_name) {
          setSelectedUserInterface(userinterface_name);
          // Auto-show content viewer with navigation tab
          setShowContentViewer(true);
          setActiveContentTab('navigation');
          setContentType('navigation-tree');
          setContentData({ userinterface_name });
          setContentTitle(`Navigation: ${userinterface_name}`);
        }
        if (testcase_id) {
          setSelectedTestCase(testcase_id);
          // Auto-show content viewer with testcase tab
          setShowContentViewer(true);
          setActiveContentTab('testcase');
          setContentType('testcase-flow');
          setContentData({ testcase_id });
          // Title will update when testCaseList is available
        }
      }
    });
    
    socket.on('disconnect', () => {
      console.log('[AgentChat] Socket disconnected');
    });
    
    return () => {
      socket.disconnect();
    };
  }, []);
  
  
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
    conversations,
    activeConversationId,
    pendingConversationId,
    backgroundTasks,
    setBackgroundAgents,
    setInput,
    sendMessage,
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
    setNavigationContext(false, location.pathname);
  }, [location.pathname, setNavigationContext]);
  
  // Manual device selection handler
  const handleDeviceSelection = (deviceId: string) => {
    setSelectedDevice(deviceId);

    // Clear interface selection when device changes
    setSelectedUserInterface('');

    if (!deviceId) {
      // Clearing device selection
      handleDeviceSelect(null, null);
      return;
    }

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

  // Get device model for the selected device (for userinterface filtering)
  const getSelectedDeviceModel = () => {
    if (!selectedDevice) return undefined;

    const hosts = getAllHosts();
    for (const host of hosts) {
      const device = host.devices?.find(d => d.device_id === selectedDevice);
      if (device) {
        return device.device_model;
      }
    }
    return undefined;
  };

  // Manual userinterface selection handler
  const handleUserInterfaceSelection = (userInterface: string) => {
    setSelectedUserInterface(userInterface);
    // Update navigation context with the selected userinterface (empty string for no selection)
    setNavigationContext(false, location.pathname, '', '', userInterface || '');

    // Auto-show ContentViewer with Navigation tab when interface selected
    if (userInterface && showContentViewer) {
      setActiveContentTab('navigation');
      setContentType('navigation-tree');
      setContentData({ userinterface_name: userInterface });
      setContentTitle(`Navigation: ${userInterface}`);
    }
  };
  
  // Fetch test case list
  const fetchTestCaseList = async () => {
    try {
      setIsLoadingTestCases(true);
      const response = await fetch(buildServerUrl(`/server/testcases/?team_id=${APP_CONFIG.DEFAULT_TEAM_ID}`));
      if (response.ok) {
        const data = await response.json();
        setTestCaseList(data.testcases || []);
      }
    } catch (error) {
      console.error('[AgentChat] Failed to fetch test cases:', error);
    } finally {
      setIsLoadingTestCases(false);
    }
  };
  
  // Fetch test cases on mount
  useEffect(() => {
    fetchTestCaseList();
  }, []);
  
  // Handle test case selection
  const handleTestCaseSelection = (testcaseId: string) => {
    setSelectedTestCase(testcaseId);

    // Auto-show ContentViewer with TestCase tab when test case selected and content viewer is active
    if (testcaseId && showContentViewer) {
      const testcase = testCaseList.find(tc => tc.testcase_id === testcaseId);
      setActiveContentTab('testcase');
      setContentType('testcase-flow');
      setContentData({ testcase_id: testcaseId });
      setContentTitle(testcase ? `Test Case: ${testcase.name}` : 'Test Case');
    }
  };

  // Handle device panel toggle
  const handleDevicePanelToggle = () => {
    if (showDevice) {
      // Hide panel
      setShowDevice(false);
    } else if (selectedDevice) {
      // Show panel for selected device
      setShowDevice(true);
    }
  };

  
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
  

  // --- Renderers ---



  // --- Left Sidebar ---
  const renderLeftSidebar = () => (
    <ConversationList
      showHistory={showHistory}
      sidebarTab={sidebarTab}
      handleSidebarTabChange={handleSidebarTabChange}
      conversations={conversations}
      activeConversationId={activeConversationId}
      backgroundAgents={backgroundAgents}
      backgroundTasks={backgroundTasks}
      backgroundExpanded={backgroundExpanded}
      setBackgroundExpanded={setBackgroundExpanded}
      createNewConversation={createNewConversation}
      switchConversation={switchConversation}
      deleteConversation={deleteConversation}
      clearBackgroundHistory={clearBackgroundHistory}
      reloadSkills={reloadSkills}
    />
  );

  // --- Right Panel (Device Execution) ---
  const renderRightPanel = () => (
    <DevicePanel
      showDevice={showDevice}
      selectedDevice={selectedDevice}
      selectedDeviceName={getSelectedDeviceName()}
      selectedUserInterface={selectedUserInterface}
      streamUrl={streamUrl}
      isLoadingUrl={isLoadingUrl}
      getSelectedDeviceModel={getSelectedDeviceModel}
    />
  );


  // --- Main Chat Content ---
  const renderChatContent = () => (
    <ChatMessages
      sidebarTab={sidebarTab}
      activeConversationId={activeConversationId}
      status={status}
      messages={messages}
      currentEvents={currentEvents}
      isProcessing={isProcessing}
      pendingConversationId={pendingConversationId}
      session={session}
      agentsLoading={agentsLoading}
      agentsError={agentsError}
      error={error}
      availableAgents={availableAgents}
      selectedAgentId={selectedAgentId}
      messageFeedback={messageFeedback}
      submitMessageFeedback={submitMessageFeedback}
      input={input}
      sendMessage={sendMessage}
      setInput={setInput}
      handleApproval={handleApproval}
      toolExpanded={toolExpanded}
      setToolExpanded={setToolExpanded}
      messagesEndRef={messagesEndRef}
      scrollContainerRef={scrollContainerRef}
      isUserScrolledUp={isUserScrolledUp}
      lastMessageCount={lastMessageCount}
      lastToolEventCount={lastToolEventCount}
      handleScroll={handleScroll}
      conversations={conversations}
      clearHistory={clearHistory}
      stopGeneration={stopGeneration}
    />
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
            <FormControl size="small" sx={{ width: 200 }}>
              <InputLabel id="agent-chat-device-select-label">Device</InputLabel>
              <Select
                labelId="agent-chat-device-select-label"
                value={selectedDevice || ''}
                onChange={(e) => handleDeviceSelection(e.target.value)}
                label="Device"
                sx={{ height: 32, fontSize: '0.85rem' }}
              >
                <MenuItem value="">
                  <em>Select Device...</em>
                </MenuItem>
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

            {/* UserInterface Selection Dropdown */}
            <Box sx={{ width: 200 }}>
              <UserinterfaceSelector
                deviceModel={getSelectedDeviceModel()}
                value={selectedUserInterface}
                onChange={handleUserInterfaceSelection}
                label="Interface"
                size="small"
                fullWidth
                sx={{ height: 32, fontSize: '0.85rem' }}
              />
            </Box>

            {/* TestCase Selection Dropdown */}
            <FormControl size="small" sx={{ width: 200 }}>
              <InputLabel id="agent-chat-testcase-select-label">Test Case</InputLabel>
              <Select
                labelId="agent-chat-testcase-select-label"
                value={selectedTestCase || ''}
                onChange={(e) => handleTestCaseSelection(e.target.value)}
                label="Test Case"
                sx={{ height: 32, fontSize: '0.85rem' }}
                disabled={isLoadingTestCases}
              >
                <MenuItem value="">
                  <em>{isLoadingTestCases ? 'Loading...' : 'Select Test Case...'}</em>
                </MenuItem>
                {testCaseList.map((tc) => (
                  <MenuItem
                    key={tc.testcase_id}
                    value={tc.testcase_id}
                  >
                    {tc.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

          </Box>

          
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
              active={showContentViewer}
              onClick={() => {
                if (showContentViewer) {
                  // Hide content viewer - go to full chat (keep selections)
                  setShowContentViewer(false);
                  setContentType(null);
                  setContentData(null);
                  setContentTitle(undefined);
                  // Don't clear selectedUserInterface/selectedTestCase - user might toggle back
                } else {
                  // Show content viewer - minimize chat
                  setShowContentViewer(true);
                  // If we have selections, show them automatically
                  if (selectedUserInterface) {
                    setActiveContentTab('navigation');
                    setContentType('navigation-tree');
                    setContentData({ userinterface_name: selectedUserInterface });
                    setContentTitle(`Navigation: ${selectedUserInterface}`);
                  } else if (selectedTestCase) {
                    setActiveContentTab('testcase');
                    setContentType('testcase-flow');
                    setContentData({ testcase_id: selectedTestCase });
                    const tc = testCaseList.find(t => t.testcase_id === selectedTestCase);
                    setContentTitle(tc ? `Test Case: ${tc.name}` : 'Test Case');
                  }
                }
              }}
              icon={ChatPanelIcon}
              tooltip={showContentViewer ? "Hide content viewer" : "Show content viewer"}
            />
            <SectionToggle
              active={showDevice}
              onClick={handleDevicePanelToggle}
              icon={DevicePanelIcon}
              tooltip={showDevice ? "Hide device panel" : "Show device panel"}
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

        {/* Center - Content Viewer + Chat (vertical split) */}
        <Box sx={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column',
          minWidth: 0,
          overflow: 'hidden',
        }}>
          {/* Content Viewer (top area - shown when user toggles it on) */}
          {showContentViewer && (
            <ContentViewer
              contentType={contentType}
              contentData={contentData}
              title={contentTitle}
              isLoading={contentLoading}
              activeTab={activeContentTab}
              onTabChange={(tab) => {
                setActiveContentTab(tab);
                // Update content type based on tab
                if (tab === 'navigation' && selectedUserInterface) {
                  setContentType('navigation-tree');
                  setContentData({ userinterface_name: selectedUserInterface });
                  setContentTitle(`Navigation: ${selectedUserInterface}`);
                } else if (tab === 'testcase' && selectedTestCase) {
                  const tc = testCaseList.find(t => t.testcase_id === selectedTestCase);
                  setContentType('testcase-flow');
                  setContentData({ testcase_id: selectedTestCase });
                  setContentTitle(tc ? `Test Case: ${tc.name}` : 'Test Case');
                }
              }}
              selectedUserInterface={selectedUserInterface}
              selectedTestCase={selectedTestCase}
              selectedTestCaseName={testCaseList.find(tc => tc.testcase_id === selectedTestCase)?.name}
              onClose={() => {
                setShowContentViewer(false);
                setContentType(null);
                setContentData(null);
                setContentTitle(undefined);
              }}
            />
          )}
          
          {/* Chat Area (minimized when content viewer is shown, full otherwise) */}
          <Box sx={{
            flex: showContentViewer ? 0.4 : 1,
            minHeight: showContentViewer ? 200 : 'auto',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            transition: 'flex 0.2s ease-in-out',
          }}>
            {renderChatContent()}
          </Box>
        </Box>

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
    </Box>
  );
};

export default AgentChat;
