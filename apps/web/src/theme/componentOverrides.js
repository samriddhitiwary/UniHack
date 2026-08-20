import { alpha } from '@mui/material/styles'

import { tokens } from './tokens'

export const componentOverrides = {
  MuiButton: {
    defaultProps: { disableElevation: true },
    styleOverrides: {
      root: {
        minHeight: 38,
        borderRadius: tokens.radius.input,
        paddingInline: 16,
        transition: `all ${tokens.transition}`,
      },
      containedPrimary: {
        boxShadow: '0 1px 2px rgba(79, 70, 229, .2)',
        '&:hover': { backgroundColor: tokens.color.brand[700] },
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        border: `1px solid ${tokens.color.slate[200]}`,
        boxShadow: tokens.shadow.card,
        borderRadius: tokens.radius.card,
      },
    },
  },
  MuiPaper: {
    styleOverrides: { rounded: { borderRadius: tokens.radius.card } },
  },
  MuiTextField: { defaultProps: { size: 'small' } },
  MuiOutlinedInput: {
    styleOverrides: {
      root: {
        borderRadius: tokens.radius.input,
        backgroundColor: '#fff',
        '&.Mui-focused': {
          boxShadow: `0 0 0 3px ${alpha(tokens.color.brand[500], 0.14)}`,
        },
      },
      notchedOutline: { borderColor: tokens.color.slate[300] },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: { borderRadius: tokens.radius.pill, fontWeight: 650 },
      sizeSmall: { height: 24, fontSize: 12 },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        backgroundColor: tokens.color.slate[900],
        borderRadius: 7,
        fontSize: 12,
        padding: '7px 10px',
      },
    },
  },
  MuiMenu: {
    styleOverrides: {
      paper: {
        marginTop: 6,
        border: `1px solid ${tokens.color.slate[200]}`,
        boxShadow: tokens.shadow.raised,
      },
    },
  },
  MuiTableCell: {
    styleOverrides: {
      root: { borderColor: tokens.color.slate[200], padding: '13px 16px' },
      head: {
        color: tokens.color.slate[600],
        backgroundColor: tokens.color.slate[50],
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: '.025em',
      },
    },
  },
  MuiIconButton: {
    styleOverrides: {
      root: {
        borderRadius: tokens.radius.input,
        transition: `all ${tokens.transition}`,
        '&:focus-visible': {
          outline: `3px solid ${alpha(tokens.color.brand[500], 0.3)}`,
          outlineOffset: 2,
        },
      },
    },
  },
  MuiCssBaseline: {
    styleOverrides: {
      '*': { boxSizing: 'border-box' },
      html: { minWidth: 320 },
      body: { margin: 0 },
      '::selection': { backgroundColor: tokens.color.brand[100] },
      'a, button': { WebkitTapHighlightColor: 'transparent' },
    },
  },
}
