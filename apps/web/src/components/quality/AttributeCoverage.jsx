import { CardContent, Divider, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'
import { formatPercent, humanizeCode } from '../../utils/qualityFormat'

export function AttributeCoverage({ coverage, accuracy }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Attribute coverage"
            subtitle="Coverage uses all 1,000 products. Precision and recall use only the two officially labelled products."
          />
          <QualityBar
            label="Products with official attributes"
            valueBp={coverage.attributeCoverageBp}
            detail={`${coverage.productsWithAttributes.toLocaleString()} of ${coverage.totalRows.toLocaleString()} products`}
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={5}>
            <Stat
              label="Average attributes / product"
              value={(coverage.averageAttributesPerProductBp / 100).toFixed(2)}
            />
            <Stat
              label="Labelled semantic precision"
              value={formatOptional(accuracy.precisionBp)}
            />
            <Stat
              label="Labelled semantic recall"
              value={formatOptional(accuracy.recallBp)}
            />
          </Stack>
          <Divider />
          <Stack spacing={1.5}>
            <Typography variant="overline" color="text.secondary">
              Top extracted official labels
            </Typography>
            {coverage.topAttributeLabels.map((item) => (
              <Stack
                key={item.label}
                direction="row"
                justifyContent="space-between"
              >
                <Typography variant="body2">{item.label}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.count.toLocaleString()}
                </Typography>
              </Stack>
            ))}
          </Stack>
          <Divider />
          <Stack spacing={2}>
            <Typography variant="overline" color="text.secondary">
              Attribute review reasons
            </Typography>
            {coverage.reviewReasonCounts.map(([reason, count]) => (
              <QualityBar
                key={reason}
                label={humanizeCode(reason)}
                valueBp={
                  (count * 10000) /
                  Math.max(1, coverage.semanticCandidatesExtracted)
                }
                detail={`${count.toLocaleString()} candidates`}
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
      <Typography variant="h2">{value}</Typography>
    </Stack>
  )
}

function formatOptional(value) {
  return value == null ? 'Not evaluable' : formatPercent(value, 2)
}
