import { Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from './AppCard'

export function MetricCard({ label, value, helper, icon }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: 5, '&:last-child': { pb: 5 } }}>
        <Stack spacing={4}>
          <Stack direction="row" alignItems="center" spacing={3}>
            <Box
              sx={{
                display: 'grid',
                placeItems: 'center',
                width: 36,
                height: 36,
                borderRadius: 2.5,
                color: 'primary.main',
                bgcolor: 'primary.light',
              }}
            >
              {icon}
            </Box>
            <Typography color="text.secondary" fontWeight={650}>
              {label}
            </Typography>
          </Stack>
          <Stack spacing={0.5}>
            <Typography
              sx={{
                fontSize: { xs: 28, md: 32 },
                lineHeight: 1.05,
                fontWeight: 720,
                letterSpacing: '-.035em',
              }}
            >
              {value}
            </Typography>
            {helper && (
              <Typography color="text.secondary" variant="caption">
                {helper}
              </Typography>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
