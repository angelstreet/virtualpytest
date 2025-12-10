import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import React from 'react';

import ThemeToggle from './ThemeToggle';

const Header: React.FC = () => {
  return (
    <AppBar 
      position="static" 
      elevation={1} 
      sx={{ 
        borderRadius: '0 !important',
        borderTopLeftRadius: '0 !important',
        borderTopRightRadius: '0 !important',
        borderBottomLeftRadius: '0 !important',
        borderBottomRightRadius: '0 !important',
        '& .MuiPaper-root': {
          borderRadius: '0 !important',
        }
      }}
    >
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          VirtualPyTest
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <ThemeToggle />
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
