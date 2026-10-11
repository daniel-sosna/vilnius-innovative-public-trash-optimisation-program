import type { FeatureCollection, Position } from 'geojson'
import type { DemoRoute } from './api'

export const emptyCollection: FeatureCollection = { type: 'FeatureCollection', features: [] }
export function prefix(path: Position[], progress: number): Position[] {
  if (!path.length) return []
  if (path.length === 1 || progress >= 1) return path
  const distances = path.slice(1).map((point, index) => {
    const previous = path[index], latitude = (point[1] + previous[1]) * Math.PI / 360
    return Math.hypot((point[0] - previous[0]) * Math.cos(latitude), point[1] - previous[1])
  })
  const total = distances.reduce((sum, distance) => sum + distance, 0)
  if (!total) return [path[0]]
  let remaining = total * Math.max(0, progress)
  const result = [path[0]]
  for (let index = 0; index < distances.length; index++) {
    if (remaining >= distances[index]) { result.push(path[index + 1]); remaining -= distances[index]; continue }
    const fraction = remaining / distances[index], a = path[index], b = path[index + 1]
    result.push([a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction])
    break
  }
  return result
}
export function routeFeatures(routes: DemoRoute[], progress: number): FeatureCollection {
  return { type: 'FeatureCollection', features: routes.map(route => {
    const coordinates = prefix(route.path.map(point => [point.longitude, point.latitude]), progress)
    return { type: 'Feature', id: route.route_id, properties: { color: route.color }, geometry: coordinates.length < 2 ? { type: 'Point', coordinates: coordinates[0] } : { type: 'LineString', coordinates } }
  }) }
}
