import { ScreenClusters, markerRadius, CLUSTER_VIEW_PADDING } from '../src/components/maps/screen-clusters.ts'

// Read-only geometry verification, independent of DOM/WebGL browser acceptance.
function mercator(coordinates) {
  const [longitude, latitude] = coordinates
  return [(longitude + 180) / 360, (1 - Math.log(Math.tan(Math.PI / 4 + latitude * Math.PI / 360)) / Math.PI) / 2]
}

function view(center, zoom, bearing = 0) {
  const width = 1280, height = 730, scale = 512 * 2 ** zoom
  const [cx, cy] = mercator(center)
  const angle = bearing * Math.PI / 180, cos = Math.cos(angle), sin = Math.sin(angle)
  const project = coordinates => {
    const [x, y] = mercator(coordinates)
    return { x: width / 2 + ((x - cx) * cos - (y - cy) * sin) * scale,
      y: height / 2 + ((x - cx) * sin + (y - cy) * cos) * scale }
  }
  const padding = CLUSTER_VIEW_PADDING
  const corners = [[-padding, -padding], [width + padding, -padding], [width + padding, height + padding], [-padding, height + padding]]
    .map(([px, py]) => {
      const dx = (px - width / 2) / scale, dy = (py - height / 2) / scale
      return [(cx + dx * cos + dy * sin) * 360 - 180,
        Math.atan(Math.sinh(Math.PI * (1 - 2 * (cy - dx * sin + dy * cos)))) * 180 / Math.PI]
    })
  return { zoom, width, height, project,
    bounds: [Math.min(...corners.map(p => p[0])), Math.min(...corners.map(p => p[1])),
      Math.max(...corners.map(p => p[0])), Math.max(...corners.map(p => p[1]))] }
}

function inspect(engine, camera, originalIds) {
  const start = performance.now()
  const layout = engine.layout(camera)
  const layoutMilliseconds = performance.now() - start
  const members = new Set()
  let count = 0, minimumGap = Infinity
  const markers = layout.data.features.map(feature => {
    const size = feature.properties.point_count ?? 1
    const leaves = size === 1 ? [feature] : engine.getLeaves(String(feature.properties.cluster_id))
    if (leaves.length !== size) throw new Error('Group count differs from its leaves')
    for (const leaf of leaves) {
      if (!originalIds.has(leaf.id) || members.has(leaf.id)) throw new Error('Missing, duplicate or unknown member identity')
      members.add(leaf.id)
    }
    count += size
    return { point: camera.project(feature.geometry.coordinates), radius: markerRadius(size, camera.zoom) }
  })
  for (let i = 0; i < markers.length; i += 1) {
    for (let j = 0; j < i; j += 1) {
      const a = markers[i], b = markers[j]
      const gap = Math.hypot(a.point.x - b.point.x, a.point.y - b.point.y) - a.radius - b.radius
      if (gap < 1.999999) throw new Error(`Intersecting circles: gap ${gap}`)
      minimumGap = Math.min(minimumGap, gap)
    }
  }
  if (count !== members.size) throw new Error('Count does not match unique represented bins')
  if (engine.layout(camera).signature !== layout.signature) throw new Error('Unchanged view produces unstable layout')
  return { zoom: camera.zoom, markers: markers.length, representedBins: count,
    minimumGap: Number.isFinite(minimumGap) ? Number(minimumGap.toFixed(2)) : null,
    layoutMilliseconds: Number(layoutMilliseconds.toFixed(1)),
    verificationMilliseconds: Number((performance.now() - start).toFixed(1)) }
}

async function main() {
  const base = (process.argv[2] ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
  const response = await fetch(`${base}/map-analytics/bins`)
  if (!response.ok) throw new Error(`Bin API returned HTTP ${response.status}`)
  const data = await response.json()
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Invalid bin response')
  const ids = new Set(data.features.map(feature => feature.id))
  if (ids.size !== data.features.length) throw new Error('Duplicate API feature IDs')
  const engine = new ScreenClusters(data, 22, 15, 20)
  const locations = new Map()
  for (const feature of data.features) {
    const key = feature.geometry.coordinates.join(',')
    const group = locations.get(key) ?? []
    group.push(feature)
    locations.set(key, group)
  }
  const largest = [...locations.values()].sort((a, b) => b.length - a.length)[0]
  for (const zoom of [10, 10.5, 12, 12.5, 13, 14.5, 15, 15.5, 18, 22]) {
    const center = zoom >= 18 && largest ? largest[0].geometry.coordinates : [25.2797, 54.6872]
    console.log(JSON.stringify(inspect(engine, view(center, zoom), ids)))
  }
  console.log('Rotated view:', JSON.stringify(inspect(engine, view([25.2797, 54.6872], 12.5, 45), ids)))
  if (largest) {
    const coordinates = largest[0].geometry.coordinates
    const pair = [1, 2].map(id => ({ type: 'Feature', id, geometry: { type: 'Point', coordinates: [...coordinates] },
      properties: { inventory_number: null, waste_type: 'Glass waste', capacity_m3: id } }))
    const fixture = { type: 'FeatureCollection', features: pair }
    const sample = new ScreenClusters(fixture, 22, 15, 20)
    const pairIds = new Set([1, 2])
    const identical = inspect(sample, view(coordinates, 22), pairIds)
    if (identical.markers !== 1 || identical.representedBins !== 2) throw new Error('Identical pair must stay grouped')
    pair[1] = { ...pair[1], geometry: { type: 'Point', coordinates: [coordinates[0] + 0.00008, coordinates[1]] } }
    sample.setData({ type: 'FeatureCollection', features: pair })
    for (const zoom of [15, 17, 17.5, 18, 22]) {
      const result = inspect(sample, view(coordinates, zoom), pairIds)
      if (result.representedBins !== 2 || (zoom >= 18 && result.markers !== 2)) throw new Error('Near pair membership/separation failed')
      console.log('Near pair:', JSON.stringify(result))
    }
  }
  console.log(`PASS: ${data.features.length} source bins; disjoint circles, exact counts, stable layouts and unique group members. Browser acceptance is separate.`)
}

main().catch(error => { console.error(error.message); process.exitCode = 1 })
