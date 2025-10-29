import { KeyboardArrowDown } from '@mui/icons-material';
import { Button, Menu, MenuItem, Box, Typography } from '@mui/material';
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { NavigationGroupedDropdownProps } from '../../types/pages/Navigation_Types';

const NavigationGroupedDropdown: React.FC<NavigationGroupedDropdownProps> = ({ label, groups }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  // Check if any of the grouped items match the current path
  const isDropdownActive = groups.some((group) =>
    group.items.some((item) => location.pathname.startsWith(item.path))
  );

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
            minWidth: 800,
            maxWidth: 960,
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
          },
        }}
      >
        {/* Four-column grid layout */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 0,
            p: 0,
          }}
        >
          {groups.map((group, groupIndex) => (
            <Box
              key={group.sectionLabel}
              sx={{
                borderRight: groupIndex < groups.length - 1 ? '1px solid rgba(0, 0, 0, 0.08)' : 'none',
              }}
            >
              {/* Section Header */}
              <Box
                sx={{
                  px: 2,
                  py: 0.75,
                  backgroundColor: 'rgba(0, 0, 0, 0.03)',
                  borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    letterSpacing: '0.5px',
                    color: 'text.secondary',
                    textTransform: 'uppercase',
                  }}
                >
                  {group.sectionLabel}
                </Typography>
              </Box>

              {/* Section Items */}
              {group.items.map((item) => (
                <MenuItem
                  key={item.path}
                  component={Link}
                  to={item.path}
                  onClick={handleClose}
                  sx={{
                    py: 0.75,
                    px: 2,
                    fontSize: '0.875rem',
                    backgroundColor: location.pathname === item.path ? 'action.selected' : 'transparent',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    {item.icon}
                    <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                      {item.label}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Box>
          ))}
        </Box>
      </Menu>
    </Box>
  );
};

export default NavigationGroupedDropdown;
