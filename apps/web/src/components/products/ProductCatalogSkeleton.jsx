import { Box, Skeleton, Stack } from '@mui/material'
import { TableSkeleton } from '../common/LoadingSkeletons'
export function ProductCatalogSkeleton() {
  return (
    <>
      <Box sx={{ display: { xs: 'none', md: 'block' } }}>
        <TableSkeleton rows={7} />
      </Box>
      <Stack
        sx={{ display: { xs: 'flex', md: 'none' }, p: 4 }}
        spacing={3}
        aria-label="Loading products"
      >
        {Array.from({ length: 4 }, (_, index) => (
          <Box
            key={index}
            sx={{
              p: 4,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 3,
            }}
          >
            <Skeleton width="70%" />
            <Skeleton width="45%" />
            <Skeleton height={56} />
          </Box>
        ))}
      </Stack>
    </>
  )
}
