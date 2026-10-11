import { useCallback, useEffect, useReducer, useRef } from 'react'
import { useToast } from '@/components/ui/toast-context'
import { loadRoute, RouteError, saveService, type FillLevel } from './api'
import { allChosen, driverReducer, initialState } from './driver-state'

export const SAVE_ERROR = 'Nepavyko išsaugoti duomenų. Bandykite dar kartą.'

export function useDriverWorkflow(truckId: number, projectDate: string) {
  const notify = useToast()
  const [state, dispatch] = useReducer(driverReducer, initialState)
  const controller = useRef<AbortController | null>(null)
  const saving = useRef(false)

  useEffect(() => () => controller.current?.abort(), [])

  const start = useCallback(() => {
    if (state.status !== 'idle' && state.status !== 'error') return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    dispatch({ type: 'start' })
    loadRoute(truckId, projectDate, current.signal)
      .then((route) => {
        if (!current.signal.aborted) dispatch({ type: 'route_loaded', route })
      })
      .catch((error: unknown) => {
        if (!current.signal.aborted)
          dispatch({ type: 'route_failed', reason: error instanceof RouteError ? error.reason : 'failed' })
      })
  }, [state.status, truckId, projectDate])

  // The request is sent from the click handler, not an effect, so a repeated tap or
  // development double-invocation can never store a stop twice.
  const confirm = useCallback(() => {
    if (
      state.status !== 'at_bin' || state.step !== state.levels.length ||
      !allChosen(state.levels) || saving.current
    )
      return
    const items = state.route.stops[state.stopIndex].bins.map((bin, index) => ({
      bin_id: bin.bin_id,
      fill_level: state.levels[index] as FillLevel,
    }))
    saving.current = true
    dispatch({ type: 'confirm' })
    saveService(items)
      .then(() => dispatch({ type: 'save_succeeded' }))
      .catch(() => {
        notify({ message: SAVE_ERROR, variant: 'error' })
        dispatch({ type: 'save_failed' })
      })
      .finally(() => {
        saving.current = false
      })
  }, [state, notify])

  return {
    state,
    start,
    confirm,
    arrived: useCallback(() => dispatch({ type: 'arrived' }), []),
    choose: useCallback((level: FillLevel) => dispatch({ type: 'choose', level }), []),
    back: useCallback(() => dispatch({ type: 'back' }), []),
  }
}
