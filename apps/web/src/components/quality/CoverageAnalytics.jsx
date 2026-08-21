import { CardContent, Chip, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'
import { formatPercent, humanizeCode } from '../../utils/qualityFormat'

export function CoverageAnalytics({ coverage }) {
  const strategies = coverage.strategyCoverage.filter(
    (item) => item.strategy !== 'UNSUPPORTED',
  )
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={5}>
          <SectionHeader
            title="Delivery coverage"
            subtitle="Coverage describes populated output, not correctness. External-only blanks are expected."
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Chip
              label={`Average ${(coverage.averagePopulatedFieldsBp / 100).toFixed(2)} / 252`}
            />
            <Chip label={`Median ${coverage.medianPopulatedFields}`} />
            <Chip
              label={`Range ${coverage.minimumPopulatedFields}–${coverage.maximumPopulatedFields}`}
            />
          </Stack>
          <QualityBar
            label="Raw 252-field coverage"
            valueBp={coverage.rawCoverageRateBp}
          />
          <QualityBar
            label="Supported-field coverage"
            valueBp={coverage.supportedCoverageRateBp}
            color="info.main"
          />
          <Stack spacing={2.5}>
            <Typography variant="overline" color="text.secondary">
              Coverage by strategy
            </Typography>
            {strategies.map((item) => (
              <QualityBar
                key={item.strategy}
                label={humanizeCode(item.strategy)}
                valueBp={item.coverageRateBp}
                detail={`${formatPercent(item.coverageRateBp)} · ${item.populatedCount.toLocaleString()} populated`}
              />
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
