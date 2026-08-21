import { useMutation, useQueryClient } from '@tanstack/react-query'
import { catalogKeys, productKeys, workflowKeys } from '../api/queryKeys'
import { resumeCatalogWorkflow, startCatalogWorkflow } from '../api/workflows'

function useWorkflowMutation(productId, mutationFn) {
  const client = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: (workflow) => {
      client.setQueryData(
        workflowKeys.detail(productId, workflow.workflowId),
        workflow,
      )
      return Promise.all([
        client.invalidateQueries({ queryKey: workflowKeys.lists(productId) }),
        client.invalidateQueries({ queryKey: productKeys.detail(productId) }),
        client.invalidateQueries({ queryKey: catalogKeys.summary(productId) }),
      ])
    },
  })
}

export function useStartWorkflow(productId) {
  return useWorkflowMutation(productId, startCatalogWorkflow)
}

export function useResumeWorkflow(productId) {
  return useWorkflowMutation(productId, resumeCatalogWorkflow)
}
