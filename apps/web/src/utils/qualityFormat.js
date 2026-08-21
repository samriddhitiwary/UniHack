export function formatPercent(basisPoints, maximumFractionDigits = 1) {
  if (basisPoints == null) return 'Not enough labelled data'
  return `${(basisPoints / 100).toLocaleString(undefined, {
    maximumFractionDigits,
  })}%`
}

export function formatCount(value) {
  return Number(value ?? 0).toLocaleString()
}

export function humanizeCode(value = '') {
  return value
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/(^|\s)\S/g, (letter) => letter.toUpperCase())
}

export function comparisonStatusLabel(status) {
  return {
    EXACT_MATCH: 'Exact',
    NORMALIZED_MATCH: 'Normalized',
    MISMATCH: 'Mismatch',
    EXPECTED_POPULATED_ACTUAL_BLANK: 'Missing',
    EXPECTED_BLANK_ACTUAL_POPULATED: 'Unexpected populated',
    BOTH_BLANK: 'Both blank',
    NOT_EVALUATED: 'Not evaluated',
  }[status]
}
