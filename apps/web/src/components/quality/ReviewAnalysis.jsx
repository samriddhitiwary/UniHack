import { CardContent, Divider, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'
import { formatPercent, humanizeCode } from '../../utils/qualityFormat'

export function ReviewAnalysis({ metrics }) {
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Review and confidence"
            subtitle="Confidence is a deterministic score, not a statistical probability."
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={5}>
            <Stack>
              <Typography variant="caption" color="text.secondary">
                Average confidence
              </Typography>
              <Typography variant="h2">
                {formatPercent(metrics.averageConfidenceBp, 2)}
              </Typography>
            </Stack>
            <Stack>
              <Typography variant="caption" color="text.secondary">
                Median confidence
              </Typography>
              <Typography variant="h2">
                {formatPercent(metrics.medianConfidenceBp, 2)}
              </Typography>
            </Stack>
          </Stack>
          <Divider />
          <Stack spacing={2.5}>
            <Typography variant="overline" color="text.secondary">
              Confidence distribution
            </Typography>
            {metrics.confidenceBands.map((item) => (
              <QualityBar
                key={item.band}
                label={humanizeCode(item.band)}
                valueBp={item.rateBp}
                detail={`${item.count.toLocaleString()} rows · ${formatPercent(item.rateBp)}`}
                color={
                  item.band === 'HIGH'
                    ? 'success.main'
                    : item.band === 'MEDIUM'
                      ? 'warning.main'
                      : 'error.main'
                }
              />
            ))}
          </Stack>
          <Divider />
          <Stack spacing={2.5}>
            <Typography variant="overline" color="text.secondary">
              Review reason breakdown
            </Typography>
            {metrics.reasonCounts.map(([reason, count]) => (
              <QualityBar
                key={reason}
                label={humanizeCode(reason)}
                valueBp={
                  (count * 10000) / Math.max(1, metrics.reviewRequiredCount)
                }
                detail={`${count.toLocaleString()} rows`}
                color="warning.main"
              />
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
