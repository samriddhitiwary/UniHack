import { Box, CardContent, Chip, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { formatCount, formatPercent } from '../../utils/qualityFormat'

const segments = [
  ['exactMatchCount', 'Exact', 'success.main'],
  ['normalizedMatchCount', 'Normalized', 'info.main'],
  ['mismatchCount', 'Mismatch', 'error.main'],
  [
    'expectedPopulatedActualBlankCount',
    'Expected value missing',
    'warning.main',
  ],
]

export function GroundTruthAccuracy({ accuracy, labelledRowCount }) {
  const total = Math.max(1, accuracy.evaluableFieldCount)
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={5}>
          <SectionHeader
            title="Ground-truth accuracy"
            subtitle="Content correctness across populated official expected fields. Both-blank cells are excluded."
            action={
              <Chip
                size="small"
                label={`${labelledRowCount} labelled products`}
              />
            }
          />
          <Stack
            direction="row"
            height={12}
            borderRadius={999}
            overflow="hidden"
            aria-label="Ground-truth match breakdown"
          >
            {segments.map(([key, label, color]) => (
              <Box
                key={key}
                title={`${label}: ${accuracy[key]}`}
                sx={{
                  width: `${(accuracy[key] / total) * 100}%`,
                  bgcolor: color,
                }}
              />
            ))}
          </Stack>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'repeat(2, 1fr)',
                sm: 'repeat(4, 1fr)',
              },
              gap: 3,
            }}
          >
            {segments.map(([key, label, color]) => (
              <Stack key={key} spacing={0.5}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: color,
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {label}
                  </Typography>
                </Stack>
                <Typography variant="h3">
                  {formatCount(accuracy[key])}
                </Typography>
              </Stack>
            ))}
          </Box>
          <Typography variant="body2" color="text.secondary">
            Exact match rate: {formatPercent(accuracy.exactMatchRateBp)} of{' '}
            {accuracy.evaluableFieldCount} evaluable populated expected values.
          </Typography>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
