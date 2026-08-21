import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createTextSource,
  deleteProductSource,
  uploadProductSource,
} from '../api/sources'
import { sourceKeys } from '../api/queryKeys'

function useSourceMutation(productId, mutationFn) {
  const client = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: () =>
      client.invalidateQueries({ queryKey: sourceKeys.lists(productId) }),
  })
}

export function useUploadProductSource(productId) {
  return useSourceMutation(productId, uploadProductSource)
}

export function useCreateTextSource(productId) {
  return useSourceMutation(productId, createTextSource)
}

export function useDeleteProductSource(productId) {
  return useSourceMutation(productId, deleteProductSource)
}
