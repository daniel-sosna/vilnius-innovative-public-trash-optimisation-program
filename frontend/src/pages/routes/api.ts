export type Figures = {
  distance_km: number
  trips: number
  trucks_used: number
  overtime_min: number
  stops_served: number
}

export type Summary = {
  optimised: Figures
  baseline: Figures
  saved_km: number
  saved_percent: number
  unserved_stops: number
  stops_total: number
  iterations: number
  stopped_by_wall_limit: boolean
  solve_seconds: number
}

export type RouteStop = {
  site_id: number
  address: string | null
  latitude: number
  longitude: number
  load_m3: number
  bin_count: number
}

export type RouteTrip = {
  load_m3: number
  distance_km: number
  duration_min: number
  stops: RouteStop[]
}

export type RouteTruck = {
  truck_id: number
  name: string
  max_volume_m3: number
  landfill: { id: number; name: string; latitude: number; longitude: number }
  trips: RouteTrip[]
}

export type UnservedStop = {
  site_id: number
  address: string | null
  latitude: number
  longitude: number
  load_m3: number
  reason: string
}

export type RoutePlan = {
  date: string
  waste_carrier: string
  created_at: string
  parameters: Record<string, number>
  summary: Summary
  unserved: UnservedStop[]
  excluded_trucks: number
  trucks: RouteTruck[]
}

export type AvailablePlan = { date: string; waste_carrier: string }

export async function loadAvailablePlans(signal: AbortSignal): Promise<AvailablePlan[]> {
  const response = await fetch('/api/route-plans/available', { signal })
  if (!response.ok) throw new Error('Route plan list failed')
  return response.json()
}

export async function loadRoutePlan(plan: AvailablePlan, signal: AbortSignal): Promise<RoutePlan> {
  const query = new URLSearchParams({ date: plan.date, waste_carrier: plan.waste_carrier })
  const response = await fetch(`/api/route-plans?${query}`, { signal })
  if (!response.ok) throw new Error('Route plan read failed')
  return response.json()
}

// One colour per truck, spread around the colour wheel.
export function truckColor(index: number): string {
  return `hsl(${Math.round((index * 137.508) % 360)} 70% 42%)`
}
