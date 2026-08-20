import { Box, Stack, Typography } from '@mui/material'
import { StatusBadge } from './StatusBadge'

function gradeFor(score) {
  if (score >= 90) return 'EXCELLENT'
  if (score >= 75) return 'GOOD'
  if (score >= 60) return 'FAIR'
  if (score >= 40) return 'POOR'
  return 'CRITICAL'
}
export function IntelligenceScore({
  score,
  grade = gradeFor(score),
  compact = false,
}) {
  if (compact)
    return (
      <Stack direction="row" alignItems="center" spacing={2}>
        <Typography fontWeight={700}>{score}</Typography>
        <StatusBadge status={grade} />
      </Stack>
    )
  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography sx={{ fontSize: 28, fontWeight: 720 }}>
          {score}
          <Typography component="span" color="text.secondary" variant="body2">
            {' '}
            / 100
          </Typography>
        </Typography>
        <StatusBadge status={grade} />
      </Stack>
      <Box
        role="progressbar"
        aria-label="Intelligence score"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        sx={{
          height: 6,
          borderRadius: 99,
          bgcolor: 'grey.200',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            height: '100%',
            width: `${score}%`,
            bgcolor: 'primary.main',
            borderRadius: 'inherit',
          }}
        />
      </Box>
    </Stack>
  )
}
