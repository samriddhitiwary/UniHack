import ConstructionRoundedIcon from '@mui/icons-material/ConstructionRounded'
import { Stack } from '@mui/material'
import { AppCard } from '../components/common/AppCard'
import { EmptyState } from '../components/common/EmptyState'
import { PageHeader } from '../components/common/PageHeader'
export function ComingSoonPage({ title }) {
  return (
    <Stack spacing={8}>
      <PageHeader
        title={title}
        subtitle={`${title} is planned for a dedicated CatalogIQ specification.`}
        breadcrumbs={[
          { label: 'Overview', href: '/dashboard' },
          { label: title },
        ]}
      />
      <AppCard>
        <EmptyState
          icon={<ConstructionRoundedIcon />}
          title={`${title} is coming soon`}
          description="This route is ready for future work, with no placeholder functionality or fabricated data."
        />
      </AppCard>
    </Stack>
  )
}
