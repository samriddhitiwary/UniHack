import { Box } from '@mui/material'
import { tokens } from '../../theme/tokens'
export function PageContainer({ children }) {
  return (
    <Box
      sx={{
        width: {
          xs: 'calc(100vw - 32px)',
          sm: 'calc(100vw - 48px)',
          lg: `calc(100vw - ${tokens.layout.sidebarWidth + 64}px)`,
        },
        minWidth: 0,
        boxSizing: 'border-box',
        maxWidth: tokens.layout.contentMaxWidth,
        ml: { xs: 4, sm: 6, lg: 'auto' },
        mr: { xs: 0, lg: 'auto' },
        py: { xs: 6, md: 8 },
      }}
    >
      {children}
    </Box>
  )
}
