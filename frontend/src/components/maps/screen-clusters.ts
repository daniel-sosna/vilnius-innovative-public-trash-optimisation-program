import type { Feature, FeatureCollection, GeoJsonProperties, Point } from 'geojson'
import { Supercluster } from '@maplibre/geojson-vt'

export const POINT_RADII = { point: 8, small: 20, medium: 25, large: 30, high: 16, stroke: 2 }
const GAP = 2
export const CLUSTER_VIEW_PADDING = 128

export type ClusterView = {
  zoom: number
  bounds: [number, number, number, number]
  width: number
  height: number
  project(coordinates: [number, number]): { x: number; y: number }
}

type Seed = {
  key: string
  feature: Feature<Point>
  count: number
  nativeId?: number
}

type Group = {
  seeds: Seed[]
  count: number
  coordinates: [number, number]
}

export function markerRadius(count: number, zoom: number, highZoom = 15): number {
  const radius = count === 1 ? POINT_RADII.point
    : zoom >= highZoom ? POINT_RADII.high
      : count >= 100 ? POINT_RADII.large : count >= 10 ? POINT_RADII.medium : POINT_RADII.small
  return radius + POINT_RADII.stroke
}

function centroid(seeds: Seed[]): [number, number] {
  let x = 0, y = 0, count = 0
  for (const seed of seeds) {
    const [longitude, latitude] = seed.feature.geometry.coordinates
    const radians = Math.max(-85.051129, Math.min(85.051129, latitude)) * Math.PI / 180
    x += (longitude + 180) / 360 * seed.count
    y += (1 - Math.log(Math.tan(Math.PI / 4 + radians / 2)) / Math.PI) / 2 * seed.count
    count += seed.count
  }
  return [x / count * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * y / count))) * 180 / Math.PI]
}

// Native clustering supplies seed membership. This pass checks actual drawn
// circles and repeats after centroids/radii change, rather than hiding collisions.
function mergeCollisions(groups: Group[], view: ClusterView, highZoom: number): Group[] {
  const cellSize = 2 * markerRadius(100, view.zoom, highZoom) + GAP
  while (groups.length > 1) {
    const parents = groups.map((_, index) => index)
    const root = (index: number): number => {
      while (parents[index] !== index) {
        parents[index] = parents[parents[index]]
        index = parents[index]
      }
      return index
    }
    const projected = groups.map(group => view.project(group.coordinates))
    const grid = new Map<string, number[]>()
    let merged = false
    for (let index = 0; index < groups.length; index += 1) {
      const point = projected[index]
      const cellX = Math.floor(point.x / cellSize), cellY = Math.floor(point.y / cellSize)
      for (let dx = -1; dx <= 1; dx += 1) {
        for (let dy = -1; dy <= 1; dy += 1) {
          for (const other of grid.get(`${cellX + dx}:${cellY + dy}`) ?? []) {
            const distance = Math.hypot(point.x - projected[other].x, point.y - projected[other].y)
            const required = markerRadius(groups[index].count, view.zoom, highZoom)
              + markerRadius(groups[other].count, view.zoom, highZoom) + GAP
            if (distance >= required) continue
            const a = root(index), b = root(other)
            if (a !== b) { parents[Math.max(a, b)] = Math.min(a, b); merged = true }
          }
        }
      }
      const key = `${cellX}:${cellY}`
      const occupants = grid.get(key) ?? []
      occupants.push(index)
      grid.set(key, occupants)
    }
    if (!merged) return groups
    const components = new Map<number, Seed[]>()
    groups.forEach((group, index) => {
      const key = root(index)
      const seeds = components.get(key) ?? []
      seeds.push(...group.seeds)
      components.set(key, seeds)
    })
    groups = [...components.values()].map(seeds => ({
      seeds, count: seeds.reduce((sum, seed) => sum + seed.count, 0), coordinates: centroid(seeds),
    }))
  }
  return groups
}

export class ScreenClusters<P extends GeoJsonProperties> {
  private data: FeatureCollection<Point, P>
  private index: Supercluster | undefined
  private radius: number | undefined
  private generation = 0
  private groups = new Map<string, Group>()
  private maxZoom: number
  private highZoom: number
  private highRadius: number

  constructor(data: FeatureCollection<Point, P>, maxZoom: number, highZoom: number, highRadius: number) {
    this.data = data
    this.maxZoom = maxZoom
    this.highZoom = highZoom
    this.highRadius = highRadius
  }

  setData(data: FeatureCollection<Point, P>) {
    this.data = data
    this.index = undefined
  }

  layout(view: ClusterView): { data: FeatureCollection<Point>; signature: string } {
    const radius = view.zoom < this.highZoom ? 80 : this.highRadius
    if (!this.index || radius !== this.radius) {
      this.index = new Supercluster({ radius, extent: 512, maxZoom: this.maxZoom, minPoints: 2, generateId: false })
      this.index.load(this.data.features)
      this.radius = radius
      this.generation += 1
    }
    const seeds = this.index.getClusters(view.bounds, Math.floor(view.zoom)).flatMap(feature => {
      const coordinates = feature.geometry.coordinates.slice(0, 2) as [number, number]
      const point = view.project(coordinates)
      if (!Number.isFinite(point.x) || !Number.isFinite(point.y)
        || point.x < -CLUSTER_VIEW_PADDING || point.x > view.width + CLUSTER_VIEW_PADDING
        || point.y < -CLUSTER_VIEW_PADDING || point.y > view.height + CLUSTER_VIEW_PADDING) return []
      const clustered = feature.properties?.cluster === true
      const nativeId = clustered ? Number(feature.properties?.cluster_id) : undefined
      return [{
        key: clustered ? `c${nativeId}` : `b${feature.id}`, feature,
        count: clustered ? Number(feature.properties?.point_count) : 1, nativeId,
      }]
    }).sort((a, b) => a.key.localeCompare(b.key))
    const groups = mergeCollisions(seeds.map(seed => ({
      seeds: [seed], count: seed.count, coordinates: seed.feature.geometry.coordinates.slice(0, 2) as [number, number],
    })), view, this.highZoom)
    this.groups = new Map(groups.map(group => [group.seeds.map(seed => seed.key).sort().join(','), group]))
    return {
      signature: `${this.generation}:${[...this.groups.keys()].sort().join('|')}`,
      data: {
        type: 'FeatureCollection',
        features: [...this.groups.entries()].map(([key, group]) => group.count === 1
          ? group.seeds[0].feature
          : {
            type: 'Feature', id: `cluster:${key}`,
            geometry: { type: 'Point', coordinates: group.coordinates },
            properties: { cluster: true, cluster_id: key, point_count: group.count },
          }),
      },
    }
  }

  getLeaves(key: string): Feature<Point>[] {
    const group = this.groups.get(key)
    if (!group || !this.index) throw new Error('Group no longer exists')
    return group.seeds.flatMap(seed => seed.nativeId === undefined
      ? [seed.feature] : this.index!.getLeaves(seed.nativeId, seed.count, 0))
  }

  getExpansionZoom(key: string, currentZoom: number): number {
    const group = this.groups.get(key)
    if (!group || !this.index) throw new Error('Group no longer exists')
    const expansions = group.seeds.flatMap(seed => seed.nativeId === undefined
      ? [] : [this.index!.getClusterExpansionZoom(seed.nativeId)])
    return Math.max(currentZoom + 1, expansions.length ? Math.min(...expansions) : currentZoom + 1)
  }
}
