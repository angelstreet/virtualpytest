/**
 * Content Viewer Component
 * 
 * Displays dynamic content in the AgentChat center area above the minimized chat.
 * Content types: navigation-tree, testcase-flow, rec-preview, report-chart, data-table
 * 
 * Controlled by AI agent via show_content_panel tool.
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Chip,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Close as CloseIcon,
  AccountTree as TreeIcon,
  PlaylistPlay as TestCaseIcon,
  Tv as StreamIcon,
  BarChart as ChartIcon,
  TableChart as TableIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { AGENT_CHAT_PALETTE as PALETTE } from '../../constants/agentChatTheme';

// Real viewer components
import { NavigationTreeViewer } from './NavigationTreeViewer';
import { TestCaseFlowViewer } from './TestCaseFlowViewer';
import { CampaignFlowViewer } from './CampaignFlowViewer';
import { HeatmapViewer } from './HeatmapViewer';
import { AlertsViewer } from './AlertsViewer';

// Content type definitions
export type ContentType =
  | 'navigation-tree'
  | 'testcase-flow'
  | 'campaign-flow'
  | 'heatmap'
  | 'alerts'
  | 'rec-preview'
  | 'report-chart'
  | 'data-table'
  | 'execution-log';

export interface ContentData {
  // Navigation tree
  tree_id?: string;
  node_id?: string;
  userinterface_name?: string;

  // Test case
  testcase_id?: string;
  editable?: boolean;

  // Campaign
  campaign_id?: string;

  // REC preview
  device_ids?: string[];
  stream_urls?: string[];

  // Report/Chart
  chart_type?: 'bar' | 'line' | 'pie' | 'area';
  chart_data?: any;

  // Data table
  columns?: { field: string; header: string }[];
  rows?: any[];

  // Execution log
  log_entries?: { timestamp: string; level: string; message: string }[];
}

export type ContentTab = 'navigation' | 'testcase' | 'campaign' | 'heatmap' | 'alerts';

interface ContentViewerProps {
  contentType: ContentType | null;
  contentData: ContentData | null;
  title?: string;
  onClose: () => void;
  isLoading?: boolean;
  // Tab support
  activeTab?: ContentTab;
  onTabChange?: (tab: ContentTab) => void;
  selectedUserInterface?: string;
  selectedTestCase?: string;
  selectedTestCaseName?: string;
  selectedCampaign?: string;
  selectedCampaignName?: string;
  // Fullscreen support
  isFullscreen?: boolean;
  onFullscreenChange?: (fullscreen: boolean) => void;
}

// Icon mapping for content types
const ContentTypeIcon: Record<ContentType, React.ElementType> = {
  'navigation-tree': TreeIcon,
  'testcase-flow': TestCaseIcon,
  'campaign-flow': TestCaseIcon, // Use same icon as testcase for now
  'heatmap': TreeIcon, // Use TreeIcon for heatmap grid
  'alerts': ErrorIcon, // Use ErrorIcon for alerts/incidents
  'rec-preview': StreamIcon,
  'report-chart': ChartIcon,
  'data-table': TableIcon,
  'execution-log': TableIcon,
};

// Label mapping for content types
const ContentTypeLabel: Record<ContentType, string> = {
  'navigation-tree': 'Navigation Tree',
  'testcase-flow': 'Test Case',
  'campaign-flow': 'Campaign',
  'heatmap': 'Heatmap',
  'alerts': 'Alerts',
  'rec-preview': 'Device Preview',
  'report-chart': 'Report',
  'data-table': 'Data',
  'execution-log': 'Execution Log',
};

export const ContentViewer: React.FC<ContentViewerProps> = ({
  contentType,
  contentData,
  title,
  onClose,
  isLoading = false,
  activeTab = 'navigation',
  onTabChange,
  selectedUserInterface,
  selectedTestCase,
  selectedTestCaseName,
  isFullscreen = false,
  onFullscreenChange,
}) => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Determine if tabs should be shown (when we have manual selection mode)
  const showTabs = selectedUserInterface !== undefined || selectedTestCase !== undefined || selectedCampaign !== undefined;

  // Tab enabled states
  const navigationEnabled = !!selectedUserInterface;
  const testcaseEnabled = !!selectedTestCase;
  const campaignEnabled = !!selectedCampaign;

  // Don't render if no content type AND no tabs
  if (!contentType && !showTabs) return null;
  
  // If showing tabs but no content type, determine from active tab
  const effectiveContentType = contentType || (activeTab === 'testcase' ? 'testcase-flow' : 'navigation-tree');

  const Icon = ContentTypeIcon[effectiveContentType];
  const typeLabel = ContentTypeLabel[effectiveContentType];

  // Render content based on type
  const renderContent = () => {
    if (isLoading) {
      return (
        <Box sx={{ 
          flex: 1, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2,
        }}>
          <CircularProgress size={40} sx={{ color: PALETTE.accent }} />
          <Typography variant="body2" color="text.secondary">
            Loading {typeLabel}...
          </Typography>
        </Box>
      );
    }

    switch (contentType) {
      case 'navigation-tree':
        return <NavigationTreeContent data={contentData} />;
      case 'testcase-flow':
        return <TestCaseFlowContent data={contentData} />;
      case 'campaign-flow':
        return <CampaignFlowContent data={contentData} />;
      case 'heatmap':
        return <HeatmapContent data={contentData} />;
      case 'alerts':
        return <AlertsContent data={contentData} />;
      case 'rec-preview':
        return <RecPreviewContent data={contentData} />;
      case 'report-chart':
        return <ReportChartContent data={contentData} />;
      case 'data-table':
        return <DataTableContent data={contentData} />;
      case 'execution-log':
        return <ExecutionLogContent data={contentData} />;
      default:
        return (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              Unknown content type: {contentType}
            </Typography>
          </Box>
        );
    }
  };

  // Render content based on effective type (handles both tab mode and direct mode)
  const renderTabContent = () => {
    if (isLoading) {
      return (
        <Box sx={{ 
          flex: 1, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2,
        }}>
          <CircularProgress size={40} sx={{ color: PALETTE.accent }} />
          <Typography variant="body2" color="text.secondary">
            Loading...
          </Typography>
        </Box>
      );
    }
    
    // In tab mode, use activeTab to determine content
    if (showTabs) {
      if (activeTab === 'navigation' && selectedUserInterface) {
        return (
          <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
            <NavigationTreeViewer
              userInterfaceName={selectedUserInterface}
              readOnly={true}
            />
          </Box>
        );
      } else if (activeTab === 'testcase' && selectedTestCase) {
        return (
          <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
            <TestCaseFlowViewer
              testcaseId={selectedTestCase}
              readOnly={true}
            />
          </Box>
        );
      } else if (activeTab === 'campaign' && selectedCampaign) {
        return (
          <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
            <CampaignFlowViewer
              campaignId={selectedCampaign}
              readOnly={true}
            />
          </Box>
        );
      } else if (activeTab === 'heatmap') {
        return (
          <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
            <HeatmapViewer />
          </Box>
        );
      } else if (activeTab === 'alerts') {
        return (
          <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
            <AlertsViewer />
          </Box>
        );
      } else {
        // No valid selection for active tab
        return (
          <Box sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 2,
            p: 4,
          }}>
            {activeTab === 'navigation' ? (
              <>
                <TreeIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
                <Typography variant="body1" color="text.secondary">
                  Select an Interface to view navigation tree
                </Typography>
              </>
            ) : activeTab === 'testcase' ? (
              <>
                <TestCaseIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
                <Typography variant="body1" color="text.secondary">
                  Select a Test Case to view flow
                </Typography>
              </>
            ) : (
              <>
                <TestCaseIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
                <Typography variant="body1" color="text.secondary">
                  Select a Campaign to view flow
                </Typography>
              </>
            )}
          </Box>
        );
      }
    }
    
    // Direct content mode (from AI agent)
    return renderContent();
  };

  return (
    <Box
      sx={{
        flex: isFullscreen ? 1 : 0.6,
        minHeight: isFullscreen ? 'auto' : 300,
        display: 'flex',
        flexDirection: 'column',
        bgcolor: isDarkMode ? PALETTE.sidebarBg : 'grey.50',
        borderBottom: '1px solid',
        borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
        overflow: 'hidden',
        transition: 'flex 0.2s ease-in-out',
      }}
    >
      {/* Header with Tabs */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 1,
          borderBottom: '1px solid',
          borderColor: isDarkMode ? PALETTE.borderColor : 'grey.200',
          bgcolor: isDarkMode ? PALETTE.surface : '#fff',
          minHeight: 44,
        }}
      >
        {/* Tabs (when in manual selection mode) */}
        {showTabs ? (
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => onTabChange?.(newValue)}
            sx={{
              minHeight: 42,
              '& .MuiTabs-indicator': {
                backgroundColor: PALETTE.accent,
                height: 2,
              },
            }}
          >
            <Tab
              value="navigation"
              label="Userinterface"
              sx={{
                minHeight: 42,
                py: 1,
                px: 2,
                textTransform: 'none',
                fontSize: '0.85rem',
                fontWeight: activeTab === 'navigation' ? 600 : 400,
                color: activeTab === 'navigation' ? 'text.primary' : 'text.secondary',
                opacity: navigationEnabled ? 1 : 0.5,
                pointerEvents: navigationEnabled ? 'auto' : 'none',
              }}
            />
            <Tab
              value="testcase"
              label="TestCase"
              sx={{
                minHeight: 42,
                py: 1,
                px: 2,
                textTransform: 'none',
                fontSize: '0.85rem',
                fontWeight: activeTab === 'testcase' ? 600 : 400,
                color: activeTab === 'testcase' ? 'text.primary' : 'text.secondary',
                opacity: testcaseEnabled ? 1 : 0.5,
                pointerEvents: testcaseEnabled ? 'auto' : 'none',
              }}
            />
            <Tab
              value="campaign"
              label="Campaign"
              sx={{
                minHeight: 42,
                py: 1,
                px: 2,
                textTransform: 'none',
                fontSize: '0.85rem',
                fontWeight: activeTab === 'campaign' ? 600 : 400,
                color: activeTab === 'campaign' ? 'text.primary' : 'text.secondary',
                opacity: campaignEnabled ? 1 : 0.5,
                pointerEvents: campaignEnabled ? 'auto' : 'none',
              }}
            />
            <Tab
              value="heatmap"
              label="Heatmap"
              sx={{
                minHeight: 42,
                py: 1,
                px: 2,
                textTransform: 'none',
                fontSize: '0.85rem',
                fontWeight: activeTab === 'heatmap' ? 600 : 400,
                color: activeTab === 'heatmap' ? 'text.primary' : 'text.secondary',
                opacity: 1, // Always enabled - no selection required
                pointerEvents: 'auto',
              }}
            />
            <Tab
              value="alerts"
              label="Alerts"
              sx={{
                minHeight: 42,
                py: 1,
                px: 2,
                textTransform: 'none',
                fontSize: '0.85rem',
                fontWeight: activeTab === 'alerts' ? 600 : 400,
                color: activeTab === 'alerts' ? 'text.primary' : 'text.secondary',
                opacity: 1, // Always enabled - no selection required
                pointerEvents: 'auto',
              }}
            />
          </Tabs>
        ) : (
          /* Simple header when showing AI-triggered content */
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: 1 }}>
            <Icon sx={{ fontSize: 20, color: PALETTE.accent }} />
            <Typography variant="subtitle2" fontWeight={600}>
              {title || typeLabel}
            </Typography>
            <Chip
              label={typeLabel}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: isDarkMode ? 'rgba(99, 102, 241, 0.2)' : 'rgba(99, 102, 241, 0.1)',
                color: PALETTE.accent,
              }}
            />
          </Box>
        )}
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton
            size="small"
            onClick={() => onFullscreenChange?.(!isFullscreen)}
            sx={{
              color: 'text.secondary',
              '&:hover': { color: PALETTE.accent },
            }}
          >
            {isFullscreen ? <FullscreenExitIcon fontSize="small" /> : <FullscreenIcon fontSize="small" />}
          </IconButton>
          <IconButton
            size="small"
            onClick={onClose}
            sx={{ 
              color: 'text.secondary',
              '&:hover': { color: 'error.main' },
            }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* Content Area */}
      <Box sx={{ flex: 1, overflow: 'auto', position: 'relative' }}>
        {renderTabContent()}
      </Box>
    </Box>
  );
};

// --- Content Type Components ---

// Navigation Tree Content - Uses real NavigationTreeViewer component
const NavigationTreeContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  // Require userinterface_name to show the navigation tree
  if (!data?.userinterface_name) {
    return (
      <Box sx={{ 
        flex: 1, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 2,
        p: 4,
      }}>
        <TreeIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
        <Typography variant="body1" color="text.secondary">
          No user interface specified
        </Typography>
        <Typography variant="caption" color="text.disabled">
          Provide userinterface_name in content_data
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      <NavigationTreeViewer
        userInterfaceName={data.userinterface_name}
        treeId={data.tree_id}
        nodeId={data.node_id}
        readOnly={true}
      />
    </Box>
  );
};

// Test Case Flow Content - Uses real TestCaseFlowViewer component
const TestCaseFlowContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  // Can show empty state or load a specific test case
  return (
    <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      <TestCaseFlowViewer
        testcaseId={data?.testcase_id}
        readOnly={!data?.editable}
      />
    </Box>
  );
};

// Campaign Flow Content - Uses real CampaignFlowViewer component
const CampaignFlowContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  // Can show empty state or load a specific campaign
  return (
    <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      <CampaignFlowViewer
        campaignId={data?.campaign_id}
        readOnly={true}
      />
    </Box>
  );
};

// Heatmap Content - Uses real HeatmapViewer component
const HeatmapContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  // Heatmap viewer doesn't need specific data - it shows the current heatmap
  return (
    <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      <HeatmapViewer />
    </Box>
  );
};

// Alerts Content - Uses real AlertsViewer component
const AlertsContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  // Alerts viewer doesn't need specific data - it shows current active alerts
  return (
    <Box sx={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      <AlertsViewer />
    </Box>
  );
};

// REC Preview Content (placeholder - will integrate HLS streams)
const RecPreviewContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  return (
    <Box sx={{ 
      flex: 1, 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 2,
      p: 4,
      bgcolor: '#000',
    }}>
      <StreamIcon sx={{ fontSize: 64, color: 'grey.600', opacity: 0.3 }} />
      <Typography variant="body1" color="grey.500">
        Device Stream Preview
      </Typography>
      {data?.device_ids && data.device_ids.length > 0 && (
        <Typography variant="caption" color="grey.600">
          Devices: {data.device_ids.join(', ')}
        </Typography>
      )}
      <Typography variant="caption" color="grey.600" sx={{ mt: 2, maxWidth: 400, textAlign: 'center' }}>
        Stream grid integration coming soon. This will display live device streams.
      </Typography>
    </Box>
  );
};

// Report Chart Content (placeholder - will integrate charting library)
const ReportChartContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  return (
    <Box sx={{ 
      flex: 1, 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 2,
      p: 4,
    }}>
      <ChartIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
      <Typography variant="body1" color="text.secondary">
        Report Chart Viewer
      </Typography>
      {data?.chart_type && (
        <Chip label={`Type: ${data.chart_type}`} size="small" variant="outlined" />
      )}
      <Typography variant="caption" color="text.disabled" sx={{ mt: 2, maxWidth: 400, textAlign: 'center' }}>
        Chart integration coming soon. This will display test results and metrics.
      </Typography>
    </Box>
  );
};

// Data Table Content (placeholder - will integrate DataGrid)
const DataTableContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  // Simple table rendering if data is provided
  if (data?.columns && data?.rows && data.rows.length > 0) {
    return (
      <Box sx={{ p: 2, overflow: 'auto' }}>
        <table style={{ 
          width: '100%', 
          borderCollapse: 'collapse',
          fontSize: '0.85rem',
        }}>
          <thead>
            <tr style={{ 
              borderBottom: `2px solid ${isDarkMode ? PALETTE.borderColor : '#e0e0e0'}`,
            }}>
              {data.columns.map((col, i) => (
                <th key={i} style={{ 
                  padding: '8px 12px', 
                  textAlign: 'left',
                  fontWeight: 600,
                  color: isDarkMode ? '#fff' : '#333',
                }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, rowIndex) => (
              <tr 
                key={rowIndex}
                style={{ 
                  borderBottom: `1px solid ${isDarkMode ? PALETTE.borderColor : '#e0e0e0'}`,
                }}
              >
                {data.columns!.map((col, colIndex) => (
                  <td key={colIndex} style={{ 
                    padding: '8px 12px',
                    color: isDarkMode ? '#ccc' : '#666',
                  }}>
                    {row[col.field] ?? '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Box>
    );
  }
  
  return (
    <Box sx={{ 
      flex: 1, 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 2,
      p: 4,
    }}>
      <TableIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
      <Typography variant="body1" color="text.secondary">
        Data Table Viewer
      </Typography>
      <Typography variant="caption" color="text.disabled">
        No data to display
      </Typography>
    </Box>
  );
};

// Execution Log Content
const ExecutionLogContent: React.FC<{ data: ContentData | null }> = ({ data }) => {
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  
  if (data?.log_entries && data.log_entries.length > 0) {
    return (
      <Box sx={{ 
        p: 1, 
        fontFamily: 'monospace', 
        fontSize: '0.75rem',
        overflow: 'auto',
        bgcolor: isDarkMode ? '#1a1a1a' : '#f5f5f5',
      }}>
        {data.log_entries.map((entry, i) => (
          <Box 
            key={i}
            sx={{ 
              py: 0.5,
              px: 1,
              display: 'flex',
              gap: 1,
              borderBottom: '1px solid',
              borderColor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
            }}
          >
            <Typography 
              component="span" 
              sx={{ 
                color: 'text.disabled',
                fontSize: 'inherit',
                fontFamily: 'inherit',
                minWidth: 80,
              }}
            >
              {entry.timestamp}
            </Typography>
            <Typography 
              component="span" 
              sx={{ 
                color: entry.level === 'error' ? 'error.main' 
                  : entry.level === 'warn' ? 'warning.main' 
                  : entry.level === 'success' ? 'success.main'
                  : 'text.secondary',
                fontSize: 'inherit',
                fontFamily: 'inherit',
                minWidth: 50,
                textTransform: 'uppercase',
              }}
            >
              [{entry.level}]
            </Typography>
            <Typography 
              component="span" 
              sx={{ 
                color: isDarkMode ? '#e0e0e0' : '#333',
                fontSize: 'inherit',
                fontFamily: 'inherit',
                flex: 1,
              }}
            >
              {entry.message}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  }
  
  return (
    <Box sx={{ 
      flex: 1, 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 2,
      p: 4,
    }}>
      <TableIcon sx={{ fontSize: 64, color: 'text.disabled', opacity: 0.3 }} />
      <Typography variant="body1" color="text.secondary">
        Execution Log
      </Typography>
      <Typography variant="caption" color="text.disabled">
        No log entries
      </Typography>
    </Box>
  );
};

export default ContentViewer;

