/**
 * useTestCaseBuilder Hook
 * 
 * Handles fetching available interfaces, navigation nodes, actions, and verifications
 * for TestCase Builder dropdowns and configuration.
 * Follows Navigation architecture pattern with buildServerUrl + fetch directly.
 */

import { useCallback } from 'react';
import { buildServerUrl } from '../../utils/buildUrlUtils';

export interface NavigationNode {
  id: string;
  label: string;
  type?: string;
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

export const useTestCaseBuilder = () => {
  
  /**
   * Fetch all user interfaces for a team
   */
  const getUserInterfaces = useCallback(async (): Promise<{ success: boolean; userinterfaces: UserInterface[] }> => {
    try {
      const response = await fetch(buildServerUrl('/server/userinterface/getAllUserInterfaces'));
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseBuilder] Error fetching user interfaces:', error);
      return { success: false, userinterfaces: [] };
    }
  }, []);

  /**
   * Fetch full navigation tree with nodes
   */
  const getNavigationTree = useCallback(async (treeId: string): Promise<{ success: boolean; tree?: any }> => {
    try {
      const response = await fetch(buildServerUrl(`/server/navigationTrees/${treeId}/full`));
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const tree = await response.json();
      return { success: true, tree };
    } catch (error) {
      console.error('[useTestCaseBuilder] Error fetching navigation tree:', error);
      return { success: false };
    }
  }, []);

  /**
   * Fetch all navigation trees for a team
   */
  const getAllNavigationTrees = useCallback(async (): Promise<{ success: boolean; trees: any[] }> => {
    try {
      const response = await fetch(buildServerUrl('/server/navigationTrees'));
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('[useTestCaseBuilder] Error fetching navigation trees:', error);
      return { success: false, trees: [] };
    }
  }, []);

  /**
   * Get navigation nodes for a specific userinterface
   * Fetches the root tree for the interface and returns its nodes
   */
  const getNavigationNodesForInterface = useCallback(async (
    userinterfaceName: string
  ): Promise<{ success: boolean; nodes: NavigationNode[] }> => {
    try {
      // First, get all trees for the team
      const treesResponse = await getAllNavigationTrees();
      
      if (!treesResponse.success || !treesResponse.trees) {
        return { success: false, nodes: [] };
      }
      
      // Find tree matching the userinterface_name
      const matchingTree = treesResponse.trees.find(
        (tree: any) => tree.userinterface_name === userinterfaceName
      );
      
      if (!matchingTree) {
        console.warn(`[useTestCaseBuilder] No tree found for userinterface: ${userinterfaceName}`);
        return { success: false, nodes: [] };
      }
      
      // Fetch full tree data with nodes
      const treeResponse = await getNavigationTree(matchingTree.tree_id);
      
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
      console.error('[useTestCaseBuilder] Error fetching navigation nodes:', error);
      return { success: false, nodes: [] };
    }
  }, [getAllNavigationTrees, getNavigationTree]);

  /**
   * Get available action commands
   * These are device commands that can be executed
   */
  const getAvailableActions = useCallback(async (): Promise<{ success: boolean; actions: ActionCommand[] }> => {
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
  }, []);

  /**
   * Get available verification types
   */
  const getAvailableVerifications = useCallback(async (): Promise<{ success: boolean; verifications: any[] }> => {
    // Hard-coded list of verification types (can be made dynamic later)
    const verifications = [
      { type: 'text', description: 'Verify text on screen', params: ['text', 'threshold'] },
      { type: 'image', description: 'Verify image reference', params: ['reference', 'threshold'] },
      { type: 'audio', description: 'Verify audio playing', params: ['threshold'] },
      { type: 'black_screen', description: 'Verify black screen', params: ['threshold'] },
      { type: 'freeze_screen', description: 'Verify not frozen', params: ['threshold'] },
    ];
    
    return { success: true, verifications };
  }, []);

  return {
    getUserInterfaces,
    getNavigationTree,
    getAllNavigationTrees,
    getNavigationNodesForInterface,
    getAvailableActions,
    getAvailableVerifications,
  };
};

