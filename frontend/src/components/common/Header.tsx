import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import React from 'react';

import ThemeToggle from './ThemeToggle';

const Header: React.FC = () => {
  return (
    <AppBar position="static" elevation={1} sx={{ borderRadius: 0 }}>
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
