import { Stack, Typography } from '@mui/material'

export function SectionHeader({ title, subtitle, action }) {
  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      justifyContent="space-between"
      alignItems="flex-start"
      gap={3}
    >
      <Stack spacing={0.75} minWidth={0}>
        <Typography component="h2" variant="h3">
          {title}
        </Typography>
        {subtitle && (
          <Typography color="text.secondary" variant="body2">
            {subtitle}
          </Typography>
        )}
      </Stack>
      {action}
    </Stack>
  )
}
