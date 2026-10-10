import type { FeatureCollection, Point, Polygon } from 'geojson'

export type LandfillProperties = {
  name: string
  operator: string | null
  address: string | null
  coordinate_quality: string | null
}

export async function loadLandfills(signal: AbortSignal): Promise<FeatureCollection<Point, LandfillProperties>> {
  const response = await fetch('/api/map-analytics/landfills', { signal })
  if (!response.ok) throw new Error('Landfill read failed')
  const data = await response.json() as FeatureCollection<Point, LandfillProperties>
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Invalid map response')
  return data
}

export type PopulationProperties = {
  density_per_ha: number | null
  suppressed: boolean
  area_ha: number
  residents: number | null
}

export async function loadPopulation(signal: AbortSignal): Promise<FeatureCollection<Polygon, PopulationProperties>> {
  const response = await fetch('/api/map-analytics/population-cells', { signal })
  if (!response.ok) throw new Error('Population read failed')
  const data = await response.json() as FeatureCollection<Polygon, PopulationProperties>
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Invalid map response')
  return data
}
