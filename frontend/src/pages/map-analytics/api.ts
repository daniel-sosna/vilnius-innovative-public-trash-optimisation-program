import type { FeatureCollection, Point } from 'geojson'

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
