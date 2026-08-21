import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded'
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded'
import { Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { formatCount, formatPercent } from '../../utils/qualityFormat'

const items = [
  [
    'processedRows',
    'Processed successfully',
    'success',
    CheckCircleRoundedIcon,
  ],
  ['reviewRequiredRows', 'Review required', 'warning', VisibilityRoundedIcon],
  ['failedRows', 'Failed', 'error', ErrorOutlineRoundedIcon],
]

export function BatchHealth({ batch }) {
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Batch health"
            subtitle="Review-required rows processed successfully; review is not failure."
          />
          {items.map(([key, label, semantic, Icon]) => (
            <Stack
              key={key}
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              gap={2}
            >
              <Stack direction="row" alignItems="center" spacing={2}>
                <Box
                  sx={{
                    display: 'grid',
                    placeItems: 'center',
                    width: 34,
                    height: 34,
                    borderRadius: 2,
                    bgcolor: `${semantic}.light`,
                    color: `${semantic}.main`,
                  }}
                >
                  <Icon fontSize="small" />
                </Box>
                <Typography fontWeight={650}>{label}</Typography>
              </Stack>
              <Typography variant="h3">{formatCount(batch[key])}</Typography>
            </Stack>
          ))}
          <Typography variant="body2" color="text.secondary">
            Processing success: {formatPercent(batch.processingSuccessRateBp)}.
            This is reliability, not product accuracy.
          </Typography>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
