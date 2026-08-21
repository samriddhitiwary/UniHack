import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { getCatalogWorkflow, listCatalogWorkflows } from '../api/workflows'
import { workflowKeys } from '../api/queryKeys'
import { workflowPollingInterval } from '../utils/workflowLabels'

export function useProductWorkflows(productId) {
  return useInfiniteQuery({
    queryKey: workflowKeys.list(productId, { limit: 10 }),
    queryFn: ({ pageParam, signal }) =>
      listCatalogWorkflows(
        productId,
        { limit: 10, ...(pageParam ? { cursor: pageParam } : {}) },
        { signal },
      ),
    initialPageParam: null,
    getNextPageParam: (page) => page.nextCursor ?? undefined,
    enabled: Boolean(productId),
  })
}

export function useWorkflow(productId, workflowId) {
  return useQuery({
    queryKey: workflowKeys.detail(productId, workflowId),
    queryFn: ({ signal }) =>
      getCatalogWorkflow(productId, workflowId, { signal }),
    enabled: Boolean(productId && workflowId),
    refetchInterval: (query) =>
      workflowPollingInterval(query.state.data?.status),
  })
}
