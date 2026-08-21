import { Box, Tab, Tabs } from '@mui/material'

export function ProductWorkspaceTabs({ value, onChange }) {
  return (
    <Box
      sx={{
        borderBottom: '1px solid',
        borderColor: 'divider',
        overflowX: 'auto',
      }}
    >
      <Tabs
        value={value}
        onChange={(_, next) => onChange(next)}
        aria-label="Product workspace sections"
        variant="scrollable"
        scrollButtons={false}
        sx={{
          minHeight: 44,
          '& .MuiTabs-indicator': { height: 2, borderRadius: 2 },
          '& .MuiTab-root': { minHeight: 44, textTransform: 'none' },
        }}
      >
        <Tab label="Overview" value="overview" />
        <Tab label="Sources" value="sources" />
        <Tab label="Workflow" value="workflow" />
      </Tabs>
    </Box>
  )
}
