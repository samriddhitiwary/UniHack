import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import RateReviewOutlinedIcon from '@mui/icons-material/RateReviewOutlined'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import { Box, Button, Divider, Stack, Typography } from '@mui/material'
import { IntelligenceScore } from '../common/IntelligenceScore'
import { PageHeader } from '../common/PageHeader'
import { StatusBadge } from '../common/StatusBadge'
import { StaleIndicator } from '../products/StaleIndicator'
import { formatDateTime } from '../../utils/dateFormat'
import {
  categoryOptions,
  identityMetadata,
  optionLabel,
} from '../../utils/productLabels'

function SummaryItem({ label, children }) {
  return (
    <Stack spacing={1} minWidth={{ xs: 0, md: 150 }}>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      {children}
    </Stack>
  )
}

export function ProductWorkspaceHeader({
  product,
  summary,
  sourceCount,
  sourceCountPartial,
  workflow,
  onPrimaryAction,
}) {
  const projection = summary?.latestProjection
  const intelligence = summary?.latestIntelligence
  const action =
    workflow?.status === 'WAITING_FOR_REVIEW'
      ? { label: 'Review Required', icon: <RateReviewOutlinedIcon /> }
      : workflow?.status === 'RUNNING'
        ? { label: 'View Active Workflow', icon: <VisibilityOutlinedIcon /> }
        : {
            label: workflow
              ? 'Run New Workflow'
              : 'Start Intelligence Workflow',
            icon: <PlayArrowRoundedIcon />,
          }
  return (
    <Stack spacing={5}>
      <PageHeader
        title={product.name}
        subtitle={identityMetadata(product)}
        breadcrumbs={[
          { label: 'Products', href: '/products' },
          { label: product.name },
        ]}
        status={<StatusBadge status={product.status} />}
        actions={
          <Button
            variant="contained"
            startIcon={action.icon}
            onClick={onPrimaryAction}
          >
            {action.label}
          </Button>
        }
      />
      <Box
        sx={{
          bgcolor: 'primary.light',
          border: '1px solid',
          borderColor: 'primary.main',
          borderRadius: 3,
          px: { xs: 4, md: 6 },
          py: 4,
        }}
      >
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          divider={
            <Divider
              flexItem
              orientation="vertical"
              sx={{ display: { xs: 'none', md: 'block' } }}
            />
          }
          gap={{ xs: 4, md: 6 }}
        >
          <SummaryItem label="Product">
            <Stack direction="row" gap={2} flexWrap="wrap">
              <StatusBadge
                status="NEUTRAL"
                label={optionLabel(categoryOptions, product.category)}
              />
              <Typography color="text.secondary" variant="caption">
                Version {product.version ?? product.productVersion ?? '—'} ·
                Updated {formatDateTime(product.updatedAt)}
              </Typography>
            </Stack>
          </SummaryItem>
          <SummaryItem label="Publishing Readiness">
            <Stack
              direction="row"
              alignItems="center"
              gap={1.5}
              flexWrap="wrap"
            >
              {projection ? (
                <StatusBadge status={projection.status} />
              ) : (
                <Typography fontWeight={700}>Not evaluated</Typography>
              )}
              {projection?.projectionCurrent === false && (
                <StaleIndicator kind="projection" />
              )}
            </Stack>
          </SummaryItem>
          <SummaryItem label="Intelligence Score">
            <Stack
              direction="row"
              alignItems="center"
              gap={1.5}
              flexWrap="wrap"
            >
              {intelligence ? (
                <IntelligenceScore
                  compact
                  score={intelligence.overallScorePercent}
                  grade={intelligence.grade}
                />
              ) : (
                <Typography fontWeight={700}>Not scored</Typography>
              )}
              {intelligence?.intelligenceCurrent === false && (
                <StaleIndicator kind="intelligence" />
              )}
            </Stack>
          </SummaryItem>
          <SummaryItem label="Sources">
            <Typography fontWeight={700}>
              {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}
              {sourceCountPartial ? ' loaded' : ''}
            </Typography>
          </SummaryItem>
        </Stack>
      </Box>
    </Stack>
  )
}
