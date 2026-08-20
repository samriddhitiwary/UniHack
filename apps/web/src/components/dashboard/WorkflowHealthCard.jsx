import { CardContent, Divider, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { StatusBadge } from '../common/StatusBadge'
export function WorkflowHealthCard({ items }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: 5, '&:last-child': { pb: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Workflow Health"
            subtitle="Current state of catalog intelligence processing."
          />
          <Stack divider={<Divider flexItem />}>
            {items.map((item) => (
              <Stack
                key={item.status}
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                sx={{ py: 2 }}
              >
                <StatusBadge status={item.status} />
                <Typography fontWeight={750}>
                  {String(item.count).padStart(2, '0')}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
