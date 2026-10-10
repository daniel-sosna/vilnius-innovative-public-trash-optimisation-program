import type { Feature, FeatureCollection, Polygon } from 'geojson'
import type { ExpressionSpecification, FilterSpecification, MapLayerMouseEvent } from 'maplibre-gl'
import type { MapLayerDefinition } from '@/components/maps/map-layer'
import { loadPopulation } from './api'
import type { PopulationProperties } from './api'

export const populationBands = [
  { minimum: 0, label: '<11', color: '#f2e5ff' },
  { minimum: 11, label: '11–49', color: '#dac2ef' },
  { minimum: 50, label: '50–99', color: '#b88bd9' },
  { minimum: 100, label: '100–199', color: '#8d50b6' },
  { minimum: 200, label: '200+', color: '#602080' },
] as const

const knownDensity: FilterSpecification = ['any',
  ['==', ['get', 'suppressed'], true],
  ['==', ['typeof', ['get', 'density_per_ha']], 'number'],
]
const densityColor: ExpressionSpecification = ['case',
  ['==', ['get', 'suppressed'], true], populationBands[0].color,
  ['step', ['number', ['get', 'density_per_ha'], 0], populationBands[0].color,
    ...populationBands.slice(1).flatMap(band => [band.minimum, band.color])],
]

const densityFormat = new Intl.NumberFormat('lt-LT')
const areaFormat = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 2 })
const residentFormat = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 1 })

export function populationDetails(feature: Feature<Polygon, PopulationProperties>): HTMLElement {
  const { density_per_ha: density, suppressed, area_ha: area, residents } = feature.properties
  const content = document.createElement('div')
  content.className = 'analytics-details'
  const heading = document.createElement('h2')
  heading.className = 'mb-3 pr-4 text-sm font-semibold'
  heading.textContent = 'Gyventojų tankumas'
  content.append(heading)
  const details = document.createElement('dl')
  details.className = 'space-y-2 text-sm'
  const fields = [
    ['Tankumas (gyv./ha)', suppressed ? '<11' : density === null ? 'N/A' : densityFormat.format(density)],
    ['Plotas (ha)', areaFormat.format(area)],
    ['Apytikslis gyventojų skaičius', residents === null ? 'N/A' : residentFormat.format(residents)],
  ] as const
  for (const [label, value] of fields) {
    const group = document.createElement('div')
    const term = document.createElement('dt')
    term.className = 'font-medium text-muted-foreground'
    term.textContent = label
    const description = document.createElement('dd')
    description.textContent = value
    group.append(term, description)
    details.append(group)
  }
  content.append(details)
  if (suppressed) {
    const assumption = document.createElement('p')
    assumption.className = 'mt-3 text-xs text-muted-foreground'
    assumption.textContent = area > 0 && residents !== null
      ? `Skaičiavimui taikyta: ${areaFormat.format(residents / area)} gyv./ha.`
      : 'Gyventojų skaičius apskaičiuotas taikant prielaidą; kai plotas lygus nuliui, taikytas tankumas nenurodomas.'
    content.append(assumption)
  }
  const explanation = document.createElement('p')
  explanation.className = 'mt-3 text-xs text-muted-foreground'
  explanation.textContent = 'Pagal deklaruotą gyvenamąją vietą. Gyventojų skaičius yra įvertis.'
  content.append(explanation)
  return content
}

// Point renderers use circle markers and symbol counts. Include future registered
// point groups without depending on the order in which datasets finish loading.
const isAnalyticsPoint = (layer: { id: string; type: string }) =>
  layer.id.startsWith('analytics:') && (layer.type === 'circle' || layer.type === 'symbol')

export const populationLayer: MapLayerDefinition = {
  id: 'population',
  label: 'Gyventojų tankumas',
  meaning: 'Gyventojų tankumas pagal deklaruotą gyvenamąją vietą šaltinio poligonuose; gyventojų skaičius yra įvertis.',
  kind: 'polygon',
  legend: [
    ...populationBands.map(band => ({ label: `Gyventojų tankumas: ${band.label} gyv./ha`, color: band.color })),
    { label: 'Gyventojų tankumas: Duomenų nėra (skaidru)', color: 'transparent' },
  ],
  load: loadPopulation,
  attach(context, data) {
    const { map } = context
    const ids = {
      source: 'analytics:population:source',
      fill: 'analytics:population:fill',
      outline: 'analytics:population:outline',
    }
    const features = new Map((data as FeatureCollection<Polygon, PopulationProperties>).features.map(feature => [String(feature.id), feature]))
    let visible = true
    let disposed = false
    const layers = map.getStyle().layers
    // Preserve point priority and, where possible, basemap labels as well.
    const anchor = layers.find(layer => isAnalyticsPoint(layer) || layer.type === 'symbol')?.id
    map.addSource(ids.source, { type: 'geojson', data, cluster: false })
    map.addLayer({
      id: ids.fill, type: 'fill', source: ids.source, filter: knownDensity,
      paint: { 'fill-color': densityColor, 'fill-opacity': 0.45 },
    }, anchor)
    map.addLayer({
      id: ids.outline, type: 'line', source: ids.source, filter: knownDensity,
      paint: { 'line-color': '#602080', 'line-opacity': 0.2, 'line-width': 0.5 },
    }, anchor)

    const inspect = (event: MapLayerMouseEvent) => {
      if (!visible || disposed) return
      if (map.queryRenderedFeatures(event.point).some(feature => isAnalyticsPoint(feature.layer))) return
      const rendered = event.features?.[0]
      const feature = rendered && features.get(String(rendered.id))
      if (!feature || (feature.properties.density_per_ha === null && !feature.properties.suppressed)) return
      context.showDetails('population', [event.lngLat.lng, event.lngLat.lat], populationDetails(feature))
    }
    const enter = () => { if (visible && !disposed) map.getCanvas().style.cursor = 'pointer' }
    const leave = () => { map.getCanvas().style.cursor = '' }
    map.on('click', ids.fill, inspect)
    map.on('mouseenter', ids.fill, enter)
    map.on('mouseleave', ids.fill, leave)

    return {
      setVisible(next) {
        if (disposed || next === visible) return
        visible = next
        for (const id of [ids.fill, ids.outline]) map.setLayoutProperty(id, 'visibility', next ? 'visible' : 'none')
        if (!next) { context.closeDetails('population'); leave() }
      },
      dispose() {
        if (disposed) return
        disposed = true
        context.closeDetails('population')
        map.off('click', ids.fill, inspect)
        map.off('mouseenter', ids.fill, enter)
        map.off('mouseleave', ids.fill, leave)
        leave()
        for (const id of [ids.outline, ids.fill]) if (map.getLayer(id)) map.removeLayer(id)
        if (map.getSource(ids.source)) map.removeSource(ids.source)
      },
    }
  },
}
