import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import { Box, Button, Stack, Typography } from '@mui/material'

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon = <Inventory2OutlinedIcon />,
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
          color: 'primary.main',
          bgcolor: 'primary.light',
          borderRadius: 3,
        }}
      >
        {icon}
      </Box>
      <Stack spacing={1} maxWidth={480}>
        <Typography component="h2" variant="h3">
          {title}
        </Typography>
        <Typography color="text.secondary">{description}</Typography>
      </Stack>
      {actionLabel && (
        <Button variant="contained" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Stack>
  )
}
