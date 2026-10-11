import { useEffect, useMemo, useRef, useState } from 'react'
import { loadAdequacy, type AdequacyEntry } from './adequacy'
import type { LayerRequest } from './use-layer-session'

export function useAdequacy() {
  const [catalog, setCatalog] = useState<AdequacyEntry[]>([])
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [analysisId, setAnalysisId] = useState('')
  const [wasteType, setWasteType] = useState('Mixed municipal waste')
  const pending = useRef<AbortController | null>(null)
  useEffect(() => () => pending.current?.abort(), [])

  function refresh() {
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    setStatus('loading')
    void fetch('/api/map-analytics/adequacy-analyses', { signal: controller.signal, cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('Catalog read failed')
        const data = await response.json() as { analyses: AdequacyEntry[] }
        if (!Array.isArray(data.analyses) || data.analyses.some(e => !/^adequacy-\d{4}-\d{2}$/.test(e.id)
          || !/^[a-f0-9]{64}$/.test(e.revision) || e.schema_version !== '1' || e.complete !== true)) throw new Error('Invalid catalog')
        if (controller.signal.aborted) return
        setCatalog(data.analyses)
        setAnalysisId(previous => data.analyses.some(e => e.id === previous) ? previous : data.analyses[0]?.id ?? '')
        setStatus('ready')
      }).catch(() => { if (!controller.signal.aborted) setStatus('error') })
  }
  const selected = catalog.find(e => e.id === analysisId)
  const requests = useMemo<Record<string, LayerRequest | null>>(() => ({
    adequacy: selected ? { key: `adequacy:${selected.id}:${selected.revision}`, load: signal => loadAdequacy(selected, signal) } : null,
  }), [selected])
  return { catalog, status, analysisId, setAnalysisId, wasteType, setWasteType, refresh, requests, selected }
}
