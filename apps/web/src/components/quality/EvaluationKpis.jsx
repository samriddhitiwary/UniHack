import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded'
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined'
import GppGoodOutlinedIcon from '@mui/icons-material/GppGoodOutlined'
import RuleOutlinedIcon from '@mui/icons-material/RuleOutlined'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import { Box } from '@mui/material'
import { MetricCard } from '../common/MetricCard'
import { formatCount, formatPercent } from '../../utils/qualityFormat'

export function EvaluationKpis({ data }) {
  const {
    accuracy,
    coverageMetrics,
    batchMetrics,
    reviewMetrics,
    descriptionMetrics,
  } = data
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          xl: 'repeat(5, 1fr)',
        },
        gap: 4,
      }}
    >
      <MetricCard
        label="Labelled exact match"
        value={`${accuracy.exactMatchCount} / ${accuracy.evaluableFieldCount}`}
        helper="Populated expected fields · 2 labelled products"
        icon={<FactCheckOutlinedIcon fontSize="small" />}
      />
      <MetricCard
        label="Supported field coverage"
        value={formatPercent(coverageMetrics.supportedCoverageRateBp)}
        helper={`${(coverageMetrics.averagePopulatedFieldsBp / 100).toFixed(2)} average populated fields`}
        icon={<RuleOutlinedIcon fontSize="small" />}
      />
      <MetricCard
        label="Batch success"
        value={`${formatCount(batchMetrics.processedRows)} / ${formatCount(batchMetrics.totalRows)}`}
        helper={`${batchMetrics.failedRows} processing failures · not accuracy`}
        icon={<CheckCircleOutlineRoundedIcon fontSize="small" />}
      />
      <MetricCard
        label="Review required"
        value={formatPercent(reviewMetrics.reviewRequiredRateBp)}
        helper={`${formatCount(reviewMetrics.reviewRequiredCount)} rows require evidence review`}
        icon={<VisibilityOutlinedIcon fontSize="small" />}
      />
      <MetricCard
        label="Description grounding"
        value={formatPercent(descriptionMetrics.groundingComplianceBp)}
        helper={`${descriptionMetrics.unsupportedFactViolationCount} unsupported fact violations`}
        icon={<GppGoodOutlinedIcon fontSize="small" />}
      />
    </Box>
  )
}
