import { apiClient } from './client'

export async function listProductSources(productId, params, { signal } = {}) {
  const response = await apiClient.get(`/products/${productId}/sources`, {
    params,
    signal,
  })
  return response.data
}

export async function uploadProductSource({ productId, file, displayName }) {
  const body = new FormData()
  body.append('file', file)
  if (displayName?.trim()) body.append('displayName', displayName.trim())
  const response = await apiClient.post(
    `/products/${productId}/sources/upload`,
    body,
  )
  return response.data
}

export async function createTextSource({
  productId,
  displayName,
  textContent,
}) {
  const response = await apiClient.post(`/products/${productId}/sources/text`, {
    displayName: displayName?.trim() || null,
    textContent: textContent.trim(),
  })
  return response.data
}

export async function deleteProductSource({ productId, sourceId, version }) {
  await apiClient.delete(`/products/${productId}/sources/${sourceId}`, {
    params: { version },
  })
}
