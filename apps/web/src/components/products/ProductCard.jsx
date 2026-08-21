import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import { Box, Divider, Stack, Typography } from '@mui/material'
import { formatDate, formatDateTime } from '../../utils/dateFormat'
import {
  identityMetadata,
  optionLabel,
  categoryOptions,
} from '../../utils/productLabels'
import { IntelligenceScore } from '../common/IntelligenceScore'
import { StatusBadge } from '../common/StatusBadge'
import { StaleIndicator } from './StaleIndicator'

export function ProductCard({ product, onOpen }) {
  return (
    <Box
      role="link"
      tabIndex={0}
      aria-label={`Open ${product.name}`}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onOpen()
        }
      }}
      sx={{
        p: 4,
        borderBottom: '1px solid',
        borderColor: 'divider',
        cursor: 'pointer',
        transition: 'background-color 180ms ease',
        '&:hover': { bgcolor: 'grey.50' },
        '&:focus-visible': {
          outline: '3px solid',
          outlineColor: 'primary.light',
          outlineOffset: -3,
        },
      }}
    >
      <Stack spacing={3}>
        <Stack direction="row" justifyContent="space-between" gap={2}>
          <Box minWidth={0}>
            <Typography
              fontWeight={700}
              sx={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {product.name}
            </Typography>
            <Typography color="text.secondary" variant="caption" noWrap>
              {identityMetadata(product)}
            </Typography>
          </Box>
          <ChevronRightRoundedIcon color="action" />
        </Stack>
        <Stack direction="row" flexWrap="wrap" gap={2}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ px: 2, py: 0.75, bgcolor: 'grey.100', borderRadius: 99 }}
          >
            {optionLabel(categoryOptions, product.category)}
          </Typography>
          <StatusBadge status={product.status} />
        </Stack>
        <Divider />
        <Stack spacing={2}>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Typography color="text.secondary" variant="body2">
              Intelligence
            </Typography>
            {product.intelligenceScorePercent == null ? (
              <Typography variant="body2">Not scored</Typography>
            ) : (
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="flex-end"
                flexWrap="wrap"
                gap={2}
              >
                <IntelligenceScore
                  compact
                  score={product.intelligenceScorePercent}
                  grade={product.intelligenceGrade}
                />
                {product.intelligenceCurrent === false && (
                  <StaleIndicator kind="intelligence" />
                )}
              </Stack>
            )}
          </Stack>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Typography color="text.secondary" variant="body2">
              Readiness
            </Typography>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="flex-end"
              flexWrap="wrap"
              gap={2}
            >
              {product.publishingReadiness ? (
                <StatusBadge status={product.publishingReadiness} />
              ) : (
                <Typography variant="body2">Not evaluated</Typography>
              )}
              {product.projectionCurrent === false && <StaleIndicator />}
            </Stack>
          </Stack>
          <Stack direction="row" justifyContent="space-between">
            <Typography color="text.secondary" variant="body2">
              Updated
            </Typography>
            <Typography
              variant="body2"
              title={formatDateTime(product.updatedAt)}
            >
              {formatDate(product.updatedAt)}
            </Typography>
          </Stack>
        </Stack>
      </Stack>
    </Box>
  )
}
