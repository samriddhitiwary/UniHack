import { apiClient } from './client'

export async function searchCatalogProducts(params, { signal } = {}) {
  const response = await apiClient.get('/catalog/products', { params, signal })
  return response.data
}

export async function getCatalogProductSummary(productId, { signal } = {}) {
  const response = await apiClient.get(
    `/products/${productId}/catalog-summary`,
    { signal },
  )
  return response.data
}
