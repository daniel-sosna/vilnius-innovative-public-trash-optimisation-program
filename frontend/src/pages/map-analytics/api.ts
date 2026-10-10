import type { FeatureCollection, Point, Polygon } from 'geojson'

export type LandfillProperties = {
  name: string
  operator: string | null
  address: string | null
  coordinate_quality: string | null
}

export type BinProperties = {
  inventory_number: string | null
  waste_type: string
  capacity_m3: number | null
}

export async function loadBins(signal: AbortSignal): Promise<FeatureCollection<Point, BinProperties>> {
  const response = await fetch('/api/map-analytics/bins', { signal })
  if (!response.ok) throw new Error('Bin read failed')
  const data = await response.json() as FeatureCollection<Point, BinProperties>
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Invalid map response')
  return data
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

export type DistrictProperties = { district_name: string }

export async function loadDistricts(signal: AbortSignal): Promise<FeatureCollection<Polygon, DistrictProperties>> {
  const response = await fetch('/api/map-analytics/district-boundaries', { signal })
  if (!response.ok) throw new Error('District read failed')
  const data = await response.json() as FeatureCollection<Polygon, DistrictProperties>
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)
    || data.features.some(feature => feature.type !== 'Feature' || !Number.isSafeInteger(feature.id)
      || feature.geometry?.type !== 'Polygon' || !Array.isArray(feature.geometry.coordinates)
      || typeof feature.properties?.district_name !== 'string')) throw new Error('Invalid district map response')
  return data
}
