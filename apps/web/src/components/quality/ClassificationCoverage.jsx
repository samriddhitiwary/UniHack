import { CardContent, Divider, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'
import { humanizeCode } from '../../utils/qualityFormat'

export function ClassificationCoverage({ metrics }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Verified classification coverage"
            subtitle="Product types come from observed descriptions; Classpaths require an official or human-verified mapping."
          />
          <QualityBar
            label="Resolved product type"
            valueBp={metrics.productTypeCoverageBp}
            detail={`${metrics.resolvedProductTypeCount.toLocaleString()} of ${metrics.totalRows.toLocaleString()} rows`}
          />
          <QualityBar
            label="Verified Classpath"
            valueBp={metrics.verifiedClasspathCoverageBp}
            detail={`${metrics.verifiedClasspathCount.toLocaleString()} rows`}
            color="success.main"
          />
          <Divider />
          <Stack spacing={2}>
            <Typography variant="overline" color="text.secondary">
              Classification review reasons
            </Typography>
            {metrics.reasonCounts.map(([reason, count]) => (
              <QualityBar
                key={reason}
                label={humanizeCode(reason)}
                valueBp={(count * 10000) / Math.max(1, metrics.totalRows)}
                detail={`${count.toLocaleString()} rows`}
                color="warning.main"
              />
            ))}
          </Stack>
          <Divider />
          <Stack spacing={1.5}>
            <Typography variant="overline" color="text.secondary">
              Top resolved product types
            </Typography>
            {metrics.topProductTypes.map((item) => (
              <Stack
                key={item.productType}
                direction="row"
                justifyContent="space-between"
              >
                <Typography variant="body2">{item.productType}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.count.toLocaleString()}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
