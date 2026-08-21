import { CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { QualityBar } from './QualityBar'

export function DescriptionCompliance({ metrics }) {
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Description compliance"
            subtitle="Deterministic formatting and grounding checks across generated descriptions."
          />
          <QualityBar
            label="INVOICE_DESC uppercase"
            valueBp={metrics.invoiceUppercaseComplianceBp}
          />
          <QualityBar
            label="INVOICE_DESC ≤ 40 characters"
            valueBp={metrics.invoiceMax40ComplianceBp}
          />
          <QualityBar
            label="MOBILE_DESC preferred 60–80"
            valueBp={metrics.mobilePreferredLengthRateBp}
            color="warning.main"
          />
          <QualityBar
            label="Description grounding"
            valueBp={metrics.groundingComplianceBp}
            color="success.main"
          />
          <QualityBar
            label="Numeric traceability"
            valueBp={metrics.numericTraceabilityBp}
            color="info.main"
          />
          <Stack
            direction="row"
            justifyContent="space-between"
            gap={2}
            sx={{ pt: 1 }}
          >
            <Typography color="text.secondary">
              Unsupported Fact Violations
            </Typography>
            <Typography fontWeight={750}>
              {metrics.unsupportedFactViolationCount}
            </Typography>
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
