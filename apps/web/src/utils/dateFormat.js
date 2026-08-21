const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})
const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export function formatDate(value) {
  return value ? dateFormatter.format(new Date(value)) : '—'
}
export function formatDateTime(value) {
  return value ? dateTimeFormatter.format(new Date(value)) : '—'
}
