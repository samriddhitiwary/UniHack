import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import ErrorRoundedIcon from '@mui/icons-material/ErrorRounded'
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded'
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded'
import RemoveCircleOutlineRoundedIcon from '@mui/icons-material/RemoveCircleOutlineRounded'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Stack,
  Typography,
} from '@mui/material'
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded'
import { buildWorkflowPhases } from '../../utils/workflowPhases'
import { stageLabels, stageStatusLabels } from '../../utils/workflowLabels'
import { formatDateTime } from '../../utils/dateFormat'

const icons = {
  COMPLETED: CheckCircleRoundedIcon,
  RUNNING: AutorenewRoundedIcon,
  WAITING: PersonOutlineRoundedIcon,
  FAILED: ErrorRoundedIcon,
  SKIPPED: RemoveCircleOutlineRoundedIcon,
  NOT_STARTED: RadioButtonUncheckedRoundedIcon,
}
const colors = {
  COMPLETED: 'success.main',
  RUNNING: 'info.main',
  WAITING: 'warning.main',
  FAILED: 'error.main',
  SKIPPED: 'text.disabled',
  NOT_STARTED: 'text.disabled',
}

export function WorkflowTimeline({ workflow }) {
  const phases = buildWorkflowPhases(workflow.stages)
  return (
    <Stack aria-label="Workflow timeline">
      {phases.map((phase, index) => {
        const Icon = icons[phase.status]
        return (
          <Stack key={phase.id} direction="row" gap={3}>
            <Stack alignItems="center" width={28} flexShrink={0}>
              <Icon color="inherit" sx={{ color: colors[phase.status] }} />
              {index < phases.length - 1 && (
                <Box
                  sx={{ width: 1, minHeight: 56, flex: 1, bgcolor: 'divider' }}
                />
              )}
            </Stack>
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                flex: 1,
                minWidth: 0,
                pb: 2,
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreRoundedIcon />}
                aria-label={`${phase.label} technical details`}
                sx={{ px: 0, minHeight: 42 }}
              >
                <Stack minWidth={0}>
                  <Typography fontWeight={700}>
                    {phase.label} — {stageStatusLabels[phase.status]}
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    {phase.description}
                  </Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails sx={{ px: 0 }}>
                <Stack spacing={2}>
                  {phase.children.map((stage) => (
                    <Box
                      key={stage.stage}
                      sx={{
                        pl: 2,
                        borderLeft: '2px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <Typography variant="body2" fontWeight={700}>
                        {stageLabels[stage.stage]} —{' '}
                        {stageStatusLabels[stage.status]}
                      </Typography>
                      <Typography
                        color="text.secondary"
                        variant="caption"
                        component="div"
                      >
                        {stage.startedAt &&
                          `Started ${formatDateTime(stage.startedAt)}`}
                        {stage.completedAt &&
                          ` · Completed ${formatDateTime(stage.completedAt)}`}
                      </Typography>
                      {stage.skipReason && (
                        <Typography color="text.secondary" variant="caption">
                          Reason:{' '}
                          {stage.skipReason.replaceAll('_', ' ').toLowerCase()}
                        </Typography>
                      )}
                      {stage.errorMessage && (
                        <Typography
                          color="error.main"
                          variant="caption"
                          sx={{ overflowWrap: 'anywhere' }}
                        >
                          {stage.errorMessage}
                        </Typography>
                      )}
                      {(stage.jobId ||
                        stage.resultReference ||
                        stage.errorCode) && (
                        <Typography
                          color="text.disabled"
                          variant="caption"
                          component="div"
                          sx={{ overflowWrap: 'anywhere' }}
                        >
                          {stage.errorCode && `Error code: ${stage.errorCode}`}
                          {stage.jobId && ` · Job: ${stage.jobId}`}
                          {stage.resultReference &&
                            ` · Result: ${stage.resultReference}`}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Stack>
              </AccordionDetails>
            </Accordion>
          </Stack>
        )
      })}
    </Stack>
  )
}
