import { useEffect, useRef, useState } from 'react'
import { GeoJSONSource, Map as LibreMap, Marker, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Feature, FeatureCollection } from 'geojson'
import { truckColor, type RoutePlan } from './api'

setWorkerUrl(workerUrl)

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

function setSource(map: LibreMap, id: string, data: FeatureCollection) {
  const source = map.getSource(id)
  if (source instanceof GeoJSONSource) source.setData(data)
}

function buildData(plan: RoutePlan, selected: number | null) {
  const lines: Feature[] = []
  const stops: Feature[] = []
  const landfills = new Map<number, Feature>()
  plan.trucks.forEach((truck, index) => {
    const color = truckColor(index)
    const dim = selected !== null && selected !== index
    const home: [number, number] = [truck.landfill.longitude, truck.landfill.latitude]
    landfills.set(truck.landfill.id, {
      type: 'Feature',
      properties: { name: truck.landfill.name },
      geometry: { type: 'Point', coordinates: home },
    })
    for (const trip of truck.trips) {
      const path = trip.stops.map((s): [number, number] => [s.longitude, s.latitude])
      lines.push({
        type: 'Feature',
        properties: { color, dim },
        geometry: { type: 'LineString', coordinates: [home, ...path, home] },
      })
      for (const stop of trip.stops)
        stops.push({
          type: 'Feature',
          properties: { color, dim },
          geometry: { type: 'Point', coordinates: [stop.longitude, stop.latitude] },
        })
    }
  })
  const unserved: Feature[] = plan.unserved.map((stop) => ({
    type: 'Feature',
    properties: {},
    geometry: { type: 'Point', coordinates: [stop.longitude, stop.latitude] },
  }))
  const collect = (features: Feature[]): FeatureCollection => ({ type: 'FeatureCollection', features })
  return { lines: collect(lines), stops: collect(stops), landfills: collect([...landfills.values()]), unserved: collect(unserved) }
}

export function RouteMap({ plan, selected }: { plan: RoutePlan; selected: number | null }) {
  const style = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<LibreMap | null>(null)
  const markers = useRef<Marker[]>([])
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const fitted = useRef<RoutePlan | null>(null)

  useEffect(() => {
    if (!container.current || !style) return
    let map: LibreMap
    try {
      map = new LibreMap({
        container: container.current,
        style,
        center: [25.2797, 54.6872],
        zoom: 10,
        attributionControl: { compact: true },
      })
    } catch {
      return
    }
    mapRef.current = map
    map.addControl(new NavigationControl({ showCompass: false }))
    map.on('error', () => setFailed(true))
    map.on('load', () => {
      for (const id of ['routes', 'stops', 'landfills', 'unserved'])
        map.addSource(id, { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'routes', type: 'line', source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': ['case', ['get', 'dim'], 1.5, 3],
          'line-opacity': ['case', ['get', 'dim'], 0.25, 0.9],
        },
      })
      map.addLayer({
        id: 'stops', type: 'circle', source: 'stops',
        paint: {
          'circle-radius': ['case', ['get', 'dim'], 2.5, 4.5],
          'circle-color': ['get', 'color'],
          'circle-opacity': ['case', ['get', 'dim'], 0.3, 1],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': ['case', ['get', 'dim'], 0, 1],
        },
      })
      map.addLayer({
        id: 'unserved', type: 'circle', source: 'unserved',
        paint: { 'circle-radius': 6, 'circle-color': '#dc2626', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 },
      })
      map.addLayer({
        id: 'landfills', type: 'circle', source: 'landfills',
        paint: { 'circle-radius': 8, 'circle-color': '#111827', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 },
      })
      setReady(true)
    })
    return () => {
      markers.current.forEach((marker) => marker.remove())
      markers.current = []
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [style])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const data = buildData(plan, selected)
    setSource(map, 'routes', data.lines)
    setSource(map, 'stops', data.stops)
    setSource(map, 'landfills', data.landfills)
    setSource(map, 'unserved', data.unserved)

    markers.current.forEach((marker) => marker.remove())
    markers.current = []
    if (selected !== null) {
      const color = truckColor(selected)
      plan.trucks[selected].trips.forEach((trip, tripIndex) =>
        trip.stops.forEach((stop, stopIndex) => {
          const element = document.createElement('div')
          element.textContent = `${tripIndex + 1}.${stopIndex + 1}`
          element.title = `${stop.address ?? 'Be adreso'} – ${stop.load_m3.toFixed(2)} m³`
          element.style.cssText = `background:${color};color:#fff;font:600 10px/1 system-ui;padding:2px 4px;border-radius:9px;border:1px solid #fff;pointer-events:auto`
          markers.current.push(new Marker({ element }).setLngLat([stop.longitude, stop.latitude]).addTo(map))
        }),
      )
    }

    if (fitted.current !== plan) {
      fitted.current = plan
      const points = [
        ...plan.trucks.flatMap((t) => [[t.landfill.longitude, t.landfill.latitude] as [number, number]]),
        ...plan.trucks.flatMap((t) => t.trips.flatMap((trip) => trip.stops.map((s): [number, number] => [s.longitude, s.latitude]))),
      ]
      if (points.length) {
        const lons = points.map((p) => p[0])
        const lats = points.map((p) => p[1])
        map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 48, duration: 0 })
      }
    }
  }, [plan, selected, ready])

  if (!style)
    return (
      <div role="alert" className="flex min-h-80 flex-1 items-center justify-center bg-muted/40 p-5 text-sm text-destructive">
        Žemėlapio konfigūracija nepasiekiama. Kreipkitės į administratorių.
      </div>
    )
  return (
    <div className="relative min-h-80 flex-1">
      {/* Inline: the MapLibre stylesheet sets position: relative on the map element. */}
      <div ref={container} style={{ position: 'absolute', inset: 0 }} aria-label="Maršrutų žemėlapis" />
      {failed && !ready && (
        <p role="alert" className="absolute left-3 top-3 rounded bg-card p-3 text-sm text-destructive shadow">
          Nepavyko įkelti žemėlapio.
        </p>
      )}
    </div>
  )
}
