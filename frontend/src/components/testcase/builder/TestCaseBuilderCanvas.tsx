import React from 'react';
import {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ExecutionOverlay } from '../ExecutionOverlay';

interface TestCaseBuilderCanvasProps {
  actualMode: 'light' | 'dark';
  isSidebarOpen: boolean;
  
  // Execution Overlay
  isExecuting: boolean;
  executionDetails: {
    command?: string;
    params?: Record<string, any>;
  };
}

export const TestCaseBuilderCanvas: React.FC<TestCaseBuilderCanvasProps> = ({
  actualMode,
  isSidebarOpen,
  isExecuting,
  executionDetails,
}) => {
  return (
    <>
      <Background
        variant={BackgroundVariant.Dots}
        gap={15}
        size={1}
        color={actualMode === 'dark' ? '#334155' : '#cbd5e1'}
      />
      <Controls
        showInteractive={false}
        position="top-left"
        style={{
          background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
          border: `1px solid ${actualMode === 'dark' ? '#334155' : '#e2e8f0'}`,
          borderRadius: '8px',
          left: isSidebarOpen ? '290px' : '10px',
          transition: 'left 0.3s ease',
        }}
      />
      <MiniMap
        nodeColor={(node) => {
          const colorMap: Record<string, string> = {
            start: '#10b981',
            success: '#10b981',
            failure: '#ef4444',
            action: '#f97316',
            verification: '#3b82f6',
            loop: '#6b7280',
            sleep: '#6b7280',
            get_current_time: '#6b7280',
            condition: '#6b7280',
            set_variable: '#6b7280',
          };
          return colorMap[node.type as string] || '#6b7280';
        }}
        style={{
          background: actualMode === 'dark' ? '#1e293b' : '#ffffff',
          border: `1px solid ${actualMode === 'dark' ? '#334155' : '#e2e8f0'}`,
          borderRadius: '8px',
        }}
        position="top-right"
      />
      
      {/* Execution Overlay */}
      {isExecuting && (
        <ExecutionOverlay
          isExecuting={isExecuting}
          command={executionDetails.command}
          params={executionDetails.params}
        />
      )}
    </>
  );
};

