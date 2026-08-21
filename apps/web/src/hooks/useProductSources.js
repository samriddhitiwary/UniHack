import { useInfiniteQuery } from '@tanstack/react-query'
import { listProductSources } from '../api/sources'
import { sourceKeys } from '../api/queryKeys'

export function useProductSources(productId) {
  return useInfiniteQuery({
    queryKey: sourceKeys.list(productId, { limit: 20 }),
    queryFn: ({ pageParam, signal }) =>
      listProductSources(
        productId,
        { limit: 20, ...(pageParam ? { cursor: pageParam } : {}) },
        { signal },
      ),
    initialPageParam: null,
    getNextPageParam: (page) => page.nextCursor ?? undefined,
    enabled: Boolean(productId),
  })
}
