import { Box } from '@mui/material'
import { tokens } from '../../theme/tokens'
export function PageContainer({ children }) {
  return (
    <Box
      sx={{
        maxWidth: tokens.layout.contentMaxWidth,
        mx: 'auto',
        px: { xs: 4, sm: 6, lg: 8 },
        py: { xs: 6, md: 8 },
      }}
    >
      {children}
    </Box>
  )
}
