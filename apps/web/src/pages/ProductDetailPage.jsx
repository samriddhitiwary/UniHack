import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded'
import { Alert, CardContent, Skeleton, Stack, Typography } from '@mui/material'
import { useLocation, useParams } from 'react-router-dom'
import { AppCard } from '../components/common/AppCard'
import { ErrorState } from '../components/common/ErrorState'
import { PageHeader } from '../components/common/PageHeader'
import { StatusBadge } from '../components/common/StatusBadge'
import { useProduct } from '../hooks/useProduct'
import {
  identityMetadata,
  optionLabel,
  categoryOptions,
} from '../utils/productLabels'

export function ProductDetailPage() {
  const { productId } = useParams()
  const location = useLocation()
  const product = useProduct(productId)
  if (product.isLoading)
    return (
      <Stack spacing={5} aria-label="Loading product">
        <Skeleton width={300} height={48} />
        <Skeleton height={180} />
      </Stack>
    )
  if (product.isError)
    return (
      <AppCard>
        <ErrorState
          title="We couldn't load this product."
          requestId={product.error.requestId}
          onRetry={() => product.refetch()}
        />
      </AppCard>
    )
  return (
    <Stack spacing={{ xs: 6, md: 8 }}>
      <PageHeader
        title={product.data.name}
        subtitle={identityMetadata(product.data)}
        breadcrumbs={[
          { label: 'Products', href: '/products' },
          { label: product.data.name },
        ]}
        status={<StatusBadge status={product.data.status} />}
      />
      {location.state?.created && (
        <Alert severity="success" icon={<CheckCircleOutlineRoundedIcon />}>
          Product created. Upload sources and start the intelligence workflow in
          the next step.
        </Alert>
      )}
      <AppCard>
        <CardContent
          sx={{ p: { xs: 5, md: 7 }, '&:last-child': { pb: { xs: 5, md: 7 } } }}
        >
          <Stack spacing={4}>
            <Stack direction={{ xs: 'column', sm: 'row' }} gap={6}>
              <Stack>
                <Typography color="text.secondary" variant="caption">
                  Category
                </Typography>
                <Typography fontWeight={700}>
                  {optionLabel(categoryOptions, product.data.category)}
                </Typography>
              </Stack>
              <Stack>
                <Typography color="text.secondary" variant="caption">
                  Product workspace
                </Typography>
                <Typography>
                  Sources, workflow tracking, review, and intelligence details
                  will appear here.
                </Typography>
              </Stack>
            </Stack>
            {product.data.description && (
              <Stack>
                <Typography color="text.secondary" variant="caption">
                  Description
                </Typography>
                <Typography>{product.data.description}</Typography>
              </Stack>
            )}
          </Stack>
        </CardContent>
      </AppCard>
    </Stack>
  )
}
