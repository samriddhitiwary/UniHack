import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProduct } from '../api/products'
import { catalogKeys, productKeys } from '../api/queryKeys'

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createProduct,
    throwOnError: false,
    onSuccess: (product) => {
      queryClient.setQueryData(productKeys.detail(product.productId), product)
      return queryClient.invalidateQueries({ queryKey: catalogKeys.all })
    },
  })
}
