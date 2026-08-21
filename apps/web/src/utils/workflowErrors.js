const messages = {
  WORKFLOW_ALREADY_ACTIVE: 'A workflow is already active for this product.',
  WORKFLOW_NO_PRODUCT_SOURCES:
    'Add at least one source before starting a workflow.',
  WORKFLOW_REVIEW_NOT_COMPLETED:
    'Complete the human review before resuming this workflow.',
  WORKFLOW_VERSION_CONFLICT:
    'The workflow changed. Refreshing the latest state.',
  WORKFLOW_PRODUCT_CHANGED:
    'This product changed while the workflow was paused. Start a new workflow for the latest state.',
  WORKFLOW_SOURCES_CHANGED:
    'Sources changed after this workflow paused. Start a new workflow to include them.',
  PRODUCT_CLASSIFICATION_UNRESOLVED:
    "CatalogIQ couldn't determine the product category. Add clearer product information and start a new workflow.",
}

export function workflowErrorMessage(error) {
  return (
    messages[error?.code] || error?.message || 'The workflow request failed.'
  )
}
