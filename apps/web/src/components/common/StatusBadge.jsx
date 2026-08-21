import { Chip } from '@mui/material'
import { statusSemantics, tokens } from '../../theme/tokens'

const colors = {
  neutral: {
    color: tokens.color.slate[600],
    backgroundColor: tokens.color.slate[100],
    borderColor: tokens.color.slate[200],
  },
  success: {
    color: tokens.color.success.main,
    backgroundColor: tokens.color.success.soft,
    borderColor: tokens.color.success.border,
  },
  warning: {
    color: tokens.color.warning.main,
    backgroundColor: tokens.color.warning.soft,
    borderColor: tokens.color.warning.border,
  },
  error: {
    color: tokens.color.error.main,
    backgroundColor: tokens.color.error.soft,
    borderColor: tokens.color.error.border,
  },
  info: {
    color: tokens.color.info.main,
    backgroundColor: tokens.color.info.soft,
    borderColor: tokens.color.info.border,
  },
}

function formatStatus(value) {
  return value
    .toLowerCase()
    .split('_')
    .map((word, index) =>
      index > 0 && ['to', 'with', 'for'].includes(word)
        ? word
        : word[0].toUpperCase() + word.slice(1),
    )
    .join(' ')
}
export function StatusBadge({ status, label }) {
  const tone = statusSemantics[status] ?? 'neutral'
  return (
    <Chip
      size="small"
      variant="outlined"
      label={label ?? formatStatus(status)}
      sx={colors[tone]}
    />
  )
}
