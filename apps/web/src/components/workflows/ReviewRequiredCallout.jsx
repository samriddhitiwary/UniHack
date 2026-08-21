import RateReviewOutlinedIcon from '@mui/icons-material/RateReviewOutlined'
import { Alert, Button, Stack, Typography } from '@mui/material'

export function ReviewRequiredCallout({
  workflow,
  onReview,
  onResume,
  resuming,
}) {
  if (workflow.status !== 'WAITING_FOR_REVIEW') return null
  const readyToResume = workflow.nextAction === 'RESUME_WORKFLOW'
  return (
    <Alert
      severity="warning"
      icon={<RateReviewOutlinedIcon />}
      sx={{ minWidth: 0, '& .MuiAlert-message': { minWidth: 0 } }}
    >
      <Stack spacing={2} minWidth={0}>
        <Stack minWidth={0}>
          <Typography fontWeight={800}>Human Review Required</Typography>
          <Typography variant="body2">
            CatalogIQ has finished automated validation. Review the proposed
            product attributes before final catalog materialization.
          </Typography>
          <Typography variant="caption">
            Workflow paused at {workflow.progressPercent}%.
          </Typography>
        </Stack>
        <Stack direction="row" gap={2} flexWrap="wrap">
          {!readyToResume && (
            <Button variant="contained" color="warning" onClick={onReview}>
              Review Attributes
            </Button>
          )}
          {readyToResume && (
            <Button variant="contained" onClick={onResume} disabled={resuming}>
              {resuming ? 'Resuming…' : 'Resume Workflow'}
            </Button>
          )}
        </Stack>
      </Stack>
    </Alert>
  )
}
