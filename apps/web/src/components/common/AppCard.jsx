import { Card } from '@mui/material'

const variants = {
  default: {},
  subtle: { backgroundColor: 'grey.50' },
  outlined: { boxShadow: 'none' },
  interactive: {
    transition: 'transform 180ms ease, box-shadow 180ms ease',
    '&:hover': { transform: 'translateY(-1px)', boxShadow: 3 },
  },
}

export function AppCard({ variant = 'default', sx, ...props }) {
  return <Card elevation={0} sx={{ ...variants[variant], ...sx }} {...props} />
}
