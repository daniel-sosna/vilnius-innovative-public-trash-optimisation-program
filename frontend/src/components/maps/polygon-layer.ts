import type { Feature, FeatureCollection, GeoJsonProperties, Polygon } from 'geojson'
import type { FillLayerSpecification, FilterSpecification, LineLayerSpecification, Map as LibreMap, MapLayerMouseEvent, SymbolLayerSpecification } from 'maplibre-gl'
import type { LayerLegendEntry, LayerRenderer, MapLayerDefinition } from './map-layer'
import { isPointStyleLayer } from './point-layer'

type PolygonDefinition<P extends GeoJsonProperties> = {
  id: string
  label: string
  meaning: string
  order: number
  legend: readonly LayerLegendEntry[]
  load(signal: AbortSignal): Promise<FeatureCollection<Polygon, P>>
  fill: FillLayerSpecification['paint']
  outline: LineLayerSpecification['paint']
  filter?: FilterSpecification
  labels?: Pick<SymbolLayerSpecification, 'minzoom' | 'layout' | 'paint'>
  interaction?: {
    details(feature: Feature<Polygon, P>): HTMLElement
    canInspect?(feature: Feature<Polygon, P>): boolean
  }
}

export function reconcilePolygonOrder(map: LibreMap, definitions: readonly MapLayerDefinition[], renderers: ReadonlyMap<string, LayerRenderer>) {
  const groups = definitions.filter(layer => layer.polygonOrder !== undefined && renderers.has(layer.id))
    .sort((a, b) => a.polygonOrder! - b.polygonOrder!)
  const anchor = map.getStyle().layers.find(layer => isPointStyleLayer(layer)
    || (layer.type === 'symbol' && !layer.id.startsWith('analytics:')))?.id
  for (const group of groups) {
    for (const id of renderers.get(group.id)?.styleLayerIds ?? []) {
      if (map.getLayer(id)) map.moveLayer(id, anchor)
    }
  }
}

export function createPolygonLayer<P extends GeoJsonProperties>(definition: PolygonDefinition<P>): MapLayerDefinition {
  return {
    id: definition.id, label: definition.label, meaning: definition.meaning,
    kind: 'polygon', polygonOrder: definition.order, legend: definition.legend, load: definition.load,
    attach(context, data) {
      const { map } = context
      const prefix = `analytics:${definition.id}`
      const source = `${prefix}:source`, fill = `${prefix}:fill`, outline = `${prefix}:outline`, labels = `${prefix}:labels`
      const styleLayerIds = [fill, outline, ...(definition.labels ? [labels] : [])]
      const features = new Map((data as FeatureCollection<Polygon, P>).features.map(feature => [String(feature.id), feature]))
      let visible = true, disposed = false, hovering = false
      const filter = definition.filter ? { filter: definition.filter } : {}
      map.addSource(source, { type: 'geojson', data, cluster: false })
      map.addLayer({ id: fill, type: 'fill', source, ...filter, paint: definition.fill })
      map.addLayer({ id: outline, type: 'line', source, ...filter, paint: definition.outline })
      if (definition.labels) map.addLayer({ id: labels, type: 'symbol', source, ...filter, ...definition.labels })

      const inspect = (event: MapLayerMouseEvent) => {
        if (!visible || disposed || !definition.interaction) return
        if (map.queryRenderedFeatures(event.point).some(feature => isPointStyleLayer(feature.layer))) return
        const rendered = event.features?.[0]
        const feature = rendered && features.get(String(rendered.id))
        if (!feature || definition.interaction.canInspect?.(feature) === false) return
        context.showDetails(definition.id, [event.lngLat.lng, event.lngLat.lat], definition.interaction.details(feature))
      }
      const enter = () => {
        if (visible && !disposed) { hovering = true; map.getCanvas().style.cursor = 'pointer' }
      }
      const leave = () => {
        if (hovering) { map.getCanvas().style.cursor = ''; hovering = false }
      }
      if (definition.interaction) {
        map.on('click', fill, inspect)
        map.on('mouseenter', fill, enter)
        map.on('mouseleave', fill, leave)
      }
      return {
        styleLayerIds,
        setVisible(next) {
          if (disposed || next === visible) return
          visible = next
          for (const id of styleLayerIds) map.setLayoutProperty(id, 'visibility', next ? 'visible' : 'none')
          if (!next && definition.interaction) { context.closeDetails(definition.id); leave() }
        },
        dispose() {
          if (disposed) return
          disposed = true
          if (definition.interaction) {
            context.closeDetails(definition.id)
            map.off('click', fill, inspect)
            map.off('mouseenter', fill, enter)
            map.off('mouseleave', fill, leave)
            leave()
          }
          for (const id of [...styleLayerIds].reverse()) if (map.getLayer(id)) map.removeLayer(id)
          if (map.getSource(source)) map.removeSource(source)
        },
      }
    },
  }
}
