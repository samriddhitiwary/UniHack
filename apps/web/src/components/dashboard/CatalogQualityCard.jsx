import { Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
export function CatalogQualityCard({ items }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: 5, '&:last-child': { pb: 5 } }}>
        <Stack spacing={5}>
          <SectionHeader
            title="Catalog Quality"
            subtitle="Quality distribution across evaluated product catalogs."
          />
          <Stack spacing={3}>
            {items.map((item) => (
              <Box
                key={item.label}
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '68px 1fr 38px',
                  gap: 3,
                  alignItems: 'center',
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {item.label}
                </Typography>
                <Box
                  sx={{
                    height: 7,
                    borderRadius: 99,
                    bgcolor: 'grey.100',
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    sx={{
                      width: `${item.value}%`,
                      minWidth: item.value > 0 ? 4 : 0,
                      height: '100%',
                      bgcolor: item.color,
                      borderRadius: 'inherit',
                    }}
                  />
                </Box>
                <Typography variant="body2" fontWeight={700} textAlign="right">
                  {item.value}%
                </Typography>
              </Box>
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
