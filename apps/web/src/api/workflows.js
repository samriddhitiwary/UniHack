import { apiClient } from './client'

export async function listCatalogWorkflows(productId, params, { signal } = {}) {
  const response = await apiClient.get(`/products/${productId}/workflows`, {
    params,
    signal,
  })
  return response.data
}

export async function getCatalogWorkflow(
  productId,
  workflowId,
  { signal } = {},
) {
  const response = await apiClient.get(
    `/products/${productId}/workflows/${workflowId}`,
    { signal },
  )
  return response.data
}

export async function startCatalogWorkflow({ productId, configuration }) {
  const response = await apiClient.post(
    `/products/${productId}/workflows`,
    configuration,
  )
  return response.data
}

export async function resumeCatalogWorkflow({
  productId,
  workflowId,
  version,
}) {
  const response = await apiClient.post(
    `/products/${productId}/workflows/${workflowId}/resume`,
    { version },
  )
  return response.data
}
