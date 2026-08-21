import RateReviewOutlinedIcon from '@mui/icons-material/RateReviewOutlined'
import { Button, CardContent, Stack, Typography } from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { AppCard } from '../components/common/AppCard'
import { PageHeader } from '../components/common/PageHeader'
import { useProduct } from '../hooks/useProduct'

export function ProductReviewPage() {
  const { productId, reviewId } = useParams()
  const navigate = useNavigate()
  const product = useProduct(productId)
  return (
    <Stack spacing={6}>
      <PageHeader
        title="Human Review"
        subtitle={product.data?.name || 'Product catalog review'}
        breadcrumbs={[
          { label: 'Products', href: '/products' },
          {
            label: product.data?.name || 'Product',
            href: `/products/${productId}`,
          },
          { label: 'Review' },
        ]}
      />
      <AppCard>
        <CardContent sx={{ p: { xs: 6, md: 10 } }}>
          <Stack
            alignItems="center"
            textAlign="center"
            spacing={3}
            maxWidth={600}
            mx="auto"
          >
            <RateReviewOutlinedIcon color="primary" sx={{ fontSize: 44 }} />
            <Typography variant="h2">Review workspace prepared</Typography>
            <Typography color="text.secondary">
              Review decisions will be implemented in SPEC-041. No attributes
              are approved, rejected, or overridden from this placeholder.
            </Typography>
            <Typography
              color="text.disabled"
              variant="caption"
              sx={{ overflowWrap: 'anywhere' }}
            >
              Review reference: {reviewId}
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate(`/products/${productId}`)}
            >
              Back to Product Workspace
            </Button>
          </Stack>
        </CardContent>
      </AppCard>
    </Stack>
  )
}
