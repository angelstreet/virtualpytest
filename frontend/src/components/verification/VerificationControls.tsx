import React from 'react';
import { Box, TextField } from '@mui/material';

import { Verification } from '../../types/verification/Verification_Types';

interface VerificationControlsProps {
  verification: Verification;
  index: number;
  onUpdateVerification: (index: number, updates: Partial<Verification>) => void;
}

export const VerificationControls: React.FC<VerificationControlsProps> = ({
  verification,
  index,
  onUpdateVerification,
}) => {
  return (
    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', mb: 0, px: 0, mx: 0 }}>
      {verification.command && (
        <TextField
          size="small"
          type="number"
          label="Timeout"
          value={verification.params?.timeout !== undefined ? verification.params.timeout : 0}
          autoComplete="off"
          onChange={(e) => {
            const value = parseFloat(e.target.value);
            onUpdateVerification(index, {
              params: {
                ...verification.params,
                timeout: isNaN(value) ? 0 : value,
              },
            });
          }}
          sx={{
            width: 80,
            '& .MuiInputBase-input': {
              padding: '4px 8px',
              fontSize: '0.8rem',
            },
          }}
          inputProps={{ min: 0, max: 60, step: 0.5 }}
        />
      )}

      {verification.command && verification.verification_type === 'adb' && (
        <TextField
          size="small"
          label="Element Criteria"
          placeholder="text=Button"
          value={
            typeof verification.params?.search_term === 'string'
              ? verification.params.search_term
              : ''
          }
          autoComplete="off"
          onChange={(e) =>
            onUpdateVerification(index, {
              params: { ...verification.params, search_term: e.target.value },
            })
          }
          sx={{
            flex: 1,
            '& .MuiInputBase-input': {
              padding: '4px 8px',
              fontSize: '0.8rem',
            },
          }}
        />
      )}

      {verification.command &&
        (verification.verification_type === 'image' ||
          verification.verification_type === 'text') && (
          <TextField
            size="small"
            type="number"
            label="Threshold"
            value={verification.params?.threshold || 0.8}
            autoComplete="off"
            onChange={(e) =>
              onUpdateVerification(index, {
                params: {
                  ...verification.params,
                  threshold: parseFloat(e.target.value) || 0.8,
                },
              })
            }
            sx={{
              width: 80,
              '& .MuiInputBase-input': {
                padding: '4px 8px',
                fontSize: '0.8rem',
              },
            }}
            inputProps={{ min: 0.1, max: 1.0, step: 0.05 }}
          />
        )}

      {verification.command && verification.verification_type === 'text' && (
        <TextField
          size="small"
          type="number"
          label="Confidence"
          value={verification.params?.confidence || 0.8}
          autoComplete="off"
          onChange={(e) =>
            onUpdateVerification(index, {
              params: {
                ...verification.params,
                confidence: parseFloat(e.target.value) || 0.8,
              },
            })
          }
          sx={{
            width: 80,
            '& .MuiInputBase-input': {
              padding: '4px 8px',
              fontSize: '0.8rem',
            },
          }}
          inputProps={{ min: 0.1, max: 1.0, step: 0.05 }}
        />
      )}

      {/* Area coordinates are loaded from database - no manual input needed */}
    </Box>
  );
};
