import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import { Box, CardContent, Stack, Typography } from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'

export function ImprovementOpportunities({ recommendations }) {
  return (
    <AppCard>
      <CardContent sx={{ p: { xs: 4, md: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Improvement opportunities"
            subtitle="Deterministic recommendations derived from measured issues—no generative scoring."
          />
          {recommendations.map((item, index) => (
            <Stack
              key={item.code}
              direction="row"
              spacing={3}
              alignItems="flex-start"
            >
              <Box
                sx={{
                  display: 'grid',
                  placeItems: 'center',
                  width: 30,
                  height: 30,
                  flexShrink: 0,
                  borderRadius: 2,
                  bgcolor: index === 0 ? 'warning.light' : 'primary.light',
                  color: index === 0 ? 'warning.dark' : 'primary.main',
                }}
              >
                <ArrowForwardRoundedIcon fontSize="small" />
              </Box>
              <Stack spacing={0.5}>
                <Typography fontWeight={720}>{item.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.description}
                </Typography>
              </Stack>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </AppCard>
  )
}
