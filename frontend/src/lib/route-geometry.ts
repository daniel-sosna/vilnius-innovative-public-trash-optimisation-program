// Pure helpers for moving along an ordered road path of [longitude, latitude] points.
export type LonLat = [number, number]
export type RouteGeometry = { points: LonLat[]; cumulative: number[]; total: number }

const METERS_PER_DEGREE = 111_320

function segmentMeters(a: LonLat, b: LonLat): number {
  const midLatitude = ((a[1] + b[1]) / 2) * (Math.PI / 180)
  const dx = (b[0] - a[0]) * Math.cos(midLatitude) * METERS_PER_DEGREE
  const dy = (b[1] - a[1]) * METERS_PER_DEGREE
  return Math.hypot(dx, dy)
}

export function buildGeometry(points: LonLat[]): RouteGeometry {
  const cumulative = [0]
  for (let index = 1; index < points.length; index++)
    cumulative.push(cumulative[index - 1] + segmentMeters(points[index - 1], points[index]))
  return { points, cumulative, total: cumulative[cumulative.length - 1] ?? 0 }
}

// Index of the last vertex at or before `distance`.
function indexBefore(geometry: RouteGeometry, distance: number): number {
  const { cumulative } = geometry
  let low = 0
  let high = cumulative.length - 1
  while (low < high) {
    const middle = Math.ceil((low + high) / 2)
    if (cumulative[middle] <= distance) low = middle
    else high = middle - 1
  }
  return low
}

export function pointAt(geometry: RouteGeometry, distance: number): LonLat {
  const { points, cumulative } = geometry
  const clamped = Math.min(Math.max(distance, 0), geometry.total)
  const index = indexBefore(geometry, clamped)
  if (index >= points.length - 1) return points[points.length - 1]
  const length = cumulative[index + 1] - cumulative[index]
  const fraction = length > 0 ? (clamped - cumulative[index]) / length : 0
  const a = points[index]
  const b = points[index + 1]
  return [a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction]
}

// Compass bearing in degrees [0, 360) from the point at `distance` to the point `lookahead` metres on.
export function bearingAt(geometry: RouteGeometry, distance: number, lookahead: number): number {
  const end = Math.min(geometry.total, distance + lookahead)
  const start = Math.max(0, end - lookahead)
  const a = pointAt(geometry, start)
  const b = pointAt(geometry, end)
  const midLatitude = ((a[1] + b[1]) / 2) * (Math.PI / 180)
  const dx = (b[0] - a[0]) * Math.cos(midLatitude)
  const dy = b[1] - a[1]
  return (Math.atan2(dx, dy) * (180 / Math.PI) + 360) % 360
}

// Done part (start to `distance`) and remaining part (`distance` to the end) of the path.
export function splitAt(geometry: RouteGeometry, distance: number): { done: LonLat[]; remaining: LonLat[] } {
  const { points } = geometry
  const clamped = Math.min(Math.max(distance, 0), geometry.total)
  const index = indexBefore(geometry, clamped)
  const here = pointAt(geometry, clamped)
  return {
    done: [...points.slice(0, index + 1), here],
    remaining: [here, ...points.slice(index + 1)],
  }
}

// Move `current` toward `target` along the shortest turn, by `factor` of the gap but at most `maxStep` degrees.
export function approachAngle(current: number, target: number, factor: number, maxStep: number): number {
  const gap = ((target - current + 540) % 360) - 180
  const step = Math.max(-maxStep, Math.min(maxStep, gap * factor))
  return (current + step + 360) % 360
}
