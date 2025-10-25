/**
 * Toolbox Builder - Build toolbox configuration from navigation data + controller actions
 * Reuses DeviceDataContext logic for actions/verifications
 */

import NavigationIcon from '@mui/icons-material/Navigation';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import VerifiedIcon from '@mui/icons-material/Verified';
import LoopIcon from '@mui/icons-material/Loop';
import type { Actions } from '../types/controller/Action_Types';
import type { Verifications } from '../types/verification/Verification_Types';

/**
 * Sort commands alphabetically, with shorter names appearing before longer ones
 * Example: "home" before "home_tvguide", "home_movies", etc.
 */
function sortCommands(commands: any[]): any[] {
  return commands.sort((a, b) => {
    const labelA = (a.label || '').toLowerCase();
    const labelB = (b.label || '').toLowerCase();
    
    // If one label starts with the other, shorter one comes first
    if (labelA.startsWith(labelB)) return 1;
    if (labelB.startsWith(labelA)) return -1;
    
    // Otherwise, alphabetical sort
    return labelA.localeCompare(labelB);
  });
}

/**
 * Build dynamic toolbox configuration
 * - Navigation blocks: from tree nodes (screen names)
 * - Actions: from DeviceDataContext availableActions
 * - Verifications: from DeviceDataContext availableVerificationTypes
 * 
 * Returns structure matching toolboxConfig.tsx format
 */
export function buildToolboxFromNavigationData(
  nodes: any[],
  availableActions: Actions,
  availableVerifications: Verifications
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
          commands: sortCommands([
            { type: 'loop', label: 'Loop', icon: LoopIcon, color: '#3b82f6', outputs: ['complete', 'break'], description: 'Repeat actions' },
            { type: 'sleep', label: 'Sleep', icon: LoopIcon, color: '#3b82f6', outputs: ['success'], description: 'Wait for duration' },
            { type: 'condition', label: 'Evaluate Condition', icon: LoopIcon, color: '#3b82f6', outputs: ['true', 'false'], description: 'Conditional branch' },
            { type: 'set_variable', label: 'Common Operation', icon: LoopIcon, color: '#3b82f6', outputs: ['success'], description: 'Set variable' },
          ])
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
      groups: extractActionGroups(availableActions)
    },
    verifications: {
      tabName: 'Verifications',
      groups: extractVerificationGroups(availableVerifications)
    }
  };
}

/**
 * Extract navigation blocks from tree nodes
 */
function extractNavigationBlocks(nodes: any[]) {
  const navigationNodes = nodes
    .filter(node => {
      // Skip entry nodes (case-insensitive) - check type, label, and id
      const nodeType = (node.type || '').toLowerCase();
      const nodeLabel = (node.label || node.data?.label || '').toLowerCase();
      const nodeId = (node.id || node.node_id || '').toLowerCase();
      
      // Filter out if type, label, or id contains "entry"
      if (nodeType === 'entry' || nodeLabel === 'entry' || nodeId === 'entry' || nodeId.includes('entry')) {
        return false;
      }
      
      // Must have a label (root or data.label)
      return (node.label || node.data?.label);
    })
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
          target_node_label: label,  // Data: target node name for execution
          target_node_id: node.id,    // Data: target node ID for execution
          // NO label field here - let addBlock auto-generate it as "navigation_1:home"
        },
        description: `Navigate to ${label}`
      };
    });

  console.log(`[@toolboxBuilder] Extracted ${navigationNodes.length} navigation nodes`);
  
  // Sort alphabetically with shorter names first
  return sortCommands(navigationNodes);
}

/**
 * Extract action groups from DeviceDataContext availableActions
 * Groups actions by action_type (remote, web, desktop, av, power, etc.)
 */
function extractActionGroups(availableActions: Actions) {
  const groupMap: Record<string, any[]> = {};

  // Iterate through all action categories (remote, web, desktop, etc.)
  Object.entries(availableActions).forEach(([category, actions]) => {
    if (!Array.isArray(actions)) return;
    
    actions.forEach((actionDef: any) => {
      // Skip verification actions (they go in verifications tab)
      if (actionDef.action_type === 'verification') return;
      
      const actionType = actionDef.action_type || category;
      
      if (!groupMap[actionType]) {
        groupMap[actionType] = [];
      }
      
      groupMap[actionType].push({
        type: 'action',
        label: actionDef.label,
        icon: TouchAppIcon,
        color: '#f97316', // orange - distinguishable from failure (red)
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

  // Convert groupMap to array of groups with formatted names and sort commands in each group
  const groups = Object.entries(groupMap).map(([actionType, commands]) => ({
    groupName: formatGroupName(actionType),
    commands: sortCommands(commands)
  }));

  const totalActions = groups.reduce((sum, g) => sum + g.commands.length, 0);
  console.log(`[@toolboxBuilder] Extracted ${totalActions} actions in ${groups.length} groups`);
  
  return groups;
}

/**
 * Extract verification groups from DeviceDataContext availableVerificationTypes
 * Groups verifications by verification_type (audio, video, image, text, etc.)
 */
function extractVerificationGroups(availableVerifications: Verifications) {
  const groups: any[] = [];

  if (!availableVerifications) {
    console.log(`[@toolboxBuilder] No verifications provided`);
    return groups;
  }

  // Each verification type becomes a group
  Object.entries(availableVerifications).forEach(([verificationType, verifications]) => {
    if (!Array.isArray(verifications) || verifications.length === 0) return;
    
    const commands = verifications.map((verificationDef: any) => ({
      type: 'verification',
      label: verificationDef.description || verificationDef.command,
      icon: VerifiedIcon,
      color: '#3b82f6', // blue - distinguishable from success (green)
      outputs: ['success', 'failure'],
      defaultData: {
        command: verificationDef.command,
        verification_type: verificationDef.verification_type || verificationType,
        params: { ...verificationDef.params },
      },
      description: verificationDef.description || `Verify ${verificationDef.command}`
    }));

    groups.push({
      groupName: formatGroupName(verificationType),
      commands: sortCommands(commands)
    });
  });

  const totalVerifications = groups.reduce((sum, g) => sum + g.commands.length, 0);
  console.log(`[@toolboxBuilder] Extracted ${totalVerifications} verifications in ${groups.length} groups`);
  
  return groups;
}

/**
 * Format group name for display (convert snake_case to Title Case)
 */
function formatGroupName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}
