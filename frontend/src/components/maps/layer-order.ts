import type { Map } from 'maplibre-gl'

// Only the point helper's actual marker/count roles suppress polygon clicks.
export function isAnalyticsPoint(layer: { id: string; type: string }) {
  return /^analytics:[^:]+:(points|clusters|counts)$/.test(layer.id)
    && (layer.type === 'circle' || layer.type === 'symbol')
}

const areaOrder = [
  'analytics:service-zones:fill',
  'analytics:population:fill',
  'analytics:population:outline',
  'analytics:service-zones:outline',
  'analytics:service-zones:labels',
] as const

export function orderAreaLayers(map: Map) {
  const anchor = map.getStyle().layers.find(layer => isAnalyticsPoint(layer)
    || (layer.type === 'symbol' && !layer.id.startsWith('analytics:')))?.id
  for (const id of areaOrder) {
    if (map.getLayer(id)) map.moveLayer(id, anchor)
  }
}
