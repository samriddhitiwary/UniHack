export const categoryOptions = [
  { value: '', label: 'All categories' },
  { value: 'CENTRIFUGAL_PUMP', label: 'Centrifugal Pump' },
  { value: 'INDUCTION_MOTOR', label: 'Induction Motor' },
  { value: 'UNCLASSIFIED', label: 'Unclassified' },
]

export const statusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'REVIEW_REQUIRED', label: 'Review Required' },
  { value: 'READY_TO_PUBLISH', label: 'Ready to Publish' },
  { value: 'FAILED', label: 'Failed' },
]

export function optionLabel(options, value) {
  return options.find((option) => option.value === value)?.label ?? value
}

export function identityMetadata(product) {
  return (
    [product.manufacturer, product.modelNumber].filter(Boolean).join(' · ') ||
    '—'
  )
}
