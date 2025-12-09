/**
 * UI Theme Constants for Agent Chat
 * 
 * Centralized color palette and layout dimensions for the AI Agent Chat page.
 */

export const AGENT_CHAT_PALETTE = {
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

export const AGENT_CHAT_LAYOUT = {
  sidebarWidth: 240,
  rightPanelWidth: 320,
};

/**
 * Agent color palette (used for UI display of agent badges/avatars)
 */
export const AGENT_COLORS: Record<string, string> = {
  'ai-assistant': AGENT_CHAT_PALETTE.accent,
  'qa-web-manager': '#4fc3f7',
  'qa-mobile-manager': '#81c784', 
  'qa-stb-manager': '#ba68c8',
  'monitoring-manager': '#ffb74d',
  'qa-manager': '#607d8b',
  'explorer': '#81c784',
  'builder': '#ffb74d',
  'executor': '#e57373',
  'analyst': '#ba68c8',
  'maintainer': '#4fc3f7',
};

