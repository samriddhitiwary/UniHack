import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Drawer,
  FormControlLabel,
  IconButton,
  Stack,
  Switch,
  Typography,
} from '@mui/material'
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded'
import { useEffect, useState } from 'react'
import { workflowErrorMessage } from '../../utils/workflowErrors'

const workflowDefaults = {
  applyPublishingReadiness: true,
  generateExport: true,
  generateAiEnrichment: true,
  calculateIntelligenceScore: true,
  failOnOptionalStageError: false,
}

const options = [
  [
    'applyPublishingReadiness',
    'Prepare publishing readiness',
    'Evaluate and apply readiness when eligible.',
  ],
  [
    'generateExport',
    'Generate export package',
    'Create JSON and CSV publication artifacts.',
  ],
  [
    'generateAiEnrichment',
    'Generate AI commerce content',
    'Create grounded commerce-ready content.',
  ],
  [
    'calculateIntelligenceScore',
    'Calculate intelligence score',
    'Evaluate catalog completeness and quality.',
  ],
]

export function WorkflowLaunchDrawer({
  open,
  onClose,
  sourceCount,
  mutation,
  onStart,
}) {
  const [configuration, setConfiguration] = useState(workflowDefaults)
  useEffect(() => {
    if (!open) setConfiguration(workflowDefaults)
  }, [open])
  const toggle = (key) =>
    setConfiguration((value) => ({ ...value, [key]: !value[key] }))
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={mutation.isPending ? undefined : onClose}
      PaperProps={{
        role: 'dialog',
        'aria-labelledby': 'workflow-launch-title',
        sx: { width: { xs: '100%', sm: 580 }, maxWidth: '100%' },
      }}
    >
      <Stack minHeight="100%">
        <Stack direction="row" justifyContent="space-between" sx={{ p: 5 }}>
          <Stack spacing={1}>
            <Typography id="workflow-launch-title" variant="h2">
              Start Intelligence Workflow
            </Typography>
            <Typography color="text.secondary">
              Configure the catalog outputs for this processing run.
            </Typography>
          </Stack>
          <IconButton
            aria-label="Close workflow configuration"
            onClick={onClose}
          >
            <CloseRoundedIcon />
          </IconButton>
        </Stack>
        <Divider />
        <Stack spacing={4} sx={{ p: 5, flex: 1 }}>
          {mutation.isError && (
            <Alert severity="error">
              {workflowErrorMessage(mutation.error)}
              {mutation.error.requestId &&
                ` · Request ID: ${mutation.error.requestId}`}
            </Alert>
          )}
          <Box sx={{ p: 3, bgcolor: 'grey.50', borderRadius: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Sources
            </Typography>
            <Typography fontWeight={700}>{sourceCount} available</Typography>
            <Typography variant="caption" color="text.secondary">
              Expected checkpoint: Human review
            </Typography>
          </Box>
          <Stack spacing={2}>
            {options.map(([key, label, description]) => (
              <FormControlLabel
                key={key}
                control={
                  <Switch
                    checked={configuration[key]}
                    onChange={() => toggle(key)}
                  />
                }
                label={
                  <Stack>
                    <Typography fontWeight={700}>{label}</Typography>
                    <Typography color="text.secondary" variant="caption">
                      {description}
                    </Typography>
                  </Stack>
                }
                sx={{ alignItems: 'flex-start', mx: 0, gap: 2 }}
              />
            ))}
          </Stack>
          <Accordion disableGutters elevation={0}>
            <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />}>
              <Typography fontWeight={700}>Advanced settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <FormControlLabel
                control={
                  <Switch
                    checked={configuration.failOnOptionalStageError}
                    onChange={() => toggle('failOnOptionalStageError')}
                  />
                }
                label="Stop workflow if an optional output fails"
              />
            </AccordionDetails>
          </Accordion>
        </Stack>
        <Divider />
        <Stack direction="row" justifyContent="flex-end" gap={2} sx={{ p: 4 }}>
          <Button onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={mutation.isPending || sourceCount === 0}
            onClick={() => onStart(configuration)}
          >
            {mutation.isPending && (
              <CircularProgress size={16} sx={{ mr: 1 }} />
            )}
            {mutation.isPending ? 'Starting…' : 'Start Workflow'}
          </Button>
        </Stack>
      </Stack>
    </Drawer>
  )
}
