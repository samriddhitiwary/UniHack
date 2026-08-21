import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined'
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import {
  Alert,
  Box,
  Button,
  CardContent,
  LinearProgress,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { StatusBadge } from '../common/StatusBadge'
import { formatDateTime } from '../../utils/dateFormat'
import { workflowErrorMessage } from '../../utils/workflowErrors'
import { workflowStatusLabels } from '../../utils/workflowLabels'
import { ReviewRequiredCallout } from './ReviewRequiredCallout'
import { WorkflowHistory } from './WorkflowHistory'
import { WorkflowOutputs } from './WorkflowOutputs'
import { WorkflowTimeline } from './WorkflowTimeline'

export function WorkflowSection({
  sourceCount,
  summary,
  historyQuery,
  workflowQuery,
  selectedId,
  onSelect,
  onLaunch,
  onReview,
  onResume,
  resumeMutation,
}) {
  const workflow = workflowQuery.data
  return (
    <Stack spacing={6}>
      <SectionHeader
        title="Intelligence Workflow"
        subtitle="Transform source evidence into a validated, commerce-ready catalog."
        action={
          workflow &&
          !['RUNNING', 'WAITING_FOR_REVIEW'].includes(workflow.status) ? (
            <Button startIcon={<PlayArrowRoundedIcon />} onClick={onLaunch}>
              Start New Workflow
            </Button>
          ) : undefined
        }
      />
      {historyQuery.isError && (
        <Alert
          severity="error"
          action={<Button onClick={() => historyQuery.refetch()}>Retry</Button>}
        >
          We couldn't load workflow history.
          {historyQuery.error.requestId &&
            ` Request ID: ${historyQuery.error.requestId}`}
        </Alert>
      )}
      {workflowQuery.isLoading ? (
        <AppCard>
          <CardContent>
            <Stack spacing={2} aria-label="Loading workflow">
              <Skeleton height={40} />
              <Skeleton height={180} />
            </Stack>
          </CardContent>
        </AppCard>
      ) : workflowQuery.isError ? (
        <Alert
          severity="error"
          action={
            <Button
              startIcon={<RefreshRoundedIcon />}
              onClick={() => workflowQuery.refetch()}
            >
              Retry
            </Button>
          }
        >
          We couldn't load this workflow.
          {workflowQuery.error.requestId &&
            ` Request ID: ${workflowQuery.error.requestId}`}
        </Alert>
      ) : !workflow ? (
        <AppCard>
          <CardContent sx={{ py: { xs: 8, md: 10 } }}>
            <Stack
              alignItems="center"
              textAlign="center"
              spacing={3}
              maxWidth={620}
              mx="auto"
            >
              <AutoAwesomeOutlinedIcon color="primary" sx={{ fontSize: 38 }} />
              <Stack spacing={1}>
                <Typography variant="h2">
                  {sourceCount
                    ? 'Ready to build intelligence'
                    : 'Build Product Intelligence'}
                </Typography>
                <Typography color="text.secondary">
                  CatalogIQ will analyze sources, structure technical
                  attributes, validate inconsistencies, prepare human review,
                  and generate catalog outputs.
                </Typography>
              </Stack>
              {!sourceCount && (
                <Alert severity="info">
                  Add at least one source before starting product intelligence.
                </Alert>
              )}
              <Button
                variant="contained"
                startIcon={<PlayArrowRoundedIcon />}
                disabled={!sourceCount}
                onClick={onLaunch}
              >
                Start Intelligence Workflow
              </Button>
            </Stack>
          </CardContent>
        </AppCard>
      ) : (
        <Stack spacing={5}>
          <ReviewRequiredCallout
            workflow={workflow}
            onReview={onReview}
            onResume={onResume}
            resuming={resumeMutation.isPending}
          />
          {resumeMutation.isError && (
            <Alert severity="warning">
              {workflowErrorMessage(resumeMutation.error)}
              {resumeMutation.error.requestId &&
                ` · Request ID: ${resumeMutation.error.requestId}`}
            </Alert>
          )}
          <AppCard>
            <CardContent sx={{ p: { xs: 5, md: 6 } }}>
              <Stack spacing={5}>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  justifyContent="space-between"
                  gap={3}
                >
                  <Stack>
                    <Typography variant="h2">
                      Catalog Intelligence Workflow
                    </Typography>
                    <Typography color="text.secondary">
                      Started{' '}
                      {formatDateTime(workflow.startedAt || workflow.createdAt)}
                    </Typography>
                  </Stack>
                  <StatusBadge
                    status={workflow.status}
                    label={workflowStatusLabels[workflow.status]}
                  />
                </Stack>
                <Stack spacing={1}>
                  <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    justifyContent="space-between"
                    gap={1}
                  >
                    <Typography fontWeight={700}>
                      {workflow.progressPercent}% complete
                    </Typography>
                    <Typography color="text.secondary" variant="caption">
                      Backend workflow progress
                    </Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={workflow.progressPercent}
                    aria-label="Workflow progress"
                    aria-valuenow={workflow.progressPercent}
                    sx={{ height: 7, borderRadius: 99 }}
                  />
                </Stack>
                {workflow.status === 'FAILED' && (
                  <Alert severity="error">
                    <Typography fontWeight={700}>Workflow Failed</Typography>
                    <Typography variant="body2">
                      {workflowErrorMessage(workflow)}
                    </Typography>
                    {workflow.errorCode && (
                      <Typography variant="caption">
                        Error code: {workflow.errorCode}
                      </Typography>
                    )}
                  </Alert>
                )}
                {workflow.status === 'COMPLETED' && (
                  <Alert severity="success">
                    Catalog Intelligence Complete. The catalog was structured
                    and evaluated.
                  </Alert>
                )}
                {workflow.status === 'COMPLETED_WITH_WARNINGS' && (
                  <Alert severity="warning">
                    Completed with Warnings. Review readiness and optional
                    output states below.
                  </Alert>
                )}
                <WorkflowOutputs workflow={workflow} summary={summary} />
                <Box>
                  <Typography variant="h3" sx={{ mb: 4 }}>
                    Pipeline
                  </Typography>
                  <WorkflowTimeline workflow={workflow} />
                </Box>
              </Stack>
            </CardContent>
          </AppCard>
        </Stack>
      )}
      <WorkflowHistory
        query={historyQuery}
        selectedId={selectedId}
        onSelect={onSelect}
      />
    </Stack>
  )
}
