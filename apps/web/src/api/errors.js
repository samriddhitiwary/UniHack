export class ApiError extends Error {
  constructor({
    status = 0,
    code = 'UNEXPECTED_ERROR',
    message = 'Something went wrong.',
    requestId = null,
    details = null,
  }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }
}

export function normalizeApiError(error) {
  if (error instanceof ApiError) return error
  const response = error?.response
  const payload = response?.data?.error ?? response?.data ?? {}
  return new ApiError({
    status: response?.status ?? 0,
    code: typeof payload.code === 'string' ? payload.code : 'UNEXPECTED_ERROR',
    message:
      typeof payload.message === 'string'
        ? payload.message
        : 'We could not complete that request.',
    requestId: response?.headers?.['x-request-id'] ?? payload.requestId ?? null,
    details: payload.details ?? null,
  })
}
