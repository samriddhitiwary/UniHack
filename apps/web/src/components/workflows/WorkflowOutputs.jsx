import { Box, Stack, Typography } from '@mui/material'
import { IntelligenceScore } from '../common/IntelligenceScore'
import { StatusBadge } from '../common/StatusBadge'

function Output({ label, children }) {
  return (
    <Box sx={{ p: 3, bgcolor: 'grey.50', borderRadius: 2, minWidth: 0 }}>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      <Box sx={{ mt: 1 }}>{children}</Box>
    </Box>
  )
}

export function WorkflowOutputs({ workflow, summary }) {
  const projection = summary?.latestProjection
  const intelligence = summary?.latestIntelligence
  if (
    !workflow.projectionId &&
    !workflow.exportId &&
    !workflow.enrichmentId &&
    !workflow.scoreId
  )
    return null
  return (
    <Stack
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          xl: 'repeat(4, 1fr)',
        },
        gap: 3,
      }}
    >
      {workflow.projectionId && (
        <Output label="Catalog Projection">
          <StatusBadge
            status={
              projection?.status === 'BLOCKED'
                ? 'REVIEW_REQUIRED'
                : projection?.status
            }
            label={
              projection?.status === 'BLOCKED'
                ? 'Blocked — needs attention'
                : projection?.status
                  ? undefined
                  : 'Generated'
            }
          />
        </Output>
      )}
      {workflow.enrichmentId && (
        <Output label="AI Commerce Content">
          <StatusBadge status="COMPLETED" label="Generated" />
        </Output>
      )}
      {workflow.exportId && (
        <Output label="Export Package">
          <StatusBadge status="READY" label="Available" />
        </Output>
      )}
      {workflow.scoreId && (
        <Output label="Intelligence">
          {intelligence ? (
            <IntelligenceScore
              compact
              score={intelligence.overallScorePercent}
              grade={intelligence.grade}
            />
          ) : (
            <Typography>Calculated</Typography>
          )}
        </Output>
      )}
    </Stack>
  )
}
