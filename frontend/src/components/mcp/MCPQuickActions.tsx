import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tabs,
  Tab,
  Stack,
  Chip,
} from '@mui/material';
import {
  Navigation as NavigationIcon,
  TouchApp as ActionIcon,
  CheckCircle as VerificationIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';

interface MCPQuickActionsProps {
  navNodes: any[];
  availableActions: any;
  availableVerifications: any;
  setPrompt: (prompt: string) => void;
  isControlActive: boolean;
}

export const MCPQuickActions: React.FC<MCPQuickActionsProps> = ({
  navNodes,
  availableActions,
  availableVerifications,
  setPrompt,
  isControlActive,
}) => {
  
  const [activeTab, setActiveTab] = useState(0);
  
  const handleQuickAction = (text: string) => {
    setPrompt(text);
  };
  
  // Build navigation items from navNodes
  const navigationItems = useMemo(() => {
    return navNodes.slice(0, 10).map(node => ({
      label: node.label || node.id,
      prompt: `Navigate to ${node.label || node.id}`,
    }));
  }, [navNodes]);
  
  // Build action items from availableActions
  const actionItems = useMemo(() => {
    if (!availableActions) return [];
    
    const items: any[] = [];
    Object.entries(availableActions).forEach(([category, actions]: [string, any]) => {
      if (Array.isArray(actions)) {
        actions.slice(0, 10).forEach((action: any) => {
          const label = action.label || action.command || action.id;
          items.push({
            label: label,
            prompt: `Execute ${label.toLowerCase()}`,
          });
        });
      }
    });
    return items.slice(0, 10); // Limit to 10 total
  }, [availableActions]);
  
  // Build verification items from availableVerifications
  const verificationItems = useMemo(() => {
    if (!availableVerifications) return [];
    
    const items: any[] = [];
    Object.entries(availableVerifications).forEach(([category, verifications]: [string, any]) => {
      if (typeof verifications === 'object' && !Array.isArray(verifications)) {
        // Handle dict structure (method_name: {description, params})
        Object.entries(verifications).slice(0, 10).forEach(([methodName, _]: [string, any]) => {
          items.push({
            label: methodName,
            prompt: `Verify ${methodName.replace(/_/g, ' ')}`,
          });
        });
      } else if (Array.isArray(verifications)) {
        // Handle list structure
        verifications.slice(0, 10).forEach((verification: any) => {
          const label = verification.label || verification.command || verification.id;
          items.push({
            label: label,
            prompt: `Verify ${label.toLowerCase()}`,
          });
        });
      }
    });
    return items.slice(0, 10); // Limit to 10 total
  }, [availableVerifications]);
  
  const tabs = [
    { label: 'Navigation', icon: <NavigationIcon fontSize="small" />, items: navigationItems },
    { label: 'Actions', icon: <ActionIcon fontSize="small" />, items: actionItems },
    { label: 'Verification', icon: <VerificationIcon fontSize="small" />, items: verificationItems },
  ];
  
  return (
    <Card
      sx={{
        border: 1,
        borderColor: 'divider',
        boxShadow: 'none',
        height: '500px', // FIXED HEIGHT - same as prompt input
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CardContent sx={{ 
        p: 2.5, 
        '&:last-child': { pb: 2.5 },
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <Typography variant="h6" sx={{ fontSize: '1.1rem', mb: 1 }}>
          Quick Actions
        </Typography>
        
        {!isControlActive ? (
          // Show message when not in control
          <Box sx={{ 
            flex: 1, 
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 2,
            opacity: 0.6,
          }}>
            <Typography variant="body2" color="text.secondary" align="center">
            ⚠️ Take control of the device first
            </Typography>
          </Box>
        ) : (
          <>
            {/* Tabs */}
            <Tabs
              value={activeTab}
              onChange={(_, newValue) => setActiveTab(newValue)}
              variant="fullWidth"
              sx={{
                minHeight: 32,
                mb: 1,
                '& .MuiTab-root': {
                  minHeight: 32,
                  fontSize: '0.8rem',
                  textTransform: 'none',
                },
              }}
            >
              {tabs.map((tab, index) => (
                <Tab
                  key={index}
                  label={tab.label}
                  icon={tab.icon}
                  iconPosition="start"
                />
              ))}
            </Tabs>
            
            {/* Tab Content with Scrollbar */}
            <Box sx={{ 
              flex: 1, 
              overflow: 'auto',
              mb: 1,
            }}>
              {tabs.map((tab, tabIndex) => (
                <Box
                  key={tabIndex}
                  role="tabpanel"
                  hidden={activeTab !== tabIndex}
                >
                  {activeTab === tabIndex && (
                    <List dense sx={{ p: 0 }}>
                      {tab.items.length === 0 ? (
                        <ListItem>
                          <ListItemText
                            primary="No items available"
                            sx={{
                              '& .MuiListItemText-primary': { fontSize: '0.85rem' },
                            }}
                          />
                        </ListItem>
                      ) : (
                        tab.items.map((item, index) => (
                          <ListItemButton
                            key={index}
                            onClick={() => handleQuickAction(item.prompt)}
                            sx={{
                              borderRadius: 1,
                              mb: 0,
                              minHeight: 16,
                              py: 0,
                              '&:hover': {
                                bgcolor: 'action.hover',
                              },
                            }}
                          >
                            <ListItemIcon sx={{ minWidth: 28 }}>
                              <ArrowForwardIcon fontSize="small" sx={{ fontSize: '1rem' }} />
                            </ListItemIcon>
                            <ListItemText
                              primary={item.label}
                              sx={{
                                '& .MuiListItemText-primary': {
                                  fontSize: '0.85rem',
                                },
                              }}
                            />
                          </ListItemButton>
                        ))
                      )}
                    </List>
                  )}
                </Box>
              ))}
            </Box>
          </>
        )}
        
        {/* Stats */}
        <Stack direction="row" spacing={1} sx={{ justifyContent: 'center', flexWrap: 'wrap', gap: 1 }}>
          <Chip
            label={`${navNodes.length} nodes`}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
          <Chip
            label={`${Object.values(availableActions || {}).flat().length} actions`}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
          <Chip
            label={`${Object.values(availableVerifications || {}).flat().length} verifications`}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
        </Stack>
      </CardContent>
    </Card>
  );
};
