import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import { ComingSoonPage } from '../pages/ComingSoonPage'
import { OverviewPage } from '../pages/OverviewPage'
import { ProductDetailPage } from '../pages/ProductDetailPage'
import { ProductsPage } from '../pages/ProductsPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<OverviewPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:productId" element={<ProductDetailPage />} />
        <Route
          path="workflows"
          element={<ComingSoonPage title="Workflows" />}
        />
        <Route
          path="quality"
          element={<ComingSoonPage title="Catalog Quality" />}
        />
        <Route
          path="ai-enrichment"
          element={<ComingSoonPage title="AI Enrichment" />}
        />
        <Route path="exports" element={<ComingSoonPage title="Exports" />} />
        <Route path="settings" element={<ComingSoonPage title="Settings" />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
