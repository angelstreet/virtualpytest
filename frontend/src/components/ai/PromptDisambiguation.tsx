/**
 * Prompt Disambiguation Component
 * 
 * Standalone modal component for resolving ambiguous navigation node references.
 * Supports two modes:
 * - Select mode: Choose from suggested matches
 * - Edit mode: Manually type/select nodes
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Checkbox,
  FormControlLabel,
  TextField,
  Chip,
  Paper,
  Modal,
  Backdrop,
} from '@mui/material';
import { getZIndex } from '../../utils/zIndexUtils';
import type { Ambiguity, AutoCorrection } from '../../types/aiagent/AIDisambiguation_Types';

interface Props {
  ambiguities: Ambiguity[];
  autoCorrections?: AutoCorrection[];
  availableNodes?: string[];
  onResolve: (selections: Record<string, string>, saveToDb: boolean) => void;
  onCancel: () => void;
}

export const PromptDisambiguation: React.FC<Props> = ({
  ambiguities,
  autoCorrections = [],
  availableNodes = [],
  onResolve,
  onCancel
}) => {
  const [mode, setMode] = useState<'select' | 'edit'>('select');
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [saveToDb, setSaveToDb] = useState(true);
  const [editedText, setEditedText] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Check if all ambiguities have selections
  const allSelected = ambiguities.every(a => selections[a.original]);

  // Filter available nodes for search
  const filteredNodes = searchTerm
    ? availableNodes.filter(node => node.toLowerCase().includes(searchTerm.toLowerCase())).slice(0, 20)
    : availableNodes.slice(0, 20);

  const handleProceed = () => {
    if (mode === 'edit') {
      // Parse edited text (simple format: node names, one per line)
      const parsed = parseEditedSelections(editedText);
      onResolve(parsed, saveToDb);
    } else {
      onResolve(selections, saveToDb);
    }
  };

  const insertNode = (node: string) => {
    setEditedText(prev => prev + (prev ? '\n' : '') + node);
  };

  return (
    <Modal
      open
      onClose={onCancel}
      closeAfterTransition
      slots={{ backdrop: Backdrop }}
      slotProps={{
        backdrop: {
          timeout: 300,
          sx: {
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            zIndex: getZIndex('AI_DISAMBIGUATION_MODAL') - 1,
          }
        }
      }}
    >
      <Box
        sx={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: getZIndex('AI_DISAMBIGUATION_MODAL'),
          width: '90%',
          maxWidth: 700,
          maxHeight: '90vh',
          overflowY: 'auto',
          bgcolor: 'background.paper',
          borderRadius: 2,
          boxShadow: 24,
          outline: 'none',
        }}
      >
        {/* Header */}
        <Box sx={{ p: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
            🤔 Clarify Navigation Nodes
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Some references in your prompt are ambiguous. Please select the correct nodes.
          </Typography>
        </Box>

        {/* Content */}
        <Box sx={{ p: 3 }}>
          {/* Auto-corrections banner */}
          {autoCorrections.length > 0 && (
            <Paper
              elevation={0}
              sx={{
                mb: 3,
                p: 2,
                bgcolor: 'success.light',
                border: '1px solid',
                borderColor: 'success.main',
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.dark', mb: 1 }}>
                ✅ Already auto-applied:
              </Typography>
              {autoCorrections.map((c, i) => (
                <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace', color: 'success.dark' }}>
                    "{c.from}"
                  </Typography>
                  <Typography variant="body2" component="span">→</Typography>
                  <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace', fontWeight: 'bold', color: 'success.dark' }}>
                    "{c.to}"
                  </Typography>
                  {c.source === 'learned' && (
                    <Chip label="🎓 Learned" size="small" color="success" sx={{ height: 20 }} />
                  )}
                </Box>
              ))}
            </Paper>
          )}

          {mode === 'select' ? (
            <>
              {/* Selection mode */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
                {ambiguities.map((amb, idx) => (
                  <Paper key={idx} elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="body2" sx={{ mb: 2, fontWeight: 500 }}>
                      What did you mean by{' '}
                      <Typography component="span" sx={{ color: 'primary.main', fontFamily: 'monospace', fontWeight: 'bold' }}>
                        "{amb.original}"
                      </Typography>
                      ?
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {amb.suggestions.map(sugg => (
                        <Button
                          key={sugg}
                          onClick={() => setSelections({ ...selections, [amb.original]: sugg })}
                          variant={selections[amb.original] === sugg ? 'contained' : 'outlined'}
                          sx={{
                            justifyContent: 'flex-start',
                            textTransform: 'none',
                            fontFamily: 'monospace',
                            py: 1.5,
                          }}
                        >
                          {sugg}
                        </Button>
                      ))}
                    </Box>
                  </Paper>
                ))}
              </Box>

              {/* Options */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={saveToDb}
                      onChange={(e) => setSaveToDb(e.target.checked)}
                    />
                  }
                  label={<Typography variant="body2">Remember my choices for next time</Typography>}
                />
                
                <Button
                  onClick={() => setMode('edit')}
                  variant="text"
                  size="small"
                  sx={{ textTransform: 'none' }}
                >
                  ✏️ Edit manually instead
                </Button>
              </Box>
            </>
          ) : (
            <>
              {/* Edit mode */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Type node names or click to insert:
                </Typography>
                <TextField
                  multiline
                  rows={4}
                  fullWidth
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  placeholder="Type node names, one per line..."
                  sx={{
                    '& textarea': {
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    }
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  Tip: Type node names directly or use the chips below
                </Typography>
              </Box>

              {/* Node search */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Available nodes:
                </Typography>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="🔍 Search nodes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  sx={{ mb: 2 }}
                />
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: 'grey.50',
                    border: '1px solid',
                    borderColor: 'divider',
                    maxHeight: 200,
                    overflowY: 'auto',
                  }}
                >
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {filteredNodes.map(node => (
                      <Chip
                        key={node}
                        label={node}
                        onClick={() => insertNode(node)}
                        clickable
                        size="small"
                        sx={{ fontFamily: 'monospace' }}
                      />
                    ))}
                  </Box>
                  {filteredNodes.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                      No nodes found matching "{searchTerm}"
                    </Typography>
                  )}
                </Paper>
              </Box>

              <Button
                onClick={() => setMode('select')}
                variant="text"
                size="small"
                sx={{ textTransform: 'none', mb: 2 }}
              >
                ← Back to selection mode
              </Button>
            </>
          )}
        </Box>

        {/* Footer */}
        <Box
          sx={{
            p: 3,
            borderTop: '1px solid',
            borderColor: 'divider',
            bgcolor: 'grey.50',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 2,
          }}
        >
          <Button
            onClick={onCancel}
            variant="outlined"
            sx={{ textTransform: 'none' }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleProceed}
            disabled={mode === 'select' && !allSelected}
            variant="contained"
            sx={{ textTransform: 'none', minWidth: 180 }}
          >
            Proceed with Execution
          </Button>
        </Box>
      </Box>
    </Modal>
  );
};

/**
 * Parse edited text selections
 * Simple format: node names, one per line
 * Or: "original phrase → selected node"
 */
function parseEditedSelections(text: string): Record<string, string> {
  const lines = text.split('\n').filter(l => l.trim());
  const result: Record<string, string> = {};
  
  lines.forEach(line => {
    // Try arrow format: "phrase → node"
    const arrowMatch = line.match(/(.+?)\s*→\s*(.+)/);
    if (arrowMatch) {
      result[arrowMatch[1].trim()] = arrowMatch[2].trim();
    }
    // Otherwise just use line as node name (for simple cases)
  });
  
  return result;
}