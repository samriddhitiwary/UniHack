import { CardContent, Skeleton, Stack } from '@mui/material'
import { AppCard } from './AppCard'

export function CardSkeleton() {
  return (
    <AppCard>
      <CardContent>
        <Stack spacing={3}>
          <Skeleton width="42%" />
          <Skeleton height={30} />
          <Skeleton height={30} />
        </Stack>
      </CardContent>
    </AppCard>
  )
}
export function PageSkeleton() {
  return (
    <Stack spacing={6} aria-label="Loading dashboard">
      <Stack spacing={2}>
        <Skeleton width={180} height={42} />
        <Skeleton width="48%" />
      </Stack>
      <Stack
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            lg: 'repeat(4, 1fr)',
          },
          gap: 4,
        }}
      >
        {Array.from({ length: 4 }, (_, i) => (
          <CardSkeleton key={i} />
        ))}
      </Stack>
      <Stack
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1.6fr 1fr' },
          gap: 4,
        }}
      >
        <CardSkeleton />
        <CardSkeleton />
      </Stack>
    </Stack>
  )
}
export function TableSkeleton({ rows = 5 }) {
  return (
    <Stack spacing={1} aria-label="Loading table" sx={{ p: 4 }}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={44} />
      ))}
    </Stack>
  )
}
