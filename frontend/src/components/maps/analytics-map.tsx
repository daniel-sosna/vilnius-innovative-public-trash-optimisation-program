import { useEffect, useRef, useState } from 'react'
import { Map as LibreMap, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Button } from '@/components/ui/button'
import type { LayerRenderer, LayerSelection, LayerStates, MapLayerDefinition } from './map-layer'
import './analytics-map.css'

setWorkerUrl(workerUrl)

type MapProps = {
  definitions: readonly MapLayerDefinition[]
  selection: LayerSelection
  states: LayerStates
}

export function AnalyticsMap(props: MapProps) {
  const style = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  let configured = false
  try {
    configured = !!style && ['https:', 'http:'].includes(new URL(style).protocol)
  } catch { /* Configuration feedback stays independent of dataset loading. */ }
  if (!configured || !style) {
    return (
      <div role="alert" className="analytics-map flex min-w-0 items-center justify-center rounded-lg border bg-muted/40 p-5 text-sm text-destructive">
        Žemėlapio konfigūracija nepasiekiama arba netinkama. Kreipkitės į administratorių.
      </div>
    )
  }
  return <AnalyticsCanvas {...props} style={style} />
}

function AnalyticsCanvas({ definitions, selection, states, style }: MapProps & { style: string }) {
  const container = useRef<HTMLDivElement>(null)
  const latest = useRef({ selection, states })
  const camera = useRef({ center: [25.2797, 54.6872] as [number, number], zoom: 10, bearing: 0, pitch: 0 })
  const runtime = useRef<{ map: LibreMap; sync(selection: LayerSelection, states: LayerStates): void } | null>(null)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<{ revision: number; status: 'ready' | 'error' } | null>(null)
  const status = result?.revision === revision ? result.status : 'loading'

  useEffect(() => {
    latest.current = { selection, states }
    runtime.current?.sync(selection, states)
  }, [selection, states])

  useEffect(() => {
    if (!container.current) return
    let map: LibreMap | undefined
    let observer: ResizeObserver | undefined
    let popup: { id: string; value: Popup } | undefined
    const renderers = new Map<string, LayerRenderer>()
    let disposed = false
    let ready = false
    let failed = false
    const events = new AbortController()
    const fail = () => {
      if (disposed) return
      failed = true
      setResult({ revision, status: 'error' })
    }
    const timeout = window.setTimeout(fail, 20000)
    const closeDetails = (id: string) => {
      if (popup?.id === id) { popup.value.remove(); popup = undefined }
    }
    try {
      const instance = new LibreMap({
        container: container.current, style, ...camera.current,
        attributionControl: { compact: true },
        locale: {
          'AttributionControl.ToggleAttribution': 'Rodyti šaltinius',
          'NavigationControl.ZoomIn': 'Priartinti',
          'NavigationControl.ZoomOut': 'Atitolinti',
          'Popup.Close': 'Uždaryti informaciją',
        },
      })
      map = instance
      instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')
      const canvas = instance.getCanvas()
      canvas.setAttribute('aria-label', 'Vilniaus žemėlapio analitika')
      // Pointer interaction should not draw the keyboard focus outline.
      canvas.addEventListener('pointerdown', () => canvas.setAttribute('data-pointer-focus', ''), { signal: events.signal })
      const clearPointerFocus = () => canvas.removeAttribute('data-pointer-focus')
      canvas.addEventListener('keydown', clearPointerFocus, { signal: events.signal })
      canvas.addEventListener('blur', clearPointerFocus, { signal: events.signal })
      const sync = (selected: LayerSelection, loaded: LayerStates) => {
        if (!ready || disposed) return
        for (const layer of definitions) {
          let renderer = renderers.get(layer.id)
          const state = loaded[layer.id]
          if (!renderer && selected[layer.id] && state?.status === 'ready') {
            renderer = layer.attach({
              map: instance, closeDetails,
              showDetails(id, coordinates, content) {
                popup?.value.remove()
                const value = new Popup({ maxWidth: '280px', className: 'analytics-popup', focusAfterOpen: true })
                  .setLngLat(coordinates).setDOMContent(content).addTo(instance)
                popup = { id, value }
                const close = value.getElement().querySelector<HTMLButtonElement>('.maplibregl-popup-close-button')
                close?.setAttribute('aria-label', 'Uždaryti informaciją')
                close?.setAttribute('title', 'Uždaryti informaciją')
                close?.addEventListener('click', () => instance.getCanvas().focus(), { once: true })
              },
            }, state.data)
            renderers.set(layer.id, renderer)
          }
          renderer?.setVisible(!!selected[layer.id])
        }
      }
      runtime.current = { map: instance, sync }
      instance.on('error', fail)
      instance.on('webglcontextlost', fail)
      instance.on('load', () => {
        window.clearTimeout(timeout)
        if (disposed) return
        ready = true
        sync(latest.current.selection, latest.current.states)
        if (!failed) setResult({ revision, status: 'ready' })
      })
      const closeWithEscape = (event: KeyboardEvent) => {
        if (event.key === 'Escape' && popup) {
          popup.value.remove()
          popup = undefined
          instance.getCanvas().focus()
        }
      }
      instance.getContainer().addEventListener('keydown', closeWithEscape, { signal: events.signal })
      observer = new ResizeObserver(() => instance.resize())
      observer.observe(container.current)
    } catch {
      queueMicrotask(fail)
    }
    return () => {
      disposed = true
      window.clearTimeout(timeout)
      events.abort()
      observer?.disconnect()
      popup?.value.remove()
      if (map) {
        camera.current = { center: map.getCenter().toArray(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() }
        for (const renderer of renderers.values()) renderer.dispose()
        map.remove()
      }
      runtime.current = null
    }
  }, [definitions, style, revision])

  return (
    <div className="analytics-map relative min-w-0 overflow-hidden rounded-lg border bg-muted/40">
      <div ref={container} className="h-full w-full" />
      {status === 'loading' && (
        <p role="status" className="absolute left-3 top-3 max-w-[calc(100%-4rem)] rounded-md bg-card px-3 py-2 text-sm shadow-sm">
          Kraunamas žemėlapis…
        </p>
      )}
      {status === 'error' && (
        <div role="alert" className="absolute left-3 right-12 top-3 flex flex-wrap items-center gap-3 rounded-md border bg-card p-3 shadow-sm">
          <p className="text-sm text-destructive">Nepavyko įkelti žemėlapio.</p>
          <Button variant="outline" size="sm" onClick={() => setRevision(value => value + 1)}>Bandyti dar kartą</Button>
        </div>
      )}
    </div>
  )
}
