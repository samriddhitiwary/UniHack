import { beforeEach, describe, expect, it, vi } from 'vitest'

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))

vi.mock('../src/api/client', () => ({
  apiClient: { get, post },
}))

import {
  createUnilogEvaluation,
  getLatestUnilogEvaluation,
  getUnilogLabelledComparison,
} from '../src/api/unilogEvaluation'

describe('Unilog evaluation API client', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
  })

  it('uses paths relative to the shared /api/v1 base URL', async () => {
    const signal = new AbortController().signal
    get.mockResolvedValueOnce({ data: { evaluationId: 'latest' } })
    post.mockResolvedValueOnce({ data: { evaluationId: 'created' } })
    get.mockResolvedValueOnce({ data: { inputRowId: 'row-1' } })

    await expect(getLatestUnilogEvaluation({ signal })).resolves.toEqual({
      evaluationId: 'latest',
    })
    await expect(createUnilogEvaluation()).resolves.toEqual({
      evaluationId: 'created',
    })
    await expect(
      getUnilogLabelledComparison('eval-1', 'row-1', { signal }),
    ).resolves.toEqual({ inputRowId: 'row-1' })

    expect(get).toHaveBeenNthCalledWith(1, '/unilog/evaluations/latest', {
      signal,
    })
    expect(post).toHaveBeenCalledWith('/unilog/evaluations')
    expect(get).toHaveBeenNthCalledWith(
      2,
      '/unilog/evaluations/eval-1/rows/row-1',
      { signal },
    )
  })
})
