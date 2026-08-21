import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import {
  Box,
  Button,
  Divider,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { StatusBadge } from '../common/StatusBadge'
import { formatDateTime } from '../../utils/dateFormat'
import { stageLabels, workflowStatusLabels } from '../../utils/workflowLabels'

export function WorkflowHistory({ query, selectedId, onSelect }) {
  const items = query.data?.pages.flatMap((page) => page.items) ?? []
  return (
    <Stack spacing={3}>
      <Stack>
        <Typography variant="h3">Workflow History</Typography>
        <Typography color="text.secondary" variant="body2">
          Previous CatalogIQ processing runs for this product.
        </Typography>
      </Stack>
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        {query.isLoading ? (
          <Stack
            spacing={2}
            sx={{ p: 4 }}
            aria-label="Loading workflow history"
          >
            <Skeleton height={56} />
            <Skeleton height={56} />
          </Stack>
        ) : items.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 5 }}>
            No workflow history yet.
          </Typography>
        ) : (
          <Stack divider={<Divider />}>
            {items.map((item, index) => (
              <Button
                key={item.workflowId}
                color="inherit"
                onClick={() => onSelect(item.workflowId)}
                aria-pressed={selectedId === item.workflowId}
                sx={{
                  justifyContent: 'stretch',
                  textAlign: 'left',
                  borderRadius: 0,
                  px: 4,
                  py: 3,
                }}
              >
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  alignItems={{ sm: 'center' }}
                  gap={3}
                  width="100%"
                >
                  <Stack flex={1} minWidth={0}>
                    <Typography fontWeight={700}>
                      {index === 0 ? 'Latest workflow' : 'Previous workflow'} ·{' '}
                      {formatDateTime(item.createdAt)}
                    </Typography>
                    <Typography color="text.secondary" variant="caption">
                      {item.progressPercent}% ·{' '}
                      {item.currentStage
                        ? stageLabels[item.currentStage]
                        : 'Catalog workflow'}
                    </Typography>
                  </Stack>
                  <StatusBadge
                    status={item.status}
                    label={workflowStatusLabels[item.status]}
                  />
                  <ChevronRightRoundedIcon color="action" />
                </Stack>
              </Button>
            ))}
          </Stack>
        )}
        {query.hasNextPage && (
          <Box
            sx={{
              p: 2,
              borderTop: '1px solid',
              borderColor: 'divider',
              textAlign: 'center',
            }}
          >
            <Button
              onClick={() => query.fetchNextPage()}
              disabled={query.isFetchingNextPage}
            >
              {query.isFetchingNextPage ? 'Loading…' : 'Load more workflows'}
            </Button>
          </Box>
        )}
      </Box>
    </Stack>
  )
}
