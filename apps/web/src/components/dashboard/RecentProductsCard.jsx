import { CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { DataTableShell } from '../common/DataTableShell'
import { IntelligenceScore } from '../common/IntelligenceScore'
import { SectionHeader } from '../common/SectionHeader'
import { StatusBadge } from '../common/StatusBadge'
const columns = [
  {
    key: 'name',
    label: 'Product',
    render: (row) => (
      <Stack spacing={0}>
        <Typography fontWeight={700} noWrap>
          {row.name}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {row.sku}
        </Typography>
      </Stack>
    ),
  },
  { key: 'category', label: 'Category' },
  {
    key: 'status',
    label: 'Status',
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'intelligence',
    label: 'Intelligence',
    render: (row) => <IntelligenceScore compact score={row.intelligence} />,
  },
  { key: 'updated', label: 'Updated' },
]
export function RecentProductsCard({ products }) {
  return (
    <AppCard sx={{ overflow: 'hidden' }}>
      <CardContent sx={{ p: 5, pb: 4 }}>
        <SectionHeader
          title="Recent Products"
          subtitle="Recently updated products and their readiness."
        />
      </CardContent>
      <DataTableShell columns={columns} rows={products} />
    </AppCard>
  )
}
