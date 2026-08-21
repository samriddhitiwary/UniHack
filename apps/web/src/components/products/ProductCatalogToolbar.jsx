import ClearRoundedIcon from '@mui/icons-material/ClearRounded'
import FilterListRoundedIcon from '@mui/icons-material/FilterListRounded'
import SearchRoundedIcon from '@mui/icons-material/SearchRounded'
import {
  Badge,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  InputAdornment,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { ActiveFilters } from './ActiveFilters'
import { ProductFilters } from './ProductFilters'

export function ProductCatalogToolbar({
  state,
  searchText,
  onSearchTextChange,
  manufacturerText,
  onManufacturerTextChange,
  onSubmitSearch,
  onModeChange,
  onApplyManufacturer,
  onCategoryChange,
  onStatusChange,
  onRemoveFilter,
  onClearAll,
}) {
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)
  const activeCount = [
    state.q,
    state.category,
    state.status,
    state.manufacturer,
  ].filter(Boolean).length
  const manufacturerPattern = Boolean(state.manufacturer)
  return (
    <Stack>
      <Stack
        direction={{ xs: 'column', lg: 'row' }}
        gap={3}
        sx={{ p: { xs: 4, md: 5 } }}
      >
        <Stack
          component="form"
          role="search"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmitSearch()
          }}
          direction="row"
          gap={2}
          sx={{
            minWidth: 0,
            maxWidth: '100%',
            width: '100%',
            flex: { lg: '0 1 480px' },
          }}
        >
          <TextField
            select
            label="Search products by"
            value={state.searchMode}
            disabled={manufacturerPattern}
            onChange={(event) => onModeChange(event.target.value)}
            sx={{ width: 142, flexShrink: 0 }}
          >
            <MenuItem value="name">Product name</MenuItem>
            <MenuItem value="model">Model number</MenuItem>
          </TextField>
          <TextField
            fullWidth
            sx={{ minWidth: 0 }}
            value={searchText}
            disabled={manufacturerPattern}
            onChange={(event) => onSearchTextChange(event.target.value)}
            placeholder={
              state.searchMode === 'model'
                ? 'Enter exact model number'
                : 'Search by product name'
            }
            inputProps={{
              'aria-label':
                state.searchMode === 'model'
                  ? 'Exact model number'
                  : 'Product name prefix',
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchRoundedIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchText ? (
                <InputAdornment position="end">
                  <Tooltip title="Clear product search">
                    <IconButton
                      size="small"
                      aria-label="Clear product search"
                      onClick={() => {
                        onSearchTextChange('')
                        if (state.q) onRemoveFilter('q')
                      }}
                    >
                      <ClearRoundedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              ) : undefined,
            }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={!searchText.trim() || manufacturerPattern}
            sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
          >
            Search
          </Button>
        </Stack>
        <Box sx={{ display: { xs: 'none', md: 'flex' }, flex: 1 }}>
          <ProductFilters
            state={state}
            manufacturerText={manufacturerText}
            onManufacturerTextChange={onManufacturerTextChange}
            onApplyManufacturer={onApplyManufacturer}
            onCategoryChange={onCategoryChange}
            onStatusChange={onStatusChange}
          />
        </Box>
        <Button
          variant="outlined"
          startIcon={
            <Badge color="primary" badgeContent={activeCount}>
              <FilterListRoundedIcon />
            </Badge>
          }
          onClick={() => setMobileFiltersOpen(true)}
          aria-label="Open product filters"
          sx={{
            display: { xs: 'inline-flex', md: 'none' },
            alignSelf: 'flex-start',
          }}
        >
          Filters{activeCount ? ` (${activeCount})` : ''}
        </Button>
      </Stack>
      <Box sx={{ px: { xs: 4, md: 5 }, pb: activeCount ? 4 : 0 }}>
        <ActiveFilters
          state={state}
          onRemove={onRemoveFilter}
          onClear={onClearAll}
        />
      </Box>
      {activeCount > 0 && <Divider />}
      <Drawer
        anchor="bottom"
        open={mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        PaperProps={{ sx: { borderRadius: '16px 16px 0 0', p: 5 } }}
      >
        <Stack spacing={5}>
          <Box>
            <Typography variant="h3">Product filters</Typography>
            <Typography color="text.secondary" variant="body2">
              Use category and status together, or an exact manufacturer lookup.
            </Typography>
          </Box>
          <ProductFilters
            state={state}
            manufacturerText={manufacturerText}
            onManufacturerTextChange={onManufacturerTextChange}
            onApplyManufacturer={() => {
              onApplyManufacturer()
              setMobileFiltersOpen(false)
            }}
            onCategoryChange={onCategoryChange}
            onStatusChange={onStatusChange}
          />
          <Button onClick={() => setMobileFiltersOpen(false)}>Done</Button>
        </Stack>
      </Drawer>
    </Stack>
  )
}
