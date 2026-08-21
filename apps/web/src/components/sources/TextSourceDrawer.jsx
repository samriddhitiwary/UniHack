import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { Controller, useForm } from 'react-hook-form'
import { useEffect } from 'react'
import { z } from 'zod'

const schema = z.object({
  displayName: z
    .string()
    .max(200, 'Source name must contain at most 200 characters.'),
  textContent: z
    .string()
    .trim()
    .min(1, 'Source text is required.')
    .max(50000, 'Source text must contain at most 50,000 characters.'),
})

export function TextSourceDrawer({ open, onClose, onSubmit, mutation }) {
  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { displayName: '', textContent: '' },
  })
  const text = watch('textContent')
  useEffect(() => {
    if (!open) reset()
  }, [open, reset])
  const close = () => {
    if (mutation.isPending) return
    mutation.reset()
    reset()
    onClose()
  }
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={close}
      PaperProps={{
        role: 'dialog',
        'aria-labelledby': 'text-source-title',
        sx: { width: { xs: '100%', sm: 560 }, maxWidth: '100%' },
      }}
    >
      <Stack
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        minHeight="100%"
      >
        <Stack direction="row" justifyContent="space-between" sx={{ p: 5 }}>
          <Stack spacing={1}>
            <Typography id="text-source-title" variant="h2">
              Add Text Source
            </Typography>
            <Typography color="text.secondary">
              Paste trusted product information from an email or specification
              sheet.
            </Typography>
          </Stack>
          <IconButton aria-label="Close text source" onClick={close}>
            <CloseRoundedIcon />
          </IconButton>
        </Stack>
        <Divider />
        <Stack spacing={4} sx={{ p: 5, flex: 1 }}>
          {mutation.isError && (
            <Alert severity="error">
              {mutation.error.message}
              {mutation.error.requestId &&
                ` · Request ID: ${mutation.error.requestId}`}
            </Alert>
          )}
          <Controller
            name="displayName"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Source name"
                autoFocus
                error={Boolean(errors.displayName)}
                helperText={errors.displayName?.message || 'Optional'}
              />
            )}
          />
          <Controller
            name="textContent"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Source text"
                multiline
                minRows={12}
                error={Boolean(errors.textContent)}
                helperText={
                  errors.textContent?.message ||
                  `${text.length.toLocaleString()} / 50,000`
                }
              />
            )}
          />
        </Stack>
        <Divider />
        <Box sx={{ p: 4 }}>
          <Stack direction="row" justifyContent="flex-end" gap={2}>
            <Button onClick={close} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={mutation.isPending}
            >
              {mutation.isPending && (
                <CircularProgress size={16} sx={{ mr: 1 }} />
              )}
              {mutation.isPending ? 'Adding…' : 'Add Text Source'}
            </Button>
          </Stack>
        </Box>
      </Stack>
    </Drawer>
  )
}
