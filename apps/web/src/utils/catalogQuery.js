export const CATALOG_LIMIT = 20

export function readCatalogState(searchParams) {
  return {
    searchMode: searchParams.get('searchMode') === 'model' ? 'model' : 'name',
    q: searchParams.get('q') ?? '',
    category: searchParams.get('category') ?? '',
    status: searchParams.get('status') ?? '',
    manufacturer: searchParams.get('manufacturer') ?? '',
  }
}

export function toApiQuery(state, cursor) {
  const query = { limit: CATALOG_LIMIT }
  if (cursor) query.cursor = cursor
  if (state.q)
    query[state.searchMode === 'model' ? 'modelNumber' : 'namePrefix'] = state.q
  else if (state.manufacturer) query.manufacturer = state.manufacturer
  else {
    if (state.category) query.category = state.category
    if (state.status) query.status = state.status
  }
  return query
}

export function hasCatalogFilters(state) {
  return Boolean(
    state.q || state.category || state.status || state.manufacturer,
  )
}
