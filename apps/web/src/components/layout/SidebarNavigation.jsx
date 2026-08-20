import {
  Box,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material'
import { NavLink } from 'react-router-dom'
import { environment } from '../../config/environment'
import { navigationSections } from '../../routes/navigation'
import { Brand } from './Brand'
export function SidebarNavigation({ onNavigate }) {
  return (
    <Stack sx={{ height: '100%', bgcolor: 'background.paper' }}>
      <Box sx={{ px: 5, py: 5 }}>
        <Brand />
      </Box>
      <Divider />
      <Box
        component="nav"
        aria-label="Primary navigation"
        sx={{ flex: 1, overflowY: 'auto', px: 3, py: 4 }}
      >
        {navigationSections.map((section, index) => (
          <Box
            key={section.label ?? 'primary'}
            sx={{ mb: index === navigationSections.length - 1 ? 0 : 5 }}
          >
            {section.label && (
              <Typography
                component="h2"
                variant="caption"
                sx={{
                  display: 'block',
                  px: 3,
                  mb: 1.5,
                  color: 'text.secondary',
                  fontWeight: 750,
                  textTransform: 'uppercase',
                  letterSpacing: '.08em',
                }}
              >
                {section.label}
              </Typography>
            )}
            <List disablePadding>
              {section.items.map((item) => {
                const Icon = item.icon
                return (
                  <ListItemButton
                    key={item.href}
                    component={NavLink}
                    to={item.href}
                    onClick={onNavigate}
                    sx={{
                      minHeight: 42,
                      px: 3,
                      py: 1.5,
                      mb: 1,
                      borderRadius: 2.5,
                      color: 'text.secondary',
                      '& .MuiListItemIcon-root': { color: 'inherit' },
                      '&.active': {
                        color: 'primary.dark',
                        bgcolor: 'primary.light',
                        fontWeight: 700,
                      },
                      '&:hover': { bgcolor: 'grey.100' },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 34 }}>
                      <Icon sx={{ fontSize: 19 }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={item.label}
                      primaryTypographyProps={{
                        fontSize: 14,
                        fontWeight: 'inherit',
                      }}
                    />
                  </ListItemButton>
                )
              })}
            </List>
          </Box>
        ))}
      </Box>
      <Box sx={{ p: 4 }}>
        <Box
          sx={{
            px: 3,
            py: 2.5,
            borderRadius: 2.5,
            bgcolor: 'grey.50',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Stack direction="row" spacing={2} alignItems="center">
            <Box
              sx={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                bgcolor: 'success.main',
              }}
            />
            <Typography
              color="text.secondary"
              variant="caption"
              fontWeight={650}
            >
              {environment.VITE_ENVIRONMENT}
            </Typography>
          </Stack>
        </Box>
      </Box>
    </Stack>
  )
}
