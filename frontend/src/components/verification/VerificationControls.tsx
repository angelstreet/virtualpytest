import React, { useMemo } from 'react';
import { Box } from '@mui/material';

import { Verification } from '../../types/verification/Verification_Types';
import { ParamDefinition } from '../../types/paramTypes';
import { DynamicParamForm } from '../testcase/dialogs/DynamicParamForm';

interface VerificationControlsProps {
  verification: Verification;
  index: number;
  onUpdateVerification: (index: number, updates: Partial<Verification>) => void;
  availableVerifications?: Record<string, any>;
}

export const VerificationControls: React.FC<VerificationControlsProps> = ({
  verification,
  index,
  onUpdateVerification,
  availableVerifications,
}) => {
  // Find typed params for this verification
  const typedParams = useMemo(() => {
    if (!availableVerifications || !verification.command) return null;
    
    // Find the verification definition from available verifications
    const verificationDef = Object.values(availableVerifications)
      .flat()
      .find((v: any) => v.command === verification.command);
    
    if (!verificationDef?.params) return null;
    
    // Check if params have typed structure (has 'type', 'required', 'default' fields)
    const firstParam = Object.values(verificationDef.params)[0] as any;
    if (firstParam && typeof firstParam === 'object' && 'type' in firstParam && 'required' in firstParam) {
      return verificationDef.params as Record<string, ParamDefinition>;
    }
    
    return null;
  }, [availableVerifications, verification.command]);

  // Always use DynamicParamForm - no fallback
  if (!typedParams) {
    return null; // No params to display
  }

  return (
    <Box sx={{ mb: 0.5 }}>
      <DynamicParamForm
        params={typedParams}
        values={verification.params || {}}
        onChange={(paramName, value) => {
          onUpdateVerification(index, {
            params: {
              ...verification.params,
              [paramName]: value,
            },
          });
        }}
        onAreaSelect={(paramName) => {
          // TODO: Implement area selection dialog
          console.log('Area selection requested for', paramName);
        }}
      />
    </Box>
  );
};
