import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import GridOnOutlinedIcon from '@mui/icons-material/GridOnOutlined'
import ImageOutlinedIcon from '@mui/icons-material/ImageOutlined'
import PictureAsPdfOutlinedIcon from '@mui/icons-material/PictureAsPdfOutlined'
import {
  Alert,
  Box,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { StatusBadge } from '../common/StatusBadge'
import { formatDate } from '../../utils/dateFormat'
import {
  sourceName,
  sourceStatusLabels,
  sourceTypes,
} from '../../utils/sourceLabels'

const icons = {
  PDF: PictureAsPdfOutlinedIcon,
  CSV: GridOnOutlinedIcon,
  IMAGE: ImageOutlinedIcon,
  TEXT: ArticleOutlinedIcon,
}

export function SourceCard({ source, deleteDisabled, onDelete }) {
  const Icon = icons[source.sourceType] ?? ArticleOutlinedIcon
  const name = sourceName(source)
  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      gap={4}
      sx={{ px: { xs: 4, md: 5 }, py: 4, minWidth: 0 }}
    >
      <Box
        sx={{
          width: 42,
          height: 42,
          borderRadius: 2.5,
          bgcolor: 'primary.light',
          color: 'primary.main',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
        }}
      >
        <Icon />
      </Box>
      <Stack flex={1} minWidth={0} spacing={1.5}>
        <Tooltip title={name} enterDelay={600}>
          <Typography fontWeight={700} noWrap>
            {name}
          </Typography>
        </Tooltip>
        <Stack direction="row" gap={2} flexWrap="wrap" alignItems="center">
          <Typography color="text.secondary" variant="body2">
            {sourceTypes[source.sourceType] ?? source.sourceType}
          </Typography>
          <StatusBadge
            status={source.status}
            label={sourceStatusLabels[source.status]}
          />
          <Typography color="text.secondary" variant="caption">
            Added {formatDate(source.createdAt)}
          </Typography>
        </Stack>
        {source.status === 'FAILED' && (
          <Alert severity="error" sx={{ py: 0 }}>
            Processing failed
            {source.errorMessage ? ` · ${source.errorMessage}` : ''}
          </Alert>
        )}
      </Stack>
      <Tooltip
        title={
          deleteDisabled
            ? "Sources can't be deleted while a workflow is active."
            : 'Delete source'
        }
      >
        <span>
          <IconButton
            aria-label={`Delete ${name}`}
            disabled={deleteDisabled}
            onClick={() => onDelete(source)}
          >
            <DeleteOutlineRoundedIcon />
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  )
}
