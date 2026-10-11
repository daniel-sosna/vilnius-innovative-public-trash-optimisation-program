export type PredictedBin = { bin_id: number; site_id: number; fill_level: 3 | 4; latitude: number | null; longitude: number | null; address: string; waste_carrier: string | null }
export type Prediction = { project_date: string; forecast_date: string; evaluated_count: number; due_count: number; unmappable_count: number; bins: PredictedBin[] }
export type Coordinate = { latitude: number; longitude: number }
export type DemoStop = Coordinate & { site_id: number; bin_ids: number[] }
export type DemoRoute = { truck_id: number; truck_name: string; route_id: string; path: Coordinate[]; stops: DemoStop[]; color: string; stopCount: number; binCount: number }
type NavigationDTO = { forecast_date: string; source: 'osrm'; routes: Omit<DemoRoute, 'color' | 'stopCount' | 'binCount'>[] }
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
export type DrivingRoute = { source: 'osrm'; path: Coordinate[]; stops: Coordinate[]; legs: { path: Coordinate[]; distance_m: number }[] }
export async function getDrivingRoute(signal: AbortSignal): Promise<DrivingRoute> {
  const route = await post<DrivingRoute>('driving-route', undefined, signal, 60000, 'GET')
  const validPoint = (point: Coordinate) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude) && Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180
  if (route.source !== 'osrm' || !route.path.length || !route.legs.length || route.stops.length !== route.legs.length || !route.path.every(validPoint) || !route.stops.every(validPoint) || route.legs.some(leg => !leg.path.length || !leg.path.every(validPoint) || !Number.isFinite(leg.distance_m) || leg.distance_m < 0)) throw new Error('Nepavyko gauti tinkamo šiukšliavežės kelio maršruto.')
  return route
}
export async function getNavigation(forecast_date: string, bin_ids: number[], signal: AbortSignal): Promise<DemoRoute[]> {
  const dto = await post<NavigationDTO>('navigation', { forecast_date, bin_ids }, signal, 15 * 60 * 1000)
  if (dto.source !== 'osrm' || dto.forecast_date !== forecast_date || !dto.routes.length) throw new Error('Netinkamas maršrutų atsakymas.')
  if (dto.routes.some(route => !route.path.length || !route.stops.length || route.path.some(point => !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude) || Math.abs(point.latitude) > 90 || Math.abs(point.longitude) > 180))) throw new Error('Maršrutuose nėra tinkamų koordinačių arba sustojimų.')
  const assigned = dto.routes.flatMap(route => route.stops.flatMap(stop => stop.bin_ids))
  if (assigned.length !== bin_ids.length || new Set(assigned).size !== assigned.length || assigned.some(id => !bin_ids.includes(id))) throw new Error('Maršrutų konteinerių priskyrimas neatitinka prognozės.')
  return dto.routes.map((route, index) => ({ ...route, color: `hsl(${(index * 137.508) % 360} 65% 42%)`, stopCount: route.stops.length, binCount: route.stops.reduce((count, stop) => count + stop.bin_ids.length, 0) }))
}
