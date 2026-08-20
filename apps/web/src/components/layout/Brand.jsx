import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import { Box, Stack, Typography } from '@mui/material'
import { environment } from '../../config/environment'
export function Brand({ compact = false }) {
  return (
    <Stack direction="row" spacing={2.5} alignItems="center">
      <Box
        sx={{
          width: 34,
          height: 34,
          borderRadius: 2.5,
          display: 'grid',
          placeItems: 'center',
          color: 'white',
          bgcolor: 'primary.main',
        }}
      >
        <AutoAwesomeRoundedIcon sx={{ fontSize: 19 }} />
      </Box>
      <Box>
        <Typography fontSize={16} fontWeight={750} letterSpacing="-.02em">
          {environment.VITE_APP_NAME}
        </Typography>
        {!compact && (
          <Typography color="text.secondary" variant="caption">
            AI Product Intelligence
          </Typography>
        )}
      </Box>
    </Stack>
  )
}
