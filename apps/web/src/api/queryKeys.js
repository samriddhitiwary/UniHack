export const catalogKeys = {
  all: ['catalog'],
  products: (query) => [...catalogKeys.all, 'products', query],
  summary: (productId) => [...catalogKeys.all, 'summary', productId],
}

export const productKeys = {
  all: ['products'],
  detail: (productId) => [...productKeys.all, 'detail', productId],
}

export const sourceKeys = {
  all: ['sources'],
  lists: (productId) => [...sourceKeys.all, 'list', productId],
  list: (productId, query) => [...sourceKeys.lists(productId), query],
}

export const workflowKeys = {
  all: ['workflows'],
  lists: (productId) => [...workflowKeys.all, 'list', productId],
  list: (productId, query) => [...workflowKeys.lists(productId), query],
  detail: (productId, workflowId) => [
    ...workflowKeys.all,
    'detail',
    productId,
    workflowId,
  ],
}

export const unilogEvaluationKeys = {
  all: ['unilog-evaluations'],
  latest: () => [...unilogEvaluationKeys.all, 'latest'],
  row: (evaluationId, inputRowId) => [
    ...unilogEvaluationKeys.all,
    evaluationId,
    'rows',
    inputRowId,
  ],
}
