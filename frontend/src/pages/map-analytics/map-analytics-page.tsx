import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { FeatureCollection, Point } from 'geojson'
import { Layers, Sparkles, X } from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AnalyticsMap } from '@/components/maps/analytics-map'
import type { Bbox } from '@/components/maps/area-selection'
import { MapLegend } from '@/components/maps/map-legend'
import { Button } from '@/components/ui/button'
import { getActiveLayers, mapLayers } from './layers'
import { useLayerSession } from './use-layer-session'
import { useBinFilters } from './use-bin-filters'
import { useProjectDate } from '@/lib/project-date/context'
import type { BinProperties } from './api'
import { adequacyMonthLabel, adequacyPeriodLabel, adequacyWasteTypes, type AdequacyData } from './adequacy'
import { useAdequacy } from './use-adequacy'

const investigationMessages = [
  'Vertinama pasirinkto ploto duomenų aprėptis…',
  'Tikrinami apžvalgos duomenys ir svarbiausi rodikliai…',
  'Lyginami surinkti rodikliai ir ieškoma reikšmingų skirtumų…',
  'Tikslinamos įžvalgos ir tikrinami duomenų ribotumai…',
]

type Analysis = { project_date: string; status: 'complete' | 'incomplete'; bbox: Bbox; answer: string | null; default_period: { start: string; end: string }; incomplete_reason: string | null; model_requests: number; elapsed_seconds: number }

export function MapAnalyticsPage() {
  const { projectDate } = useProjectDate()
  const currentProjectDate = useRef(projectDate)
  currentProjectDate.current = projectDate
  const adequacy = useAdequacy(projectDate)
  const { selection, states, toggle, retry } = useLayerSession(mapLayers, adequacy.requests)
  const bins = states.bins
  const binFilters = useBinFilters(bins?.status === 'ready' ? bins.data as FeatureCollection<Point, BinProperties> : undefined)
  const adequacyState = states.adequacy
  const analysisData = adequacyState?.status === 'ready' ? adequacyState.data as AdequacyData : undefined
  const renderedData = useMemo(() => ({
    bins: binFilters.filteredData,
    adequacy: analysisData ? { ...analysisData, features: analysisData.features.filter(f => f.properties.waste_type === adequacy.wasteType) } : undefined,
  }), [binFilters.filteredData, analysisData, adequacy.wasteType])
  const activeLayers = getActiveLayers(selection)
  const [sidebarMode, setSidebarMode] = useState<'layers' | 'ai' | null>(null)
  const layersTrigger = useRef<HTMLButtonElement>(null), aiTrigger = useRef<HTMLButtonElement>(null)
  const [mode, setMode] = useState<'drawing' | 'review' | null>(null)
  const [draft, setDraft] = useState<Bbox | null>(null), [confirmed, setConfirmed] = useState<Bbox | null>(null)
  const [pending, setPending] = useState(false), [answer, setAnswer] = useState<Analysis | null>(null), [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState('Ruošiama pasirinkto ploto analizė…')
  const request = useRef<AbortController | null>(null)
  const close = useCallback(() => {
    setSidebarMode(null)
    ;(sidebarMode === 'layers' ? layersTrigger : aiTrigger).current?.focus()
  }, [sidebarMode, setSidebarMode])
  const cancelSelection = useCallback(() => { setDraft(null); setMode(null); setSidebarMode('ai'); requestAnimationFrame(() => aiTrigger.current?.focus()) }, [setDraft, setMode, setSidebarMode])
  useEffect(() => {
    if (mode) {
      const cancel = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); cancelSelection() } }
      document.addEventListener('keydown', cancel, true)
      return () => document.removeEventListener('keydown', cancel, true)
    }
    if (!sidebarMode) return
    const dismiss = (event: KeyboardEvent) => { if (event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); close() } }
    document.addEventListener('keydown', dismiss)
    return () => document.removeEventListener('keydown', dismiss)
  }, [sidebarMode, mode, close, cancelSelection])
  useEffect(() => () => { request.current?.abort(); request.current = null }, [])
  useLayoutEffect(() => {
    request.current?.abort(); request.current = null
    setPending(false); setAnswer(null); setError(null)
    setProgress('Ruošiama pasirinkto ploto analizė…')
  }, [projectDate])
  async function analyze() {
    if (!confirmed || request.current) return
    const controller = new AbortController()
    request.current = controller
    setPending(true); setError(null); setAnswer(null); setProgress('Ruošiama pasirinkto ploto analizė…')
    const timeout = window.setTimeout(() => controller.abort(), 65000)
    try {
      const response = await fetch('/api/map-analytics/agent/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' }, body: JSON.stringify({ bbox: confirmed, project_date: projectDate }), signal: controller.signal })
      if (!response.ok) throw new Error(response.status === 503 ? 'AI analizė nesukonfigūruota. Kreipkitės į administratorių.' : 'Analizės atlikti nepavyko. Bandykite dar kartą.')
      if (!response.body) throw new Error('Nepavyko gauti analizės atsakymo.')
      const reader = response.body.getReader(), decoder = new TextDecoder()
      let buffer = '', received = false
      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value, { stream: !done })
        let boundary: number
        while ((boundary = buffer.indexOf('\n\n')) >= 0) {
          const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2)
          const event = frame.split('\n').find(line => line.startsWith('event: '))?.slice(7)
          const dataLine = frame.split('\n').find(line => line.startsWith('data: '))
          if (!dataLine) continue
          const data = JSON.parse(dataLine.slice(6))
          if (request.current !== controller || currentProjectDate.current !== projectDate || controller.signal.aborted) continue
          if (event === 'result') {
            if (data.project_date !== projectDate) throw new Error('Gautas kitos datos atsakymas. Bandykite dar kartą.')
            setAnswer(data as Analysis); received = true
          }
          if (event === 'error') throw new Error(data.message)
          if (event === 'progress') {
            const tool = String(data.tool ?? '')
            const message = data.stage === 'synthesis' ? 'Rengiamos išvados iš surinktų duomenų…'
              : data.stage === 'investigation' ? investigationMessages[Math.max(0, Math.min(investigationMessages.length - 1, Number(data.round) - 1))]
              : tool.includes('population') ? 'Tikrinamas gyventojų tankis ir teritorijos aprėptis…'
              : tool.includes('request') ? 'Nagrinėjami gyventojų pranešimai…'
              : tool.includes('service') || tool.includes('fill') ? 'Nagrinėjama aptarnavimo istorija ir užpildymas…'
              : tool.includes('plan') || tool.includes('synthetic') ? 'Tikrinami surinkimo planai ir prognozės…'
              : tool === 'get_area_overview' ? 'Renkama pasirinkto ploto duomenų apžvalga…'
              : 'Tikrinami papildomi pasirinkto ploto duomenys…'
            setProgress(message)
          }
        }
        if (done) break
      }
      if (!received) throw new Error('Ryšys nutrūko negavus analizės atsakymo.')
    } catch (failure) {
      if (request.current === controller && currentProjectDate.current === projectDate) setError(controller.signal.aborted ? 'Ryšys nutrūko arba baigėsi laukimo laikas. Bandykite dar kartą.' : failure instanceof Error ? failure.message : 'Analizės atlikti nepavyko.')
    } finally {
      window.clearTimeout(timeout)
      if (request.current === controller) { request.current = null; setPending(false) }
    }
  }
  return (
    <section className="analytics-layout relative min-h-0 min-w-0 flex-1" aria-labelledby="analytics-title" data-project-date={projectDate} data-active-layers={activeLayers.map(layer => layer.id).join(' ')}>
      <h1 id="analytics-title" className="sr-only">Žemėlapio analitika</h1>
      <AnalyticsMap definitions={mapLayers} selection={selection} states={states} renderedData={renderedData} areaSelection={{ mode, draft, confirmed,
        onDraft: bbox => { setDraft(bbox); if (bbox) setMode('review') }, onCancel: cancelSelection,
        onRetake: () => { setDraft(null); setMode('drawing') },
        onConfirm: () => { if (draft) { setConfirmed(draft); setAnswer(null); setError(null); setDraft(null); setMode(null); setSidebarMode('ai'); requestAnimationFrame(() => aiTrigger.current?.focus()) } },
      }} />
      {mode && <Button variant="outline" className="absolute left-3 top-3 z-20" onClick={cancelSelection}>Atšaukti</Button>}
      {!mode && <div className="absolute left-3 top-3 z-10 flex gap-2">
        <Button ref={layersTrigger} className={sidebarMode === 'layers' ? 'shadow-md hover:bg-primary' : 'bg-card hover:bg-accent dark:bg-card dark:hover:bg-accent shadow-md'} variant={sidebarMode === 'layers' ? 'default' : 'outline'} size="icon" aria-label="Sluoksniai ir legenda" aria-expanded={sidebarMode === 'layers'} aria-controls="analytics-sidebar" onClick={() => sidebarMode === 'layers' ? close() : setSidebarMode('layers')}><Layers aria-hidden="true" /></Button>
        <Button ref={aiTrigger} className={sidebarMode === 'ai' ? 'shadow-md hover:bg-primary' : 'bg-card hover:bg-accent dark:bg-card dark:hover:bg-accent shadow-md'} variant={sidebarMode === 'ai' ? 'default' : 'outline'} size="icon" aria-label="AI ploto analizė" aria-expanded={sidebarMode === 'ai'} aria-controls="analytics-sidebar" onClick={() => sidebarMode === 'ai' ? close() : setSidebarMode('ai')}><Sparkles aria-hidden="true" /></Button>
      </div>}
      {sidebarMode && !mode && <aside id="analytics-sidebar" aria-label={sidebarMode === 'layers' ? 'Sluoksniai ir legenda' : 'AI ploto analizė'} className="absolute inset-x-3 bottom-10 z-10 flex max-h-[55%] flex-col rounded-lg border bg-card shadow-lg sm:inset-x-auto sm:bottom-10 sm:right-14 sm:top-3 sm:max-h-none sm:w-[360px] sm:max-w-[calc(100%-8rem)]">
        <div className="flex shrink-0 items-center justify-between border-b px-4 py-2"><h2 className="font-semibold">{sidebarMode === 'layers' ? 'Sluoksniai ir legenda' : 'AI ploto analizė'}</h2><Button variant="ghost" size="icon" aria-label="Uždaryti skydelį" onClick={close}><X aria-hidden="true" /></Button></div>
        <div className="min-h-0 space-y-5 overflow-y-auto p-4">
          {sidebarMode === 'layers' ? <>
            <section aria-label="Žemėlapio sluoksniai"><h3 className="mb-3 font-semibold">Sluoksniai</h3>
              <div role="group" aria-label="Sluoksnių sąrašas" className="space-y-4">
                {mapLayers.map(layer => {
                  const state = states[layer.id], selected = !!selection[layer.id]
                  return <div key={layer.id} className="space-y-2">
                    <label className="flex cursor-pointer items-center gap-2 text-sm font-medium"><input type="checkbox" className="size-4 shrink-0 accent-primary" checked={selected} onChange={event => {
                      if (layer.id === 'adequacy') adequacy.setEnabled(event.target.checked)
                      toggle(layer.id, event.target.checked)
                    }} />{layer.label}</label>
                    {layer.id === 'bins' && <div role="group" aria-label="Konteinerių atliekų rūšys" className="ml-6 space-y-3">{binFilters.availableCategories.map(category => <label key={category.id} className="flex cursor-pointer items-start gap-2 text-sm"><input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-primary" checked={binFilters.categories[category.id]} onChange={event => binFilters.toggleCategory(category.id, event.target.checked)} /><span>{category.label}</span></label>)}</div>}
                    {layer.id === 'adequacy' && selected && <div className="ml-6 space-y-3">
                      <label className="grid gap-2 text-sm font-medium">Mėnuo
                        <select aria-label="Analizės mėnuo" className="min-w-0 w-full rounded-md border bg-background p-2 text-sm" value={adequacy.month} onChange={event => adequacy.setMonth(event.target.value)}>
                          {adequacy.months.map(month => <option key={month} value={month}>{adequacyMonthLabel(month)}</option>)}
                        </select>
                      </label>
                      <label className="grid gap-2 text-sm font-medium">Atliekų rūšis
                        <select aria-label="Analizės atliekų rūšis" className="min-w-0 w-full rounded-md border bg-background p-2 text-sm" value={adequacy.wasteType} onChange={event => adequacy.setWasteType(event.target.value)}>
                          {adequacyWasteTypes.map(w => <option key={w.value} value={w.value}>{w.label}</option>)}
                        </select>
                      </label>
                      {adequacy.status === 'error' && <Button variant="outline" size="sm" className="h-auto whitespace-normal" onClick={adequacy.refresh}>Bandyti dar kartą</Button>}
                      {adequacy.status === 'loading' && <p role="status" className="text-xs">Kraunami duomenys…</p>}
                      {adequacy.status === 'ready' && !adequacy.selected && <p role="status" className="text-xs">Duomenų nėra.</p>}
                      {adequacy.status === 'error' && <p role="alert" className="text-xs text-destructive">Nepavyko įkelti sluoksnio.</p>}
                      {adequacy.selected && <p className="text-xs">{adequacyPeriodLabel(adequacy.selected)}</p>}
                    </div>}
                    {selected && state?.status === 'loading' && <p role="status" className="text-xs">Kraunami duomenys…</p>}
                    {selected && state?.status === 'ready' && state.data.features.length === 0 && <p role="status" className="text-xs">Duomenų nėra.</p>}
                    {layer.id === 'bins' && selected && state?.status === 'ready' && state.data.features.length > 0 && binFilters.noneSelected && <p role="status" className="text-xs">Nepasirinkta atliekų rūšių.</p>}
                    {selected && state?.status === 'error' && <div className="space-y-2"><p role="alert" className="text-xs text-destructive">Nepavyko įkelti sluoksnio.</p><Button variant="outline" size="sm" aria-label={`Bandyti dar kartą: ${layer.label}`} onClick={() => retry(layer.id)}>Bandyti dar kartą</Button></div>}
                  </div>
                })}
              </div>
            </section><MapLegend definitions={activeLayers} />
          </> : <>
            <Button variant="outline" disabled={pending} onClick={() => { setDraft(null); setMode('drawing'); setSidebarMode(null) }}>Pasirinkite plotą</Button>
            {confirmed ? <div className="space-y-3"><p className="break-words text-sm">Pasirinktas plotas: {confirmed.min_latitude.toFixed(5)}, {confirmed.min_longitude.toFixed(5)} – {confirmed.max_latitude.toFixed(5)}, {confirmed.max_longitude.toFixed(5)}</p>{answer?.status !== 'complete' && <Button className="h-auto whitespace-normal" disabled={pending} onClick={analyze}>{answer || error ? 'Bandyti dar kartą' : 'Analizuoti pasirinktą plotą'}</Button>}</div> : <p className="text-sm text-muted-foreground">Pažymėkite analizuojamą plotą žemėlapyje.</p>}
            {pending && <p role="status" className="analytics-progress text-sm">{progress}</p>}
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            {answer && <div className="space-y-3">
              {answer.status === 'incomplete' && <p role="status" className="text-sm">Analizė nebaigta. {answer.answer && 'Pateikiamas dalinis atsakymas.'} Galite bandyti dar kartą.</p>}
              {answer.answer && <div className="analytics-answer min-w-0 break-words text-sm"><Markdown skipHtml remarkPlugins={[remarkGfm]}>{answer.answer}</Markdown></div>}
            </div>}
          </>}
        </div>
      </aside>}
    </section>
  )
}
