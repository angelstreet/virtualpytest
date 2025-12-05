import { KeyboardArrowDown, OpenInNew } from '@mui/icons-material';
import { Button, Menu, MenuItem, Box, Typography } from '@mui/material';
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { NavigationDropdownProps, NavigationItem } from '../../types/pages/Navigation_Types';

const NavigationDropdown: React.FC<NavigationDropdownProps> = ({ label, items }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExternalClick = (href: string) => {
    window.open(href, '_blank', 'noopener,noreferrer');
    handleClose();
  };

  // Check if any of the dropdown items match the current path (only internal links)
  const isDropdownActive = items.some((item) => !item.external && location.pathname.startsWith(item.path));

  const renderMenuItem = (item: NavigationItem) => {
    if (item.external && item.href) {
      // External link - opens in new tab
      return (
        <MenuItem
          key={item.href}
          onClick={() => handleExternalClick(item.href!)}
          sx={{
            py: 1.5,
            px: 2,
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          <Box display="flex" alignItems="center" gap={1} width="100%">
            {item.icon}
            <Typography variant="body2" sx={{ flex: 1 }}>{item.label}</Typography>
            <OpenInNew fontSize="small" sx={{ opacity: 0.5, ml: 1 }} />
          </Box>
        </MenuItem>
      );
    }

    // Internal link - uses React Router
    return (
      <MenuItem
        key={item.path}
        component={Link}
        to={item.path}
        onClick={handleClose}
        sx={{
          py: 1.5,
          px: 2,
          backgroundColor: location.pathname === item.path ? 'action.selected' : 'transparent',
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          {item.icon}
          <Typography variant="body2">{item.label}</Typography>
        </Box>
      </MenuItem>
    );
  };

  return (
    <Box>
      <Button
        onClick={handleClick}
        endIcon={<KeyboardArrowDown />}
        sx={{
          color: isDropdownActive ? 'secondary.main' : 'inherit',
          fontWeight: isDropdownActive ? 600 : 400,
          textTransform: 'none',
          px: 2,
          py: 1,
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          },
        }}
      >
        {label}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        PaperProps={{
          sx: {
            mt: 1,
            minWidth: 200,
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
          },
        }}
      >
        {items.map(renderMenuItem)}
      </Menu>
    </Box>
  );
};

export default NavigationDropdown;
