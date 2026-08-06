import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import { Box, Chip, Paper, Stack, Typography } from '@mui/material'

export function HomePage() {
  return (
    <Paper
      elevation={0}
      sx={{ border: '1px solid', borderColor: 'divider', p: { xs: 4, md: 7 } }}
    >
      <Stack spacing={3} maxWidth="760px">
        <Chip
          icon={<CheckCircleRoundedIcon />}
          label="Foundation ready"
          color="primary"
          variant="outlined"
          sx={{ alignSelf: 'flex-start' }}
        />
        <Box>
          <Typography component="h1" variant="h2" gutterBottom>
            Product intelligence, built on trustworthy foundations.
          </Typography>
          <Typography color="text.secondary" variant="h6" fontWeight={400}>
            CatalogIQ AI is configured for a serverless API and a focused
            product workflow. Product features arrive through dedicated
            specifications.
          </Typography>
        </Box>
      </Stack>
    </Paper>
  )
}
