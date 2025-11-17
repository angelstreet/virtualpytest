import { useCallback, useState, useEffect, useMemo, useRef } from 'react';

import { Host } from '../../types/common/Host_Types';
import { NodeForm, UINavigationNode } from '../../types/pages/Navigation_Types';
import { Verification } from '../../types/verification/Verification_Types';
import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { useVerification } from '../verification/useVerification';
import { useNavigation } from '../../contexts/navigation/NavigationContext';
import { useNavigationPreviewCache } from '../../contexts/navigation/NavigationPreviewCacheContext';

export interface UseNodeEditProps {
  isOpen: boolean;
  nodeForm: NodeForm | null;
  setNodeForm: (form: NodeForm) => void;
  selectedHost?: Host;
  isControlActive?: boolean;
}

export const useNodeEdit = ({
  isOpen,
  nodeForm,
  setNodeForm,
  selectedHost,
  isControlActive = false,
}: UseNodeEditProps) => {
  // Get device data context for model references
  const { getModelReferences, referencesLoading, references } = useDeviceData();
  
  // Get navigation context for save and treeId
  const { userInterface, saveNodeWithStateUpdate, treeId } = useNavigation();
  
  // Get preview cache context for invalidation
  const { invalidateTree } = useNavigationPreviewCache();

  // Use userinterface name for reference lookup
  const referenceKey = userInterface?.name;

  // Get model references using the userinterface name
  // IMPORTANT: Must depend on references state to re-render when references are added
  const modelReferences = useMemo(() => {
    if (!referenceKey) return {};
    return getModelReferences(referenceKey);
  }, [getModelReferences, referenceKey, references]);

  // Verification hook for managing verifications
  const verification = useVerification({
    captureSourcePath: undefined,
    userinterfaceName: referenceKey,  // Pass userinterface name for reference resolution
    verificationPassCondition: nodeForm?.verification_pass_condition || 'all',  // Pass from nodeForm
  });

  // Local state for dialog-specific concerns
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Fix loop: Use a ref to track if we've already initialized, preventing re-calls during the same open session.
  // Also, use shallow equality for verifications dep to avoid triggering on new array references.
  const initializedRef = useRef(false);

  useEffect(() => {
    if (isOpen && nodeForm?.verifications && !initializedRef.current) {
      console.log('[useNodeEdit] Initializing verifications from nodeForm:', nodeForm.verifications);
      verification.handleVerificationsChange(nodeForm.verifications);
      initializedRef.current = true;
    } else if (isOpen) {
      console.log('[useNodeEdit] Dialog opened but no verifications in nodeForm:', nodeForm);
    }

    // Reset ref when dialog closes
    return () => {
      if (!isOpen) {
        initializedRef.current = false;
      }
    };
  }, [isOpen, nodeForm, verification]); // Removed modelReferences dependency

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setSaveSuccess(false);
      // Don't clear verification state immediately to preserve test results
      // Let the user see results before dialog closes
      setTimeout(() => {
        verification.handleVerificationsChange([]);
      }, 100);
    }
  }, [isOpen, verification]);

  // Handle verification changes
  // In handleVerificationsChange, reuse the existing verifications array if unchanged to avoid new references.
  // This prevents unnecessary effect triggers.
  const handleVerificationsChange = useCallback(
    (newVerifications: Verification[]) => {
      if (!nodeForm) return;

      console.log('[useNodeEdit] Verification changes:', newVerifications);

      // Check if verifications actually changed (shallow compare)
      const isSame = JSON.stringify(nodeForm.verifications) === JSON.stringify(newVerifications);
      if (isSame) return; // Skip update to break potential loops

      setNodeForm({
        ...nodeForm,
        verifications: newVerifications, // Assume caller provides stable reference; don't create new array here
      });
      verification.handleVerificationsChange(newVerifications);
    },
    [nodeForm, setNodeForm, verification],
  );

  // Handle save operation - INCREMENTAL CACHE UPDATE (no rebuild)
  const handleSave = useCallback(async () => {
    if (!nodeForm) {
      console.error('[useNodeEdit] Cannot save: nodeForm is null');
      return;
    }
    
    try {
      // 1. Save to database via context
      await saveNodeWithStateUpdate(nodeForm);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      
      // 2. Update cache incrementally on all hosts (no rebuild)
      if (treeId) {
        console.log('[useNodeEdit] Updating node in cache for tree:', treeId);
        const { buildServerUrl } = await import('../../utils/buildUrlUtils');
        
        // Call server to update node in cache on all hosts (buildServerUrl adds team_id automatically)
        const response = await fetch(buildServerUrl(`/server/navigation/cache/update-node`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            node: nodeForm,
            tree_id: treeId
          })
        });
        
        if (!response.ok) {
          console.error('[useNodeEdit] Failed to update node in cache:', response.statusText);
        } else {
          const result = await response.json();
          console.log('[useNodeEdit] ✅ Node updated in cache (incremental):', result);
        }
        
        // 3. Invalidate preview cache since node data changed
        invalidateTree(treeId);
        console.log('[useNodeEdit] 🗑️ Preview cache invalidated for tree:', treeId);
      }
    } catch (error) {
      console.error('[useNodeEdit] Failed to save node or update cache:', error);
      throw error;
    }
  }, [nodeForm, saveNodeWithStateUpdate, treeId, invalidateTree]);

  // Validate form
  const isFormValid = useCallback(
    (form: NodeForm | null) => {
      if (!form?.label?.trim()) return false;

      return verification.verifications.every((verificationItem) => {
        if (!verificationItem.command) return true;

        if (verificationItem.verification_type === 'image') {
          return Boolean(verificationItem.params?.image_path);
        } else if (verificationItem.verification_type === 'text') {
          return Boolean(verificationItem.params?.text);
        }

        return true;
      });
    },
    [verification.verifications],
  );


  // Get parent names from parent IDs
  const getParentNames = useCallback((parentIds: string[], nodes: UINavigationNode[]): string => {
    if (!parentIds || parentIds.length === 0) return 'None';
    if (!nodes || !Array.isArray(nodes)) return 'None';

    const parentNames = parentIds.map((id) => {
      const parentNode = nodes.find((node) => node.id === id);
      return parentNode ? parentNode.data.label : id;
    });

    return parentNames.join(' > ');
  }, []);

  // Check button visibility
  const getButtonVisibility = useCallback(() => {
    return {
      canRunGoto: isControlActive && Boolean(selectedHost),
      canTest: isControlActive && Boolean(selectedHost) && verification.verifications.length > 0,
    };
  }, [isControlActive, selectedHost, verification.verifications.length]);

  return {
    // Verification
    verification,
    handleVerificationsChange,

    // Model references for verification dropdown
    modelReferences,
    referencesLoading,

    // Form validation and actions
    handleSave,
    isFormValid,
    saveSuccess,


    // Utilities
    getParentNames,
    getButtonVisibility,
  };
};
