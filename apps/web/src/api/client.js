import axios from 'axios'
import { environment } from '../config/environment'
import { normalizeApiError } from './errors'

export const apiClient = axios.create({
  baseURL: environment.VITE_API_BASE_URL,
  headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
  timeout: 15000,
})
apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeApiError(error)),
)
