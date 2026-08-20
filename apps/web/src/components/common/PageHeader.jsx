import { Breadcrumbs, Link, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

export function PageHeader({
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  status,
}) {
  return (
    <Stack spacing={2.5}>
      {breadcrumbs.length > 0 && (
        <Breadcrumbs aria-label="Breadcrumbs">
          {breadcrumbs.map((item) =>
            item.href ? (
              <Link
                key={item.label}
                component={RouterLink}
                to={item.href}
                color="text.secondary"
                underline="hover"
              >
                {item.label}
              </Link>
            ) : (
              <Typography
                key={item.label}
                color="text.secondary"
                variant="body2"
              >
                {item.label}
              </Typography>
            ),
          )}
        </Breadcrumbs>
      )}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ sm: 'flex-start' }}
        gap={3}
      >
        <Stack spacing={1} minWidth={0}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography component="h1" variant="h1">
              {title}
            </Typography>
            {status}
          </Stack>
          {subtitle && (
            <Typography color="text.secondary" maxWidth={760}>
              {subtitle}
            </Typography>
          )}
        </Stack>
        {actions && (
          <Stack direction="row" spacing={2} flexShrink={0}>
            {actions}
          </Stack>
        )}
      </Stack>
    </Stack>
  )
}
