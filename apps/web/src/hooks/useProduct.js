import { useQuery } from '@tanstack/react-query'
import { getProduct } from '../api/products'
import { productKeys } from '../api/queryKeys'

export function useProduct(productId) {
  return useQuery({
    queryKey: productKeys.detail(productId),
    queryFn: ({ signal }) => getProduct(productId, { signal }),
    enabled: Boolean(productId),
  })
}
