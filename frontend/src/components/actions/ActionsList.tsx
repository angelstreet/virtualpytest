import { Box } from '@mui/material';
import React from 'react';

import { useDeviceData } from '../../contexts/device/DeviceDataContext';
import { Action } from '../../types/pages/Navigation_Types';

import { ActionItem } from './ActionItem';

interface ActionsListProps {
  actions: Action[];
  onActionsUpdate: (actions: Action[]) => void;
}

export type { ActionsListProps };

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

    if (!selectedAction) {
      console.warn('[ActionsList] No action found for ID:', actionId);
      return;
    }

    const updatedActions = actions.map((action, i) => {
      if (i === index) {
        return {
          ...action,
          command: selectedAction.command,
          params: { ...selectedAction.params },
          device_model: selectedAction.device_model,
          action_type: selectedAction.action_type,
          verification_type: selectedAction.verification_type,
        };
      }
      return action;
    });
    onActionsUpdate(updatedActions);
  };

  const handleUpdateAction = (index: number, updates: Partial<Action>) => {
    const updatedActions = actions.map((action, i) => {
      if (i === index) {
        return { ...action, ...updates } as Action;
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
          key={index}
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
