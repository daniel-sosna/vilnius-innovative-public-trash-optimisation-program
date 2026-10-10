import type { MapLayerDefinition } from '@/components/maps/map-layer'
import { loadServiceZones } from './api'

export const serviceZoneStyle = {
  fillColor: '#0f766e',
  fillOpacity: 0.15,
  outlineColor: '#115e59',
  outlineWidth: 1.5,
  textColor: '#134e4a',
  haloColor: '#ffffff',
  haloWidth: 1.25,
} as const

export const serviceZonesLayer: MapLayerDefinition = {
  id: 'service-zones',
  label: 'Aptarnavimo zonos',
  meaning: 'Atliekų surinkimo aptarnavimo zonos pagal importuotą teritorijų duomenų rinkinį.',
  kind: 'polygon',
  legend: [],
  load: loadServiceZones,
  attach({ map }, data) {
    const source = 'analytics:service-zones:source'
    const layers = [
      'analytics:service-zones:fill',
      'analytics:service-zones:outline',
      'analytics:service-zones:labels',
    ]
    let visible = true
    let disposed = false
    map.addSource(source, { type: 'geojson', data, cluster: false })
    map.addLayer({
      id: layers[0], type: 'fill', source,
      paint: { 'fill-color': serviceZoneStyle.fillColor, 'fill-opacity': serviceZoneStyle.fillOpacity },
    })
    map.addLayer({
      id: layers[1], type: 'line', source,
      paint: { 'line-color': serviceZoneStyle.outlineColor, 'line-width': serviceZoneStyle.outlineWidth },
    })
    map.addLayer({
      id: layers[2], type: 'symbol', source, minzoom: 9,
      layout: {
        'symbol-placement': 'point',
        'text-field': ['get', 'zone_name'],
        'text-font': ['Noto Sans Regular'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 9, 11, 12, 14, 16, 16],
        'text-padding': 4,
        'text-variable-anchor': ['center', 'top', 'bottom', 'left', 'right'],
        'text-radial-offset': 1.2,
        'text-allow-overlap': false,
      },
      paint: {
        'text-color': serviceZoneStyle.textColor,
        'text-halo-color': serviceZoneStyle.haloColor,
        'text-halo-width': serviceZoneStyle.haloWidth,
      },
    })
    return {
      setVisible(next) {
        if (disposed || next === visible) return
        visible = next
        for (const id of layers) map.setLayoutProperty(id, 'visibility', next ? 'visible' : 'none')
      },
      dispose() {
        if (disposed) return
        disposed = true
        for (const id of [...layers].reverse()) if (map.getLayer(id)) map.removeLayer(id)
        if (map.getSource(source)) map.removeSource(source)
      },
    }
  },
}
