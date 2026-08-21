import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createUnilogEvaluation,
  getLatestUnilogEvaluation,
  getUnilogLabelledComparison,
} from '../api/unilogEvaluation'
import { unilogEvaluationKeys } from '../api/queryKeys'

export function useLatestUnilogEvaluation({ enabled = true } = {}) {
  return useQuery({
    queryKey: unilogEvaluationKeys.latest(),
    queryFn: ({ signal }) => getLatestUnilogEvaluation({ signal }),
    enabled,
    retry: false,
  })
}

export function useCreateUnilogEvaluation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createUnilogEvaluation,
    onSuccess: (data) =>
      queryClient.setQueryData(unilogEvaluationKeys.latest(), data),
  })
}

export function useUnilogLabelledComparison(
  evaluationId,
  inputRowId,
  { enabled = true } = {},
) {
  return useQuery({
    queryKey: unilogEvaluationKeys.row(evaluationId, inputRowId),
    queryFn: ({ signal }) =>
      getUnilogLabelledComparison(evaluationId, inputRowId, { signal }),
    enabled: enabled && Boolean(evaluationId && inputRowId),
    retry: false,
  })
}
