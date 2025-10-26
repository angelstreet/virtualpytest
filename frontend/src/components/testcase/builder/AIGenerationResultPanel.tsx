/**
 * AIGenerationResultPanel Component
 * 
 * Draggable panel that appears after AI generation completes
 * Shows:
 * - AI reasoning/analysis
 * - Generation stats (time, tokens, block counts)
 * - Block type breakdown
 * 
 * Similar UX to ExecutionProgressBar but for generation results
 */

import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, IconButton, Tooltip, Collapse, Chip } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { useTheme } from '../../../contexts/ThemeContext';

interface AIGenerationResult {
  success: boolean;
  graph: {
    nodes: any[];
    edges: any[];
  };
  analysis?: string;
  plan_id?: string;
  execution_time: number; // seconds
  generation_stats?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    block_counts?: {
      navigation: number;
      action: number;
      verification: number;
      other: number;
      total: number;
    };
    blocks_generated?: Array<{
      type: string;
      label: string;
      id: string;
    }>;
  };
  error?: string;
}

interface AIGenerationResultPanelProps {
  result: AIGenerationResult;
  onClose: () => void;
  onRegenerate: () => void;
}

export const AIGenerationResultPanel: React.FC<AIGenerationResultPanelProps> = ({
  result,
  onClose,
  onRegenerate,
}) => {
  const { actualMode } = useTheme();
  const [isAnalysisExpanded, setIsAnalysisExpanded] = useState(true);
  const [isStatsExpanded, setIsStatsExpanded] = useState(true);
  
  // Draggable state
  const [position, setPosition] = useState({ x: 0, y: 120 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; initialX: number; initialY: number } | null>(null);

  // Parse analysis into Goal and Thinking
  const parseAnalysis = (analysis?: string) => {
    if (!analysis) return { goal: '', thinking: '' };
    
    const lines = analysis.split('\n');
    let goal = '';
    let thinking = '';
    
    for (const line of lines) {
      if (line.startsWith('Goal:')) {
        goal = line.replace('Goal:', '').trim();
      } else if (line.startsWith('Thinking:')) {
        thinking = line.replace('Thinking:', '').trim();
      }
    }
    
    return { goal, thinking };
  };

  const { goal, thinking } = parseAnalysis(result.analysis);

  // Calculate block type counts from graph if not provided
  const blockCounts = result.generation_stats?.block_counts || {
    navigation: result.graph.nodes.filter(n => n.type === 'navigation').length,
    action: result.graph.nodes.filter(n => n.type === 'action').length,
    verification: result.graph.nodes.filter(n => n.type === 'verification').length,
    other: result.graph.nodes.filter(n => !['start', 'success', 'failure', 'navigation', 'action', 'verification'].includes(n.type)).length,
    total: result.graph.nodes.length,
  };

  // Generate blocks list if not provided
  const blocksGenerated = result.generation_stats?.blocks_generated || 
    result.graph.nodes.map(node => ({
      type: node.type,
      label: node.data?.label || node.data?.command || node.type,
      id: node.id,
    }));

  // Draggable handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.drag-handle')) {
      setIsDragging(true);
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        initialX: position.x,
        initialY: position.y,
      };
      e.preventDefault();
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && dragRef.current) {
        const deltaX = e.clientX - dragRef.current.startX;
        const deltaY = e.clientY - dragRef.current.startY;
        setPosition({
          x: dragRef.current.initialX + deltaX,
          y: dragRef.current.initialY + deltaY,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      dragRef.current = null;
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const getBlockTypeIcon = (type: string) => {
    switch (type) {
      case 'navigation': return '🧭';
      case 'action': return '⚡';
      case 'verification': return '✓';
      case 'start': return '▶️';
      case 'success': return '✅';
      case 'failure': return '❌';
      default: return '🎬';
    }
  };

  const getBlockTypeColor = (type: string) => {
    switch (type) {
      case 'navigation': return '#3b82f6';
      case 'action': return '#8b5cf6';
      case 'verification': return '#10b981';
      case 'start': return '#6b7280';
      case 'success': return '#10b981';
      case 'failure': return '#ef4444';
      default: return '#f59e0b';
    }
  };

  return (
    <Box
      onMouseDown={handleMouseDown}
      sx={{
        position: 'fixed',
        top: `${position.y}px`,
        right: position.x === 0 ? '24px' : 'auto',
        left: position.x !== 0 ? `${position.x}px` : 'auto',
        zIndex: 1100,
        minWidth: 500,
        maxWidth: 650,
        backgroundColor: actualMode === 'dark' ? '#1f2937' : '#ffffff',
        borderRadius: 2,
        boxShadow: isDragging ? '0 12px 24px rgba(0, 0, 0, 0.4)' : '0 8px 16px rgba(0, 0, 0, 0.3)',
        border: '2px solid',
        borderColor: '#10b981',
        cursor: isDragging ? 'grabbing' : 'default',
        userSelect: isDragging ? 'none' : 'auto',
        transition: isDragging ? 'none' : 'box-shadow 0.2s ease',
        animation: position.x === 0 && position.y === 120 ? 'slideDown 0.3s ease-out' : 'none',
        '@keyframes slideDown': {
          from: {
            opacity: 0,
            transform: 'translateY(-20px)',
          },
          to: {
            opacity: 1,
            transform: 'translateY(0)',
          },
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          pb: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Drag Handle */}
          <Box
            className="drag-handle"
            sx={{
              cursor: 'grab',
              display: 'flex',
              alignItems: 'center',
              color: 'text.secondary',
              '&:hover': {
                color: 'text.primary',
              },
              '&:active': {
                cursor: 'grabbing',
              },
            }}
          >
            <DragIndicatorIcon fontSize="small" />
          </Box>
          
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: '#10b981',
              animation: 'successPulse 2s ease-in-out infinite',
              '@keyframes successPulse': {
                '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                '50%': { opacity: 0.6, transform: 'scale(1.2)' },
              },
            }}
          />
          
          <CheckCircleIcon sx={{ color: '#10b981', fontSize: 20 }} />
          <Typography variant="subtitle2" fontWeight="bold" color="#10b981">
            ⚡ AI GENERATION COMPLETE
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Stats */}
          <Chip 
            label={`${blockCounts.total} blocks`}
            size="small"
            sx={{ 
              fontWeight: 'bold',
              backgroundColor: actualMode === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
              color: '#3b82f6',
            }}
          />
          
          {/* Timer */}
          <Typography
            variant="caption"
            sx={{
              fontFamily: 'monospace',
              color: 'text.secondary',
              fontWeight: 'bold',
            }}
          >
            ⏱ {result.execution_time.toFixed(2)}s
          </Typography>

          {/* Close Button */}
          <Tooltip title="Close">
            <IconButton
              size="small"
              onClick={onClose}
              sx={{
                color: 'text.secondary',
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.1)',
                },
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* AI Analysis Section */}
      {(goal || thinking) && (
        <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              px: 2,
              py: 1,
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
              },
            }}
            onClick={() => setIsAnalysisExpanded(!isAnalysisExpanded)}
          >
            <Typography variant="caption" fontWeight="bold" color="text.secondary">
              🤖 AI ANALYSIS
            </Typography>
            <IconButton size="small">
              {isAnalysisExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>
          
          <Collapse in={isAnalysisExpanded}>
            <Box sx={{ px: 2, pb: 2 }}>
              {goal && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#3b82f6', display: 'block', mb: 0.5 }}>
                    🎯 Goal
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                    {goal}
                  </Typography>
                </Box>
              )}
              
              {thinking && (
                <Box>
                  <Typography variant="caption" fontWeight="bold" sx={{ color: '#10b981', display: 'block', mb: 0.5 }}>
                    💭 Thinking
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                    {thinking}
                  </Typography>
                </Box>
              )}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Generation Stats Section */}
      <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1,
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
            },
          }}
          onClick={() => setIsStatsExpanded(!isStatsExpanded)}
        >
          <Typography variant="caption" fontWeight="bold" color="text.secondary">
            📊 GENERATION STATS
          </Typography>
          <IconButton size="small">
            {isStatsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        </Box>
        
        <Collapse in={isStatsExpanded}>
          <Box sx={{ px: 2, pb: 2 }}>
            {/* Top Stats Row */}
            <Box 
              sx={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(3, 1fr)', 
                gap: 2, 
                mb: 2,
                p: 1.5,
                borderRadius: 1,
                backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
              }}
            >
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                  ⏱ Generation Time
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {result.execution_time.toFixed(3)}s
                </Typography>
              </Box>
              
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                  📦 Total Blocks
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {blockCounts.total} blocks
                </Typography>
              </Box>
              
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                  🔤 Tokens
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {result.generation_stats?.prompt_tokens || 'N/A'} / {result.generation_stats?.completion_tokens || 'N/A'}
                </Typography>
              </Box>
            </Box>

            {/* Block Type Breakdown */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" fontWeight="bold" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                Block Type Breakdown
              </Typography>
              <Box 
                sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(2, 1fr)', 
                  gap: 1,
                }}
              >
                <Box 
                  sx={{ 
                    p: 1,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                    backgroundColor: actualMode === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
                  }}
                >
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    🧭 Navigation
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" sx={{ color: '#3b82f6' }}>
                    {blockCounts.navigation} {blockCounts.navigation === 1 ? 'block' : 'blocks'}
                  </Typography>
                </Box>

                <Box 
                  sx={{ 
                    p: 1,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                    backgroundColor: actualMode === 'dark' ? 'rgba(139, 92, 246, 0.1)' : 'rgba(139, 92, 246, 0.05)',
                  }}
                >
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    ⚡ Action
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" sx={{ color: '#8b5cf6' }}>
                    {blockCounts.action} {blockCounts.action === 1 ? 'block' : 'blocks'}
                  </Typography>
                </Box>

                <Box 
                  sx={{ 
                    p: 1,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                    backgroundColor: actualMode === 'dark' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.05)',
                  }}
                >
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    ✓ Verification
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" sx={{ color: '#10b981' }}>
                    {blockCounts.verification} {blockCounts.verification === 1 ? 'block' : 'blocks'}
                  </Typography>
                </Box>

                <Box 
                  sx={{ 
                    p: 1,
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                    backgroundColor: actualMode === 'dark' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(245, 158, 11, 0.05)',
                  }}
                >
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    🎬 Other
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" sx={{ color: '#f59e0b' }}>
                    {blockCounts.other} {blockCounts.other === 1 ? 'block' : 'blocks'}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Generated Blocks List */}
            <Box>
              <Typography variant="caption" fontWeight="bold" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                Generated Blocks
              </Typography>
              <Box 
                sx={{ 
                  maxHeight: 200,
                  overflowY: 'auto',
                  '&::-webkit-scrollbar': {
                    width: '6px',
                  },
                  '&::-webkit-scrollbar-track': {
                    background: actualMode === 'dark' ? '#374151' : '#e5e7eb',
                    borderRadius: '3px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    background: actualMode === 'dark' ? '#6b7280' : '#9ca3af',
                    borderRadius: '3px',
                    '&:hover': {
                      background: actualMode === 'dark' ? '#9ca3af' : '#6b7280',
                    },
                  },
                }}
              >
                {blocksGenerated.map((block, idx) => (
                  <Box
                    key={block.id}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      p: 0.75,
                      mb: 0.5,
                      borderRadius: 0.5,
                      backgroundColor: actualMode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                      border: '1px solid',
                      borderColor: actualMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
                    }}
                  >
                    <Typography variant="caption" sx={{ fontSize: '0.875rem' }}>
                      {getBlockTypeIcon(block.type)}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: getBlockTypeColor(block.type),
                        fontWeight: 'bold',
                        minWidth: 80,
                      }}
                    >
                      {block.type.toUpperCase()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.primary', flex: 1 }}>
                      {block.label}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        </Collapse>
      </Box>

      {/* Action Buttons */}
      <Box 
        sx={{ 
          borderTop: 1, 
          borderColor: 'divider',
          p: 2,
          pt: 1.5,
          display: 'flex',
          gap: 1,
          justifyContent: 'flex-end',
        }}
      >
        <Tooltip title="Generate a new test case with a different prompt">
          <IconButton
            size="small"
            onClick={onRegenerate}
            sx={{
              color: '#3b82f6',
              border: '1px solid',
              borderColor: '#3b82f6',
              borderRadius: 1,
              px: 2,
              '&:hover': {
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
              },
            }}
          >
            <RefreshIcon fontSize="small" sx={{ mr: 0.5 }} />
            <Typography variant="caption" fontWeight="bold">
              Regenerate
            </Typography>
          </IconButton>
        </Tooltip>

        <Tooltip title="Keep the generated graph and close this panel">
          <IconButton
            size="small"
            onClick={onClose}
            sx={{
              color: '#10b981',
              border: '1px solid',
              borderColor: '#10b981',
              borderRadius: 1,
              px: 2,
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              '&:hover': {
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
              },
            }}
          >
            <Typography variant="caption" fontWeight="bold">
              Close & Keep Graph
            </Typography>
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
};


