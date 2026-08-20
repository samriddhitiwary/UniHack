import { createTheme } from '@mui/material/styles'

import { componentOverrides } from './componentOverrides'
import { tokens } from './tokens'
import { typography } from './typography'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: tokens.color.brand[600],
      dark: tokens.color.brand[700],
      light: tokens.color.brand[100],
      contrastText: '#fff',
    },
    background: { default: tokens.color.slate[50], paper: '#fff' },
    text: {
      primary: tokens.color.slate[900],
      secondary: tokens.color.slate[600],
    },
    divider: tokens.color.slate[200],
    success: { main: tokens.color.success.main },
    warning: { main: tokens.color.warning.main },
    error: { main: tokens.color.error.main },
    info: { main: tokens.color.info.main },
  },
  typography,
  shape: { borderRadius: tokens.radius.card },
  spacing: 4,
  shadows: [
    'none',
    tokens.shadow.card,
    tokens.shadow.card,
    tokens.shadow.raised,
    ...Array(21).fill(tokens.shadow.raised),
  ],
  components: componentOverrides,
})
