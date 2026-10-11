import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { TrucksPage } from '@/pages/trucks/trucks-page'
import { SitesPage } from '@/pages/sites/sites-page'
import { SiteDetailPage } from '@/pages/sites/site-detail-page'
import { RoleSelection } from '@/pages/role-selection/role-selection-page'
import { AdminLayout } from '@/components/layout/admin-layout'
import { ToastProvider } from '@/components/ui/toast'
import { ResidentRequestPage } from '@/pages/resident-request/resident-request-page'
import { MapAnalyticsPage } from '@/pages/map-analytics/map-analytics-page'
import { ProjectDateProvider } from '@/lib/project-date/provider'
import { DemoPage } from '@/pages/demo/demo-page'
import { TruckDemoPage } from '@/pages/demo/truck-demo-page'
import { TruckPickerPage } from '@/pages/driver/truck-picker-page'
import { DriverRouteScreen } from '@/pages/driver/driver-route-screen'

export default function App() {
  return (
    <ProjectDateProvider><BrowserRouter>
      <Routes>
        <Route path="/" element={<RoleSelection />} />
        <Route
          path="/resident-request/:bin_id"
          element={<ToastProvider><ResidentRequestPage /></ToastProvider>}
        />
        <Route path="/driver" element={<ToastProvider><TruckPickerPage /></ToastProvider>} />
        <Route path="/driver/:truck_id" element={<ToastProvider><DriverRouteScreen /></ToastProvider>} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route path="trucks" element={<TrucksPage />} />
          <Route path="sites" element={<SitesPage />} />
          <Route path="sites/:id" element={<SiteDetailPage />} />
          <Route path="map-analytics" element={<MapAnalyticsPage />} />
          <Route path="demo" element={<Navigate to="/admin/routes" replace />} />
          <Route path="demo/truck/:truck_id" element={<TruckDemoPage />} />
          <Route path="routes" element={<DemoPage />} />
          <Route path="routes/truck/:truck_id" element={<TruckDemoPage />} />
        </Route>
        <Route
          path="*"
          element={
            <main className="mx-auto max-w-md px-6 py-12">
              <h1 className="mb-4 text-xl font-semibold">Puslapis nerastas</h1>
              <Button asChild>
                <Link to="/">Grįžti į pradžią</Link>
              </Button>
            </main>
          }
        />
      </Routes>
    </BrowserRouter></ProjectDateProvider>
  )
}
