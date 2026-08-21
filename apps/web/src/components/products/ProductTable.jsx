import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import { IconButton, Stack, Tooltip, Typography } from '@mui/material'
import { formatDate, formatDateTime } from '../../utils/dateFormat'
import {
  categoryOptions,
  identityMetadata,
  optionLabel,
} from '../../utils/productLabels'
import { DataTableShell } from '../common/DataTableShell'
import { IntelligenceScore } from '../common/IntelligenceScore'
import { StatusBadge } from '../common/StatusBadge'
import { StaleIndicator } from './StaleIndicator'

const columns = [
  {
    key: 'name',
    label: 'Product',
    render: (product) => (
      <Stack minWidth={220} maxWidth={360}>
        <Tooltip title={product.name} enterDelay={700}>
          <Typography fontWeight={700} noWrap>
            {product.name}
          </Typography>
        </Tooltip>
        <Typography color="text.secondary" variant="caption" noWrap>
          {identityMetadata(product)}
        </Typography>
      </Stack>
    ),
  },
  {
    key: 'status',
    label: 'Status',
    render: (product) => <StatusBadge status={product.status} />,
  },
  {
    key: 'intelligence',
    label: 'Intelligence',
    render: (product) =>
      product.intelligenceScorePercent == null ? (
        <Typography color="text.secondary" variant="body2">
          Not scored
        </Typography>
      ) : (
        <Stack spacing={1} alignItems="flex-start">
          <IntelligenceScore
            compact
            score={product.intelligenceScorePercent}
            grade={product.intelligenceGrade}
          />
          {product.intelligenceCurrent === false && (
            <StaleIndicator kind="intelligence" />
          )}
        </Stack>
      ),
  },
  {
    key: 'readiness',
    label: 'Publishing Readiness',
    render: (product) => (
      <Stack spacing={1} alignItems="flex-start">
        {product.publishingReadiness ? (
          <StatusBadge status={product.publishingReadiness} />
        ) : (
          <Typography color="text.secondary" variant="body2">
            Not evaluated
          </Typography>
        )}
        {product.projectionCurrent === false && <StaleIndicator />}
      </Stack>
    ),
  },
  {
    key: 'category',
    label: 'Category',
    render: (product) => (
      <Typography variant="body2">
        {optionLabel(categoryOptions, product.category)}
      </Typography>
    ),
  },
  {
    key: 'updated',
    label: 'Updated',
    sx: { display: { md: 'none', lg: 'table-cell' } },
    render: (product) => (
      <Typography
        variant="body2"
        title={formatDateTime(product.updatedAt)}
        noWrap
      >
        {formatDate(product.updatedAt)}
      </Typography>
    ),
  },
  {
    key: 'actions',
    label: '',
    align: 'right',
    sx: { width: 48 },
    render: (product) => (
      <Tooltip title={`Open ${product.name}`}>
        <IconButton size="small" aria-label={`Open ${product.name}`}>
          <ChevronRightRoundedIcon />
        </IconButton>
      </Tooltip>
    ),
  },
]

export function ProductTable({ products, onOpen, pagination }) {
  return (
    <DataTableShell
      columns={columns}
      rows={products}
      getRowKey={(product) => product.productId}
      onRowActivate={onOpen}
      pagination={pagination}
    />
  )
}
