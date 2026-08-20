import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded'
import {
  Box,
  Button,
  CardContent,
  Divider,
  Stack,
  Typography,
} from '@mui/material'
import { AppCard } from '../common/AppCard'
import { SectionHeader } from '../common/SectionHeader'
const icons = {
  warning: WarningAmberRoundedIcon,
  error: ErrorOutlineRoundedIcon,
  info: InfoOutlinedIcon,
}
const colors = {
  warning: 'warning.main',
  error: 'error.main',
  info: 'info.main',
}
export function AttentionRequiredCard({ items }) {
  return (
    <AppCard sx={{ height: '100%' }}>
      <CardContent sx={{ p: 5, '&:last-child': { pb: 5 } }}>
        <Stack spacing={4}>
          <SectionHeader
            title="Attention Required"
            subtitle="Items that need review or corrective action."
          />
          <Stack divider={<Divider flexItem />}>
            {items.map((item) => {
              const Icon = icons[item.tone]
              return (
                <Stack key={item.id} direction="row" spacing={3} sx={{ py: 3 }}>
                  <Box sx={{ color: colors[item.tone], pt: 0.5 }}>
                    <Icon fontSize="small" />
                  </Box>
                  <Stack spacing={1.5} flex={1}>
                    <Box>
                      <Typography fontWeight={700}>{item.title}</Typography>
                      <Typography color="text.secondary" variant="body2">
                        {item.description}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      variant="text"
                      endIcon={<ArrowForwardRoundedIcon />}
                      sx={{ alignSelf: 'flex-start', px: 0, minHeight: 30 }}
                    >
                      {item.action}
                    </Button>
                  </Stack>
                </Stack>
              )
            })}
          </Stack>
        </Stack>
      </CardContent>
    </AppCard>
  )
}
