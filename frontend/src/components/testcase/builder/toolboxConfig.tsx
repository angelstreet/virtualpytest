import React from 'react';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import VerifiedIcon from '@mui/icons-material/Verified';
import NavigationIcon from '@mui/icons-material/Navigation';
import LoopIcon from '@mui/icons-material/Loop';
import SettingsIcon from '@mui/icons-material/Settings';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import SwipeIcon from '@mui/icons-material/Swipe';
import KeyboardIcon from '@mui/icons-material/Keyboard';
import ImageIcon from '@mui/icons-material/Image';
import AudiotrackIcon from '@mui/icons-material/Audiotrack';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import HttpIcon from '@mui/icons-material/Http';
import ShuffleIcon from '@mui/icons-material/Shuffle';
import StorageIcon from '@mui/icons-material/Storage';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { BlockType } from '../../../types/testcase/TestCase_Types';

export type OutputType = 'success' | 'failure' | 'true' | 'false' | 'complete' | 'break';

export interface CommandConfig {
  type: string;
  label: string;
  icon: React.ReactNode;
  color: string;
  outputs: OutputType[];
  defaultData?: Record<string, any>;
  description?: string;
}

export interface CommandGroup {
  groupName: string;
  commands: CommandConfig[];
}

export interface TabConfig {
  tabName: string;
  groups: CommandGroup[];
}

/**
 * Comprehensive toolbox configuration
 * Organized by tabs → groups → specific commands
 */
export const toolboxConfig: Record<string, TabConfig> = {
  standard: {
    tabName: 'Standard',
    groups: [
      {
        groupName: 'Control Flow',
        commands: [
          {
            type: BlockType.LOOP,
            label: 'Loop',
            icon: <LoopIcon fontSize="small" />,
            color: '#f59e0b',
            outputs: ['complete', 'break'],
            defaultData: { iterations: 1 },
            description: 'Repeat steps multiple times'
          },
          {
            type: 'condition',
            label: 'Evaluate Condition',
            icon: <AccountTreeIcon fontSize="small" />,
            color: '#8b5cf6',
            outputs: ['true', 'false'],
            description: 'Conditional branching'
          },
          {
            type: 'container',
            label: 'Container',
            icon: <SettingsIcon fontSize="small" />,
            color: '#6b7280',
            outputs: ['success', 'failure'],
            description: 'Group multiple blocks'
          },
        ]
      },
      {
        groupName: 'Variables',
        commands: [
          {
            type: 'set_variable',
            label: 'Set Variable',
            icon: <StorageIcon fontSize="small" />,
            color: '#3b82f6',
            outputs: ['success'],
            description: 'Store a value in variable'
          },
        ]
      },
      {
        groupName: 'Timing',
        commands: [
          {
            type: 'sleep',
            label: 'Sleep',
            icon: <AccessTimeIcon fontSize="small" />,
            color: '#6b7280',
            outputs: ['success'],
            description: 'Wait for specified duration'
          },
        ]
      },
      {
        groupName: 'Data Operations',
        commands: [
          {
            type: 'get_current_time',
            label: 'Get Current Time',
            icon: <AccessTimeIcon fontSize="small" />,
            color: '#6b7280',
            outputs: ['success'],
            description: 'Get current timestamp'
          },
          {
            type: 'generate_random',
            label: 'Generate Random',
            icon: <ShuffleIcon fontSize="small" />,
            color: '#6b7280',
            outputs: ['success'],
            description: 'Generate random value'
          },
        ]
      },
      {
        groupName: 'Network',
        commands: [
          {
            type: 'http_request',
            label: 'HTTP Request',
            icon: <HttpIcon fontSize="small" />,
            color: '#6b7280',
            outputs: ['success', 'failure'],
            description: 'Make HTTP API call'
          },
        ]
      }
    ]
  },
  
  actions: {
    tabName: 'Actions',
    groups: [
      {
        groupName: 'Remote Control',
        commands: [
          {
            type: 'press_key',
            label: 'Press Key',
            icon: <PlayArrowIcon fontSize="small" />,
            color: '#3b82f6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'press_key', action_type: 'remote' },
            description: 'Send IR remote key'
          },
          {
            type: 'press_sequence',
            label: 'Press Sequence',
            icon: <PlayArrowIcon fontSize="small" />,
            color: '#3b82f6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'press_sequence', action_type: 'remote' },
            description: 'Send multiple IR keys'
          },
        ]
      },
      {
        groupName: 'ADB Actions',
        commands: [
          {
            type: 'tap',
            label: 'Tap',
            icon: <TouchAppIcon fontSize="small" />,
            color: '#10b981',
            outputs: ['success', 'failure'],
            defaultData: { command: 'tap', action_type: 'adb' },
            description: 'Tap at coordinates'
          },
          {
            type: 'swipe',
            label: 'Swipe',
            icon: <SwipeIcon fontSize="small" />,
            color: '#10b981',
            outputs: ['success', 'failure'],
            defaultData: { command: 'swipe', action_type: 'adb' },
            description: 'Swipe gesture'
          },
          {
            type: 'type_text',
            label: 'Type Text',
            icon: <KeyboardIcon fontSize="small" />,
            color: '#10b981',
            outputs: ['success', 'failure'],
            defaultData: { command: 'type_text', action_type: 'adb' },
            description: 'Input text via ADB'
          },
        ]
      }
    ]
  },
  
  verifications: {
    tabName: 'Verifications',
    groups: [
      {
        groupName: 'Visual',
        commands: [
          {
            type: 'verify_image',
            label: 'Find Template',
            icon: <ImageIcon fontSize="small" />,
            color: '#8b5cf6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'verify_image', verification_type: 'image' },
            description: 'Template matching'
          },
          {
            type: 'verify_ocr',
            label: 'OCR Text',
            icon: <VerifiedIcon fontSize="small" />,
            color: '#8b5cf6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'verify_ocr', verification_type: 'ocr' },
            description: 'Optical character recognition'
          },
        ]
      },
      {
        groupName: 'Audio',
        commands: [
          {
            type: 'verify_audio',
            label: 'Check Audio',
            icon: <AudiotrackIcon fontSize="small" />,
            color: '#8b5cf6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'verify_audio', verification_type: 'audio' },
            description: 'Verify audio is playing'
          },
        ]
      },
      {
        groupName: 'State',
        commands: [
          {
            type: 'verify_element',
            label: 'Element Exists',
            icon: <CheckCircleOutlineIcon fontSize="small" />,
            color: '#8b5cf6',
            outputs: ['success', 'failure'],
            defaultData: { command: 'verify_element', verification_type: 'element' },
            description: 'Check if element exists'
          },
        ]
      }
    ]
  },
  
  navigation: {
    tabName: 'Navigation',
    groups: [
      {
        groupName: 'Navigation',
        commands: [
          {
            type: BlockType.NAVIGATION,
            label: 'Goto',
            icon: <NavigationIcon fontSize="small" />,
            color: '#10b981',
            outputs: ['success', 'failure'],
            description: 'Navigate to UI node'
          },
        ]
      }
    ]
  }
};

/**
 * Helper to get command config by type
 */
export const getCommandConfig = (type: string): CommandConfig | undefined => {
  for (const tab of Object.values(toolboxConfig)) {
    for (const group of tab.groups) {
      const command = group.commands.find(cmd => cmd.type === type);
      if (command) return command;
    }
  }
  return undefined;
};

/**
 * Helper to get output handles for a command type
 */
export const getOutputHandles = (type: string): OutputType[] => {
  const config = getCommandConfig(type);
  return config?.outputs || ['success', 'failure'];
};

