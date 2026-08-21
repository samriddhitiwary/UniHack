import AddRoundedIcon from '@mui/icons-material/AddRounded'
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined'
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import RateReviewOutlinedIcon from '@mui/icons-material/RateReviewOutlined'
import WorkspacePremiumOutlinedIcon from '@mui/icons-material/WorkspacePremiumOutlined'
import { Button, Stack } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { AppCard } from '../components/common/AppCard'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'
import { MetricCard } from '../components/common/MetricCard'
import { PageHeader } from '../components/common/PageHeader'
import { PageSkeleton } from '../components/common/LoadingSkeletons'
import { AttentionRequiredCard } from '../components/dashboard/AttentionRequiredCard'
import { CatalogQualityCard } from '../components/dashboard/CatalogQualityCard'
import { RecentProductsCard } from '../components/dashboard/RecentProductsCard'
import { WorkflowHealthCard } from '../components/dashboard/WorkflowHealthCard'
import { dashboardFixture } from '../mocks/dashboard'
const metricIcons = {
  inventory: <Inventory2OutlinedIcon fontSize="small" />,
  ready: <FactCheckOutlinedIcon fontSize="small" />,
  review: <RateReviewOutlinedIcon fontSize="small" />,
  score: <WorkspacePremiumOutlinedIcon fontSize="small" />,
}
export function OverviewPage({
  state = 'ready',
  data = dashboardFixture,
  requestId,
  onRetry,
}) {
  const navigate = useNavigate()
  const addProduct = () => navigate('/products?create=1')
  if (state === 'loading') return <PageSkeleton />
  return (
    <Stack spacing={{ xs: 6, md: 8 }}>
      <PageHeader
        title="Overview"
        subtitle="Monitor product catalog quality, workflow health, and publishing readiness."
        actions={
          <Button
            variant="contained"
            startIcon={<AddRoundedIcon />}
            onClick={addProduct}
          >
            Add Product
          </Button>
        }
      />
      {state === 'error' ? (
        <AppCard>
          <ErrorState requestId={requestId} onRetry={onRetry} />
        </AppCard>
      ) : state === 'empty' ? (
        <AppCard>
          <EmptyState
            title="Start building your product intelligence catalog"
            description="Add your first product and upload a datasheet, image, CSV, or text source."
            actionLabel="Add Product"
            onAction={addProduct}
          />
        </AppCard>
      ) : (
        <>
          <Stack
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, minmax(0, 1fr))',
                lg: 'repeat(4, minmax(0, 1fr))',
              },
              gap: 4,
            }}
          >
            {data.metrics.map((metric) => (
              <MetricCard
                key={metric.id}
                {...metric}
                icon={metricIcons[metric.icon]}
              />
            ))}
          </Stack>
          <Stack
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'minmax(0, 1fr)',
                lg: 'minmax(0, 1.6fr) minmax(280px, 1fr)',
              },
              gap: 4,
            }}
          >
            <CatalogQualityCard items={data.quality} />
            <WorkflowHealthCard items={data.workflows} />
          </Stack>
          <Stack
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'minmax(0, 1fr)',
                lg: 'minmax(0, 1.6fr) minmax(280px, 1fr)',
              },
              gap: 4,
            }}
          >
            <RecentProductsCard products={data.recentProducts} />
            <AttentionRequiredCard items={data.attention} />
          </Stack>
        </>
      )}
    </Stack>
  )
}
