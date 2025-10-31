import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
  Divider
} from '@mui/material';
import { LinkIcon, CheckCircleIcon, InfoIcon } from '@mui/x-date-pickers';

interface OutputValueDialogProps {
  open: boolean;
  onClose: () => void;
  output: {
    name: string;
    type: string;
    sourceBlockId?: string;
    sourceOutputName?: string;
  } | null;
  executionValue: any;
  blockOutputs: Record<string, Record<string, any>>;
}

const OutputValueDialog: React.FC<OutputValueDialogProps> = ({
  open,
  onClose,
  output,
  executionValue,
  blockOutputs
}) => {
  if (!output) return null;

  const hasExecutionValue = executionValue !== undefined;
  const isLinked = !!output.sourceBlockId;

  // Format value for display
  const formatValue = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  // Get source block outputs if linked
  const sourceOutputs = isLinked && output.sourceBlockId
    ? blockOutputs[output.sourceBlockId]
    : null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          bgcolor: '#1e1e1e',
          color: 'white'
        }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1,
        borderBottom: '1px solid rgba(255,255,255,0.1)'
      }}>
        <CheckCircleIcon sx={{ color: '#10b981' }} />
        Output Value: {output.name}
      </DialogTitle>

      <DialogContent sx={{ pt: 3 }}>
        {/* Output Info */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', mb: 1, display: 'block' }}>
            OUTPUT DETAILS
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={`Type: ${output.type}`}
              size="small"
              sx={{ bgcolor: 'rgba(6, 182, 212, 0.2)', color: '#06b6d4' }}
            />
            {isLinked && (
              <Chip
                icon={<LinkIcon />}
                label={`Linked: ${output.sourceBlockId} → ${output.sourceOutputName}`}
                size="small"
                sx={{ bgcolor: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }}
              />
            )}
          </Box>
        </Box>

        <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.1)' }} />

        {/* Execution Value */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', mb: 1, display: 'block' }}>
            EXECUTION VALUE
          </Typography>
          {hasExecutionValue ? (
            <Box
              sx={{
                bgcolor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: 1,
                p: 2,
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                maxHeight: '300px',
                overflowY: 'auto'
              }}
            >
              {formatValue(executionValue)}
            </Box>
          ) : (
            <Box
              sx={{
                bgcolor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 1,
                p: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
            >
              <InfoIcon sx={{ color: '#ef4444' }} />
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                No execution value available. Run the test case to see the value.
              </Typography>
            </Box>
          )}
        </Box>

        {/* Source Block Outputs (if linked) */}
        {isLinked && sourceOutputs && (
          <>
            <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.1)' }} />
            <Box>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', mb: 1, display: 'block' }}>
                SOURCE BLOCK OUTPUTS ({output.sourceBlockId})
              </Typography>
              <Box
                sx={{
                  bgcolor: 'rgba(100, 116, 139, 0.1)',
                  border: '1px solid rgba(100, 116, 139, 0.3)',
                  borderRadius: 1,
                  p: 2,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}
              >
                {formatValue(sourceOutputs)}
              </Box>
            </Box>
          </>
        )}

        {/* Default Value Info */}
        <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(100, 116, 139, 0.1)', borderRadius: 1 }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
            💡 <strong>Tip:</strong> This value is populated after execution and can be used in:
          </Typography>
          <ul style={{ margin: '8px 0 0 20px', padding: 0, color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem' }}>
            <li>Campaign chaining (passed to next script)</li>
            <li>Metadata storage (saved to database)</li>
            <li>Other block inputs (drag & drop)</li>
          </ul>
        </Box>
      </DialogContent>

      <DialogActions sx={{ borderTop: '1px solid rgba(255,255,255,0.1)', p: 2 }}>
        <Button onClick={onClose} variant="contained" sx={{ bgcolor: '#10b981', '&:hover': { bgcolor: '#059669' } }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OutputValueDialog;

