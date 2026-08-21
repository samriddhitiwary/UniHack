import { Button, MenuItem, Stack, TextField, Tooltip } from '@mui/material'
import { categoryOptions, statusOptions } from '../../utils/productLabels'

export function ProductFilters({
  state,
  manufacturerText,
  onManufacturerTextChange,
  onApplyManufacturer,
  onCategoryChange,
  onStatusChange,
}) {
  const indexedSearchActive = Boolean(state.q)
  const manufacturerActive = Boolean(
    state.manufacturer || manufacturerText.trim(),
  )
  const standardFiltersActive = Boolean(state.category || state.status)
  const help = 'This indexed lookup cannot be combined with other filters.'
  return (
    <Stack direction={{ xs: 'column', md: 'row' }} gap={3} sx={{ flex: 1 }}>
      <Tooltip title={indexedSearchActive || manufacturerActive ? help : ''}>
        <span>
          <TextField
            select
            fullWidth
            label="Category"
            value={state.category}
            disabled={indexedSearchActive || manufacturerActive}
            onChange={(event) => onCategoryChange(event.target.value)}
            sx={{ minWidth: { md: 170 } }}
          >
            {categoryOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
        </span>
      </Tooltip>
      <Tooltip title={indexedSearchActive || manufacturerActive ? help : ''}>
        <span>
          <TextField
            select
            fullWidth
            label="Status"
            value={state.status}
            disabled={indexedSearchActive || manufacturerActive}
            onChange={(event) => onStatusChange(event.target.value)}
            sx={{ minWidth: { md: 170 } }}
          >
            {statusOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
        </span>
      </Tooltip>
      <Tooltip
        title={
          indexedSearchActive || standardFiltersActive
            ? help
            : 'Matches manufacturer name exactly.'
        }
      >
        <span>
          <TextField
            fullWidth
            label="Manufacturer"
            placeholder="Exact manufacturer"
            value={manufacturerText}
            disabled={indexedSearchActive || standardFiltersActive}
            onChange={(event) => onManufacturerTextChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') onApplyManufacturer()
            }}
            sx={{ minWidth: { md: 200 } }}
          />
        </span>
      </Tooltip>
      <Button
        variant="outlined"
        onClick={onApplyManufacturer}
        disabled={
          !manufacturerText.trim() ||
          indexedSearchActive ||
          standardFiltersActive
        }
      >
        Apply
      </Button>
    </Stack>
  )
}
