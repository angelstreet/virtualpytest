/**
 * Toolbox Builder - Build toolbox configuration from navigation data + controller actions
 * Reuses DeviceDataContext logic for actions/verifications
 */

import NavigationIcon from '@mui/icons-material/Navigation';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import VerifiedIcon from '@mui/icons-material/Verified';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PublicIcon from '@mui/icons-material/Public';
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
 * 
 * @param isControlActive - Only build toolbox when control is active (not just device selected)
 */
export function buildToolboxFromNavigationData(
  nodes: any[],
  availableActions: Actions,
  availableVerifications: Verifications,
  standardBlocks: any[],
  isControlActive: boolean = false
) {
  // Only show toolbox after taking control, not just on device selection
  if (!isControlActive) {
    console.log('[@toolboxBuilder] Control not active - toolbox not available');
    return null;
  }
  
  // Note: userInterface is optional - only nodes and availableActions are required
  if (!nodes || nodes.length === 0) {
    console.log('[@toolboxBuilder] Cannot build toolbox - no nodes provided');
    return null;
  }

  return {
    standard: {
      tabName: 'Standard',
      groups: extractStandardBlockGroups(standardBlocks.filter(b => b.category !== 'api'))
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
    },
    api: {
      tabName: 'API',
      groups: extractApiBlockGroups(standardBlocks.filter(b => b.category === 'api'))
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
          label: actionDef.label, // ✅ Preserve action label for block display
          command: actionDef.command,
          action_type: actionDef.action_type,
          params: { ...actionDef.params },
          device_model: actionDef.device_model,
          blockOutputs: actionDef.outputs || [], // ✅ Add outputs for data flow
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
      label: verificationDef.label || verificationDef.command,  // Use label (required), fallback to command
      icon: VerifiedIcon,
      color: '#3b82f6', // blue - distinguishable from success (green)
      outputs: ['success', 'failure'],
      defaultData: {
        label: verificationDef.label || verificationDef.command, // ✅ Preserve verification label for block display
        command: verificationDef.command,
        action_type: 'verification', // ✅ Required for backend routing
        verification_type: verificationDef.verification_type || verificationType,
        params: { ...verificationDef.params },
        blockOutputs: verificationDef.outputs || [], // ✅ Add outputs for data flow (getMenuInfo, etc.)
      },
      description: verificationDef.description || verificationDef.label || `Verify ${verificationDef.command}`
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

/**
 * Extract standard block groups from BuilderContext
 * Converts standard blocks from backend into toolbox format
 * 
 * EXPORTED for use in Campaign builder (which doesn't have navigation nodes)
 */
export function extractStandardBlockGroups(standardBlocks: any[]) {
  const groups: any[] = [];

  if (!standardBlocks || standardBlocks.length === 0) {
    console.log(`[@toolboxBuilder] No standard blocks provided`);
    return groups;
  }

  // Map each standard block to toolbox format
  const commands = standardBlocks.map((blockDef: any) => {
    // Extract default values from param schemas
    const defaultParams: Record<string, any> = {};
    if (blockDef.params && typeof blockDef.params === 'object') {
      for (const [key, paramSchema] of Object.entries(blockDef.params)) {
        const schema = paramSchema as any;
        // Get default value from schema
        if (schema && typeof schema === 'object' && 'default' in schema) {
          defaultParams[key] = schema.default;
        }
      }
    }

    return {
      type: blockDef.command,
      label: blockDef.label || blockDef.description || blockDef.command,  // Use short label
      icon: AccessTimeIcon, // Default icon (could be customized per block type)
      color: '#6b7280', // grey - standard operations
      outputs: ['success', 'failure'], // Standard blocks can succeed or fail
      defaultData: {
        command: blockDef.command,
        action_type: 'standard_block',
        params: defaultParams, // ← EXTRACTED DEFAULT VALUES
        paramSchema: blockDef.params || {}, // ← ADD FULL PARAM SCHEMA FOR CONFIG DIALOG
      },
      description: blockDef.description || `Execute ${blockDef.command}`  // Long description
    };
  });

  groups.push({
    groupName: 'Standard',
    commands: sortCommands(commands)
  });

  const totalBlocks = commands.length;
  console.log(`[@toolboxBuilder] Extracted ${totalBlocks} standard blocks`);
  
  return groups;
}

/**
 * Extract API block groups from standard blocks with category='api'
 * API blocks (like api_call) for Postman integration
 */
function extractApiBlockGroups(apiBlocks: any[]) {
  const groups: any[] = [];

  if (!apiBlocks || apiBlocks.length === 0) {
    console.log(`[@toolboxBuilder] No API blocks provided`);
    return groups;
  }

  // Map each API block to toolbox format
  const commands = apiBlocks.map((blockDef: any) => {
    // Extract default values from param schemas
    const defaultParams: Record<string, any> = {};
    if (blockDef.params && typeof blockDef.params === 'object') {
      for (const [key, paramSchema] of Object.entries(blockDef.params)) {
        const schema = paramSchema as any;
        if (schema && typeof schema === 'object' && 'default' in schema) {
          defaultParams[key] = schema.default;
        }
      }
    }

    return {
      type: blockDef.command,
      label: blockDef.name || blockDef.label || blockDef.command,
      icon: blockDef.icon === '🌐' ? PublicIcon : PublicIcon, // Use globe icon
      color: '#06b6d4', // cyan - API blocks
      outputs: ['success', 'failure'],
      defaultData: {
        command: blockDef.command,
        action_type: 'api',
        params: defaultParams,
        paramSchema: blockDef.params || {},
        blockOutputs: blockDef.outputs || [
          { name: 'response', type: 'object' },
          { name: 'status_code', type: 'number' },
          { name: 'headers', type: 'object' },
        ],
      },
      description: blockDef.description || `Execute API call`
    };
  });

  groups.push({
    groupName: 'API',
    commands: sortCommands(commands)
  });

  const totalBlocks = commands.length;
  console.log(`[@toolboxBuilder] Extracted ${totalBlocks} API blocks`);
  
  return groups;
}
