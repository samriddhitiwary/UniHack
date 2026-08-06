import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    primary: { main: '#0b6e69', dark: '#064e4a', contrastText: '#ffffff' },
    secondary: { main: '#f59e0b' },
    background: { default: '#f4f7f9', paper: '#ffffff' },
    text: { primary: '#102a43', secondary: '#486581' },
  },
  typography: {
    fontFamily:
      'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.03em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    button: { fontWeight: 700, textTransform: 'none' },
  },
  shape: { borderRadius: 12 },
})
