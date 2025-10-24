/**
 * Navigation and Actions API Service
 * 
 * Provides helper functions for fetching available navigation nodes,
 * actions, and verifications for TestCase Builder dropdowns.
 */

import { apiClient } from './apiClient';

export interface NavigationNode {
  id: string;
  label: string;
  type?: string;
}

export interface NavigationTree {
  tree_id: string;
  tree_name: string;
  userinterface_name: string;
  nodes?: NavigationNode[];
}

export interface UserInterface {
  id: string;
  userinterface_name: string;
  display_name?: string;
}

export interface ActionCommand {
  command: string;
  description: string;
  params?: Record<string, any>;
}

/**
 * Fetch all user interfaces for a team
 */
export async function getUserInterfaces(teamId: string): Promise<{ success: boolean; userinterfaces: UserInterface[] }> {
  try {
    const response = await apiClient.get<{ success: boolean; userinterfaces: UserInterface[] }>(
      '/server/userinterface/getAllUserInterfaces',
      { team_id: teamId }
    );
    return response;
  } catch (error) {
    console.error('[testcaseBuilderApi] Error fetching user interfaces:', error);
    return { success: false, userinterfaces: [] };
  }
}

/**
 * Fetch full navigation tree with nodes
 */
export async function getNavigationTree(treeId: string, teamId: string): Promise<{ success: boolean; tree?: any }> {
  try {
    const response = await apiClient.get<any>(
      `/server/navigationTrees/${treeId}/full`,
      { team_id: teamId }
    );
    return { success: true, tree: response };
  } catch (error) {
    console.error('[testcaseBuilderApi] Error fetching navigation tree:', error);
    return { success: false };
  }
}

/**
 * Fetch all navigation trees for a team
 */
export async function getAllNavigationTrees(teamId: string): Promise<{ success: boolean; trees: any[] }> {
  try {
    const response = await apiClient.get<{ success: boolean; trees: any[] }>(
      '/server/navigationTrees',
      { team_id: teamId }
    );
    return response;
  } catch (error) {
    console.error('[testcaseBuilderApi] Error fetching navigation trees:', error);
    return { success: false, trees: [] };
  }
}

/**
 * Get navigation nodes for a specific userinterface
 * Fetches the root tree for the interface and returns its nodes
 */
export async function getNavigationNodesForInterface(
  userinterfaceName: string,
  teamId: string
): Promise<{ success: boolean; nodes: NavigationNode[] }> {
  try {
    // First, get all trees for the team
    const treesResponse = await getAllNavigationTrees(teamId);
    
    if (!treesResponse.success || !treesResponse.trees) {
      return { success: false, nodes: [] };
    }
    
    // Find tree matching the userinterface_name
    const matchingTree = treesResponse.trees.find(
      (tree: any) => tree.userinterface_name === userinterfaceName
    );
    
    if (!matchingTree) {
      console.warn(`[testcaseBuilderApi] No tree found for userinterface: ${userinterfaceName}`);
      return { success: false, nodes: [] };
    }
    
    // Fetch full tree data with nodes
    const treeResponse = await getNavigationTree(matchingTree.tree_id, teamId);
    
    if (!treeResponse.success || !treeResponse.tree) {
      return { success: false, nodes: [] };
    }
    
    const nodes = treeResponse.tree.nodes || [];
    return {
      success: true,
      nodes: nodes.map((node: any) => ({
        id: node.id,
        label: node.label || node.id,
        type: node.type,
      })),
    };
  } catch (error) {
    console.error('[testcaseBuilderApi] Error fetching navigation nodes:', error);
    return { success: false, nodes: [] };
  }
}

/**
 * Get available action commands
 * These are device commands that can be executed
 */
export async function getAvailableActions(): Promise<{ success: boolean; actions: ActionCommand[] }> {
  // Hard-coded list of common actions (can be made dynamic later)
  const actions: ActionCommand[] = [
    { command: 'press_ok', description: 'Press OK button' },
    { command: 'press_back', description: 'Press Back button' },
    { command: 'press_home', description: 'Press Home button' },
    { command: 'press_up', description: 'Press Up button' },
    { command: 'press_down', description: 'Press Down button' },
    { command: 'press_left', description: 'Press Left button' },
    { command: 'press_right', description: 'Press Right button' },
    { command: 'press_menu', description: 'Press Menu button' },
    { command: 'press_power', description: 'Press Power button' },
    { command: 'press_mute', description: 'Press Mute button' },
    { command: 'press_volume_up', description: 'Volume Up' },
    { command: 'press_volume_down', description: 'Volume Down' },
    { command: 'press_channel_up', description: 'Channel Up' },
    { command: 'press_channel_down', description: 'Channel Down' },
    { command: 'press_play', description: 'Press Play button' },
    { command: 'press_pause', description: 'Press Pause button' },
    { command: 'press_stop', description: 'Press Stop button' },
    { command: 'press_rewind', description: 'Press Rewind button' },
    { command: 'press_fast_forward', description: 'Press Fast Forward button' },
    { command: 'click_element', description: 'Click UI element', params: { element_id: 'string' } },
    { command: 'send_text', description: 'Send text input', params: { text: 'string' } },
    { command: 'wait', description: 'Wait for duration', params: { seconds: 'number' } },
  ];
  
  return { success: true, actions };
}

/**
 * Get available verification types
 */
export async function getAvailableVerifications(): Promise<{ success: boolean; verifications: any[] }> {
  // Hard-coded list of verification types (can be made dynamic later)
  const verifications = [
    { type: 'text', description: 'Verify text on screen', params: ['text', 'threshold'] },
    { type: 'image', description: 'Verify image reference', params: ['reference', 'threshold'] },
    { type: 'audio', description: 'Verify audio playing', params: ['threshold'] },
    { type: 'black_screen', description: 'Verify black screen', params: ['threshold'] },
    { type: 'freeze_screen', description: 'Verify not frozen', params: ['threshold'] },
  ];
  
  return { success: true, verifications };
}

