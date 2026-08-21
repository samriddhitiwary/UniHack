import { Box } from '@mui/material'
import { tokens } from '../../theme/tokens'
export function PageContainer({ children }) {
  return (
    <Box
      sx={{
        width: {
          xs: 'calc(100% - 32px)',
          sm: 'calc(100% - 48px)',
          lg: 'calc(100% - 64px)',
        },
        minWidth: 0,
        boxSizing: 'border-box',
        maxWidth: tokens.layout.contentMaxWidth,
        mx: 'auto',
        py: { xs: 6, md: 8 },
      }}
    >
      {children}
    </Box>
  )
}
