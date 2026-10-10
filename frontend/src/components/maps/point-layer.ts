import type { Feature, FeatureCollection, GeoJsonProperties, Point } from 'geojson'
import { GeoJSONSource } from 'maplibre-gl'
import type { DataDrivenPropertyValueSpecification, MapLayerMouseEvent, MapMouseEvent } from 'maplibre-gl'
import type { LayerLegendEntry, MapLayerDefinition } from './map-layer'
import { CLUSTER_VIEW_PADDING, POINT_RADII, ScreenClusters } from './screen-clusters'
import type { ClusterView } from './screen-clusters'

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
  clustering?: {
    radius: number
    throughMaxZoom: boolean
    avoidOverlap?: boolean
  }
  overlapGroup?: {
    minZoom: number
    details(features: Feature<Point, P>[], isCurrent: () => boolean): HTMLElement
  }
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
      let interactionSequence = 0
      let sourceRevision = 0
      let sourceReady = true
      let opacityReady = true
      let groupOpen = false
      let appliedData = data
      // Resolve details from the original data, preserving nulls and feature IDs.
      let features = new Map((data as FeatureCollection<Point, P>).features.map(feature => [String(feature.id), feature]))
      const clustering = definition.clustering
      const overlap = definition.overlapGroup
      // MapLibre's canonical tile limit is 25; reserve the final source zoom
      // for individual points. The default map (22) therefore uses 22/23.
      const clusterMaxZoom = Math.min(24, Math.floor(map.getMaxZoom()))
      const screenClusters = clustering?.avoidOverlap
        ? new ScreenClusters(data as FeatureCollection<Point, P>, clusterMaxZoom, overlap?.minZoom ?? 15, clustering.radius)
        : undefined
      const view = (): ClusterView => {
        const canvas = map.getCanvas()
        const width = canvas.clientWidth, height = canvas.clientHeight
        const padding = CLUSTER_VIEW_PADDING
        const corners = [[-padding, -padding], [width + padding, -padding], [width + padding, height + padding], [-padding, height + padding]]
          .map(point => map.unproject(point as [number, number]))
        const centerLongitude = map.getCenter().lng
        return {
          zoom: map.getZoom(), width, height,
          bounds: [Math.min(...corners.map(point => point.lng)), Math.min(...corners.map(point => point.lat)),
            Math.max(...corners.map(point => point.lng)), Math.max(...corners.map(point => point.lat))],
          project: coordinates => map.project([
            coordinates[0] + 360 * Math.round((centerLongitude - coordinates[0]) / 360), coordinates[1],
          ]),
        }
      }
      const initialLayout = screenClusters?.layout(view())
      let layoutSignature = initialLayout?.signature
      let layoutPending = false
      let visibilityPending = false
      let completedRevision = 0
      let updateFrame: number | undefined

      map.addSource(ids.source, {
        type: 'geojson', data: initialLayout?.data ?? data, cluster: !screenClusters, ...POINT_CLUSTER_DEFAULTS,
        ...(clustering && {
          clusterRadius: clustering.radius,
          ...(clustering.throughMaxZoom && {
            maxzoom: clusterMaxZoom + 1, clusterMaxZoom, clusterMinPoints: 2,
          }),
        }),
      })
      map.addLayer({
        id: ids.clusters, type: 'circle', source: ids.source,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': definition.appearance.clusterColor ?? definition.appearance.color,
          ...(screenClusters && {
            'circle-pitch-scale': 'viewport' as const, 'circle-pitch-alignment': 'viewport' as const,
            'circle-opacity-transition': { duration: 0, delay: 0 },
            'circle-stroke-opacity-transition': { duration: 0, delay: 0 },
          }),
          'circle-radius': overlap
            ? ['step', ['zoom'], ['step', ['get', 'point_count'], POINT_RADII.small, 10, POINT_RADII.medium, 100, POINT_RADII.large], overlap.minZoom, POINT_RADII.high]
            : ['step', ['get', 'point_count'], POINT_RADII.small, 10, POINT_RADII.medium, 100, POINT_RADII.large],
          'circle-stroke-width': POINT_RADII.stroke, 'circle-stroke-color': '#ffffff',
        },
      })
      map.addLayer({
        id: ids.counts, type: 'symbol', source: ids.source,
        filter: ['has', 'point_count'],
        layout: {
          'text-field': ['get', overlap ? 'point_count' : 'point_count_abbreviated'],
          'text-font': definition.appearance.countFont ?? ['Noto Sans Regular'],
          'text-size': 13, 'text-allow-overlap': true,
        },
        paint: {
          'text-color': definition.appearance.countColor ?? '#ffffff',
          ...(screenClusters && { 'text-opacity-transition': { duration: 0, delay: 0 } }),
        },
      })
      map.addLayer({
        id: ids.points, type: 'circle', source: ids.source,
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': definition.appearance.color, 'circle-radius': POINT_RADII.point,
          ...(screenClusters && {
            'circle-pitch-scale': 'viewport' as const, 'circle-pitch-alignment': 'viewport' as const,
            'circle-opacity-transition': { duration: 0, delay: 0 },
            'circle-stroke-opacity-transition': { duration: 0, delay: 0 },
          }),
          'circle-stroke-width': POINT_RADII.stroke, 'circle-stroke-color': '#ffffff',
        },
      })

      // Overlapping point datasets receive separate delegated events. Activate
      // only the topmost point/cluster so one click belongs to one dataset.
      const topmostAt = (point: MapMouseEvent['point']) => map.queryRenderedFeatures(point).find(item =>
          item.layer.id.startsWith('analytics:')
          && (item.layer.id.endsWith(':points') || item.layer.id.endsWith(':clusters'))
          && map.getPaintProperty(item.layer.id, 'circle-opacity') !== 0)
      const isTopmost = (event: MapLayerMouseEvent, id: string) => topmostAt(event.point)?.layer.id === id
      const interactive = () => !disposed && visible && sourceReady && map.isSourceLoaded(ids.source)
      const invalidate = (close: boolean) => {
        interactionSequence += 1
        if (close) context.closeDetails(definition.id)
      }
      const synchronizeOpacity = () => {
        if (!screenClusters || disposed || opacityReady === sourceReady) return
        opacityReady = sourceReady
        for (const id of [ids.points, ids.clusters]) {
          map.setPaintProperty(id, 'circle-opacity', sourceReady ? 1 : 0)
          map.setPaintProperty(id, 'circle-stroke-opacity', sourceReady ? 1 : 0)
        }
        map.setPaintProperty(ids.counts, 'text-opacity', sourceReady ? 1 : 0)
      }
      const checkReady = () => {
        if (disposed || sourceReady || layoutPending || visibilityPending || completedRevision !== sourceRevision || !map.isSourceLoaded(ids.source)) return
        sourceReady = true
        synchronizeOpacity()
      }
      const onRender = () => { visibilityPending = false; checkReady() }
      const publishData = (next: FeatureCollection, hideUntilReady = false) => {
        sourceReady = false
        const revision = ++sourceRevision
        invalidate(true)
        // Camera changes retain MapLibre's renderable tiles while replacements
        // load. Only a filter change hides the previous, now-excluded members.
        if (hideUntilReady) synchronizeOpacity()
        const source = map.getSource(ids.source)
        if (!(source instanceof GeoJSONSource)) return
        void source.setData(next).then(() => {
          if (disposed || revision !== sourceRevision) return
          completedRevision = revision
          checkReady()
        }).catch(() => { /* Map recovery owns source errors. */ })
      }
      const refreshLayout = (force = false) => {
        if (!screenClusters || disposed) return
        const layout = screenClusters.layout(view())
        layoutPending = false
        if (!force && layout.signature === layoutSignature) { checkReady(); return }
        layoutSignature = layout.signature
        publishData(layout.data, force)
      }
      const scheduleLayout = () => {
        if (!screenClusters || !visible || disposed) return
        // Gate stale clicks, but keep the existing markers and counts visible
        // while the worker installs the current camera's collision-free layout.
        layoutPending = true
        sourceReady = false
        if (updateFrame !== undefined) return
        updateFrame = requestAnimationFrame(() => {
          updateFrame = undefined
          if (!visible || disposed) { layoutPending = false; return }
          refreshLayout()
        })
      }
      const onNavigate = () => invalidate(groupOpen)
      // A click belonging to another dataset also supersedes pending work here.
      const onMapClick = (event: MapMouseEvent) => {
        const topmost = topmostAt(event.point)
        if (topmost?.layer.id !== ids.points && topmost?.layer.id !== ids.clusters) invalidate(groupOpen)
      }
      const openGroup = (readLeaves: () => Promise<Feature[]>, count: number, coordinates: [number, number]) => {
        if (!overlap) return
        const revision = sourceRevision
        const content = document.createElement('div')
        groupOpen = true
        context.showDetails(definition.id, coordinates, content, () => {
          groupOpen = false
          interactionSequence += 1
        })
        const read = async () => {
          const sequence = ++interactionSequence
          const current = () => interactive() && sourceRevision === revision && interactionSequence === sequence && groupOpen
          const loading = document.createElement('p')
          loading.className = 'pr-4 text-sm'
          loading.setAttribute('role', 'status')
          loading.textContent = 'Kraunamas konteinerių sąrašas…'
          content.replaceChildren(loading)
          try {
            const leaves = await readLeaves()
            if (!current()) return
            const members = new Map<string, Feature<Point, P>>()
            for (const leaf of leaves) {
              const original = features.get(String(leaf.id))
              if (!original) throw new Error('Missing group member')
              members.set(String(original.id), original)
            }
            if (members.size !== count) throw new Error('Incomplete group')
            const ordered = [...members.values()].sort((a, b) =>
              String(a.id).localeCompare(String(b.id), 'en', { numeric: true }))
            content.replaceChildren(overlap.details(ordered, current))
            content.querySelector<HTMLButtonElement>('button')?.focus()
          } catch {
            if (!current()) return
            const error = document.createElement('p')
            error.className = 'mb-3 pr-4 text-sm text-destructive'
            error.setAttribute('role', 'alert')
            error.textContent = 'Nepavyko įkelti konteinerių sąrašo.'
            const retry = document.createElement('button')
            retry.type = 'button'
            retry.className = 'analytics-group-button'
            retry.textContent = 'Bandyti dar kartą'
            retry.addEventListener('click', () => { if (current()) void read() })
            content.replaceChildren(error, retry)
            retry.focus()
          }
        }
        void read()
      }
      const expand = async (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!interactive() || feature?.geometry.type !== 'Point') return
        if (!isTopmost(event, ids.clusters)) return
        invalidate(true)
        const source = map.getSource(ids.source)
        if (!(source instanceof GeoJSONSource)) return
        const coordinates = feature.geometry.coordinates.slice(0, 2) as [number, number]
        const clusterKey = String(feature.properties.cluster_id)
        const clusterId = Number(clusterKey)
        const count = Number(feature.properties.point_count)
        if (overlap && map.getZoom() >= overlap.minZoom) {
          openGroup(() => screenClusters
            ? Promise.resolve().then(() => screenClusters.getLeaves(clusterKey))
            : source.getClusterLeaves(clusterId, count, 0), count, coordinates)
          return
        }
        const revision = sourceRevision
        const sequence = interactionSequence
        try {
          const zoom = screenClusters
            ? await Promise.resolve().then(() => screenClusters.getExpansionZoom(clusterKey, map.getZoom()))
            : await source.getClusterExpansionZoom(clusterId)
          if (interactive() && revision === sourceRevision && sequence === interactionSequence) {
            map.easeTo({ center: coordinates, zoom: Math.min(zoom, map.getMaxZoom()) })
          }
        } catch {
          // Disposal can invalidate a pending worker response; no camera change.
        }
      }
      const inspect = (event: MapLayerMouseEvent) => {
        if (!interactive()) return
        if (!isTopmost(event, ids.points)) return
        const rendered = event.features?.[0]
        const feature = rendered && features.get(String(rendered.id))
        if (!feature) return
        invalidate(true)
        context.showDetails(definition.id, feature.geometry.coordinates.slice(0, 2) as [number, number], definition.details(feature))
      }
      const enter = () => { if (interactive()) map.getCanvas().style.cursor = 'pointer' }
      const leave = () => { map.getCanvas().style.cursor = '' }
      map.on('movestart', onNavigate)
      map.on('move', scheduleLayout)
      map.on('resize', scheduleLayout)
      map.on('sourcedata', checkReady)
      map.on('render', onRender)
      map.on('click', onMapClick)
      map.on('click', ids.clusters, expand)
      map.on('click', ids.points, inspect)
      for (const id of [ids.clusters, ids.points]) {
        map.on('mouseenter', id, enter)
        map.on('mouseleave', id, leave)
      }

      return {
        setData(next) {
          if (disposed || next === appliedData) return
          appliedData = next
          invalidate(true)
          features = new Map((next as FeatureCollection<Point, P>).features.map(feature => [String(feature.id), feature]))
          if (screenClusters) {
            screenClusters.setData(next as FeatureCollection<Point, P>)
            refreshLayout(true)
          } else publishData(next, true)
        },
        setVisible(next) {
          if (disposed || next === visible) return
          invalidate(true)
          visible = next
          if (next && screenClusters) {
            visibilityPending = true
            sourceReady = false
          }
          for (const id of styleLayers) map.setLayoutProperty(id, 'visibility', next ? 'visible' : 'none')
          if (next && screenClusters) { refreshLayout(); checkReady() }
          if (!next) { context.closeDetails(definition.id); leave() }
        },
        dispose() {
          disposed = true
          if (updateFrame !== undefined) cancelAnimationFrame(updateFrame)
          invalidate(true)
          map.off('movestart', onNavigate)
          map.off('move', scheduleLayout)
          map.off('resize', scheduleLayout)
          map.off('sourcedata', checkReady)
          map.off('render', onRender)
          map.off('click', onMapClick)
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
