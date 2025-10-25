/**
 * Toolbox Builder - Build toolbox configuration from navigation data + controller actions
 * Reuses DeviceDataContext logic for actions/verifications
 */

import NavigationIcon from '@mui/icons-material/Navigation';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import VerifiedIcon from '@mui/icons-material/Verified';
import LoopIcon from '@mui/icons-material/Loop';
import type { Actions } from '../types/controller/Action_Types';

/**
 * Build dynamic toolbox configuration
 * - Navigation blocks: from tree nodes (screen names)
 * - Actions/Verifications: from DeviceDataContext (controller capabilities)
 * 
 * Returns structure matching toolboxConfig.tsx format
 */
export function buildToolboxFromNavigationData(
  nodes: any[],
  availableActions: Actions,
  userInterface: any
) {
  // Note: userInterface is optional - only nodes and availableActions are required
  if (!nodes || nodes.length === 0) {
    console.log('[@toolboxBuilder] Cannot build toolbox - no nodes provided');
    return null;
  }

  return {
    standard: {
      tabName: 'Standard',
      groups: [
        {
          groupName: 'Standard',
          commands: [
            { type: 'loop', label: 'Loop', icon: LoopIcon, color: '#3b82f6', outputs: ['complete', 'break'], description: 'Repeat actions' },
            { type: 'sleep', label: 'Sleep', icon: LoopIcon, color: '#3b82f6', outputs: ['success'], description: 'Wait for duration' },
            { type: 'condition', label: 'Evaluate Condition', icon: LoopIcon, color: '#3b82f6', outputs: ['true', 'false'], description: 'Conditional branch' },
            { type: 'set_variable', label: 'Common Operation', icon: LoopIcon, color: '#3b82f6', outputs: ['success'], description: 'Set variable' },
          ]
        }
      ]
    },
    navigation: {
      tabName: 'Navigation',
      groups: [
        {
          groupName: 'Navigation',
          commands: extractNavigationBlocks(nodes)
        }
      ]
    },
    actions: {
      tabName: 'Actions',
      groups: [
        {
          groupName: 'Actions',
          commands: extractActionBlocks(availableActions)
        }
      ]
    },
    verifications: {
      tabName: 'Verifications',
      groups: [
        {
          groupName: 'Verifications',
          commands: extractVerificationBlocks(availableActions)
        }
      ]
    }
  };
}

/**
 * Extract navigation blocks from tree nodes
 */
function extractNavigationBlocks(nodes: any[]) {
  const navigationNodes = nodes
    .filter(node => 
      node.type !== 'entry' &&  // Skip entry nodes
      (node.label || node.data?.label)  // Must have a label (root or data.label)
    )
    .map(node => {
      // Support both API structure (label at root) and ReactFlow structure (data.label)
      const label = node.label || node.data?.label;
      
      return {
        type: 'navigation',
        label: label,  // Show node name in toolbox (e.g., "Home", "Live TV")
        icon: NavigationIcon,
        color: '#8b5cf6',
        outputs: ['success', 'failure'],
        defaultData: {
          target_node_label: label,  // This is what UniversalBlock expects
          target_node_id: node.id,
          label: label  // Also store as 'label' for compatibility
        },
        description: `Navigate to ${label}`
      };
    });

  console.log(`[@toolboxBuilder] Extracted ${navigationNodes.length} navigation nodes`);
  return navigationNodes;
}

/**
 * Extract action blocks from DeviceDataContext availableActions
 * REUSES the same logic as Navigation Editor (ActionsList.tsx)
 */
function extractActionBlocks(availableActions: Actions) {
  const commands: any[] = [];

  // Iterate through all action categories (remote, web, desktop, etc.)
  Object.entries(availableActions).forEach(([category, actions]) => {
    if (!Array.isArray(actions)) return;
    
    actions.forEach((actionDef: any) => {
      // Skip verification actions (they go in verifications tab)
      if (actionDef.action_type === 'verification') return;
      
      commands.push({
        type: 'action',
        label: actionDef.label,
        icon: TouchAppIcon,
        color: '#ef4444',
        outputs: ['success', 'failure'],
        defaultData: {
          command: actionDef.command,
          action_type: actionDef.action_type,
          params: { ...actionDef.params },
          device_model: actionDef.device_model,
        },
        description: actionDef.description || `Execute ${actionDef.label}`
      });
    });
  });

  console.log(`[@toolboxBuilder] Extracted ${commands.length} actions from controllers`);
  return commands;
}

/**
 * Extract verification blocks from DeviceDataContext availableActions
 * REUSES the same logic as Navigation Editor
 * Verifications are stored in availableActions under 'verification' action_type
 */
function extractVerificationBlocks(availableActions: Actions) {
  const commands: any[] = [];

  // Iterate through all action categories and filter for verifications
  Object.entries(availableActions).forEach(([category, actions]) => {
    if (!Array.isArray(actions)) return;
    
    actions.forEach((actionDef: any) => {
      // Only include actions with action_type === 'verification'
      if (actionDef.action_type === 'verification') {
        commands.push({
          type: 'verification',
          label: actionDef.label,
          icon: VerifiedIcon,
          color: '#10b981',
          outputs: ['success', 'failure'],
          defaultData: {
            command: actionDef.command,
            action_type: actionDef.action_type,
            verification_type: actionDef.verification_type,
            params: { ...actionDef.params },
            device_model: actionDef.device_model,
          },
          description: actionDef.description || `Verify ${actionDef.label}`
        });
      }
    });
  });

  console.log(`[@toolboxBuilder] Extracted ${commands.length} verifications from controllers`);
  return commands;
}
