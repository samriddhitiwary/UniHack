export const sourceTypes = {
  PDF: 'PDF Datasheet',
  IMAGE: 'Product Image / Nameplate',
  CSV: 'CSV Data',
  TEXT: 'Text Source',
}

export const sourceStatusLabels = {
  PENDING: 'Pending',
  READY: 'Ready',
  PROCESSING: 'Processing',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
}

const MiB = 1024 * 1024
const fileRules = {
  pdf: { types: ['application/pdf'], maximum: 10 * MiB },
  png: { types: ['image/png'], maximum: 10 * MiB },
  jpg: { types: ['image/jpeg'], maximum: 10 * MiB },
  jpeg: { types: ['image/jpeg'], maximum: 10 * MiB },
  webp: { types: ['image/webp'], maximum: 10 * MiB },
  csv: {
    types: ['text/csv', 'application/csv', 'application/vnd.ms-excel'],
    maximum: 5 * MiB,
  },
}

export function validateSourceFile(file) {
  const extension = file.name.split('.').pop()?.toLowerCase()
  const rule = fileRules[extension]
  if (!rule || !rule.types.includes(file.type))
    return 'Choose a PDF, CSV, PNG, JPEG, or WEBP file.'
  if (file.size > rule.maximum)
    return extension === 'csv'
      ? 'CSV files must be 5 MiB or smaller.'
      : 'PDF and image files must be 10 MiB or smaller.'
  return null
}

export function sourceName(source) {
  return source.displayName || source.originalFilename || 'Untitled source'
}
