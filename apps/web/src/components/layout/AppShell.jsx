import { Box, Drawer } from '@mui/material'
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { tokens } from '../../theme/tokens'
import { PageContainer } from './PageContainer'
import { SidebarNavigation } from './SidebarNavigation'
import { TopHeader } from './TopHeader'

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Box
        component="aside"
        sx={{
          width: { xs: 0, lg: tokens.layout.sidebarWidth },
          flexShrink: { lg: 0 },
        }}
      >
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', lg: 'block' },
            '& .MuiDrawer-paper': {
              width: tokens.layout.sidebarWidth,
              borderRightColor: 'divider',
            },
          }}
        >
          <SidebarNavigation />
        </Drawer>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', lg: 'none' },
            '& .MuiDrawer-paper': { width: tokens.layout.sidebarWidth },
          }}
        >
          <SidebarNavigation onNavigate={() => setMobileOpen(false)} />
        </Drawer>
      </Box>
      <TopHeader onMenuOpen={() => setMobileOpen(true)} />
      <Box
        component="main"
        sx={{
          flex: 1,
          minWidth: 0,
          width: {
            xs: '100vw',
            lg: `calc(100vw - ${tokens.layout.sidebarWidth}px)`,
          },
          overflowX: 'hidden',
          pt: `${tokens.layout.headerHeight}px`,
        }}
      >
        <PageContainer>
          <Outlet />
        </PageContainer>
      </Box>
    </Box>
  )
}
