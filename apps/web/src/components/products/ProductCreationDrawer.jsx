import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Drawer,
  FormControl,
  FormHelperText,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { useNotifications } from '../feedback/notificationContext'
import { useCreateProduct } from '../../hooks/useCreateProduct'

const categories = [
  { value: 'UNCLASSIFIED', label: 'Unclassified' },
  { value: 'INDUCTION_MOTOR', label: 'Induction Motor' },
  { value: 'CENTRIFUGAL_PUMP', label: 'Centrifugal Pump' },
]
const optionalText = (maximum) =>
  z.string().max(maximum, `Must contain at most ${maximum} characters.`)
const productCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, 'Product name is required.')
    .max(200, 'Product name must contain at most 200 characters.'),
  manufacturer: optionalText(200),
  modelNumber: optionalText(120),
  category: z.enum(['UNCLASSIFIED', 'INDUCTION_MOTOR', 'CENTRIFUGAL_PUMP']),
  description: optionalText(4000),
})
const defaults = {
  name: '',
  manufacturer: '',
  modelNumber: '',
  category: 'UNCLASSIFIED',
  description: '',
}
function payloadFrom(values) {
  return {
    name: values.name.trim(),
    manufacturer: values.manufacturer.trim() || null,
    modelNumber: values.modelNumber.trim() || null,
    category: values.category,
    description: values.description.trim() || null,
  }
}

export function ProductCreationDrawer({
  open,
  onClose,
  onCreated,
  mutation: mutationOverride,
}) {
  const defaultMutation = useCreateProduct()
  const mutation = mutationOverride ?? defaultMutation
  const { notify } = useNotifications()
  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(productCreateSchema),
    defaultValues: defaults,
  })
  const description = watch('description')
  const close = () => {
    if (mutation.isPending) return
    reset(defaults)
    mutation.reset()
    onClose()
  }
  const submit = handleSubmit((values) => {
    mutation.mutate(payloadFrom(values), {
      onSuccess: (product) => {
        notify('Product created successfully.', 'success')
        reset(defaults)
        onClose()
        onCreated(product)
      },
      onError: () => undefined,
    })
  })
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={close}
      PaperProps={{
        component: 'aside',
        'aria-labelledby': 'create-product-title',
        sx: { width: { xs: '100%', sm: 560 }, maxWidth: '100vw' },
      }}
    >
      <Box
        component="form"
        onSubmit={submit}
        noValidate
        sx={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}
      >
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="flex-start"
          sx={{ px: { xs: 5, sm: 7 }, py: 6 }}
        >
          <Box>
            <Typography id="create-product-title" variant="h2">
              Add Product
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 430 }}>
              Create the base product record. Sources and intelligence
              processing can be added next.
            </Typography>
          </Box>
          <Tooltip title="Close">
            <IconButton aria-label="Close Add Product" onClick={close}>
              <CloseRoundedIcon />
            </IconButton>
          </Tooltip>
        </Stack>
        <Divider />
        <Stack
          spacing={7}
          sx={{ flex: 1, px: { xs: 5, sm: 7 }, py: 7, overflowY: 'auto' }}
        >
          {mutation.isError && (
            <Alert severity="error" variant="outlined">
              <Typography fontWeight={700}>
                We couldn't create this product.
              </Typography>
              <Typography variant="body2">{mutation.error.message}</Typography>
              {mutation.error.requestId && (
                <Typography variant="caption">
                  Request ID: {mutation.error.requestId}
                </Typography>
              )}
            </Alert>
          )}
          <Stack spacing={4}>
            <Box>
              <Typography variant="h3">Product identity</Typography>
              <Typography color="text.secondary" variant="body2">
                Add the names operators use to recognize this product.
              </Typography>
            </Box>
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  autoFocus
                  required
                  label="Product name"
                  placeholder="e.g. Industrial Induction Motor IM-5500"
                  error={Boolean(errors.name)}
                  helperText={errors.name?.message}
                  inputProps={{ maxLength: 200 }}
                />
              )}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
              <Controller
                name="manufacturer"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    fullWidth
                    label="Manufacturer"
                    placeholder="e.g. ABC Motors"
                    error={Boolean(errors.manufacturer)}
                    helperText={errors.manufacturer?.message ?? 'Optional'}
                    inputProps={{ maxLength: 200 }}
                  />
                )}
              />
              <Controller
                name="modelNumber"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    fullWidth
                    label="Model number"
                    placeholder="e.g. IM-5500"
                    error={Boolean(errors.modelNumber)}
                    helperText={errors.modelNumber?.message ?? 'Optional'}
                    inputProps={{ maxLength: 120 }}
                  />
                )}
              />
            </Stack>
          </Stack>
          <Divider />
          <Stack spacing={4}>
            <Box>
              <Typography variant="h3">Catalog classification</Typography>
              <Typography color="text.secondary" variant="body2">
                You can leave the product unclassified if its category will be
                determined later.
              </Typography>
            </Box>
            <Controller
              name="category"
              control={control}
              render={({ field }) => (
                <FormControl error={Boolean(errors.category)}>
                  <InputLabel id="product-category-label">Category</InputLabel>
                  <Select
                    {...field}
                    labelId="product-category-label"
                    label="Category"
                  >
                    {categories.map((category) => (
                      <MenuItem key={category.value} value={category.value}>
                        {category.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.category && (
                    <FormHelperText>{errors.category.message}</FormHelperText>
                  )}
                </FormControl>
              )}
            />
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  multiline
                  minRows={4}
                  label="Description"
                  placeholder="Optional product context or existing description"
                  error={Boolean(errors.description)}
                  helperText={
                    errors.description?.message ??
                    `${description.length} / 4000 · Optional`
                  }
                  inputProps={{ maxLength: 4000 }}
                />
              )}
            />
          </Stack>
        </Stack>
        <Box
          sx={{
            position: 'sticky',
            bottom: 0,
            bgcolor: 'background.paper',
            borderTop: '1px solid',
            borderColor: 'divider',
            px: { xs: 5, sm: 7 },
            py: 4,
          }}
        >
          <Stack direction="row" justifyContent="flex-end" spacing={3}>
            <Button
              variant="text"
              onClick={close}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={mutation.isPending}
              startIcon={
                mutation.isPending ? (
                  <CircularProgress color="inherit" size={16} />
                ) : undefined
              }
            >
              {mutation.isPending ? 'Creating…' : 'Create Product'}
            </Button>
          </Stack>
        </Box>
      </Box>
    </Drawer>
  )
}
