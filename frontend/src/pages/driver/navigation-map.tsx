import { useEffect, useImperativeHandle, useRef, useState, type Ref } from 'react'
import { GeoJSONSource, Map as LibreMap, Marker, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Feature, FeatureCollection } from 'geojson'
import { approachAngle, bearingAt, pointAt, splitAt, type RouteGeometry } from '@/lib/route-geometry'

setWorkerUrl(workerUrl)

export type StopState = 'done' | 'next' | 'future'
export type NavigationMapHandle = { update: (distance: number) => void }

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }
const ZOOM = 16
const PITCH = 45
const LOOKAHEAD_M = 60
const HEADING_FACTOR = 0.08
const HEADING_MAX_STEP = 3
const LINE_INTERVAL_MS = 100
// Share of the map height kept empty above the truck, which puts it in the lower-middle.
const TOP_PADDING_SHARE = 0.45

function line(points: [number, number][]): FeatureCollection {
  return points.length < 2
    ? EMPTY
    : { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: points } }] }
}

function truckElement(): HTMLElement {
  const element = document.createElement('div')
  element.setAttribute('role', 'img')
  element.setAttribute('aria-label', 'Šiukšliavežė')
  element.style.cssText = 'width:44px;height:44px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))'
  // Top-down truck, cab at the top, so rotating by the bearing makes it face the driving direction.
  element.innerHTML =
    '<svg viewBox="0 0 44 44" width="44" height="44" aria-hidden="true">' +
    '<rect x="11" y="3" width="22" height="38" rx="5" fill="#ffffff"/>' +
    '<rect x="13" y="5" width="18" height="12" rx="3" fill="#1d4ed8"/>' +
    '<rect x="15" y="8" width="14" height="4" rx="1" fill="#bfdbfe"/>' +
    '<rect x="13" y="20" width="18" height="19" rx="2" fill="#15803d"/></svg>'
  return element
}

type Props = {
  ref?: Ref<NavigationMapHandle>
  geometry: RouteGeometry
  stops: { distance: number; state: StopState }[]
  following: boolean
  onUserPan: () => void
}

export function NavigationMap({ ref, geometry, stops, following, onUserPan }: Props) {
  const style = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<LibreMap | null>(null)
  const truck = useRef<Marker | null>(null)
  const distance = useRef(0)
  const heading = useRef<number | null>(null)
  const followingRef = useRef(following)
  const lineTimer = useRef<number | null>(null)
  const lastLine = useRef(0)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const panned = useRef(onUserPan)

  useEffect(() => {
    panned.current = onUserPan
  }, [onUserPan])

  function drawLines() {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    lastLine.current = performance.now()
    const { done, remaining } = splitAt(geometry, distance.current)
    const done_ = map.getSource('route-done')
    const rest = map.getSource('route-rest')
    if (done_ instanceof GeoJSONSource) void done_.setData(line(done)).catch(() => {})
    if (rest instanceof GeoJSONSource) void rest.setData(line(remaining)).catch(() => {})
  }

  function placeTruck() {
    const map = mapRef.current
    const marker = truck.current
    if (!map || !marker) return
    const position = pointAt(geometry, distance.current)
    const target = bearingAt(geometry, distance.current, LOOKAHEAD_M)
    heading.current =
      heading.current === null ? target : approachAngle(heading.current, target, HEADING_FACTOR, HEADING_MAX_STEP)
    marker.setLngLat(position).setRotation(heading.current)
    if (followingRef.current)
      map.jumpTo({
        center: position,
        bearing: heading.current,
        zoom: ZOOM,
        pitch: PITCH,
        padding: { top: map.getContainer().clientHeight * TOP_PADDING_SHARE, bottom: 0, left: 0, right: 0 },
      })
  }

  useImperativeHandle(ref, () => ({
    update(next: number) {
      distance.current = next
      placeTruck()
      const wait = LINE_INTERVAL_MS - (performance.now() - lastLine.current)
      if (wait <= 0) drawLines()
      else if (lineTimer.current === null)
        lineTimer.current = window.setTimeout(() => {
          lineTimer.current = null
          drawLines()
        }, wait)
    },
  }))

  useEffect(() => {
    if (!container.current || !style) return
    let map: LibreMap
    try {
      map = new LibreMap({
        container: container.current,
        style,
        center: pointAt(geometry, 0),
        zoom: ZOOM,
        pitch: PITCH,
        attributionControl: { compact: true },
      })
    } catch {
      return
    }
    mapRef.current = map
    map.on('error', () => setFailed(true))
    map.on('dragstart', (event) => {
      if (event.originalEvent) panned.current()
    })
    map.on('load', () => {
      for (const id of ['route-done', 'route-rest', 'stops']) map.addSource(id, { type: 'geojson', data: EMPTY })
      const layout = { 'line-cap': 'round', 'line-join': 'round' } as const
      map.addLayer({ id: 'route-casing', type: 'line', source: 'route-rest', layout, paint: { 'line-color': '#ffffff', 'line-width': 14 } })
      map.addLayer({ id: 'route-done', type: 'line', source: 'route-done', layout, paint: { 'line-color': '#94a3b8', 'line-width': 8 } })
      map.addLayer({ id: 'route-rest', type: 'line', source: 'route-rest', layout, paint: { 'line-color': '#1d4ed8', 'line-width': 9 } })
      map.addLayer({
        id: 'stops', type: 'circle', source: 'stops',
        paint: {
          'circle-radius': ['match', ['get', 'state'], 'next', 15, 10],
          'circle-color': ['match', ['get', 'state'], 'done', '#16a34a', 'next', '#f97316', '#ffffff'],
          'circle-stroke-color': ['match', ['get', 'state'], 'future', '#334155', '#ffffff'],
          'circle-stroke-width': 3,
        },
      })
      truck.current = new Marker({ element: truckElement(), rotationAlignment: 'map', pitchAlignment: 'viewport' })
        .setLngLat(pointAt(geometry, distance.current))
        .addTo(map)
      setReady(true)
    })
    return () => {
      if (lineTimer.current !== null) window.clearTimeout(lineTimer.current)
      lineTimer.current = null
      truck.current?.remove()
      truck.current = null
      map.remove()
      mapRef.current = null
      setReady(false)
    }
    // The map is created once per route; the geometry only changes with a new route.
  }, [style, geometry])

  useEffect(() => {
    if (!ready) return
    drawLines()
    placeTruck()
    // Draw once when the style is ready; later frames come from `update`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  useEffect(() => {
    followingRef.current = following
    if (following && ready) placeTruck()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [following, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('stops')
    const features: Feature[] = stops.map((stop, index) => ({
      type: 'Feature',
      id: index,
      properties: { state: stop.state },
      geometry: { type: 'Point', coordinates: pointAt(geometry, stop.distance) },
    }))
    if (source instanceof GeoJSONSource)
      void source.setData({ type: 'FeatureCollection', features }).catch(() => {})
  }, [stops, geometry, ready])

  if (!style)
    return (
      <div role="alert" className="flex h-full items-center justify-center bg-muted p-5 text-center text-base text-destructive">
        Žemėlapio konfigūracija nepasiekiama. Kreipkitės į administratorių.
      </div>
    )
  return (
    <div className="relative h-full w-full">
      {/* Inline: the MapLibre stylesheet sets position: relative on the map element. */}
      <div ref={container} style={{ position: 'absolute', inset: 0 }} aria-label="Navigacijos žemėlapis" />
      {failed && !ready && (
        <p role="alert" className="absolute left-3 top-3 rounded bg-card p-3 text-sm text-destructive shadow">
          Nepavyko įkelti žemėlapio.
        </p>
      )}
    </div>
  )
}
