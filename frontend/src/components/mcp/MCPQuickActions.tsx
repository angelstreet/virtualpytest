import React, { useState } from 'react';
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
  Collapse,
  IconButton,
  Chip,
  Tabs,
  Tab,
  Stack,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
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
}

export const MCPQuickActions: React.FC<MCPQuickActionsProps> = ({
  navNodes,
  availableActions,
  availableVerifications,
  setPrompt,
}) => {
  
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  
  const handleQuickAction = (text: string) => {
    setPrompt(text);
  };
  
  // Common navigation commands
  const commonNavigation = navNodes.slice(0, 5).map(node => ({
    label: `Navigate to ${node.label}`,
    prompt: `Navigate to ${node.label}`,
  }));
  
  // Common actions
  const commonActions = [
    { label: 'Take Screenshot', prompt: 'Take a screenshot' },
    { label: 'Swipe Up', prompt: 'Swipe up' },
    { label: 'Swipe Down', prompt: 'Swipe down' },
    { label: 'Press Back', prompt: 'Press back button' },
    { label: 'Press Home', prompt: 'Press home button' },
  ];
  
  // Common verifications
  const commonVerifications = [
    { label: 'Verify Element Exists', prompt: 'Verify element exists' },
    { label: 'Verify Text Visible', prompt: 'Verify text is visible' },
    { label: 'Check Screen Content', prompt: 'Check screen content' },
  ];
  
  const tabs = [
    { label: 'Navigation', icon: <NavigationIcon fontSize="small" />, items: commonNavigation },
    { label: 'Actions', icon: <ActionIcon fontSize="small" />, items: commonActions },
    { label: 'Verification', icon: <VerificationIcon fontSize="small" />, items: commonVerifications },
  ];
  
  return (
    <Card
      sx={{
        border: 1,
        borderColor: 'divider',
        boxShadow: 'none',
        height: { lg: 'fit-content' },
        maxHeight: { lg: 'calc(100vh - 200px)' },
        overflow: 'auto',
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: isCollapsed ? 0 : 2,
            cursor: { xs: 'pointer', lg: 'default' },
          }}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <Typography variant="h6" sx={{ fontSize: { xs: '1rem', md: '1.1rem' } }}>
            Quick Actions
          </Typography>
          <IconButton
            size="small"
            sx={{ display: { xs: 'block', lg: 'none' } }}
          >
            {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
          </IconButton>
        </Box>
        
        {/* Collapsible Content */}
        <Collapse in={!isCollapsed} timeout="auto">
          <Stack spacing={2}>
            {/* Tabs */}
            <Tabs
              value={activeTab}
              onChange={(_, newValue) => setActiveTab(newValue)}
              variant="fullWidth"
              sx={{
                minHeight: { xs: 44, md: 40 },
                '& .MuiTab-root': {
                  minHeight: { xs: 44, md: 40 },
                  fontSize: { xs: '0.85rem', md: '0.8rem' },
                },
              }}
            >
              {tabs.map((tab, index) => (
                <Tab
                  key={index}
                  label={tab.label}
                  icon={tab.icon}
                  iconPosition="start"
                  sx={{
                    textTransform: 'none',
                  }}
                />
              ))}
            </Tabs>
            
            {/* Tab Content */}
            <Box>
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
                            secondary="Connect to device to see options"
                            sx={{
                              '& .MuiListItemText-primary': {
                                fontSize: { xs: '0.9rem', md: '0.85rem' },
                              },
                              '& .MuiListItemText-secondary': {
                                fontSize: { xs: '0.8rem', md: '0.75rem' },
                              },
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
                              mb: 0.5,
                              minHeight: { xs: 48, md: 44 },
                              '&:hover': {
                                bgcolor: 'action.hover',
                              },
                            }}
                          >
                            <ListItemIcon sx={{ minWidth: { xs: 40, md: 36 } }}>
                              <ArrowForwardIcon fontSize="small" />
                            </ListItemIcon>
                            <ListItemText
                              primary={item.label}
                              sx={{
                                '& .MuiListItemText-primary': {
                                  fontSize: { xs: '0.9rem', md: '0.85rem' },
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
            
            {/* Stats */}
            <Stack direction="row" spacing={1} sx={{ justifyContent: 'center', flexWrap: 'wrap', gap: 1 }}>
              <Chip
                label={`${navNodes.length} nodes`}
                size="small"
                variant="outlined"
                sx={{ fontSize: { xs: '0.8rem', md: '0.75rem' } }}
              />
              <Chip
                label={`${Object.values(availableActions || {}).flat().length} actions`}
                size="small"
                variant="outlined"
                sx={{ fontSize: { xs: '0.8rem', md: '0.75rem' } }}
              />
              <Chip
                label={`${Object.values(availableVerifications || {}).flat().length} verifications`}
                size="small"
                variant="outlined"
                sx={{ fontSize: { xs: '0.8rem', md: '0.75rem' } }}
              />
            </Stack>
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  );
};

