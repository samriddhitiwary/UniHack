import { Box, Stack, Typography } from '@mui/material'
import { formatPercent } from '../../utils/qualityFormat'

export function QualityBar({ label, valueBp, color = 'primary.main', detail }) {
  const width = Math.max(0, Math.min(100, (valueBp ?? 0) / 100))
  return (
    <Stack spacing={1.25}>
      <Stack direction="row" justifyContent="space-between" gap={2}>
        <Typography variant="body2" fontWeight={650}>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {detail ?? formatPercent(valueBp)}
        </Typography>
      </Stack>
      <Box
        role="img"
        aria-label={`${label}: ${detail ?? formatPercent(valueBp)}`}
        sx={{
          height: 8,
          bgcolor: 'grey.100',
          borderRadius: 999,
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            width: `${width}%`,
            height: '100%',
            bgcolor: color,
            borderRadius: 999,
          }}
        />
      </Box>
    </Stack>
  )
}
