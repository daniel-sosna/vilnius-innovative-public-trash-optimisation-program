import type { FeatureCollection, Point } from 'geojson'
import { GeoJSONSource } from 'maplibre-gl'
import type { MapLayerDefinition } from '@/components/maps/map-layer'
import { createPointLayer } from '@/components/maps/point-layer'
import type { PredictedBin } from './api'
import { emptyCollection } from './geometry'

export const selectedLayer = createPointLayer({
  id: 'demo-selected', label: 'Aptarnauti skirti konteineriai', meaning: 'Tikros prognozės lygiai 3 ir 4', legend: [],
  load: async () => emptyCollection as FeatureCollection<Point>,
  appearance: { color: '#dc2626', clusterColor: '#b91c1c', countColor: '#ffffff' },
  clustering: false,
  details(feature) {
    const element = document.createElement('p')
    element.textContent = `Konteineris ${feature.id} · lygis ${feature.properties?.fill_level} · ${feature.properties?.address ?? ''}`
    return element
  },
})

export const routeSourceId = 'demo-routes-source'
export const routesLayer: MapLayerDefinition = {
  id: 'demo-routes', label: 'Maršrutai', meaning: 'Maršrutų trajektorijos', kind: 'line', legend: [], load: async () => emptyCollection,
  attach({ map }, data) {
    const source = routeSourceId, line = 'demo-routes-line', point = 'demo-routes-point'
    map.addSource(source, { type: 'geojson', data })
    const before = map.getStyle().layers?.find(layer => layer.type === 'symbol')?.id
    map.addLayer({ id: line, type: 'line', source, filter: ['==', ['geometry-type'], 'LineString'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': ['get', 'color'], 'line-width': 4, 'line-opacity': 0.85 } }, before)
    map.addLayer({ id: point, type: 'circle', source, filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-color': ['get', 'color'], 'circle-radius': 9, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } }, before)
    return { styleLayerIds: [line, point], setData(value) { (map.getSource(source) as GeoJSONSource).setData(value) }, setVisible(value) { for (const id of [line, point]) map.setLayoutProperty(id, 'visibility', value ? 'visible' : 'none') }, dispose() { for (const id of [line, point]) if (map.getLayer(id)) map.removeLayer(id); if (map.getSource(source)) map.removeSource(source) } }
  },
}
export const demoLayers = [selectedLayer] as const
export const demoSelection = { 'demo-selected': true }
export function selectedFeatures(bins: PredictedBin[], limit = bins.length): FeatureCollection {
  return { type: 'FeatureCollection', features: bins.filter(bin => bin.fill_level > 2 && bin.latitude !== null && bin.longitude !== null).slice(0, limit).map(bin => ({ type: 'Feature', id: bin.bin_id, properties: { fill_level: bin.fill_level, address: bin.address, site_id: bin.site_id }, geometry: { type: 'Point', coordinates: [bin.longitude!, bin.latitude!] } })) }
}
