import {
  Box,
  Button,
  CardContent,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import { useMemo, useState } from 'react'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
import { comparisonStatusLabel } from '../../utils/qualityFormat'

const statusStyles = {
  EXACT_MATCH: { bgcolor: '#f0fdf4', borderColor: '#bbf7d0', color: '#15803d' },
  NORMALIZED_MATCH: {
    bgcolor: '#f0f9ff',
    borderColor: '#bae6fd',
    color: '#0369a1',
  },
  MISMATCH: { bgcolor: '#fef2f2', borderColor: '#fecaca', color: '#b91c1c' },
  EXPECTED_POPULATED_ACTUAL_BLANK: {
    bgcolor: '#fffbeb',
    borderColor: '#fde68a',
    color: '#b45309',
  },
  EXPECTED_BLANK_ACTUAL_POPULATED: {
    bgcolor: '#f0f9ff',
    borderColor: '#bae6fd',
    color: '#0369a1',
  },
  BOTH_BLANK: {
    bgcolor: 'grey.50',
    borderColor: 'divider',
    color: 'text.secondary',
  },
}

function matchesFilter(status, filter) {
  if (filter === 'matches')
    return ['EXACT_MATCH', 'NORMALIZED_MATCH'].includes(status)
  if (filter === 'mismatches')
    return ['MISMATCH', 'EXPECTED_BLANK_ACTUAL_POPULATED'].includes(status)
  if (filter === 'missing') return status === 'EXPECTED_POPULATED_ACTUAL_BLANK'
  return true
}

export function LabelledRowComparison({
  rows,
  selectedId,
  onSelect,
  comparison,
  loading,
}) {
  const [filter, setFilter] = useState('all')
  const [showBlank, setShowBlank] = useState(false)
  const comparisons = useMemo(
    () =>
      (comparison?.comparisons ?? []).filter(
        (item) =>
          matchesFilter(item.status, filter) &&
          (showBlank || item.status !== 'BOTH_BLANK'),
      ),
    [comparison, filter, showBlank],
  )
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={5}>
          <SectionHeader
            title="Labelled row comparison"
            subtitle="Expected versus CatalogIQ output. Both-blank fields are hidden by default."
          />
          <Stack
            direction="row"
            flexWrap="wrap"
            gap={2}
            aria-label="Select labelled product"
          >
            {rows.map((row) => (
              <Button
                key={row.inputRowId}
                variant={
                  selectedId === row.inputRowId ? 'contained' : 'outlined'
                }
                onClick={() => onSelect(row.inputRowId)}
                aria-pressed={selectedId === row.inputRowId}
              >
                {row.mfgPartNum}
              </Button>
            ))}
          </Stack>
          {comparison && (
            <Typography variant="body2" color="text.secondary">
              {comparison.accuracy.exactMatchCount} exact ·{' '}
              {comparison.accuracy.mismatchCount} mismatches ·{' '}
              {comparison.accuracy.expectedPopulatedActualBlankCount} expected
              values missing
            </Typography>
          )}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            justifyContent="space-between"
            alignItems={{ sm: 'center' }}
            gap={3}
          >
            <ToggleButtonGroup
              exclusive
              size="small"
              value={filter}
              onChange={(_, value) => value && setFilter(value)}
              aria-label="Comparison result filter"
              sx={{ flexWrap: 'wrap' }}
            >
              <ToggleButton value="all">All</ToggleButton>
              <ToggleButton value="matches">Matches</ToggleButton>
              <ToggleButton value="mismatches">Mismatches</ToggleButton>
              <ToggleButton value="missing">Missing</ToggleButton>
            </ToggleButtonGroup>
            <FormControlLabel
              control={
                <Switch
                  checked={showBlank}
                  onChange={(event) => setShowBlank(event.target.checked)}
                />
              }
              label="Show blank fields"
            />
          </Stack>
          {loading ? (
            <Stack alignItems="center" py={8}>
              <CircularProgress
                size={28}
                aria-label="Loading labelled comparison"
              />
            </Stack>
          ) : (
            <Stack
              role="table"
              aria-label="Labelled field comparison"
              spacing={1.5}
            >
              <Box
                role="row"
                sx={{
                  display: { xs: 'none', md: 'grid' },
                  gridTemplateColumns: '.75fr 1.25fr 1.25fr .55fr',
                  gap: 3,
                  px: 3,
                  pb: 1,
                }}
              >
                {['Field', 'Expected', 'CatalogIQ', 'Result'].map((label) => (
                  <Typography
                    key={label}
                    role="columnheader"
                    variant="caption"
                    color="text.secondary"
                  >
                    {label}
                  </Typography>
                ))}
              </Box>
              {comparisons.map((item) => (
                <Box
                  role="row"
                  key={item.fieldName}
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: {
                      xs: '1fr',
                      md: '.75fr 1.25fr 1.25fr .55fr',
                    },
                    gap: { xs: 1.5, md: 3 },
                    p: 3,
                    border: 1,
                    borderRadius: 2.5,
                    ...statusStyles[item.status],
                  }}
                >
                  <Typography
                    role="cell"
                    fontWeight={720}
                    sx={{ overflowWrap: 'anywhere' }}
                  >
                    {item.fieldName}
                  </Typography>
                  <ValueCell label="Expected" value={item.expectedValue} />
                  <ValueCell label="CatalogIQ" value={item.actualValue} />
                  <Typography role="cell" fontWeight={700}>
                    {comparisonStatusLabel(item.status)}
                  </Typography>
                </Box>
              ))}
              {!comparisons.length && !loading && (
                <Typography color="text.secondary" textAlign="center" py={6}>
                  No fields match this filter.
                </Typography>
              )}
            </Stack>
          )}
        </Stack>
      </CardContent>
    </AppCard>
  )
}

function ValueCell({ label, value }) {
  return (
    <Stack role="cell" spacing={0.25} minWidth={0}>
      <Typography
        sx={{ display: { md: 'none' } }}
        variant="caption"
        color="text.secondary"
      >
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}
      >
        {value || '—'}
      </Typography>
    </Stack>
  )
}
