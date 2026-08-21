import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material'
import { sourceName } from '../../utils/sourceLabels'

export function DeleteSourceDialog({ source, onClose, onConfirm, mutation }) {
  return (
    <Dialog
      open={Boolean(source)}
      onClose={mutation.isPending ? undefined : onClose}
    >
      <DialogTitle>Delete this source?</DialogTitle>
      <DialogContent>
        <DialogContentText>
          This removes {source ? sourceName(source) : 'the source'} and its
          stored file from CatalogIQ. Historical workflow results may reference
          earlier artifacts.
        </DialogContentText>
        {mutation.isError && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {mutation.error.message}
            {mutation.error.requestId &&
              ` · Request ID: ${mutation.error.requestId}`}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button
          color="error"
          variant="contained"
          disabled={mutation.isPending}
          onClick={onConfirm}
        >
          {mutation.isPending ? 'Deleting…' : 'Delete Source'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
