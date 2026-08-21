import AddRoundedIcon from '@mui/icons-material/AddRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded'
import {
  Alert,
  Box,
  Button,
  Divider,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { useNotifications } from '../feedback/notificationContext'
import {
  useCreateTextSource,
  useDeleteProductSource,
  useUploadProductSource,
} from '../../hooks/useSourceMutations'
import { SectionHeader } from '../common/SectionHeader'
import { SourceDropzone } from './SourceDropzone'
import { SourceCard } from './SourceCard'
import { TextSourceDrawer } from './TextSourceDrawer'
import { DeleteSourceDialog } from './DeleteSourceDialog'

export function SourcesSection({ productId, query, activeWorkflow }) {
  const { notify } = useNotifications()
  const [textOpen, setTextOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const upload = useUploadProductSource(productId)
  const createText = useCreateTextSource(productId)
  const remove = useDeleteProductSource(productId)
  const sources = query.data?.pages.flatMap((page) => page.items) ?? []
  const addedMessage = activeWorkflow
    ? 'Source added. It will be included the next time you start a workflow.'
    : 'Source added successfully.'
  return (
    <Stack spacing={5}>
      <SectionHeader
        title="Sources"
        subtitle="Provide the product information CatalogIQ uses to build and validate the catalog."
        action={
          <Button
            startIcon={<AddRoundedIcon />}
            onClick={() => setTextOpen(true)}
          >
            Add Text Source
          </Button>
        }
      />
      <SourceDropzone
        uploading={upload.isPending}
        onUpload={(file) =>
          upload.mutate(
            { productId, file },
            {
              onSuccess: () =>
                notify(
                  activeWorkflow
                    ? addedMessage
                    : 'Source uploaded successfully.',
                  'success',
                ),
            },
          )
        }
      />
      {upload.isError && (
        <Alert severity="error">
          {upload.error.message}
          {upload.error.requestId && ` · Request ID: ${upload.error.requestId}`}
        </Alert>
      )}
      {activeWorkflow && (
        <Alert severity="info">
          New sources are included only when the next workflow starts. Sources
          cannot be deleted while this workflow is active.
        </Alert>
      )}
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        {query.isLoading ? (
          <Stack spacing={2} sx={{ p: 4 }} aria-label="Loading sources">
            {Array.from({ length: 3 }, (_, index) => (
              <Skeleton key={index} height={72} />
            ))}
          </Stack>
        ) : query.isError ? (
          <Stack alignItems="center" spacing={3} sx={{ p: 6 }}>
            <Typography fontWeight={700}>We couldn't load sources.</Typography>
            {query.error.requestId && (
              <Typography variant="caption">
                Request ID: {query.error.requestId}
              </Typography>
            )}
            <Button
              startIcon={<RefreshRoundedIcon />}
              onClick={() => query.refetch()}
            >
              Retry
            </Button>
          </Stack>
        ) : sources.length === 0 ? (
          <Stack
            alignItems="center"
            textAlign="center"
            spacing={3}
            sx={{ p: 8 }}
          >
            <UploadFileRoundedIcon color="primary" />
            <Stack spacing={1} maxWidth={520}>
              <Typography variant="h3">No sources yet</Typography>
              <Typography color="text.secondary">
                Add a PDF datasheet, CSV file, product image, nameplate, or
                trusted text source to begin building product intelligence.
              </Typography>
            </Stack>
            <Button variant="contained" onClick={() => setTextOpen(true)}>
              Add Text Source
            </Button>
          </Stack>
        ) : (
          <Stack divider={<Divider />}>
            {sources.map((source) => (
              <SourceCard
                key={source.sourceId}
                source={source}
                deleteDisabled={activeWorkflow}
                onDelete={(value) => {
                  remove.reset()
                  setDeleteTarget(value)
                }}
              />
            ))}
          </Stack>
        )}
        {query.hasNextPage && (
          <Box
            sx={{
              p: 3,
              borderTop: '1px solid',
              borderColor: 'divider',
              textAlign: 'center',
            }}
          >
            <Button
              onClick={() => query.fetchNextPage()}
              disabled={query.isFetchingNextPage}
            >
              {query.isFetchingNextPage ? 'Loading…' : 'Load more sources'}
            </Button>
          </Box>
        )}
      </Box>
      <TextSourceDrawer
        open={textOpen}
        onClose={() => setTextOpen(false)}
        mutation={createText}
        onSubmit={(values) =>
          createText.mutate(
            { productId, ...values },
            {
              onSuccess: () => {
                notify(addedMessage, 'success')
                setTextOpen(false)
              },
            },
          )
        }
      />
      <DeleteSourceDialog
        source={deleteTarget}
        mutation={remove}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() =>
          remove.mutate(
            {
              productId,
              sourceId: deleteTarget.sourceId,
              version: deleteTarget.version,
            },
            {
              onSuccess: () => {
                notify('Source deleted.', 'success')
                setDeleteTarget(null)
              },
            },
          )
        }
      />
    </Stack>
  )
}
