/**
 * Toolbox Builder - Extract toolbox configuration from Navigation data
 * Reuses data already loaded by NavigationEditor infrastructure
 */

import NavigationIcon from '@mui/icons-material/Navigation';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import VerifiedIcon from '@mui/icons-material/Verified';
import LoopIcon from '@mui/icons-material/Loop';

/**
 * Build dynamic toolbox configuration from loaded navigation data
 * This reuses data from NavigationEditor's loadTreeByUserInterface call
 * 
 * Returns structure matching toolboxConfig.tsx format:
 * {
 *   tabName: {
 *     tabName: string,
 *     groups: [{ groupName: string, commands: [...] }]
 *   }
 * }
 */
export function buildToolboxFromNavigationData(
  nodes: any[],
  edges: any[],
  userInterface: any
) {
  if (!nodes || !edges || !userInterface) {
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
      tabName: 'Action',
      groups: [
        {
          groupName: 'Action',
          commands: extractActionBlocks(edges)
        }
      ]
    },
    verifications: {
      tabName: 'Verifcation',
      groups: [
        {
          groupName: 'Verification',
          commands: extractVerificationBlocks(nodes)
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
      node.data?.label  // Must have a label
    )
    .map(node => ({
      type: 'navigation',
      label: node.data.label,  // Show node name in toolbox (e.g., "home", "live_tv")
      icon: NavigationIcon,
      color: '#8b5cf6',
      outputs: ['success', 'failure'],
      defaultData: {
        target_node_label: node.data.label,  // This is what UniversalBlock expects
        target_node_id: node.id,
        label: node.data.label  // Also store as 'label' for compatibility
      },
      description: `Navigate to ${node.data.label}`
    }));

  console.log(`[@toolboxBuilder] Extracted ${navigationNodes.length} navigation nodes`);
  return navigationNodes;
}

/**
 * Extract action blocks from edges' action_sets
 * Edges contain action_sets with arrays of actions
 */
function extractActionBlocks(edges: any[]) {
  const actionsMap = new Map();

  edges.forEach(edge => {
    edge.data?.action_sets?.forEach((actionSet: any) => {
      actionSet.actions?.forEach((action: any) => {
        const key = action.command;
        if (!actionsMap.has(key)) {
          // Create human-readable label
          const label = action.command
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .trim()
            .split(' ')
            .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');

          actionsMap.set(key, {
            type: 'action',
            label,
            icon: TouchAppIcon,
            color: '#ef4444',
            outputs: ['success', 'failure'],
            defaultData: {
              command: action.command,
              action_type: action.action_type || 'remote',
              params: action.params || {}
            },
            description: `Execute ${label}`
          });
        }
      });
    });
  });

  const actions = Array.from(actionsMap.values());
  console.log(`[@toolboxBuilder] Extracted ${actions.length} unique actions from edges`);
  return actions;
}

/**
 * Extract verification blocks from nodes' verifications
 * Nodes contain verification arrays
 */
function extractVerificationBlocks(nodes: any[]) {
  const verificationsMap = new Map();

  nodes.forEach(node => {
    node.data?.verifications?.forEach((verification: any) => {
      const key = verification.command;
      if (!verificationsMap.has(key)) {
        // Create human-readable label
        const label = verification.command
          .replace(/([A-Z])/g, ' $1')
          .trim()
          .split(' ')
          .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ');

        verificationsMap.set(key, {
          type: 'verification',
          label,
          icon: VerifiedIcon,
          color: '#10b981',
          outputs: ['success', 'failure'],
          defaultData: {
            command: verification.command,
            verification_type: verification.verification_type || 'image',
            params: verification.params || {}
          },
          description: `Verification ${label}`
        });
      }
    });
  });

  const verifications = Array.from(verificationsMap.values());
  console.log(`[@toolboxBuilder] Extracted ${verifications.length} unique verifications from nodes`);
  return verifications;
}

