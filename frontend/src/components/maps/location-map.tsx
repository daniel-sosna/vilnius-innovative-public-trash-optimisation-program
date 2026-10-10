import { useEffect, useRef, useState } from 'react'
import { Map, Marker, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

setWorkerUrl(workerUrl)

type Location = { latitude: number; longitude: number }
type LocationMapProps = {
  latitude: number | null
  longitude: number | null
  zoom?: number
  interactive?: boolean
  canvasClassName?: string
  onSelect?: (location: Location) => void
}

export function LocationMap({ latitude, longitude, zoom = 15.5, interactive = false, canvasClassName, onSelect }: LocationMapProps) {
  const style = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  if (!onSelect && (latitude === null || longitude === null)) {
    return <p role="status" className="rounded-lg border bg-muted/40 p-5 text-sm">Vietos koordinatės: N/A. Žemėlapis nepasiekiamas.</p>
  }
  if ((latitude !== null && (!Number.isFinite(latitude) || Math.abs(latitude) > 90))
    || (longitude !== null && (!Number.isFinite(longitude) || Math.abs(longitude) > 180))) {
    return <MapUnavailable message="Vietos koordinatės netinkamos. Žemėlapis nepasiekiamas." />
  }
  let validStyle = false
  try {
    const url = new URL(style ?? '', window.location.href)
    validStyle = !!style && ['https:', 'http:'].includes(url.protocol)
  } catch { /* Invalid configuration has its own map area. */ }
  if (!validStyle || !style) return <MapUnavailable message="Žemėlapio konfigūracija nepasiekiama. Kreipkitės į administratorių." />
  return <MapCanvas latitude={latitude} longitude={longitude} zoom={zoom} interactive={interactive} style={style} canvasClassName={canvasClassName} onSelect={onSelect} />
}

function MapUnavailable({ message }: { message: string }) {
  return <p role="alert" className="rounded-lg border bg-muted/40 p-5 text-sm text-destructive">{message}</p>
}

function MapCanvas({ latitude, longitude, zoom = 15.5, interactive = false, style, canvasClassName, onSelect }: LocationMapProps & { style: string }) {
  const container = useRef<HTMLDivElement>(null)
  const latest = useRef({ latitude, longitude, zoom, onSelect })
  const runtime = useRef<{ map: Map; marker?: Marker } | null>(null)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<{ key: string; error: boolean } | null>(null)
  const selecting = !!onSelect
  const key = JSON.stringify([interactive, selecting, style, revision])
  const current = result?.key === key ? result : null

  useEffect(() => { latest.current = { latitude, longitude, zoom, onSelect } }, [latitude, longitude, zoom, onSelect])

  useEffect(() => {
    if (!container.current) return
    let map: Map | undefined
    let observer: ResizeObserver | undefined
    let disposed = false
    let failed = false
    let loaded = false
    let selectCenter: ((event: KeyboardEvent) => void) | undefined
    const fail = () => {
      if (disposed) return
      failed = true
      setResult({ key, error: true })
    }
    const timeout = window.setTimeout(fail, 20000)
    try {
      const initial = latest.current
      map = new Map({
        container: container.current, style,
        center: [initial.longitude ?? 25.2797, initial.latitude ?? 54.6872],
        zoom: initial.zoom, bearing: 0, pitch: 0,
        interactive: interactive || selecting,
        attributionControl: { compact: false },
        locale: {
          'AttributionControl.ToggleAttribution': 'Rodyti šaltinius',
          'NavigationControl.ZoomIn': 'Priartinti',
          'NavigationControl.ZoomOut': 'Atitolinti',
        },
      })
      runtime.current = { map }
      if (interactive || selecting) map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
      map.getCanvas().setAttribute('aria-label', 'Surinkimo vietos žemėlapis')
      if (!interactive && !selecting) map.getCanvas().removeAttribute('tabindex')
      if (initial.latitude !== null && initial.longitude !== null) {
        const marker = new Marker({ color: '#15803d' }).setLngLat([initial.longitude, initial.latitude]).addTo(map)
        marker.getElement().setAttribute('aria-label', 'Surinkimo vieta')
        runtime.current.marker = marker
      }
      if (selecting) {
        map.getCanvas().setAttribute('aria-description', 'Judėkite rodyklių klavišais. Enter arba tarpas pasirenka žemėlapio centrą.')
        map.on('click', (event) => {
          if (loaded && !failed) latest.current.onSelect?.({ latitude: event.lngLat.lat, longitude: event.lngLat.wrap().lng })
        })
        selectCenter = (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          if (!loaded || failed || event.repeat) return
          const center = map?.getCenter().wrap()
          if (center) latest.current.onSelect?.({ latitude: center.lat, longitude: center.lng })
        }
        map.getCanvas().addEventListener('keydown', selectCenter)
      }
      map.on('error', fail)
      map.on('webglcontextlost', fail)
      map.on('load', () => {
        window.clearTimeout(timeout)
        loaded = true
        if (!disposed && !failed) setResult({ key, error: false })
      })
      observer = new ResizeObserver(() => map?.resize())
      observer.observe(container.current)
    } catch { queueMicrotask(fail) }
    return () => {
      disposed = true
      window.clearTimeout(timeout)
      observer?.disconnect()
      if (selectCenter) map?.getCanvas().removeEventListener('keydown', selectCenter)
      runtime.current?.marker?.remove()
      runtime.current = null
      map?.remove()
    }
  }, [interactive, selecting, style, revision, key])

  useEffect(() => {
    const active = runtime.current
    if (!active || latitude === null || longitude === null) return
    if (!active.marker) {
      active.marker = new Marker({ color: '#15803d' }).setLngLat([longitude, latitude]).addTo(active.map)
      active.marker.getElement().setAttribute('aria-label', 'Surinkimo vieta')
    } else active.marker.setLngLat([longitude, latitude])
    if (!selecting) active.map.jumpTo({ center: [longitude, latitude], zoom, bearing: 0, pitch: 0 })
  }, [latitude, longitude, zoom, key, selecting])

  return (
    <div className="relative min-w-0 overflow-hidden rounded-lg border bg-muted/40">
      <div ref={container} className={cn('h-72 w-full sm:h-96', canvasClassName)} />
      {!current && <p role="status" className="absolute left-3 top-3 rounded-md bg-card px-3 py-2 text-sm shadow-sm">Kraunamas žemėlapis…</p>}
      {current?.error && (
        <div role="alert" className="absolute left-3 right-3 top-3 flex flex-wrap items-center gap-3 rounded-md border bg-card p-3 shadow-sm">
          <p className="text-sm text-destructive">Nepavyko įkelti žemėlapio. Bandykite dar kartą.</p>
          <Button type="button" variant="outline" size="sm" onClick={() => setRevision((value) => value + 1)}>Bandyti dar kartą</Button>
        </div>
      )}
    </div>
  )
}
