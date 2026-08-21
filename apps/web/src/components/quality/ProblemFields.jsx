import { Box, CardContent, Chip, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { humanizeCode } from '../../utils/qualityFormat'

export function ProblemFields({ problems, blankFields }) {
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={5}>
          <SectionHeader
            title="Top problem fields"
            subtitle="Priority = labelled issue frequency × importance × fixability."
          />
          <Stack spacing={1}>
            {problems.slice(0, 8).map((item) => (
              <Box
                key={`${item.fieldName}-${item.issueType}`}
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr auto', sm: '1.4fr 1fr auto' },
                  gap: 2,
                  alignItems: 'center',
                  py: 2.25,
                  borderBottom: 1,
                  borderColor: 'divider',
                }}
              >
                <Typography fontWeight={680} sx={{ overflowWrap: 'anywhere' }}>
                  {item.fieldName}
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {humanizeCode(item.issueType)} · {item.affectedLabelledRows}{' '}
                  rows
                </Typography>
                <Chip
                  size="small"
                  label={`Priority ${item.priorityScore}`}
                  color={item.supported ? 'warning' : 'default'}
                />
              </Box>
            ))}
          </Stack>
          <Stack spacing={2}>
            <Typography variant="overline" color="text.secondary">
              Frequently blank supported fields
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={2}>
              {blankFields.slice(0, 6).map((item) => (
                <Chip
                  key={item.fieldName}
                  variant="outlined"
                  label={`${item.fieldName} · ${(item.blankRateBp / 100).toFixed(0)}% blank`}
                />
              ))}
            </Stack>
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
