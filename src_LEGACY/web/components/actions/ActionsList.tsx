import { Box } from '@mui/material';
import React from 'react';

import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { EdgeAction } from '../../types/pages/Navigation_Types';

import { ActionItem } from './ActionItem';

interface ActionsListProps {
  actions: EdgeAction[];
  onActionsUpdate: (actions: EdgeAction[]) => void;
}

export const ActionsList: React.FC<ActionsListProps> = ({ actions, onActionsUpdate }) => {
  const { getAvailableActions } = useDeviceData();
  const availableActions = getAvailableActions();

  const handleActionSelect = (index: number, actionId: string) => {
    // Find the selected action from available actions by ID
    let selectedAction: any = undefined;

    for (const actions of Object.values(availableActions)) {
      if (!Array.isArray(actions)) continue;

      const action = actions.find((a) => a.id === actionId);
      if (action) {
        selectedAction = action;
        break;
      }
    }

    const updatedActions = actions.map((action, i) => {
      if (i === index) {
        return {
          ...action,
          id: selectedAction.id,
          command: selectedAction.command,
          label: selectedAction.label,
          params: { ...selectedAction.params },
        };
      }
      return action;
    });
    onActionsUpdate(updatedActions);
  };

  const handleUpdateAction = (index: number, updates: Partial<EdgeAction>) => {
    const updatedActions = actions.map((action, i) => {
      if (i === index) {
        return { ...action, ...updates };
      }
      return action;
    });
    onActionsUpdate(updatedActions);
  };

  const handleRemoveAction = (index: number) => {
    const updatedActions = actions.filter((_, i) => i !== index);
    onActionsUpdate(updatedActions);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updatedActions = [...actions];
    [updatedActions[index - 1], updatedActions[index]] = [
      updatedActions[index],
      updatedActions[index - 1],
    ];
    onActionsUpdate(updatedActions);
  };

  const handleMoveDown = (index: number) => {
    if (index === actions.length - 1) return;
    const updatedActions = [...actions];
    [updatedActions[index], updatedActions[index + 1]] = [
      updatedActions[index + 1],
      updatedActions[index],
    ];
    onActionsUpdate(updatedActions);
  };

  return (
    <Box>
      {actions.map((action, index) => (
        <ActionItem
          key={action.id}
          action={action}
          index={index}
          availableActions={availableActions}
          onActionSelect={handleActionSelect}
          onUpdateAction={handleUpdateAction}
          onRemoveAction={handleRemoveAction}
          onMoveUp={handleMoveUp}
          onMoveDown={handleMoveDown}
          canMoveUp={index > 0}
          canMoveDown={index < actions.length - 1}
        />
      ))}
    </Box>
  );
};
