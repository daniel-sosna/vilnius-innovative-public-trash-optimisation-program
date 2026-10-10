import { createPolygonLayer } from '@/components/maps/polygon-layer'
import type { ServiceZoneProperties } from './api'
import { loadServiceZones } from './api'

export const serviceZoneStyle = {
  fillColor: '#0f766e',
  fillOpacity: 0.15,
  outlineColor: '#115e59',
  outlineWidth: 3.5,
  textColor: '#134e4a',
  haloColor: '#ffffff',
  haloWidth: 1.25,
} as const

export const serviceZonesLayer = createPolygonLayer<ServiceZoneProperties>({
  id: 'service-zones',
  label: 'Aptarnavimo zonos',
  meaning: 'Atliekų surinkimo aptarnavimo zonos pagal importuotą teritorijų duomenų rinkinį.',
  // Keep the light tint below population and bold boundaries above it.
  order: 15,
  outlineOrder: 30,
  legend: [],
  load: loadServiceZones,
  fill: { 'fill-color': serviceZoneStyle.fillColor, 'fill-opacity': serviceZoneStyle.fillOpacity },
  outline: { 'line-color': serviceZoneStyle.outlineColor, 'line-width': serviceZoneStyle.outlineWidth },
  labels: {
    minzoom: 9,
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
  },
})
