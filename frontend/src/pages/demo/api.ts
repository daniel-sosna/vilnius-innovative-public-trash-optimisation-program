export type PredictedBin = { bin_id: number; site_id: number; fill_level: 3 | 4; latitude: number | null; longitude: number | null; address: string; waste_carrier: string | null }
export type Prediction = { project_date: string; forecast_date: string; evaluated_count: number; due_count: number; unmappable_count: number; bins: PredictedBin[] }
export type Coordinate = { latitude: number; longitude: number }
export type DemoStop = Coordinate & { site_id: number; bin_ids: number[] }
export type DemoRoute = { truck_id: number; truck_name: string; route_id: string; path: Coordinate[]; stops: DemoStop[]; color: string; stopCount: number; binCount: number }
export type UnservedStop = DemoStop & { reason: string }
type NavigationDTO = { run_id: string; forecast_date: string; source: 'pyvrp-osrm'; routes: Omit<DemoRoute, 'color' | 'stopCount' | 'binCount'>[]; unserved: UnservedStop[] }
export const routeColors = ['#2563eb', '#b45309', '#7c3aed'] as const

async function post<T>(path: string, body: unknown, signal: AbortSignal, deadline: number, method: 'GET' | 'POST' = 'POST'): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const abort = () => controller.abort()
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) abort()
  const timer = window.setTimeout(() => { timedOut = true; controller.abort() }, deadline)
  try {
    const response = await fetch(`/api/demo/${path}`, { method, headers: { 'Content-Type': 'application/json' }, body: method === 'POST' ? JSON.stringify(body) : undefined, signal: controller.signal })
    const result = await response.json().catch(() => null)
    if (!response.ok) throw new Error(result?.detail?.message ?? (response.status === 504 ? 'Serverio tarpininkas nutraukė ilgą užklausą. Patikrinkite laukimo laiko konfigūraciją.' : 'Demonstracijos užklausa nepavyko. Patikrinkite duomenis ir bandykite dar kartą.'))
    if (!result) throw new Error('Serveris grąžino netinkamą atsakymą. Bandykite dar kartą.')
    return result as T
  } catch (error) {
    if (timedOut) throw new Error('Baigėsi laukimo laikas. Serveris gali tęsti prognozavimą; palaukite ir bandykite dar kartą.')
    if (controller.signal.aborted) throw error
    if (error instanceof TypeError) throw new Error('Nepavyko susisiekti su serveriu. Patikrinkite ryšį ir bandykite dar kartą.')
    throw error instanceof Error ? error : new Error('Nepavyko susisiekti su serveriu.')
  } finally {
    window.clearTimeout(timer)
    signal.removeEventListener('abort', abort)
  }
}

export const getPrediction = (project_date: string, signal: AbortSignal) => post<Prediction>('predictions', { project_date }, signal, 15 * 60 * 1000)
export type DrivingRoute = { source: 'osrm'; path: Coordinate[]; stops: Coordinate[]; legs: { path: Coordinate[]; distance_m: number; stop_index: number | null }[] }
export async function getDrivingRoute(runId: string, truckId: number, signal: AbortSignal): Promise<DrivingRoute> {
  const route = await post<DrivingRoute>(`driving-route?run_id=${encodeURIComponent(runId)}&truck_id=${truckId}`, undefined, signal, 60000, 'GET')
  const validPoint = (point: Coordinate) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude) && Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180
  if (route.source !== 'osrm' || !route.path.length || !route.legs.length || !route.path.every(validPoint) || !route.stops.every(validPoint) || route.legs.some(leg => !leg.path.length || !leg.path.every(validPoint) || !Number.isFinite(leg.distance_m) || leg.distance_m < 0 || (leg.stop_index !== null && (!Number.isInteger(leg.stop_index) || leg.stop_index < 0 || leg.stop_index >= route.stops.length)))) throw new Error('Nepavyko gauti tinkamo šiukšliavežės kelio maršruto.')
  return route
}
export async function getNavigation(forecast_date: string, bins: PredictedBin[], signal: AbortSignal): Promise<{ runId: string; routes: DemoRoute[]; unserved: UnservedStop[] }> {
  const bin_ids = bins.map(bin => bin.bin_id)
  const fill_levels = Object.fromEntries(bins.map(bin => [bin.bin_id, bin.fill_level]))
  const dto = await post<NavigationDTO>('navigation', { forecast_date, bin_ids, fill_levels }, signal, 15 * 60 * 1000)
  if (!/^[a-f0-9]{32}$/.test(dto.run_id) || dto.source !== 'pyvrp-osrm' || dto.forecast_date !== forecast_date || !Array.isArray(dto.routes) || !Array.isArray(dto.unserved)) throw new Error('Netinkamas maršrutų atsakymas.')
  if (dto.routes.some(route => !route.path.length || !route.stops.length || route.path.some(point => !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude) || Math.abs(point.latitude) > 90 || Math.abs(point.longitude) > 180))) throw new Error('Maršrutuose nėra tinkamų koordinačių arba sustojimų.')
  const accounted = [...dto.routes.flatMap(route => route.stops.flatMap(stop => stop.bin_ids)), ...dto.unserved.flatMap(stop => stop.bin_ids)]
  const input = new Set(bin_ids)
  if (accounted.length !== bin_ids.length || new Set(accounted).size !== accounted.length || accounted.some(id => !input.has(id))) throw new Error('Maršrutų konteinerių priskyrimas neatitinka prognozės.')
  return { runId: dto.run_id, routes: dto.routes.map((route, index) => ({ ...route, color: `hsl(${(index * 137.508) % 360} 65% 42%)`, stopCount: route.stops.length, binCount: route.stops.reduce((count, stop) => count + stop.bin_ids.length, 0) })), unserved: dto.unserved }
}
