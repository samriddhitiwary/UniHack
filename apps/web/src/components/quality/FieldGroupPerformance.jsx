import { Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { formatPercent, humanizeCode } from '../../utils/qualityFormat'

const shownGroups = [
  'IDENTITY',
  'CLASSIFICATION',
  'DESCRIPTION',
  'ATTRIBUTE',
  'COMMERCIAL',
  'ASSET',
]

export function FieldGroupPerformance({ groups }) {
  const items = shownGroups.map((group) =>
    groups.find((item) => item.group === group),
  )
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Field-group performance"
            subtitle="Accuracy is shown only where official populated labels exist."
          />
          <Box role="table" aria-label="Field group performance">
            <Box
              role="row"
              sx={{
                display: { xs: 'none', sm: 'grid' },
                gridTemplateColumns: '1.2fr repeat(3, .8fr)',
                gap: 2,
                pb: 2,
                borderBottom: 1,
                borderColor: 'divider',
              }}
            >
              {[
                'Group',
                'Exact / evaluable',
                'Exact rate',
                'Label coverage',
              ].map((label) => (
                <Typography
                  key={label}
                  role="columnheader"
                  variant="caption"
                  color="text.secondary"
                >
                  {label}
                </Typography>
              ))}
            </Box>
            {items.map((item) => (
              <Box
                key={item.group}
                role="row"
                sx={{
                  display: 'grid',
                  gridTemplateColumns: {
                    xs: '1fr 1fr',
                    sm: '1.2fr repeat(3, .8fr)',
                  },
                  gap: 2,
                  py: 3,
                  borderBottom: 1,
                  borderColor: 'divider',
                  '&:last-child': { borderBottom: 0 },
                }}
              >
                <Typography role="cell" fontWeight={700}>
                  {humanizeCode(item.group)}
                </Typography>
                <Typography role="cell">
                  {item.accuracy.evaluableFieldCount
                    ? `${item.accuracy.exactMatchCount} / ${item.accuracy.evaluableFieldCount}`
                    : 'Not enough labelled data'}
                </Typography>
                <Typography role="cell" color="text.secondary">
                  {item.accuracy.evaluableFieldCount
                    ? formatPercent(item.accuracy.exactMatchRateBp)
                    : '—'}
                </Typography>
                <Typography role="cell" color="text.secondary">
                  {item.labelledPopulatedCount
                    ? formatPercent(item.coverageRateBp)
                    : '—'}
                </Typography>
              </Box>
            ))}
          </Box>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
