import { Button, Stack, Typography } from '@mui/material'

export function CursorPagination({
  canPrevious,
  canNext,
  onPrevious,
  onNext,
  loading,
}) {
  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      justifyContent="space-between"
      alignItems={{ sm: 'center' }}
      gap={3}
      sx={{ px: 4, py: 3 }}
    >
      <Typography color="text.secondary" variant="body2">
        Showing up to 20 products
      </Typography>
      <Stack direction="row" spacing={2}>
        <Button
          variant="outlined"
          disabled={!canPrevious || loading}
          onClick={onPrevious}
        >
          Previous
        </Button>
        <Button
          variant="outlined"
          disabled={!canNext || loading}
          onClick={onNext}
        >
          Next
        </Button>
      </Stack>
    </Stack>
  )
}
