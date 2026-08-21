import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined'
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import { Alert, Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { StatusBadge } from '../common/StatusBadge'
import { workflowStatusLabels } from '../../utils/workflowLabels'

function StateRow({ label, children }) {
  return (
    <Stack direction="row" justifyContent="space-between" gap={3}>
      <Typography color="text.secondary">{label}</Typography>
      <Box textAlign="right">{children}</Box>
    </Stack>
  )
}

export function ProductOverview({ product, summary, sources, workflow }) {
  const typeCount = new Set(sources.map((source) => source.sourceType)).size
  return (
    <Stack spacing={5}>
      {workflow?.status === 'WAITING_FOR_REVIEW' && (
        <Alert severity="warning" icon={<WarningAmberRoundedIcon />}>
          Automated validation is complete. Human review is required before the
          catalog can be finalized.
        </Alert>
      )}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1.35fr 1fr' },
          gap: 4,
        }}
      >
        <AppCard>
          <CardContent sx={{ p: 6 }}>
            <Stack spacing={4}>
              <SectionHeader
                title="Current Catalog State"
                subtitle="The latest Product and catalog intelligence state."
              />
              <StateRow label="Product status">
                <StatusBadge status={product.status} />
              </StateRow>
              <StateRow label="Publishing readiness">
                {summary?.latestProjection ? (
                  <StatusBadge status={summary.latestProjection.status} />
                ) : (
                  <Typography>Not evaluated</Typography>
                )}
              </StateRow>
              <StateRow label="Intelligence score">
                <Typography fontWeight={700}>
                  {summary?.latestIntelligence
                    ? `${summary.latestIntelligence.overallScorePercent} · ${summary.latestIntelligence.grade}`
                    : 'Not scored'}
                </Typography>
              </StateRow>
              <StateRow label="Latest workflow">
                {workflow ? (
                  <StatusBadge
                    status={workflow.status}
                    label={workflowStatusLabels[workflow.status]}
                  />
                ) : (
                  <Typography>Not started</Typography>
                )}
              </StateRow>
            </Stack>
          </CardContent>
        </AppCard>
        <Stack spacing={4}>
          <AppCard variant="subtle">
            <CardContent sx={{ p: 5 }}>
              <Stack direction="row" gap={3} alignItems="flex-start">
                <Inventory2OutlinedIcon color="primary" />
                <Stack>
                  <Typography fontWeight={700}>Source Evidence</Typography>
                  <Typography color="text.secondary">
                    {sources.length} loaded across {typeCount} source
                    {typeCount === 1 ? ' type' : ' types'}.
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </AppCard>
          <AppCard variant="subtle">
            <CardContent sx={{ p: 5 }}>
              <Stack direction="row" gap={3} alignItems="flex-start">
                <AutoAwesomeOutlinedIcon color="primary" />
                <Stack>
                  <Typography fontWeight={700}>Optional Outputs</Typography>
                  <Typography color="text.secondary">
                    AI content{' '}
                    {summary?.enrichmentAvailable
                      ? 'generated'
                      : 'not generated'}{' '}
                    · Export{' '}
                    {summary?.exportAvailable ? 'available' : 'not available'}
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </AppCard>
        </Stack>
      </Box>
    </Stack>
  )
}
