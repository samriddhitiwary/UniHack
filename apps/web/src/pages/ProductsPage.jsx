import AddRoundedIcon from '@mui/icons-material/AddRounded'
import { Box, Button, LinearProgress, Stack } from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AppCard } from '../components/common/AppCard'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'
import { PageHeader } from '../components/common/PageHeader'
import { CursorPagination } from '../components/products/CursorPagination'
import { ProductCard } from '../components/products/ProductCard'
import { ProductCatalogSkeleton } from '../components/products/ProductCatalogSkeleton'
import { ProductCatalogToolbar } from '../components/products/ProductCatalogToolbar'
import { ProductCreationDrawer } from '../components/products/ProductCreationDrawer'
import { ProductTable } from '../components/products/ProductTable'
import { useCatalogProducts } from '../hooks/useCatalogProducts'
import {
  hasCatalogFilters,
  readCatalogState,
  toApiQuery,
} from '../utils/catalogQuery'

function paramsFromState(state) {
  const params = new URLSearchParams()
  if (state.searchMode === 'model') params.set('searchMode', 'model')
  for (const key of ['q', 'category', 'status', 'manufacturer'])
    if (state[key]) params.set(key, state[key])
  return params
}

export function ProductsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const state = readCatalogState(searchParams)
  const [searchText, setSearchText] = useState(state.q)
  const [manufacturerText, setManufacturerText] = useState(state.manufacturer)
  const [cursorHistory, setCursorHistory] = useState([null])
  const [pageIndex, setPageIndex] = useState(0)
  const [creationOpen, setCreationOpen] = useState(
    searchParams.get('create') === '1',
  )
  const filterSignature = `${state.searchMode}|${state.q}|${state.category}|${state.status}|${state.manufacturer}`
  useEffect(() => {
    setCursorHistory([null])
    setPageIndex(0)
  }, [filterSignature])
  useEffect(() => setSearchText(state.q), [state.q])
  useEffect(() => setManufacturerText(state.manufacturer), [state.manufacturer])
  const query = useMemo(
    () => toApiQuery(state, cursorHistory[pageIndex]),
    [state, cursorHistory, pageIndex],
  )
  const catalog = useCatalogProducts(query)
  const update = (next) =>
    setSearchParams(paramsFromState({ ...state, ...next }))
  const openProduct = (product) => navigate(`/products/${product.productId}`)
  const closeCreation = () => {
    setCreationOpen(false)
    if (searchParams.has('create')) {
      const next = new URLSearchParams(searchParams)
      next.delete('create')
      setSearchParams(next, { replace: true })
    }
  }
  const pagination = (
    <CursorPagination
      canPrevious={pageIndex > 0}
      canNext={Boolean(catalog.data?.nextCursor)}
      loading={catalog.isFetching}
      onPrevious={() => setPageIndex((value) => Math.max(0, value - 1))}
      onNext={() => {
        if (!catalog.data?.nextCursor) return
        setCursorHistory((history) => [
          ...history.slice(0, pageIndex + 1),
          catalog.data.nextCursor,
        ])
        setPageIndex((value) => value + 1)
      }}
    />
  )
  const filtered = hasCatalogFilters(state)
  return (
    <>
      <Stack
        spacing={{ xs: 6, md: 8 }}
        minWidth={0}
        sx={{ width: { xs: 'calc(100vw - 32px)', sm: '100%' } }}
      >
        <PageHeader
          title="Products"
          subtitle="Manage industrial product records, catalog quality, and publishing readiness."
          breadcrumbs={[{ label: 'Catalog' }, { label: 'Products' }]}
          actions={
            <Button
              variant="contained"
              startIcon={<AddRoundedIcon />}
              onClick={() => setCreationOpen(true)}
            >
              Add Product
            </Button>
          }
        />
        <AppCard sx={{ overflow: 'hidden', minWidth: 0, maxWidth: '100%' }}>
          <ProductCatalogToolbar
            state={state}
            searchText={searchText}
            onSearchTextChange={setSearchText}
            manufacturerText={manufacturerText}
            onManufacturerTextChange={setManufacturerText}
            onSubmitSearch={() => {
              const q = searchText.trim()
              if (q) update({ q, category: '', status: '', manufacturer: '' })
            }}
            onModeChange={(searchMode) => {
              setSearchText('')
              update({ searchMode, q: '' })
            }}
            onApplyManufacturer={() => {
              const manufacturer = manufacturerText.trim()
              if (manufacturer)
                update({ manufacturer, q: '', category: '', status: '' })
            }}
            onCategoryChange={(category) =>
              update({ category, q: '', manufacturer: '' })
            }
            onStatusChange={(status) =>
              update({ status, q: '', manufacturer: '' })
            }
            onRemoveFilter={(key) => update({ [key]: '' })}
            onClearAll={() => {
              setSearchText('')
              setManufacturerText('')
              setSearchParams(new URLSearchParams())
            }}
          />
          {catalog.isFetching && !catalog.isLoading && (
            <LinearProgress aria-label="Updating product catalog" />
          )}
          {catalog.isLoading ? (
            <ProductCatalogSkeleton />
          ) : catalog.isError ? (
            <ErrorState
              title="We couldn't load the product catalog."
              requestId={catalog.error.requestId}
              onRetry={() => catalog.refetch()}
            />
          ) : catalog.data.items.length === 0 ? (
            <EmptyState
              title={
                filtered
                  ? 'No products match these filters'
                  : 'Build your product intelligence catalog'
              }
              description={
                filtered
                  ? 'Try adjusting your search or clearing one of the active filters.'
                  : 'Add your first industrial product, then attach PDFs, CSV files, images, or text sources to start the intelligence workflow.'
              }
              actionLabel={filtered ? 'Clear filters' : 'Add Product'}
              onAction={
                filtered
                  ? () => {
                      setSearchText('')
                      setManufacturerText('')
                      setSearchParams(new URLSearchParams())
                    }
                  : () => setCreationOpen(true)
              }
            />
          ) : (
            <>
              <Box sx={{ display: { xs: 'none', md: 'block' } }}>
                <ProductTable
                  products={catalog.data.items}
                  onOpen={openProduct}
                  pagination={pagination}
                />
              </Box>
              <Box sx={{ display: { xs: 'block', md: 'none' } }}>
                {catalog.data.items.map((product) => (
                  <ProductCard
                    key={product.productId}
                    product={product}
                    onOpen={() => openProduct(product)}
                  />
                ))}
                {pagination}
              </Box>
            </>
          )}
        </AppCard>
      </Stack>
      <ProductCreationDrawer
        open={creationOpen}
        onClose={closeCreation}
        onCreated={(product) =>
          navigate(`/products/${product.productId}`, {
            state: { created: true },
          })
        }
      />
    </>
  )
}
