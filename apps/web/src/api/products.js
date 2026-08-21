import { apiClient } from './client'

export async function createProduct(payload) {
  const response = await apiClient.post('/products', payload)
  return response.data
}

export async function getProduct(productId, { signal } = {}) {
  const response = await apiClient.get(`/products/${productId}`, { signal })
  return response.data
}
