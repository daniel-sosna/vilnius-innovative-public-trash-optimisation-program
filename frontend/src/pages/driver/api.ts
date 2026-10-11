export type FillLevel = 0 | 1 | 2 | 3 | 4

export type PathPoint = { latitude: number; longitude: number }
export type RouteBin = { bin_id: number; inventory_number: string | null; waste_type: string }
export type RouteStop = {
  site_id: number
  address: string | null
  path_index: number
  bins: RouteBin[]
}
export type DriverRoute = { truck_id: number; plan_date: string; path: PathPoint[]; stops: RouteStop[] }

export type RouteFailure = 'truck_missing' | 'no_plan' | 'failed'

export class RouteError extends Error {
  constructor(public reason: RouteFailure) {
    super(reason)
  }
}

function isFinitePoint(point: PathPoint): boolean {
  return (
    Number.isFinite(point.latitude) && Number.isFinite(point.longitude) &&
    Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180
  )
}

// The navigation result is the one contract that may change; reject anything the screen cannot follow.
function validRoute(route: DriverRoute): boolean {
  if (route.stops.length === 0) return true
  const indexes = route.stops.map((stop) => stop.path_index)
  return (
    route.path.length >= 2 &&
    route.path.every(isFinitePoint) &&
    indexes.every((index, position) =>
      Number.isInteger(index) && index >= 0 && index < route.path.length &&
      (position === 0 || index >= indexes[position - 1]),
    ) &&
    route.stops.every((stop) => stop.bins.length > 0)
  )
}

export async function loadRoute(truckId: number, projectDate: string, signal?: AbortSignal): Promise<DriverRoute> {
  let response: Response
  try {
    response = await fetch('/api/driver/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ truck_id: truckId, project_date: projectDate }),
      signal,
    })
  } catch {
    throw new RouteError('failed')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.detail?.code
    throw new RouteError(
      response.status === 404 && code === 'truck_not_found' ? 'truck_missing'
        : response.status === 404 && code === 'no_plan' ? 'no_plan'
        : 'failed',
    )
  }
  const route = (await response.json().catch(() => null)) as DriverRoute | null
  if (!route || !Array.isArray(route.path) || !Array.isArray(route.stops) || !validRoute(route))
    throw new RouteError('failed')
  return route
}

export async function saveService(items: { bin_id: number; fill_level: FillLevel }[]): Promise<void> {
  const response = await fetch('/api/driver/service', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ services: items }),
  })
  if (!response.ok) throw new Error('Service save failed')
}

export type TruckRoute = { truck_id: number; truck_name: string; stop_count: number; bin_count: number }

// Trucks that have a calculated route for the day after the project date.
export async function loadTruckRoutes(projectDate: string, signal: AbortSignal): Promise<TruckRoute[]> {
  const response = await fetch(`/api/driver/trucks?project_date=${encodeURIComponent(projectDate)}`, { signal })
  if (!response.ok) throw new Error('Truck route list failed')
  return (await response.json()) as TruckRoute[]
}

// 'missing' only for a definite 404; other failures let the route request report the problem.
export async function truckExists(truckId: number, signal: AbortSignal): Promise<'ok' | 'missing'> {
  try {
    const response = await fetch(`/api/trucks/${truckId}`, { signal })
    return response.status === 404 ? 'missing' : 'ok'
  } catch {
    return 'ok'
  }
}
