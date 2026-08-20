import MenuRoundedIcon from '@mui/icons-material/MenuRounded'
import {
  AppBar,
  Box,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material'
import { useLocation } from 'react-router-dom'
import { navigationSections } from '../../routes/navigation'
import { tokens } from '../../theme/tokens'
import { Brand } from './Brand'
function currentLabel(pathname) {
  return (
    navigationSections
      .flatMap((section) => section.items)
      .find(
        (item) =>
          pathname === item.href || pathname.startsWith(`${item.href}/`),
      )?.label ?? 'Overview'
  )
}

export function TopHeader({ onMenuOpen }) {
  const location = useLocation()
  const label = currentLabel(location.pathname)
  return (
    <AppBar
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        width: { lg: `calc(100% - ${tokens.layout.sidebarWidth}px)` },
        ml: { lg: `${tokens.layout.sidebarWidth}px` },
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: 'rgba(255,255,255,.96)',
      }}
    >
      <Toolbar
        sx={{
          minHeight: `${tokens.layout.headerHeight}px !important`,
          px: { xs: 4, sm: 6, lg: 8 },
        }}
      >
        <Tooltip title="Open navigation">
          <IconButton
            aria-label="Open navigation"
            onClick={onMenuOpen}
            sx={{ display: { lg: 'none' }, mr: 2 }}
          >
            <MenuRoundedIcon />
          </IconButton>
        </Tooltip>
        <Box sx={{ display: { xs: 'block', sm: 'none' }, mr: 3 }}>
          <Brand compact />
        </Box>
        <Stack direction="row" alignItems="center" spacing={2} minWidth={0}>
          <Typography
            color="text.secondary"
            variant="body2"
            sx={{ display: { xs: 'none', sm: 'block' } }}
          >
            CatalogIQ
          </Typography>
          <Typography
            color="text.disabled"
            sx={{ display: { xs: 'none', sm: 'block' } }}
          >
            /
          </Typography>
          <Typography variant="body2" fontWeight={700} noWrap>
            {label}
          </Typography>
        </Stack>
        <Box sx={{ flex: 1 }} />
        <Typography
          color="text.secondary"
          variant="caption"
          sx={{ display: { xs: 'none', sm: 'block' } }}
        >
          Local environment
        </Typography>
      </Toolbar>
    </AppBar>
  )
}
