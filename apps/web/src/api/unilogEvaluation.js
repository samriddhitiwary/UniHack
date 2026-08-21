import { apiClient } from './client'

export async function getLatestUnilogEvaluation({ signal } = {}) {
  const response = await apiClient.get('/unilog/evaluations/latest', {
    signal,
  })
  return response.data
}

export async function createUnilogEvaluation() {
  const response = await apiClient.post('/unilog/evaluations')
  return response.data
}

export async function getUnilogLabelledComparison(
  evaluationId,
  inputRowId,
  { signal } = {},
) {
  const response = await apiClient.get(
    `/unilog/evaluations/${evaluationId}/rows/${inputRowId}`,
    { signal },
  )
  return response.data
}
