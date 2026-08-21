import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded'
import { Alert, Button, CardContent, Skeleton, Stack } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { AppCard } from '../components/common/AppCard'
import { ErrorState } from '../components/common/ErrorState'
import { ProductOverview } from '../components/product-workspace/ProductOverview'
import { ProductWorkspaceHeader } from '../components/product-workspace/ProductWorkspaceHeader'
import { ProductWorkspaceTabs } from '../components/product-workspace/ProductWorkspaceTabs'
import { SourcesSection } from '../components/sources/SourcesSection'
import { WorkflowLaunchDrawer } from '../components/workflows/WorkflowLaunchDrawer'
import { WorkflowSection } from '../components/workflows/WorkflowSection'
import { useCatalogSummary } from '../hooks/useCatalogSummary'
import { useProduct } from '../hooks/useProduct'
import { useProductSources } from '../hooks/useProductSources'
import { useProductWorkflows, useWorkflow } from '../hooks/useProductWorkflows'
import {
  useResumeWorkflow,
  useStartWorkflow,
} from '../hooks/useWorkflowMutations'
import { isActiveWorkflow } from '../utils/workflowLabels'

function WorkspaceSkeleton() {
  return (
    <Stack spacing={6} aria-label="Loading Product workspace">
      <Stack spacing={2}>
        <Skeleton width="46%" height={48} />
        <Skeleton width="28%" />
      </Stack>
      <Skeleton height={112} />
      <Skeleton height={48} />
      <Skeleton height={320} />
    </Stack>
  )
}

export function ProductDetailPage() {
  const { productId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [tab, setTab] = useState('overview')
  const [launchOpen, setLaunchOpen] = useState(false)
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(null)
  const product = useProduct(productId)
  const summary = useCatalogSummary(productId)
  const sources = useProductSources(productId)
  const history = useProductWorkflows(productId)
  const historyItems = useMemo(
    () => history.data?.pages.flatMap((page) => page.items) ?? [],
    [history.data],
  )
  const latestId = historyItems[0]?.workflowId ?? null
  useEffect(() => {
    if (!selectedWorkflowId && latestId) setSelectedWorkflowId(latestId)
  }, [latestId, selectedWorkflowId])
  const workflow = useWorkflow(productId, selectedWorkflowId || latestId)
  const start = useStartWorkflow(productId)
  const resume = useResumeWorkflow(productId)
  const sourceItems = sources.data?.pages.flatMap((page) => page.items) ?? []
  const activeWorkflow = isActiveWorkflow(workflow.data?.status)

  if (product.isLoading) return <WorkspaceSkeleton />
  if (product.isError)
    return (
      <AppCard>
        <CardContent>
          <ErrorState
            title={
              product.error.status === 404
                ? 'Product not found'
                : "We couldn't load this product."
            }
            description={
              product.error.status === 404
                ? 'This product may have been removed or the link is no longer valid.'
                : undefined
            }
            requestId={product.error.requestId}
            onRetry={
              product.error.status === 404 ? undefined : () => product.refetch()
            }
          />
          {product.error.status === 404 && (
            <Stack alignItems="center" sx={{ mt: -6, pb: 5 }}>
              <Button onClick={() => navigate('/products')}>
                Back to Products
              </Button>
            </Stack>
          )}
        </CardContent>
      </AppCard>
    )

  const primaryAction = () => {
    if (activeWorkflow) {
      setTab('workflow')
      return
    }
    if (sources.isSuccess && sourceItems.length === 0) {
      setTab('sources')
      return
    }
    setTab('workflow')
    setLaunchOpen(true)
  }

  return (
    <Stack spacing={{ xs: 5, md: 7 }} minWidth={0}>
      <ProductWorkspaceHeader
        product={product.data}
        summary={summary.data}
        sourceCount={sourceItems.length}
        sourceCountPartial={Boolean(sources.hasNextPage)}
        workflow={workflow.data}
        onPrimaryAction={primaryAction}
      />
      {location.state?.created && (
        <Alert severity="success" icon={<CheckCircleOutlineRoundedIcon />}>
          Product created. Add trusted sources, then start the intelligence
          workflow.
        </Alert>
      )}
      {summary.isError && (
        <Alert
          severity="warning"
          action={<Button onClick={() => summary.refetch()}>Retry</Button>}
        >
          Catalog summary is temporarily unavailable.
          {summary.error.requestId && ` Request ID: ${summary.error.requestId}`}
        </Alert>
      )}
      <ProductWorkspaceTabs value={tab} onChange={setTab} />
      <section role="tabpanel" aria-label={`${tab} workspace`}>
        {tab === 'overview' && (
          <ProductOverview
            product={product.data}
            summary={summary.data}
            sources={sourceItems}
            workflow={workflow.data}
          />
        )}
        {tab === 'sources' && (
          <SourcesSection
            productId={productId}
            query={sources}
            activeWorkflow={activeWorkflow}
          />
        )}
        {tab === 'workflow' && (
          <WorkflowSection
            sourceCount={sourceItems.length}
            summary={summary.data}
            historyQuery={history}
            workflowQuery={workflow}
            selectedId={selectedWorkflowId || latestId}
            onSelect={setSelectedWorkflowId}
            onLaunch={() => setLaunchOpen(true)}
            onReview={() =>
              navigate(
                `/products/${productId}/review/${workflow.data.reviewId}`,
              )
            }
            onResume={() =>
              resume.mutate(
                {
                  productId,
                  workflowId: workflow.data.workflowId,
                  version: workflow.data.version,
                },
                {
                  onSuccess: (value) => setSelectedWorkflowId(value.workflowId),
                  onError: (error) => {
                    if (error.code === 'WORKFLOW_VERSION_CONFLICT')
                      workflow.refetch()
                  },
                },
              )
            }
            resumeMutation={resume}
          />
        )}
      </section>
      <WorkflowLaunchDrawer
        open={launchOpen}
        onClose={() => {
          if (!start.isPending) {
            start.reset()
            setLaunchOpen(false)
          }
        }}
        sourceCount={sourceItems.length}
        mutation={start}
        onStart={(configuration) =>
          start.mutate(
            { productId, configuration },
            {
              onSuccess: (value) => {
                setSelectedWorkflowId(value.workflowId)
                setLaunchOpen(false)
                setTab('workflow')
              },
              onError: (error) => {
                if (error.code === 'WORKFLOW_ALREADY_ACTIVE') history.refetch()
              },
            },
          )
        }
      />
    </Stack>
  )
}
