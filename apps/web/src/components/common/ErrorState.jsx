import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded'
import { Box, Button, Stack, Typography } from '@mui/material'

export function ErrorState({
  title = "We couldn't load catalog intelligence.",
  description = 'Please try again. If the problem continues, share the request ID with support.',
  requestId,
  onRetry,
}) {
  return (
    <Stack
      alignItems="center"
      textAlign="center"
      spacing={3}
      sx={{ py: { xs: 8, md: 12 }, px: 4 }}
    >
      <Box
        sx={{
          width: 48,
          height: 48,
          display: 'grid',
          placeItems: 'center',
          color: 'error.main',
          bgcolor: '#fef2f2',
          borderRadius: 3,
        }}
      >
        <ErrorOutlineRoundedIcon />
      </Box>
      <Stack spacing={1} maxWidth={520}>
        <Typography component="h2" variant="h3">
          {title}
        </Typography>
        <Typography color="text.secondary">{description}</Typography>
        {requestId && (
          <Typography color="text.secondary" variant="caption">
            Request ID: {requestId}
          </Typography>
        )}
      </Stack>
      {onRetry && (
        <Button variant="outlined" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Stack>
  )
}
