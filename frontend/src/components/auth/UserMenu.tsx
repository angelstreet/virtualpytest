import React, { useState } from 'react';
import {
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Typography,
  Divider,
  ListItemIcon,
  ListItemText,
  Chip,
} from '@mui/material';
import {
  Logout as LogoutIcon,
  Person as PersonIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useAuth } from '../../hooks/auth/useAuth';
import { useProfile } from '../../hooks/auth/useProfile';
import { useNavigate } from 'react-router-dom';
import { isAuthEnabled } from '../../lib/supabase';

/**
 * User Menu Component
 * Displays user avatar and dropdown menu with profile info and logout
 */
export const UserMenu: React.FC = () => {
  const { user, signOut } = useAuth();
  const { profile } = useProfile();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleProfile = () => {
    handleMenuClose();
    navigate('/profile');
  };

  const handleSettings = () => {
    handleMenuClose();
    navigate('/configuration/settings');
  };

  const handleLogout = async () => {
    handleMenuClose();
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Don't show user menu if auth is disabled or no user
  if (!isAuthEnabled || !user) {
    return null;
  }

  const displayName = profile?.full_name || user.email?.split('@')[0] || 'User';
  const avatarUrl = profile?.avatar_url || user.user_metadata?.avatar_url;

  return (
    <Box>
      <IconButton onClick={handleMenuOpen} size="small">
        <Avatar
          src={avatarUrl}
          alt={displayName}
          sx={{
            width: 32,
            height: 32,
            bgcolor: 'primary.main',
          }}
        >
          {displayName.charAt(0).toUpperCase()}
        </Avatar>
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        onClick={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          sx: { minWidth: 240, mt: 1 },
        }}
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" fontWeight="bold">
            {displayName}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {user.email}
          </Typography>
          {profile?.role && (
            <Chip
              label={profile.role.toUpperCase()}
              size="small"
              color={profile.role === 'admin' ? 'error' : profile.role === 'tester' ? 'primary' : 'default'}
              sx={{ mt: 1 }}
            />
          )}
        </Box>

        <Divider />

        <MenuItem onClick={handleProfile}>
          <ListItemIcon>
            <PersonIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Profile</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleSettings}>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>

        <Divider />

        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

