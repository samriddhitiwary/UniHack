import { CardContent, Divider, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'
import { formatPercent, humanizeCode } from '../../utils/qualityFormat'

export function IdentityResolutionCoverage({ metrics }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Manufacturer and brand resolution"
            subtitle="Coverage and ambiguity describe all 1,000 rows; exact results use only two labelled products."
          />
          <Stack spacing={3}>
            <QualityBar
              label="Manufacturer resolution coverage"
              valueBp={metrics.manufacturerResolutionCoverageBp}
              detail={`${metrics.manufacturerResolved.toLocaleString()} resolved rows`}
            />
            <QualityBar
              label="Brand resolution coverage"
              valueBp={metrics.brandResolutionCoverageBp}
              detail={`${metrics.brandResolved.toLocaleString()} resolved rows`}
            />
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={5}>
            <Stat
              label="Supplier-only evidence"
              value={metrics.supplierOnlyRows}
            />
            <Stat
              label="Manufacturer ambiguity"
              value={metrics.manufacturerAmbiguous}
            />
            <Stat label="Brand ambiguity" value={metrics.brandAmbiguous} />
          </Stack>
          <Divider />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={5}>
            <Stat
              label="Labelled manufacturer exact"
              value={`${metrics.manufacturerExactLabelled} / ${metrics.labelledRows}`}
            />
            <Stat
              label="Labelled brand exact"
              value={`${metrics.brandExactLabelled} / ${metrics.labelledRows}`}
            />
          </Stack>
          <Typography variant="caption" color="text.secondary">
            Resolution coverage is not accuracy. Manufacturer and brand are
            resolved independently.
          </Typography>
          <Divider />
          <Stack spacing={1.5}>
            <Typography variant="overline" color="text.secondary">
              Identity evidence sources
            </Typography>
            {metrics.evidenceSourceCounts.map(([source, count]) => (
              <Row
                key={source}
                label={humanizeCode(source)}
                value={`${count} rows`}
              />
            ))}
          </Stack>
          <Divider />
          <Stack spacing={2}>
            <Typography variant="overline" color="text.secondary">
              Top identity review reasons
            </Typography>
            {metrics.reviewReasonCounts.slice(0, 5).map(([reason, count]) => (
              <QualityBar
                key={reason}
                label={humanizeCode(reason)}
                valueBp={(count * 10000) / Math.max(1, metrics.totalRows)}
                detail={`${count.toLocaleString()} rows · ${formatPercent((count * 10000) / metrics.totalRows)}`}
                color="warning.main"
              />
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}

function Stat({ label, value }) {
  return (
    <Stack>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h2">
        {Number.isInteger(value) ? value.toLocaleString() : value}
      </Typography>
    </Stack>
  )
}

function Row({ label, value }) {
  return (
    <Stack direction="row" justifyContent="space-between" gap={2}>
      <Typography variant="body2">{label}</Typography>
      <Typography variant="body2" color="text.secondary">
        {value}
      </Typography>
    </Stack>
  )
}
