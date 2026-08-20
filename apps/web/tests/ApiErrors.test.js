import { describe, expect, it } from 'vitest'
import { normalizeApiError } from '../src/api/errors'
describe('API error normalization', () => {
  it('retains only the safe error contract and request ID', () => {
    const result = normalizeApiError({
      response: {
        status: 409,
        headers: { 'x-request-id': 'req-409' },
        data: {
          error: {
            code: 'VERSION_CONFLICT',
            message: 'The product changed.',
            details: { version: 2 },
          },
        },
      },
    })
    expect(result).toMatchObject({
      status: 409,
      code: 'VERSION_CONFLICT',
      message: 'The product changed.',
      requestId: 'req-409',
      details: { version: 2 },
    })
  })
  it('uses a calm fallback for transport errors', () => {
    expect(normalizeApiError(new Error('socket secret'))).toMatchObject({
      status: 0,
      code: 'UNEXPECTED_ERROR',
      message: 'We could not complete that request.',
      requestId: null,
    })
  })
})
