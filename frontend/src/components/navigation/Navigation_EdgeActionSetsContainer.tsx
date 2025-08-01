import React, { useMemo } from 'react';
import { useReactFlow } from 'reactflow';

import { Host } from '../../types/common/Host_Types';
import { UINavigationEdge, EdgeForm } from '../../types/pages/Navigation_Types';
import { ActionSetPanel } from './Navigation_ActionSetPanel';

interface EdgeActionSetsContainerProps {
  selectedEdge: UINavigationEdge;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
  setEdgeForm: React.Dispatch<React.SetStateAction<EdgeForm>>;
  setIsEdgeDialogOpen: (open: boolean) => void;

  // Device control props
  isControlActive?: boolean;
  selectedHost?: Host;
  selectedDeviceId?: string;

  // Add props for passing labels to the edit dialog
  onEditWithLabels?: (fromLabel: string, toLabel: string) => void;
  
  // Current edge form state (for running updated actions)
  currentEdgeForm?: EdgeForm | null;
}

export const EdgeActionSetsContainer: React.FC<EdgeActionSetsContainerProps> = React.memo(({
  selectedEdge,
  onClose,
  onEdit,
  onDelete: _onDelete,
  setEdgeForm: _setEdgeForm,
  setIsEdgeDialogOpen: _setIsEdgeDialogOpen,
  isControlActive = false,
  selectedHost,
  selectedDeviceId,
  onEditWithLabels,
  currentEdgeForm: _currentEdgeForm,
}) => {
  const { getNodes } = useReactFlow();

  // Get actual node labels for from/to display
  const { fromLabel, toLabel } = useMemo(() => {
    const nodes = getNodes();
    const sourceNode = nodes.find((node) => node.id === selectedEdge.source);
    const targetNode = nodes.find((node) => node.id === selectedEdge.target);

    return {
      fromLabel: sourceNode?.data?.label || selectedEdge.source,
      toLabel: targetNode?.data?.label || selectedEdge.target,
    };
  }, [getNodes, selectedEdge.source, selectedEdge.target]);

  // Note: edgeHook removed as it's not needed for this component

  // Get action sets from edge - STRICT: NO LEGACY SUPPORT
  const actionSets = useMemo(() => {
    if (!selectedEdge.data?.action_sets) {
      throw new Error("Edge missing action_sets - migration incomplete");
    }
    return selectedEdge.data.action_sets;
  }, [selectedEdge]);

  const defaultActionSetId = selectedEdge.data?.default_action_set_id;
  
  // Strict validation - NO LEGACY SUPPORT
  if (!defaultActionSetId) {
    throw new Error("Edge missing default_action_set_id - migration incomplete");
  }

  // Handle edit for specific action set
  const handleEdit = () => {
    if (onEditWithLabels) {
      onEditWithLabels(fromLabel, toLabel);
    } else {
      onEdit();
    }
  };

  // If no action sets, show error message
  if (actionSets.length === 0) {
    return (
      <div style={{
        position: 'fixed',
        top: '120px',
        right: '20px',
        width: '400px',
        padding: '16px',
        backgroundColor: '#ffebee',
        border: '1px solid #f44336',
        borderRadius: '8px',
        zIndex: 1000,
      }}>
        <p style={{ margin: 0, color: '#d32f2f' }}>
          Error: Edge missing action_sets structure. Migration may be incomplete.
        </p>
        <button onClick={onClose} style={{ marginTop: '8px', padding: '4px 8px' }}>
          Close
        </button>
      </div>
    );
  }

  // Render one panel per action set
  return (
    <>
      {actionSets.map((actionSet: any, index: number) => (
        <ActionSetPanel
          key={`${selectedEdge.id}-${actionSet.id}`}
          selectedEdge={selectedEdge}
          actionSet={actionSet}
          isDefault={actionSet.id === defaultActionSetId}
          panelIndex={index}
          onClose={index === 0 ? onClose : () => {}} // Only first panel can close all
          onEdit={handleEdit}
          fromLabel={fromLabel}
          toLabel={toLabel}
          isControlActive={isControlActive}
          selectedHost={selectedHost}
          selectedDeviceId={selectedDeviceId}
        />
      ))}
    </>
  );
});

EdgeActionSetsContainer.displayName = 'EdgeActionSetsContainer';