import { useEffect, useRef, useState } from 'react'
import type { Map as LibreMap, GeoJSONSource } from 'maplibre-gl'
import { Button } from '@/components/ui/button'

export type Bbox = { min_latitude: number; min_longitude: number; max_latitude: number; max_longitude: number }
export type AreaSelectionProps = {
  mode: 'drawing' | 'review' | null
  draft: Bbox | null
  confirmed: Bbox | null
  onDraft(bbox: Bbox | null): void
  onCancel(): void
  onRetake(): void
  onConfirm(): void
}

export function AreaSelection({ map, mode, draft, confirmed, onDraft, onCancel, onRetake, onConfirm }: AreaSelectionProps & { map: LibreMap }) {
  const surface = useRef<HTMLDivElement>(null)
  const gesture = useRef<{ id: number; start: [number, number]; end: [number, number] } | null>(null)
  const [rectangle, setRectangle] = useState<{ left: number; top: number; width: number; height: number } | null>(null)
  const [invalid, setInvalid] = useState(false)
  const active = mode !== null
  useEffect(() => {
    if (!active) return
    const capturedSurface = surface.current
    const handlers = [map.boxZoom, map.doubleClickZoom, map.dragPan, map.dragRotate, map.keyboard, map.scrollZoom, map.touchZoomRotate, map.touchPitch]
    const enabled = handlers.map(handler => handler.isEnabled())
    handlers.forEach(handler => handler.disable())
    return () => {
      handlers.forEach((handler, i) => { if (enabled[i]) handler.enable() })
      const current = gesture.current
      if (current && capturedSurface?.hasPointerCapture(current.id)) capturedSurface.releasePointerCapture(current.id)
      gesture.current = null
    }
  }, [map, active])
  useEffect(() => {
    if (!active) return
    const cancel = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onCancel() } }
    document.addEventListener('keydown', cancel, true)
    return () => document.removeEventListener('keydown', cancel, true)
  }, [active, onCancel])
  useEffect(() => {
    const source = 'analytics:selected-area'
    map.addSource(source, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
    map.addLayer({ id: `${source}:fill`, type: 'fill', source, paint: { 'fill-color': '#2563eb', 'fill-opacity': 0.12 } })
    map.addLayer({ id: `${source}:line`, type: 'line', source, paint: { 'line-color': '#2563eb', 'line-width': 2, 'line-dasharray': [3, 2] } })
    return () => {
      for (const id of [`${source}:line`, `${source}:fill`]) if (map.getLayer(id)) map.removeLayer(id)
      if (map.getSource(source)) map.removeSource(source)
    }
  }, [map])
  useEffect(() => {
    const bbox = mode === 'review' ? draft : confirmed
    const coordinates = bbox ? [[[bbox.min_longitude, bbox.min_latitude], [bbox.max_longitude, bbox.min_latitude], [bbox.max_longitude, bbox.max_latitude], [bbox.min_longitude, bbox.max_latitude], [bbox.min_longitude, bbox.min_latitude]]] : []
    ;(map.getSource('analytics:selected-area') as GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: bbox ? [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates } }] : [] })
  }, [map, mode, draft, confirmed])
  function position(event: React.PointerEvent): [number, number] {
    const bounds = event.currentTarget.getBoundingClientRect()
    return [Math.max(0, Math.min(bounds.width, event.clientX - bounds.left)), Math.max(0, Math.min(bounds.height, event.clientY - bounds.top))]
  }
  function move(event: React.PointerEvent) {
    const current = gesture.current
    if (!current || current.id !== event.pointerId) return
    current.end = position(event)
    const [x, y] = current.start, [endX, endY] = current.end
    setRectangle({ left: Math.min(x, endX), top: Math.min(y, endY), width: Math.abs(endX - x), height: Math.abs(endY - y) })
  }
  function finish(event: React.PointerEvent) {
    move(event)
    const current = gesture.current
    if (!current || current.id !== event.pointerId) return
    gesture.current = null
    event.currentTarget.releasePointerCapture(event.pointerId)
    setRectangle(null)
    try {
      const [x, y] = current.start, [endX, endY] = current.end
      if (x === endX || y === endY) throw new Error('Empty rectangle')
      const corners = [[x, y], [endX, y], [endX, endY], [x, endY]].map(point => map.unproject(point as [number, number]))
      if (corners.some((corner, index) => { const screen = map.project(corner); const original = [[x, y], [endX, y], [endX, endY], [x, endY]][index]; return Math.hypot(screen.x - original[0], screen.y - original[1]) > 2 })) throw new Error('Unprojectable sky area')
      const bbox = { min_latitude: Math.min(...corners.map(p => p.lat)), max_latitude: Math.max(...corners.map(p => p.lat)), min_longitude: Math.min(...corners.map(p => p.lng)), max_longitude: Math.max(...corners.map(p => p.lng)) }
      if (!Object.values(bbox).every(Number.isFinite) || bbox.min_latitude < -90 || bbox.max_latitude > 90 || bbox.min_longitude < -180 || bbox.max_longitude > 180 || bbox.max_longitude - bbox.min_longitude >= 180 || bbox.min_latitude >= bbox.max_latitude || bbox.min_longitude >= bbox.max_longitude) throw new Error('Invalid envelope')
      setInvalid(false)
      onDraft(bbox)
    } catch { setInvalid(true); onDraft(null) }
  }
  if (!active) return null
  return <>
    <div ref={surface} className="absolute inset-0 z-10 touch-none" style={{ cursor: mode === 'drawing' ? 'crosshair' : 'default' }}
      onPointerDown={event => {
        if (mode !== 'drawing' || gesture.current || !event.isPrimary || event.button !== 0) return
        event.preventDefault()
        setInvalid(false)
        gesture.current = { id: event.pointerId, start: position(event), end: position(event) }
        event.currentTarget.setPointerCapture(event.pointerId)
      }} onPointerMove={move} onPointerUp={finish}
      onPointerCancel={event => {
        if (gesture.current?.id === event.pointerId) { gesture.current = null; setRectangle(null); onCancel() }
      }}>
      {rectangle && <div className="pointer-events-none absolute border-2 border-blue-600 bg-blue-500/20" style={rectangle} />}
    </div>
    <div className="absolute inset-x-3 bottom-10 z-20 mx-auto flex max-w-lg flex-wrap items-center justify-center gap-2 rounded-lg border bg-card p-3 shadow-lg">
      <p role="status" className="w-full text-center text-sm">{invalid ? 'Plotas netinkamas. Pasirinkite iš naujo.' : mode === 'drawing' ? 'Brėžkite stačiakampį žemėlapyje.' : 'Patikrinkite pažymėtą geografinį plotą.'}</p>
      {mode === 'review' && <Button onClick={onConfirm} disabled={!draft}>Patvirtinti</Button>}
      {(mode === 'review' || invalid) && <Button variant="outline" onClick={() => { setInvalid(false); setRectangle(null); onRetake() }}>Pasirinkti iš naujo</Button>}
      <Button variant="outline" onClick={onCancel}>Atšaukti</Button>
    </div>
  </>
}
