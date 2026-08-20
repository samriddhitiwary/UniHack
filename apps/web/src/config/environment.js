import { z } from 'zod'

const environmentSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default('http://localhost:8000/api/v1'),
  VITE_APP_NAME: z.string().min(1).default('CatalogIQ'),
  VITE_ENVIRONMENT: z.string().min(1).default('Local Development'),
})

export const environment = environmentSchema.parse(import.meta.env)
