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
        maxHeight: '300px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CardContent sx={{ 
        p: isCollapsed ? 0.5 : 0.5, 
        '&:last-child': { pb: isCollapsed ? 0.5 : 0.5 },
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: isCollapsed ? 0 : 1,
            cursor: 'pointer',
          }}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6" sx={{ mb: 0, fontSize: isCollapsed ? '1rem' : '1.1rem' }}>
              Command History
            </Typography>
            <Chip
              label={commandHistory.length}
              size="small"
              sx={{
                fontSize: '0.7rem',
                height: isCollapsed ? 18 : 20,
              }}
            />
          </Stack>
          <IconButton size="small">
            {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
          </IconButton>
        </Box>
        
        {/* Collapsible Content */}
        <Collapse in={!isCollapsed} timeout="auto">
          <Stack spacing={1}>
            {/* History List - with max height and scroll */}
            <Box sx={{ maxHeight: '160px', overflow: 'auto' }}>
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
                      py: 0.5,
                      px: 1,
                      minHeight: 'auto',
                      '&:hover': {
                        bgcolor: 'action.hover',
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      {item.success ? (
                        <SuccessIcon fontSize="small" color="success" />
                      ) : (
                        <ErrorIcon fontSize="small" color="error" />
                      )}
                    </ListItemIcon>
                    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, overflow: 'hidden' }}>
                      <Typography
                        sx={{
                          fontSize: '0.85rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          flex: 1,
                        }}
                      >
                        {item.prompt}
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: '0.7rem',
                          color: 'text.secondary',
                          flexShrink: 0,
                        }}
                      >
                        {formatTimestamp(item.timestamp)}
                      </Typography>
                    </Box>
                  </ListItemButton>
                </ListItem>
              ))}
              </List>
            </Box>
            
            {/* Show More / Clear Buttons */}
            <Stack direction="row" spacing={1} sx={{ pt: 0.5 }}>
              {commandHistory.length > 5 && (
                <Button
                  size="small"
                  onClick={() => setShowAll(!showAll)}
                  sx={{
                    textTransform: 'none',
                    fontSize: '0.75rem',
                    py: 0.5,
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
                  fontSize: '0.75rem',
                  py: 0.5,
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

