import { Dialog, DialogProps, styled } from '@mui/material';

/**
 * Consistent styled Dialog component with border and white button borders
 */
export const StyledDialog = styled(Dialog)(({ theme }) => ({
  '& .MuiDialog-paper': {
    border: `2px solid ${theme.palette.primary.main}`,
    borderRadius: theme.spacing(1),
  },
  '& .MuiDialogActions-root': {
    '& .MuiButton-outlined, & .MuiButton-contained': {
      border: '2px solid white',
      '&:hover': {
        border: '2px solid white',
      },
    },
  },
}));

export default StyledDialog;

