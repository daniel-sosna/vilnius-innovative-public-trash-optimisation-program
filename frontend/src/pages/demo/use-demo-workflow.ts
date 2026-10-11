import { useCallback, useEffect, useRef, useState } from 'react'
import { LngLatBounds, type Map as LibreMap } from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'
import { useProjectDate } from '@/lib/project-date/context'
import { getNavigation, getPrediction, type DemoRoute, type PredictedBin, type Prediction } from './api'
import { emptyCollection, routeFeatures } from './geometry'

export type Stage = 'idle' | 'predicting' | 'bin_animation' | 'predicted' | 'routing' | 'route_animation' | 'completed' | 'empty' | 'error'
type State = { date: string; stage: Stage; prediction: Prediction | null; binRevealOrder: PredictedBin[]; visibleBinCount: number; routes: DemoRoute[]; routeData: FeatureCollection; error?: string; failedStage?: Stage; key?: number; awaitingPaint?: boolean }
type Run = { owner: symbol; key: number; controller: AbortController; phase: Stage; frame?: number; timer?: number; revealTimer?: number; visibleBinCount?: number; revealStep?: number }
const initial = (date: string): State => ({ date, stage: 'idle', prediction: null, binRevealOrder: [], visibleBinCount: 0, routes: [], routeData: emptyCollection })

export function useDemoWorkflow() {
  const { projectDate, acquire, release, locked } = useProjectDate()
  const [state, setState] = useState<State>(() => initial(projectDate))
  const current = useRef<Run | null>(null), sequence = useRef(0)
  const map = useRef<LibreMap | null>(null), mapStatus = useRef('loading')
  const stop = useCallback((run: Run) => {
    run.controller.abort()
    if (run.frame !== undefined) cancelAnimationFrame(run.frame)
    window.clearTimeout(run.timer)
    window.clearTimeout(run.revealTimer)
    release(run.owner)
    if (current.current === run) current.current = null
  }, [release])
  const fail = useCallback((run: Run, message: string) => {
    if (current.current !== run) return
    setState(previous => ({ ...previous, stage: 'error', failedStage: run.phase, routes: [], routeData: emptyCollection, awaitingPaint: false, error: message }))
    stop(run)
  }, [stop])
  const onMapState = useCallback((status: 'loading' | 'ready' | 'error', instance: LibreMap | null) => {
    map.current = instance; mapStatus.current = status
    if (status === 'error' && current.current) fail(current.current, 'Žemėlapio nepavyko įkelti arba piešti. Bandykite dar kartą.')
  }, [fail])
  useEffect(() => () => { if (current.current) stop(current.current) }, [projectDate, stop])

  const start = useCallback(async () => {
    if (current.current) return
    const owner = Symbol('demo-run')
    if (!acquire(owner)) return
    const run: Run = { owner, key: ++sequence.current, controller: new AbortController(), phase: 'predicting' }
    current.current = run
    setState({ ...initial(projectDate), stage: 'predicting', key: run.key })
    if (mapStatus.current === 'error') { fail(run, 'Žemėlapis nepasiekiamas. Patikrinkite konfigūraciją arba bandykite dar kartą.'); return }
    try {
      const prediction = await getPrediction(projectDate, run.controller.signal)
      if (current.current !== run) return
      if (prediction.project_date !== projectDate) throw new Error('Prognozės data neatitinka pasirinktos dienos.')
      if (!prediction.due_count || prediction.unmappable_count === prediction.due_count) {
        setState(previous => ({ ...previous, prediction, stage: 'empty' })); stop(run); return
      }
      const points = prediction.bins.filter(bin => bin.fill_level > 2 && bin.latitude !== null && bin.longitude !== null)
      // Shuffle a separate visual order once per run, preserving the prediction/routing input.
      for (let index = points.length - 1; index > 0; index--) {
        const other = Math.floor(Math.random() * (index + 1))
        const point = points[index]
        points[index] = points[other]
        points[other] = point
      }
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      run.phase = reducedMotion ? 'predicted' : 'bin_animation'
      run.visibleBinCount = reducedMotion ? points.length : 1
      run.revealStep = 0
      setState(previous => ({ ...previous, prediction, binRevealOrder: points, stage: run.phase, visibleBinCount: run.visibleBinCount! }))
      if (map.current && points.length) {
        const bounds = new LngLatBounds()
        for (const bin of points) bounds.extend([bin.longitude!, bin.latitude!])
        map.current.fitBounds(bounds, { padding: 50, maxZoom: 14, duration: 0 })
      }
      run.timer = window.setTimeout(() => fail(run, 'Konteinerių nepavyko parodyti žemėlapyje. Bandykite dar kartą.'), 20000)
    } catch (error) { if (current.current === run) fail(run, error instanceof Error ? error.message : 'Prognozavimas nepavyko.') }
  }, [projectDate, acquire, stop, fail])

  const onPresented = useCallback(async (key: number) => {
    const run = current.current
    if (!run || run.key !== key) return
    if (run.phase === 'route_animation' && state.awaitingPaint) {
      setState(previous => ({ ...previous, stage: 'completed', awaitingPaint: false })); stop(run); return
    }
    if (run.phase === 'bin_animation' && state.prediction) {
      // Ignore acknowledgements from a previous source update or an already scheduled batch.
      if (run.visibleBinCount !== state.visibleBinCount || run.revealTimer !== undefined) return
      const total = state.binRevealOrder.length
      if (state.visibleBinCount < total) {
        window.clearTimeout(run.timer)
        const delay = Math.max(180, 700 * 0.88 ** Math.floor((run.revealStep ?? 0) / 3))
        run.revealTimer = window.setTimeout(() => {
          run.revealTimer = undefined
          if (current.current !== run) return
          const nextStep = (run.revealStep ?? 0) + 1
          const batchSize = 2 ** Math.floor(nextStep / 3)
          const visibleBinCount = Math.min(total, state.visibleBinCount + batchSize)
          run.visibleBinCount = visibleBinCount
          run.revealStep = nextStep
          setState(previous => ({ ...previous, visibleBinCount }))
          run.timer = window.setTimeout(() => fail(run, 'Konteinerių nepavyko parodyti žemėlapyje. Bandykite dar kartą.'), 20000)
        }, delay)
        return
      }
      // The final batch is on the map before navigation starts.
      run.phase = 'predicted'
    }
    if (run.phase !== 'predicted' || !state.prediction) return
    window.clearTimeout(run.timer)
    run.phase = 'routing'
    setState(previous => ({ ...previous, stage: 'routing' }))
    try {
      const prediction = state.prediction
      const routes = await getNavigation(prediction.forecast_date, prediction.bins.filter(bin => bin.latitude !== null && bin.longitude !== null).map(bin => bin.bin_id), run.controller.signal)
      if (current.current !== run) return
      if (!map.current) throw new Error('Žemėlapis nepasiekiamas maršrutams piešti.')
      run.phase = 'route_animation'
      setState(previous => ({ ...previous, stage: 'route_animation', routes, routeData: routeFeatures(routes, 0) }))
      const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 150 : 4000
      const began = performance.now()
      run.timer = window.setTimeout(() => fail(run, 'Maršrutų piešimas nebaigtas. Bandykite dar kartą.'), 20000)
      const draw = (now: number) => {
        if (current.current !== run) return
        try {
          const progress = Math.min(1, (now - began) / duration)
          setState(previous => ({ ...previous, routeData: routeFeatures(routes, progress), awaitingPaint: progress >= 1 }))
          if (progress < 1) { run.frame = requestAnimationFrame(draw); return }
          // AnalyticsMap acknowledges the final source update after React commits it.
        } catch { fail(run, 'Maršrutų piešimas nepavyko. Bandykite dar kartą.') }
      }
      run.frame = requestAnimationFrame(draw)
    } catch (error) { if (current.current === run) fail(run, error instanceof Error ? error.message : 'Maršrutų skaičiavimas nepavyko.') }
  }, [state.prediction, state.binRevealOrder, state.visibleBinCount, state.awaitingPaint, fail, stop])

  // A terminal result from another date is never rendered or automatically rerun.
  const shown = state.date === projectDate ? state : initial(projectDate)
  return { state: shown, start, onMapState, onPresented, locked }
}
