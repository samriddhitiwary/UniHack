export const catalogKeys = {
  all: ['catalog'],
  products: (query) => [...catalogKeys.all, 'products', query],
}

export const productKeys = {
  all: ['products'],
  detail: (productId) => [...productKeys.all, 'detail', productId],
}
