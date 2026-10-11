import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CheckCircle2, LoaderCircle, LocateFixed } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { buildGeometry, type LonLat } from '@/lib/route-geometry'
import { truckExists, type FillLevel } from './api'
import { BinLevelStep } from './bin-level-step'
import { binCount, allChosen } from './driver-state'
import { NavigationMap, type NavigationMapHandle, type StopState } from './navigation-map'
import { NextStopPanel } from './next-stop-panel'
import { StopDoneView } from './stop-done-view'
import { useDriverWorkflow } from './use-driver-workflow'
import { useRouteAnimator } from './use-route-animator'

const MISSING_DATA = 'Šiai dienai paruošto maršruto duomenų nėra.'
const EMPTY_ROUTE = 'Šiandien suplanuotų konteinerių nėra.'
const FAILED = 'Nepavyko paruošti maršruto. Bandykite dar kartą.'
const TRUCK_MISSING = 'Šiukšliavežė nerasta.'

export function DriverRouteScreen() {
  const { truck_id = '' } = useParams()
  const truckId = /^[1-9]\d*$/.test(truck_id) && Number.isSafeInteger(Number(truck_id)) ? Number(truck_id) : null
  if (truckId === null) return <Message text={TRUCK_MISSING} />
  return <TruckRoute key={truckId} truckId={truckId} />
}

function Message({ text, action }: { text: string; action?: { label: string; onClick: () => void } }) {
  return (
    <main className="flex h-dvh flex-col items-center justify-center gap-6 bg-background p-6 text-center">
      <p role="alert" className="text-2xl font-semibold">{text}</p>
      {action && (
        <Button onClick={action.onClick} className="h-14 w-full max-w-xs text-lg">{action.label}</Button>
      )}
      <Button variant="outline" asChild className="h-14 w-full max-w-xs text-lg">
        <Link to="/driver">Atgal</Link>
      </Button>
    </main>
  )
}

function TruckRoute({ truckId }: { truckId: number }) {
  const [missing, setMissing] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    truckExists(truckId, controller.signal).then((result) => {
      if (!controller.signal.aborted && result === 'missing') setMissing(true)
    })
    return () => controller.abort()
  }, [truckId])
  if (missing) return <Message text={TRUCK_MISSING} />
  return <Workflow truckId={truckId} />
}

function Workflow({ truckId }: { truckId: number }) {
  const { state, start, confirm, arrived, choose, back } = useDriverWorkflow(truckId)
  const mapRef = useRef<NavigationMapHandle>(null)
  const [following, setFollowing] = useState(true)

  const route = 'route' in state ? state.route : null
  const geometry = useMemo(
    () => buildGeometry((route?.path ?? []).map((point): LonLat => [point.longitude, point.latitude])),
    [route],
  )
  const stopDistances = useMemo(
    () => (route?.stops ?? []).map((stop) => geometry.cumulative[stop.path_index]),
    [route, geometry],
  )

  // Index of the stop the truck drives to or stands at, and how many stops are finished.
  let currentStop = -1
  let finished = 0
  if (state.status === 'navigating') currentStop = finished = state.nextStop
  else if (state.status === 'at_bin' || state.status === 'saving_service') currentStop = finished = state.stopIndex
  else if (state.status === 'completed') finished = stopDistances.length

  const standing = state.status === 'navigating' ? null : finished === stopDistances.length ? finished - 1 : currentStop
  const from = state.status === 'navigating'
    ? (state.nextStop === 0 ? 0 : stopDistances[state.nextStop - 1])
    : standing !== null && standing >= 0 ? stopDistances[standing] : 0
  const to = state.status === 'navigating' ? stopDistances[state.nextStop] : from

  useRouteAnimator({
    running: state.status === 'navigating',
    from,
    to,
    onFrame: (distance) => mapRef.current?.update(distance),
    onArrive: arrived,
  })

  const stopStates = useMemo(
    () =>
      stopDistances.map((distance, index): { distance: number; state: StopState } => ({
        distance,
        state: index < finished ? 'done' : index === currentStop ? 'next' : 'future',
      })),
    [stopDistances, finished, currentStop],
  )

  if (state.status === 'idle')
    return (
      <main className="flex h-dvh flex-col items-center justify-center gap-6 bg-background p-6">
        <Button onClick={start} className="h-20 w-full max-w-sm text-2xl">Pradėti maršrutą</Button>
        <Button variant="outline" asChild className="h-14 w-full max-w-sm text-lg">
          <Link to="/driver">Atgal</Link>
        </Button>
      </main>
    )
  if (state.status === 'preparing_route')
    return (
      <main role="status" className="flex h-dvh flex-col items-center justify-center gap-4 bg-background p-6 text-xl">
        <LoaderCircle className="size-10 animate-spin text-primary" aria-hidden="true" />
        Ruošiamas maršrutas...
      </main>
    )
  if (state.status === 'error')
    return (
      <Message
        text={
          state.reason === 'empty' ? EMPTY_ROUTE
            : state.reason === 'no_plan' ? MISSING_DATA
            : state.reason === 'truck_missing' ? TRUCK_MISSING
            : FAILED
        }
        action={state.reason === 'truck_missing' ? undefined : { label: 'Bandyti dar kartą', onClick: start }}
      />
    )

  const activeStop = currentStop >= 0 ? state.route.stops[currentStop] : null
  const serviced = binCount(state.route, finished)

  return (
    <main className="relative h-dvh overflow-hidden bg-slate-900">
      <NavigationMap
        ref={mapRef}
        geometry={geometry}
        stops={stopStates}
        following={following}
        onUserPan={() => setFollowing(false)}
      />
      {state.status === 'navigating' && activeStop && (
        <NextStopPanel stop={activeStop} serviced={serviced} total={binCount(state.route)} />
      )}
      {state.status === 'navigating' && !following && (
        <button
          type="button"
          onClick={() => setFollowing(true)}
          aria-label="Grįžti prie šiukšliavežės"
          className="absolute bottom-6 right-4 z-10 flex size-16 items-center justify-center rounded-full bg-white text-slate-900 shadow-xl"
        >
          <LocateFixed className="size-8" aria-hidden="true" />
        </button>
      )}
      {(state.status === 'at_bin' || state.status === 'saving_service') && activeStop &&
        (state.status === 'saving_service' || state.step === state.levels.length ? (
          allChosen(state.levels) && (
            <StopDoneView
              stop={activeStop}
              levels={state.levels}
              saving={state.status === 'saving_service'}
              onBack={back}
              onConfirm={confirm}
            />
          )
        ) : (
          <BinLevelStep
            address={activeStop.address}
            bin={activeStop.bins[state.step]}
            position={state.step + 1}
            total={activeStop.bins.length}
            chosen={state.levels[state.step] as FillLevel | null}
            onChoose={choose}
            onBack={state.step > 0 ? back : null}
          />
        ))}
      {state.status === 'completed' && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 bg-background p-6 text-center">
          <CheckCircle2 className="size-20 text-primary" aria-hidden="true" />
          <h1 className="text-3xl font-bold">Maršrutas baigtas</h1>
          <p className="text-xl">Aptarnauta: {state.serviced} konteinerių</p>
          <Button asChild className="mt-4 h-14 w-full max-w-xs text-lg">
            <Link to="/driver">Baigti</Link>
          </Button>
        </div>
      )}
    </main>
  )
}
