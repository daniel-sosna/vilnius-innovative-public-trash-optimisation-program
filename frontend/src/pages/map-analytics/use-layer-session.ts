import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { LayerData, LayerLoadState, LayerSelection, LayerStates, MapLayerDefinition } from '@/components/maps/map-layer'

export type LayerRequest = { key: string; load(signal: AbortSignal): Promise<LayerData> }
type Requests = Record<string, LayerRequest | null>
type PendingRead = { controller: AbortController; promise: Promise<LayerData> }
const noRequests: Requests = {}
const resolveRequest = (requests: Requests, layer: MapLayerDefinition): LayerRequest | null =>
  Object.hasOwn(requests, layer.id) ? requests[layer.id] : { key: layer.id, load: layer.load }

export function useLayerSession(definitions: readonly MapLayerDefinition[], requests: Requests = noRequests) {
  const [selection, setSelection] = useState<LayerSelection>({})
  const [stored, setStored] = useState<Record<string, { key: string; state: LayerLoadState }>>({})
  const cache = useRef(new Map<string, LayerData>())
  const pending = useRef(new Map<string, PendingRead>())
  const mounted = useRef(false)
  const current = useRef(requests)
  useLayoutEffect(() => { current.current = requests }, [requests])
  function requestFor(layer: MapLayerDefinition): LayerRequest | null {
    return resolveRequest(current.current, layer)
  }

  useEffect(() => {
    mounted.current = true
    const reads = pending.current
    return () => {
      mounted.current = false
      for (const read of reads.values()) read.controller.abort()
      reads.clear()
    }
  }, [])

  function load(layer: MapLayerDefinition): void {
    const request = requestFor(layer)
    if (!request) return
    const { key } = request
    const publish = (state: LayerLoadState) => {
      if (mounted.current && requestFor(layer)?.key === key) setStored(previous => ({ ...previous, [layer.id]: { key, state } }))
    }
    const cached = cache.current.get(key)
    if (cached) { publish({ status: 'ready', data: cached }); return }
    publish({ status: 'loading' })
    let read = pending.current.get(key)
    if (!read) {
      const controller = new AbortController()
      const promise = Promise.resolve().then(() => request.load(controller.signal)).then(data => {
        if (!controller.signal.aborted) cache.current.set(key, data)
        return data
      }).finally(() => {
        if (pending.current.get(key)?.controller === controller) pending.current.delete(key)
      })
      read = { controller, promise }
      pending.current.set(key, read)
    }
    const selectedRead = read
    void read.promise.then(data => {
      if (!selectedRead.controller.signal.aborted) publish({ status: 'ready', data })
    }).catch(() => {
      if (!selectedRead.controller.signal.aborted) publish({ status: 'error' })
    })
  }

  // Artifact revision changes data identity without changing the map definition.
  useEffect(() => {
    for (const layer of definitions) {
      const request = requestFor(layer)
      if (selection[layer.id] && request && stored[layer.id]?.key !== request.key) load(layer)
    }
  })

  function toggle(id: string, checked: boolean) {
    const layer = definitions.find(definition => definition.id === id)
    if (!layer) return
    setSelection(previous => ({ ...previous, [id]: checked }))
  }

  function retry(id: string) {
    const layer = definitions.find(definition => definition.id === id)
    if (layer && selection[id]) void load(layer)
  }

  const states: LayerStates = {}
  for (const layer of definitions) {
    const request = resolveRequest(requests, layer)
    states[layer.id] = request && stored[layer.id]?.key === request.key ? stored[layer.id].state : { status: 'idle' }
  }
  return { selection, states, toggle, retry }
}
