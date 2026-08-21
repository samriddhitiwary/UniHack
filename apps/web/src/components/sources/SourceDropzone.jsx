import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined'
import { Box, Button, LinearProgress, Stack, Typography } from '@mui/material'
import { useRef, useState } from 'react'
import { validateSourceFile } from '../../utils/sourceLabels'

export function SourceDropzone({ onUpload, uploading }) {
  const input = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const choose = (file) => {
    if (!file) return
    const validation = validateSourceFile(file)
    setError(validation || '')
    if (!validation) onUpload(file)
  }
  const openPicker = () => !uploading && input.current?.click()
  return (
    <Box
      role="button"
      tabIndex={uploading ? -1 : 0}
      aria-label="Upload product source file"
      onClick={openPicker}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          openPicker()
        }
      }}
      onDragEnter={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        choose(event.dataTransfer.files[0])
      }}
      sx={{
        border: '1px dashed',
        borderColor: dragging
          ? 'primary.main'
          : error
            ? 'error.main'
            : 'divider',
        bgcolor: dragging ? 'primary.light' : 'background.paper',
        borderRadius: 3,
        p: { xs: 4, md: 5 },
        cursor: uploading ? 'wait' : 'pointer',
        transition: 'all 180ms ease',
        '&:focus-visible': { outline: '3px solid rgba(99,102,241,.3)' },
      }}
    >
      <input
        ref={input}
        hidden
        type="file"
        aria-label="Choose product source file"
        accept=".pdf,.csv,.png,.jpg,.jpeg,.webp"
        onChange={(event) => {
          choose(event.target.files[0])
          event.target.value = ''
        }}
      />
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        gap={3}
        alignItems={{ sm: 'center' }}
      >
        <CloudUploadOutlinedIcon color="primary" />
        <Stack flex={1}>
          <Typography fontWeight={700}>Upload product source</Typography>
          <Typography color="text.secondary" variant="body2">
            <Box
              component="span"
              sx={{ display: { xs: 'none', sm: 'inline' } }}
            >
              Drag a file here or{' '}
            </Box>
            choose a PDF, CSV, or product image.
          </Typography>
          <Typography
            color={error ? 'error.main' : 'text.secondary'}
            variant="caption"
          >
            {error || 'PDF, PNG, JPEG, WEBP up to 10 MiB · CSV up to 5 MiB'}
          </Typography>
        </Stack>
        <Button variant="outlined" component="span" disabled={uploading}>
          {uploading ? 'Uploading…' : 'Choose File'}
        </Button>
      </Stack>
      {uploading && (
        <LinearProgress aria-label="Uploading source" sx={{ mt: 3 }} />
      )}
    </Box>
  )
}
