import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { searchCatalogProducts } from '../api/catalog'
import { catalogKeys } from '../api/queryKeys'

export function useCatalogProducts(query) {
  return useQuery({
    queryKey: catalogKeys.products(query),
    queryFn: ({ signal }) => searchCatalogProducts(query, { signal }),
    placeholderData: keepPreviousData,
  })
}
