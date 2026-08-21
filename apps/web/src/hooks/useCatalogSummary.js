import { useQuery } from '@tanstack/react-query'
import { getCatalogProductSummary } from '../api/catalog'
import { catalogKeys } from '../api/queryKeys'

export function useCatalogSummary(productId) {
  return useQuery({
    queryKey: catalogKeys.summary(productId),
    queryFn: ({ signal }) => getCatalogProductSummary(productId, { signal }),
    enabled: Boolean(productId),
  })
}
