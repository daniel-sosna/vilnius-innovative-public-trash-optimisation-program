import type { Feature, FeatureCollection, GeoJsonProperties, Point } from 'geojson'
import { GeoJSONSource } from 'maplibre-gl'
import type { DataDrivenPropertyValueSpecification, MapLayerMouseEvent } from 'maplibre-gl'
import type { LayerLegendEntry, MapLayerDefinition } from './map-layer'

export const POINT_CLUSTER_DEFAULTS = { clusterRadius: 50, clusterMaxZoom: 14 }

type PointDefinition<P extends GeoJsonProperties> = {
  id: string
  label: string
  meaning: string
  legend: readonly LayerLegendEntry[]
  load(signal: AbortSignal): Promise<FeatureCollection<Point, P>>
  appearance: {
    color: DataDrivenPropertyValueSpecification<string>
    clusterColor?: string
    countColor?: string
    countFont?: string[]
  }
  details(feature: Feature<Point, P>): HTMLElement
}

export function pointLayerIds(id: string) {
  const prefix = `analytics:${id}`
  return {
    source: `${prefix}:source`,
    clusters: `${prefix}:clusters`,
    counts: `${prefix}:counts`,
    points: `${prefix}:points`,
  }
}

export function createPointLayer<P extends GeoJsonProperties>(definition: PointDefinition<P>): MapLayerDefinition {
  return {
    id: definition.id,
    label: definition.label,
    meaning: definition.meaning,
    kind: 'point',
    legend: definition.legend,
    load: definition.load,
    attach(context, data) {
      const { map } = context
      const ids = pointLayerIds(definition.id)
      const styleLayers = [ids.clusters, ids.counts, ids.points]
      let visible = true
      let disposed = false
      let visibilityRevision = 0
      // Resolve details from the original data, preserving nulls and feature IDs.
      const features = new Map((data as FeatureCollection<Point, P>).features.map(feature => [String(feature.id), feature]))

      map.addSource(ids.source, {
        type: 'geojson', data, cluster: true, ...POINT_CLUSTER_DEFAULTS,
      })
      map.addLayer({
        id: ids.clusters, type: 'circle', source: ids.source,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': definition.appearance.clusterColor ?? definition.appearance.color,
          'circle-radius': ['step', ['get', 'point_count'], 20, 10, 25, 100, 30],
          'circle-stroke-width': 2, 'circle-stroke-color': '#ffffff',
        },
      })
      map.addLayer({
        id: ids.counts, type: 'symbol', source: ids.source,
        filter: ['has', 'point_count'],
        layout: {
          'text-field': ['get', 'point_count_abbreviated'],
          'text-font': definition.appearance.countFont ?? ['Noto Sans Regular'],
          'text-size': 13, 'text-allow-overlap': true,
        },
        paint: { 'text-color': definition.appearance.countColor ?? '#ffffff' },
      })
      map.addLayer({
        id: ids.points, type: 'circle', source: ids.source,
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': definition.appearance.color, 'circle-radius': 8,
          'circle-stroke-width': 2, 'circle-stroke-color': '#ffffff',
        },
      })

      // Overlapping point datasets receive separate delegated events. Activate
      // only the topmost point/cluster so one click belongs to one dataset.
      const isTopmost = (event: MapLayerMouseEvent, id: string) => {
        const feature = map.queryRenderedFeatures(event.point).find(item =>
          item.layer.id.startsWith('analytics:')
          && (item.layer.id.endsWith(':points') || item.layer.id.endsWith(':clusters')))
        return feature?.layer.id === id
      }
      const expand = async (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!visible || disposed || feature?.geometry.type !== 'Point') return
        if (!isTopmost(event, ids.clusters)) return
        context.closeDetails(definition.id)
        const source = map.getSource(ids.source)
        if (!(source instanceof GeoJSONSource)) return
        const coordinates = feature.geometry.coordinates.slice(0, 2) as [number, number]
        const revision = visibilityRevision
        try {
          const zoom = await source.getClusterExpansionZoom(Number(feature.properties.cluster_id))
          if (!disposed && visible && revision === visibilityRevision) map.easeTo({ center: coordinates, zoom })
        } catch {
          // Disposal can invalidate a pending worker response; no camera change.
        }
      }
      const inspect = (event: MapLayerMouseEvent) => {
        if (!visible || disposed) return
        if (!isTopmost(event, ids.points)) return
        const rendered = event.features?.[0]
        const feature = rendered && features.get(String(rendered.id))
        if (!feature) return
        context.showDetails(definition.id, feature.geometry.coordinates.slice(0, 2) as [number, number], definition.details(feature))
      }
      const enter = () => { if (visible) map.getCanvas().style.cursor = 'pointer' }
      const leave = () => { map.getCanvas().style.cursor = '' }
      map.on('click', ids.clusters, expand)
      map.on('click', ids.points, inspect)
      for (const id of [ids.clusters, ids.points]) {
        map.on('mouseenter', id, enter)
        map.on('mouseleave', id, leave)
      }

      return {
        setVisible(next) {
          if (disposed || next === visible) return
          visibilityRevision += 1
          visible = next
          for (const id of styleLayers) map.setLayoutProperty(id, 'visibility', next ? 'visible' : 'none')
          if (!next) { context.closeDetails(definition.id); leave() }
        },
        dispose() {
          disposed = true
          context.closeDetails(definition.id)
          map.off('click', ids.clusters, expand)
          map.off('click', ids.points, inspect)
          for (const id of [ids.clusters, ids.points]) {
            map.off('mouseenter', id, enter)
            map.off('mouseleave', id, leave)
          }
          leave()
          for (const id of [...styleLayers].reverse()) if (map.getLayer(id)) map.removeLayer(id)
          if (map.getSource(ids.source)) map.removeSource(ids.source)
        },
      }
    },
  }
}
