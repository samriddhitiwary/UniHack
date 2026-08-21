import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded'
import { Chip, Tooltip } from '@mui/material'

export function StaleIndicator({ kind = 'projection' }) {
  const title =
    kind === 'intelligence'
      ? 'This score belongs to an earlier product or catalog state.'
      : 'Product changed after this catalog projection was created.'
  return (
    <Tooltip title={title}>
      <Chip
        icon={<HistoryRoundedIcon />}
        label="Outdated"
        size="small"
        variant="outlined"
        sx={{
          color: 'warning.main',
          borderColor: 'warning.light',
          bgcolor: '#fffbeb',
        }}
      />
    </Tooltip>
  )
}
