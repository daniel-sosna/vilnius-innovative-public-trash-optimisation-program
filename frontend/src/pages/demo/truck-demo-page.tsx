import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { GeoJSONSource, Marker, type Map as LibreMap } from 'maplibre-gl'
import type { FeatureCollection, Point } from 'geojson'
import { AnalyticsMap } from '@/components/maps/analytics-map'
import { createPointLayer } from '@/components/maps/point-layer'
import { truckRequest, type Truck } from '@/pages/trucks/api'
import { getDrivingRoute, type DrivingRoute } from './api'
import { emptyCollection, prefix } from './geometry'
import { routeSourceId, routesLayer } from './layers'

const stopsLayer = createPointLayer({
  id: 'driving-stops', label: 'Konteineriai', meaning: 'Surinkimo sustojimai', legend: [],
  load: async () => emptyCollection as FeatureCollection<Point>,
  appearance: { color: ['case', ['get', 'collected'], '#15803d', '#dc2626'] },
  clustering: false,
  details(feature) {
    const element = document.createElement('p')
    element.textContent = `Konteineris ${feature.id}: ${feature.properties?.collected ? 'surinktas' : 'laukiama'}`
    return element
  },
})
const drivingLayers = [routesLayer, stopsLayer] as const
const drivingSelection = { 'demo-routes': true, 'driving-stops': true }
const travelTimes = [6500, 9500, 8000, 11000, 7200]
const pauseTimes = [2200, 3400, 1800, 2800, 2400]

function truckIcon(): HTMLElement {
  const element = document.createElement('div')
  element.className = 'rounded-full border-2 border-white bg-blue-700 p-2 text-white shadow-lg'
  element.setAttribute('role', 'img'); element.setAttribute('aria-label', 'Šiukšliavežė')
  element.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M1 3h14v13H1zM15 8h4l3 4v4h-7"/><circle cx="5" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>'
  return element
}

export function TruckDemoPage() {
  const { truck_id = '' } = useParams()
  const [lookup, setLookup] = useState<{ id: string; route?: DrivingRoute; error?: string }>({ id: '' })
  const [map, setMap] = useState<LibreMap | null>(null)
  const [mapError, setMapError] = useState(false)
  const [collection, setCollection] = useState<{ route: DrivingRoute | null; count: number }>({ route: null, count: 0 })
  const route = lookup.id === truck_id ? lookup.route : undefined
  const error = lookup.id === truck_id ? lookup.error : undefined
  const collected = collection.route === route ? collection.count : 0
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      if (!/^[1-9]\d*$/.test(truck_id) || !Number.isSafeInteger(Number(truck_id))) {
        setLookup({ id: truck_id, error: 'Netinkamas šiukšliavežės numeris.' }); return
      }
      try {
        await truckRequest<Truck>(`/${truck_id}`, { signal: controller.signal })
      } catch {
        if (!controller.signal.aborted) setLookup({ id: truck_id, error: 'Šiukšliavežė nerasta arba serveris nepasiekiamas.' })
        return
      }
      try {
        const road = await getDrivingRoute(controller.signal)
        if (!controller.signal.aborted) setLookup({ id: truck_id, route: road })
      } catch (failure) {
        if (!controller.signal.aborted) setLookup({ id: truck_id, error: failure instanceof Error ? failure.message : 'Nepavyko gauti kelio maršruto. Atnaujinkite puslapį.' })
      }
    }
    void load()
    return () => controller.abort()
  }, [truck_id])
  const onMapState = useCallback((status: 'loading' | 'ready' | 'error', instance: LibreMap | null) => {
    setMap(instance); setMapError(status === 'error')
  }, [])
  useEffect(() => {
    if (!map || !route) return
    let frame = 0, disposed = false
    const position = (point: { longitude: number; latitude: number }): [number, number] => [point.longitude, point.latitude]
    const marker = new Marker({ element: truckIcon() }).setLngLat(position(route.path[0])).addTo(map)
    map.jumpTo({ center: position(route.path[0]), zoom: 16 })
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let accumulated = 0
    const timeline = route.legs.map((leg, index) => {
      const move = reducedMotion ? 600 : Math.min(14000, Math.max(6000, travelTimes[index % travelTimes.length] + leg.distance_m * 4))
      const pause = reducedMotion ? 500 : pauseTimes[index % pauseTimes.length]
      const start = accumulated
      accumulated += move + pause
      return { start, move, pause, end: accumulated, path: leg.path.map(position) }
    })
    const begin = performance.now()
    let lastCollected = -1
    let lastLeg = -2, lastProgress = -1
    queueMicrotask(() => { if (!disposed) setCollection({ route, count: 0 }) })
    const animate = (now: number) => {
      if (disposed) return
      const elapsed = Math.min(accumulated, now - begin)
      const index = timeline.findIndex(leg => elapsed < leg.end)
      const legIndex = index < 0 ? timeline.length - 1 : index
      const leg = timeline[legIndex], local = elapsed - leg.start
      const progress = Math.min(1, Math.max(0, local / leg.move))
      // Accelerate, vary speed during travel, then decelerate at each stop.
      const eased = progress * progress * (3 - 2 * progress)
      const varied = eased - 0.12 * Math.sin(4 * Math.PI * eased) / (4 * Math.PI)
      const path = prefix(leg.path, varied)
      const currentPosition = path[path.length - 1] as [number, number]
      marker.setLngLat(currentPosition)
      map.jumpTo({ center: currentPosition })
      if (index !== lastLeg || varied !== lastProgress) {
        lastLeg = index; lastProgress = varied
        const remaining = index < 0 ? [] : [
          currentPosition,
          ...(progress >= 1 ? [] : leg.path.slice(path.length - 1)),
          ...timeline.slice(legIndex + 1).flatMap(next => next.path.slice(1)),
        ]
        const source = map.getSource(routeSourceId)
        if (source instanceof GeoJSONSource) {
          const data: FeatureCollection = remaining.length < 2 ? emptyCollection : {
            type: 'FeatureCollection', features: [{ type: 'Feature', properties: { color: '#2563eb' }, geometry: { type: 'LineString', coordinates: remaining } }],
          }
          // Keep the source and map instance; trim behind the same interpolated
          // position used by the truck, retaining all future road legs.
          void source.setData(data).catch(() => { /* Shared map error feedback owns failures. */ })
        }
      }
      const count = index < 0 ? timeline.length : legIndex + (local >= leg.move + leg.pause * 0.75 ? 1 : 0)
      if (count !== lastCollected) {
        lastCollected = count
        setCollection({ route, count })
      }
      if (elapsed < accumulated) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => { disposed = true; cancelAnimationFrame(frame); marker.remove() }
  }, [map, route])
  const roadData = useMemo<FeatureCollection>(() => route ? { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { color: '#2563eb' }, geometry: { type: 'LineString', coordinates: route.path.map(point => [point.longitude, point.latitude]) } }] } : emptyCollection, [route])
  const states = useMemo(() => ({
    'demo-routes': { status: 'ready' as const, data: roadData },
    'driving-stops': { status: 'ready' as const, data: { type: 'FeatureCollection', features: (route?.stops ?? []).map((point, index) => ({ type: 'Feature', id: index + 1, geometry: { type: 'Point', coordinates: [point.longitude, point.latitude] }, properties: { collected: index < collected } })) } as FeatureCollection },
  }), [roadData, route, collected])
  return <section className="min-w-0 space-y-4">
    <h1 className="text-2xl font-semibold">Šiukšliavežės sekimas</h1>
    {error ? <p role="alert" className="text-destructive">{error}</p> : !route ? <p role="status">Kraunamas šiukšliavežės maršrutas…</p> : <>
      <div className="h-[72dvh] min-h-80 overflow-hidden rounded-lg border"><AnalyticsMap definitions={drivingLayers} selection={drivingSelection} states={states} accessibleLabel="Šiukšliavežės sekimo žemėlapis" onMapState={onMapState} /></div>
      {mapError && <p role="alert" className="text-destructive">Žemėlapis nepasiekiamas. Bandykite įkelti dar kartą.</p>}
      <p className="text-xs text-muted-foreground"><a className="underline" href="https://project-osrm.org/">OSRM</a> · © <a className="underline" href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · <a className="underline" href="https://www.openstreetmap.org/">Taisyti žemėlapį</a></p>
    </>}
  </section>
}
