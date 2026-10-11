import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { loadAdequacy, type AdequacyEntry } from './adequacy'
import type { LayerRequest } from './use-layer-session'

export function useAdequacy(projectDate: string) {
  const [catalog, setCatalog] = useState<AdequacyEntry[]>([])
  const [catalogDate, setCatalogDate] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [month, setMonth] = useState('2026-09')
  const [enabled, setEnabled] = useState(false)
  const [wasteType, setWasteType] = useState('Mixed municipal waste')
  const pending = useRef<AbortController | null>(null)
  const currentDate = useRef(projectDate)
  currentDate.current = projectDate
  useEffect(() => () => pending.current?.abort(), [])

  const refresh = useCallback(() => {
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    setStatus('loading')
    void fetch(`/api/map-analytics/adequacy-analyses?project_date=${encodeURIComponent(projectDate)}`, { signal: controller.signal, cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('Catalog read failed')
        const data = await response.json() as { analyses: AdequacyEntry[] }
        if (!Array.isArray(data.analyses) || data.analyses.some(e => !/^adequacy-\d{4}-\d{2}(?:-\d{2})?$/.test(e.id)
          || !/^[a-f0-9]{64}$/.test(e.revision) || !['1', '2'].includes(e.schema_version)
          || e.method_version !== e.schema_version || typeof e.complete !== 'boolean'
          || (e.schema_version === '2' ? e.id !== `adequacy-${projectDate}` : !e.complete || e.period_end > projectDate))) throw new Error('Invalid catalog')
        if (controller.signal.aborted || currentDate.current !== projectDate || pending.current !== controller) return
        setCatalog(data.analyses)
        setMonth(previous => previous === '2026-09' || data.analyses.some(entry => entry.month === previous) ? previous : '2026-09')
        setCatalogDate(projectDate)
        setStatus('ready')
      }).catch(() => { if (!controller.signal.aborted && currentDate.current === projectDate) setStatus('error') })
  }, [projectDate])

  useEffect(() => {
    if (enabled) refresh()
    if (!enabled) pending.current?.abort()
    // Explicit refresh remains available after an error; avoid an automatic retry loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, projectDate, refresh])

  const analysisId = month === '2026-09' ? `adequacy-${projectDate}` : `adequacy-${month}`
  const selected = catalog.find(e => e.id === analysisId && (e.month !== '2026-09' || catalogDate === projectDate))
  const requests = useMemo<Record<string, LayerRequest | null>>(() => ({
    adequacy: selected ? { key: `adequacy:${selected.id}:${selected.revision}`, load: signal => loadAdequacy(selected, signal) } : null,
  }), [selected])
  const months = [...new Set(['2026-09', ...catalog.map(entry => entry.month)])]
  const visibleStatus = enabled && catalogDate !== projectDate && status !== 'error' ? 'loading' : status
  return { catalog, status: visibleStatus, month, setMonth, months, analysisId, wasteType, setWasteType, refresh, requests, selected, setEnabled }
}
