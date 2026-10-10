import { useEffect, useRef, useState } from 'react'
import type { LayerLoadState, LayerSelection, LayerStates, MapLayerDefinition } from '@/components/maps/map-layer'

type PendingRead = { controller: AbortController; promise: Promise<void> }

export function useLayerSession(definitions: readonly MapLayerDefinition[]) {
  const [selection, setSelection] = useState<LayerSelection>({})
  const [states, setStates] = useState<LayerStates>({})
  const cache = useRef<LayerStates>({})
  const pending = useRef(new Map<string, PendingRead>())
  const mounted = useRef(false)

  useEffect(() => {
    mounted.current = true
    const reads = pending.current
    return () => {
      mounted.current = false
      for (const read of reads.values()) read.controller.abort()
      reads.clear()
    }
  }, [])

  function publish(id: string, state: LayerLoadState) {
    cache.current[id] = state
    setStates(previous => ({ ...previous, [id]: state }))
  }

  function load(layer: MapLayerDefinition): Promise<void> {
    const inFlight = pending.current.get(layer.id)
    if (inFlight) return inFlight.promise
    if (cache.current[layer.id]?.status === 'ready') return Promise.resolve()
    const controller = new AbortController()
    publish(layer.id, { status: 'loading' })
    // Defer invocation so even a synchronous loader error follows this lifecycle.
    const promise = Promise.resolve().then(() => layer.load(controller.signal))
      .then(data => {
        if (mounted.current && !controller.signal.aborted) publish(layer.id, { status: 'ready', data })
      })
      .catch(() => {
        if (mounted.current && !controller.signal.aborted) publish(layer.id, { status: 'error' })
      })
      .finally(() => {
        if (pending.current.get(layer.id)?.controller === controller) pending.current.delete(layer.id)
      })
    pending.current.set(layer.id, { controller, promise })
    return promise
  }

  function toggle(id: string, checked: boolean) {
    const layer = definitions.find(definition => definition.id === id)
    if (!layer) return
    setSelection(previous => ({ ...previous, [id]: checked }))
    if (checked && cache.current[id]?.status !== 'error') void load(layer)
  }

  function retry(id: string) {
    const layer = definitions.find(definition => definition.id === id)
    if (layer && selection[id]) void load(layer)
  }

  return { selection, states, toggle, retry }
}
