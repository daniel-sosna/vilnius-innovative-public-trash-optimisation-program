import type { DriverRoute, FillLevel, RouteFailure } from './api'

export type Levels = (FillLevel | null)[]

export type DriverState =
  | { status: 'idle' }
  | { status: 'preparing_route' }
  | { status: 'navigating'; route: DriverRoute; nextStop: number }
  // `step` is the bin index being asked, or the bin count for the all-done view.
  | { status: 'at_bin'; route: DriverRoute; stopIndex: number; step: number; levels: Levels }
  | { status: 'saving_service'; route: DriverRoute; stopIndex: number; levels: Levels }
  | { status: 'completed'; route: DriverRoute; serviced: number }
  | { status: 'error'; reason: RouteFailure | 'empty' }

export type DriverAction =
  | { type: 'start' }
  | { type: 'route_loaded'; route: DriverRoute }
  | { type: 'route_failed'; reason: RouteFailure }
  | { type: 'arrived' }
  | { type: 'choose'; level: FillLevel }
  | { type: 'back' }
  | { type: 'confirm' }
  | { type: 'save_succeeded' }
  | { type: 'save_failed' }

export const initialState: DriverState = { status: 'idle' }

export function binCount(route: DriverRoute, stops = route.stops.length): number {
  return route.stops.slice(0, stops).reduce((sum, stop) => sum + stop.bins.length, 0)
}

export function allChosen(levels: Levels): levels is FillLevel[] {
  return levels.every((level) => level !== null)
}

export function driverReducer(state: DriverState, action: DriverAction): DriverState {
  switch (action.type) {
    case 'start':
      return state.status === 'idle' || state.status === 'error' ? { status: 'preparing_route' } : state
    case 'route_loaded':
      if (state.status !== 'preparing_route') return state
      return action.route.stops.length === 0
        ? { status: 'error', reason: 'empty' }
        : { status: 'navigating', route: action.route, nextStop: 0 }
    case 'route_failed':
      return state.status === 'preparing_route' ? { status: 'error', reason: action.reason } : state
    case 'arrived':
      if (state.status !== 'navigating') return state
      return {
        status: 'at_bin',
        route: state.route,
        stopIndex: state.nextStop,
        step: 0,
        levels: state.route.stops[state.nextStop].bins.map(() => null),
      }
    case 'choose': {
      if (state.status !== 'at_bin' || state.step >= state.levels.length) return state
      const levels = state.levels.map((level, index) => (index === state.step ? action.level : level))
      return { ...state, levels, step: state.step + 1 }
    }
    case 'back':
      return state.status === 'at_bin' && state.step > 0 ? { ...state, step: state.step - 1 } : state
    case 'confirm':
      if (state.status !== 'at_bin' || state.step !== state.levels.length || !allChosen(state.levels))
        return state
      return { status: 'saving_service', route: state.route, stopIndex: state.stopIndex, levels: state.levels }
    case 'save_succeeded':
      if (state.status !== 'saving_service') return state
      return state.stopIndex === state.route.stops.length - 1
        ? { status: 'completed', route: state.route, serviced: binCount(state.route) }
        : { status: 'navigating', route: state.route, nextStop: state.stopIndex + 1 }
    case 'save_failed':
      return state.status === 'saving_service'
        ? { status: 'at_bin', route: state.route, stopIndex: state.stopIndex, step: state.levels.length, levels: state.levels }
        : state
  }
}
