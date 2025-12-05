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
} from '@mui/icons-material';
import { useAgentChat, type AgentEvent, type Conversation } from '../hooks/aiagent';
import { useProfile } from '../hooks/auth/useProfile';

// --- Constants & Configuration ---

const PALETTE = {
  background: '#1a1a1a',
  surface: '#242424',
  inputBg: '#2a2a2a',
  sidebarBg: '#1e1e1e',
  textPrimary: '#f0f0f0',
  textSecondary: '#9a9a9a',
  textMuted: '#666666',
  accent: '#d4a574',
  accentHover: '#c49464',
  agentBubble: '#262626',
  agentBorder: '#333333',
  userBubble: '#3a3a3a',
  userBorder: '#4a4a4a',
  borderColor: '#383838',
  hoverBg: '#2a2a2a',
  cardShadow: '0 2px 8px rgba(0,0,0,0.3)',
};

const SIDEBAR_WIDTH = 240;
const RIGHT_PANEL_WIDTH = 320;

const AGENT_CONFIG: Record<string, { color: string; label: string }> = {
  'QA Manager': { color: '#607d8b', label: 'Orchestrator' },
  'Explorer': { color: '#81c784', label: 'Explorer' },
  'Builder': { color: '#ffb74d', label: 'Builder' },
  'Executor': { color: '#e57373', label: 'Executor' },
  'Analyst': { color: '#ba68c8', label: 'Analyst' },
  'Maintainer': { color: '#4fc3f7', label: 'Maintainer' },
};

const getInitials = (name: string) => name.split(' ').map(n => n[0]).join('').substring(0, 2);

// Merge tool_call events with their corresponding tool_result events
const mergeToolEvents = (events: AgentEvent[]): AgentEvent[] => {
  const toolCalls = events.filter(e => e.type === 'tool_call');
  const toolResults = events.filter(e => e.type === 'tool_result');
  
  return toolCalls.map(call => {
    const result = toolResults.find(r => r.tool_name === call.tool_name);
    return {
      ...call,
      tool_result: result?.tool_result ?? call.tool_result,
      success: result?.success ?? call.success,
    };
  });
};

// Group conversations by time period
const groupConversationsByTime = (conversations: Conversation[]) => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const thisWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const thisMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] },
    { label: 'This Month', items: [] },
    { label: 'Older', items: [] },
  ];

  conversations.forEach(conv => {
    const date = new Date(conv.updatedAt);
    if (date >= today) {
      groups[0].items.push(conv);
    } else if (date >= yesterday) {
      groups[1].items.push(conv);
    } else if (date >= thisWeek) {
      groups[2].items.push(conv);
    } else if (date >= thisMonth) {
      groups[3].items.push(conv);
    } else {
      groups[4].items.push(conv);
    }
  });

  return groups.filter(g => g.items.length > 0);
};

// --- Components ---

const AgentChat: React.FC = () => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  const { profile } = useProfile();
  
  // Layout state - each section can be shown/hidden
  const [showHistory, setShowHistory] = useState(true);
  const [showChat, setShowChat] = useState(true);
  const [showDevice, setShowDevice] = useState(false);
  
  const {
    status,
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
  } = useAgentChat();
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentEvents]);
  
  // Group conversations
  const groupedConversations = groupConversationsByTime(conversations);

  // --- Renderers ---

  const renderToolActivity = (event: AgentEvent, idx: number) => (
    <Accordion 
      key={`${event.tool_name}-${idx}-${event.success ?? 'pending'}-${event.tool_result ? 'done' : 'waiting'}`} 
      disableGutters 
      elevation={0}
      sx={{ 
        bgcolor: 'transparent',
        border: 'none',
        '&:before': { display: 'none' },
        mb: 0.5
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandIcon sx={{ fontSize: 14, color: 'text.disabled' }} />}
        sx={{ 
          minHeight: 24, 
          p: 0, 
          '& .MuiAccordionSummary-content': { my: 0 },
          flexDirection: 'row-reverse',
          gap: 1
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <ConsoleIcon sx={{ fontSize: 12, color: 'text.disabled' }} />
          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', flex: 1 }}>
            {event.tool_name}
          </Typography>
          {event.success === false ? 
            <ErrorIcon sx={{ fontSize: 12, color: 'error.main' }} /> : 
            <SuccessIcon sx={{ fontSize: 12, color: PALETTE.accent }} />
          }
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0, pl: 3 }}>
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 1.5, 
            bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.50',
            borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'grey.300',
            borderRadius: 2
          }}
        >
          <Typography variant="caption" display="block" color="text.secondary" gutterBottom>Input</Typography>
          <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary', maxHeight: 150 }}>
            {event.tool_params ? JSON.stringify(event.tool_params, null, 2) : '{}'}
          </Box>
          
          <Typography variant="caption" display="block" color="text.secondary" gutterBottom sx={{ mt: 1.5 }}>Result</Typography>
          <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', overflow: 'auto', color: 'text.primary', maxHeight: 300 }}>
            {event.tool_result === undefined || event.tool_result === null 
              ? <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>No result data</Typography>
              : typeof event.tool_result === 'string' 
                ? event.tool_result 
                : JSON.stringify(event.tool_result, null, 2)
            }
          </Box>
        </Paper>
      </AccordionDetails>
    </Accordion>
  );

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
            <Button
              fullWidth
              startIcon={<AddIcon />}
              onClick={createNewConversation}
              sx={{
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
          </Box>

          {/* Conversation History */}
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
            {groupedConversations.map((group) => (
              <Box key={group.label} sx={{ mb: 1 }}>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    px: 1,
                    py: 0.75,
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
                    onClick={() => switchConversation(conv.id)}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      px: 1.5,
                      py: 1,
                      borderRadius: 1.5,
                      cursor: 'pointer',
                      bgcolor: conv.id === activeConversationId 
                        ? (isDarkMode ? PALETTE.hoverBg : 'grey.200')
                        : 'transparent',
                      '&:hover': {
                        bgcolor: isDarkMode ? PALETTE.hoverBg : 'grey.100',
                      },
                      transition: 'background-color 0.15s',
                    }}
                  >
                    <ChatIcon sx={{ fontSize: 14, color: PALETTE.textMuted, flexShrink: 0 }} />
                    <Typography
                      variant="body2"
                      sx={{
                        flex: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        color: conv.id === activeConversationId ? 'text.primary' : 'text.secondary',
                        fontSize: '0.85rem',
                      }}
                    >
                      {conv.title}
                    </Typography>
                    {conv.id === activeConversationId && (
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
                    )}
                  </Box>
                ))}
              </Box>
            ))}

            {conversations.length === 0 && (
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
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
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
          
          {/* Suggestion Chips */}
          <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
            {['Automate web app', 'Run goto test', 'How many test cases?', 'What devices are available?'].map((suggestion) => (
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
        </Box>
      </Fade>
    </Box>
  );

  // --- Main Chat Content ---
  const renderChatContent = () => (
    <>
      {/* Chat Stream */}
      <Box sx={{ 
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
                <Button variant="contained" onClick={saveApiKey} disabled={isValidating}>Save</Button>
                <IconButton onClick={() => setShowApiKey(!showApiKey)} size="small">
                  {showApiKey ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </Box>
              {error && <Typography color="error" variant="caption">{error}</Typography>}
            </Box>
          )}

          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            const agentColor = AGENT_CONFIG[msg.agent || 'QA Manager']?.color;
            
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
                  {!isUser && (
                    <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ mb: 0.5, fontSize: '0.8rem' }}>
                      {msg.agent || 'QA Manager'}
                    </Typography>
                  )}

                  {!isUser && msg.events && msg.events.filter(e => e.type === 'tool_call').length > 0 && (
                    <Box sx={{ mb: 1, p: 1, bgcolor: isDarkMode ? 'rgba(0,0,0,0.2)' : 'grey.100', borderRadius: 1.5 }}>
                      {mergeToolEvents(msg.events).map(renderToolActivity)}
                    </Box>
                  )}
                  
                  {!isUser && msg.events ? (
                    <Box>
                      {/* Show thinking/reasoning accordion only if meaningful content exists */}
                      {(() => {
                        const thinkingContent = msg.events
                          .filter(e => e.type === 'thinking')
                          .map(e => e.content)
                          .join('\n\n')
                          .replace(/\n{3,}/g, '\n\n')
                          .trim();
                        // Only show if there's real reasoning, not just placeholder
                        const hasRealThinking = thinkingContent.length > 50 && 
                          !thinkingContent.match(/^Analyzing your request\.{0,3}$/i);
                        
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
                      {/* Show actual response - ONLY message/result events */}
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: 'text.primary', fontSize: '0.9rem' }}>
                        {msg.events.filter(e => e.type === 'message' || e.type === 'result').map(e => e.content).join('\n\n').replace(/\n{3,}/g, '\n\n').trim()}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: 'text.primary', fontSize: '0.9rem' }}>
                      {(msg.content || '').replace(/\n{3,}/g, '\n\n').trim()}
                    </Typography>
                  )}

                  {!isUser && msg.events && (() => {
                    const metrics = msg.events.reduce((acc, e) => {
                      if (e.metrics) {
                        acc.duration += e.metrics.duration_ms;
                        acc.input += e.metrics.input_tokens;
                        acc.output += e.metrics.output_tokens;
                      }
                      return acc;
                    }, { duration: 0, input: 0, output: 0 });
                    
                    if (metrics.duration === 0 && metrics.input === 0) return null;
                    
                    return (
                      <Box sx={{ mt: 1, pt: 0.75, borderTop: '1px solid', borderColor: isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)', display: 'flex', gap: 2, opacity: 0.5 }}>
                        <Tooltip title="Processing time">
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <TimeIcon sx={{ fontSize: 10 }} />
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem' }}>
                              {(metrics.duration / 1000).toFixed(1)}s
                            </Typography>
                          </Box>
                        </Tooltip>
                        <Tooltip title={`Input: ${metrics.input.toLocaleString()} tokens (read) / Output: ${metrics.output.toLocaleString()} tokens (generated)`}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <TokenIcon sx={{ fontSize: 10 }} />
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem' }}>
                              ↓{metrics.input.toLocaleString()} ↑{metrics.output.toLocaleString()}
                            </Typography>
                          </Box>
                        </Tooltip>
                      </Box>
                    );
                  })()}
                </Paper>
              </Box>
            );
          })}

          {/* Processing State */}
          {isProcessing && (
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
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: currentEvents.length > 0 ? 1.5 : 0 }}>
                <ThinkingIcon sx={{ animation: 'pulse 1.5s infinite', color: PALETTE.accent, fontSize: 18 }} />
                <Typography variant="body2" fontWeight={500}>Processing...</Typography>
              </Box>
                
              {currentEvents.length > 0 && (
                <Box sx={{ pl: 2, borderLeft: `2px solid ${PALETTE.accent}40` }}>
                  {mergeToolEvents(currentEvents).map(renderToolActivity)}
                  {currentEvents.filter(e => e.type === 'thinking').map((event, idx) => (
                    <Typography key={`thinking-${idx}`} variant="caption" display="block" color="text.secondary" sx={{ mb: 0.5 }}>
                      {event.content}
                    </Typography>
                  ))}
                </Box>
              )}

              {currentEvents.length === 0 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {[0, 1, 2].map((i) => (
                    <Box 
                      key={i}
                      sx={{ 
                        width: 5, height: 5, borderRadius: '50%', bgcolor: PALETTE.accent,
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
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              sx={{ ml: 1.5, flex: 1, py: 0.25 }}
              variant="standard"
              autoComplete="off"
              InputProps={{ disableUnderline: true, sx: { fontSize: '0.9rem' } }}
            />
            <IconButton 
              onClick={isProcessing ? stopGeneration : sendMessage}
              disabled={!input.trim() && !isProcessing}
              sx={{  
                m: 0.25, 
                bgcolor: input.trim() ? PALETTE.accent : 'transparent',
                color: input.trim() ? '#fff' : 'text.disabled',
                width: 32, height: 32,
                '&:hover': { bgcolor: input.trim() ? PALETTE.accentHover : 'transparent' },
              }}
            >
              {isProcessing ? <StopIcon sx={{ fontSize: 18 }} /> : <SendIcon sx={{ fontSize: 18 }} />}
            </IconButton>
          </Paper>
          
          <Box sx={{ display: 'flex', gap: 0.25 }}>
            <Tooltip title="Copy conversation">
              <span>
                <IconButton size="small" disabled={messages.length === 0} sx={{ opacity: messages.length > 0 ? 0.5 : 0.2, '&:hover': { opacity: 1 } }}>
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
        {/* Left: Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <SparkleIcon sx={{ fontSize: 18, color: PALETTE.accent }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.primary' }}>
            AI Agent
          </Typography>
        </Box>
        
        {/* Right: Section Toggles */}
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
            {status === 'ready' && messages.length === 0 ? renderEmptyState() : renderChatContent()}
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
    </Box>
  );
};

export default AgentChat;
