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
  'assistant': AGENT_CHAT_PALETTE.accent,
  'monitor': '#4fc3f7',
  'analyzer': '#81c784',
  // Skill colors (for skill badges)
  'exploration-mobile': '#81c784',
  'exploration-web': '#4fc3f7',
  'exploration-stb': '#ba68c8',
  'execution': '#e57373',
  'design': '#ffb74d',
  'monitoring-read': '#4fc3f7',
};

