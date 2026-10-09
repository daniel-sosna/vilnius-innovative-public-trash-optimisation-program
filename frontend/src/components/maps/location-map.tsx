import { useEffect, useRef, useState } from 'react'
import { Map, Marker, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// Bundle the ESM worker as a separate same-origin asset for development/builds.
setWorkerUrl(workerUrl)

type LocationMapProps = {
  latitude: number | null
  longitude: number | null
  zoom?: number
  interactive?: boolean
  canvasClassName?: string
}

export function LocationMap({
  latitude,
  longitude,
  zoom = 15.5,
  interactive = false,
  canvasClassName,
}: LocationMapProps) {
  const style = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  if (latitude === null || longitude === null) {
    return (
      <p role="status" className="rounded-lg border bg-muted/40 p-5 text-sm">
        Vietos koordinatės: N/A. Žemėlapis nepasiekiamas.
      </p>
    )
  }
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)
    || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    return <MapUnavailable message="Vietos koordinatės netinkamos. Žemėlapis nepasiekiamas." />
  }
  let validStyle = false
  try {
    const url = new URL(style ?? '', window.location.href)
    validStyle = !!style && ['https:', 'http:'].includes(url.protocol)
  } catch { /* Invalid configuration has its own recoverable map area. */ }
  if (!validStyle || !style) {
    return <MapUnavailable message="Žemėlapio konfigūracija nepasiekiama. Kreipkitės į administratorių." />
  }
  return <MapCanvas latitude={latitude} longitude={longitude} zoom={zoom} interactive={interactive} style={style} canvasClassName={canvasClassName} />
}

function MapUnavailable({ message }: { message: string }) {
  return <p role="alert" className="rounded-lg border bg-muted/40 p-5 text-sm text-destructive">{message}</p>
}

function MapCanvas({ latitude, longitude, zoom, interactive, style, canvasClassName }: {
  latitude: number
  longitude: number
  zoom: number
  interactive: boolean
  style: string
  canvasClassName?: string
}) {
  const container = useRef<HTMLDivElement>(null)
  const initialView = useRef({ latitude, longitude, zoom })
  const runtime = useRef<{ map: Map; marker: Marker } | null>(null)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<{ key: string; error: boolean } | null>(null)
  const key = JSON.stringify([interactive, style, revision])
  const current = result?.key === key ? result : null

  useEffect(() => {
    if (!container.current) return
    let map: Map | undefined
    let marker: Marker | undefined
    let observer: ResizeObserver | undefined
    let disposed = false
    let failed = false
    const fail = () => {
      if (disposed) return
      failed = true
      setResult({ key, error: true })
    }
    const timeout = window.setTimeout(fail, 20000)
    try {
      const initial = initialView.current
      map = new Map({
        container: container.current,
        style,
        center: [initial.longitude, initial.latitude],
        zoom: initial.zoom,
        bearing: 0,
        pitch: 0,
        interactive,
        attributionControl: { compact: false },
        locale: {
          'AttributionControl.ToggleAttribution': 'Rodyti šaltinius',
          'NavigationControl.ZoomIn': 'Priartinti',
          'NavigationControl.ZoomOut': 'Atitolinti',
        },
      })
      if (interactive) map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
      map.getCanvas().setAttribute('aria-label', 'Surinkimo vietos žemėlapis')
      if (!interactive) map.getCanvas().removeAttribute('tabindex')
      marker = new Marker({ color: '#15803d' })
        .setLngLat([initial.longitude, initial.latitude]).addTo(map)
      runtime.current = { map, marker }
      marker.getElement().setAttribute('aria-label', 'Surinkimo vieta')
      map.on('error', fail)
      map.on('webglcontextlost', fail)
      map.on('load', () => {
        window.clearTimeout(timeout)
        if (!disposed && !failed) setResult({ key, error: false })
      })
      observer = new ResizeObserver(() => map?.resize())
      observer.observe(container.current)
    } catch {
      // Report synchronous WebGL/setup failures after the effect finishes.
      queueMicrotask(fail)
    }
    return () => {
      disposed = true
      window.clearTimeout(timeout)
      observer?.disconnect()
      runtime.current = null
      marker?.remove()
      map?.remove()
    }
  }, [interactive, style, revision, key])

  useEffect(() => {
    runtime.current?.marker.setLngLat([longitude, latitude])
    runtime.current?.map.jumpTo({ center: [longitude, latitude], zoom, bearing: 0, pitch: 0 })
  }, [latitude, longitude, zoom, key])

  return (
    <div className="relative overflow-hidden rounded-lg border bg-muted/40">
      <div ref={container} className={cn('h-72 w-full sm:h-96', canvasClassName)} />
      {!current && (
        <p role="status" className="absolute left-3 top-3 rounded-md bg-card px-3 py-2 text-sm shadow-sm">
          Kraunamas žemėlapis…
        </p>
      )}
      {current?.error && (
        <div role="alert" className="absolute left-3 right-3 top-3 flex flex-wrap items-center gap-3 rounded-md border bg-card p-3 shadow-sm">
          <p className="text-sm text-destructive">Nepavyko įkelti žemėlapio. Vietos duomenis galite peržiūrėti žemiau.</p>
          <Button variant="outline" size="sm" onClick={() => setRevision((value) => value + 1)}>
            Bandyti dar kartą
          </Button>
        </div>
      )}
    </div>
  )
}
