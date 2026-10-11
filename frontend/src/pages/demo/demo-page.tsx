import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Circle, LoaderCircle, X } from 'lucide-react'
import { AnalyticsMap } from '@/components/maps/analytics-map'
import { Button } from '@/components/ui/button'
import { TablePagination } from '@/components/table-pagination'
import { forecastDate, useProjectDate } from '@/lib/project-date/context'
import { demoLayers, demoSelection, selectedFeatures } from './layers'
import { useDemoWorkflow } from './use-demo-workflow'

const truckPageSize = 5
export function DemoPage() {
  const { projectDate } = useProjectDate()
  const { state, start, onMapState, onPresented, locked } = useDemoWorkflow()
  const [pagination, setPagination] = useState({ run: state.key, page: 1 })
  const page = pagination.run === state.key ? pagination.page : 1
  const visibleRoutes = state.routes.slice((page - 1) * truckPageSize, page * truckPageSize)
  const selectedData = useMemo(() => selectedFeatures(state.binRevealOrder, state.visibleBinCount), [state.binRevealOrder, state.visibleBinCount])
  const states = useMemo(() => ({ 'demo-selected': { status: 'ready' as const, data: selectedData } }), [selectedData])
  const active = ['predicting', 'bin_animation', 'predicted', 'routing'].includes(state.stage)
  const trucksPending = ['bin_animation', 'predicted', 'routing'].includes(state.stage)
  const predictionFailed = state.stage === 'error' && state.failedStage === 'predicting'
  const PredictionIcon = predictionFailed ? X : state.prediction ? Check : state.stage === 'predicting' ? LoaderCircle : Circle
  return <section className="min-w-0 space-y-4" aria-labelledby="demo-title">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 id="demo-title" className="text-2xl font-semibold">Maršrutai</h1><p className="text-sm text-muted-foreground">Projekto data: {projectDate} · Aptarnavimo diena: {forecastDate(projectDate)}</p></div>
      <Button className="h-auto min-h-10 max-w-full whitespace-normal" disabled={active || locked} onClick={() => void start()}>Pradėti maršrutų planavimą</Button>
    </div>
    {state.stage !== 'completed' && <ol aria-label="Planavimo eiga" aria-live="polite" className="flex flex-wrap gap-x-6 gap-y-2 rounded-lg border p-3 text-sm">
      <li className="flex items-center gap-2"><PredictionIcon aria-hidden="true" className={`size-4 shrink-0 ${state.stage === 'predicting' ? 'animate-spin motion-reduce:animate-none' : ''} ${predictionFailed ? 'text-destructive' : state.prediction ? 'text-green-700' : ''}`} /><span>Konteinerių prognozavimas<span className="sr-only">: {predictionFailed ? 'nepavyko' : state.prediction ? 'baigta' : state.stage === 'predicting' ? 'vyksta' : 'laukiama'}</span></span></li>
    </ol>}
    {state.stage !== 'completed' && state.prediction && <p className="text-sm">Įvertinta: {state.prediction.evaluated_count} · Žemėlapyje: {state.visibleBinCount}{state.prediction.unmappable_count > 0 && ` · Be tinkamų koordinačių: ${state.prediction.unmappable_count}`}</p>}
    {state.stage === 'empty' && <p role="status">{state.prediction?.due_count ? 'Aptarnauti skirtų konteinerių koordinatės netinkamos. Maršrutų sudaryti negalima.' : 'Šiai dienai aptarnauti skirtų konteinerių nerasta.'}</p>}
    {state.error && <p role="alert" className="text-sm text-destructive">{state.error}</p>}
    {state.stage === 'completed' && state.unserved.length > 0 && <div role="status" className="space-y-1 text-sm"><p>Nesuplanuota konteinerių: {state.unserved.reduce((count, stop) => count + stop.bin_ids.length, 0)}</p>{[...new Set(state.unserved.map(stop => stop.reason))].map(reason => <p key={reason} className="text-muted-foreground">{reason}</p>)}</div>}
    <div className="h-[58dvh] min-h-80 overflow-hidden rounded-lg border">
      <AnalyticsMap definitions={demoLayers} selection={demoSelection} states={states} accessibleLabel="Prognozuotų konteinerių žemėlapis" onMapState={onMapState} presentationKey={state.stage === 'bin_animation' || state.stage === 'predicted' ? state.key : undefined} onPresented={onPresented} />
    </div>
    <p className="text-xs text-muted-foreground"><a className="underline" href="https://project-osrm.org/">OSRM</a> · © <a className="underline" href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · <a className="underline" href="https://www.openstreetmap.org/">Taisyti žemėlapį</a></p>
    {state.prediction && <div className="space-y-3">
      <p role="status" className="font-medium">{state.stage === 'completed' ? `Maršrutai paruošti · Šiukšliavežės: ${state.routes.length}` : 'Šiukšliavežės'}</p>
      <table className="w-full table-fixed text-left text-sm" aria-busy={trucksPending}>
        <caption className="sr-only">Priskirtos šiukšliavežės</caption>
        <thead><tr><th className="py-2">Šiukšliavežė / maršrutas</th><th className="w-20">Vietos</th><th className="w-24">Konteineriai</th></tr></thead>
        <tbody>
          {trucksPending && <tr className="border-t"><td colSpan={3} className="py-6"><div role="status" className="flex items-center justify-center gap-2 text-muted-foreground"><LoaderCircle aria-hidden="true" className="size-4 shrink-0 animate-spin motion-reduce:animate-none" /><span>{state.stage === 'routing' ? 'Maršrutų skaičiavimas' : 'Ruošiami maršrutų duomenys'}</span></div></td></tr>}
          {!trucksPending && state.routes.length === 0 && <tr className="border-t"><td colSpan={3} className="py-6 text-center text-muted-foreground">{state.stage === 'error' ? 'Maršrutų paruošti nepavyko.' : 'Priskirtų šiukšliavežių nėra.'}</td></tr>}
          {visibleRoutes.map(route => <tr key={route.route_id} className="border-t"><td className="break-words py-3 pr-2"><Link to={`/admin/routes/truck/${route.truck_id}?run_id=${state.runId}`} className="inline-flex max-w-full items-center gap-2 rounded-sm underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-ring"><span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: route.color }} aria-hidden="true" /><span>{route.truck_name}<span className="block text-xs text-muted-foreground">{route.route_id}</span></span></Link></td><td>{route.stopCount}</td><td>{route.binCount}</td></tr>)}
        </tbody>
      </table>
      {state.routes.length > 0 && <TablePagination page={page} pageSize={truckPageSize} total={state.routes.length} onPageChange={next => setPagination({ run: state.key, page: next })} />}
    </div>}
  </section>
}
