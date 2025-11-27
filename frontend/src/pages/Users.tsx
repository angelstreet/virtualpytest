import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Avatar,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  People as UsersIcon,
} from '@mui/icons-material';
import { useUsers, User } from '../hooks/pages/useUsers';
import { useTeams } from '../hooks/pages/useTeams';

/**
 * Users Management Page
 * Allows admins to manage users, assign them to teams, and update their profiles
 */
const Users: React.FC = () => {
  const {
    users,
    isLoading,
    error,
    updateUser,
    deleteUser,
    assignUserToTeam,
    isUpdating,
    isDeleting,
    updateError,
    deleteError,
  } = useUsers();

  const { teams } = useTeams();

  const [openDialog, setOpenDialog] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    role: 'tester' as 'admin' | 'tester' | 'viewer',
    teamId: '',
  });

  const handleOpenDialog = (user?: User) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        fullName: user.full_name,
        email: user.email,
        role: user.role,
        teamId: user.team_id || '',
      });
    } else {
      setEditingUser(null);
      setFormData({
        fullName: '',
        email: '',
        role: 'tester',
        teamId: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingUser(null);
    setFormData({ fullName: '', email: '', role: 'tester', teamId: '' });
  };

  const handleSaveUser = async () => {
    if (!editingUser) return;

    try {
      // Update user profile
      await updateUser({
        id: editingUser.id,
        payload: {
          full_name: formData.fullName,
          role: formData.role,
          team_id: formData.teamId || undefined,
        },
      });

      // If team changed, assign to new team
      if (formData.teamId && formData.teamId !== editingUser.team_id) {
        await assignUserToTeam({
          userId: editingUser.id,
          payload: {
            team_id: formData.teamId,
          },
        });
      }

      handleCloseDialog();
    } catch (err) {
      console.error('Error saving user:', err);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await deleteUser(userId);
      } catch (err) {
        console.error('Error deleting user:', err);
      }
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'error';
      case 'tester':
        return 'primary';
      case 'viewer':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <UsersIcon fontSize="large" color="primary" />
          <Typography variant="h4" component="h1">
            Users Management
          </Typography>
        </Box>
      </Box>

      {/* Error Messages */}
      {(error || updateError || deleteError) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || updateError || deleteError}
        </Alert>
      )}

      {/* Loading State */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Card>
        <CardContent>
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>User</strong></TableCell>
                  <TableCell><strong>Email</strong></TableCell>
                  <TableCell><strong>Role</strong></TableCell>
                  <TableCell><strong>Team</strong></TableCell>
                  <TableCell><strong>Joined</strong></TableCell>
                  <TableCell align="right"><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Avatar
                          src={user.avatar_url}
                          sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}
                        >
                          {user.full_name?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase()}
                        </Avatar>
                        <Typography variant="body1" fontWeight="medium">
                          {user.full_name || 'No name'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.role.toUpperCase()}
                        size="small"
                        color={getRoleColor(user.role)}
                      />
                    </TableCell>
                    <TableCell>{user.team || 'No team'}</TableCell>
                    <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleOpenDialog(user)}
                        disabled={isUpdating || isDeleting}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={isUpdating || isDeleting}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {users.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="textSecondary" sx={{ py: 4 }}>
                        No users found. Add your first user to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      )}

      {/* Edit User Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          Edit User
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Full Name"
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              fullWidth
              disabled
              helperText="Email cannot be changed"
            />
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={formData.role}
                label="Role"
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    role: e.target.value as 'admin' | 'tester' | 'viewer',
                  })
                }
              >
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="tester">Tester</MenuItem>
                <MenuItem value="viewer">Viewer</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Team</InputLabel>
              <Select
                value={formData.teamId}
                label="Team"
                onChange={(e) => setFormData({ ...formData, teamId: e.target.value })}
              >
                <MenuItem value="">
                  <em>No team</em>
                </MenuItem>
                {teams.map((team) => (
                  <MenuItem key={team.id} value={team.id}>
                    {team.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSaveUser}
            variant="contained"
            disabled={!formData.fullName.trim() || isUpdating}
          >
            {isUpdating ? 'Saving...' : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Users;

