import { useEffect, useEffectEvent } from 'react'

// Demo speed, faster than a real truck so a route can be shown in minutes.
export const DEMO_SPEED_MPS = 100
const SLOW_ZONE_M = 250
const MIN_SPEED_FACTOR = 0.25
const MAX_STEP_MS = 100

type Options = {
  running: boolean
  from: number
  to: number
  onFrame: (distance: number) => void
  onArrive: () => void
}

// Advances a distance along the path from `from` to `to` while running, slowing near `to`.
// When not running it only reports `from`, which is where the truck stands.
export function useRouteAnimator({ running, from, to, onFrame, onArrive }: Options) {
  const frame = useEffectEvent(onFrame)
  const arrive = useEffectEvent(onArrive)

  useEffect(() => {
    frame(from)
    if (!running) return
    let distance = from
    let last = performance.now()
    let id = 0
    const tick = (now: number) => {
      // Cap the step so a throttled background tab cannot jump past a stop.
      const seconds = Math.min(now - last, MAX_STEP_MS) / 1000
      last = now
      const factor = Math.max(MIN_SPEED_FACTOR, Math.min(1, (to - distance) / SLOW_ZONE_M))
      distance = Math.min(to, distance + DEMO_SPEED_MPS * factor * seconds)
      frame(distance)
      if (distance >= to) {
        arrive()
        return
      }
      id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [running, from, to])
}
