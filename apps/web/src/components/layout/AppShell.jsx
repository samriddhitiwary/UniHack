import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import {
  AppBar,
  Box,
  Container,
  Stack,
  Toolbar,
  Typography,
} from '@mui/material'
import { Outlet } from 'react-router-dom'

import { environment } from '../../config/environment'

export function AppShell() {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <AutoAwesomeRoundedIcon sx={{ mr: 1.25 }} aria-hidden="true" />
          <Typography component="span" variant="h6" fontWeight={700}>
            {environment.VITE_APP_NAME}
          </Typography>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
        <Stack spacing={4}>
          <Outlet />
        </Stack>
      </Container>
    </Box>
  )
}
