import { Button, Chip, Stack } from '@mui/material'
import {
  categoryOptions,
  optionLabel,
  statusOptions,
} from '../../utils/productLabels'

export function ActiveFilters({ state, onRemove, onClear }) {
  const filters = []
  if (state.q)
    filters.push({
      key: 'q',
      label:
        state.searchMode === 'model'
          ? `Model: ${state.q}`
          : `Name starts with: ${state.q}`,
    })
  if (state.category)
    filters.push({
      key: 'category',
      label: `Category: ${optionLabel(categoryOptions, state.category)}`,
    })
  if (state.status)
    filters.push({
      key: 'status',
      label: `Status: ${optionLabel(statusOptions, state.status)}`,
    })
  if (state.manufacturer)
    filters.push({
      key: 'manufacturer',
      label: `Manufacturer: ${state.manufacturer}`,
    })
  if (!filters.length) return null
  return (
    <Stack direction="row" alignItems="center" flexWrap="wrap" gap={2}>
      {filters.map((filter) => (
        <Chip
          key={filter.key}
          label={filter.label}
          onDelete={() => onRemove(filter.key)}
        />
      ))}
      <Button size="small" variant="text" onClick={onClear}>
        Clear all
      </Button>
    </Stack>
  )
}
