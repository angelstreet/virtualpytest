import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Collapse,
  IconButton,
  Chip,
  Button,
  Stack,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Replay as ReplayIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

interface MCPCommandHistoryProps {
  commandHistory: Array<{ timestamp: Date; prompt: string; success: boolean; result?: any }>;
  setPrompt: (prompt: string) => void;
  clearHistory: () => void;
}

export const MCPCommandHistory: React.FC<MCPCommandHistoryProps> = ({
  commandHistory,
  setPrompt,
  clearHistory,
}) => {
  
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [showAll, setShowAll] = useState(false);
  
  const displayedHistory = showAll ? commandHistory : commandHistory.slice(0, 5);
  
  const handleReplay = (prompt: string) => {
    setPrompt(prompt);
  };
  
  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return `${seconds}s ago`;
  };
  
  if (commandHistory.length === 0) {
    return null;
  }
  
  return (
    <Card
      sx={{
        border: 1,
        borderColor: 'divider',
        boxShadow: 'none',
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
            cursor: 'pointer',
          }}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6" sx={{ fontSize: { xs: '1rem', md: '1.1rem' } }}>
              Command History
            </Typography>
            <Chip
              label={commandHistory.length}
              size="small"
              sx={{
                fontSize: { xs: '0.75rem', md: '0.7rem' },
                height: 20,
              }}
            />
          </Stack>
          <IconButton size="small">
            {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
          </IconButton>
        </Box>
        
        {/* Collapsible Content */}
        <Collapse in={!isCollapsed} timeout="auto">
          <Stack spacing={2}>
            {/* History List */}
            <List dense sx={{ p: 0 }}>
              {displayedHistory.map((item, index) => (
                <ListItem
                  key={index}
                  disablePadding
                  sx={{ mb: 0.5 }}
                  secondaryAction={
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={() => handleReplay(item.prompt)}
                      sx={{ mr: 1 }}
                    >
                      <ReplayIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemButton
                    onClick={() => handleReplay(item.prompt)}
                    sx={{
                      borderRadius: 1,
                      border: 1,
                      borderColor: 'divider',
                      minHeight: { xs: 64, md: 56 },
                      '&:hover': {
                        bgcolor: 'action.hover',
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: { xs: 40, md: 36 } }}>
                      {item.success ? (
                        <SuccessIcon fontSize="small" color="success" />
                      ) : (
                        <ErrorIcon fontSize="small" color="error" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={item.prompt}
                      secondary={formatTimestamp(item.timestamp)}
                      primaryTypographyProps={{
                        sx: {
                          fontSize: { xs: '0.9rem', md: '0.85rem' },
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        },
                      }}
                      secondaryTypographyProps={{
                        sx: {
                          fontSize: { xs: '0.75rem', md: '0.7rem' },
                        },
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
            
            {/* Show More / Clear Buttons */}
            <Stack direction="row" spacing={1}>
              {commandHistory.length > 5 && (
                <Button
                  size="small"
                  onClick={() => setShowAll(!showAll)}
                  sx={{
                    textTransform: 'none',
                    fontSize: { xs: '0.85rem', md: '0.8rem' },
                  }}
                >
                  {showAll ? 'Show Less' : `Show All (${commandHistory.length})`}
                </Button>
              )}
              <Box sx={{ flex: 1 }} />
              <Button
                size="small"
                color="error"
                startIcon={<DeleteIcon fontSize="small" />}
                onClick={clearHistory}
                sx={{
                  textTransform: 'none',
                  fontSize: { xs: '0.85rem', md: '0.8rem' },
                }}
              >
                Clear
              </Button>
            </Stack>
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  );
};

